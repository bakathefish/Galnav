"""Spec 1 acceptance test: geometry primitives.

angle_between(v1, v2) takes two DIRECTION vectors -- which way you'd point a
telescope -- and returns the angle between them in radians. It doesn't care
how far away anything is, only which way each vector points. Later, v1/v2
will be real star directions built from catalog RA/dec; for now these are
toy directions chosen because the right answer is obvious by hand.
"""

import numpy as np

from galnav.geometry import angle_between


def test_perpendicular_vectors_are_90_degrees():
    # x-axis and y-axis point at right angles to each other.
    assert abs(angle_between([1, 0, 0], [0, 1, 0]) - np.pi / 2) < 1e-12


def test_identical_vectors_are_0_degrees():
    # pointing at the same thing twice: no angle between them.
    assert abs(angle_between([1, 0, 0], [1, 0, 0])) < 1e-12


def test_opposite_vectors_are_180_degrees():
    # pointing in exactly opposite directions.
    assert abs(angle_between([1, 0, 0], [-1, 0, 0]) - np.pi) < 1e-12


def test_angle_between_is_symmetric():
    a, b = [1, 0, 0], [0, 1, 1]
    assert abs(angle_between(a, b) - angle_between(b, a)) < 1e-12


def test_length_does_not_matter_only_direction():
    # a vector 5 units long pointing at x vs 3 units long pointing at y --
    # still 90 degrees apart, because only direction matters here.
    assert abs(angle_between([5, 0, 0], [0, 3, 0]) - np.pi / 2) < 1e-12
