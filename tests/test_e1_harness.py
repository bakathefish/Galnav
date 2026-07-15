"""E1 harness acceptance test: the grid machinery behind the first
research figure.

E1's scientific pass criterion (project plan): across every cell of the
(spacecraft distance x star count x camera noise) grid, the Monte Carlo
RMS position error must track the CRLB theory prediction within
E1_CRLB_TRACK_FACTOR in either direction. These tests run a small but
real corner of that grid through the same harness the full experiment
uses -- if the harness lies, the figure lies, so the harness gets an
acceptance test like everything else.
"""

from pathlib import Path

import numpy as np

from experiments.e1_crlb_grid import run_cell, select_pairs
from galnav.truth.sky import load_catalog, star_positions_au
from tests.golden_numbers import E1_CRLB_TRACK_FACTOR, RAD_ARCSEC

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)


def _stars_all():
    return star_positions_au(load_catalog(CATALOG_CSV))


def test_pair_selection_excludes_close_pairs_and_caps_count():
    # The 61 Cygni lesson, institutionalized: no near-coincident pairs may
    # ever reach the solver, and the pair count must respect the memory cap.
    stars = _stars_all()[:20]
    obs = np.array([1.0e5, -2.0e5, 3.0e5])
    pairs = select_pairs(stars, obs, max_pairs=50, rng=np.random.default_rng(0))
    assert len(pairs) <= 50
    d = stars - obs
    u = d / np.linalg.norm(d, axis=1)[:, None]
    ang = np.arctan2(
        np.linalg.norm(np.cross(u[pairs[:, 0]], u[pairs[:, 1]]), axis=1),
        np.sum(u[pairs[:, 0]] * u[pairs[:, 1]], axis=1),
    )
    assert np.all(ang > 0.01)  # exclusion threshold, radians (setup value)


def test_grid_cells_track_crlb_within_factor():
    # Four real grid cells spanning near/far spacecraft and few/many
    # stars: the harness's Monte Carlo RMS must track its CRLB prediction
    # within the plan's factor. Catches biased solving, wrong noise
    # scaling, or a harness that computes theory and practice at
    # different geometries.
    stars = _stars_all()
    sigma_rad = 1.0 / RAD_ARCSEC  # 1 arcsec (setup value)
    for dist_pc in (1.0, 10.0):
        for n_stars in (10, 50):
            cell = run_cell(
                stars,
                n_stars=n_stars,
                dist_pc=dist_pc,
                sigma_rad=sigma_rad,
                n_trials=200,
                rng=np.random.default_rng(0),
            )
            ratio = cell["rms_au"] / cell["crlb_au"]
            assert 1.0 / E1_CRLB_TRACK_FACTOR < ratio < E1_CRLB_TRACK_FACTOR, (
                f"cell D={dist_pc} N={n_stars}: ratio {ratio}"
            )


def test_cell_results_are_reproducible():
    # Same seed, same cell, byte-identical numbers -- every figure must be
    # regenerable exactly (project rule).
    stars = _stars_all()
    kwargs = dict(n_stars=15, dist_pc=5.0, sigma_rad=1.0 / RAD_ARCSEC, n_trials=100)
    a = run_cell(stars, rng=np.random.default_rng(3), **kwargs)
    b = run_cell(stars, rng=np.random.default_rng(3), **kwargs)
    assert a["rms_au"] == b["rms_au"]
    assert a["crlb_au"] == b["crlb_au"]
