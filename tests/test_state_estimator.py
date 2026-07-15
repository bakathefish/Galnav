"""Velocity+aberration card acceptance tests (state = position + velocity).

A moving camera sees a tilted sky: special-relativistic aberration slides
every star toward the direction of motion (the apex), and HOW MUCH it
slides encodes the velocity — about 0.7 arcsec per km/s of sideways
speed, for every star at once. That makes velocity observable from ONE
snapshot of pair angles, and the navigator's state grows to six numbers:
barycentric position (au) and velocity (km/s). The epoch is NOT solved
for: with a static catalog its sensitivity column is identically zero (a
7-state solve would be singular); Bailer-Jones's own control (Sec. 4.1)
shows fixing it leaves the other parameters unaffected.

THE TRAP these tests exist to prevent (measured, logbook 2026-07-15): an
implementation using the WRONG aberration formula (Galilean, no gamma)
on BOTH sides of the truth wall cancels its own error and passes
recovery AND the anchor. Only comparing against an EXTERNAL trusted
oracle — the golden SR_ABER_PHI_RAD, at oblique angles where every
wrong variant shows — catches it. Test 1 is therefore the keystone.
"""

from pathlib import Path

import numpy as np

from galnav.nav.estimator import solve_state
from galnav.nav.measmodel import (
    pair_angle_state_jacobian,
    predicted_pair_angles_moving,
)
from galnav.truth.observer import observed_pair_angles_moving
from galnav.units import C_KM_S, deg_to_rad, parallax_mas_to_dist_au, radec_to_unit
from tests.golden_numbers import (
    ANGLE_TOL_RAD,
    BAILER_JONES_ANCHOR,
    JACOBIAN_REL_TOL,
    RAD_ARCSEC,
    SOLVER_MAX_ITERS,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_RECOVERY_TOL_KMS,
    SOLVER_STEP_TOL_AU,
    SOLVER_STEP_TOL_KMS,
    SR_ABER_PHI_RAD,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

# Bailer-Jones network: the Sun (origin, row 0) as the hub reference star
# plus the 19 nearest bright stars; measurements are the 19 hub angles.
PAIRS_HUB = np.column_stack([np.zeros(19, dtype=int), np.arange(1, 20)])

TRUE_POS_AU = np.array([3.0e5, 1.0e5, 1.0e5])  # 1.61 pc from the barycenter
VEL_DIR = np.array([0.6, -0.64, 0.48]) / np.linalg.norm([0.6, -0.64, 0.48])


def _anchor_stars():
    """Sun + the 19 nearest phot_g_mean_mag < 10 stars, positions in au."""
    raw = np.genfromtxt(CATALOG_CSV, delimiter=",", names=True)
    bright = raw[raw["phot_g_mean_mag"] < 10.0][:19]  # nearest-first order
    unit = radec_to_unit(deg_to_rad(bright["ra"]), deg_to_rad(bright["dec"]))
    stars = unit * parallax_mas_to_dist_au(bright["parallax"])[:, None]
    return np.vstack([np.zeros(3), stars])


def test_aberration_matches_special_relativity_oracle():
    # The keystone: the code's aberrated hub angles must equal the golden
    # SR oracle. Observer at the origin, v = 0.1c along +x, stars placed
    # by pure direction. Three configurations, each killing a bug class:
    # A (probe at 90 deg): the plain gamma test — a Galilean formula
    #   misses by 102.88 arcsec, ~5e8x the gate;
    # A-oblique (probe at 150 deg): kills a wrong k coefficient, which
    #   is invisible at 90 deg (its term multiplies b.u = 0 there) but
    #   shows off-axis — measured: k = gamma/(gamma+1) errs 2.68 arcsec
    #   at 150 deg, ~1.3e7x the gate (kill-matrix run, 2026-07-15);
    # B (reference at 60 deg, probe at 120 deg, coplanar with the apex):
    #   kills "aberrate the pair angle instead of each direction" —
    #   exact when the reference sits dead ahead, 0.08 rad wrong here.
    # Plus the strict toward-apex inequality that kills a sign-flipped
    # beta (self-consistent everywhere else, including the anchor).
    beta = 0.1
    vel = np.array([beta * C_KM_S, 0.0, 0.0])
    d = 1.0e9  # au; aberration acts on directions, distance is irrelevant
    stars = d * np.array(
        [
            [1.0, 0.0, 0.0],  # 0: dead ahead (the apex)
            [0.0, 1.0, 0.0],  # 1: 90 deg from the apex
            [np.cos(5 * np.pi / 6), np.sin(5 * np.pi / 6), 0.0],  # 2: 150 deg
            [np.cos(np.pi / 3), np.sin(np.pi / 3), 0.0],  # 3: 60 deg
            [np.cos(2 * np.pi / 3), np.sin(2 * np.pi / 3), 0.0],  # 4: 120 deg
        ]
    )
    pairs = np.array([[0, 1], [0, 2], [3, 4]])
    angles = predicted_pair_angles_moving(stars, np.zeros(3), vel, pairs)

    phi_90 = SR_ABER_PHI_RAD(beta, np.pi / 2)
    phi_150 = SR_ABER_PHI_RAD(beta, 5 * np.pi / 6)
    phi_60 = SR_ABER_PHI_RAD(beta, np.pi / 3)
    phi_120 = SR_ABER_PHI_RAD(beta, 2 * np.pi / 3)

    assert abs(angles[0] - phi_90) < ANGLE_TOL_RAD  # config A
    assert abs(angles[1] - phi_150) < ANGLE_TOL_RAD  # config A-oblique
    assert abs(angles[2] - (phi_120 - phi_60)) < ANGLE_TOL_RAD  # config B
    assert angles[0] < np.pi / 2  # strictly TOWARD the apex (sign kill)


def test_state_jacobian_matches_finite_differences_over_decades():
    # Both Jacobian blocks — d(angle)/d(position) chained THROUGH the
    # aberration map (rad/au) and d(angle)/d(velocity) (rad per km/s) —
    # against central finite differences, at a slow leg (400 km/s) and a
    # relativistic leg (0.3c) where the gamma-gradient terms matter.
    # Catches: reusing the static Spec 4 position block (144% wrong at
    # 0.3c), a dropped gamma^3 term, wrong 1/r, wrong star.
    stars = _anchor_stars()
    for speed_kms in (400.0, 0.3 * C_KM_S):
        vel = speed_kms * VEL_DIR
        jac = pair_angle_state_jacobian(stars, TRUE_POS_AU, vel, PAIRS_HUB)
        assert jac.shape == (19, 6)
        fd = np.zeros_like(jac)
        # Position decades sit one notch below Spec 4's (0.01-10 au, not
        # 0.1-100 au): this network's nearest hub star is ~0.3 pc from
        # the craft, and central differences carry an h^2 truncation term
        # measured at 1.37e-6 for h = 100 au here — pure step-size error,
        # scaling exactly as h^2 (2.6e-8 at h = 10 au). Four decades and
        # the JACOBIAN_REL_TOL gate are unchanged.
        for axis in range(3):  # loop over axes/decades, test style
            for h_au in (0.01, 0.1, 1.0, 10.0):
                dp = np.zeros(3)
                dp[axis] = h_au
                col = (
                    predicted_pair_angles_moving(
                        stars, TRUE_POS_AU + dp, vel, PAIRS_HUB
                    )
                    - predicted_pair_angles_moving(
                        stars, TRUE_POS_AU - dp, vel, PAIRS_HUB
                    )
                ) / (2.0 * h_au)
                fd[:, axis] = col
                rel = np.abs(fd[:, axis] - jac[:, axis]) / np.abs(jac[:, axis])
                assert np.all(rel < JACOBIAN_REL_TOL), (
                    f"pos axis {axis}, h={h_au} au, v={speed_kms}: {rel.max()}"
                )
            for h_kms in (0.01, 0.1, 1.0, 10.0):
                dv = np.zeros(3)
                dv[axis] = h_kms
                col = (
                    predicted_pair_angles_moving(
                        stars, TRUE_POS_AU, vel + dv, PAIRS_HUB
                    )
                    - predicted_pair_angles_moving(
                        stars, TRUE_POS_AU, vel - dv, PAIRS_HUB
                    )
                ) / (2.0 * h_kms)
                fd[:, 3 + axis] = col
                rel = np.abs(fd[:, 3 + axis] - jac[:, 3 + axis]) / np.abs(
                    jac[:, 3 + axis]
                )
                assert np.all(rel < JACOBIAN_REL_TOL), (
                    f"vel axis {axis}, h={h_kms} km/s, v={speed_kms}: {rel.max()}"
                )


def test_noiseless_state_recovery_to_machine_precision():
    # With a perfect camera the 6-state solver has no excuse, from EVERY
    # corner of Bailer-Jones's 10% initialization box (2^6 = 64 corner
    # starts, one batched call). This test also cross-checks the two
    # INDEPENDENTLY WRITTEN aberration implementations (truth's arccos
    # path vs nav's arctan2/Jacobian path) through a full inversion.
    # The iteration cap is load-bearing: a stale static position block
    # can still creep to the answer, but not in under SOLVER_MAX_ITERS.
    stars = _anchor_stars()
    vel_true = 0.3 * C_KM_S * VEL_DIR
    rng = np.random.default_rng(0)
    measured = observed_pair_angles_moving(
        stars, TRUE_POS_AU, vel_true, PAIRS_HUB, 0.0, rng
    )
    corners = (
        np.array(np.meshgrid(*([[0.9, 1.1]] * 6), indexing="ij")).reshape(6, -1).T
    )  # (64, 6) corner factors
    pos0 = corners[:, :3] * TRUE_POS_AU
    vel0 = corners[:, 3:] * vel_true
    pos, vel, iterations = solve_state(
        np.broadcast_to(measured, (64, 19)),
        stars,
        PAIRS_HUB,
        pos0,
        vel0,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )
    assert np.all(np.linalg.norm(pos - TRUE_POS_AU, axis=-1) < SOLVER_RECOVERY_TOL_AU)
    assert np.all(np.linalg.norm(vel - vel_true, axis=-1) < SOLVER_RECOVERY_TOL_KMS)
    assert iterations < SOLVER_MAX_ITERS

    _, _, iters_exact = solve_state(
        measured,
        stars,
        PAIRS_HUB,
        TRUE_POS_AU,
        vel_true,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )
    assert iters_exact <= 1  # starting on the answer must cost nothing


def test_batched_state_solver_equals_single_trial():
    # One deliberately heterogeneous batch — a static trial (v = 0, the
    # exact reduction INSIDE a batch), 0.2c along x, 0.4c along z, three
    # different positions — must give the same answers as three single
    # solves. Kills trial-axis broadcasting bugs in the batched gamma/k
    # scalars against the (T, N, 3, 3) Jacobian tensors.
    stars = _anchor_stars()
    pos_true = np.array(
        [[3.0e5, 1.0e5, 1.0e5], [-2.0e5, 2.0e5, 1.0e5], [1.0e5, -1.0e5, 4.0e5]]
    )
    vel_true = np.array(
        [[0.0, 0.0, 0.0], [0.2 * C_KM_S, 0.0, 0.0], [0.0, 0.0, 0.4 * C_KM_S]]
    )
    rng = np.random.default_rng(7)
    measured = observed_pair_angles_moving(
        stars, pos_true, vel_true, PAIRS_HUB, 1.0 / RAD_ARCSEC, rng
    )
    pos0, vel0 = 1.1 * pos_true, 1.1 * vel_true  # v=0 row starts at v=0 too
    batch_pos, batch_vel, _ = solve_state(
        measured,
        stars,
        PAIRS_HUB,
        pos0,
        vel0,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )
    for t in range(3):  # tiny cross-check loop, test style
        single_pos, single_vel, _ = solve_state(
            measured[t],
            stars,
            PAIRS_HUB,
            pos0[t],
            vel0[t],
            SOLVER_STEP_TOL_AU,
            SOLVER_STEP_TOL_KMS,
            SOLVER_MAX_ITERS,
        )
        assert np.linalg.norm(batch_pos[t] - single_pos) < SOLVER_RECOVERY_TOL_AU
        assert np.linalg.norm(batch_vel[t] - single_vel) < SOLVER_RECOVERY_TOL_KMS
        assert np.all(np.isfinite(batch_pos[t])) and np.all(np.isfinite(batch_vel[t]))


def test_solver_survives_superluminal_overshoot():
    # Regression, pinned to a real failure (found by the 200-seed
    # verification ensemble, 2026-07-15: anchor protocol seed 10067,
    # trial 72 — spacecraft only 0.18 ly out at 0.496c, the nastiest
    # corner of the 10% start box). Undamped Gauss-Newton crossed the
    # speed of light on round 2 (no Lorentz factor -> NaN) and then
    # diverged through position; the damped solver must CONVERGE it.
    # Fully deterministic: the exact inputs are frozen below, no rng.
    stars = _anchor_stars()
    p_true = np.array([-4231.499826312869, -4615.185375158721, -9587.149577850974])
    v_true = np.array([-54954.42163160356, -59937.3398144458, -124508.16064561921])
    start_pos = np.array([-4038.9200513239975, -4245.419190030151, -9961.223841302384])
    start_vel = np.array(
        [-56291.047838475526, -63118.087008829934, -129513.71294328326]
    )
    measured = np.array(
        [
            3.0599099207426366,
            2.3432123095976514,
            1.8018982713653857,
            2.5883606428791976,
            2.3042337231593684,
            2.353006464415811,
            1.5244942567866606,
            1.5244312370090176,
            1.471054997311019,
            1.471106633801146,
            0.8411263918164635,
            0.8408922730367266,
            2.5951542334001125,
            1.7764732289278495,
            2.293612785753953,
            2.4961843514375452,
            2.6433937938089955,
            1.3851258984778805,
            2.900645070074014,
        ]
    )
    pos, vel, iterations = solve_state(
        measured,
        stars,
        PAIRS_HUB,
        start_pos,
        start_vel,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )
    assert np.all(np.isfinite(pos)) and np.all(np.isfinite(vel))
    assert np.linalg.norm(vel) < C_KM_S  # strictly inside the light cone
    assert iterations < SOLVER_MAX_ITERS  # genuinely converged (6 rounds)
    # Single-trial accuracy inside the anchor's own tolerance band
    # (deterministic: measured 1.85 au / 1.95 km/s on this exact input).
    assert np.linalg.norm(pos - p_true) < (
        BAILER_JONES_ANCHOR["pos_err_au"] * BAILER_JONES_ANCHOR["tol_factor"]
    )
    assert np.linalg.norm(vel - v_true) < (
        BAILER_JONES_ANCHOR["vel_err_kms"] * BAILER_JONES_ANCHOR["tol_factor"]
    )
