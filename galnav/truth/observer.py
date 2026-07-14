"""TRUTH SIDE: generates the noisy measurements a spacecraft camera would
record. Experiment scripts hand these to the navigator — this module and
the navigator never touch each other directly."""

import numpy as np


def observed_pair_angles(star_pos_au, obs_pos_au, pairs, sigma_rad, rng):
    """Measured angles between pairs of stars, as seen from the spacecraft.

    star_pos_au: (N, 3) true star positions, au.
    obs_pos_au: (3,) true spacecraft position, au.
    pairs: (P, 2) integer star indices — which two stars each measurement
           compares.
    sigma_rad: Gaussian measurement noise per angle, radians (0 = perfect
               camera).
    rng: np.random.Generator — all randomness comes through here.
    Returns: (P,) measured angles in radians.
    """
    pairs = np.asarray(pairs)
    towards = star_pos_au - np.asarray(obs_pos_au, dtype=float)
    unit = towards / np.linalg.norm(towards, axis=1)[:, None]
    cos_angles = np.sum(unit[pairs[:, 0]] * unit[pairs[:, 1]], axis=1)
    true_angles = np.arccos(np.clip(cos_angles, -1.0, 1.0))
    return true_angles + sigma_rad * rng.standard_normal(len(pairs))
