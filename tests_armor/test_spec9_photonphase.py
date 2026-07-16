"""Acceptance tests for Spec 9 -- PINT photon phase (armor tier).

AI-authored under the build-night ratification-pending pattern (see
journal/logbook.md 2026-07-16 and the ratification worksheet). Students:
read and own every assertion before ratifying.

The compass card, verbatim (section 6): "Spec 9 -- PINT photon phase
(armor). Test: PINT `photonphase` agreement with reference to `< 1e-9` in
phase."

What that means physically: each NICER photon's arrival time, moved to the
Solar System Barycentre and fed to the pulsar's spin-down model, yields a
rotational PHASE (which fraction of a turn the pulsar had completed). Two
fully independent walks of that chain -- the `photonphase` command-line tool
(Route A) and our own composition of PINT's library API (Route B) -- plus a
hand-rolled longdouble evaluation of the spin-down polynomial itself (T2)
must all agree to better than one part in 10^9 of a turn. For J0030+0451
(P = 4.865 ms) that is ~4.9 picoseconds of timing: nothing but the SAME
physics, computed correctly at 80-bit precision, agrees that well.

Data: ONE real NICER observation of PSR J0030+0451 (ObsID 1060020263,
2018-01-19, 29.5 ks, 152,107 cleaned photons) + its ISS orbit file --
provenance in data/e4_nicer/README.md -- and the NANOGrav 15-yr narrowband
timing model (data/e4_nicer/pars/, provenance ibid.). The ephemeris is
pinned to the par file's own EPHEM (DE440); nothing uses a default.

The only tolerance here is the frozen SPEC9_PHASE_AGREEMENT = 1e-9 from
tests/golden_numbers.py (authorized override #12, the plan's own
pre-registered gate). Every other assertion is exact, structural, or a
strict inequality derived from geometry in the docstring that uses it.

This file runs ONLY in the WSL2 armor environment (see tests_armor/
__init__.py and journal/environment-armor.md):
  /opt/galnav/venv/bin/python -m pytest tests_armor -q
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from tests.golden_numbers import SPEC9_PHASE_AGREEMENT
from tests_armor import _pint_routes as routes

REPO = Path(__file__).resolve().parents[1]
EVT = (
    REPO / "data/e4_nicer/2018_01/1060020263/xti/event_cl/ni1060020263_0mpu7_cl.evt.gz"
)
ORB = REPO / "data/e4_nicer/2018_01/1060020263/auxil/ni1060020263.orb.gz"
PAR = REPO / "data/e4_nicer/pars/J0030+0451_PINT_20220302.nb.par"
EPHEM = "DE440"  # the par file's own EPHEM line -- pinned, never defaulted

# The library route costs minutes on 152,107 photons, so T1/T2/T4 share ONE
# build through this plain module-level cache (no fixtures -- plain-function
# house style). T3 deliberately does NOT use it: determinism is only proven
# by building fresh.
_CACHE = {}


def _library():
    """Build (or fetch the cached) Route-B objects for T1/T2/T4."""
    if "lib" not in _CACHE:
        _CACHE["lib"] = routes.phases_library(EVT, PAR, ORB, EPHEM)
    return _CACHE["lib"]


def test_t1_two_route_agreement_below_gate():
    """T1 (THE CARD GATE): photonphase CLI vs our library route, all photons.

    Route A runs the shipped `photonphase` executable exactly as a mission
    analyst would; Route B composes PINT's public API ourselves (satellite
    observatory from the .orb, event TOAs, barycentric chain, absolute
    phase). The wrap-aware |difference| must be < SPEC9_PHASE_AGREEMENT
    (1e-9 turns) for EVERY one of the 152,107 photons -- max, not median.

    What it catches: a wrong orbit interpolation, a drifted ephemeris
    default, a clock-chain mismatch (TT(BIPM2019) vs TAI), a TZR reference
    slip, an off-by-one in event row order -- any of these moves phases by
    orders of magnitude more than 1e-9. Agreement this tight is only
    possible if our understanding of the pipeline IS the pipeline.
    """
    frac_cli = routes.phases_photonphase_cli(EVT, PAR, ORB, EPHEM)
    model, toas, ph_int, ph_frac = _library()
    assert frac_cli.shape == ph_frac.shape == (152107,)
    delta = routes.wrapped_abs_delta(frac_cli, ph_frac)
    assert float(np.max(delta)) < SPEC9_PHASE_AGREEMENT, (
        "max |dPhi|",
        float(np.max(delta)),
    )


def test_t2_longdouble_spindown_reference():
    """T2 (the teachable formula): our own polynomial vs PINT's spindown.

    We parse F0, F1, PEPOCH from the par TEXT ourselves at full longdouble
    width (the par carries 20 significant digits -- more than float64 can
    hold) and evaluate the students' formula phi = F0*dt + F1*dt^2/2
    (+ F2*dt^3/6) at the pulsar-frame times since PEPOCH. PINT's own
    Spindown-component phase must match to < 1e-9 turns INCLUDING the
    integer turn count (~3.4e10 turns from PEPOCH 56231 to the 2018 data:
    the int64 turns must be EQUAL, the fractions within the gate).

    AMENDED PRE-GREEN (2026-07-16, ratification worksheet item hh): the
    first draft routed the comparison through barycentric MJDs as single
    longdoubles. That representation cannot carry the gate -- at MJD
    58137 (the 2^15 binade) a longdouble's grid is 2^-48 day ~ 0.31 ns ~
    6.3e-8 turns of J0030 phase, ~63x the gate -- so the draft test was
    IMPOSSIBLE to pass for reasons of
    number representation, not physics. The amended chain uses PINT's own
    decomposition (dt = (tdbld - PEPOCH) - delay, kept apart from any
    absolute epoch; see pulsar_frame_dt_seconds), which is exactly the
    discipline PINT exists to enforce. The lesson is written up in
    journal/spec-9-photon-phase.md.

    What it catches: a float64 round-off anywhere in the chain (the turn
    count alone needs 19 digits), a wrong PEPOCH unit (days vs seconds), a
    factor-2 slip in the F1 term, or a misread of what PINT means by
    "phase". This is the 80-bit discipline test: on native Windows this
    assertion CANNOT pass (see journal/environment-armor.md).
    """
    model, toas, ph_int, ph_frac = _library()
    sd = routes.parse_spindown_longdouble(PAR)
    dt_s = routes.pulsar_frame_dt_seconds(model, toas, sd["PEPOCH"])
    ref_int, ref_frac = routes.spindown_phase_reference(
        dt_s, sd["F0"], sd["F1"], sd["F2"]
    )
    pint_int, pint_frac = routes.pint_spindown_phase(model, toas)
    assert np.array_equal(ref_int, pint_int)
    delta = routes.wrapped_abs_delta(ref_frac, pint_frac)
    assert float(np.max(delta)) < SPEC9_PHASE_AGREEMENT, (
        "max |dPhi| spindown",
        float(np.max(delta)),
    )


def test_t3_determinism_and_offline():
    """T3: two fresh builds are bit-identical -- and the second one OFFLINE.

    Blessed numbers must not depend on the network's mood or a clock-file
    auto-update. This test builds Route B from scratch in a SUBPROCESS whose
    environment points every proxy variable at an unroutable address
    (127.0.0.1:9), so ANY attempt to download anything fails instantly --
    if the phases still come out, every ephemeris/clock file the chain needs
    is already pinned in the local caches recorded in
    journal/environment-armor.md. The subprocess prints a sha256 over the
    exact bytes of (phase_int, phase_frac); it must equal the in-process
    build's hash bit for bit.

    What it catches: hidden nondeterminism (dict ordering, unseeded noise,
    time-dependent clock interpolation) and any un-vendored runtime
    download -- either would change or break the hash.
    """
    model, toas, ph_int, ph_frac = _library()
    h_here = hashlib.sha256(ph_int.tobytes() + ph_frac.tobytes()).hexdigest()

    code = (
        "import sys, hashlib; sys.path.insert(0, sys.argv[1]);"
        "from tests_armor import _pint_routes as r;"
        "m, t, pi, pf = r.phases_library(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]);"
        "print(hashlib.sha256(pi.tobytes() + pf.tobytes()).hexdigest())"
    )
    env = dict(os.environ)
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env[var] = "http://127.0.0.1:9"  # unroutable: any download dies fast
    env["NO_PROXY"] = ""
    out = subprocess.run(
        [sys.executable, "-c", code, str(REPO), str(EVT), str(PAR), str(ORB), EPHEM],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
        check=True,
    )
    h_offline = out.stdout.strip().splitlines()[-1]
    assert h_offline == h_here


def test_t4_orbit_file_is_load_bearing():
    """T4: the ISS orbit file demonstrably drives the computation.

    A pipeline that silently ignored --orbfile would still produce plausible
    phases (Earth-centre barycentering) -- wrong by up to the ISS orbit's
    light-radius. So we check the observatory positions PINT actually used:
    subtracting Earth's geocentre (same ephemeris, same times) must leave a
    vector whose length sits in the LEO band and whose projection on the
    pulsar sightline SWINGS as the ISS circles Earth.

    The bounds, derived here and not tuned: Earth's equatorial radius is
    6378 km and the ISS flies ~370-460 km up, so 6600 km < |r_geo| <
    6900 km for every photon. Light crosses that radius in at most
    6900/299792.458 = 23.0 ms, so |tau| = |r.n_hat|/c <= 23 ms always; and
    over 29.5 ks (~5.3 ISS orbits) the projection must swing by more than
    5 ms peak-to-peak (it would be CONSTANT ZERO if the orbit file were
    ignored, since r_geo would vanish). Strict inequalities, no golden
    number.
    """
    model, toas, ph_int, ph_frac = _library()
    r_obs = routes.ssb_obs_positions_km(toas)
    r_earth = routes.earth_ssb_positions_km(toas, EPHEM)
    r_geo = r_obs - r_earth  # ISS position relative to Earth's centre, km
    norms = np.linalg.norm(r_geo, axis=1)
    assert norms.shape == (152107,)
    assert float(norms.min()) > 6600.0
    assert float(norms.max()) < 6900.0
    n_hat = routes.pulsar_unit_vector(model)
    tau_ms = (r_geo @ n_hat) / 299792.458 * 1e3  # light-time along sightline
    assert float(np.max(np.abs(tau_ms))) <= 23.0
    assert float(tau_ms.max() - tau_ms.min()) > 5.0
