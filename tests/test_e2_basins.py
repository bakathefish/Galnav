"""Acceptance tests for the E2 convergence-basin harness.

AI-authored under the build-night ratification-pending pattern (user granted
full build authority 2026-07-16; E2 ruling = OPTION A, per-trial failure
isolation, ratification item flagged). E2 asks a lost-in-space question: from
how far can the initial guess be displaced from the true spacecraft position
and STILL have the Gauss-Newton navigator converge back to it? Each cell
displaces the start by a fixed magnitude in many ISOTROPIC random directions
and measures the CAPTURE FRACTION (fraction of directions that converge).

Zero measurement noise throughout: the basin is a property of the residual
landscape, so the only randomness is the displacement DIRECTION. The true
position is then an exact residual-zero fixed point, and a trial either
converges to it (capture) or lands elsewhere / diverges (escape).

Goldens: reuses SOLVER_RECOVERY_TOL_AU (the capture radius), SOLVER_STEP_TOL_AU
and SOLVER_MAX_ITERS (the DEPLOYED solver's own step tolerance and iteration
budget — E2 characterises the shipped navigator, not a bespoke one). ONE new
golden, E2_ISOTROPY_M4_TOL (authorized override #10), gates the isotropy
statistical test (T5).
"""

import numpy as np

from experiments.e1_crlb_grid import CATALOG_CSV, START_OFFSET_AU
from experiments.e2_convergence_basins import (
    _captured,
    capture_fraction_cell,
    compute,
    fifty_percent_displacement,
    isotropic_directions,
    replot_from_npz,
    run_grid,
    save_outputs,
)
from galnav.nav.catalog import load_catalog as load_nav_catalog
from galnav.truth.sky import load_catalog, star_positions_au
from galnav.units import AU_PER_PC
from tests.golden_numbers import E2_ISOTROPY_M4_TOL, SOLVER_RECOVERY_TOL_AU

# Real catalogue, loaded once. TRUTH positions generate the (noise-free)
# measurements; the public NAV positions feed the solver (truth wall, as E1).
STARS = star_positions_au(load_catalog(CATALOG_CSV))
NAV_STARS = load_nav_catalog(CATALOG_CSV)["star_pos_au"]


def test_start_offset_anchor_off_grid_captures():
    """T1 (off-grid anchor): the E1 good-start displacement always converges.

    |START_OFFSET_AU| = 100*sqrt(3) ~ 173 au is E1's proven good start. It is
    OFF the parsec-scale displacement grid (0.1 pc = 20,626 au is already
    ~120x larger), so it is not a grid column — it is the sanity anchor that
    ties this harness back to E1: from 173 au every isotropic direction sits
    deep inside the basin, so the capture fraction must be exactly 1.0. A
    harness that mis-wired the solve or the capture test would drop below 1.
    """
    disp_au = float(np.linalg.norm(START_OFFSET_AU))
    f = capture_fraction_cell(
        STARS,
        NAV_STARS,
        n_stars=20,
        dist_pc=1.0,
        disp_au=disp_au,
        n_trials=64,
        rng=np.random.default_rng(0),
    )
    assert f == 1.0


def test_capture_weakly_decreases_with_displacement():
    """T2 (monotonicity): more displacement never captures MORE, per count.

    The basin is a connected neighbourhood of the truth: pushing the start
    farther can only lose directions, never gain them. So for every star
    count the capture fraction at the smallest displacement is >= that at the
    largest. A sign error or a basin that grew with distance would break this.
    """
    counts = [5, 20]
    disps_au = np.array([1.0, 40.0]) * AU_PER_PC  # smallest, largest (pc scale)
    cap = run_grid(
        STARS,
        NAV_STARS,
        counts,
        disps_au,
        n_trials=64,
        rng=np.random.default_rng(1),
    )
    for row in cap:  # one row per star count
        assert row[0] >= row[-1]


def test_basin_is_finite_at_small_count():
    """T2b (headline pin): the basin is FINITE — far starts escape.

    Parameter-free and tolerance-free (strict inequalities only). At the
    smallest star count, capture at the largest displacement is strictly below
    capture at the smallest AND strictly below 1.0: there is a wall the solver
    cannot cross, which is the whole point of E2. A basin that never closed
    (capture 1.0 everywhere) would be physically wrong yet still pass the weak
    monotonicity test above.
    """
    disps_au = np.array([1.0, 60.0]) * AU_PER_PC  # inside vs far outside the basin
    cap = run_grid(
        STARS, NAV_STARS, [5], disps_au, n_trials=64, rng=np.random.default_rng(11)
    )
    near, far = cap[0, 0], cap[0, -1]
    assert far < near
    assert far < 1.0


