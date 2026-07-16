"""E4 machinery: fold real pulsar photons, inject an orbit bias, recover it.

Armor tier (WSL2 only; journal/environment-armor.md). Builds directly on
tests_armor/_pint_routes.py (Spec 9's proven photon->phase chain).

The experiment in one breath (full story in journal/e4-nicer-injection.md):
a navigator that believes a WRONG spacecraft ephemeris computes wrong
barycentric times, so every pulsar's measured pulse phase slides by

    dphi_p = f0_p * (dr . n_hat_p) / c        [turns]

-- the bias dr projected on the pulsar's sightline, in light-time, times
the spin frequency. Measure dphi on pulsars with THREE independent
sightlines and the linear system inverts back to the full 3-D dr. E4 does
this with real NICER photons: inject a KNOWN dr into the ISS orbit file
(truth side), watch the folds shift, recover dr (nav side), and demand
agreement within 2 sigma.

TRUTH WALL inside this module: inject_orbit_bias is the TRUTH side (it
knows dr). recover_bias is the NAV side -- a pure function of measured
shifts, their uncertainties, and PUBLIC pulsar facts (f0, sightline); it
never sees the injected vector. run_experiment passes only measurements
across, exactly like every experiment script in this project.

ENERGY CUTS (measured necessity, journal section "the background lesson"):
NICER is not an imager -- every X-ray in the field lands in the event
list, and the fraction that is PULSAR varies wildly between observations
(measured: J0030's 2017-08 ObsID is 93% background above 1.5 keV, burying
the pulse at H = 5.1; its soft 0.3-1.5 keV band restores it). Each pulsar
therefore carries a documented PI band (NICER PI = energy/10 eV): the
soft band for the thermal pulsars (J0030, J0437), a hard band for
non-thermal B1937. Filtering happens identically for template and
measurement folds, before any orbit is touched, so it cannot know or leak
the injection.

Statistical honesty (why two ObsIDs per pulsar): each pulsar's template
peak comes from a DIFFERENT observation (independent photons, months
apart) than the measurement fold, so the shift error bar
sigma^2 = sigma_meas^2 + sigma_template^2 is real photon statistics, not a
fold compared against itself. The price, stated openly: any cross-epoch
phase-connection error of the timing model (NG15 rms residuals are
sub-microsecond, ~1e-4 turns -- tiny against the ~2e-2..6e-2-turn
injected signals) rides in the residual, where it belongs; and the one
shared template per pulsar mildly correlates the three injections'
errors (recorded in the journal).

Units: phases in turns (fraction in [0,1) unless stated); positions km;
frequencies Hz; times s; PI in NICER channels (10 eV each).
"""

import tempfile
from pathlib import Path

import numpy as np

C_KM_S = 299792.458  # speed of light, km/s (SI definition; [SI] in citations)

_BOOT_CHUNK = 50  # bootstrap replicates per vectorized block (memory cap;
# a fixed small block loop, not a loop over trials -- each block is fully
# vectorized)


def filter_events_pi(evt_path, pi_band, out_path):
    """Write a copy of an event file keeping only one energy band.

    Standard NICER screening: keep EVENTS rows with pi_band[0] <= PI <=
    pi_band[1] (PI = photon energy / 10 eV). Applied IDENTICALLY to
    template and measurement observations, before any orbit file enters
    the story -- energy knows nothing about the injected bias. All other
    extensions (GTIs etc.) ride along; header EXPOSURE keywords become
    stale for the filtered copy, which is harmless for phase computation
    (PINT reads photon TIME rows, not exposure summaries) and is recorded
    in the journal.

    evt_path: source .evt(.gz) FITS. pi_band: (lo, hi) inclusive channels.
    out_path: destination .fits (plain). Returns: str(out_path).
    """
    from astropy.io import fits

    lo, hi = int(pi_band[0]), int(pi_band[1])
    with fits.open(str(evt_path)) as hdul:
        events = hdul["EVENTS"]
        pi = np.asarray(events.data["PI"], dtype=np.int64)
        mask = (pi >= lo) & (pi <= hi)
        events.data = events.data[mask]
        hdul.writeto(str(out_path), overwrite=True)
    return str(out_path)


