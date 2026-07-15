"""NAV SIDE: the Gauss-Newton position solver. Inverts the measurement
model: given measured star-pair angles, the public catalog, and a starting
guess, find the position whose predicted angles best match the
measurements. Sees ONLY what a real spacecraft would have."""

import numpy as np

from galnav.nav.measmodel import (
    catalog_angle_covariance,
    pair_angle_jacobian,
    pair_angle_state_jacobian,
    predicted_pair_angles,
    predicted_pair_angles_moving,
)
from galnav.units import C_KM_S


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


def _inside_light_cone(vel_kms):
    """Pull any at-or-beyond-light-speed velocity back inside the cone.

    A hypothesized speed >= c has no Lorentz factor, so candidate states
    must stay sub-luminal to be evaluable. Domain guard (like the arccos
    clip), not an accepted-answer tolerance: 0.99 c is only a re-entry
    point for the next Gauss-Newton round; it never touches convergent
    trials.

    vel_kms: (..., 3) velocity(ies), km/s.
    Returns: (..., 3) velocity(ies), km/s, every speed strictly below c.
    """
    speed = np.linalg.norm(vel_kms, axis=-1)
    outside = speed >= C_KM_S
    if not np.any(outside):
        return vel_kms
    scale = np.where(outside, 0.99 * C_KM_S / np.where(outside, speed, 1.0), 1.0)
    return vel_kms * scale[..., None]


def solve_state(
    measured_rad,
    star_pos_au,
    pairs,
    initial_pos_au,
    initial_vel_kms,
    step_tol_au,
    step_tol_kms,
    max_iters,
):
    """Recover the spacecraft's SIX-number state — position AND velocity —
    from one snapshot of measured star-pair angles.

    Same Gauss-Newton recipe as solve_position (derivation D3), on the
    stacked 6-vector [position (au), velocity (km/s)]: aberration couples
    velocity into every predicted angle, so one snapshot determines both.
    The epoch is NOT an unknown (with a static catalog its sensitivity is
    identically zero; [BJ21] Sec. 4.1 shows fixing it costs nothing).
    Stops only when EVERY trial's position step is below step_tol_au AND
    its velocity step is below step_tol_kms — a unit-honest dual rule.

    Step control (measured necessary at ~1 in 10^4 anchor trials — the
    plan's "GN with LM damping" core, in its minimal form): each round
    proposes the full Gauss-Newton step, then HALVES it, per trial, until
    that trial's residual sum-of-squares does not increase; after 8
    halvings (a 256x shorter step still going uphill) the step is
    REJECTED outright — the solver never moves uphill. A NaN residual
    counts as "worse", so diverging or non-evaluable states are
    automatically rejected too. A trial whose full step descends takes it
    unchanged, so away from the rounding floor the damping never
    activates; at the floor (final polish, where residual changes are
    rounding dust) it can clip the last step, shifting results only in
    the last ulps.

    Light-cone guard: a proposed velocity at or beyond c has no Lorentz
    factor, so before each trial evaluation the velocity is pulled back
    inside the light cone (to 0.99 c — a domain guard like the arccos
    clip, not an accepted-answer tolerance), keeping every candidate
    state evaluable.

    measured_rad: (..., P) measured pair angles, radians.
    star_pos_au: (N, 3) catalog star positions, au.
    pairs: (P, 2) integer star indices per measurement (P >= 6).
    initial_pos_au: (..., 3) starting position guess(es), au.
    initial_vel_kms: (..., 3) starting velocity guess(es), km/s.
    step_tol_au: position half of the stopping rule, au.
    step_tol_kms: velocity half of the stopping rule, km/s.
    max_iters: hard cap on iterations (returns current best at the cap).
    Returns: (position (..., 3) au, velocity (..., 3) km/s, iterations).
    """
    position = np.array(initial_pos_au, dtype=float)
    velocity = np.array(initial_vel_kms, dtype=float)
    measured = np.asarray(measured_rad, dtype=float)
    for iteration in range(1, max_iters + 1):
        residual = measured - predicted_pair_angles_moving(
            star_pos_au, position, velocity, pairs
        )
        res_norm = np.sum(residual**2, axis=-1)
        jac = pair_angle_state_jacobian(star_pos_au, position, velocity, pairs)
        jtj = np.einsum("...pi,...pj->...ij", jac, jac)
        jtr = np.einsum("...pi,...p->...i", jac, residual)
        step = np.linalg.solve(jtj, jtr[..., None])[..., 0]
        scale = np.ones(res_norm.shape)
        for _ in range(8):  # halving passes, vectorized across all trials
            trial_pos = position + scale[..., None] * step[..., :3]
            trial_vel = _inside_light_cone(velocity + scale[..., None] * step[..., 3:])
            trial_res = measured - predicted_pair_angles_moving(
                star_pos_au, trial_pos, trial_vel, pairs
            )
            worse = ~(np.sum(trial_res**2, axis=-1) <= res_norm)  # NaN = worse
            if not np.any(worse):
                break
            scale = np.where(worse, scale / 2.0, scale)
        if np.any(worse):  # exhausted: an uphill step is never accepted
            scale = np.where(worse, 0.0, scale)
            trial_pos = position + scale[..., None] * step[..., :3]
            trial_vel = _inside_light_cone(velocity + scale[..., None] * step[..., 3:])
        position, velocity = trial_pos, trial_vel
        taken = scale[..., None] * step
        if np.all(np.linalg.norm(taken[..., :3], axis=-1) < step_tol_au) and np.all(
            np.linalg.norm(taken[..., 3:], axis=-1) < step_tol_kms
        ):
            return position, velocity, iteration
    return position, velocity, max_iters


