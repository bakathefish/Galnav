"""Experiment E5-lite: the pulsar-comb lattice impossibility (a headline).

Shows, with the project's own §12 pulsar combs, WHY pulsar-only navigation
cannot be bootstrapped from a starlight position fix at interstellar range:
a star-only fix (~1 au ~ 1.5e8 km) is 4+ orders of magnitude coarser than
even the widest phase comb (Crab, ~10,073 km), so no comb's integer
turn-count can be locked. It also reproduces the 467 km comb coast budgets
(9 months at 1 cm/s, 3 days at 1 m/s).

This experiment is a PUBLIC-physics analysis: it touches neither the truth
simulator nor the navigator solver. It only uses galnav.pulsar (combs, the
ambiguity-lattice packing radius, coast time) and galnav.units.

It does NOT solve the general closest-vector integer-recovery problem
(LAMBDA/LLL or fpylll) -- that is a deferred follow-up card. The impossibility
here needs only the packing radius, which the module computes by bounded
enumeration.

Run:  python -m experiments.e5_pulsar_lattice   (writes results/ npz + PNG)
"""

from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from galnav.pulsar import (
    PULSAR_PERIODS_S,
    ambiguity_lattice_generator,
    coast_time_days,
    comb_spacing_km,
    packing_radius_km,
)
from galnav.units import AU_KM, C_KM_S
from tests.golden_numbers import BAILER_JONES_ANCHOR

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"

# Representative star-only position-fix uncertainties (au). The band spans the
# starlight results at 1 pc: the finest camera cell reaches ~0.01 au, the
# Bailer-Jones anchor ~3 au, and the E6 age-0 epoch parallax floor ~7.66 au.
STAR_FIX_AU_GRID = np.logspace(-2, 1, 31)  # 0.01 .. 10 au
STAR_FIX_REF_AU = 1.0  # the ~1 au scale in the E5-lite prediction
# Drift prevention: source the reference fixes from their canonical homes
# instead of retyping magic numbers. BJ anchor = the frozen golden
# Bailer-Jones position error; the E6 epoch floor is read at runtime from the
# blessed E6 archive (see _e6_epoch_floor_au), with the logbooked value as a
# fallback only if the archive is absent.
BJ_ANCHOR_AU = BAILER_JONES_ANCHOR["pos_err_au"]  # au (golden)
E6_FLOOR_FALLBACK_AU = 7.66  # au; E6 age-0 epoch parallax floor at 1 pc /
#                              20 stars (logbook 2026-07-16, blessed npz 60a8d4e)

# Velocity-uncertainty axis for the coast-budget panel (km/s): 1 mm/s .. 10 m/s.
SIGMA_V_KMS_GRID = np.array(
    [1e-6, 3.16e-6, 1e-5, 3.16e-5, 1e-4, 3.16e-4, 1e-3, 3.16e-3, 1e-2]
)
COMB_FOR_COAST = "B1937+21"  # the 467 km comb the budgets are quoted on

# A concrete, well-separated 3-pulsar geometry for the packing-radius demo.
PACKING_TRIPLE = ("B0531+21", "B1937+21", "J0030+0451")


def _triple_sightlines():
    """Three spread-out UNIT sightlines (not coplanar) for the lattice demo."""
    N = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, np.sqrt(0.5)],
        ]
    )
    return N / np.linalg.norm(N, axis=1, keepdims=True)


def _e6_epoch_floor_au():
    """E6 age-0 epoch parallax floor (au), read from the blessed E6 archive.

    Drift-proof source for the reference annotation: loads the newest blessed
    E6 npz and returns its age-0, finest-sensor RMS. Falls back to the
    logbooked E6_FLOOR_FALLBACK_AU only if no archive file is present.

    Returns: float, au.
    """
    archive = sorted((REPO_ROOT / "results" / "archive").glob("e6_catalog_aging_*.npz"))
    if not archive:
        return float(E6_FLOOR_FALLBACK_AU)
    with np.load(archive[-1], allow_pickle=True) as z:
        rms = np.asarray(z["rms_au"])
        sig = np.asarray(z["sigmas_rad"])
    return float(rms[0, int(np.argmin(sig))])


def compute():
    """Compute every plotted array. Returns a dict ready for save_outputs.

    Return-dict units: pulsar_names (str); periods_s (s); comb_km (km);
    star_fix_au (au) / star_fix_km (km); star_fix_ref_au, bj_anchor_au,
    e6_floor_au (au); sigma_v_kms (km/s); coast_days (days);
    comb_for_coast_km (km); packing_names (str); packing_radius_km (km);
    gap_widest / gap_finest (dimensionless ratios); au_km (km/au);
    c_km_s (km/s).
    """
    names = list(PULSAR_PERIODS_S)
    periods_s = np.array([PULSAR_PERIODS_S[n] for n in names])
    comb_km = comb_spacing_km(periods_s)

    star_fix_km = STAR_FIX_AU_GRID * AU_KM
    widest_comb = float(np.max(comb_km))
    finest_comb = float(np.min(comb_km))
    gap_widest = (STAR_FIX_REF_AU * AU_KM) / widest_comb
    gap_finest = (STAR_FIX_REF_AU * AU_KM) / finest_comb

    coast_days = coast_time_days(
        comb_spacing_km(PULSAR_PERIODS_S[COMB_FOR_COAST]), SIGMA_V_KMS_GRID
    )

    N = _triple_sightlines()
    triple_comb = np.array(
        [comb_spacing_km(PULSAR_PERIODS_S[n]) for n in PACKING_TRIPLE]
    )
    B = ambiguity_lattice_generator(N, triple_comb)
    rho_km = packing_radius_km(B)

    return dict(
        pulsar_names=np.array(names),
        periods_s=periods_s,
        comb_km=comb_km,
        star_fix_au=STAR_FIX_AU_GRID,
        star_fix_km=star_fix_km,
        star_fix_ref_au=float(STAR_FIX_REF_AU),
        bj_anchor_au=float(BJ_ANCHOR_AU),
        e6_floor_au=float(_e6_epoch_floor_au()),
        sigma_v_kms=SIGMA_V_KMS_GRID,
        coast_days=coast_days,
        comb_for_coast_km=float(comb_spacing_km(PULSAR_PERIODS_S[COMB_FOR_COAST])),
        packing_names=np.array(PACKING_TRIPLE),
        packing_radius_km=float(rho_km),
        gap_widest=float(gap_widest),
        gap_finest=float(gap_finest),
        au_km=float(AU_KM),
        c_km_s=float(C_KM_S),
    )


