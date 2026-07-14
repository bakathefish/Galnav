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

    Handles one trial or a whole Monte Carlo batch in a single call
    (project rule: vectorize over trials, no Python loops over trials) —
    the loop below is over Gauss-Newton ROUNDS, which are sequential by
    nature; every round advances all trials simultaneously.

    measured_rad: (..., P) measured pair angles, radians.
    star_pos_au: (N, 3) catalog star positions, au.
    pairs: (P, 2) integer star indices per measurement (P >= 3).
    initial_guess_au: (..., 3) starting position guess(es), au.
    step_tol_au: stop once every trial's correction step is below this, au.
    max_iters: hard cap on iterations (returns current best at the cap).
    Returns: (position estimate(s) (..., 3) in au, iterations used).
    """
    position = np.array(initial_guess_au, dtype=float)
    measured = np.asarray(measured_rad, dtype=float)
    for iteration in range(1, max_iters + 1):
        residual = measured - predicted_pair_angles(star_pos_au, position, pairs)
        jac = pair_angle_jacobian(star_pos_au, position, pairs)
        jtj = np.einsum("...pi,...pj->...ij", jac, jac)
        jtr = np.einsum("...pi,...p->...i", jac, residual)
        step = np.linalg.solve(jtj, jtr[..., None])[..., 0]
        position = position + step
        if np.all(np.linalg.norm(step, axis=-1) < step_tol_au):
            return position, iteration
    return position, max_iters


def position_covariance(star_pos_au, obs_pos_au, pairs, sigma_rad):
    """Predicted error-bar matrix of the solved position (derivation D4).

    Cov = sigma^2 (J^T J)^-1 — how scattered the solved positions will be
    around the truth when each angle measurement carries Gaussian noise
    sigma. For Gaussian noise this is also the Cramer-Rao lower bound
    (derivation D6): no unbiased navigator can do better.

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) position(s) where the sensitivity is evaluated, au.
    pairs: (P, 2) integer star indices per measurement (P >= 3).
    sigma_rad: per-measurement Gaussian noise, radians.
    Returns: (..., 3, 3) covariance of the position estimate, au^2.
    """
    jac = pair_angle_jacobian(star_pos_au, obs_pos_au, pairs)
    jtj = np.einsum("...pi,...pj->...ij", jac, jac)
    return sigma_rad**2 * np.linalg.inv(jtj)
