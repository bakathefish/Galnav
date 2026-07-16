"""Experiment E7: relativistic aberration at 0.1c (the relativistic armor).

At an interstellar cruise speed of 0.1c the stellar aberration is a LARGE effect
(~5.74 deg). E7 shows that the EXACT special-relativistic form is MANDATORY, not
a refinement: a navigator that uses the classical (Galilean, Lauer Eq. 1)
aberration is biased by ~1300 au — the difference between arriving and being
lost.

E7 is an EXPERIMENT ONLY; it does NOT modify galnav/. The aberration is already
exact special-relativistic on BOTH sides of the truth wall (truth _aberrate and
nav _aberrate_nav, independent Klioner-2003 k-forms with the Lorentz gamma,
agreeing to ~1e-16). So there is NO Galilean aberration anywhere in galnav to
reuse: the classical predictor below is NEW, experiment-local, DELIBERATELY
WRONG physics, honestly labelled. It reuses nav's _unit_directions and
_pair_sin_cos and differs from the real navigator in exactly one line — the
aberration.

Three parts:
  A. aberration magnitude: Galilean max = arcsin(0.1) = 5.739 deg vs exact
     relativistic max = 5.746 deg (26 arcsec larger, peak pulled toward 90 deg
     by gamma). Small-angle (5.730 deg) is a distinct third quantity.
  B. recovery: the deployed exact solve_state recovers the true 6-state at 0.1c
     to the deployed recovery tolerance (truth/nav aberration agree through a
     full inversion at relativistic speed).
  C. THE PAYLOAD: feed the exact measurements to a classical-aberration
     navigator; its per-angle model error is ~500 arcsec (NOT the 26 arcsec
     max-deflection gap), which fuses into a ~1300 au / ~1180 km/s state bias.

Run:  python -m experiments.e7_relativistic_aberration
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from galnav.nav.estimator import solve_state
from galnav.nav.measmodel import (
    _pair_sin_cos,
    _unit_directions,
    pair_angle_state_jacobian,
    predicted_pair_angles_moving,
)
from galnav.truth.observer import observed_pair_angles_moving
from galnav.units import (
    AU_PER_LY,
    C_KM_S,
    arcsec_to_rad,
    deg_to_rad,
    kms_to_beta,
    parallax_mas_to_dist_au,
    radec_to_unit,
)
from tests.golden_numbers import (
    SOLVER_MAX_ITERS,
    SOLVER_STEP_TOL_AU,
    SOLVER_STEP_TOL_KMS,
    SR_ABER_PHI_RAD,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"
RESULTS_DIR = REPO_ROOT / "results"

BETA_CRUISE = 0.1  # interstellar cruise speed, v/c
N_HUB = 19  # Sun + 19 nearest bright stars -> 19 Sun-star hub angles (BJ network)
# Experiment-local iteration budget for the WRONG-PHYSICS classical solve: the
# classical fit never drives the residual to zero (the model is wrong), so it
# needs a longer budget than the deployed SOLVER_MAX_ITERS to settle onto its
# biased fixed point. This is NOT the deployed navigator's budget.
GALILEAN_MAX_ITERS = 60


def build_network(csv_path=CATALOG_CSV, n_hub=N_HUB):
    """Sun-hub star network (the BJ-anchor geometry).

    csv_path: path to the Gaia nav-subset CSV.
    n_hub: number of nearest bright stars (hub angles).
    Returns: (stars (n_hub+1, 3) au — the Sun at the origin then the stars,
        pairs (n_hub, 2) int — each Sun-star hub angle).
    """
    raw = np.genfromtxt(csv_path, delimiter=",", names=True)
    bright = raw[raw["phot_g_mean_mag"] < 10.0][:n_hub]  # nearest-first
    unit = radec_to_unit(deg_to_rad(bright["ra"]), deg_to_rad(bright["dec"]))
    stars = np.vstack(
        [np.zeros(3), unit * parallax_mas_to_dist_au(bright["parallax"])[:, None]]
    )
    pairs = np.column_stack([np.zeros(n_hub, dtype=int), np.arange(1, n_hub + 1)])
    return stars, pairs


# --- Part A: aberration magnitude -------------------------------------------
def galilean_deflection(beta, theta_rad):
    """Classical (Galilean, gamma=1) aberration deflection, radians.

    phi = atan2(sin theta, beta + cos theta); deflection = theta - phi. This is
    the exact classical (Lauer Eq. 1) form, NOT the small-angle approximation.

    beta: v/c (dimensionless). theta_rad: true angle from the apex, radians.
    Returns: deflection theta - phi, radians.
    """
    phi = np.arctan2(np.sin(theta_rad), beta + np.cos(theta_rad))
    return theta_rad - phi


def exact_deflection(beta, theta_rad):
    """Exact special-relativistic aberration deflection, radians.

    Uses the SR_ABER_PHI_RAD oracle (gamma form). beta: v/c. theta_rad: true
    angle from the apex, radians. Returns: theta - phi, radians.
    """
    return theta_rad - SR_ABER_PHI_RAD(beta, theta_rad)


def max_deflection(beta, relativistic):
    """Maximum aberration deflection and the angle where it peaks.

    The peak LOCATION is found with a bounded 1-D optimizer (a grid argmax
    would quantize it); the peak VALUE is grid-robust either way.

    beta: v/c (dimensionless). relativistic: True for the exact SR form, False
        for the classical (Galilean) form.
    Returns: (max deflection in degrees, peak angle in degrees).
    """
    f = exact_deflection if relativistic else galilean_deflection
    res = minimize_scalar(
        lambda th: -f(beta, th), bounds=(1e-6, np.pi - 1e-6), method="bounded"
    )
    return float(np.degrees(f(beta, res.x))), float(np.degrees(res.x))


# --- Part C: the WRONG-PHYSICS classical navigator (experiment-local) -------
def _classical_aberrate(unit, vel_kms):
    """Classical (Galilean, Lauer Eq. 1) aberration -- DELIBERATELY WRONG.

    u' = normalize(u + beta), beta = v/c. Drops the Lorentz gamma the real
    navigator carries; this is the whole point of Part C. Experiment-local, not
    part of galnav.

    unit: (..., N, 3) rest-frame unit directions. vel_kms: (..., 3) velocity,
    km/s. Returns: (..., N, 3) classically-aberrated unit directions.
    """
    beta = kms_to_beta(vel_kms)
    aberrated = unit + beta[..., None, :]
    return aberrated / np.linalg.norm(aberrated, axis=-1, keepdims=True)


def galilean_predicted_pair_angles(star_pos_au, obs_pos_au, obs_vel_kms, pairs):
    """Pair angles a CLASSICAL-aberration navigator predicts.

    Mirrors nav's predicted_pair_angles_moving but with the wrong
    _classical_aberrate. star_pos_au: (N, 3) au. obs_pos_au: (..., 3) au.
    obs_vel_kms: (..., 3) km/s. pairs: (P, 2) int. Returns: (..., P) radians.
    """
    pairs = np.asarray(pairs)
    unit, _ = _unit_directions(star_pos_au, obs_pos_au)
    sin_t, cos_t = _pair_sin_cos(_classical_aberrate(unit, obs_vel_kms), pairs)
    return np.arctan2(sin_t, cos_t)


def _clip_light_cone(vel_kms):
    """Pull any at-or-beyond-c velocity back inside the cone (domain guard).

    vel_kms: (..., 3) km/s. Returns: (..., 3) km/s, every speed below c.
    """
    speed = np.linalg.norm(vel_kms, axis=-1)
    outside = speed >= C_KM_S
    if not np.any(outside):
        return vel_kms
    scale = np.where(outside, 0.99 * C_KM_S / np.where(outside, speed, 1.0), 1.0)
    return vel_kms * scale[..., None]


def _galilean_fd_jacobian(star_pos, pos, vel, pairs, h_au, h_kms):
    """Finite-difference jacobian of the classical predictor w.r.t. the state.

    CENTRAL differences keep the wrong-physics predictor as the single source of
    truth (the jacobian is derived FROM it, so the two cannot silently disagree,
    unlike a second hand-derived analytic jacobian). Vectorized over the whole
    ensemble.

    Step size (an implementation parameter of the probe, NOT a physics
    tolerance): central differences balance O(h^2) truncation against O(eps/h)
    float64 rounding, minimized near h ~ eps^(1/3) * L with L the scale over
    which a predicted angle turns by O(1) -- the star distance (~2e5 au) for
    position and c (~3e5 km/s) for velocity. eps^(1/3) ~ 6e-6 gives ~1.2 au and
    ~1.8 km/s, so the h_au = h_kms = 1.0 defaults sit in the optimal band
    (each step moves the angle by ~1 arcsec, far above the ~1e-11 rad float64
    angle floor and far below the ~0.1 rad aberration scale). Measured: the
    recovered bias is identical to the reported precision across h in
    [0.1, 100] (four decades) -- the O(h^2) fixed-point error is negligible
    against the ~1300 au signal. (Precedent: the suite's own FD-vs-analytic
    jacobian tests carry FD steps.)

    star_pos: (N, 3) au. pos: (..., 3) au. vel: (..., 3) km/s. pairs: (P, 2) int.
    h_au: position step, au. h_kms: velocity step, km/s.
    Returns: (..., P, 6) jacobian; columns 0-2 in rad/au, columns 3-5 in
        rad/(km/s).
    """
    cols = []
    for k in range(3):
        e = np.zeros_like(pos)
        e[..., k] = h_au
        cols.append(
            (
                galilean_predicted_pair_angles(star_pos, pos + e, vel, pairs)
                - galilean_predicted_pair_angles(star_pos, pos - e, vel, pairs)
            )
            / (2.0 * h_au)
        )
    for k in range(3):
        e = np.zeros_like(vel)
        e[..., k] = h_kms
        cols.append(
            (
                galilean_predicted_pair_angles(star_pos, pos, vel + e, pairs)
                - galilean_predicted_pair_angles(star_pos, pos, vel - e, pairs)
            )
            / (2.0 * h_kms)
        )
    return np.stack(cols, axis=-1)


def galilean_solve_state(
    measured,
    star_pos,
    pairs,
    pos0,
    vel0,
    step_tol_au,
    step_tol_kms,
    max_iters,
    h_au=1.0,
    h_kms=1.0,
):
    """Hand-rolled damped Gauss-Newton with the WRONG-PHYSICS classical model.

    Mirrors solve_state's recipe (step-halving damping + light-cone guard) but
    fits the classical predictor with a finite-difference jacobian. No scipy in
    the loop. Vectorized over the ensemble. The batched normal-equation solve
    ASSUMES a non-singular J^T J for every ensemble member; unlike the deployed
    solver this wrong-physics probe carries no recovery guarantee, and it is
    used only on the well-conditioned hub geometry (verified non-raising over
    the blessed 200-run ensemble).

    measured: (..., P) measured angles, radians. star_pos: (N, 3) au.
    pairs: (P, 2) int. pos0/vel0: (..., 3) starting guesses (au / km/s).
    step_tol_au/step_tol_kms: stopping steps (au / km/s). max_iters: cap.
    h_au/h_kms: finite-difference steps (au / km/s).
    Returns: (position (..., 3) au, velocity (..., 3) km/s, iterations).
    """
    pos = np.array(pos0, dtype=float)
    vel = np.array(vel0, dtype=float)
    measured = np.asarray(measured, dtype=float)
    for iteration in range(1, max_iters + 1):
        residual = measured - galilean_predicted_pair_angles(star_pos, pos, vel, pairs)
        res_norm = np.sum(residual**2, axis=-1)
        jac = _galilean_fd_jacobian(star_pos, pos, vel, pairs, h_au, h_kms)
        jtj = np.einsum("...pi,...pj->...ij", jac, jac)
        jtr = np.einsum("...pi,...p->...i", jac, residual)
        step = np.linalg.solve(jtj, jtr[..., None])[..., 0]
        scale = np.ones(res_norm.shape)
        for _ in range(8):  # step-halving, vectorized over the ensemble
            trial_pos = pos + scale[..., None] * step[..., :3]
            trial_vel = _clip_light_cone(vel + scale[..., None] * step[..., 3:])
            trial_res = measured - galilean_predicted_pair_angles(
                star_pos, trial_pos, trial_vel, pairs
            )
            worse = ~(np.sum(trial_res**2, axis=-1) <= res_norm)  # NaN counts as worse
            if not np.any(worse):
                break
            scale = np.where(worse, scale / 2.0, scale)
        if np.any(worse):  # exhausted -> never move uphill
            scale = np.where(worse, 0.0, scale)
            trial_pos = pos + scale[..., None] * step[..., :3]
            trial_vel = _clip_light_cone(vel + scale[..., None] * step[..., 3:])
        pos, vel = trial_pos, trial_vel
        taken = scale[..., None] * step
        if np.all(np.linalg.norm(taken[..., :3], axis=-1) < step_tol_au) and np.all(
            np.linalg.norm(taken[..., 3:], axis=-1) < step_tol_kms
        ):
            return pos, vel, iteration
    return pos, vel, max_iters


# --- ensembles ---------------------------------------------------------------
def _draw_truths(beta, n_runs, rng):
    """Random true states at fixed speed beta*c (radially outbound).

    beta: v/c, dimensionless. n_runs: ensemble size (count). rng:
        np.random.Generator (all randomness comes through here).
    Returns: (pos_true (n_runs, 3) au, vel_true (n_runs, 3) km/s, directions
        (n_runs, 3) dimensionless unit vectors).
    """
    directions = rng.normal(size=(n_runs, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    dist_au = rng.uniform(0.1, 10.0, n_runs) * AU_PER_LY  # 0.1-10 light years
    pos_true = directions * dist_au[:, None]
    vel_true = directions * (beta * C_KM_S)  # radially outbound at exactly beta*c
    return pos_true, vel_true, directions


def run_ensemble(star_pos, pairs, beta, n_runs, sigma_arcsec, rng):
    """One ensemble at fixed 0.1c: exact recovery AND the classical mis-fit.

    star_pos: (N, 3) au. pairs: (P, 2) int. beta: v/c. n_runs: ensemble size.
    sigma_arcsec: camera noise (arcsec; 0 = perfect). rng: np.random.Generator.
    Returns: dict of recovery errors, classical bias (arrays + medians), and the
        per-angle exact-vs-classical aberration difference (arcsec).
    """
    pos_true, vel_true, _ = _draw_truths(beta, n_runs, rng)
    sigma_rad = arcsec_to_rad(sigma_arcsec)  # arcsec -> rad at the I/O edge
    measured = observed_pair_angles_moving(
        star_pos, pos_true, vel_true, pairs, sigma_rad, rng
    )

    # (a) the DEPLOYED exact navigator recovers the truth (0.9-1.1x start).
    factors = rng.uniform(0.9, 1.1, (n_runs, 6))
    pos_hat, vel_hat, _ = solve_state(
        measured,
        star_pos,
        pairs,
        factors[:, :3] * pos_true,
        factors[:, 3:] * vel_true,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        SOLVER_MAX_ITERS,
    )
    rec_pos = np.linalg.norm(pos_hat - pos_true, axis=1)
    rec_vel = np.linalg.norm(vel_hat - vel_true, axis=1)

    # (b) the WRONG-PHYSICS classical navigator mis-fits the SAME measurements
    # from the SAME realistic 0.9-1.1x start as the exact navigator (a) -- the
    # two differ ONLY in the aberration physics, and neither is handed the truth
    # as its start (truth-wall clean; the bias is a property of the residual
    # landscape, not of the starting point).
    gpos, gvel, _ = galilean_solve_state(
        measured,
        star_pos,
        pairs,
        factors[:, :3] * pos_true,
        factors[:, 3:] * vel_true,
        SOLVER_STEP_TOL_AU,
        SOLVER_STEP_TOL_KMS,
        GALILEAN_MAX_ITERS,
    )
    bias_pos = np.linalg.norm(gpos - pos_true, axis=1)
    bias_vel = np.linalg.norm(gvel - vel_true, axis=1)

    # per-angle model error: exact vs classical aberration at the TRUE state.
    exact_ang = predicted_pair_angles_moving(star_pos, pos_true, vel_true, pairs)
    gal_ang = galilean_predicted_pair_angles(star_pos, pos_true, vel_true, pairs)
    # rad -> arcsec at the I/O edge (via the units edge helper, e3/e6 path).
    dtheta_arcsec = np.abs(exact_ang - gal_ang) / arcsec_to_rad(1.0)

    return dict(
        recovery_pos_au_max=float(rec_pos.max()),
        recovery_vel_kms_max=float(rec_vel.max()),
        recovery_pos_au_median=float(np.median(rec_pos)),
        recovery_vel_kms_median=float(np.median(rec_vel)),
        galilean_bias_pos_au=bias_pos,
        galilean_bias_vel_kms=bias_vel,
        galilean_bias_pos_au_median=float(np.median(bias_pos)),
        galilean_bias_vel_kms_median=float(np.median(bias_vel)),
        dtheta_arcsec=dtheta_arcsec,
        dtheta_arcsec_median=float(np.median(dtheta_arcsec)),
    )


def linearized_galilean_bias(star_pos, pairs, beta, n_runs, rng):
    """First-order cross-check of the classical bias (disclosed, order-of-mag).

    d_state = (J^T J)^-1 J^T d_theta, J the exact 6-state jacobian, d_theta the
    per-angle exact-vs-classical aberration difference at the true state. Agrees
    with the full solve only to order of magnitude (~12% median, up to ~330%
    tail disagreement) because the ~500-arcsec model error is far outside the
    linear regime — reported as a cross-check, never as the headline. The
    normal-equation solve assumes a non-singular J^T J (well-conditioned hub
    geometry).

    star_pos: (N, 3) au. pairs: (P, 2) int. beta: v/c, dimensionless. n_runs:
        ensemble size (count). rng: np.random.Generator.
    Returns: (median position bias au, median velocity bias km/s).
    """
    pos_true, vel_true, _ = _draw_truths(beta, n_runs, rng)
    exact_ang = predicted_pair_angles_moving(star_pos, pos_true, vel_true, pairs)
    gal_ang = galilean_predicted_pair_angles(star_pos, pos_true, vel_true, pairs)
    dtheta = exact_ang - gal_ang
    jac = pair_angle_state_jacobian(star_pos, pos_true, vel_true, pairs)
    jtj = np.einsum("...pi,...pj->...ij", jac, jac)
    jtd = np.einsum("...pi,...p->...i", jac, dtheta)
    dstate = np.linalg.solve(jtj, jtd[..., None])[..., 0]
    return (
        float(np.median(np.linalg.norm(dstate[:, :3], axis=1))),
        float(np.median(np.linalg.norm(dstate[:, 3:], axis=1))),
    )


def compute(n_runs=200, seed=42, beta=BETA_CRUISE, sigma_arcsec=1.0):
    """Compute every reported quantity for E7. Returns a dict for save_outputs.

    n_runs: ensemble size per part (count). seed: master seed (int; the parts
        use seed, seed+1, seed+2 for independent streams). beta: v/c,
        dimensionless. sigma_arcsec: camera noise for the noisy-recovery part,
        arcsec. Returns: dict of every plotted array + parameter.
    """
    stars, pairs = build_network()
    theta = np.linspace(1e-6, np.pi - 1e-6, 2001)
    gal_max, gal_peak = max_deflection(beta, relativistic=False)
    exact_max, exact_peak = max_deflection(beta, relativistic=True)
    clean = run_ensemble(stars, pairs, beta, n_runs, 0.0, np.random.default_rng(seed))
    noisy = run_ensemble(
        stars, pairs, beta, n_runs, sigma_arcsec, np.random.default_rng(seed + 1)
    )
    lin_pos, lin_vel = linearized_galilean_bias(
        stars, pairs, beta, n_runs, np.random.default_rng(seed + 2)
    )
    return dict(
        beta=float(beta),
        theta_grid_deg=np.degrees(theta),
        deflection_galilean_deg=np.degrees(galilean_deflection(beta, theta)),
        deflection_exact_deg=np.degrees(exact_deflection(beta, theta)),
        aber_max_galilean_deg=gal_max,
        aber_max_exact_deg=exact_max,
        aber_peak_galilean_deg=gal_peak,
        aber_peak_exact_deg=exact_peak,
        galilean_bias_pos_au=clean["galilean_bias_pos_au"],
        galilean_bias_vel_kms=clean["galilean_bias_vel_kms"],
        galilean_bias_pos_au_median=clean["galilean_bias_pos_au_median"],
        galilean_bias_vel_kms_median=clean["galilean_bias_vel_kms_median"],
        dtheta_arcsec_median=clean["dtheta_arcsec_median"],
        recovery_pos_au_max=clean["recovery_pos_au_max"],
        recovery_vel_kms_max=clean["recovery_vel_kms_max"],
        recovery_pos_au_median_noisy=noisy["recovery_pos_au_median"],
        recovery_vel_kms_median_noisy=noisy["recovery_vel_kms_median"],
        linearized_bias_pos_au_median=lin_pos,
        linearized_bias_vel_kms_median=lin_vel,
        n_runs=int(n_runs),
        seed=int(seed),
        sigma_arcsec=float(sigma_arcsec),
    )


def save_outputs(data, out_dir=RESULTS_DIR):
    """Write a timestamped .npz with every plotted array + parameter.

    data: the dict from compute(). out_dir: directory. Returns: the .npz Path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e7_relativistic_aberration_{stamp}.npz"
    np.savez(path, **data)
    return path