def save_outputs(data, out_dir=RESULTS_DIR):
    """Write a timestamped .npz with every plotted array + params."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e5_pulsar_lattice_{stamp}.npz"
    np.savez(path, **data)
    return path


def _draw(fig, d):
    """Render the two panels into fig from a plain dict of arrays."""
    ax1, ax2 = fig.subplots(1, 2)

    # Panel 1: comb spacings vs star-fix uncertainty, on a shared km log axis.
    names = [str(n) for n in d["pulsar_names"]]
    comb_km = np.asarray(d["comb_km"])
    star_fix_km = np.asarray(d["star_fix_km"])
    au_km = float(d["au_km"])

    ax1.fill_between(
        [0, 1],
        star_fix_km.min(),
        star_fix_km.max(),
        color="tab:orange",
        alpha=0.18,
        label="star-only fix (E1: 0.01-10 au)",
    )
    for ref_au, lab in [
        (float(d["star_fix_ref_au"]), "~1 au fix"),
        (float(d["bj_anchor_au"]), f"BJ anchor {float(d['bj_anchor_au']):.0f} au"),
        (float(d["e6_floor_au"]), f"E6 epoch floor {float(d['e6_floor_au']):.2f} au"),
    ]:
        ax1.axhline(ref_au * au_km, color="tab:orange", lw=1.0, ls="--")
        ax1.text(0.02, ref_au * au_km * 1.05, lab, fontsize=7, color="tab:orange")
    for name, s in zip(names, comb_km):
        ax1.axhline(s, color="tab:blue", lw=1.2)
        ax1.text(0.55, s * 1.03, f"{name}  {s:,.0f} km", fontsize=7, color="tab:blue")

    ax1.set_yscale("log")
    ax1.set_xlim(0, 1)
    ax1.set_xticks([])
    ax1.set_ylabel("length scale, km (log)")
    ax1.set_title(
        f"phase combs ({comb_km.min():,.0f}-{comb_km.max():,.0f} km)\n"
        f"vs star fix ~1 au: gap x{d['gap_widest']:,.0f} to widest comb"
    )
    ax1.legend(loc="lower right", fontsize=7)

    # Panel 2: coast time to lost lock vs velocity uncertainty, 467 km comb.
    sig = np.asarray(d["sigma_v_kms"])
    coast = np.asarray(d["coast_days"])
    ax2.loglog(sig * 1e3, coast, "o-", color="tab:green")  # x in m/s
    for v_ms, tag in [(1e-2, "1 cm/s"), (1.0, "1 m/s")]:
        t = 0.5 * float(d["comb_for_coast_km"]) / (v_ms * 1e-3) / 86400.0
        ax2.plot([v_ms], [t], "s", color="tab:red")
        ax2.text(
            v_ms,
            t * 1.3,
            f"{tag}\n{t:.0f} d" if t > 10 else f"{tag}\n{t:.1f} d",
            fontsize=7,
            ha="center",
            color="tab:red",
        )
    ax2.set_xlabel("velocity uncertainty, m/s (log)")
    ax2.set_ylabel("coast time to lost lock, days (log)")
    ax2.set_title(f"{d['comb_for_coast_km']:,.0f} km comb: T = (s/2)/sigma_v")
    ax2.grid(True, which="both", alpha=0.3)

    fig.suptitle(
        "E5-lite - pulsar phase-comb navigation is unreachable from a starlight fix",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E5-lite figure from a saved .npz ALONE (no recompute)."""
    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=True) as z:
        d = {k: z[k] for k in z.files}
    fig = plt.figure(figsize=(11, 5))
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
        f"comb spacings (km): "
        f"{', '.join(f'{n}={s:,.0f}' for n, s in zip(d['pulsar_names'], d['comb_km']))}"
    )
    print(
        f"star fix 1 au is x{d['gap_widest']:,.0f} the widest comb, "
        f"x{d['gap_finest']:,.0f} the finest comb"
    )
    print(
        f"packing radius of {tuple(d['packing_names'])}: {d['packing_radius_km']:,.1f} km "
        f"-> 1 au / rho = {d['au_km'] / d['packing_radius_km']:,.0f}"
    )
    i_1cm = int(np.argmin(np.abs(d["sigma_v_kms"] - 1e-5)))
    i_1m = int(np.argmin(np.abs(d["sigma_v_kms"] - 1e-3)))
    print(
        f"coast on 467 km comb: {d['coast_days'][i_1cm]:.1f} d at 1 cm/s, "
        f"{d['coast_days'][i_1m]:.2f} d at 1 m/s"
    )
    return path


if __name__ == "__main__":
    main()
