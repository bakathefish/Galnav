# GalNav — Compilation of ALL findings (paper source pack)

*Assembled 2026-07-16 at the close of the build queue (HEAD 493dca2). This
is the single source-of-truth summary for the paper: every finding, every
measured number, where it is proven, and which citation tags it leans on.
Status letters: [DONE] = built, tested, committed, journaled;
[PROPOSED] = candidate next card, prior-art-scouted, AWAITING STUDENT
RULING. The logbook remains authoritative; this file only collects.*

## 0. The thesis in three legs

**Where you are. When you are. How long you can trust it.** Starlight gives
an interstellar spacecraft an absolute but au-coarse position fix that
DECAYS on a measurable schedule as its star catalog ages (leg 1 — E6, the
headline). Pulsars offer km-fine but integer-ambiguous ticks that an
au-coarse fix can NEVER bootstrap — a four-order-of-magnitude no-man's-land
(leg 2 — E5 + Spec 8). Both legs are anchored to reality with real NASA
data: a real spacecraft found from its own star photos (E3), and real
X-ray photons surrendering an injected spacecraft ephemeris error (E4)
(leg 3). Everything is reproducible bit-for-bit from a fresh clone.

## 1. Findings — the spine

**F1 [DONE] The navigator is provably optimal.** Monte-Carlo RMS error
tracks the Cramér-Rao lower bound: worst cell ratio 1.064 across the full
96-cell (distance x star count) grid, and 1.045 across the four-cell CI
harness (gate 1.5 for both; the two scopes are distinct — sweep-corrected
wording); the estimator is unbiased. Proven: E1 + tests/test_covariance.py; blessed archive
reproduces 1.063652 bitwise. Leans on [CRLB], [COV], [GN], [Gauss1809].

**F2 [DONE] The field's anchor result reproduces.** Bailer-Jones (2021)
lost-in-space accuracy — ~3 au / ~2 km/s at 20 stars, 1 arcsec —
reproduced: median 3.019 au / 2.028 km/s, percentile bands matching, in
his own 7-unknown protocol (hub angles, MEDIAN-of-100-runs statistics).
The Aug-15 plan gate passed a month early. Proven: tests/test_bj_anchor.py.
Leans on [BJ21], [Klioner03].

**F3 [DONE] It finds a REAL spacecraft.** From Lauer et al. (2025)'s
measured New Horizons star directions (Proxima Cen + Wolf 359, epoch
2020.3, spacecraft at 47.1 au), our independent pipeline — Gaia CSV ->
epoch propagation (J2016.0 -> 2020.3, Spec 10) -> n_star_solve — recovers
the real New Horizons to **0.3467 au** of the JPL ephemeris (plan gate
3 au: 8.7x inside; Lauer's own miss: 0.351 au; we reproduce Lauer's
solution to 0.0065 au). CRITICAL measured sub-finding: epoch propagation
is mandatory — solving with unpropagated J2016.0 positions misses by
~30 au. Proven: E3 + tests/test_e3_triangulation.py; archive
results/archive/ (commit 6e3832e). Leans on [Lauer25], [Lauer25-data],
[GaiaDR3], [NASA20].

**F4 [DONE] THE HEADLINE — star catalogs have a navigation expiration
date.** Propagating Gaia DR3 forward with its own velocity uncertainties
(5 of the 20 nearest stars lack radial velocities), navigation error at
1 pc / 20 stars grows with catalog age: aging factor 2.22x at 100 yr and
4.14x at 200 yr (at 10 mas sensor noise); the **crossover time** where
catalog age overtakes sensor quality RISES from 44.8 yr (10 mas camera)
to 161.9 yr (60 arcsec camera); below the **knee at ~15.9 arcsec** a
better camera buys nothing at 1 pc because the **epoch-parallax floor
(7.66 au)** dominates. Proven: E6 (Spec 7 catalog covariance + Spec 10
propagator + E6a sampled sky + E6b experiment); blessed archive
e6_catalog_aging_20260715T231348Z reproduces bitwise. Novelty: SURVIVED
three adversarial prior-art sweeps — the astrometric community knows
catalogs age ([AbsAstro50]); the NAVIGATION-error map over (age x sensor)
with crossover locus and floor is unpublished. Must-distinguish:
[YucalanPeck19], [YucalanPeck21], [ZhangLiLiu26], [Franzese26],
[DSNcompare21], [BJ15].

