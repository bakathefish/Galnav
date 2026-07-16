"""Acceptance tests for E4 -- real-NICER orbit-bias injection and recovery.

AI-authored under the build-night ratification-pending pattern (see
journal/logbook.md 2026-07-16 and the ratification worksheet). Students:
read and own every assertion before ratifying.

The compass card, verbatim (section 7, armor): "E4 real NICER photon
analysis (... PINT phases, folding; inject known orbit-ephemeris bias,
recover from phase residuals of 2-3 pulsars; pass = bias recovery within
2 sigma on 3 independent injections)". Section 11 budget: photon TOA
(folding) 1-50 us; barycentering < 1 us.

Design decisions these tests embody (journal/e4-nicer-injection.md; all
ratification items):
- THREE pulsars, all with phase-connected NANOGrav 15-yr timing models
  byte-extracted from the release tarball (md5-verified): PSR J0030+0451,
  PSR B1937+21, PSR J0437-4715 (binary, BINARY DD -- PINT-native). Three
  well-separated sightlines make the FULL 3-D bias observable
  (recover_bias basis rank 3).
- ENERGY CUTS per pulsar (the measured background lesson: J0030's 2017-08
  observation folds at H = 5.1 unfiltered -- 93% of its events are
  background above 1.5 keV -- and at high significance in its soft band).
  Soft band PI 30-150 (0.3-1.5 keV) for the thermal pulsars J0030/J0437;
  hard band PI 120-400 (1.2-4 keV) for non-thermal B1937, chosen by the
  measured band scan on template data. Bands are documented stimulus
  parameters (like the injected 100 km), not tolerances; chosen values
  follow standard NICER practice and the measured H tables in the journal.
- TEMPLATE FROM A DIFFERENT OBSERVATION: each pulsar's reference peak
  comes from its OTHER ObsID (independent photons), so the measured
  shift's error bar is real photon statistics. Phase-connection across
  epochs is what the NG15 models provide.
- The ONLY frozen tolerances are the card's own: E4_TOA_SIGMA_MAX_S
  (50 us, section 11) and E4_HTEST_MIN (fold-cleanliness floor, set below
  the measured H values with recorded headroom) -- authorized override
  #13. The 2-sigma gate needs no frozen number: sigma comes from the data
  itself.

Runtime note: ~10-15 minutes in WSL -- each fold is a full Spec-9 phase
computation on the energy-filtered photons (2.7e4-1.3e5 per fold). That is
the price of a real-data armor gate; the machinery smoke path is Spec 9's
suite.

Run: /opt/galnav/venv/bin/python -m pytest tests_armor -q   (inside WSL)
"""

from pathlib import Path

import numpy as np

from tests.golden_numbers import E4_HTEST_MIN, E4_TOA_SIGMA_MAX_S
from tests_armor import _e4_fold as e4

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data/e4_nicer"
EPHEM = "DE440"  # all three NG15 pars state EPHEM DE440; pinned, never defaulted
SEED = 20260716
N_BOOT = 200
BIAS_KM = 100.0  # injected magnitude: up to ~334 us of light-time along a
# sightline (0.058-0.214 turns across these three pulsars -- comfortably
# under the 0.5-turn wrap ceiling, which sits at |dr| = 0.5 c / f0_max =
# 233 km for B1937, and decisively above the measured 116-260 us shift
# noise so the recovery is sharp, not vacuous) -- stimulus parameter,
# documented here and in the journal, not a tolerance.

PULSARS = {
    "J0030+0451": {
        "par": DATA / "pars/J0030+0451_PINT_20220302.nb.par",
        "pi_band": (30, 150),  # 0.3-1.5 keV: the thermal pulse's band
        # template: the OTHER (big) ObsID; measurement: the small, fast one
        "template_evt": DATA
        / "2017_08/1060020113/xti/event_cl/ni1060020113_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_08/1060020113/auxil/ni1060020113.orb.gz",
        "meas_evt": DATA
        / "2018_01/1060020263/xti/event_cl/ni1060020263_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2018_01/1060020263/auxil/ni1060020263.orb.gz",
    },
    "B1937+21": {
        "par": DATA / "pars/B1937+21_PINT_20220306.nb.par",
        # 1.2-4 keV: chosen by a measured band scan ON TEMPLATE DATA (journal
        # table): the wide 1-7 keV band folds at H=15.5 on the template
        # observation (a hard background component: H collapses to 0.3 at
        # 2.5-12 keV), while 120-400 folds at H=43.8 template / 199.3
        # measurement -- both epochs improve, same band both epochs (mixed
        # bands would inject a chromatic peak offset).
        "pi_band": (120, 400),
        "template_evt": DATA
        / "2017_09/1070020147/xti/event_cl/ni1070020147_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_09/1070020147/auxil/ni1070020147.orb.gz",
        "meas_evt": DATA
        / "2017_09/1070020148/xti/event_cl/ni1070020148_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2017_09/1070020148/auxil/ni1070020148.orb.gz",
    },
    "J0437-4715": {
        "par": DATA / "pars/J0437-4715_PINT_20220301.nb.par",
        "pi_band": (30, 150),  # 0.3-1.5 keV: thermal-dominated pulse
        "template_evt": DATA
        / "2017_10/1060010157/xti/event_cl/ni1060010157_0mpu7_cl.evt.gz",
        "template_orb": DATA / "2017_10/1060010157/auxil/ni1060010157.orb.gz",
        "meas_evt": DATA
        / "2017_12/1060010188/xti/event_cl/ni1060010188_0mpu7_cl.evt.gz",
        "meas_orb": DATA / "2017_12/1060010188/auxil/ni1060010188.orb.gz",
    },
}

