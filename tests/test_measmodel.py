"""Spec 4 acceptance test: Measurement Model A + its position Jacobian.

The NAVIGATOR's side of the mirror. predicted_pair_angles answers "if the
spacecraft were at position X, what angle would the camera see between
star i and star j?" pair_angle_jacobian answers "and how much does each
of those predicted angles change if X slides 1 au along x, y, or z?"

The Jacobian gate (from the project plan): the hand-derived formula must
agree with brute-force numerical nudging to better than 1e-6 relative,
and must stay that accurate across FOUR decades of nudge size (0.1 au to
100 au). Passing at one nudge size could be luck; passing across four
decades means the formula itself is right.
"""

from pathlib import Path

import numpy as np

from galnav.geometry import angle_between
from galnav.nav.measmodel import pair_angle_jacobian, predicted_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from tests.golden_numbers import ANGLE_TOL_RAD, JACOBIAN_REL_TOL

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

# Fixed spacecraft guess ~1.8 pc out (setup value, not a tolerance), same
# vantage point style as Spec 3's tests.
GUESS_POS_AU = np.array([1.0e5, -2.0e5, 3.0e5])

# Star pairs chosen to be WELL SEPARATED (20-156 degrees; verified against
# the catalog). Stars 8 and 9 are the two members of the 61 Cygni binary --
# 0.0165 degrees apart from our vantage point -- so they are never paired
# with EACH OTHER: a near-zero pair angle carries almost no position signal,
# which makes the 1e-6 numerical-agreement gate physically unreachable for
# that one pair (students' decision 2026-07-14, journal/logbook.md). Both
# stars still appear below, paired with distant partners.
PAIRS = np.array([[0, 1], [2, 3], [4, 5], [6, 7], [8, 3], [0, 9], [3, 7]])


def _stars():
    # The test plays the role of an experiment script: it loads the public
    # catalog and hands plain arrays to the navigator.
    return star_positions_au(load_catalog(CATALOG_CSV))[:10]


def test_predicted_angles_match_independent_construction():
    # The predictor must give exactly the angle you get by building each
    # arrow by hand and using Spec 1's tool. Catches indexing, sign, and
    # normalization mistakes.
    stars = _stars()
    got = predicted_pair_angles(stars, GUESS_POS_AU, PAIRS)
    for k, (i, j) in enumerate(PAIRS):
        expected = angle_between(stars[i] - GUESS_POS_AU, stars[j] - GUESS_POS_AU)
        assert abs(got[k] - expected) < ANGLE_TOL_RAD


def test_analytic_jacobian_matches_numerical_over_four_decades():
    # Central differences: nudge the position +h and -h along each axis,
    # difference the predicted angles, divide by 2h. The analytic formula
    # must match that, row by row, for h = 0.1, 1, 10 and 100 au.
    stars = _stars()
    analytic = pair_angle_jacobian(stars, GUESS_POS_AU, PAIRS)  # (P, 3)
    assert analytic.shape == (len(PAIRS), 3)

    for h_au in (0.1, 1.0, 10.0, 100.0):
        numerical = np.empty_like(analytic)
        for axis in range(3):
            step = np.zeros(3)
            step[axis] = h_au
            plus = predicted_pair_angles(stars, GUESS_POS_AU + step, PAIRS)
            minus = predicted_pair_angles(stars, GUESS_POS_AU - step, PAIRS)
            numerical[:, axis] = (plus - minus) / (2.0 * h_au)
        row_err = np.linalg.norm(numerical - analytic, axis=1)
        row_scale = np.linalg.norm(analytic, axis=1)
        assert np.all(row_err / row_scale < JACOBIAN_REL_TOL), f"failed at h={h_au} au"


def test_jacobian_magnitude_obeys_displacement_rule():
    # Physics sanity: Spec 2 taught us a 1 au move shifts a star at
    # distance d by about 1/d radians. The sensitivity of a PAIR angle can
    # therefore never exceed (1/d_i + 1/d_j) -- each star contributes at
    # most its own displacement-rule shift. Catches any formula that has
    # the right shape but wrong scale.
    stars = _stars()
    analytic = pair_angle_jacobian(stars, GUESS_POS_AU, PAIRS)
    dist = np.linalg.norm(stars - GUESS_POS_AU, axis=1)
    bound = 1.0 / dist[PAIRS[:, 0]] + 1.0 / dist[PAIRS[:, 1]]
    assert np.all(np.linalg.norm(analytic, axis=1) <= bound)
