"""E4 -- real NICER photons: inject a known orbit bias, recover it. (armor)

AI-authored under the build-night ratification-pending pattern; worksheet
item (ii). Runs ONLY inside the WSL2 armor environment
(journal/environment-armor.md):

    wsl -d Ubuntu -u root -- bash -lc \
      "cd /mnt/c/Users/rudra/OneDrive/Desktop/spacenav && \
       /opt/galnav/venv/bin/python -m experiments.e4_nicer_photon"

The claim this experiment demonstrates, on REAL data: pulsar photon phases
carry spacecraft position information. A navigator whose ISS ephemeris is
wrong by a constant vector dr sees every pulsar's fold shifted by
dphi_p = f0_p (dr . n_hat_p) / c; with three well-separated sightlines
(J0030+0451, B1937+21, J0437-4715) the full 3-D dr is recoverable from
three fold shifts. Truth injects dr into the orbit files; nav sees only
the measured shifts + public pulsar facts and must recover dr within
2 sigma -- three independent seeded injections (compass section 7's own
pass criterion). All machinery: tests_armor/_e4_fold.py, gated by
tests_armor/test_e4_injection.py; every fold rides Spec 9's bit-verified
photon->phase chain.

Headline seed 42 (house convention for blessed runs; the acceptance test
runs the same pipeline at its own seed). Outputs: timestamped .npz with
every plotted array + a PNG regenerable from the .npz alone
(replot_from_npz, returns the PNG Path).
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from tests_armor import _e4_fold as e4

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data/e4_nicer"
RESULTS_DIR = REPO / "results"

EPHEM = "DE440"  # all three NG15 pars state EPHEM DE440
SEED = 42  # house blessed-run seed
N_BOOT = 200
BIAS_KM = 100.0  # up to 0.214 turns on B1937 -- decisive vs the measured
# shift noise, comfortably under the 233 km / 0.5-turn wrap ceiling
N_INJECTIONS = 3

# The same six observations + bands the acceptance test pins (kept inline
# and explicit, house experiment style; provenance in data/e4_nicer/README.md).
PULSARS = {
    "J0030+0451": {
        "par": DATA / "pars/J0030+0451_PINT_20220302.nb.par",
        "pi_band": (30, 150),
        "template_evt": DATA
        / "2017_08/1060020113/xti/event_cl/ni1060020113_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_08/1060020113/auxil/ni1060020113.orb.gz",
        "meas_evt": DATA
        / "2018_01/1060020263/xti/event_cl/ni1060020263_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2018_01/1060020263/auxil/ni1060020263.orb.gz",
    },
    "B1937+21": {
        "par": DATA / "pars/B1937+21_PINT_20220306.nb.par",
        "pi_band": (120, 400),  # band-scan choice; see the acceptance test
        "template_evt": DATA
        / "2017_09/1070020147/xti/event_cl/ni1070020147_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_09/1070020147/auxil/ni1070020147.orb.gz",
        "meas_evt": DATA
        / "2017_09/1070020148/xti/event_cl/ni1070020148_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2017_09/1070020148/auxil/ni1070020148.orb.gz",
    },
    "J0437-4715": {
        "par": DATA / "pars/J0437-4715_PINT_20220301.nb.par",
        "pi_band": (30, 150),
        "template_evt": DATA
        / "2017_10/1060010157/xti/event_cl/ni1060010157_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_10/1060010157/auxil/ni1060010157.orb.gz",
        "meas_evt": DATA
        / "2017_12/1060010188/xti/event_cl/ni1060010188_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2017_12/1060010188/auxil/ni1060010188.orb.gz",
    },
}


def compute():
    """Run the full injection/recovery experiment; flatten for the npz.

    Returns: dict of flat numpy arrays / scalars (npz- and plot-ready):
    profiles + labels, H-tests, photon counts, TOA sigmas, per-injection
    truths/recoveries/errors/sigmas/shifts, geometry, and parameters.
    """
    res = e4.run_experiment(
        PULSARS,
        ephem=EPHEM,
        bias_km=BIAS_KM,
        n_injections=N_INJECTIONS,
        n_boot=N_BOOT,
        seed=SEED,
    )
    names = res["pulsars"]
    fold_labels = sorted(res["htests"])
    inj = res["injections"]
    d = {
        "pulsar_names": np.array(names),
        "f0s_hz": res["f0s_hz"],
        "n_hats": res["n_hats"],
        "fold_labels": np.array(fold_labels),
        "htests": np.array([res["htests"][k] for k in fold_labels]),
        "fold_n_photons": np.array([res["n_photons"][k] for k in fold_labels]),
        "toa_sigmas_s": np.array([res["toa_sigmas_s"][n] for n in names]),
        "profile_labels": np.array(fold_labels),
        "profiles": np.stack([res["profiles"][k] for k in fold_labels]),
        "dr_true_km": np.stack([i["dr_true_km"] for i in inj]),
        "dr_hat_km": np.stack([i["dr_hat_km"] for i in inj]),
        "err_coeffs_km": np.stack([i["projected_error_coeffs_km"] for i in inj]),
        "sigma_coeffs_km": np.stack([i["projected_sigma_km"] for i in inj]),
        "shifts_turns": np.stack([i["shifts_turns"] for i in inj]),
        "shift_sigmas_turns": np.stack([i["sigmas_turns"] for i in inj]),
        "cov_km2": np.stack([i["cov_km2"] for i in inj]),
        "seed": SEED,
        "bias_km": BIAS_KM,
        "n_boot": N_BOOT,
        "n_injections": N_INJECTIONS,
        "ephem": np.array(EPHEM),
        "pi_bands": np.array([list(PULSARS[n]["pi_band"]) for n in names]),
    }
    # predicted shifts from the injected truths (truth-side bookkeeping for
    # the figure's measured-vs-predicted panel; the nav side never sees it)
    A = (res["f0s_hz"][:, None] / e4.C_KM_S) * res["n_hats"]  # (3,3) turns/km
    d["shifts_predicted_turns"] = d["dr_true_km"] @ A.T
    return d


def save_outputs(data, out_dir=RESULTS_DIR):
    """Write a timestamped .npz with every plotted array + parameter.

    data: the dict from compute(). out_dir: directory. Returns: the .npz Path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"e4_bias_recovery_{stamp}.npz"
    np.savez(path, **data)
    return path


