"""Geometry primitives shared by the whole project."""

import numpy as np


def angle_between(v1, v2):
    """Angle between two direction vectors.

    v1, v2: 3-component direction vectors (any length units -- only
            direction matters, magnitude cancels out).
    Returns: angle in radians, in [0, pi].
    """
    v1 = np.asarray(v1, dtype=float)
    v2 = np.asarray(v2, dtype=float)
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return np.arccos(np.clip(cos_angle, -1.0, 1.0))
