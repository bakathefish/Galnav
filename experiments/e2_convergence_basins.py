"""Experiment E2: convergence basins of the Gauss-Newton navigator.

The lost-in-space question. E1 always started the solver 173 au from the truth
and asked how ACCURATE it is; E2 fixes the truth and asks how FAR the initial
guess can be displaced before the solver stops finding its way home. For a grid
of (displacement magnitude x star count) at 1 pc, each cell displaces the start
by a fixed magnitude in many ISOTROPIC random directions and records the
CAPTURE FRACTION: the fraction of directions from which Gauss-Newton converges
back to the true position. The 0.5-capture displacement per star count is the
basin's median radius; it grows with the number of stars (more constraints ->
a wider, gentler residual bowl).

Zero measurement noise throughout: a convergence basin is a property of the
residual landscape, so the ONLY randomness is the displacement direction. With
noise-free angles the true position is an exact residual-zero fixed point, and
a trial either converges to it or lands on a different stationary point /
diverges.

WHY A PER-TRIAL LOOP (documented, ratification-flagged exception to the
project's no-Python-loops-over-trials rule). That rule exists for Monte-Carlo
THROUGHPUT. Here the loop is FAILURE ISOLATION, not throughput: near the basin
edge a start that begins well-conditioned can diverge and drive that ONE
trial's normal-matrix J^T J singular at some Gauss-Newton round, which makes the
batched np.linalg.solve raise LinAlgError and kill the WHOLE cell. The
alternatives were weighed (journal/spec-e2-convergence-basins.md): (B) damping
the solver would re-bless E1/E6/anchor; (C) holding for ratification stalls the
build; (D) a batched pre-solve condition screen is BLIND to a singularity that
first appears mid-iteration. Option A -- wrap the per-trial solve in
try/except -- is a ~10-line loop the reviewer measured at seconds for the full
grid, and "simplicity beats cleverness" (the project rulebook) settles it. The loop only
wraps the solve; the directions are still drawn batched up front.

TRUTH WALL: TRUTH star positions generate the measurements; the public NAV
catalogue positions feed the solver (identical arrays today, as E1). The solver
never sees the true position -- it enters only the capture test (the score).

Run:  python -m experiments.e2_convergence_basins   (writes results/ npz + PNG)
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from experiments.e1_crlb_grid import (
    CATALOG_CSV,
    MAX_PAIRS,
    SPACECRAFT_DIR,
    select_pairs,
)
from galnav.nav.catalog import load_catalog as load_nav_catalog
from galnav.nav.estimator import solve_position
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from galnav.units import AU_PER_PC
from tests.golden_numbers import (
    SOLVER_MAX_ITERS,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_STEP_TOL_AU,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# Fixed configuration. The basin is studied at one spacecraft distance so the
# figure's two axes are displacement and star count alone.
DIST_PC = 1.0
# Displacement grid (parsecs). End anchors 0.1 and 100 pc bracket "always
# captured" and "never captured"; the interior is dense across 1-20 pc because
# the measured 0.5-capture radius runs ~2 pc (5 stars) to ~12 pc (100 stars),
# so that is where the basin edge must be resolved.
DISPS_PC = [0.1, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 100.0]
STAR_COUNTS = [5, 10, 20, 50, 100]


def isotropic_directions(n, rng):
    """n unit vectors drawn uniformly on the sphere (isotropic).

    Construction: normalise an (n, 3) standard-normal draw. The multivariate
    standard normal is spherically symmetric, so dividing by the norm gives a
    direction uniform on S^2. A normalised UNIFORM cube would NOT be isotropic
    -- it over-weights the cube diagonals -- and would bias the basin estimate.
    The draw order is the row order of the (n, 3) array, fixed, so a fixed seed
    reproduces the exact directions (determinism test).

    n: number of directions (count).
    rng: np.random.Generator -- all randomness comes through here.
    Returns: (n, 3) unit vectors (dimensionless).
    """
    g = rng.standard_normal((n, 3))
    return g / np.linalg.norm(g, axis=1, keepdims=True)


def _captured(solved_au, true_pos_au, tol_au):
    """True iff a solve converged back to the true position.

    BOTH clauses are required. Finiteness rejects diverged / NaN solves; the
    distance clause rejects the finite-but-WRONG stationary points Gauss-Newton
    can settle into near the basin edge (a real ~30% population there). Either
    clause alone would over-count captures.

    solved_au: (3,) solved position, au.
    true_pos_au: (3,) true position, au.
    tol_au: capture radius, au (SOLVER_RECOVERY_TOL_AU).
    Returns: bool.
    """
    solved = np.asarray(solved_au, dtype=float)
    return bool(
        np.all(np.isfinite(solved))
        and np.linalg.norm(solved - np.asarray(true_pos_au, dtype=float)) < tol_au
    )


def capture_fraction_cell(
    stars_all_au, nav_stars_all_au, n_stars, dist_pc, disp_au, n_trials, rng
):
    """One grid cell: fraction of isotropic starts that converge to the truth.

    stars_all_au: (N_cat, 3) TRUTH star positions, au -- generate measurements
                  and (physical) pair separations.
    nav_stars_all_au: (N_cat, 3) public NAV catalogue positions, au -- feed the
                  solver only.
    n_stars: use the n nearest stars (count).
    dist_pc: spacecraft distance from the Sun (parsecs).
    disp_au: initial-guess displacement magnitude from the planned position, au
             (== truth today; the start keys off the plan, not the truth).
    n_trials: isotropic directions to try in this cell (count).
    rng: np.random.Generator -- pairs, directions, and (zero) noise flow here.
    Returns: capture fraction in [0, 1] (float).
    """
    stars = stars_all_au[:n_stars]
    nav_stars = nav_stars_all_au[:n_stars]
    # The flight PLAN puts the spacecraft here -- public mission-design
    # knowledge the navigator may hold. Pair selection and the displaced starts
    # key off the PLAN, never the truth, so a future execution error would not
    # silently feed the executed true position into the nav path (E1's pattern,
    # e1_crlb_grid.py). Today truth realizes the plan exactly, so true_pos ==
    # plan_pos bitwise; true_pos is kept separate as the truth-only score.
    plan_pos = SPACECRAFT_DIR * dist_pc * AU_PER_PC
    true_pos = plan_pos
    pairs = select_pairs(stars, plan_pos, MAX_PAIRS, rng)
    dirs = isotropic_directions(n_trials, rng)  # batched up front
    starts = plan_pos + disp_au * dirs  # (n_trials, 3), displaced around the PLAN
    # Zero noise -> exact angles; the true position is an exact fixed point.
    measured = observed_pair_angles(stars, true_pos, pairs, 0.0, rng)  # (P,)

    captured = np.zeros(n_trials, dtype=bool)
    for t in range(n_trials):  # FAILURE ISOLATION loop (see module docstring)
        # An escaping start legitimately drives a pair angle to 0 or pi
        # mid-iteration, so the jacobian divides by sin(theta) -> 0; that
        # non-finite intermediate is EXACTLY the divergence we are measuring
        # and the capture test below rejects it, so silence the expected
        # divide/invalid warnings for this scoped solve only.
        with np.errstate(divide="ignore", invalid="ignore"):
            try:
                solved, _ = solve_position(
                    measured,
                    nav_stars,
                    pairs,
                    starts[t],
                    SOLVER_STEP_TOL_AU,
                    SOLVER_MAX_ITERS,
                )
            except np.linalg.LinAlgError:
                continue  # singular J^T J at some GN round -> this start escaped
        if _captured(solved, true_pos, SOLVER_RECOVERY_TOL_AU):
            captured[t] = True
    return float(captured.mean())


def run_grid(
    stars_all_au,
    nav_stars_all_au,
    star_counts,
    disps_au,
    n_trials,
    rng,
    dist_pc=DIST_PC,
):
    """Sweep the (star count x displacement) grid of capture fractions.

    stars_all_au, nav_stars_all_au: truth / nav catalogues, au (see cell doc).
    star_counts: iterable of star counts (grid rows).
    disps_au: iterable of displacement magnitudes, au (grid columns).
    n_trials: isotropic directions per cell (count).
    rng: np.random.Generator -- spawned into one independent child per cell so
         every cell is reproducible from the one seed.
    dist_pc: spacecraft distance for every cell, parsecs (passed explicitly
        rather than read from the module global).
    Returns: (len(star_counts), len(disps_au)) capture-fraction array.
    """
    cap = np.zeros((len(star_counts), len(disps_au)))
    cell_rngs = rng.spawn(cap.size)
    for i, n_stars in enumerate(star_counts):
        for j, disp_au in enumerate(disps_au):
            cap[i, j] = capture_fraction_cell(
                stars_all_au,
                nav_stars_all_au,
                n_stars,
                dist_pc,
                disp_au,
                n_trials,
                cell_rngs[i * len(disps_au) + j],
            )
    return cap


def fifty_percent_displacement(capture_row, disps_au):
    """Displacement where the capture fraction crosses 0.5 (log-interpolated).

    The basin's median radius for one star count. Degenerate-field guard: a row
    that never crosses 0.5 -- all >= 0.5 (all captured) or all < 0.5 (all
    failed) -- has no basin edge in range; return NaN rather than extrapolate.
    Uses the first high->low crossing (capture falls with displacement).

    capture_row: (D,) capture fractions along increasing displacement.
    disps_au: (D,) displacement magnitudes, au (strictly increasing).
    Returns: displacement at 0.5 capture, au, or NaN if undefined.
    """
    cap = np.asarray(capture_row, dtype=float)
    disps = np.asarray(disps_au, dtype=float)
    hi = cap >= 0.5
    if hi.all() or (~hi).all():
        return float("nan")
    j = int(np.argmax(~hi))  # first index below 0.5
    if j == 0:
        return float("nan")  # already below 0.5 at the smallest displacement
    x0, x1 = np.log(disps[j - 1]), np.log(disps[j])
    y0, y1 = cap[j - 1], cap[j]
    t = (0.5 - y0) / (y1 - y0) if y1 != y0 else 0.0
    return float(np.exp(x0 + t * (x1 - x0)))


def compute(star_counts=None, disps_pc=None, n_trials=500, seed=42):
    """Run the E2 grid. Returns a dict of every array ready for save_outputs.

    star_counts: grid rows (defaults to STAR_COUNTS).
    disps_pc: grid columns in parsecs (defaults to DISPS_PC).
    n_trials: isotropic directions per cell (count).
    seed: master seed for the reproducible per-cell child streams.
    Returns: dict with capture_fraction, star_counts, disps_pc, fifty_pc_disp_pc
        (the 0.5-capture radius per star count, pc), n_trials, seed, dist_pc.
    """
    star_counts = list(STAR_COUNTS if star_counts is None else star_counts)
    disps_pc = list(DISPS_PC if disps_pc is None else disps_pc)
    stars_all = star_positions_au(load_catalog(CATALOG_CSV))  # TRUTH sky
    nav_stars_all = load_nav_catalog(CATALOG_CSV)["star_pos_au"]  # public catalog
    disps_au = np.array(disps_pc) * AU_PER_PC
    cap = run_grid(
        stars_all,
        nav_stars_all,
        star_counts,
        disps_au,
        n_trials,
        rng=np.random.default_rng(seed),
    )
    fifty = np.array(
        [
            fifty_percent_displacement(cap[i], disps_au) / AU_PER_PC
            for i in range(len(star_counts))
        ]
    )
    return dict(
        capture_fraction=cap,
        star_counts=np.array(star_counts),
        disps_pc=np.array(disps_pc),
        fifty_pc_disp_pc=fifty,
        n_trials=int(n_trials),
        seed=int(seed),
        dist_pc=float(DIST_PC),
    )


def save_outputs(data, out_dir=RESULTS_DIR):
    """Write a timestamped .npz with every plotted array + parameter.

    data: the dict returned by compute(). out_dir: directory to write into.
    Returns: the written .npz Path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e2_convergence_basins_{stamp}.npz"
    np.savez(path, **data)
    return path