def _draw(fig, d):
    """Render the three E4 panels from a dict of arrays. Returns: None."""
    ax1, ax2, ax3 = fig.subplots(1, 3)

    labels = [str(x) for x in d["profile_labels"]]
    profiles = np.asarray(d["profiles"], dtype=float)
    bins = np.linspace(0.0, 1.0, profiles.shape[1] + 1)
    centres = 0.5 * (bins[:-1] + bins[1:])
    for i, lab in enumerate(labels):
        prof = profiles[i] / profiles[i].mean()
        ax1.plot(centres, prof + 1.2 * i, lw=0.9, label=lab)
    ax1.set_xlabel("pulse phase, turns")
    ax1.set_ylabel("counts / mean, offset per fold")
    ax1.set_title("energy-filtered folds (real NICER photons)")
    ax1.legend(fontsize=5)

    meas = np.asarray(d["shifts_turns"], dtype=float).ravel()
    pred = np.asarray(d["shifts_predicted_turns"], dtype=float).ravel()
    serr = np.asarray(d["shift_sigmas_turns"], dtype=float).ravel()
    ax2.errorbar(pred, meas, yerr=serr, fmt="o", ms=4, lw=0.8)
    lim = 1.1 * float(np.max(np.abs(np.concatenate([pred, meas]))))
    ax2.plot([-lim, lim], [-lim, lim], "0.8", lw=0.7)
    ax2.set_xlabel("predicted shift f0 (dr.n)/c, turns")
    ax2.set_ylabel("measured fold shift, turns")
    ax2.set_title("9 pulsar-injection pairs vs prediction")

    err = np.asarray(d["err_coeffs_km"], dtype=float)
    sig = np.asarray(d["sigma_coeffs_km"], dtype=float)
    x = np.arange(err.size, dtype=float)
    ax3.errorbar(x, err.ravel(), yerr=2.0 * sig.ravel(), fmt="o", ms=4, lw=0.8)
    ax3.axhline(0.0, color="0.8", lw=0.7)
    ax3.set_xlabel("injection x component (3 x 3)")
    ax3.set_ylabel("recovery error, km (bars = 2 sigma)")
    ax3.set_title(
        f"bias {float(d['bias_km']):.0f} km recovered within 2 sigma, "
        f"{int(d['n_injections'])} injections"
    )


def replot_from_npz(npz_path, out_png=None):
    """Regenerate the E4 figure from a saved .npz ALONE. Returns: the PNG Path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=True) as z:
        d = {k: z[k] for k in z.files}
    fig = plt.figure(figsize=(15, 5))
    _draw(fig, d)
    if out_png is None:
        out_png = npz_path.with_suffix(".png")
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return Path(out_png)


def main():
    """Compute, save arrays + figure, and print the headline. Returns: npz Path."""
    d = compute()
    path = save_outputs(d)
    png = replot_from_npz(path, out_png=path.with_suffix(".png"))
    print(f"wrote {path.name} and {png.name}")
    names = [str(x) for x in d["pulsar_names"]]
    print(
        "folds: "
        + "; ".join(
            f"{str(lab)} H={h:.0f}" for lab, h in zip(d["fold_labels"], d["htests"])
        )
    )
    print(
        "TOA sigma (us): "
        + ", ".join(f"{n} {s * 1e6:.1f}" for n, s in zip(names, d["toa_sigmas_s"]))
    )
    for j in range(int(d["n_injections"])):
        err = d["err_coeffs_km"][j]
        sig = d["sigma_coeffs_km"][j]
        worst = float(np.max(np.abs(err) / sig))
        print(
            f"injection-{j + 1}: |dr_true| = {np.linalg.norm(d['dr_true_km'][j]):.1f} km, "
            f"|recovery error| = {np.linalg.norm(err):.3f} km, "
            f"worst component {worst:.2f} sigma (gate 2.0)"
        )
    return path


if __name__ == "__main__":
    main()
