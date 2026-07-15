"""TRUTH SIDE: generates the noisy measurements a spacecraft camera would
record. Experiment scripts hand these to the navigator — this module and
the navigator never touch each other directly."""

import numpy as np

from galnav.units import C_KM_S


def _aberrate(unit, vel_kms):
    """Directions seen by a MOVING camera: exact special-relativistic
    aberration of each unit direction (truth's own implementation —
    deliberately written independently of the navigator's; the
    zero-noise recovery test cross-checks the two through inversion).

    Klioner (2003) Eq. 10 form, arranged to stay finite at v = 0 by
    replacing (gamma - 1)/|v|^2 with gamma^2 / ((gamma + 1) c^2):

        s_hat = (s_hat' + [gamma/c + (gamma^2/((gamma+1) c^2))(v . s_hat')] v)
                / (gamma (1 + v . s_hat' / c))

    unit: (..., N, 3) rest-frame unit directions toward the stars,
          dimensionless.
    vel_kms: (..., 3) true spacecraft velocity, km/s.
    Returns: (..., N, 3) unit directions in the spacecraft frame,
             dimensionless (stars slide TOWARD the direction of motion).
    """
    vel = np.asarray(vel_kms, dtype=float)
    speed_sq = np.sum(vel * vel, axis=-1)  # (km/s)^2
    gamma = 1.0 / np.sqrt(1.0 - speed_sq / C_KM_S**2)
    v_dot_u = np.sum(vel[..., None, :] * unit, axis=-1)  # (..., N), km/s
    coeff = (
        gamma[..., None] / C_KM_S
        + (gamma[..., None] ** 2 / ((gamma[..., None] + 1.0) * C_KM_S**2)) * v_dot_u
    )
    numerator = unit + coeff[..., None] * vel[..., None, :]
    denominator = gamma[..., None] * (1.0 + v_dot_u / C_KM_S)
    return numerator / denominator[..., None]


def observed_pair_angles_moving(
    star_pos_au, obs_pos_au, obs_vel_kms, pairs, sigma_rad, rng
):
    """Measured pair angles from a spacecraft that is MOVING: the true
    geometric directions are aberrated by the true velocity, then the
    angles between them are read off and camera noise is added.

    star_pos_au: (N, 3) true star positions, au.
    obs_pos_au: (..., 3) true spacecraft position(s), au.
    obs_vel_kms: (..., 3) true spacecraft velocity(ies), km/s.
    pairs: (P, 2) integer star indices per measurement.
    sigma_rad: Gaussian measurement noise per angle, radians.
    rng: np.random.Generator — all randomness comes through here.
    Returns: (..., P) measured angles in radians.
    """
    pairs = np.asarray(pairs)
    obs = np.asarray(obs_pos_au, dtype=float)
    towards = np.asarray(star_pos_au, dtype=float) - obs[..., None, :]
    unit = _aberrate(towards / np.linalg.norm(towards, axis=-1)[..., None], obs_vel_kms)
    cos_angles = np.sum(unit[..., pairs[:, 0], :] * unit[..., pairs[:, 1], :], axis=-1)
    true_angles = np.arccos(np.clip(cos_angles, -1.0, 1.0))
    return true_angles + sigma_rad * rng.standard_normal(true_angles.shape)


def observed_pair_angles(star_pos_au, obs_pos_au, pairs, sigma_rad, rng):
    """Measured angles between pairs of stars, as seen from the spacecraft.

    star_pos_au: (N, 3) true star positions, au.
    obs_pos_au: (..., 3) true spacecraft position(s), au — a single (3,)
                position, or (T, 3) to generate T independent noisy
                measurement sets at once (vectorized Monte Carlo; the
                project rule forbids Python loops over trials).
    pairs: (P, 2) integer star indices — which two stars each measurement
           compares.
    sigma_rad: Gaussian measurement noise per angle, radians (0 = perfect
               camera).
    rng: np.random.Generator — all randomness comes through here.
    Returns: (..., P) measured angles in radians.
    """
    pairs = np.asarray(pairs)
    obs = np.asarray(obs_pos_au, dtype=float)
    towards = np.asarray(star_pos_au, dtype=float) - obs[..., None, :]
    unit = towards / np.linalg.norm(towards, axis=-1)[..., None]
    cos_angles = np.sum(unit[..., pairs[:, 0], :] * unit[..., pairs[:, 1], :], axis=-1)
    true_angles = np.arccos(np.clip(cos_angles, -1.0, 1.0))
    return true_angles + sigma_rad * rng.standard_normal(true_angles.shape)
