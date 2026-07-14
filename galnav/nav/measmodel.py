"""NAV SIDE: Measurement Model A — predicted star-pair angles for a
hypothesized spacecraft position, and their sensitivity (Jacobian) to that
position. Uses ONLY public catalog values handed in by the caller; never
touches galnav/truth/."""

import numpy as np


def _unit_directions(star_pos_au, obs_pos_au):
    """Unit direction vectors from a hypothesized observer to each star.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (3,) hypothesized observer position, au.
    Returns: (unit (N, 3) dimensionless, range (N,) in au).
    """
    towards = np.asarray(star_pos_au, dtype=float) - np.asarray(obs_pos_au, dtype=float)
    ranges = np.linalg.norm(towards, axis=1)
    return towards / ranges[:, None], ranges


def _pair_sin_cos(unit, pairs):
    """sin and cos of each pair angle, precise at ALL angles.

    sin comes from the cross product's length and cos from the dot
    product; arctan2(sin, cos) then never suffers arccos's precision
    collapse near 0 and pi (needed: the real sky contains close binary
    pairs with nearly-zero separation angles).

    unit: (N, 3) unit direction vectors (dimensionless).
    pairs: (P, 2) integer star indices.
    Returns: (sin (P,), cos (P,)), both dimensionless.
    """
    u_i, u_j = unit[pairs[:, 0]], unit[pairs[:, 1]]
    sin_t = np.linalg.norm(np.cross(u_i, u_j), axis=1)
    cos_t = np.sum(u_i * u_j, axis=1)
    return sin_t, cos_t


def predicted_pair_angles(star_pos_au, obs_pos_au, pairs):
    """Angles the camera WOULD see between star pairs from a guessed position.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (3,) hypothesized observer position, au.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (P,) predicted angles, radians.
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
    obs_pos_au: (3,) hypothesized observer position, au.
    pairs: (P, 2) integer star indices per measured pair.
    Returns: (P, 3) d(angle)/d(position), radians per au.
    """
    pairs = np.asarray(pairs)
    unit, ranges = _unit_directions(star_pos_au, obs_pos_au)
    u_i, u_j = unit[pairs[:, 0]], unit[pairs[:, 1]]
    r_i, r_j = ranges[pairs[:, 0]], ranges[pairs[:, 1]]
    sin_t, cos_t = _pair_sin_cos(unit, pairs)
    dcos_dp = (cos_t[:, None] * u_i - u_j) / r_i[:, None] + (
        cos_t[:, None] * u_j - u_i
    ) / r_j[:, None]
    return -dcos_dp / sin_t[:, None]
