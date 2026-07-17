"""Test for gui.age.estimate_age -- the estimate-the-catalog-age mode.

Full chain on two synthetic frames rendered at a known true age: the chi2 scan
must find that age, the parabola curvature must bracket it, and the curve must
be convex at the minimum.
"""

import numpy as np

from gui.age import estimate_age
from gui.centroids import find_centroids
from gui.locate import (
    LineOfPosition,
    identify_in_frame,
    load_aged_catalog,
    measured_direction,
)
from tests_gui.synth import BARNARD_ID, PROXIMA_ID, REAL_CSV, Scene, build_synthetic

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