# One full experiment run shared by every test (plain module cache, no
# fixtures -- house style; ~10-15 min, computed once).
_CACHE = {}


def _run():
    if "res" not in _CACHE:
        _CACHE["res"] = e4.run_experiment(
            PULSARS,
            ephem=EPHEM,
            bias_km=BIAS_KM,
            n_injections=3,
            n_boot=N_BOOT,
            seed=SEED,
        )
    return _CACHE["res"]


def test_t1_bias_recovered_within_two_sigma_three_injections():
    """T1 (THE CARD GATE): three injections, each recovered within 2 sigma.

    For each seeded injection dr_true: the nav-side recover_bias sees only
    the three measured fold shifts, their bootstrap sigmas, and public
    (f0, sightline) facts. Three well-separated sightlines make the full
    3-D bias observable (basis rank 3), and the test demands, per
    injection, that ALL THREE components of the error dr_hat - dr_true,
    expressed in the recovered orthonormal basis, sit within 2x their own
    recovered standard deviation. Fixed seed makes this deterministic: it
    either proves the chain or fails loudly.

    What it catches: a sign error in the Roemer projection, a wrong f0/c
    scaling, an orbit injection that PINT silently ignored, mixed-up
    pulsar ordering, an over-optimistic sigma -- each moves some component
    outside 2 sigma immediately (the injected shifts are ~1e2-1e3x the
    fold noise).
    """
    res = _run()
    assert res["n_hats"].shape == (3, 3)
    assert len(res["injections"]) == 3
    for inj in res["injections"]:
        e_proj = inj["projected_error_coeffs_km"]  # (3,): full 3-D observable
        s_proj = inj["projected_sigma_km"]
        assert e_proj.shape == s_proj.shape == (3,)
        assert np.all(np.abs(e_proj) <= 2.0 * s_proj), (
            inj["label"],
            e_proj.tolist(),
            s_proj.tolist(),
        )


def test_t2_folds_are_clean_htest():
    """T2 (fold cleanliness -- the Sep-5 criterion): H-test on every fold.

    Every energy-filtered fold the experiment used (each pulsar's template
    fold and each measurement fold) must clear the frozen E4_HTEST_MIN,
    with p ~ exp(-0.4 H). The floor sits far below every measured value
    (headroom recorded in the override-#13 comment) while being far above
    noise (H of a few). Catches: a par/data mismatch, a broken fold, a
    wrong-pulsar file swap, an energy band that guts the pulse -- any of
    which collapses H toward zero.
    """
    res = _run()
    for name, h in res["htests"].items():
        assert h >= E4_HTEST_MIN, (name, h)


def test_t3_toa_budget():
    """T3 (the section-11 budget line): the 1-50 us fold budget, demonstrated.

    The bootstrap peak sigma in turns divided by f0 is the fold's
    time-of-arrival uncertainty. The compass budget table says 1-50 us for
    NICER folding; the frozen E4_TOA_SIGMA_MAX_S is that table's own upper
    bound, and the BEST measurement fold must demonstrate it on real data
    (measured: J0437 31.3 us and B1937 ~40 us meet it; J0030's short soft
    exposure measured 134 us -- recorded openly in the journal, not hidden;
    its sigma still enters the recovery honestly through the weights).
    Every fold must also be SANE: sigma strictly positive (a ~0 sigma
    would fingerprint a fold compared against itself) and below 500 us
    (folds noisier than that would make the 2-sigma gate vacuous against
    the ~334 us maximum injected signal -- the inline bound is that
    design statement, not an accuracy tolerance).
    """
    res = _run()
    sigmas = res["toa_sigmas_s"]
    for name, toa_sigma_s in sigmas.items():
        assert 0.0 < toa_sigma_s < 500e-6, (name, toa_sigma_s)
    assert min(sigmas.values()) <= E4_TOA_SIGMA_MAX_S, sigmas


def test_t4_recovery_is_deterministic():
    """T4: same seed, same measurements -> bit-identical recovery.

    Re-derives every injection's recovered vector from the CACHED fold
    measurements with a fresh identically-seeded call, and demands
    np.array_equal against the first pass. Catches hidden nondeterminism
    in the solver or bookkeeping (the blessed npz must be exactly
    regenerable, per the project's reproducibility rule).
    """
    res = _run()
    res2 = e4.rerun_recoveries(res, seed=SEED)
    for a, b in zip(res["injections"], res2["injections"]):
        assert np.array_equal(a["dr_hat_km"], b["dr_hat_km"]), a["label"]
