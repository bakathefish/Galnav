"""Experiment E3: real New Horizons interstellar navigation (the real-data anchor).

Recover the 3D position of the New Horizons spacecraft from optical measurements
of two nearby stars (Proxima Centauri, Wolf 359) taken by LORRI on 2020-04-23,
and compare to the JPL Horizons ephemeris. Reproduces Lauer et al. (2025,
AJ 170, 1); real data from Zenodo doi:10.5281/zenodo.15359866 (see
data/e3_new_horizons/, [Lauer25], [Lauer25-data]).

TRUTH WALL: the JPL ephemeris is the TRUTH (enters ONLY the scoring); Lauer's
measured star directions are the MEASUREMENTS; our nav is the independent
line-of-position solver galnav/nav/triangulate.py::n_star_solve, fed our own
Gaia catalogue positions propagated to the image epoch. n_star_solve NEVER sees
the JPL state.

Two things are computed:
  1. OUR PIPELINE (the gate): load our Gaia DR3 catalogue, select Proxima +
     Wolf 359 by source_id, propagate J2016.0 -> image epoch (mandatory: PM+RV;
     skipping it lands ~30 au off), triangulate on the measured directions,
     and score the miss vs JPL. Gate: miss < NH_NAV_TOL_AU (plan section 7).
  2. REPRODUCTION CROSS-CHECK (reported): feed n_star_solve Lauer's OWN
     propagated positions + directions; it reproduces his recovered x2 to
     ~0.006 au (8-digit fixture rounding), confirming the shared algorithm.

Reported, not gated: the miss distance (~0.35 au) and the 1-sigma error
ellipsoid. NOTE: Lauer's famous "0.44 au" is the largest ELLIPSOID SEMI-AXIS
(0.441 x 0.233 x 0.206 au from his 12-line x60 solve), NOT the miss (0.351 au).

Run:  python -m experiments.e3_new_horizons   (writes results/ npz + PNG)
"""

from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from galnav.nav.catalog import (
    load_catalog,
    propagate_positions_au,
    star_velocities_kms,
)
from galnav.nav.triangulate import n_star_solve
from galnav.units import arcsec_to_rad
from tests.golden_numbers import NH_NAV_TOL_AU

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"
RESULTS_DIR = REPO_ROOT / "results"

# --- Lauer et al. 2025 measured inputs -------------------------------------
# Extracted from nhparallax.ipynb (Zenodo 15359866); frame = ICRS equatorial
# Cartesian, origin = Solar System Barycenter, units = au. Directions are the
# re-normalised mean of the 6 per-image line-of-sight unit vectors per star.
P_DBAR = np.array([-0.36482883, -0.27856106, -0.88842763])  # measured -> Proxima
W_DBAR = np.array([-0.95454352, 0.27201153, 0.12188681])  # measured -> Wolf 359
# Lauer's own Gaia-propagated star positions (au) -- for the reproduction check.
LAUER_PROXIMA_P = np.array([-97946.863, -74838.542, -238568.733])
LAUER_WOLF_P = np.array([-474254.151, 135108.026, 60543.598])
LAUER_X2 = np.array([13.67954173, -41.82188783, -16.19762222])  # his recovered x2
# JPL Horizons truth: newh_x = 0.5*(mean 6 Proxima-epoch + mean 6 Wolf-epoch
# hardcoded Horizons positions), au, ICRS equatorial, SSB (notebook cell 4).
NEWH_X_JPL = np.array([13.5495, -42.0195, -16.4573])
RMSSIG_ARCSEC = 0.44  # per-image astrometric sigma (Buie); scales the ellipsoid
LAUER_X60_ELLIPSOID_AU = np.array([0.441, 0.233, 0.206])  # 12-line 1-sigma (quoted)
LAUER_X60_MISS_AU = 0.351  # Lauer's 12-line x60 miss vs JPL (0.94-sigma Mahalanobis)

# Star selection + epoch (source_ids from the notebook; J2016.0 -> mean image JD).
PROXIMA_ID = 5853498713190525696
WOLF_ID = 3864972938605115520
JD_J2016 = 2457388.5  # Gaia DR3 reference epoch 2016.0
JD_MEAN_IMAGE = 2458962.25  # mean of the 12 LORRI image times (notebook)
AGE_YR = (JD_MEAN_IMAGE - JD_J2016) / 365.25  # ~4.309 Julian yr
# Our Gaia CSV has no Wolf 359 radial velocity; fill with the Simbad value Lauer
# used (documented choice; rv_fill = 0 shifts the miss by only ~0.03 au).
WOLF_RV_FILL_KMS = 19.57


def _select_indices(csv_path, source_ids):
    """Row indices of the given Gaia source_ids (load_catalog drops that column).

    csv_path: path to the nav-subset CSV (column 0 is source_id).
    source_ids: iterable of int64 Gaia source ids.
    Returns: list of int row indices, one per source id (same order).
    """
    ids = np.loadtxt(csv_path, delimiter=",", skiprows=1, usecols=0, dtype=np.int64)
    return [int(np.where(ids == sid)[0][0]) for sid in source_ids]


def our_pipeline(csv_path=CATALOG_CSV):
    """Recover NH from OUR Gaia catalogue: select, propagate, triangulate.

    Returns: dict with x_au (recovered position), star_pos_au (the two
        propagated star positions used), age_yr, and miss_au vs JPL.
    """
    catalog = load_catalog(csv_path)
    idx = _select_indices(csv_path, [PROXIMA_ID, WOLF_ID])
    vel = star_velocities_kms(catalog, rv_fill_kms=WOLF_RV_FILL_KMS)
    propagated = propagate_positions_au(catalog["star_pos_au"], vel, AGE_YR)
    star_pos = propagated[idx]  # (2, 3): Proxima, Wolf at image epoch
    x, _, _ = n_star_solve(star_pos, np.array([P_DBAR, W_DBAR]))
    return dict(
        x_au=x,
        star_pos_au=star_pos,
        age_yr=float(AGE_YR),
        miss_au=float(np.linalg.norm(x - NEWH_X_JPL)),
    )


