"""NAV SIDE: Measurement Model A — predicted star-pair angles for a
hypothesized spacecraft state, and their sensitivity (Jacobian) to that
state. Uses ONLY public catalog values handed in by the caller; never
touches galnav/truth/."""

import numpy as np

from galnav.units import C_KM_S, kms_to_beta


def _unit_directions(star_pos_au, obs_pos_au):
    """Unit direction vectors from hypothesized observer position(s) to each star.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au — a single
                (3,) position or a whole batch (T, 3) of Monte Carlo
                trials at once (project rule: vectorize over trials).
    Returns: (unit (..., N, 3) dimensionless, range (..., N) in au).
    """
    obs = np.asarray(obs_pos_au, dtype=float)
    towards = np.asarray(star_pos_au, dtype=float) - obs[..., None, :]
    ranges = np.linalg.norm(towards, axis=-1)
    return towards / ranges[..., None], ranges


def _pair_sin_cos(unit, pairs):
    """sin and cos of each pair angle, precise at ALL angles.

    sin comes from the cross product's length and cos from the dot
    product; arctan2(sin, cos) then never suffers arccos's precision
    collapse near 0 and pi (needed: the real sky contains close binary
    pairs with nearly-zero separation angles).

    unit: (..., N, 3) unit direction vectors (dimensionless).
    pairs: (P, 2) integer star indices.
    Returns: (sin (..., P), cos (..., P)), both dimensionless.
    """
    u_i, u_j = unit[..., pairs[:, 0], :], unit[..., pairs[:, 1], :]
    sin_t = np.linalg.norm(np.cross(u_i, u_j), axis=-1)
    cos_t = np.sum(u_i * u_j, axis=-1)
    return sin_t, cos_t


def predicted_pair_angles(star_pos_au, obs_pos_au, pairs):
    """Angles the camera WOULD see between star pairs from guessed position(s).

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (..., P) predicted angles, radians.
    """
    pairs = np.asarray(pairs)
    unit, _ = _unit_directions(star_pos_au, obs_pos_au)
    sin_t, cos_t = _pair_sin_cos(unit, pairs)
    return np.arctan2(sin_t, cos_t)


def pair_angle_jacobian(star_pos_au, obs_pos_au, pairs):
    """Sensitivity of each predicted pair angle to the position guess.

    Derived by the chain rule from angle = arccos(u_i . u_j), where
    u = (s - p)/|s - p|; full derivation in journal/spec-4-measmodel.md.
    Pairs must be distinct, non-antipodal stars (0 < angle < pi) -- true
    for any real star field.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (..., P, 3) d(angle)/d(position), radians per au.
    """
    pairs = np.asarray(pairs)
    unit, ranges = _unit_directions(star_pos_au, obs_pos_au)
    u_i, u_j = unit[..., pairs[:, 0], :], unit[..., pairs[:, 1], :]
    r_i, r_j = ranges[..., pairs[:, 0]], ranges[..., pairs[:, 1]]
    sin_t, cos_t = _pair_sin_cos(unit, pairs)
    dcos_dp = (cos_t[..., None] * u_i - u_j) / r_i[..., None] + (
        cos_t[..., None] * u_j - u_i
    ) / r_j[..., None]
    return -dcos_dp / sin_t[..., None]


def _sun_units(star_pos_au):
    """Unit direction from the barycenter to each catalog star.

    star_pos_au: (N, 3) catalog star positions, au.
    Returns: (N, 3) Sun->star unit vectors, dimensionless. A catalog
             DISTANCE error moves the star along this direction.
    """
    stars = np.asarray(star_pos_au, dtype=float)
    return stars / np.linalg.norm(stars, axis=-1)[..., None]


def pair_angle_dist_jacobian(star_pos_au, obs_pos_au, pairs):
    """Sensitivity of each predicted pair angle to each star's catalog
    DISTANCE (the direction a parallax error moves a star).

    Same chain rule as pair_angle_jacobian, but the perturbed point is the
    STAR, moved radially along its Sun->star unit u_hat (derivation D7,
    journal/spec-7-catalog-covariance.md):
        d(angle)/d(d_i) = [cos(angle) (u_hat_i . u_i) - u_hat_i . u_j]
                          / (r_i sin(angle))
    where u/r are spacecraft->star units/ranges.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (..., P, N) d(angle)/d(star distance), radians per au — each
             row nonzero only at its pair's two star columns.
    """
    pairs = np.asarray(pairs)
    unit, ranges = _unit_directions(star_pos_au, obs_pos_au)
    sun_u = _sun_units(star_pos_au)
    u_i, u_j = unit[..., pairs[:, 0], :], unit[..., pairs[:, 1], :]
    r_i, r_j = ranges[..., pairs[:, 0]], ranges[..., pairs[:, 1]]
    hat_i, hat_j = sun_u[pairs[:, 0]], sun_u[pairs[:, 1]]
    sin_t, cos_t = _pair_sin_cos(unit, pairs)
    g_i = (cos_t * np.sum(hat_i * u_i, axis=-1) - np.sum(hat_i * u_j, axis=-1)) / (
        r_i * sin_t
    )
    g_j = (cos_t * np.sum(hat_j * u_j, axis=-1) - np.sum(hat_j * u_i, axis=-1)) / (
        r_j * sin_t
    )
    n_stars = np.asarray(star_pos_au).shape[0]
    jac = np.zeros(g_i.shape[:-1] + (len(pairs), n_stars))
    jac[..., np.arange(len(pairs)), pairs[:, 0]] = g_i
    jac[..., np.arange(len(pairs)), pairs[:, 1]] = g_j
    return jac


