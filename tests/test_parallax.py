"""Spec 2 acceptance test: parallax / displacement engine.

parallax_angle(baseline_au, distance_au) answers: if the observer slides
sideways by baseline_au (perpendicular to the line of sight), by what angle
does a star at distance_au appear to shift? Returns radians. This is the
physical signal the whole navigation method reads.
"""

import numpy as np

from galnav.geometry import angle_between
from galnav.parallax import parallax_angle
from tests.golden_numbers import (
    ANGLE_TOL_RAD,
    DISPLACEMENT_REL_TOL,
    PARALLAX_REL_TOL,
    PC_AU,
    RAD_ARCSEC,
)


def test_star_at_one_parsec_shifts_one_arcsec_over_one_au():
    # THE definition of a parsec: 1 au of sideways motion, star 1 pc away,
    # apparent shift exactly 1 arcsecond. If this fails the code is wrong,
    # full stop -- it's a definition, not a measurement.
    shift_arcsec = parallax_angle(1.0, PC_AU) * RAD_ARCSEC
    assert abs(shift_arcsec - 1.0) < PARALLAX_REL_TOL


def test_displacement_rule_holds_over_six_orders_of_magnitude():
    # The shortcut rule: shift = (how far you moved) / (how far the star is).
    # Checked for stars from 1,000 au to 1,000,000,000 au -- six jumps of
    # 10x -- because precision bugs hide at the extremes, not in the middle.
    d_au = np.logspace(3, 9, 7)  # 1e3, 1e4, ..., 1e9 au
    exact = parallax_angle(1.0, d_au)
    shortcut = 1.0 / d_au
    assert exact.shape == d_au.shape  # must vectorize, not loop
    assert np.all(np.abs(exact - shortcut) / exact < DISPLACEMENT_REL_TOL)


def test_agrees_with_full_3d_construction_using_spec1_tool():
    # Independent cross-check: build the same situation as actual 3D arrows
    # and measure with Spec 1's angle_between. Star straight ahead at 10 au,
    # observer slides 1 au sideways. (A deliberately WIDE angle: arccos in
    # angle_between loses precision on tiny angles, so the tight comparison
    # is only fair where both methods are at full precision.)
    d_au, move_au = 10.0, 1.0
    look_before = [0.0, 0.0, d_au]
    look_after = [-move_au, 0.0, d_au]
    assert (
        abs(angle_between(look_before, look_after) - parallax_angle(move_au, d_au))
        < ANGLE_TOL_RAD
    )