def test_captured_requires_finite_and_within_tol():
    """T3 (capture predicate — BOTH clauses): finite AND within tolerance.

    The two clauses guard different failure modes. The finiteness clause
    rejects diverged / NaN trials. The distance clause rejects the
    finite-but-WRONG stationary points Gauss-Newton falls into near the basin
    edge (the reviewer measured a real ~30% finite-but-wrong population there);
    without it those would be miscounted as captures and the basin would look
    far larger than it is.
    """
    true = np.array([1.0, 2.0, 3.0])
    assert _captured(true.copy(), true, SOLVER_RECOVERY_TOL_AU)  # exact hit
    assert not _captured(true + 10.0, true, SOLVER_RECOVERY_TOL_AU)  # finite, wrong
    assert not _captured(np.array([np.nan, 2.0, 3.0]), true, SOLVER_RECOVERY_TOL_AU)
    assert not _captured(np.array([np.inf, 2.0, 3.0]), true, SOLVER_RECOVERY_TOL_AU)


def test_directions_are_unit_and_isotropic():
    """T5 (isotropy guard): unit vectors, spherically uniform (4th moment).

    The construction MUST be a normalised standard-normal, not a normalised
    uniform cube. Isotropy discriminator: for a spherically-uniform draw the
    projection onto ANY unit vector is identically Uniform(-1, 1), so the fourth
    moment E[(u.v)^4] = 1/5 for every v; the coordinate-axis and body-diagonal
    4th moments must therefore agree. The 2nd moment does NOT discriminate --
    BOTH the sphere and the normalised cube give a projection variance ~1/3, so
    an axis-vs-diagonal VARIANCE test (the first draft's) passes on the buggy
    cube. Measured (n = 200,000): the correct draw gives |m4_axis - m4_diag| ~
    2e-4 at this seed (<= ~2e-3 over 200 seeds), while a normalised uniform cube
    gives ~0.033 -- the E2_ISOTROPY_M4_TOL gate sits cleanly between them.
    """
    d = isotropic_directions(200_000, np.random.default_rng(3))
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)
    axis = np.array([1.0, 0.0, 0.0])
    diag = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
    m4_axis = ((d @ axis) ** 4).mean()
    m4_diag = ((d @ diag) ** 4).mean()
    assert abs(m4_axis - m4_diag) < E2_ISOTROPY_M4_TOL


def test_deterministic_capture_grid():
    """T4 (determinism): same seed -> bit-identical capture grid.

    All randomness flows through the seeded generator and the fixed direction
    draw order, so two runs with the same seed must agree exactly.
    """
    counts = [5, 20]
    disps_au = np.array([2.0, 10.0]) * AU_PER_PC
    a = run_grid(STARS, NAV_STARS, counts, disps_au, 48, np.random.default_rng(7))
    b = run_grid(STARS, NAV_STARS, counts, disps_au, 48, np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_fifty_percent_degenerate_field_guard():
    """T6a (degenerate guard): an all-captured or all-failed row has no 0.5.

    The 0.5-crossing is undefined when the field never crosses 0.5. The locus
    finder must return NaN rather than extrapolate a fake basin edge.
    """
    disps = np.array([1.0, 2.0, 3.0])
    assert np.isnan(fifty_percent_displacement(np.ones(3), disps))
    assert np.isnan(fifty_percent_displacement(np.zeros(3), disps))
    # a genuine high->low crossing returns a value strictly inside the bracket
    x = fifty_percent_displacement(np.array([1.0, 0.0]), np.array([2.0, 8.0]))
    assert 2.0 < x < 8.0


def test_outputs_and_replot_from_npz(tmp_path):
    """T6b (outputs): npz carries every plotted array; replot uses it alone.

    The blessed-results rule requires the figure be regenerable from the saved
    arrays with no recompute. A tiny real grid exercises the full save->replot
    path including the degenerate-field contour guard.
    """
    d = compute(
        star_counts=[5, 20],
        disps_pc=[0.1, 2.0, 100.0],
        n_trials=48,
        seed=42,
    )
    path = save_outputs(d, out_dir=tmp_path)
    with np.load(path, allow_pickle=True) as z:
        for key in ("capture_fraction", "star_counts", "disps_pc", "seed", "n_trials"):
            assert key in z.files
    png = replot_from_npz(path)
    assert png.exists()