def catalog_angle_covariance(star_pos_au, obs_pos_au, pairs, sigma_dist_au):
    """The catalog term of the measurement error budget: pair-angle
    covariance from per-star catalog distance errors.

    R_cat = G diag(sigma_dist^2) G^T with G the distance Jacobian — DENSE,
    because two pairs sharing a star carry the SAME distance error and are
    therefore correlated (rank-1 per star, never independent).

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    pairs: (P, 2) integer star indices per measured pair.
    sigma_dist_au: (N,) 1-sigma catalog distance error per star, au.
    Returns: (..., P, P) pair-angle covariance, radians^2.
    """
    jac = pair_angle_dist_jacobian(star_pos_au, obs_pos_au, pairs)
    var = np.asarray(sigma_dist_au, dtype=float) ** 2
    return np.einsum("...pi,i,...qi->...pq", jac, var, jac)


def _aberrate_nav(unit, vel_kms):
    """Directions a MOVING camera would report: exact special-relativistic
    aberration of each hypothesized unit direction (the navigator's own
    implementation, written independently of truth's; the zero-noise
    recovery test cross-checks the two through a full inversion).

    k-form, finite at v = 0 (never (gamma-1)/|v|^2): with b = v/c,
    gamma = 1/sqrt(1 - |b|^2), k = gamma^2/(gamma + 1),
    s = k (b . u) + gamma, D = gamma (1 + b . u):

        u' = (u + s b) / D

    unit: (..., N, 3) unit directions toward the stars, dimensionless.
    vel_kms: (..., 3) hypothesized spacecraft velocity, km/s.
    Returns: (..., N, 3) aberrated unit directions, dimensionless.
    """
    beta = kms_to_beta(vel_kms)
    gamma = 1.0 / np.sqrt(1.0 - np.sum(beta * beta, axis=-1))
    k = gamma**2 / (gamma + 1.0)
    b_dot_u = np.sum(beta[..., None, :] * unit, axis=-1)  # (..., N)
    s = k[..., None] * b_dot_u + gamma[..., None]
    denom = gamma[..., None] * (1.0 + b_dot_u)
    return (unit + s[..., None] * beta[..., None, :]) / denom[..., None]


def predicted_pair_angles_moving(star_pos_au, obs_pos_au, obs_vel_kms, pairs):
    """Angles a MOVING camera would see between star pairs, from a
    hypothesized state: geometric directions from the position, aberrated
    by the velocity, then the robust arctan2 pair-angle recipe.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    obs_vel_kms: (..., 3) hypothesized observer velocity(ies), km/s.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (..., P) predicted angles, radians.
    """
    pairs = np.asarray(pairs)
    unit, _ = _unit_directions(star_pos_au, obs_pos_au)
    sin_t, cos_t = _pair_sin_cos(_aberrate_nav(unit, obs_vel_kms), pairs)
    return np.arctan2(sin_t, cos_t)


