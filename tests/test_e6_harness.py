"""E6b acceptance tests: the catalog-aging experiment harness (THE HEADLINE).

E6 maps navigation error over (catalog age, sensor precision). Truth samples
a per-trial true sky (E6a), ages it, and generates measurements; the
navigator ages its PUBLIC catalog and solves against that alone (the E1-swap
wall). These smoke tests run a tiny corner of the real grid so the harness is
trustworthy before the full grid runs.

Tolerances come only from tests/golden_numbers.py: SOLVER_RECOVERY_TOL_AU
(T1) and E6_AGING_SMOKE_MIN_FACTOR (T2/T3, authorized override #7). T4/T5 are
exact wiring/output checks needing none.

AI-authored under the recorded ratification-pending exception (items x/y/z).
"""

from pathlib import Path

import numpy as np

from experiments.e6_catalog_aging import (
    crossover_ages,
    replot_from_npz,
    run_e6_cell,
    run_e6_grid,
    save_outputs,
)
from galnav.nav.catalog import load_catalog as load_nav_catalog
from galnav.nav.estimator import solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog as load_truth_catalog
from galnav.units import arcsec_to_rad, mas_to_rad
from tests.golden_numbers import (
    E6_AGING_SMOKE_MIN_FACTOR,
    SOLVER_MAX_ITERS,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_STEP_TOL_AU,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)


def _truth():
    return load_truth_catalog(CATALOG_CSV)


def _nav():
    return load_nav_catalog(CATALOG_CSV)


def _zeroed_truth():
    # A truth catalog with every error column zeroed: sampling then returns
    # the central values exactly, so the true sky equals the nav catalog
    # (up to the two sides' independent float paths).
    tc = dict(_truth())
    for key in (
        "parallax_error_mas",
        "pmra_error_mas_yr",
        "pmdec_error_mas_yr",
        "rv_error_kms",
    ):
        tc[key] = np.zeros_like(tc[key])
    return tc


def test_t1_perfect_catalog_null():
    # Perfect catalog: errors zeroed, missing RVs filled IDENTICALLY with 0.0
    # on both sides (missing_rv_scale = 0), and a perfect camera (sigma = 0).
    # Aging then costs nothing: at every age the solver must recover the true
    # position to the machine-precision solver gate. Any wiring/sign/frame bug
    # lands orders past 1e-8 au. (Bitwise equality FALSE-fails here because
    # truth and nav age with their INDEPENDENT velocity builders; the
    # recovery tolerance is the honest gate.)
    tc, nc = _zeroed_truth(), _nav()
    for age in (0.0, 100.0):
        cell = run_e6_cell(
            tc,
            nc,
            n_stars=20,
            dist_pc=1.0,
            age_yr=age,
            sigma_rad=0.0,
            n_trials=6,
            missing_rv_scale_kms=0.0,
            rng=np.random.default_rng(42),
        )
        err = float(np.max(np.linalg.norm(cell["solved"] - cell["plan_pos"], axis=1)))
        assert err < SOLVER_RECOVERY_TOL_AU


def test_t2_aging_hurts():
    # Realistic sampling on: at a fine sensor (10 mas) the 100-yr-aged error
    # must exceed the age-0 error by at least the smoke factor. Same seed for
    # both cells, so the two see the SAME sampled skies and only the age
    # differs -- isolating aging. (Measured seed-42 ratio ~2.17; see journal.)
    tc, nc = _truth(), _nav()
    sigma = mas_to_rad(10.0)
    c0 = run_e6_cell(
        tc,
        nc,
        n_stars=20,
        dist_pc=1.0,
        age_yr=0.0,
        sigma_rad=sigma,
        n_trials=40,
        missing_rv_scale_kms=30.0,
        rng=np.random.default_rng(42),
    )
    c100 = run_e6_cell(
        tc,
        nc,
        n_stars=20,
        dist_pc=1.0,
        age_yr=100.0,
        sigma_rad=sigma,
        n_trials=40,
        missing_rv_scale_kms=30.0,
        rng=np.random.default_rng(42),
    )
    assert c100["rms_au"] / c0["rms_au"] > E6_AGING_SMOKE_MIN_FACTOR


