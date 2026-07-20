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
    line_of_position_summary,
    measured_direction,
)
from gui.platesolve import PlateSolution
from tests_gui.synth import (
    BARNARD_ID,
    PROXIMA_ID,
    WIDE_PAIR_A_ID,
    WIDE_PAIR_B_ID,
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


# --- do.txt item 9: solve from ONE image with two nearby stars ---------------
# A single frame that shows >= 2 distinct nearby stars already fixes a 3-D point:
# fix_position needs 2 lines from 2 distinct stars and does NOT care that both
# came from one image. WIDE_PAIR_A/B are 10.56 deg apart, so a single wide-field
# TAN frame holds both; each New Horizons LORRI frame (0.29 deg field) holds only
# ONE nearby star, which is the honest reason THAT demo needs two images. The
# observer sits at ~329 au (a hypothetical distant probe) so the two stars'
# parallax is a few pixels even at the coarse wide-field plate scale.
WIDE_R_TRUE = np.array([180.0, -260.0, 90.0])  # |r| = 328.8 au


def _wide_single_frame_lines(seed=7):
    """Full pipeline on ONE wide frame holding the two isolated nearby stars:
    render -> centroid -> identify -> measured_direction -> LineOfPosition. Both
    returned lines carry the SAME image_name (they came from one frame)."""
    sc = build_synthetic(
        Scene(
            r_au=WIDE_R_TRUE,
            source_ids=[WIDE_PAIR_A_ID, WIDE_PAIR_B_ID],
            age_yr=AGE,
            scale_arcsec_px=34.0,  # coarse: 11.3 deg half-field holds the 10.56 deg pair
            size_px=(2400, 2400),
            seed=seed,
            filler_xy=[],  # render ONLY the two catalog stars (no decoy blobs)
        )
    )
    cen = find_centroids(sc["image"])
    matches = identify_in_frame(sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"])
    lines = []
    for m in matches:
        sid = int(sc["aged_cat"]["source_id"][m["star_index"]])
        direction = measured_direction(sc["plate"], cen["xy"][m["centroid_index"]])
        pos = sc["aged_cat"]["positions_au"][m["star_index"]]
        lines.append(
            LineOfPosition(pos, direction, sid, m["sep_arcsec"], "one-wide-frame")
        )
    return lines


def test_single_image_two_wide_stars_fixes_observer():
    """ONE image with two distinct nearby stars gives a full 3-D point fix.
    The two lines of position s_i - lambda_i*d_i leave DIFFERENT stars and cross
    at the single observer, so one frame suffices -- no second image needed. This
    is do.txt item 9 made concrete: run the real pipeline on one wide frame and
    recover where the camera was.

    Measured recovery at seed 7 is 6.8 au (2.1% of |r|=329 au); the worst over
    seeds 1-8 is 11.8 au (3.6%). We gate at 10% of |r| -- comfortably met, yet
    ~35x tighter than the narrow-field twin's ~630 au ellipsoid below, so a
    regression that broke the single-frame geometry (e.g. dropped a line) fails."""
    lines = _wide_single_frame_lines(seed=7)
    ids = {ln.star_source_id for ln in lines}
    assert ids == {WIDE_PAIR_A_ID, WIDE_PAIR_B_ID}  # both stars, no decoy matches
    assert len({ln.image_name for ln in lines}) == 1  # ... from a SINGLE image
    fix = fix_position(lines, rmssig_arcsec=0.5)
    assert fix["distinct_stars"] == 2 and fix["n_lines"] == 2
    miss = np.linalg.norm(fix["x_au"] - WIDE_R_TRUE)
    assert miss < 0.1 * np.linalg.norm(WIDE_R_TRUE)


def _dop_major_axis_au(gamma_deg, d0_pc=3.97, d1_pc=4.97, rmssig=0.5):
    """Formal 1-sigma major axis (au) of the fix from TWO exact lines whose
    sightlines cross at angle gamma, at the real wide-pair distances and the same
    observer as the frame test. Exact directions isolate the pure geometry: the
    fix is machine-exact, so only the error ELLIPSOID reflects gamma. Returns
    (major_axis_au, fix_miss_au)."""
    au_per_pc = 206264.806
    g = deg_to_rad(gamma_deg)
    u0 = np.array([1.0, 0.0, 0.0])
    u1 = np.array([np.cos(g), np.sin(g), 0.0])
    p0 = WIDE_R_TRUE + d0_pc * au_per_pc * u0
    p1 = WIDE_R_TRUE + d1_pc * au_per_pc * u1
    lines = [
        LineOfPosition(p0, u0, 1, 0.0, "a"),
        LineOfPosition(p1, u1, 2, 0.0, "b"),
    ]
    fix = fix_position(lines, rmssig_arcsec=rmssig)
    miss = np.linalg.norm(fix["x_au"] - WIDE_R_TRUE)
    return fix["ellipsoid_au"][0], miss


def test_narrow_field_dilutes_fix_as_one_over_sin_half_gamma():
    """WHY the New Horizons demo needs two images: geometric dilution.
    Two lines crossing at a wide angle pin the observer tightly; two crossing at
    a narrow angle (both stars inside one 0.29 deg LORRI field) pin only a fat
    cigar along the mean sightline. For two equal-weighted lines the summed
    projector sum(I - d d^T) has smallest eigenvalue 1 - cos(gamma), so the major
    semi-axis grows as 1/sqrt(1 - cos gamma) = 1/(sqrt2 * sin(gamma/2)) -- it
    blows up as gamma -> 0. Wide gamma = 10.56 deg is the real pair's separation
    (the frame test above); narrow gamma = 0.29 deg is LORRI's field width, the
    most two of its in-frame nearby stars could be apart.

    Measured: major axis 17.3 au (wide) vs 628 au (narrow), a 36.4x blow-up, while
    the fix itself still recovers the observer to < 1e-3 au -- it is the ELLIPSOID
    that balloons, not the point. We pin ratio > 20 and that it tracks the
    1/sin(gamma/2) law to 3% (measured 36.4 vs 36.36)."""
    wide, wide_miss = _dop_major_axis_au(10.56)
    narrow, narrow_miss = _dop_major_axis_au(0.29)
    # Exact directions -> the fix still returns a finite POINT in both cases.
    assert wide_miss < 1e-3 and narrow_miss < 1e-3
    # The narrow-field major axis balloons relative to the wide-field one.
    ratio = narrow / wide
    assert ratio > 20.0
    # ... and it follows the analytic 1/sin(gamma/2) dilution law.
    law = np.sin(deg_to_rad(10.56 / 2.0)) / np.sin(deg_to_rad(0.29 / 2.0))
    assert abs(ratio - law) / law < 0.03
    # Absolute grounding: wide is tens of au, narrow is hundreds.
    assert wide < 50.0 and narrow > 300.0


def _one_star_line(sid=PROXIMA_ID, seed=7, name="frame"):
    """Full pipeline on a one-star frame -> that star's single LineOfPosition."""
    sc = _one_star_scene(sid, seed=seed)
    cen = find_centroids(sc["image"])
    m = next(
        m
        for m in identify_in_frame(
            sc["plate"], cen["xy"], sc["aged_cat"]["positions_au"]
        )
        if int(sc["aged_cat"]["source_id"][m["star_index"]]) == sid
    )
    direction = measured_direction(sc["plate"], cen["xy"][m["centroid_index"]])
    pos = sc["aged_cat"]["positions_au"][m["star_index"]]
    return LineOfPosition(pos, direction, sid, m["sep_arcsec"], name)


def _perp_distance_au(point, anchor, ray_unit):
    """Perpendicular distance from point to the ray through anchor along ray_unit."""
    v = np.asarray(point, float) - np.asarray(anchor, float)
    u = np.asarray(ray_unit, float)
    return float(np.linalg.norm(v - (v @ u) * u))


def test_line_of_position_summary_ray_passes_through_observer():
    """One image, one nearby star: no point fix, but a drawable LINE. The helper
    returns the ray from the star toward the observer, and the TRUE observer must
    lie on it. Measured perpendicular miss is 0.033 au at seed 7 (0.068 au worst
    over seeds 1-8) -- a whisker beside Proxima's 268,530 au distance -- so we
    gate at 0.2 au. Also checks the ray is a unit vector pointing star->observer
    (back toward the Sun), the fan-out is exactly 0 for one line, and the draw
    span reaches 100 au past the star's distance."""
    summ = line_of_position_summary([_one_star_line(PROXIMA_ID, seed=7)])
    assert summ["source_id"] == PROXIMA_ID
    assert summ["n_lines"] == 1
    assert summ["residual_spread_arcsec"] == 0.0  # one line cannot disagree
    ray = np.array(summ["ray_unit"])
    assert abs(np.linalg.norm(ray) - 1.0) < 1e-12  # unit vector
    anchor = np.array(summ["anchor_au"])
    # The ray points FROM the star back toward the observer / Sun (anti-anchor).
    assert ray @ (-anchor / np.linalg.norm(anchor)) > 0.999
    # Recommended draw span = |anchor| + 100 au; endpoint is its far end.
    assert abs(summ["span_au"] - (np.linalg.norm(anchor) + 100.0)) < 1e-6
    endpoint = np.array(summ["endpoint_au"])
    assert np.linalg.norm(endpoint - (anchor + summ["span_au"] * ray)) < 1e-6
    # THE point of item 9: the true observer sits on the returned line.
    assert _perp_distance_au(R_TRUE, anchor, ray) < 0.2


def test_line_of_position_summary_merges_two_same_star_lines():
    """Two frames of the SAME nearby star (the degenerate two-image case, e.g. the
    two New Horizons Proxima frames) still make only a line, but the helper merges
    them: it averages the two rays and reports how far they fan apart. Measured
    fan-out is 0.015 arcsec and the merged ray still passes 0.050 au from the
    observer; we gate the spread in (0, 0.1 arcsec) and the miss < 0.2 au."""
    lines = [
        _one_star_line(PROXIMA_ID, seed=7, name="f0"),
        _one_star_line(PROXIMA_ID, seed=8, name="f1"),
    ]
    summ = line_of_position_summary(lines)
    assert summ["n_lines"] == 2
    assert summ["source_id"] == PROXIMA_ID
    # Two noisy frames disagree a little, but far less than an arcsec.
    assert 0.0 < summ["residual_spread_arcsec"] < 0.1
    assert _perp_distance_au(R_TRUE, summ["anchor_au"], summ["ray_unit"]) < 0.2


def test_line_of_position_summary_rejects_zero_lines():
    """No line at all -> nothing to draw; the helper says so in plain English."""
    with pytest.raises(ValueError, match="at least one"):
        line_of_position_summary([])


def test_line_of_position_summary_rejects_multiple_stars():
    """Lines from >= 2 distinct stars fix a POINT, not a line -- that case belongs
    to fix_position, and the helper refuses it by name."""
    lines = _exact_lines([PROXIMA_ID, BARNARD_ID])
    with pytest.raises(ValueError, match="distinct stars"):
        line_of_position_summary(lines)
