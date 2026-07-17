"""Test for gui.age.estimate_age -- the estimate-the-catalog-age mode.

Full chain on two synthetic frames rendered at a known true age: the chi2 scan
must find that age, the parabola curvature must bracket it, and the curve must
be convex at the minimum.
"""

import numpy as np
from astropy.coordinates import SkyCoord

from galnav.units import deg_to_rad, radec_to_unit
from gui.age import drift_date, estimate_age
from gui.centroids import find_centroids
from gui.locate import (
    LineOfPosition,
    identify_in_frame,
    load_aged_catalog,
    measured_direction,
)
from gui.platesolve import PlateSolution
from tests_gui.synth import (
    BARNARD_ID,
    PROXIMA_ID,
    REAL_CSV,
    Scene,
    _tan_wcs,
    build_synthetic,
)

AU_PER_PC = 206264.806

R_TRUE = np.array([13.5, -42.0, -16.5])
# Deliberately OFF-grid (grid step 0.25, nodes at ...4.5, 4.75...): the true age
# falling between nodes lets the sub-grid parabola vertex beat the grid argmin,
# which pins the vertex-formula sign.
TRUE_AGE = 4.6
SCALE = 4.0

# Grid step is 0.25 yr; the sub-grid parabola recovers the true age to ~0.001 yr
# (measured). 0.5 yr is a loose gate that still fails if the minimum lands on
# the wrong grid node (>=0.25 yr off) or the curve is not tracking proper motion.
AGE_ERR_TOL_YR = 0.5

# Pristine sigma_age for THIS scene at rmssig=1.0, MEASURED 2026-07-17 = 0.4836 yr.
# Asserting 0.5x-2x pins the magnitude: it kills the "factor 2 -> 1" mutant in
# sigma=sqrt(2/chi2'') and, crucially, the "norm -> 1" mutant (un-normalised chi2
# blows sigma up to ~1e5 yr, far outside this band).
SIGMA_AGE_YR_MEASURED = 0.4836


def test_estimate_age_recovers_true_age():
    """The chi2-vs-age minimum must sit at the epoch the frames were taken,
    within 0.5 yr, with the true age inside age_hat +/- 3 sigma and a convex
    minimum -- i.e. proper-motion drift really does drive the fix quality."""
    frames = []
    for sid in (PROXIMA_ID, BARNARD_ID):
        sc = build_synthetic(
            Scene(r_au=R_TRUE, source_ids=[sid], age_yr=TRUE_AGE, scale_arcsec_px=SCALE)
        )
        frames.append((sid, sc["plate"], find_centroids(sc["image"])))

    def build_lines(age_yr):
        lines = []
        for sid, plate, cen in frames:
            cat = load_aged_catalog(REAL_CSV, age_yr, rv_fill_kms=0.0)
            matches = identify_in_frame(
                plate, cen["xy"], cat["positions_au"], match_radius_arcsec=200.0
            )
            for m in matches:
                if int(cat["source_id"][m["star_index"]]) != sid:
                    continue
                d = measured_direction(plate, cen["xy"][m["centroid_index"]])
                lines.append(
                    LineOfPosition(
                        cat["positions_au"][m["star_index"]],
                        d,
                        sid,
                        m["sep_arcsec"],
                        str(sid),
                    )
                )
        return lines

    grid = np.arange(0.0, 10.0 + 1e-9, 0.25)
    res = estimate_age(build_lines, grid, rmssig_arcsec=1.0)

    assert abs(res["age_hat_yr"] - TRUE_AGE) < AGE_ERR_TOL_YR
    assert np.isfinite(res["sigma_age_yr"]) and res["sigma_age_yr"] > 0
    assert abs(res["age_hat_yr"] - TRUE_AGE) < 3.0 * res["sigma_age_yr"]
    # sigma MAGNITUDE (kills the factor-2 and un-normalised-chi2 mutants):
    assert (
        0.5 * SIGMA_AGE_YR_MEASURED < res["sigma_age_yr"] < 2.0 * SIGMA_AGE_YR_MEASURED
    )
    # Normalised chi2 is a proper chi-squared, so its minimum is O(1), not 1e-13
    # (raw) nor 1e5 (mis-normalised): the raw-vs-normalised sanity guard.
    assert float(np.min(res["chi2s"])) < 5.0
    # The sub-grid vertex must be at least as close to truth as the grid node it
    # sits between (kills a sign flip in the parabola-vertex formula).
    grid_argmin_age = float(grid[int(np.argmin(res["chi2s"]))])
    assert abs(res["age_hat_yr"] - TRUE_AGE) <= abs(grid_argmin_age - TRUE_AGE)
    # Convex minimum: both neighbours of the grid argmin are strictly higher.
    i = int(np.argmin(res["chi2s"]))
    assert 0 < i < len(grid) - 1
    assert res["chi2s"][i - 1] > res["chi2s"][i] < res["chi2s"][i + 1]