def _draw(fig, d):
    """Render the basin map (capture fraction + 0.5 contour) from a dict.

    fig: a matplotlib Figure to draw onto. d: the npz dict of arrays.
    Returns: None (draws onto fig in place).
    """
    cap = np.asarray(d["capture_fraction"], dtype=float)
    counts = np.asarray(d["star_counts"], dtype=float)
    disps_pc = np.asarray(d["disps_pc"], dtype=float)
    ax = fig.subplots(1, 1)
    # capture fraction as a filled field: x = star count (log), y = disp (log).
    xx, yy = np.meshgrid(counts, disps_pc)
    mesh = ax.pcolormesh(
        xx, yy, cap.T, cmap="viridis", vmin=0.0, vmax=1.0, shading="auto"
    )
    fig.colorbar(mesh, ax=ax, label="capture fraction")
    # 0.5 contour only where the field actually spans 0.5 (degenerate guard:
    # an all-1 or all-0 field has no 0.5 level and contour would draw nothing
    # or warn).
    if np.nanmin(cap) < 0.5 < np.nanmax(cap):
        ax.contour(xx, yy, cap.T, levels=[0.5], colors="white", linewidths=1.5)
    # the per-star-count 0.5-capture radius (basin median radius).
    fifty = np.asarray(d["fifty_pc_disp_pc"], dtype=float)
    good = np.isfinite(fifty)
    ax.plot(counts[good], fifty[good], "o-", color="red", label="0.5-capture radius")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("number of stars")
    ax.set_ylabel("initial-guess displacement, pc")
    ax.set_title(
        f"E2 - convergence basin at {float(d['dist_pc']):g} pc "
        f"({int(d['n_trials'])} isotropic starts/cell, zero noise)"
    )
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E2 figure from a saved .npz ALONE.

    npz_path: path to a saved E2 .npz. out_png: optional output path (defaults
    to the npz path with a .png suffix). Sets the Agg backend locally so
    importing this module has no matplotlib side effect (E1's precedent).
    Returns: the written PNG Path.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=True) as z:
        d = {k: z[k] for k in z.files}
    fig = plt.figure(figsize=(7, 6))
    _draw(fig, d)
    if out_png is None:
        out_png = npz_path.with_suffix(".png")
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return out_png


def main():
    """Compute, save arrays + figure, and print the 0.5-capture curve.

    Returns: the written .npz Path.
    """
    d = compute()
    path = save_outputs(d)
    png = replot_from_npz(path, out_png=path.with_suffix(".png"))
    print(f"wrote {path.name} and {png.name}")
    for n, r in zip(d["star_counts"], d["fifty_pc_disp_pc"]):
        print(f"  {int(n):>4d} stars: 0.5-capture radius {r:.2f} pc")
    return path


if __name__ == "__main__":
    main()