def inject_orbit_bias(orb_path, delta_r_km, out_path):
    """TRUTH SIDE: write a copy of an FPorbit file with a constant bias.

    Adds delta_r (a constant geocentric J2000 offset, km) to the ORBIT
    extension's X/Y/Z columns (stored in metres; measured structure:
    ni*.orb ext 1 'ORBIT', TIME s / X,Y,Z m / Vx,Vy,Vz m/s); velocities
    untouched (a constant offset has zero time derivative). PINT's
    load_FPorbit reads exactly this extension, so the biased file models a
    navigator whose ISS ephemeris is wrong by exactly delta_r. The
    SPS_ORBIT extension rides along unmodified (PINT does not read it).

    orb_path: source .orb(.gz) FITS path. delta_r_km: (3,) offset in km.
    out_path: destination .fits path (plain FITS, not gzipped).
    Returns: str(out_path).
    """
    from astropy.io import fits

    delta_m = np.asarray(delta_r_km, dtype=np.float64) * 1000.0  # km -> m
    with fits.open(str(orb_path)) as hdul:
        orbit = hdul["ORBIT"]
        for i, axis in enumerate(("X", "Y", "Z")):
            orbit.data[axis] = orbit.data[axis] + delta_m[i]
        hdul.writeto(str(out_path), overwrite=True)
    return str(out_path)


def first_harmonic_peak(frac):
    """Fold peak phase from the first Fourier harmonic (circular mean).

    phi_hat = atan2(sum sin 2*pi*phi_i, sum cos 2*pi*phi_i) / (2*pi), mapped
    to [0, 1). For ANY pulse shape this estimator returns a fixed reference
    point of the profile; two folds of the same profile shifted by d land
    exactly d apart -- which is all the experiment needs (it measures phase
    DIFFERENCES, never absolute peak positions).

    frac: float64 array of photon phases in [0, 1).
    Returns: float64 scalar peak phase in [0, 1).
    """
    ang = 2.0 * np.pi * np.asarray(frac, dtype=np.float64)
    s = float(np.sin(ang).sum())
    c = float(np.cos(ang).sum())
    return float((np.arctan2(s, c) / (2.0 * np.pi)) % 1.0)


def htest(frac):
    """The de Jager H-test statistic for pulsation significance.

    Z^2_m = (2/N) * sum_{k=1..m} [ (sum cos k*ang)^2 + (sum sin k*ang)^2 ]
    and H = max over m = 1..20 of ( Z^2_m - 4m + 4 ) -- the statistic of
    de Jager, Raubenheimer & Swanepoel (1989). The significance shorthand
    p ~ exp(-0.4 H) is the later calibration of de Jager & Buesching
    (2010) [deJagerBusching10]. Bigger = the fold is more obviously a
    pulse and not noise. Used by the fold-cleanliness gate (the compass's
    Sep-5 criterion) via the frozen E4_HTEST_MIN.

    frac: float64 array of photon phases in [0, 1).
    Returns: float64 scalar H.
    """
    ang = 2.0 * np.pi * np.asarray(frac, dtype=np.float64)
    n = ang.size
    ks = np.arange(1, 21, dtype=np.float64)[:, None]  # 20 harmonics
    ka = ks * ang[None, :]
    C = np.cos(ka).sum(axis=1)
    S = np.sin(ka).sum(axis=1)
    z2m = (2.0 / n) * np.cumsum(C**2 + S**2)
    m = np.arange(1, 21, dtype=np.float64)
    return float(np.max(z2m - 4.0 * m + 4.0))