def _stub_two_lines(offset_z):
    """Two skew lines whose closest-approach gap (hence chi2) grows with
    |offset_z|; they intersect exactly at offset_z = 0."""
    p_a = np.array([1.0e5, 0.0, 0.0])
    d_a = np.array([-1.0, 0.0, 0.0])
    p_b = np.array([0.0, 1.0e5, offset_z])
    d_b = np.array([0.0, -1.0, 0.0])
    return [
        LineOfPosition(p_a, d_a, 111, 0.0, "a"),
        LineOfPosition(p_b, d_b, 222, 0.0, "b"),
    ]


def test_estimate_age_survives_unmatchable_ages():
    """Ages that yield < 2 lines (stars drift out of the match radius) must NOT
    crash the scan: they score +inf and the parabola still fits the interior
    minimum. Guards the booth-critical default-settings crash."""

    def build_lines(age_yr):
        if abs(age_yr - 5.0) > 3.0:  # far ages: nothing in frame -> no lines
            return []
        return _stub_two_lines((age_yr - 5.0) * 100.0)  # parabolic chi2, min at 5

    grid = np.arange(0.0, 10.0 + 1e-9, 0.25)
    res = estimate_age(build_lines, grid)  # must not raise
    assert np.any(~np.isfinite(res["chi2s"]))  # some ages really were unmatchable
    assert np.isfinite(res["age_hat_yr"])
    assert abs(res["age_hat_yr"] - 5.0) < 0.5
    assert np.isfinite(res["sigma_age_yr"]) and res["sigma_age_yr"] > 0


def test_estimate_age_edge_or_infneighbor_falls_back_to_nan_sigma():
    """When the minimum's neighbour is +inf (unmatchable), sigma is unavailable:
    return the grid-argmin age, NaN sigma, and a plain-English note -- never
    raise, never emit a bogus curvature error."""

    def build_lines(age_yr):
        if abs(age_yr - 5.0) > 0.1:  # only age 5.0 is matchable -> neighbours inf
            return []
        return _stub_two_lines(0.0)

    grid = np.arange(0.0, 10.0 + 1e-9, 0.25)
    res = estimate_age(build_lines, grid)
    assert abs(res["age_hat_yr"] - 5.0) < 1e-9  # grid node, no sub-grid shift
    assert np.isnan(res["sigma_age_yr"])
    assert res["note"]  # non-empty explanation the app can print


# --- single-star drift dating (negative ages) -------------------------------


def _drift_scene(
    true_age,
    pmra=4.0,
    pmdec=-3.0,
    dist_pc=3.0,
    sid=900123,
    ra0=150.0,
    dec0=20.0,
    scale=2.0,
    nx=128,
    ny=128,
    offset_px=0.25,
):
    """A one-star drift scene: a catalog fn for a star drifting at (pmra, pmdec)
    arcsec/yr, a plate centred on the star's position at `true_age`, and one
    centroid at the star's projected pixel (nudged offset_px for a realistic V).
    No parallax (observer at the barycentre), matching a ground plate's ~0.4 arcsec."""

    def cat_fn(a):
        dec = dec0 + a * pmdec / 3600.0
        ra = ra0 + a * pmra / 3600.0 / np.cos(np.radians(dec0))
        u = radec_to_unit(deg_to_rad(ra), deg_to_rad(dec))
        return {
            "positions_au": (u * dist_pc * AU_PER_PC).reshape(1, 3),
            "source_id": np.array([sid], dtype=np.int64),
        }

    u = cat_fn(true_age)["positions_au"][0]
    u = u / np.linalg.norm(u)
    ra_t = float(np.degrees(np.arctan2(u[1], u[0])))
    dec_t = float(np.degrees(np.arcsin(u[2])))
    plate = PlateSolution(
        wcs=_tan_wcs(ra_t, dec_t, scale, nx, ny), source="mock", width=nx, height=ny
    )
    px, py = plate.wcs.world_to_pixel(SkyCoord(ra_t, dec_t, unit="deg"))
    cen = np.array([[float(px) + offset_px, float(py)]])
    return plate, cen, cat_fn, sid


