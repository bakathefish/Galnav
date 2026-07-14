"""Spec 6 acceptance test: error bars — covariance and the CRLB.

One noisy measurement gives one slightly-wrong position; many noisy
measurements give a CLOUD of positions. Derivation D4 predicts the cloud's
exact size and shape: Cov = sigma^2 (J^T J)^-1 — which for Gaussian noise
is also the Cramer-Rao lower bound (D6): the best ANY unbiased navigator
could ever do. These tests check (1) the formula is a valid covariance,
(2) the batched solver (vectorized over trials, per the project rule: no
Python loops over trials) agrees exactly with the single-trial solver,
and (3) a 500-trial Monte Carlo cloud matches the formula within the
statistics-honest 15% gate.
"""

from pathlib import Path

import numpy as np

from galnav.nav.estimator import position_covariance, solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from tests.golden_numbers import (
    MC_CRLB_REL_TOL,
    MC_TRIALS,
    RAD_ARCSEC,
    SOLVER_MAX_ITERS,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_STEP_TOL_AU,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

TRUE_POS_AU = np.array([1.0e5, -2.0e5, 3.0e5])
PAIRS = np.array([[0, 1], [2, 3], [4, 5], [6, 7], [8, 3], [0, 9], [3, 7]])
SIGMA_RAD = 1.0 / RAD_ARCSEC  # 1 arcsec camera noise (setup value)
START_OFFSET_AU = np.array([500.0, -500.0, 500.0])


def _stars():
    return star_positions_au(load_catalog(CATALOG_CSV))[:10]


def test_covariance_is_symmetric_positive_definite():
    # A covariance matrix that isn't symmetric or has non-positive
    # eigenvalues is not a covariance at all -- catches transposition and
    # sign mistakes in the formula before any statistics run.
    cov = position_covariance(_stars(), TRUE_POS_AU, PAIRS, SIGMA_RAD)
    assert cov.shape == (3, 3)
    assert np.allclose(cov, cov.T)
    assert np.all(np.linalg.eigvalsh(cov) > 0)


def test_batched_solver_equals_single_trial_solver():
    # The vectorized solver (many trials at once) must give the SAME
    # answers as the proven single-trial solver -- otherwise the Monte
    # Carlo below tests different code than the navigation actually uses.
    stars = _stars()
    rng = np.random.default_rng(7)
    measured = observed_pair_angles(
        stars, np.broadcast_to(TRUE_POS_AU, (3, 3)), PAIRS, SIGMA_RAD, rng
    )  # 3 noisy trials, shape (3, P)
    starts = np.broadcast_to(TRUE_POS_AU + START_OFFSET_AU, (3, 3))
    batch, _ = solve_position(
        measured, stars, PAIRS, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )
    for t in range(3):  # tiny cross-check loop, test style
        single, _ = solve_position(
            measured[t],
            stars,
            PAIRS,
            TRUE_POS_AU + START_OFFSET_AU,
            SOLVER_STEP_TOL_AU,
            SOLVER_MAX_ITERS,
        )
        assert np.linalg.norm(batch[t] - single) < SOLVER_RECOVERY_TOL_AU


def test_monte_carlo_scatter_matches_theory():
    # THE D4 checkpoint: solve MC_TRIALS noisy universes in one vectorized
    # call, and the per-axis scatter of the solutions must match
    # sigma^2 (J^T J)^-1 within the statistics-honest 15% gate.
    stars = _stars()
    rng = np.random.default_rng(0)
    measured = observed_pair_angles(
        stars, np.broadcast_to(TRUE_POS_AU, (MC_TRIALS, 3)), PAIRS, SIGMA_RAD, rng
    )  # (MC_TRIALS, P) -- noise generated truth-side, all trials at once
    starts = np.broadcast_to(TRUE_POS_AU + START_OFFSET_AU, (MC_TRIALS, 3))
    solved, _ = solve_position(
        measured, stars, PAIRS, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )
    assert solved.shape == (MC_TRIALS, 3)

    empirical_std = solved.std(axis=0, ddof=1)
    theory_std = np.sqrt(
        np.diag(position_covariance(stars, TRUE_POS_AU, PAIRS, SIGMA_RAD))
    )
    assert np.all(np.abs(empirical_std - theory_std) / theory_std < MC_CRLB_REL_TOL)
