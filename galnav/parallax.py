"""Parallax / displacement engine: how a star's apparent direction shifts
when the observer moves."""

import numpy as np


def parallax_angle(baseline_au, distance_au):
    """Apparent angular shift of a star when the observer slides sideways.

    baseline_au: distance moved perpendicular to the line of sight, in au.
    distance_au: observer-to-star distance, in au (scalar or numpy array).
    Returns: exact angular shift in radians, same shape as distance_au.
    """
    return np.arctan(
        np.asarray(baseline_au, dtype=float) / np.asarray(distance_au, dtype=float)
    )