def _draw(fig, d):
    """Render the two E7 panels from a dict of arrays. Returns: None."""
    ax1, ax2 = fig.subplots(1, 2)
    theta = np.asarray(d["theta_grid_deg"], dtype=float)
    ax1.plot(theta, d["deflection_galilean_deg"], label="Galilean (classical)")
    ax1.plot(theta, d["deflection_exact_deg"], "--", label="exact relativistic")
    ax1.axvline(90.0, color="0.85", lw=0.7)
    ax1.set_xlabel("true angle from apex, deg")
    ax1.set_ylabel("aberration deflection, deg")
    ax1.set_title(
        f"Part A: max {float(d['aber_max_galilean_deg']):.3f} deg (Galilean) "
        f"vs {float(d['aber_max_exact_deg']):.3f} deg (exact)"
    )
    ax1.legend(fontsize=8)

    bias = np.asarray(d["galilean_bias_pos_au"], dtype=float)
    ax2.hist(bias, bins=24, color="tab:red", alpha=0.8)
    med = float(d["galilean_bias_pos_au_median"])
    ax2.axvline(med, color="k", lw=1.5, label=f"median {med:.0f} au")
    ax2.set_xlabel("classical-navigator position bias, au")
    ax2.set_ylabel("count")
    ax2.set_title(
        f"Part C: ignoring relativity at {float(d['beta']):.1f}c misses by ~{med:.0f} au"
    )
    ax2.legend(fontsize=8)
    fig.tight_layout()


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E7 figure from a saved .npz ALONE. Returns: the PNG Path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=True) as z:
        d = {k: z[k] for k in z.files}
    fig = plt.figure(figsize=(12, 5))
    _draw(fig, d)
    if out_png is None:
        out_png = npz_path.with_suffix(".png")
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return out_png


