"""Tests for gui.locate -- identification and the line-of-position fix.

The exact-direction fix is machine-precision; the pixel-quantized full chain is
bounded by the centroiding angular error times the (far) star distance, a bound
computed from the scene rather than hardcoded.
"""

import numpy as np
import pytest

from galnav.units import arcsec_to_rad, deg_to_rad, radec_to_unit
from gui.centroids import find_centroids
from gui.locate import (
    LineOfPosition,
    fix_position,
    identify_in_frame,
    measured_direction,
)
from gui.platesolve import PlateSolution
from tests_gui.synth import (
    BARNARD_ID,
    PROXIMA_ID,
    WOLF_ID,
    Scene,
    build_synthetic,
    _tan_wcs,
)

R_TRUE = np.array([13.5, -42.0, -16.5])
AGE = 4.5
SCALE = 4.0

# Exact directions pass exactly through r, so n_star_solve recovers it to
# rounding (~1e-10 au measured); 1e-6 au is a loose gate that still fails any
# real algebra error.
EXACT_FIX_TOL_AU = 1e-6


def _one_star_scene(sid, seed=7):
    return build_synthetic(
        Scene(
            r_au=R_TRUE, source_ids=[sid], age_yr=AGE, scale_arcsec_px=SCALE, seed=seed
        )
    )