def test_drift_date_recovers_injected_negative_age():
    """A single fast-moving star dates the plate by drift: the scan minimum must
    land on the injected NEGATIVE epoch (an old plate) to <1 yr, with a finite
    residual-curvature sigma. This is the F12 chronometer on one star."""
    true_age = -48.5  # off-grid, decades before the catalog epoch
    plate, cen, cat_fn, _sid = _drift_scene(true_age)
    grid = np.arange(-75.0, 25.0 + 1e-9, 0.5)
    d = drift_date([(plate, cen, "synth")], grid, cat_fn, threshold_arcsec=3.0)
    assert d["ok"] and d["mode"] == "single-star drift"
    assert abs(d["age_hat_yr"] - true_age) < 1.0
    assert d["best_sep_arcsec"] < 3.0
    assert np.isfinite(d["sigma_age_yr"]) and d["sigma_age_yr"] > 0


def test_drift_date_guard_fires_on_starless_field():
    """When no catalogued star drifts near a detection, the guard must refuse a
    date (ok:False) rather than report a spurious minimum."""
    plate, _cen, cat_fn, _sid = _drift_scene(-48.5)
    far_detection = np.array([[123.0, 5.0]])  # nowhere near the star's swept track
    grid = np.arange(-75.0, 25.0 + 1e-9, 0.5)
    d = drift_date(
        [(plate, far_detection, "synth")], grid, cat_fn, threshold_arcsec=3.0
    )
    assert d["ok"] is False and "no reliable drift date" in d["message"]


def test_negative_age_catalog_propagation_is_linear():
    """Propagation must handle NEGATIVE ages: positions are linear in age, so the
    -50 yr state equals the epoch state minus 50x the 1 yr velocity. Kills a
    sign/abs bug that would break dating anything before 2016."""
    c0 = load_aged_catalog(REAL_CSV, 0.0, rv_fill_kms=0.0)["positions_au"]
    c1 = load_aged_catalog(REAL_CSV, 1.0, rv_fill_kms=0.0)["positions_au"]
    cm = load_aged_catalog(REAL_CSV, -50.0, rv_fill_kms=0.0)["positions_au"]
    vel = c1 - c0  # au/yr
    assert np.allclose(cm, c0 - 50.0 * vel, rtol=1e-9, atol=1e-6)
    assert np.max(np.linalg.norm(cm - c0, axis=1)) > 0  # motion is real


# --- dense-field false-minimum fix (static-star exclusion) ------------------