def main():
    """Compute, save arrays + figure, and print the headline. Returns: npz Path."""
    d = compute()
    path = save_outputs(d)
    png = replot_from_npz(path, out_png=path.with_suffix(".png"))
    print(f"wrote {path.name} and {png.name}")
    print(
        f"Part A: Galilean max {d['aber_max_galilean_deg']:.4f} deg (peak "
        f"{d['aber_peak_galilean_deg']:.2f}), exact max {d['aber_max_exact_deg']:.4f} deg "
        f"(peak {d['aber_peak_exact_deg']:.2f}); gap "
        f"{(d['aber_max_exact_deg'] - d['aber_max_galilean_deg']) * 3600:.1f} arcsec"
    )
    print(
        f"Part B: exact recovery at {d['beta']:.1f}c -> max {d['recovery_pos_au_max']:.2e} au, "
        f"{d['recovery_vel_kms_max']:.2e} km/s"
    )
    print(
        f"Part C: per-angle model error median {d['dtheta_arcsec_median']:.0f} arcsec; "
        f"classical navigator bias median {d['galilean_bias_pos_au_median']:.0f} au, "
        f"{d['galilean_bias_vel_kms_median']:.0f} km/s "
        f"(linearized cross-check {d['linearized_bias_pos_au_median']:.0f} au)"
    )
    return path


if __name__ == "__main__":
    main()