def test_t3_sensor_dominated_flank():
    # At a coarse sensor (60 arcsec) the cell is sensor-limited: 5 yr of aging
    # must NOT reach the smoke factor. Fine cells degrade first, coarse cells
    # last -- the qualitative ordering the headline claims.
    tc, nc = _truth(), _nav()
    sigma = arcsec_to_rad(60.0)
    c0 = run_e6_cell(
        tc,
        nc,
        n_stars=20,
        dist_pc=1.0,
        age_yr=0.0,
        sigma_rad=sigma,
        n_trials=40,
        missing_rv_scale_kms=30.0,
        rng=np.random.default_rng(42),
    )
    c5 = run_e6_cell(
        tc,
        nc,
        n_stars=20,
        dist_pc=1.0,
        age_yr=5.0,
        sigma_rad=sigma,
        n_trials=40,
        missing_rv_scale_kms=30.0,
        rng=np.random.default_rng(42),
    )
    assert c5["rms_au"] / c0["rms_au"] < E6_AGING_SMOKE_MIN_FACTOR


def test_t4_measurement_provenance():
    # E1-swap-style wiring proof, adapted to E6's per-trial truth sky:
    # (a) perturbing ONE trial's sampled true sky moves ONLY that trial's
    #     measurements; (b) perturbing the nav catalog moves the solution while
    #     the measurements are untouched.
    tc, nc = _truth(), _nav()
    sigma = arcsec_to_rad(1.0)
    cell = run_e6_cell(
        tc,
        nc,
        n_stars=8,
        dist_pc=1.0,
        age_yr=50.0,
        sigma_rad=sigma,
        n_trials=4,
        missing_rv_scale_kms=30.0,
        rng=np.random.default_rng(0),
    )
    at, an = cell["aged_true_pos"], cell["aged_nav_pos"]
    pairs, plan, starts = cell["pairs"], cell["plan_pos"], cell["starts"]

    # (a) truth -> measurements (per trial)
    m0 = observed_pair_angles(at, plan, pairs, sigma, np.random.default_rng(99))
    at_bad = at.copy()
    at_bad[1, 0] = at_bad[1, 0] + np.array([1000.0, 0.0, 0.0])  # au, trial 1, star 0
    m1 = observed_pair_angles(at_bad, plan, pairs, sigma, np.random.default_rng(99))
    assert not np.array_equal(m1[1], m0[1])  # trial 1 moved
    assert np.array_equal(
        np.delete(m1, 1, axis=0), np.delete(m0, 1, axis=0)
    )  # rest same

    # (b) nav positions -> solution only
    s0 = solve_position(m0, an, pairs, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS)[0]
    an_bad = an.copy()
    an_bad[0] = an_bad[0] + np.array([1000.0, 0.0, 0.0])  # au
    s1 = solve_position(
        m0, an_bad, pairs, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )[0]
    assert not np.array_equal(s0, s1)


def test_t5_outputs_and_replot(tmp_path):
    # The npz must carry every plotted array + params + seed, and a figure
    # must be regenerable from the npz ALONE (closes the recorded no-replot
    # finding for E6).
    tc, nc = _truth(), _nav()
    ages = [0.0, 50.0]
    sigmas = [mas_to_rad(10.0), arcsec_to_rad(1.0)]
    rms = run_e6_grid(
        tc,
        nc,
        ages_yr=ages,
        sigmas_rad=sigmas,
        n_stars=20,
        dist_pc=1.0,
        n_trials=8,
        missing_rv_scale_kms=30.0,
        seed=42,
    )
    assert rms.shape == (2, 2)

    npz_path = save_outputs(
        rms,
        ages,
        sigmas,
        n_trials=8,
        seed=42,
        star_count=20,
        dist_pc=1.0,
        missing_rv_scale_kms=30.0,
        out_dir=tmp_path,
    )
    data = np.load(npz_path)
    for key in (
        "rms_au",
        "ages_yr",
        "sigmas_rad",
        "n_trials",
        "seed",
        "star_count",
        "dist_pc",
        "missing_rv_scale_kms",
    ):
        assert key in data
    assert np.array_equal(data["rms_au"], rms)

    assert crossover_ages(np.asarray(ages), rms).shape == (2,)

    fig = replot_from_npz(npz_path)
    assert fig is not None and len(fig.axes) >= 1