**F5 [DONE] The pulsar rescue fails — quantified.** The positions
consistent with K pulsar phase measurements form a lattice; the largest
prior uncertainty that still picks the right integers is the packing
radius rho = lambda_1/2 = 286.02 km for the (Crab, B1937+21, J0030+0451)
comb set (archive value 286.024866; sweep-corrected rounding). A ~1 au
starlight fix is **523,024x** that radius: the comb
integers are unrecoverable — pulsars beyond the solar system are an
odometer, not a GPS. Coast budgets: a 467 km comb holds lock 270.3 days
at 1 cm/s velocity knowledge, 2.70 days at 1 m/s. Proven: E5-lite +
tests/test_e5_pulsar.py; archive b89b6ff. NARROW framing (mandatory):
solar-system pulsar navigation is established ([Deng13], [Shemar16],
[Becker13]); the finding is the INTERSTELLAR bootstrap limit. Naming-
collision defusal (sweep O6): an identically-named solar-system sub-field
— "X-ray pulsar / starlight Doppler deeply-integrated navigation"
([PulsarDoppler]: Liu & Fang 2015; Wang, Zheng & Zhang 2017) — fuses
pulsar timing with starlight RADIAL VELOCITY as an in-system velocity
aid; it never addresses interstellar POSITION bootstrap or catalog aging;
cite + distinguish in one sentence up front. Leans on
[LAMBDA], [ATNF], [SI].

**F6 [DONE] Inside the packing radius, recovery is exact.** The hand-coded
closest-lattice-point solver (Babai rounding + exact 27-point box,
[Babai86]) recovers injected integer turn-counts with measured 100.000%
success on 8,000 trials at prior offsets up to 0.999 rho, and provably so
(inside rho the true point is the UNIQUE closest). At 1.5 rho the integer
genuinely flips — the ambiguity is physical, not algorithmic. Proven:
Spec 8 + tests/test_spec8_cvp.py (zero new tolerances — integer-exact).
Lattice-convention note (sweep O3): F5's rho = 286.02 km is the PHYSICAL
c*P-comb lattice (archive 286.024866); the Spec 8 test runs on the frozen
integer COMB_KM lattice, rho = 285.978 km — the two conventions differ by
47 m (0.02%); quote 286.02 as the headline and label 285.978 as the
integer-lattice test value.

**F7 [DONE] Relativity is not optional.** At 0.1c a navigator using the
classical (Galilean) aberration formula is biased by median **1356 au /
1201 km/s**; the exact special-relativistic solver recovers to 1.2e-9 au.
Per-angle model error median ~402 arcsec (never confuse with the
26-arcsec max-deflection gap). Proven: E7 + tests/test_e7_aberration.py;
archive 470faef. Leans on [SR-ABER], [Klioner03], [Lauer25] Eq. 1
(explicitly its v<<c form).

