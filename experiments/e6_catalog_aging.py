"""E6 — Catalog aging (THE HEADLINE figure).

Maps Monte Carlo navigation error over a grid of (catalog age x sensor
precision) and shows three regions: the catalog-aging-dominated region, the
epoch-parallax-floor region (the age-0 error the sampled catalog already
carries), and the crossover curve between them.

The truth wall, upheld: TRUTH samples a per-trial true sky (E6a), ages it with
the Spec-10 truth propagator, and generates the measurements. The NAVIGATOR
ages its PUBLIC catalog with the Spec-10 nav propagator and E1's unweighted
Gauss-Newton solver, reading ONLY the aged catalog positions + the measurement
vector — never any sampled-truth array (the E6a forward advisory). Pair
selection is from the NAV positions (required: truth is now per-trial (T,N,3)
and cannot feed select_pairs). This experiment's v1 does NOT compute a CRLB
overlay; the age-0-with-catalog-covariance baseline is realized EMPIRICALLY by
the sampled parallax scatter (~8.3 au at 1 pc / 20 stars).

Run:  python -m experiments.e6_catalog_aging   (writes results/ npz + PNG)
Do NOT expect an aging-aware navigator here — an age-inflated W is a separate
future card, flagged not implemented.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from experiments.e1_crlb_grid import (
    MAX_PAIRS,
    SPACECRAFT_DIR,
    START_OFFSET_AU,
    select_pairs,
)
from galnav.nav.catalog import (
    load_catalog as load_nav_catalog,
    propagate_positions_au as nav_propagate,
    star_velocities_kms as nav_star_velocities_kms,
)
from galnav.nav.estimator import solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sampling import sample_true_skies
from galnav.truth.sky import (
    load_catalog as load_truth_catalog,
    propagate_positions_au as truth_propagate,
)
from galnav.units import AU_PER_PC, arcsec_to_rad
from tests.golden_numbers import SOLVER_MAX_ITERS, SOLVER_STEP_TOL_AU

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"
RESULTS_DIR = REPO_ROOT / "results"

# Grid (plan sections 6/7, with the recorded student ruling + measured
# amendments: 40 & 70 yr added around the ~55 yr knee; sigma extended to
# 60 arcsec so the sensor-limited region above the ~8.3 au epoch floor is on
# the figure). Documented in journal/spec-e6b-aging-experiment.md.
AGES_YR = [0, 5, 10, 20, 40, 50, 70, 100, 150, 200]
SIGMAS_ARCSEC = [0.01, 0.0316, 0.1, 0.316, 1.0, 3.16, 10.0, 20.0, 35.0, 60.0]


def _slice_catalog(catalog, n_stars):
    """Keep the n_stars nearest stars (catalog is parallax-sorted, nearest
    first). Slices every per-star array in the catalog dict.

    catalog: dict from a load_catalog (each value a length-N array).
    n_stars: number of nearest stars to keep (count).
    Returns: a new dict with each array sliced to [:n_stars].
    """
    return {key: value[:n_stars] for key, value in catalog.items()}


def run_e6_cell(
    truth_catalog,
    nav_catalog,
    n_stars,
    dist_pc,
    age_yr,
    sigma_rad,
    n_trials,
    missing_rv_scale_kms,
    rng,
):
    """One (age, sigma) cell: Monte Carlo navigation RMS at one configuration.

    truth_catalog: dict from galnav.truth.sky.load_catalog (raw uncertainties
        included — E6a samples from them).
    nav_catalog: dict from galnav.nav.catalog.load_catalog (public catalog).
    n_stars: use the n nearest stars (count).
    dist_pc: spacecraft distance from the Sun, parsecs.
    age_yr: catalog age for this cell, Julian years (SCALAR — the truth and
        nav propagators' scalar-age branch broadcasts the (T,N,3)/(N,3)
        positions; E6 never uses their array-age branch).
    sigma_rad: per-measurement camera noise, radians.
    n_trials: Monte Carlo trials, solved in one vectorized call (count).
    missing_rv_scale_kms: 1-sigma radial-velocity scale (km/s) truth gives the
        stars with no catalog RV (the navigator assumes 0 for those).
    rng: np.random.Generator — all randomness flows through here.
    Returns: dict with rms_au (float, RMS |estimate - true|, au) plus the exact
        intermediate arrays used, so the wiring is inspectable: measured
        ((n_trials, P) angles, rad), solved ((n_trials, 3) au), aged_true_pos
        ((n_trials, n_stars, 3) au), aged_nav_pos ((n_stars, 3) au), pairs
        ((P, 2) indices), plan_pos ((3,) au), starts ((n_trials, 3) au).
    """
    truth = _slice_catalog(truth_catalog, n_stars)
    nav = _slice_catalog(nav_catalog, n_stars)
    # Public mission-design position the navigator is allowed to hold; truth
    # realizes it exactly (no execution error, as in E1).
    plan_pos = SPACECRAFT_DIR * dist_pc * AU_PER_PC
    true_pos = plan_pos

    # NAV: age the PUBLIC catalog with its cataloged central kinematics; a
    # missing RV is assumed 0 (rv_fill_kms=0.0). Pair selection is from these
    # nav positions.
    nav_vel = nav_star_velocities_kms(nav, rv_fill_kms=0.0)
    aged_nav_pos = nav_propagate(nav["star_pos_au"], nav_vel, age_yr)
    pairs = select_pairs(aged_nav_pos, plan_pos, MAX_PAIRS, rng)
    starts = np.broadcast_to(plan_pos + START_OFFSET_AU, (n_trials, 3))

    # TRUTH: sample T true skies (E6a), age each by the cell's age.
    epoch_pos, epoch_vel = sample_true_skies(truth, n_trials, rng, missing_rv_scale_kms)
    aged_true_pos = truth_propagate(epoch_pos, epoch_vel, age_yr)

    # Measurements: each trial's own aged sky, one fixed observer.
    measured = observed_pair_angles(aged_true_pos, plan_pos, pairs, sigma_rad, rng)
    # Solve against the aged NAV catalog only.
    solved, _ = solve_position(
        measured, aged_nav_pos, pairs, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )

    rms_au = float(np.sqrt(np.mean(np.sum((solved - true_pos) ** 2, axis=1))))
    return {
        "rms_au": rms_au,
        "measured": measured,
        "solved": solved,
        "aged_true_pos": aged_true_pos,
        "aged_nav_pos": aged_nav_pos,
        "pairs": pairs,
        "plan_pos": plan_pos,
        "starts": np.asarray(starts),
    }


def run_e6_grid(
    truth_catalog,
    nav_catalog,
    ages_yr,
    sigmas_rad,
    n_stars,
    dist_pc,
    n_trials,
    missing_rv_scale_kms,
    seed,
):
    """Sweep the (age x sigma) grid. Loops over CELLS (independent
    configurations); within each cell all trials are vectorized.

    truth_catalog, nav_catalog: dicts from the two load_catalog functions.
    ages_yr: catalog ages, Julian years (the first should be 0, the baseline).
    sigmas_rad: per-measurement camera noise levels, radians.
    n_stars: nearest stars to use (count).
    dist_pc: spacecraft distance, parsecs.
    n_trials: Monte Carlo trials per cell (count).
    missing_rv_scale_kms: truth's missing-RV scale, km/s.
    seed: integer seed spawned into one child stream per cell (each cell
        independently reproducible from the one seed).
    Returns: rms_au array of shape (len(ages_yr), len(sigmas_rad)), au.
    """
    shape = (len(ages_yr), len(sigmas_rad))
    rms = np.zeros(shape)
    cell_rngs = np.random.default_rng(seed).spawn(rms.size)
    for a, age_yr in enumerate(ages_yr):
        for s, sigma_rad in enumerate(sigmas_rad):
            cell = run_e6_cell(
                truth_catalog,
                nav_catalog,
                n_stars=n_stars,
                dist_pc=dist_pc,
                age_yr=float(age_yr),
                sigma_rad=sigma_rad,
                n_trials=n_trials,
                missing_rv_scale_kms=missing_rv_scale_kms,
                rng=cell_rngs[a * len(sigmas_rad) + s],
            )
            rms[a, s] = cell["rms_au"]
    return rms


def crossover_ages(ages_yr, rms_au):
    """Age at which aging error equals the age-0 error in quadrature.

    Definition (ratification item (y)): the crossover is where
    rms(age, sigma) = sqrt(2) * rms(0, sigma) — the age at which the aging
    contribution equals the age-0 (sensor + epoch-catalog) contribution added
    in quadrature. Interpolated LINEARLY IN LOG-AGE between the two bracketing
    POSITIVE ages. Sigma rows whose curve never reaches the target within the
    age range, OR reaches it before the first positive age, are CENSORED (NaN)
    — no extrapolation.

    ages_yr: (A,) catalog ages, Julian years; ages_yr[0] must be 0 (baseline).
    rms_au: (A, S) RMS navigation error, au.
    Returns: (S,) crossover age per sigma, Julian years (NaN where censored).
    """
    ages = np.asarray(ages_yr, dtype=float)
    rms = np.asarray(rms_au, dtype=float)
    target = np.sqrt(2.0) * rms[0]  # (S,)
    out = np.full(rms.shape[1], np.nan)
    positive = ages > 0
    log_age = np.log(ages[positive])
    for s in range(rms.shape[1]):
        col = rms[positive, s]
        reached = np.nonzero(col >= target[s])[0]
        if reached.size == 0 or reached[0] == 0:
            continue  # never crosses, or crosses before the first positive age
        k = reached[0]
        x0, x1 = log_age[k - 1], log_age[k]
        y0, y1 = col[k - 1], col[k]
        out[s] = float(np.exp(x0 + (target[s] - y0) * (x1 - x0) / (y1 - y0)))
    return out


def save_outputs(
    rms_au,
    ages_yr,
    sigmas_rad,
    n_trials,
    seed,
    star_count,
    dist_pc,
    missing_rv_scale_kms,
    out_dir,
):
    """Write every plotted array + parameters to a timestamped .npz.

    rms_au: (A, S) RMS navigation error, au.
    ages_yr: (A,) ages, Julian years. sigmas_rad: (S,) noise levels, radians.
    n_trials, seed, star_count: ints. dist_pc: parsecs.
    missing_rv_scale_kms: km/s. out_dir: directory to write into (Path/str).
    Returns: Path to the written .npz (the figure is regenerable from it
        alone via replot_from_npz).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e6_catalog_aging_{stamp}.npz"
    np.savez(
        path,
        rms_au=np.asarray(rms_au),
        ages_yr=np.asarray(ages_yr, dtype=float),
        sigmas_rad=np.asarray(sigmas_rad, dtype=float),
        n_trials=n_trials,
        seed=seed,
        star_count=star_count,
        dist_pc=dist_pc,
        missing_rv_scale_kms=missing_rv_scale_kms,
        spacecraft_dir=SPACECRAFT_DIR,
        start_offset_au=START_OFFSET_AU,
    )
    return path


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E6 figure from a saved .npz ALONE (no Monte Carlo).

    npz_path: path to an .npz written by save_outputs.
    out_png: optional path to also save a PNG.
    Returns: the matplotlib Figure — a filled contour of RMS over
        (age [x, symlog], sigma [y, log]) with the crossover curve overlaid
        where it exists and the epoch-parallax floor annotated.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = np.load(npz_path)
    rms = data["rms_au"]  # (A, S)
    ages = data["ages_yr"]
    sig_arcsec = data["sigmas_rad"] / arcsec_to_rad(1.0)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    age_grid, sig_grid = np.meshgrid(ages, sig_arcsec, indexing="ij")
    cf = ax.contourf(age_grid, sig_grid, rms)
    fig.colorbar(cf, ax=ax, label="RMS position error, au")
    ax.set_xscale("symlog", linthresh=5.0)
    ax.set_yscale("log")
    ax.set_xlabel("catalog age, Julian years")
    ax.set_ylabel("sensor noise sigma, arcsec")

    xover = crossover_ages(ages, rms)
    finite = np.isfinite(xover)
    if finite.any():
        ax.plot(
            xover[finite],
            sig_arcsec[finite],
            "w-o",
            lw=2,
            ms=4,
            label=r"crossover: rms = $\sqrt{2}\,$rms(age 0)",
        )
        ax.legend(loc="upper left", fontsize=8)

    floor = float(rms[0].min())
    ax.set_title(
        f"E6 — navigation error vs catalog age and sensor precision\n"
        f"epoch parallax floor ~ {floor:.1f} au (catalog-limited below the crossover)"
    )
    fig.tight_layout()
    if out_png is not None:
        fig.savefig(out_png, dpi=150)
    return fig