def test_identify_finds_injected_star_with_correct_id():
    """identify must match the target star to its own centroid with the right
    source id; a WCS 0-vs-1-index bug would put the prediction a pixel off but
    still inside radius, so we also require the matched centroid to sit on the
    injected pixel (<1 px)."""
    sc = _one_star_scene(PROXIMA_ID)
    cen = find_centroids(sc["image"])
    matches = identify_in_frame(sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"])
    ids = {int(sc["aged_cat"]["source_id"][m["star_index"]]) for m in matches}
    assert PROXIMA_ID in ids
    m = next(
        m
        for m in matches
        if int(sc["aged_cat"]["source_id"][m["star_index"]]) == PROXIMA_ID
    )
    cx, cy = cen["xy"][m["centroid_index"]]
    ax, ay = sc["apparent_xy"][0]
    assert np.hypot(cx - ax, cy - ay) < 1.0


def test_identify_rejects_centroid_outside_match_radius():
    """With a match radius smaller than the parallax offset, the star's centroid
    is beyond tolerance from its barycentric prediction and must NOT match --
    proving the radius gate works (parallax = 8 px here, radius = 10 arcsec)."""
    sc = _one_star_scene(PROXIMA_ID)
    cen = find_centroids(sc["image"])
    off_px = np.hypot(*(sc["apparent_xy"][0] - sc["bary_xy"][0]))
    assert off_px * SCALE > 10.0  # parallax offset exceeds the radius we set
    matches = identify_in_frame(
        sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"], match_radius_arcsec=10.0
    )
    got = {int(sc["aged_cat"]["source_id"][m["star_index"]]) for m in matches}
    assert PROXIMA_ID not in got


def test_identify_ignores_filler_star():
    """Filler (non-catalog) sources must never be reported as catalog matches;
    only the injected catalog star is returned."""
    sc = _one_star_scene(PROXIMA_ID)
    cen = find_centroids(sc["image"])
    matches = identify_in_frame(sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"])
    # Every match must land on the injected star's pixel, never on a filler.
    for m in matches:
        cx, cy = cen["xy"][m["centroid_index"]]
        on_star = np.hypot(cx - sc["apparent_xy"][0][0], cy - sc["apparent_xy"][0][1])
        assert on_star < 2.0


def _exact_lines(ids):
    sc = build_synthetic(
        Scene(r_au=R_TRUE, source_ids=ids, age_yr=AGE, scale_arcsec_px=SCALE)
    )
    lines = []
    for k, sid in enumerate(ids):
        si = sc["star_indices"][k]
        lines.append(
            LineOfPosition(
                sc["aged_cat"]["positions_au"][si],
                sc["directions"][k],
                sid,
                0.0,
                "exact",
            )
        )
    return lines


def test_fix_exact_two_lines_recovers_position():
    """Two exact lines of position must intersect at the true spacecraft to
    machine precision -- the algebra of n_star_solve reused here."""
    fix = fix_position(_exact_lines([PROXIMA_ID, BARNARD_ID]))
    assert np.linalg.norm(fix["x_au"] - R_TRUE) < EXACT_FIX_TOL_AU
    assert fix["n_lines"] == 2 and fix["distinct_stars"] == 2
    # The error ellipsoid semi-axes must be sorted largest-first.
    assert np.all(np.diff(fix["ellipsoid_au"]) <= 0)


def test_fix_exact_three_lines_recovers_position():
    """A third line must not degrade the fix; over-determined solve still lands
    on the true position to machine precision."""
    fix = fix_position(_exact_lines([PROXIMA_ID, BARNARD_ID, WOLF_ID]))
    assert np.linalg.norm(fix["x_au"] - R_TRUE) < EXACT_FIX_TOL_AU


def test_fix_full_pixel_chain_recovers_position():
    """The full chain (render -> centroid -> WCS direction -> fix) must recover
    r within the centroiding error bound: miss <~ (far star distance) times a
    2-pixel angular error. Measured miss ~0.01 au, bound ~15 au."""
    lines, max_dist = [], 0.0
    for sid in (PROXIMA_ID, BARNARD_ID):
        sc = _one_star_scene(sid)
        cen = find_centroids(sc["image"])
        matches = identify_in_frame(
            sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"]
        )
        m = next(
            m
            for m in matches
            if int(sc["aged_cat"]["source_id"][m["star_index"]]) == sid
        )
        si = m["star_index"]
        direction = measured_direction(sc["plate"], cen["xy"][m["centroid_index"]])
        pos = sc["aged_cat"]["positions_au"][si]
        lines.append(LineOfPosition(pos, direction, sid, m["sep_arcsec"], str(sid)))
        max_dist = max(max_dist, np.linalg.norm(pos))
    fix = fix_position(lines, rmssig_arcsec=0.44)
    miss = np.linalg.norm(fix["x_au"] - R_TRUE)
    bound_au = max_dist * arcsec_to_rad(2.0 * SCALE)  # 2-pixel angular error
    assert miss < bound_au


def test_fix_single_line_raises():
    """One image gives a line, not a point; fix_position must refuse and say so."""
    lines = _exact_lines([PROXIMA_ID, BARNARD_ID])[:1]
    with pytest.raises(ValueError, match="at least 2"):
        fix_position(lines)


def test_fix_same_star_lines_raise():
    """Two lines from the SAME star are parallel and fix only a line; refuse."""
    lines = _exact_lines([PROXIMA_ID, BARNARD_ID])
    lines[1].star_source_id = lines[0].star_source_id  # pretend both are Proxima
    with pytest.raises(ValueError, match="same star"):
        fix_position(lines)


def test_fix_parallel_directions_raise():
    """Distinct stars but near-parallel sightlines do not intersect at a point;
    the eigenvalue gate must catch it."""
    p = np.array([1.0e5, 0.0, 0.0])
    d0 = np.array([1.0, 0.0, 0.0])
    d1 = np.array([1.0, 1e-8, 0.0])
    d1 /= np.linalg.norm(d1)
    lines = [
        LineOfPosition(p, d0, 111, 0.0, "a"),
        LineOfPosition(p * 1.1, d1, 222, 0.0, "b"),
    ]
    with pytest.raises(ValueError, match="parallel"):
        fix_position(lines)


def _mock_plate(nx=256, ny=256, ra0=100.0, dec0=20.0, scale=4.0):
    """A distortion-free TAN PlateSolution for direct identify_in_frame tests."""
    return PlateSolution(
        wcs=_tan_wcs(ra0, dec0, scale, nx, ny), source="mock", width=nx, height=ny
    )


def _dir_at_pixel(plate, x, y):
    """Unit direction whose barycentric projection lands on pixel (x, y)."""
    sky = plate.wcs.pixel_to_world(x, y).icrs
    return radec_to_unit(deg_to_rad(sky.ra.deg), deg_to_rad(sky.dec.deg))


def test_identify_uniqueness_closest_star_wins():
    """Two catalog stars predicted near ONE centroid must not both claim it: the
    closer star wins and the centroid is used at most once. Exercises the
    one-to-one matching guard."""
    plate = _mock_plate()
    near = _dir_at_pixel(plate, 129.0, 128.0)  # 1 px from the centroid
    far = _dir_at_pixel(plate, 132.0, 128.0)  # 4 px from the centroid
    positions = np.array([far, near]) * 1.0e5  # deliberately far-first ordering
    centroids = np.array([[128.0, 128.0]])  # a single centroid
    matches = identify_in_frame(plate, centroids, positions, match_radius_arcsec=120.0)
    assert len(matches) == 1
    assert matches[0]["star_index"] == 1  # the CLOSER star (row 1) wins
    used = [m["centroid_index"] for m in matches]
    assert len(used) == len(set(used))  # centroid claimed at most once


def test_identify_border_pixel_in_bounds():
    """A star landing exactly on the (0,0) or (w-1,h-1) corner pixel must count as
    in-frame -- the WCS round-trip can push it a sub-picometre negative, which a
    naive [0, w-1] bound would wrongly reject."""
    plate = _mock_plate()
    for bx, by in [(0.0, 0.0), (plate.width - 1.0, plate.height - 1.0)]:
        direction = _dir_at_pixel(plate, bx, by)
        positions = np.array([direction]) * 1.0e5
        centroids = np.array([[bx, by]])
        matches = identify_in_frame(
            plate, centroids, positions, match_radius_arcsec=60.0
        )
        assert len(matches) == 1
