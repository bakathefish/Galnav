"""NAV SIDE: line-of-position triangulation navigator (Experiment E3).

Independent re-implementation of the closed-form solver Lauer et al. (2025,
AJ 170, 1) used to fix the New Horizons spacecraft's position from optical
directions to nearby stars. Like the rest of galnav/nav, it sees ONLY what a
real spacecraft would have: public catalog star positions and its own
measured directions. It imports nothing from galnav/truth.

This is a DIFFERENT navigator from the Gauss-Newton pair-angle solver in
estimator.py. Here each star's known 3D position plus the measured direction
to it defines a line the spacecraft must lie on (a "line of position"); with
two or more stars the lines intersect at the spacecraft.
"""

import numpy as np


def n_star_solve(star_pos_au, directions_unit, weighted=True):
    """Recover spacecraft position from N stars by line-of-position intersection.

    Star i sits at known position p_i and is seen from the spacecraft in
    measured unit direction d_i, so the spacecraft lies on the line through
    p_i along d_i. The maximum-likelihood position minimises the summed
    squared PERPENDICULAR distances to the N lines. With the projector onto
    the plane orthogonal to d_i, q_i = I - d_i d_i^T, and the per-star weight
    w_i = q_i / |p_i|^2 (weighted) or w_i = q_i (unweighted):

        x = (sum_i w_i)^{-1} (sum_i w_i p_i).

    The inverse-square weight down-weights distant stars, whose transverse
    position error grows with distance (Lauer et al. 2025).

    star_pos_au: (N, 3) star positions in au, in the frame/origin the answer
        is wanted (barycentric here). N >= 2.
    directions_unit: (N, 3) measured unit directions spacecraft->star
        (each row is normalised to length 1).
    weighted: True -> weight star i by 1/|p_i|^2 (matches Lauer et al.);
        False -> weight every line equally.
    Returns:
        x: (3,) spacecraft position, au (same frame/origin as star_pos_au).
        xcov: (3, 3) unscaled covariance = (sum_i w_i)^{-1}; multiply by the
            per-measurement angular variance (rad^2) for the position
            covariance in au^2 (weighted case), per Lauer et al.
        chi2: scalar weighted sum of squared perpendicular line distances at
            x (~0 for exactly consistent measurements).
    """
    p = np.asarray(star_pos_au, dtype=float)
    d = np.asarray(directions_unit, dtype=float)
    # Per-star projector onto the plane orthogonal to the measured direction.
    q = np.eye(3) - d[:, :, None] * d[:, None, :]  # (N, 3, 3)
    if weighted:
        w = q / (p**2).sum(axis=-1)[:, None, None]  # 1/|p_i|^2
    else:
        w = q
    xcov = np.linalg.inv(w.sum(axis=0))
    rhs = (w @ p[:, :, None]).sum(axis=0)  # (3, 1)
    x = (xcov @ rhs)[:, 0]
    xmp = x - p  # (N, 3)
    chi2 = float((xmp * (w @ xmp[:, :, None])[:, :, 0]).sum())
    return x, xcov, chi2