def bootstrap_peak_sigma(frac, n_boot, rng):
    """Photon-statistics error bar on first_harmonic_peak, by bootstrap.

    Resamples the photons with replacement n_boot times, recomputes the
    peak per replicate, and returns the circular standard deviation of the
    replicate peaks around the full-sample peak. This is the fold's own
    noise floor: how much the measured peak would wobble if the
    observation were rerun. Replicates are processed in fixed vectorized
    blocks of _BOOT_CHUNK (memory cap), never one at a time.

    frac: float64 photon phases in [0, 1). n_boot: replicate count (int).
    rng: np.random.Generator (explicit, per project rule).
    Returns: float64 scalar sigma in turns.
    """
    frac = np.asarray(frac, dtype=np.float64)
    n = frac.size
    ang = 2.0 * np.pi * frac
    sin_a = np.sin(ang)
    cos_a = np.cos(ang)
    peaks = np.empty(n_boot, dtype=np.float64)
    done = 0
    while done < n_boot:
        block = min(_BOOT_CHUNK, n_boot - done)
        idx = rng.integers(0, n, size=(block, n))
        s = sin_a[idx].sum(axis=1)
        c = cos_a[idx].sum(axis=1)
        peaks[done : done + block] = (np.arctan2(s, c) / (2.0 * np.pi)) % 1.0
        done += block
    centre = first_harmonic_peak(frac)
    return float(np.std(circular_diff(peaks, centre)))


def circular_diff(a, b):
    """Signed smallest phase difference a - b on the circle, in [-0.5, 0.5).

    a, b: phases in turns (scalars or arrays).
    Returns: signed difference in turns.
    """
    return (
        np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64) + 0.5
    ) % 1.0 - 0.5


def fold_observation(evt_path, par_path, orb_path, ephem, pi_band, n_boot, rng):
    """Filter, phase, and fold one observation; return its measurements.

    The one composite step every fold shares: energy-filter the events to
    the pulsar's documented PI band, run Spec 9's proven photon->phase
    chain on the filtered copy, and reduce to (peak, sigma, H, N).

    evt_path/par_path/orb_path/ephem: as in _pint_routes.phases_library.
    pi_band: (lo, hi) PI channels. n_boot: bootstrap replicates.
    rng: np.random.Generator.
    Returns: dict with peak (turns), sigma (turns), htest, n_photons, and
        profile -- a (64,) int64 histogram of the fold over [0, 1) (the
        figure's raw material; 64 bins is display resolution, load-bearing
        on nothing).
    """
    from tests_armor import _pint_routes as routes

    with tempfile.TemporaryDirectory() as td:
        filtered = filter_events_pi(evt_path, pi_band, Path(td) / "band.evt.fits")
        _, _, _, frac = routes.phases_library(filtered, par_path, orb_path, ephem)
    profile, _ = np.histogram(frac, bins=64, range=(0.0, 1.0))
    return {
        "peak": first_harmonic_peak(frac),
        "sigma": bootstrap_peak_sigma(frac, n_boot, rng),
        "htest": htest(frac),
        "n_photons": int(frac.size),
        "profile": profile.astype(np.int64),
    }