def reproduce_lauer():
    """Feed n_star_solve Lauer's OWN inputs; reproduce his x2 (cross-check).

    Returns: dict with x_au, xcov, miss_vs_lauer_au, miss_vs_jpl_au, and the
        2-star 1-sigma ellipsoid semi-axes (au, from xcov scaled by rmssig).
    """
    x, xcov, _ = n_star_solve([LAUER_PROXIMA_P, LAUER_WOLF_P], [P_DBAR, W_DBAR])
    rmssig_rad = arcsec_to_rad(RMSSIG_ARCSEC)
    ellipsoid = np.sqrt(np.linalg.eigvalsh(xcov)) * rmssig_rad  # au
    return dict(
        x_au=x,
        xcov=xcov,
        miss_vs_lauer_au=float(np.linalg.norm(x - LAUER_X2)),
        miss_vs_jpl_au=float(np.linalg.norm(x - NEWH_X_JPL)),
        ellipsoid_x2_au=np.sort(ellipsoid)[::-1],
    )


def compute():
    """Compute every reported quantity. Returns a dict ready for save_outputs."""
    pipe = our_pipeline()
    repro = reproduce_lauer()
    return dict(
        x_pipeline_au=pipe["x_au"],
        star_pos_au=pipe["star_pos_au"],
        age_yr=pipe["age_yr"],
        miss_pipeline_au=pipe["miss_au"],
        x_repro_au=repro["x_au"],
        miss_repro_vs_lauer_au=repro["miss_vs_lauer_au"],
        miss_repro_vs_jpl_au=repro["miss_vs_jpl_au"],
        ellipsoid_x2_au=repro["ellipsoid_x2_au"],
        newh_x_jpl_au=NEWH_X_JPL,
        lauer_x2_au=LAUER_X2,
        lauer_x60_ellipsoid_au=LAUER_X60_ELLIPSOID_AU,
        lauer_x60_miss_au=float(LAUER_X60_MISS_AU),
        nh_nav_tol_au=float(NH_NAV_TOL_AU),
        rmssig_arcsec=float(RMSSIG_ARCSEC),
    )


def save_outputs(data, out_dir=RESULTS_DIR):
    """Write a timestamped .npz with every reported array + param."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e3_new_horizons_{stamp}.npz"
    np.savez(path, **data)
    return path


def _draw(fig, d):
    """Render the fix comparison from a plain dict of arrays."""
    ax = fig.subplots(1, 1)
    # Project the three positions onto the plane perpendicular to the mean
    # sightline, centred on JPL truth, in au (a local tangent view of the miss).
    jpl = np.asarray(d["newh_x_jpl_au"])
    pts = {
        "JPL truth": (jpl, "k", "*"),
        "our pipeline": (np.asarray(d["x_pipeline_au"]), "tab:blue", "o"),
        "Lauer x2 (reproduced)": (np.asarray(d["x_repro_au"]), "tab:green", "s"),
    }
    # basis in the plane perpendicular to jpl direction
    u = jpl / np.linalg.norm(jpl)
    e1 = np.cross(u, [0, 0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    for name, (p, c, m) in pts.items():
        dp = p - jpl
        ax.plot(dp @ e1, dp @ e2, m, color=c, ms=11, label=name)
    ax.axhline(0, color="0.8", lw=0.7)
    ax.axvline(0, color="0.8", lw=0.7)
    ax.set_aspect("equal")
    ax.set_xlabel("offset from JPL, au (sky-plane e1)")
    ax.set_ylabel("offset from JPL, au (sky-plane e2)")
    ax.set_title(
        f"E3 - New Horizons fix from 2 real stars\n"
        f"pipeline miss {d['miss_pipeline_au']:.3f} au vs JPL "
        f"(gate < {float(d['nh_nav_tol_au']):.0f} au); Lauer x60 miss "
        f"{float(d['lauer_x60_miss_au']):.3f} au, ellipsoid "
        f"{'/'.join(f'{v:.3f}' for v in d['lauer_x60_ellipsoid_au'])} au"
    )
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E3 figure from a saved .npz ALONE."""
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
    """Compute, save arrays + figure, and print the headline numbers."""
    d = compute()
    path = save_outputs(d)
    png = replot_from_npz(path, out_png=path.with_suffix(".png"))
    print(f"wrote {path.name} and {png.name}")
    print(
        f"OUR PIPELINE: recovered {np.round(d['x_pipeline_au'], 3)} au, "
        f"miss vs JPL = {d['miss_pipeline_au']:.4f} au "
        f"(gate < {NH_NAV_TOL_AU:.0f} au), age {d['age_yr']:.4f} yr"
    )
    print(
        f"REPRODUCTION: reproduces Lauer x2 to "
        f"{d['miss_repro_vs_lauer_au']:.4f} au; miss vs JPL "
        f"{d['miss_repro_vs_jpl_au']:.4f} au"
    )
    print(
        f"2-star ellipsoid (ours) {np.round(d['ellipsoid_x2_au'], 3)} au; "
        f"Lauer x60 ellipsoid {d['lauer_x60_ellipsoid_au']} au"
    )
    return path


if __name__ == "__main__":
    main()
