# Spec 9 — PINT photon phase (armor): every photon knows what time it is

*2026-07-16. AI-authored under the build-night ratification-pending pattern;
ratification worksheet item (hh). Compass §6, verbatim: "Spec 9 — PINT
photon phase (armor) (~2 sessions). Test: PINT `photonphase` agreement with
reference to `< 1e-9` in phase." Runs ONLY in the WSL2 armor environment —
journal/environment-armor.md explains why native Windows cannot do this at
all.*

## 1. What this card builds, in one breath

Given one real NICER observation of PSR J0030+0451 — 152,107 X-ray photons
caught on the ISS on 2018-01-19 — assign every photon the pulsar's
rotational PHASE at the moment its wavefront crossed the Solar System
Barycentre, three independent ways, and prove all three agree to better
than one billionth of a turn. The machinery lives in
`tests_armor/_pint_routes.py`; the proof in
`tests_armor/test_spec9_photonphase.py`; both are reused by E4.

## 2. The chain, one symbol at a time

A photon arrives at the detector at topocentric time t_topo (the ISS's
clock, converted to TDB). The pulsar does not care where the ISS was — its
rotation is a clock at the pulsar — so we move the arrival to the Solar
System Barycentre (SSB), the one point the planets' tugs average out:

    t_bary = t_topo − Δ_total
    Δ_total = Δ_Roemer + Δ_Shapiro + Δ_clock (+ Δ_DM, zero here)

- **Δ_Roemer** (geometry, the big one): the light-travel time between the
  ISS and the SSB along the pulsar direction n̂, r·n̂/c, where r = ISS
  position from the `.orb` file (measured: |r_geo| between 6775.3 and
  6788.1 km — the real ISS altitude band that week) plus Earth's position
  from the JPL DE440 ephemeris (the par file's own EPHEM). Earth's part
  swings ±~8 light-minutes over a year; the ISS's part swings ±23 ms max
  over each 92-minute orbit (we measured 7.14 → 20.31 ms along this
  sightline, a 13.16 ms swing during the 29.5 ks observation).
- **Δ_Shapiro** (relativity): light climbing past the Sun (and, with
  PLANET_SHAPIRO Y, the giant planets) is delayed by their gravity —
  microseconds near the Sun's limb, always present.
- **Δ_clock**: instrument time → TT. Measured finding, recorded because it
  surprised us: the photon pipeline runs with `include_bipm=False`
  (photonphase's `--use_bipm` defaults OFF; pint 1.1.4 photonphase.py lines
  189–196) — the par's `CLOCK TT(BIPM2019)` refinement is a tens-of-ns
  radio-timing nicety, far beneath photon TOA precision, so the tool skips
  it and our mirror must too.
- **Δ_DM** (dispersion): radio waves are slowed by interstellar electrons
  as 1/f²; X-ray photons have effectively infinite frequency, so the DM
  delay is zero here. The par's DM/DMX blocks ride along harmlessly (they
  model delays, not phase). Likewise the model's TroposphereDelay is a
  radio-telescope term — zero for a satellite.

Then the pulsar's own clock reads out the PHASE — the spin-down Taylor
polynomial:

    φ(dt) = F0·dt + F1·dt²/2 (+ F2·dt³/6),   dt = t_bary − PEPOCH  [s]

with, for J0030+0451 from the NANOGrav 15-yr par: F0 =
205.53069907954086655 Hz (the pulsar turns 205.53… times every second; 20
significant digits — more than a float64 can hold, which is the whole
plot of §4), F1 = −4.2978×10⁻¹⁶ Hz/s (it slows, imperceptibly), PEPOCH =
MJD 56231. Our photons sit dt ≈ 1906 days after PEPOCH — measured turn
counts 33,846,551,371 → 33,864,120,872 (≈3.39×10¹⁰ turns). `abs_phase=True`
anchors phase zero at the model's TZR (time-of-zero-reference) so both
routes share the same "turn number zero".

## 3. The three computations that must agree

- **Route A** — the shipped `photonphase` CLI, run exactly as a mission
  analyst would (`--orbfile … --ephem DE440 --addphase`), PULSE_PHASE
  column read back.
- **Route B** — our own composition of PINT's public library API
  (get_satellite_observatory → get_event_TOAs(include_bipm=False,
  planets=True) → model.phase(abs_phase=True)). Written without looking at
  Route A's output; if our understanding of ANY step differed, the phases
  would disagree wildly.
- **The reference** — the students' polynomial itself, F0/F1/PEPOCH parsed
  from the par TEXT by our own 20-digit longdouble parser and evaluated by
  our own Horner loop.

MEASURED RESULT (2026-07-16, evidence script in the session log): Route A
vs Route B — max |Δφ| = **0.0, bit-identical on all 152,107 photons**. The
reference vs PINT's Spindown component — max |Δφ| = **0.0, bit-identical,
including every one of the ~3.4×10¹⁰-turn integers**. The `< 1e-9` gate is
passed with literal zeros.

## 4. The two precision lessons (why the zeros were hard)

These are the card's real teaching payload; both failures happened live
and are preserved here.

**Lesson 1 — never recombine a split phase (the 2⁻²⁹ bug).** Our first
Route B summed PINT's (integer turns, fraction) pair into one longdouble
"total phase" before re-splitting. A longdouble carries 64 mantissa bits;
at 3.4×10¹⁰ (≈2³⁵) turns its representable grid is 2³⁵⁻⁶³ = 2⁻²⁸ turns, so
the summation quantized every fraction at half that grid — and T1 failed
with max |Δφ| = 1.862645149230957×10⁻⁹, which is EXACTLY 2⁻²⁹, constant
across all photons. That number is a fingerprint: not physics, not noise —
pure floating-point representation. The fix (`_floor_split_pair`) never
sums the pair; it is precisely why PINT's Phase type is a two-component
number.