def main():
    """Run the full E6 grid and write results/ npz + PNG."""
    truth_catalog = load_truth_catalog(CATALOG_CSV)
    nav_catalog = load_nav_catalog(CATALOG_CSV)
    sigmas_rad = [arcsec_to_rad(s) for s in SIGMAS_ARCSEC]
    n_trials, seed = 500, 42

    rms = run_e6_grid(
        truth_catalog,
        nav_catalog,
        ages_yr=AGES_YR,
        sigmas_rad=sigmas_rad,
        n_stars=20,
        dist_pc=1.0,
        n_trials=n_trials,
        missing_rv_scale_kms=30.0,
        seed=seed,
    )
    path = save_outputs(
        rms,
        AGES_YR,
        sigmas_rad,
        n_trials=n_trials,
        seed=seed,
        star_count=20,
        dist_pc=1.0,
        missing_rv_scale_kms=30.0,
        out_dir=RESULTS_DIR,
    )
    replot_from_npz(path, out_png=path.with_suffix(".png"))
    xover = crossover_ages(np.asarray(AGES_YR, dtype=float), rms)
    print(f"wrote {path.name} and .png")
    print(f"epoch parallax floor (age 0, finest sensor): {rms[0].min():.2f} au")
    print(f"crossover ages per sigma (yr): {np.round(xover, 1)}")


if __name__ == "__main__":
    main()