def pair_angle_state_jacobian(star_pos_au, obs_pos_au, obs_vel_kms, pairs):
    """Sensitivity of each predicted pair angle to the SIX-number state:
    position (au) and velocity (km/s).

    Position columns chain THROUGH the aberration map (derivation D8,
    journal/spec-velocity-aberration.md): with u' = (u + s b)/D as in
    _aberrate_nav,
        du'/du = (I + k b b^T - u' (gamma b)^T) / D,
        du/dp  = -(I - u u^T) / r,
    and the velocity columns differentiate the map in b = v/c itself:
        du'/dv = [s I + b (grad_b s)^T - u' (dD/db)^T] / (D c),
        grad_b s = k u + gamma^3 ((b.u) dk/dgamma + 1) b,
        dk/dgamma = gamma (gamma + 2) / (gamma + 1)^2,
        dD/db = gamma^3 (1 + b.u) b + gamma u.
    Each pair angle then follows the tangent-plane rule through its two
    aberrated directions.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) hypothesized observer position(s), au.
    obs_vel_kms: (..., 3) hypothesized observer velocity(ies), km/s.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (..., P, 6) — columns 0-2 d(angle)/d(position) in radians
             per au, columns 3-5 d(angle)/d(velocity) in radians per
             (km/s).
    """
    pairs = np.asarray(pairs)
    unit, ranges = _unit_directions(star_pos_au, obs_pos_au)
    beta = kms_to_beta(obs_vel_kms)
    gamma = 1.0 / np.sqrt(1.0 - np.sum(beta * beta, axis=-1))
    k = gamma**2 / (gamma + 1.0)
    dk_dgamma = gamma * (gamma + 2.0) / (gamma + 1.0) ** 2
    b_dot_u = np.sum(beta[..., None, :] * unit, axis=-1)  # (..., N)
    s = k[..., None] * b_dot_u + gamma[..., None]
    denom = gamma[..., None] * (1.0 + b_dot_u)
    aberrated = (unit + s[..., None] * beta[..., None, :]) / denom[..., None]

    eye = np.eye(3)
    # du'/du, shape (..., N, 3, 3)
    b_outer_b = beta[..., :, None] * beta[..., None, :]  # (..., 3, 3)
    du_prime_du = (
        (eye + k[..., None, None] * b_outer_b)[..., None, :, :]
        - aberrated[..., :, :, None] * (gamma[..., None] * beta)[..., None, None, :]
    ) / denom[..., None, None]
    # du/dp, shape (..., N, 3, 3)
    du_dp = -(eye - unit[..., :, None] * unit[..., None, :]) / ranges[..., None, None]
    pos_block = np.einsum("...nij,...njk->...nik", du_prime_du, du_dp)

    # du'/dv, shape (..., N, 3, 3)
    grad_s = (
        k[..., None, None] * unit
        + (gamma**3)[..., None, None]
        * (b_dot_u * dk_dgamma[..., None] + 1.0)[..., :, None]
        * beta[..., None, :]
    )
    dD_db = (gamma**3)[..., None, None] * (1.0 + b_dot_u)[..., :, None] * beta[
        ..., None, :
    ] + gamma[..., None, None] * unit
    vel_block = (
        s[..., None, None] * eye
        + beta[..., None, :, None] * grad_s[..., :, None, :]
        - aberrated[..., :, :, None] * dD_db[..., :, None, :]
    ) / (denom[..., None, None] * C_KM_S)

    sin_t, cos_t = _pair_sin_cos(aberrated, pairs)
    m_i = aberrated[..., pairs[:, 0], :]
    m_j = aberrated[..., pairs[:, 1], :]
    g_i = (cos_t[..., None] * m_i - m_j) / sin_t[..., None]
    g_j = (cos_t[..., None] * m_j - m_i) / sin_t[..., None]

    pos_cols = np.einsum(
        "...pi,...pij->...pj", g_i, pos_block[..., pairs[:, 0], :, :]
    ) + np.einsum("...pi,...pij->...pj", g_j, pos_block[..., pairs[:, 1], :, :])
    vel_cols = np.einsum(
        "...pi,...pij->...pj", g_i, vel_block[..., pairs[:, 0], :, :]
    ) + np.einsum("...pi,...pij->...pj", g_j, vel_block[..., pairs[:, 1], :, :])
    return np.concatenate([pos_cols, vel_cols], axis=-1)


def per_star_floor_au(star_pos_au, sigma_dist_au, obs_pos_au):
    """Equivalent position error one star's catalog distance uncertainty
    imposes on a fix at obs_pos — the per-star catalog floor.

    A star misplaced radially by sigma_dist is indistinguishable, through
    that star, from the SPACECRAFT being displaced by the part of that
    misplacement transverse to the line of sight (displacement rule D2
    inverted): floor = sigma_dist * |u_hat - u (u . u_hat)|, computed as
    the norm of the rejection vector — NOT sqrt(1 - dot^2), which loses
    precision exactly where the floor vanishes.

    star_pos_au: (N, 3) catalog star positions, au.
    sigma_dist_au: (N,) 1-sigma catalog distance error per star, au.
    obs_pos_au: (..., 3) observer position(s), au.
    Returns: (..., N) per-star equivalent position error, au.
    """
    unit, _ = _unit_directions(star_pos_au, obs_pos_au)
    sun_u = _sun_units(star_pos_au)
    rejection = sun_u - unit * np.sum(unit * sun_u, axis=-1)[..., None]
    return np.asarray(sigma_dist_au, dtype=float) * np.linalg.norm(rejection, axis=-1)