**Lesson 2 — a barycentric MJD cannot carry the gate (the T2 amendment).**
The first T2 draft asked for phases from "barycentric times" as longdouble
MJDs. At MJD ≈ 58137 (≈2¹⁶ days) a longdouble's grid is 2¹⁶⁻⁶³ day ≈
0.24 ns — times F0, that is ≈5×10⁻⁸ turns, fifty times coarser than the
gate. No implementation could pass; the TEST was wrong, for representation
reasons, not physics. Because the card is AI-authored and pre-ratification,
T2 was amended BEFORE the green run (the approved-with-amendments pattern,
recorded in the test's docstring and worksheet item hh) to use PINT's own
decomposition: keep (tdbld − PEPOCH) — a subtraction of nearby values,
exact by Sterbenz's lemma — and the delay as SEPARATE numbers, converting
to seconds only at the end, in the same operation order as PINT's
`get_dt` + `taylor_horner` (`((F2·dt/3 + F1)·dt/2 + F0)·dt/1`, read from
the installed source). On equal terms, the students' formula reproduces
PINT bit for bit.

## 5. What each test proves

- **T1 (the card gate):** the CLI and our library mirror agree — wrap-aware
  max |Δφ| < 1e-9 over every photon (measured 0.0). Catches a wrong orbit
  interpolation, drifted ephemeris default (the CLI's default is DE421; we
  pin the par's DE440 explicitly), clock-chain mismatch, TZR slip, row
  reorder.
- **T2 (the formula):** our longdouble parse + Horner = PINT's Spindown,
  integer turns np.array_equal AND fractions < 1e-9 (measured 0.0/equal).
  Catches any float64 leak (the turn count alone needs 19 digits), a
  factor-2 slip on F1, a day/second unit error, a misread of "phase".
- **T3 (determinism + offline):** a fresh subprocess with every proxy
  variable pointed at an unroutable address rebuilds Route B and its
  sha256 over (int, frac) bytes matches the in-process build exactly —
  proving byte-reproducibility AND that every ephemeris/clock file is
  local (the runtime-download landmine from environment-armor.md is
  defused). Catches hidden nondeterminism and un-vendored downloads.
- **T4 (the orbit is load-bearing):** the observatory positions PINT used,
  minus Earth's centre from the same DE440, land in the LEO band
  (measured 6775.3–6788.1 km, inside the derived 6600–6900 bound) and the
  sightline light-time swings 13.16 ms > 5 ms over the observation. A
  pipeline that silently ignored `--orbfile` would sit at the geocentre
  (r_geo = 0) and fail instantly. Bounds derived in the docstring from
  Earth radius + ISS altitude + c; no golden number.

Bonus measured fact (not a gate here, but the Sep-5 gate's subject): the
J0030 fold of these 152,107 phases has **H-test = 77.4** (p ≈ e^(−0.4·H)
≈ 4×10⁻¹⁴) — the pulsation is unambiguously detected, so the compass's
risk #7 ("NICER fold not clean → E4 simulation-only") is retired with
evidence, seven weeks before its Sep 5 gate. E4 proceeds on real data.

## 6. Tolerances touched

Exactly one, new: `SPEC9_PHASE_AGREEMENT = 1e-9` (tests/golden_numbers.py,
authorized override #12). WHY this value: it is the plan's own
pre-registered gate, quoted verbatim from compass §6 — not measured, not
tuned. The measured agreement is 0.0, so the gate carries ~∞ headroom; it
exists to catch any future regression (a PINT upgrade, an ephemeris swap,
an environment drift) the moment it moves a single photon's phase by a
part per billion. No other tolerance was added or changed; every other
assertion is exact (np.array_equal, sha256 equality) or a strict
inequality derived from geometry inline.

## 7. What Spec 9 does NOT do

It does not fold profiles into TOAs, estimate fold uncertainties, or
inject/recover any bias — that is E4, which reuses this module. It does
not validate the par's astrophysics (both routes share the par, so a
wrong F0 would cancel — authenticity is a provenance question, handled in
data/e4_nicer/README.md with a deferred byte-check against the Zenodo
archive). It does not run on native Windows, by measured impossibility,
and it does not touch the spine: galnav/ unchanged, spine suite still
84 passed / 0 skipped on Windows with `pytest.ini` scoping the default
collection to tests/.

## 8. Deviations from the compass, all recorded

- HEASoft-free: §7/§11 name `nicerl2` + `barycorr`; we use the archive's
  already-nicerl2-screened cl.evt files and PINT's own barycentering
  (measured working; retires risk #2 for this pass).
- pint-pulsar 1.1.4 (current) supersedes §5's 1.1.2 pin (environment-armor
  amendment, item gg).
- Ephemeris DE440 (the par's own EPHEM) rather than the CLI default DE421;
  both are cached and hash-recorded.

## 9. Where this sits

Armor tier, first half: the photon→phase machinery is now proven at the
billionth-of-a-turn level on real data. E4 stands on it directly: fold
these phases into pulse arrival measurements for three pulsars, inject a
known ISS-orbit bias, and recover it — the last unbuilt experiment in the
project.