def run_experiment(pulsars, ephem, bias_km, n_injections, n_boot, seed):
    """Orchestrate the full injection/recovery experiment (truth + nav).

    For each pulsar: fold the TEMPLATE observation with its true orbit
    (reference peak, H-test, bootstrap sigma); then for each of
    n_injections seeded bias vectors: inject the bias into the MEASUREMENT
    observation's orbit (truth side), fold the (energy-filtered)
    measurement, measure the shift vs the template peak, and hand ONLY
    (shifts, sigmas, f0s, sightlines) to recover_bias (nav side).
    Deterministic under `seed` (folds themselves are deterministic --
    Spec 9 T3 -- and every random draw comes from the one seeded generator
    in a fixed order).

    The loops here run over 3 pulsars and 3 injections -- fixed, small,
    and each iteration is a fully vectorized fold; nothing loops over
    photons or Monte-Carlo trials.

    pulsars: dict name -> {par, template_evt, template_orb, meas_evt,
        meas_orb, pi_band} paths + band. ephem: JPL ephemeris name.
    bias_km: injected magnitude (km; directions drawn from the seeded
    rng). n_injections / n_boot: counts. seed: rng seed (int).
    Returns: dict with "pulsars" (ordered names), "f0s_hz", "n_hats",
        "htests" (name:role -> H), "n_photons" (name:role -> filtered N),
        "toa_sigmas_s" (name -> measurement-fold TOA sigma, s),
        "templates" (name -> peak/sigma), and "injections": list of dicts
        with label, dr_true_km, dr_hat_km, cov_km2, projector,
        projected_error_coeffs_km, projected_sigma_km, shifts_turns,
        sigmas_turns -- everything the npz/journal needs.
    """
    from tests_armor import _pint_routes as routes

    rng = np.random.default_rng(seed)
    names = list(pulsars)

    f0s = []
    n_hats = []
    templates = {}
    htests_out = {}
    n_photons = {}
    toa_sigmas = {}
    profiles_out = {}  # 64-bin fold histograms for the figure/npz

    for name in names:
        cfg = pulsars[name]
        tmpl = fold_observation(
            cfg["template_evt"],
            cfg["par"],
            cfg["template_orb"],
            ephem,
            cfg["pi_band"],
            n_boot,
            rng,
        )
        templates[name] = tmpl
        htests_out[f"{name}:template"] = tmpl["htest"]
        n_photons[f"{name}:template"] = tmpl["n_photons"]
        profiles_out[f"{name}:template"] = tmpl["profile"]
        sd = routes.parse_spindown_longdouble(cfg["par"])
        f0s.append(float(sd["F0"]))
        from pint.models import get_model

        n_hats.append(routes.pulsar_unit_vector(get_model(str(cfg["par"]))))

    f0s = np.asarray(f0s, dtype=np.float64)
    n_hats = np.asarray(n_hats, dtype=np.float64)

    directions = rng.standard_normal((n_injections, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    dr_trues = bias_km * directions

    injections = []
    for j in range(n_injections):
        label = f"injection-{j + 1}"
        shifts = []
        sigmas = []
        for k, name in enumerate(names):
            cfg = pulsars[name]
            with tempfile.TemporaryDirectory() as td:
                biased_orb = inject_orbit_bias(
                    cfg["meas_orb"], dr_trues[j], Path(td) / "biased.orb.fits"
                )
                meas = fold_observation(
                    cfg["meas_evt"],
                    cfg["par"],
                    biased_orb,
                    ephem,
                    cfg["pi_band"],
                    n_boot,
                    rng,
                )
            if j == 0:
                htests_out[f"{name}:measurement"] = meas["htest"]
                n_photons[f"{name}:measurement"] = meas["n_photons"]
                toa_sigmas[name] = meas["sigma"] / f0s[k]
                profiles_out[f"{name}:measurement"] = meas["profile"]
            shifts.append(float(circular_diff(meas["peak"], templates[name]["peak"])))
            sigmas.append(float(np.hypot(meas["sigma"], templates[name]["sigma"])))
        shifts = np.asarray(shifts, dtype=np.float64)
        sigmas = np.asarray(sigmas, dtype=np.float64)

        rec = recover_bias(shifts, sigmas, f0s, n_hats)
        basis = rec["basis"]  # (rank, 3); rank 3 with three sightlines
        err = basis @ (rec["dr_hat_km"] - dr_trues[j])
        sig_proj = np.sqrt(np.diag(basis @ rec["cov_km2"] @ basis.T))
        injections.append(
            {
                "label": label,
                "dr_true_km": dr_trues[j],
                "dr_hat_km": rec["dr_hat_km"],
                "cov_km2": rec["cov_km2"],
                "projector": rec["projector"],
                "projected_error_coeffs_km": err,
                "projected_sigma_km": sig_proj,
                "shifts_turns": shifts,
                "sigmas_turns": sigmas,
            }
        )

    return {
        "pulsars": names,
        "f0s_hz": f0s,
        "n_hats": n_hats,
        "htests": htests_out,
        "n_photons": n_photons,
        "toa_sigmas_s": toa_sigmas,
        "profiles": profiles_out,
        "templates": {
            k: {"peak": v["peak"], "sigma": v["sigma"]} for k, v in templates.items()
        },
        "injections": injections,
    }


def rerun_recoveries(result, seed):
    """Re-derive every recovery from cached fold measurements (T4 helper).

    Uses the shift measurements already inside `result` (no re-folding),
    reruns only the nav-side solve, and returns a structure shaped like
    run_experiment's "injections" for comparison. The recovery itself is
    deterministic linear algebra; `seed` is accepted for signature honesty
    (nothing stochastic remains at this stage) and to keep T4's contract
    explicit.

    result: run_experiment output. seed: same seed (unused by the math).
    Returns: dict with "injections" (label + dr_hat_km per injection).
    """
    del seed  # recovery is deterministic; the folds already happened
    out = []
    for inj in result["injections"]:
        rec = recover_bias(
            inj["shifts_turns"],
            inj["sigmas_turns"],
            result["f0s_hz"],
            result["n_hats"],
        )
        out.append({"label": inj["label"], "dr_hat_km": rec["dr_hat_km"]})
    return {"injections": out}


def recover_bias(shifts_turns, sigmas_turns, f0s_hz, n_hats):
    """NAV SIDE: invert measured phase shifts into the orbit-bias vector.

    The model: shifts_p = (f0_p / c) * (n_hat_p . dr), one equation per
    pulsar. Weighted least squares with W = diag(1/sigma^2):

        A[p, :] = (f0_p / C_KM_S) * n_hat_p          [turns per km]
        dr_hat  = pinv(W^(1/2) A) W^(1/2) shifts     (minimum-norm WLS)

    With K >= 3 well-spread sightlines the full 3-D bias is observable
    (basis = all of R^3); with K < 3 only the projection onto span(rows of
    A) is, and the function returns exactly that subspace. It sees ONLY
    measurements and public pulsar facts -- never the injected truth.

    shifts_turns: (K,) measured phase shifts. sigmas_turns: (K,) their
    1-sigma errors. f0s_hz: (K,) spin frequencies. n_hats: (K, 3) unit
    sightlines (ICRS).
    Returns: dict with dr_hat_km (3,), cov_km2 (3, 3) (rank K), basis
        (rank, 3) orthonormal rows spanning the observable subspace, and
        projector (3, 3) onto it.
    """
    shifts = np.asarray(shifts_turns, dtype=np.float64)
    sigmas = np.asarray(sigmas_turns, dtype=np.float64)
    f0s = np.asarray(f0s_hz, dtype=np.float64)
    n_hats = np.asarray(n_hats, dtype=np.float64)

    A = (f0s[:, None] / C_KM_S) * n_hats  # (K, 3), turns per km
    w = 1.0 / sigmas
    Aw = A * w[:, None]
    sw = shifts * w
    Aw_pinv = np.linalg.pinv(Aw)  # (3, K)
    dr_hat = Aw_pinv @ sw
    cov = Aw_pinv @ Aw_pinv.T  # (3, 3), rank K

    _, svals, vt = np.linalg.svd(A, full_matrices=False)
    rank = int(np.sum(svals > svals.max() * 1e-12))
    basis = vt[:rank]  # (rank, 3) orthonormal rows
    projector = basis.T @ basis
    return {
        "dr_hat_km": dr_hat,
        "cov_km2": cov,
        "basis": basis,
        "projector": projector,
    }
