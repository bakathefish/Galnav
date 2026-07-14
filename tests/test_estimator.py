"""Spec 5 acceptance test: the Gauss-Newton position solver.

The moment of truth for the whole project so far: hand the navigator only
(a) the measured star-pair angles, (b) the public catalog, and (c) a rough
starting guess -- and it must find the spacecraft's true position. With a
perfect camera (zero noise) there is no excuse: recovery must be exact to
machine precision (SOLVER_RECOVERY_TOL_AU), in fewer than
SOLVER_MAX_ITERS rounds, from any direction of starting error.

The navigator never sees TRUE_POS_AU -- the test (playing the experiment-
script role) uses it only to generate measurements on the truth side and
to grade the answer afterward.
"""

from pathlib import Path

import numpy as np

from galnav.nav.estimator import solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from tests.golden_numbers import (
    SOLVER_MAX_ITERS,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_STEP_TOL_AU,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

TRUE_POS_AU = np.array([1.0e5, -2.0e5, 3.0e5])

# Same well-separated pairs as Spec 4 (61 Cygni companions never paired
# with each other -- see journal/spec-4-measmodel.md).
PAIRS = np.array([[0, 1], [2, 3], [4, 5], [6, 7], [8, 3], [0, 9], [3, 7]])

# "Good start" offsets: ~1000 au of initial error, tried along axes and
# diagonally so no lucky direction can hide a bug (setup values).
START_OFFSETS_AU = np.array(
    [
        [800.0, -600.0, 400.0],
        [-1000.0, 0.0, 0.0],
        [0.0, 0.0, 1000.0],
        [577.0, 577.0, 577.0],
    ]
)


def _measurements_and_stars():
    stars = star_positions_au(load_catalog(CATALOG_CSV))[:10]
    measured = observed_pair_angles(
        stars, TRUE_POS_AU, PAIRS, 0.0, np.random.default_rng(0)
    )
    return measured, stars


def test_noiseless_recovery_to_machine_precision():
    # Zero camera noise -> the solver must land ON the true position,
    # from every starting direction. Catches wrong Jacobian usage, wrong
    # residual sign, and any systematic bias in the update step.
    measured, stars = _measurements_and_stars()
    for offset in START_OFFSETS_AU:
        found, _ = solve_position(
            measured,
            stars,
            PAIRS,
            TRUE_POS_AU + offset,
            SOLVER_STEP_TOL_AU,
            SOLVER_MAX_ITERS,
        )
        assert np.linalg.norm(found - TRUE_POS_AU) < SOLVER_RECOVERY_TOL_AU


def test_converges_in_under_ten_rounds():
    # Healthy Gauss-Newton doubles its correct digits every round, so a
    # good start must converge fast. Slow creep means the Jacobian and
    # the residual disagree -- a bug this test refuses to let hide.
    measured, stars = _measurements_and_stars()
    for offset in START_OFFSETS_AU:
        _, iterations = solve_position(
            measured,
            stars,
            PAIRS,
            TRUE_POS_AU + offset,
            SOLVER_STEP_TOL_AU,
            SOLVER_MAX_ITERS,
        )
        assert iterations < SOLVER_MAX_ITERS


def test_reports_honest_iteration_count():
    # The iteration count must be a real diagnostic, not decoration:
    # starting EXACTLY at the answer must cost at most one round.
    measured, stars = _measurements_and_stars()
    _, iterations = solve_position(
        measured, stars, PAIRS, TRUE_POS_AU.copy(), SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )
    assert iterations <= 1