def position_covariance(star_pos_au, obs_pos_au, pairs, sigma_rad, sigma_dist_au=None):
    """Predicted error-bar matrix of the solved position (derivation D4).

    Without sigma_dist_au: Cov = sigma^2 (J^T J)^-1 — how scattered the
    solved positions will be around the truth when each angle measurement
    carries Gaussian noise sigma. For Gaussian noise this is also the
    Cramer-Rao lower bound (derivation D6): no unbiased navigator can do
    better.

    With sigma_dist_au (Spec 7): the error budget grows a catalog term,
    R = sigma^2 I + R_cat (R_cat dense — pairs sharing a star carry the
    SAME distance error), and Cov = (J^T R^-1 J)^-1 — derivation D4 with
    W = R^-1: the best ANY navigator could achieve given both camera
    noise and the catalog's own error bars. With a perfect camera
    (sigma = 0) this no longer vanishes: the catalog floor. R must be
    invertible (true for real per-star sigmas; all-zero sigma_dist_au
    with sigma = 0 has no error budget to invert).

    star_pos_au: (N, 3) catalog star positions, au.
    obs_pos_au: (..., 3) position(s) where the sensitivity is evaluated, au.
    pairs: (P, 2) integer star indices per measurement (P >= 3).
    sigma_rad: per-measurement Gaussian noise, radians.
    sigma_dist_au: optional (N,) 1-sigma catalog distance error per star, au.
    Returns: (..., 3, 3) covariance of the position estimate, au^2.
    """
    jac = pair_angle_jacobian(star_pos_au, obs_pos_au, pairs)
    if sigma_dist_au is None:
        jtj = np.einsum("...pi,...pj->...ij", jac, jac)
        return sigma_rad**2 * np.linalg.inv(jtj)
    r_total = catalog_angle_covariance(
        star_pos_au, obs_pos_au, pairs, sigma_dist_au
    ) + sigma_rad**2 * np.eye(len(pairs))
    jtwj = np.einsum("...pi,...pj->...ij", jac, np.linalg.solve(r_total, jac))
    return np.linalg.inv(jtwj)
