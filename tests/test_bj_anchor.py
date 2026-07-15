"""THE ANCHOR (plan week-5 hard gate): reproduce Bailer-Jones 2021.

His protocol, extracted from the full text ([BJ21], verified 2026-07-15)
and mirrored here as faithfully as the instrument allows:
- Network: the Sun (hub reference) + the 19 nearest bright stars; the
  measurements are the 19 Sun-star hub angles at 1 arcsec noise each —
  NOT all pairs (he explicitly declines all-pairs). Our brightness cut is
  phot_g_mean_mag < 10, the Gaia analog of his V < 10 instrument cut.
- Truths: 100 runs; direction isotropic; distance uniform 0.1-10 light
  years; velocity PARALLEL to position (radially outbound), magnitude
  uniform 0 to 0.5c; solver initialized uniformly in 0.9-1.1x the truth,
  per parameter (his footnote-4 assumption).
- Statistic: the MEDIAN over runs of the 3D error MAGNITUDE (his Fig. 8
  metric) — not RMS (heavy-tail inflated), not per-axis (sqrt(3)
  smaller, his caption's own warning).
- Gate: median position error within tol_factor of pos_err_au AND median
  velocity error within tol_factor of vel_err_kms, TWO-SIDED — landing
  10x better would mean we solved an easier problem, not reproduced his.
Known honest differences, disclosed (none changes the physics tested):
- He solves 7 parameters (epoch included, forced by his unknown-time
  setup); with our static catalog the epoch column is identically zero,
  so we solve 6. His Sec. 4.1 control shows this costs nothing.
- Star networks differ in composition: his Hipparcos V < 10 list keeps
  alpha Cen A/B, Sirius, Procyon; our Gaia subset's RUWE < 1.4 quality
  cut drops those exact stars (bright/binary), so our 19 are drawn
  slightly deeper. Same character (nearest bright stars), not the same
  list.
- He infers by MCMC and reports the posterior median; we take the
  damped Gauss-Newton least-squares point estimate. For this unimodal,
  near-Gaussian likelihood the two estimators agree to within the noise
  — which the matching medians AND matching percentile bands confirm.
"""

from pathlib import Path

import numpy as np

from galnav.nav.estimator import solve_state
from galnav.truth.observer import observed_pair_angles_moving
from galnav.units import (
    AU_PER_LY,
    C_KM_S,
    deg_to_rad,
    parallax_mas_to_dist_au,
    radec_to_unit,
)
from tests.golden_numbers import (
    BAILER_JONES_ANCHOR,
    RAD_ARCSEC,
    SOLVER_MAX_ITERS,
    SOLVER_STEP_TOL_AU,
    SOLVER_STEP_TOL_KMS,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)


def test_bailer_jones_anchor_reproduced():
    anchor = BAILER_JONES_ANCHOR
    n_hub = anchor["n_stars"] - 1  # 19 hub angles for 20 stars
    raw = np.genfromtxt(CATALOG_CSV, delimiter=",", names=True)
    bright = raw[raw["phot_g_mean_mag"] < 10.0][:n_hub]  # nearest-first
    unit = radec_to_unit(deg_to_rad(bright["ra"]), deg_to_rad(bright["dec"]))
    stars = np.vstack(
        [np.zeros(3), unit * parallax_mas_to_dist_au(bright["parallax"])[:, None]]
    )
    pairs = np.column_stack([np.zeros(n_hub, dtype=int), np.arange(1, n_hub + 1)])

    rng = np.random.default_rng(2026)
    n_runs = anchor["n_runs"]
    directions = rng.normal(size=(n_runs, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    dist_au = rng.uniform(0.1, 10.0, n_runs) * AU_PER_LY  # 0.1-10 light years
    pos_true = directions * dist_au[:, None]
    speed_kms = rng.uniform(0.0, 0.5, n_runs) * C_KM_S
    vel_true = directions * speed_kms[:, None]  # radially outbound

    sigma_rad = anchor["sigma_theta_arcsec"] / RAD_ARCSEC
    measured = observed_pair_angles_moving(
        stars, pos_true, vel_true, pairs, sigma_rad, rng
    )

    factors = rng.uniform(0.9, 1.1, (n_runs, 6))
    pos, vel, _ = solve_state(
        measured,
        stars,
        pairs,
        factors[:, :3] * pos_true,
        factors[:, 3:] * vel_true,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )

    median_pos_au = float(np.median(np.linalg.norm(pos - pos_true, axis=1)))
    median_vel_kms = float(np.median(np.linalg.norm(vel - vel_true, axis=1)))

    tol = anchor["tol_factor"]
    assert anchor["pos_err_au"] / tol < median_pos_au < anchor["pos_err_au"] * tol, (
        f"median position error {median_pos_au:.2f} au vs anchor "
        f"{anchor['pos_err_au']} au (factor {tol})"
    )
    assert anchor["vel_err_kms"] / tol < median_vel_kms < anchor["vel_err_kms"] * tol, (
        f"median velocity error {median_vel_kms:.2f} km/s vs anchor "
        f"{anchor['vel_err_kms']} km/s (factor {tol})"
    )
