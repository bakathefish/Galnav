"""NAV SIDE: the Gauss-Newton position solver. Inverts the measurement
model: given measured star-pair angles, the public catalog, and a starting
guess, find the position whose predicted angles best match the
measurements. Sees ONLY what a real spacecraft would have."""

import numpy as np

from galnav.nav.measmodel import pair_angle_jacobian, predicted_pair_angles


def solve_position(
    measured_rad, star_pos_au, pairs, initial_guess_au, step_tol_au, max_iters
):
    """Recover the spacecraft position from measured star-pair angles.

    Gauss-Newton iteration (derivation D3, journal/spec-5-estimator.md):
    residual r = measured - predicted(p), then the best linear correction
    solves the normal equations (J^T J) delta = J^T r; apply and repeat
    until the correction is below step_tol_au.

    measured_rad: (P,) measured pair angles, radians.
    star_pos_au: (N, 3) catalog star positions, au.
    pairs: (P, 2) integer star indices per measurement (P >= 3).
    initial_guess_au: (3,) starting position guess, au.
    step_tol_au: stop once the correction step is smaller than this, au.
    max_iters: hard cap on iterations (returns current best at the cap).
    Returns: (position estimate (3,) in au, iterations used).
    """
    position = np.array(initial_guess_au, dtype=float)
    for iteration in range(1, max_iters + 1):
        residual = np.asarray(measured_rad, dtype=float) - predicted_pair_angles(
            star_pos_au, position, pairs
        )
        jac = pair_angle_jacobian(star_pos_au, position, pairs)
        step = np.linalg.solve(jac.T @ jac, jac.T @ residual)
        position = position + step
        if np.linalg.norm(step) < step_tol_au:
            return position, iteration
    return position, max_iters