**F8 [DONE] The solver basically cannot get lost locally.** 50%-capture
radius of the position solver's convergence basin: 2.0 -> 11.6 pc as the
star count grows 5 -> 100 (at 1 pc, 500 trials/cell). Undamped
Gauss-Newton captures from parsecs away. Proven: E2 +
tests/test_e2_basins.py; archive 2e88513 (isotropy guarded by a
4th-moment gate after the variance test was measured blind to a cube-
sampler bug — override #10 story).

## 2. Findings — the armor (real photon data)

**F9 [DONE] Our use of PINT is proven to a billionth of a turn.** On
152,107 real NICER photons of PSR J0030+0451 (ObsID 1060020263 + ISS
orbit file): the photonphase CLI and our independent composition of
PINT's library API agree BIT-IDENTICALLY (max |dPhi| = 0.0); our own
20-digit-longdouble parse + Horner spin-down polynomial reproduces PINT's
phase bit-for-bit INCLUDING all ~3.39e10 integer turn counts; the chain
is bit-reproducible OFFLINE (proxy-poisoned subprocess, sha256 match);
the ISS orbit is demonstrably load-bearing (sightline light-time swings
13.16 ms over 5.3 orbits). Fold H-test 77.4 retired the plan's Sep-5
"fold clean" gate seven weeks early. Two preserved precision lessons:
(i) summing PINT's (int, frac) phase pair quantizes at the 3.4e10-turn
longdouble grid — measured as an EXACTLY-2^-29 constant error;
(ii) a barycentric MJD in one longdouble carries only ~6.3e-8 turns
(2^-48 day at MJD 58137; sweep-corrected binade) — which is why PINT
keeps (tdbld - PEPOCH) and delay separate. Proven:
Spec 9, tests_armor/test_spec9_photonphase.py (armor env:
journal/environment-armor.md — native Windows measured INCAPABLE,
eps 2.2e-16 vs required <2e-19). Leans on [PINT], [NG15], [NICERarch],
[NICER16].

**F10 [DONE] Real photons surrender an injected spacecraft ephemeris
error.** Three seeded 100 km biases injected into the ISS orbit files;
for each, the folds of three real pulsars (J0030+0451, B1937+21, and the
BINARY J0437-4715 — DD model, validated end-to-end at H = 874) shift by
f0 (dr.n)/c; the nav-side weighted least squares recovers the full 3-D
bias **within 2 sigma on all three injections** (worst components
1.84/1.88/1.85 sigma; |error| 76.15 km). Two honest, quantified lessons:
(i) ENERGY CUTS are load-bearing — J0030's template observation folds at
H = 5.1 unfiltered (93% background) and H = 96.2 in its 0.3-1.5 keV band;
B1937's band was chosen by a measured scan on template data (H 15.5 ->
43.8); (ii) the TEMPLATE is the noise floor — the near-identical 76 km
errors across injections are the shared template's single ~1.85-sigma
excursion, exactly the size the quadrature error bars predict; IF
template-photon-limited, 16x deeper templates -> ~20 km (a fixed
cross-epoch systematic is not excluded and would floor it higher —
sweep-hedged, needs a third epoch to distinguish). TOA sigmas 31.0 us (J0437) and ~43 us (B1937) land
inside the plan's own 1-50 us budget row; J0030's 134-149 us is recorded
openly. Proven: E4 + tests_armor/test_e4_injection.py; blessed archive
e4_bias_recovery_20260716T154452Z. Leans on [deJager89], [NG15],
[NICERarch], [PINT].

## 3. Findings — the apparatus (methodology as a result)

**F11 [DONE] The reproducibility machine.** A truth wall separating
simulator from navigator, enforced by an uneditable AST test + two
independent human-style audits per card; every tolerance frozen in one
deny-locked golden file with 13 evidence-commented authorized overrides
(12 carry explicit #2-#13 labels; the first predates the numbering —
sweep-corrected wording; the sweep additionally counts ~6 pre-numbering
lock-lift EVENTS in the logbook, so whether the aggregate reads "13" or
"18" is a ratification wording call — worksheet note); 92 tests across two pinned environments (84 spine, run by the DEFAULT
pytest gate on native Windows Py 3.13.3/numpy 2.4.1; 8 armor, run ONLY by
explicit WSL2 invocation in the float128 env — the split forced by a
measured platform limit and documented per-version, per-hash; sweep O7:
re-run + record the armor 8 at the science freeze, since no routine gate
collects them);
every figure regenerable from committed arrays alone; every blessed
number byte-reproducible from a fresh clone; a maximum-correctness sweep
(4 independent legs incl. first-principles physics re-derivation to
2.2e-16) closed all-green. This section IS a finding: it is what makes
every other claim survivable under hostile questioning.

## 4. Proposed next findings [ALL AWAITING STUDENT RULING; prior-art scouted 2026-07-16]