def _decoy_scene(
    true_age=-50.0,
    false_age=20.0,
    pmra=8.0,
    dist_pc=3.0,
    sid=900123,
    decoy_sid=555000,
    ra0=150.0,
    dec0=20.0,
    scale=2.0,
    nx=600,
    ny=600,
):
    """A Barnard-style trap: one fast mover, plus a STATIC decoy star sitting
    exactly where the mover's track crosses at a WRONG (false) epoch, closer than
    the mover ever sits to its own true-epoch blob.

    Returns (plate, centroids, cat_fn, cone). Without the cone the drift scan is
    fooled onto false_age (the decoy wins); with the cone (a full-depth catalog
    listing the decoy at its STATIC position) the decoy centroid is masked and
    the true_age is recovered. Mirrors the real POSS Barnard plates.
    """

    def cat_fn(a):
        ra = ra0 + a * pmra / 3600.0 / np.cos(np.radians(dec0))
        u = radec_to_unit(deg_to_rad(ra), deg_to_rad(dec0))
        return {
            "positions_au": (u * dist_pc * AU_PER_PC).reshape(1, 3),
            "source_id": np.array([sid], dtype=np.int64),
        }

    def _sky(a):
        u = cat_fn(a)["positions_au"][0]
        u = u / np.linalg.norm(u)
        return float(np.degrees(np.arctan2(u[1], u[0]))), float(
            np.degrees(np.arcsin(u[2]))
        )

    rac, decc = _sky((true_age + false_age) / 2.0)  # centre between the epochs
    plate = PlateSolution(
        wcs=_tan_wcs(rac, decc, scale, nx, ny), source="mock", width=nx, height=ny
    )

    def _pix(a, off):
        ra, dec = _sky(a)
        px, py = plate.wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
        return [float(px) + off, float(py)]

    true_blob = _pix(true_age, 0.4)  # real detection, small residual
    decoy = _pix(false_age, 0.1)  # unrelated field star, even closer
    cen = np.array([true_blob, decoy])

    u_decoy = cat_fn(false_age)["positions_au"][0]
    u_decoy = u_decoy / np.linalg.norm(u_decoy)
    cone = {
        "positions_au": u_decoy.reshape(1, 3),  # STATIC (catalog-epoch) position
        "source_id": np.array([decoy_sid], dtype=np.int64),
    }
    return plate, cen, cat_fn, cone


def test_drift_date_static_star_exclusion_rejects_decoy():
    """The dense-field fix: a mover's track passes a STATIC field star closer, at
    a false epoch, than it sits to its own true blob. Without the cone the scan is
    fooled onto the false epoch; feeding the full-depth cone masks the cataloged
    decoy so the TRUE epoch is recovered. This is the Barnard 2035->1950/1991
    fix in miniature."""
    plate, cen, cat_fn, cone = _decoy_scene()
    grid = np.arange(-75.0, 25.0 + 1e-9, 0.5)

    off = drift_date([(plate, cen, "synth")], grid, cat_fn)
    assert off["ok"] and off["age_hat_yr"] > 10.0  # fooled onto the false +20 min

    on = drift_date([(plate, cen, "synth")], grid, cat_fn, cone_fn=lambda p: cone)
    assert on["ok"] and abs(on["age_hat_yr"] - (-50.0)) < 1.0  # decoy masked
    assert on["best_sep_arcsec"] < 3.0


def test_drift_date_default_threshold_rejects_unreliable_field():
    """The reliability guard must fire at the DEFAULT threshold (3 arcsec): a
    mover whose closest approach to any detection is ~10 arcsec is NOT a date.
    Calls drift_date WITHOUT threshold_arcsec so it pins the 3.0 default -- a
    mutant that widened it (3.0 -> 300) would wrongly accept this field."""
    # offset 5 px x 2 arcsec/px = 10 arcsec closest approach (never within 3").
    plate, cen, cat_fn, _sid = _drift_scene(-40.0, offset_px=5.0)
    grid = np.arange(-75.0, 25.0 + 1e-9, 0.5)
    d = drift_date([(plate, cen, "synth")], grid, cat_fn)  # DEFAULT threshold
    assert d["ok"] is False and "no reliable drift date" in d["message"]


def test_drift_date_sigma_is_grid_invariant_and_physical():
    """The reported sigma must be the physical noise-propagated value
    sigma_centroid/omega -- grid-INVARIANT (the old curvature sigma swung ~3x
    with the step). Same scene at 0.5 and 0.1 yr steps must give the same sigma,
    and it must match sigma_centroid_px * scale / omega."""
    plate, cen, cat_fn, _sid = _drift_scene(-40.0, pmra=4.0, pmdec=-3.0, scale=2.0)
    d_coarse = drift_date(
        [(plate, cen, "synth")], np.arange(-75, 25 + 1e-9, 0.5), cat_fn
    )
    d_fine = drift_date([(plate, cen, "synth")], np.arange(-75, 25 + 1e-9, 0.1), cat_fn)
    assert (
        abs(d_coarse["sigma_age_yr"] - d_fine["sigma_age_yr"]) < 1e-3
    )  # grid-invariant
    omega = np.hypot(4.0, 3.0)  # total proper motion, arcsec/yr
    expected = 0.3 * 2.0 / omega  # sigma_centroid_px * scale / omega
    assert abs(d_fine["sigma_age_yr"] - expected) < 0.02
