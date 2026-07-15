"""E1 — Solver validation + CRLB (the signature figure).

Sweeps the finished instrument over a grid of (spacecraft distance x star
count x camera noise), runs a vectorized Monte Carlo in every cell, and
overlays the measured scatter (points) on the CRLB theory line. Pass
criterion: RMS tracks CRLB within E1_CRLB_TRACK_FACTOR everywhere.

Run:  python -m experiments.e1_crlb_grid
Writes PNG figure + exact plotted arrays (.npz) to results/ with a
timestamp, so the figure is regenerable from the arrays alone.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from galnav.nav.catalog import load_catalog as load_nav_catalog
from galnav.nav.estimator import position_covariance, solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from galnav.units import AU_PER_PC
from tests.golden_numbers import RAD_ARCSEC, SOLVER_MAX_ITERS, SOLVER_STEP_TOL_AU

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"
RESULTS_DIR = REPO_ROOT / "results"

# Experiment parameters (design choices, documented in journal/e1-crlb-grid.md)
MIN_PAIR_SEP_RAD = 0.01  # never feed near-coincident pairs (61 Cygni lesson)
MAX_PAIRS = 2000  # memory cap: 500 trials x 2000 pairs x 3 axes ~ 24 MB
SPACECRAFT_DIR = np.array([0.6, -0.64, 0.48]) / np.linalg.norm([0.6, -0.64, 0.48])
START_OFFSET_AU = np.array([100.0, -100.0, 100.0])  # good-start displacement


def select_pairs(star_pos_au, obs_pos_au, max_pairs, rng):
    """All well-separated unique star pairs, capped for memory.

    star_pos_au: (N, 3) star positions, au.
    obs_pos_au: (3,) observer position, au.
    max_pairs: keep at most this many pairs (uniform random subsample).
    rng: np.random.Generator (used only if subsampling is needed).
    Returns: (P, 2) integer pair indices, every pair separated by more
             than MIN_PAIR_SEP_RAD as seen from obs_pos_au.
    """
    n = len(star_pos_au)
    pairs = np.column_stack(np.triu_indices(n, k=1))
    towards = star_pos_au - obs_pos_au
    unit = towards / np.linalg.norm(towards, axis=1)[:, None]
    u_i, u_j = unit[pairs[:, 0]], unit[pairs[:, 1]]
    angles = np.arctan2(
        np.linalg.norm(np.cross(u_i, u_j), axis=1), np.sum(u_i * u_j, axis=1)
    )
    pairs = pairs[angles > MIN_PAIR_SEP_RAD]
    if len(pairs) > max_pairs:
        pairs = pairs[rng.choice(len(pairs), size=max_pairs, replace=False)]
    return pairs


def run_cell(
    stars_all_au, nav_stars_all_au, n_stars, dist_pc, sigma_rad, n_trials, rng
):
    """One grid cell: Monte Carlo RMS vs CRLB at one configuration.

    Two star arrays are passed so the truth wall stays intact: TRUTH
    positions generate the measurements, the public NAV CATALOG positions
    feed the navigator (solver + CRLB covariance). Today the two arrays are
    bitwise identical, so every number is unchanged; the split makes the
    navigator's dependence on the public catalog explicit rather than
    accidental.

    stars_all_au: (N_catalog, 3) TRUTH star positions, au — used only to
                  generate the measurements (and to pick well-separated
                  pairs, a physical-separation property of the real sky).
    nav_stars_all_au: (N_catalog, 3) public NAV CATALOG star positions, au —
                  the ONLY sky knowledge the solver and covariance see.
    n_stars: use the n nearest stars.
    dist_pc: spacecraft distance from the Sun, parsecs.
    sigma_rad: per-measurement camera noise, radians.
    n_trials: Monte Carlo trials (solved in ONE vectorized call).
    rng: np.random.Generator — all randomness flows through here.
    Returns: dict with rms_au (Monte Carlo RMS position error, au),
             crlb_au (sqrt-trace of the CRLB covariance, au), and measured
             ((n_trials, P) measured pair angles, radians) — the exact
             measurement vector the navigator consumed.
    """
    stars = stars_all_au[:n_stars]
    nav_stars = nav_stars_all_au[:n_stars]
    # The flight PLAN puts the spacecraft here — public mission-design
    # knowledge the navigator is allowed to hold (E2 studies lost-in-space).
    plan_pos = SPACECRAFT_DIR * dist_pc * AU_PER_PC
    # Truth independently realizes the plan exactly (no execution error yet).
    true_pos = plan_pos
    # Nav side sees ONLY: the plan, the catalog stars, and the measurements.
    pairs = select_pairs(stars, plan_pos, MAX_PAIRS, rng)
    starts = np.broadcast_to(plan_pos + START_OFFSET_AU, (n_trials, 3))

    measured = observed_pair_angles(
        stars, np.broadcast_to(true_pos, (n_trials, 3)), pairs, sigma_rad, rng
    )
    solved, _ = solve_position(
        measured, nav_stars, pairs, starts, SOLVER_STEP_TOL_AU, SOLVER_MAX_ITERS
    )

    rms_au = float(np.sqrt(np.mean(np.sum((solved - true_pos) ** 2, axis=1))))
    cov = position_covariance(nav_stars, plan_pos, pairs, sigma_rad)
    crlb_au = float(np.sqrt(np.trace(cov)))
    return {
        "rms_au": rms_au,
        "crlb_au": crlb_au,
        "measured": measured,
    }


def run_grid(
    stars_all_au, nav_stars_all_au, dists_pc, star_counts, sigmas_rad, n_trials, rng
):
    """Sweep the full grid. Loops over CELLS (independent configurations);
    within each cell all trials are vectorized.

    stars_all_au: (N_catalog, 3) TRUTH star positions, au — generate
                  measurements.
    nav_stars_all_au: (N_catalog, 3) public NAV CATALOG star positions, au —
                  feed the navigator (solver + covariance).
    dists_pc: spacecraft distances from the Sun, parsecs.
    star_counts: numbers of nearest stars to use (counts, dimensionless).
    sigmas_rad: per-measurement camera noise levels, radians.
    n_trials: Monte Carlo trials per cell (count, dimensionless).
    rng: np.random.Generator — spawned into one child stream per cell,
         so every cell is independently reproducible from the one seed.
    Returns: (rms, crlb) arrays of shape (len(dists), len(counts),
             len(sigmas)), in au.
    """
    shape = (len(dists_pc), len(star_counts), len(sigmas_rad))
    rms = np.zeros(shape)
    crlb = np.zeros(shape)
    cell_rngs = rng.spawn(rms.size)
    for a, dist_pc in enumerate(dists_pc):
        for b, n_stars in enumerate(star_counts):
            for c, sigma_rad in enumerate(sigmas_rad):
                cell = run_cell(
                    stars_all_au,
                    nav_stars_all_au,
                    n_stars=n_stars,
                    dist_pc=dist_pc,
                    sigma_rad=sigma_rad,
                    n_trials=n_trials,
                    rng=cell_rngs[(a * len(star_counts) + b) * len(sigmas_rad) + c],
                )
                rms[a, b, c] = cell["rms_au"]
                crlb[a, b, c] = cell["crlb_au"]
    return rms, crlb


def main():
    """Run E1, save figure + exact arrays + parameters to results/."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    stars_all = star_positions_au(load_catalog(CATALOG_CSV))  # TRUTH sky
    nav_stars_all = load_nav_catalog(CATALOG_CSV)["star_pos_au"]  # public catalog
    dists_pc = [1.0, 4.0, 10.0, 20.0]
    star_counts = [5, 10, 20, 50, 100, 200]
    sigmas_arcsec = [0.01, 0.1, 1.0, 10.0]
    sigmas_rad = [s / RAD_ARCSEC for s in sigmas_arcsec]
    n_trials, seed = 500, 42

    rms, crlb = run_grid(
        stars_all,
        nav_stars_all,
        dists_pc,
        star_counts,
        sigmas_rad,
        n_trials,
        rng=np.random.default_rng(seed),
    )
    worst = float(np.max(np.maximum(rms / crlb, crlb / rms)))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(exist_ok=True)
    np.savez(
        RESULTS_DIR / f"e1_crlb_grid_{stamp}.npz",
        rms_au=rms,
        crlb_au=crlb,
        dists_pc=dists_pc,
        star_counts=star_counts,
        sigmas_rad=sigmas_rad,
        n_trials=n_trials,
        seed=seed,
        min_pair_sep_rad=MIN_PAIR_SEP_RAD,
        max_pairs=MAX_PAIRS,
        spacecraft_dir=SPACECRAFT_DIR,
        start_offset_au=START_OFFSET_AU,
    )

    fig, axes = plt.subplots(
        1, len(dists_pc), figsize=(4 * len(dists_pc), 4), sharey=True
    )
    for a, (ax, dist_pc) in enumerate(zip(axes, dists_pc)):
        for c, sigma_arcsec in enumerate(sigmas_arcsec):
            label = f"{sigma_arcsec:g}″"
            (line,) = ax.loglog(star_counts, crlb[a, :, c], "-", label=f"CRLB {label}")
            ax.loglog(star_counts, rms[a, :, c], "o", color=line.get_color(), ms=4)
        ax.set_title(f"spacecraft at {dist_pc:g} pc")
        ax.set_xlabel("number of stars")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel("position error, au")
    axes[0].legend(fontsize=8, title="lines: theory\ndots: 500-trial MC")
    fig.suptitle(
        "E1 — Monte Carlo scatter tracks the CRLB "
        "(position-only; all well-separated pairs, capped at 2000)"
    )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / f"e1_crlb_grid_{stamp}.png", dpi=150)

    print(f"cells: {rms.size}   worst RMS/CRLB deviation factor: {worst:.3f}")
    print(f"wrote results/e1_crlb_grid_{stamp}.png and .npz")


if __name__ == "__main__":
    main()