**F12 [PROPOSED] The starlight chronometer precision law.** sigma_epoch —
how precisely a lost, clockless observer can read WHAT YEAR IT IS from
star geometry alone — as a function of (range, star count, sensor noise,
CATALOG AGE), via the 7-state joint solve. NARROWED claim (scout-verified):
the capability is pre-owned (plate dating: Barron et al. 2008 "Blind
Date"; joint 7th parameter: [BJ21] — who never reports sigma_epoch); the
PRECISION LAW and its catalog-age axis are unpublished. Must-cite:
Barron08 (live-verified), BJ21. STRUCK by the 2026-07-17 sweep: the
scout-suggested "He&Zhao 2025" and "SESCC 2026" FAILED live verification
(no matching papers found — possible hallucinated references); before F12
is drafted the students must find real ancient-catalog/plate-dating
adjacent refs or proceed with Barron08 alone.

**F13 [PROPOSED] The navigation capacity of the Galaxy.** The full-catalog
Fisher/CRLB ceiling on position knowledge, mapped over galactic location —
the limit no camera or algorithm can beat; result-not-method novelty
(technique is textbook and must be framed so). Must-cite: BJ21
(N-scaling), arXiv:2512.04326 (per-star measurement floor — different
level), StarNAV19, LONEStar/Krause24, classical GDOP; ADDED by sweep O8:
Fialho & Mortari 2019 (Sensors 19(24):5355, arXiv:1910.00558 — a
fundamental stellar-accuracy limit at ONE galactic location; F13's map
over the whole galaxy must distinguish it explicitly).

**F14 [PROPOSED] The comb-lock HOLD frontier.** The (sigma_v, coast time,
K pulsars, sigma_TOA) surface on which a fused starlight+pulsar probe
KEEPS a comb lock acquired at departure — with the acquisition/hold split
stated plainly (velocimetry holds a lock; it cannot shrink the 1-au
acquisition prior — E5's impossibility stands untouched). Must-cite:
Sheikh/Golshan/Pines 2007, cold-start XNAV (arXiv:2302.06741),
arXiv:2604.20182, Teunissen [LAMBDA], Deng13/Shemar16/Becker13; ADDED by
sweep O9: "Stellar Angle-Aided Pulse Phase Estimation" (Aerospace 2021,
10.3390/aerospace8090240) + [PulsarDoppler] — the stellar-aided
LOCK-HOLD mechanism is pre-owned in-system; only the interstellar
coast-hold SURFACE remains claimable, and the card must say so.
KILLED sibling for the record: "probe as gravitational-wave detector"
died at prior art + a 3-4 order sensitivity shortfall (Armstrong 2006;
J1713 single-pulsar limits; McGrath 2025).

**F15 [PROPOSED] The capstone: a drift-aware image->state solver.** Raw
spacecraft star-field image -> centroids -> star identification -> joint
7-state solve (position, velocity, epoch) weighted by AGE-INFLATED
catalog covariance -> "where you are, when you are, with error bars."
End-to-end demo target: the 12 raw New Horizons LORRI FITS frames already
on disk. Component novelty: none (plate-solving = Astrometry.net, Lang
et al. 2010 — cite up front); the drift-aware weighting and the printed
sigma_epoch/CRLB error bars ARE F12/F13/F4 operationalized. This is the
research made tangible, not a new claim.

## 5. The numbers table (memorize-grade)

| number | meaning | provenance |
|---|---|---|
| 1.064 (grid) / 1.045 (CI cells) | worst MC/CRLB ratios — optimal navigator | E1 archive + test_e1_harness |
| 3.019 au / 2.028 km/s | BJ21 anchor reproduced (3 / 2 published) | test_bj_anchor |
| 0.3467 au | real New Horizons recovered (JPL truth) | E3 archive |
| ~30 au | the miss if you skip epoch propagation | E3 journal |
| 7.66 au | epoch-parallax floor, 1 pc / 20 stars (sub-10-mas asymptote) | E6 journal (archive finest cell 7.70) |
| 44.8 -> 161.9 yr | catalog-age crossover vs sensor (10 mas -> 60") | E6 archive |
| ~15.9 arcsec | the knee below which cameras stop mattering at 1 pc | E6 archive |
| 286.02 km / 523,024x | comb packing radius / how far a 1-au fix overshoots it | E5 archive |
| 100.000% / 8,000 | exact integer recovery inside rho | Spec 8 tests |
| 1356 au / 1201 km/s | classical navigator's bias at 0.1c | E7 archive |
| 270.3 d @ 1 cm/s | comb-lock coast budget (467 km comb) | E5 archive |
| 0.0 (bit-identical) | two-route photon-phase agreement, 152,107 photons | Spec 9 |
| 3.39e10 turns | pulsar rotations tracked to 1e-9 of one turn | Spec 9 |
| 2^-29 exactly | the recombination bug's fingerprint | Spec 9 journal |
| H = 874.1 | J0437 fold significance (binary model validated) | E4 |
| 76.15 km / 1.85 sigma | 100 km bias recovery error / its honest size | E4 archive |
| 92 / 13 / 2 | tests / authorized overrides / pinned environments | repo |

## 6. Open items and boundaries

Students: ratification sitting (worksheet items a-ii). Rulings pending:
F12-F15 card menu (+ scout-2's real-catalog time-travel feasibility, in
flight). Deferred by ruling: E3 x60 reproduction (v1.1), template-fit TOA
estimator (v1.1), true-history GitHub push (project completion). Science
freeze 2026-10-01. The paper is the students' to write — this file is its
evidence index, not its draft.
