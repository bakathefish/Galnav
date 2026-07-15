"""NAV SIDE: Measurement Model A — predicted star-pair angles for a
hypothesized spacecraft position, and their sensitivity (Jacobian) to that
position. Uses ONLY public catalog values handed in by the caller; never
touches galnav/truth/."""

import numpy as np


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
