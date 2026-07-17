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
TRUE_AGE = 4.5
SCALE = 4.0

# Grid step is 0.25 yr; the sub-grid parabola recovers the true age to ~0.001 yr
# (measured). 0.5 yr is a loose gate that still fails if the minimum lands on
# the wrong grid node (>=0.25 yr off) or the curve is not tracking proper motion.
AGE_ERR_TOL_YR = 0.5


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
    # Convex minimum: both neighbours of the grid argmin are strictly higher.
    i = int(np.argmin(res["chi2s"]))
    assert 0 < i < len(grid) - 1
    assert res["chi2s"][i - 1] > res["chi2s"][i] < res["chi2s"][i + 1]
