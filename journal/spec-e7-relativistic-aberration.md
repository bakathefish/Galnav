# E7 — Relativistic aberration at 0.1c (the relativistic armor)

*AI-authored under the build-night ratification-pending pattern (user granted
full build authority 2026-07-16). The card was adversarially reviewed by main
and APPROVED WITH AMENDMENTS; every amendment is folded in here — the corrected
payload, the honest "wrong-physics" labelling, the reframed peak discriminator,
and the three distinct aberration maxima. Worksheet item (dd).*

## The one-sentence result

At an interstellar cruise speed of 0.1c, a navigator that uses the classical
(Galilean) aberration instead of the exact special-relativistic form mislocates
the spacecraft by **~1350 au** — while the exact navigator recovers to ~1e-9 au.
**Relativity is not a refinement here; it is the difference between arriving and
being lost.**

## Why this experiment exists, and what it is NOT

The velocity+aberration card already proved the navigator recovers position AND
velocity from a single moving-camera snapshot, and the Bailer-Jones anchor
already spans speeds 0–0.5c. So E7's job is NOT "does aberration-aware nav work"
(settled). E7 isolates a sharper question: **at 0.1c, does it matter that we use
the EXACT relativistic aberration rather than the classical approximation?** The
answer is a resounding yes.

E7 is an EXPERIMENT ONLY. It does not touch `galnav/`. The aberration is already
exact special-relativistic on both sides of the truth wall — truth `_aberrate`
and nav `_aberrate_nav` are independent Klioner-2003 k-forms carrying the Lorentz
factor γ, and they agree to ~1e-16. There is therefore NO Galilean aberration
anywhere in `galnav` to "reuse": the classical predictor E7 needs is NEW,
experiment-local, and DELIBERATELY WRONG physics, honestly labelled as such.

## The three aberration maxima (never conflate them)

For β = 0.1 the maximum aberration deflection has three different values
depending on the physics used, and the card's first draft conflated them:

| model | formula | max deflection | peak angle |
|-------|---------|---------------:|-----------:|
| small-angle | β (radians) | 5.730° | 90° |
| Galilean (classical, Lauer Eq. 1) | arcsin(β) | 5.739° | arccos(−β) = 95.74° |
| exact relativistic | γ-form ([SR-ABER]) | 5.746° | 92.87° |

The frozen golden `ABERRATION_MAX_DEG_AT_0P1C = 5.74` is the **Galilean**
value (arcsin(0.1)). The exact relativistic maximum is 26 arcsec larger — and,
crucially, its peak sits *closer* to 90° than the Galilean peak: **γ pulls the
peak toward perpendicular** (95.74° → 92.87°), it does not push it past. (The
first draft claimed the opposite; corrected.)

Measured (bounded 1-D optimizer for the peak location; the value is grid-robust):
Galilean max 5.7392° at 95.74°, exact max 5.7464° at 92.87°, gap 26.0 arcsec.

## Part A — aberration magnitude (formulas, symbol by symbol)

For a star at true angle θ from the velocity apex, seen by an observer moving at
β = v/c, the apparent angle φ is:
- **Galilean (classical):** φ = atan2(sin θ, β + cos θ). Deflection δ = θ − φ.
  This is the EXACT classical form (Lauer Eq. 1), NOT the small-angle β·sin θ.
- **Exact relativistic:** φ = atan2(sin θ, γ(β + cos θ)), γ = 1/√(1−β²)
  ([SR-ABER]; the only change is the γ multiplying the cosine term).

`max_deflection(β, relativistic)` maximizes δ(θ) over θ ∈ (0, π) with a bounded
optimizer. The **26 arcsec** gap between the two maxima is a Part-A curiosity —
it is NOT the payload (that pitfall is why the first draft understated the
result 20×).

## Part B — the exact navigator recovers the truth at 0.1c

Using the deployed `solve_state` (6-state damped Gauss-Newton, exact aberration,
light-cone guard) on the Sun-hub network (Sun + 19 nearest bright stars, 19 hub
angles — the anchor geometry), at a true speed pinned to exactly 0.1c radially
outbound, distances 0.1–10 ly, 0.9–1.1× start:
- **Zero noise:** max recovery error 1.2e-9 au / 8.0e-10 km/s across the
  ensemble — under the deployed golden `SOLVER_RECOVERY_TOL_AU/_KMS = 1e-8`. The
  truth and nav aberration implementations invert each other cleanly at
  relativistic speed. (Honest note, S2: the ~6× margin under the golden is
  thinner than the 16× the golden's own comment cites for the low-speed anchor —
  0.1c is a harder inversion; still a comfortable pass, recorded here.)
- **1 arcsec noise:** the honest achievable median accuracy at 0.1c (reported in
  the npz; same order as the anchor).

## Part C — THE PAYLOAD: a classical navigator is catastrophically biased

This is the corrected heart of the experiment.

**The model error is ~500 arcsec, not 26 arcsec.** The 26 arcsec gap is only the
difference of the two *maxima*. The quantity that actually drives the bias is the
**per-angle** difference between the exact and classical aberration in the real
hub geometry, evaluated at the true state:
    dθ_i = φ_exact(θ_i) − φ_classical(θ_i)
Measured median |dθ| ≈ 402 arcsec across the ensemble (θ = 90° alone gives
102.9 arcsec, matching citations.md's recorded ~103). This is ~400× the 1 arcsec
camera — the classical model is wrong at a level the instrument cannot excuse.

**The wrong-physics navigator.** `_classical_aberrate(u, v) = normalize(u + β)`
(β = v/c) is the classical (Lauer Eq. 1) aberration — it drops the γ the real
navigator carries. It is experiment-local and clearly labelled WRONG. From it,
`galilean_predicted_pair_angles` mirrors nav's `predicted_pair_angles_moving`
(reusing `_unit_directions` and `_pair_sin_cos`) differing in that one line, and
`galilean_solve_state` is a hand-rolled damped Gauss-Newton (step-halving +
light-cone guard, mirroring `solve_state`, no scipy in the loop) with a
finite-difference jacobian of the classical predictor. The finite-difference
jacobian keeps the wrong-physics predictor as the single source of truth (the
jacobian is derived from it, so the two cannot silently disagree); it is
vectorized over the whole ensemble (sub-second).

**Why finite differences are exact enough (the O(step²) argument).** Gauss-Newton's
converged fixed point is defined by the stationarity condition Jᵀr = 0; the
jacobian J enters only through *where* that condition is satisfied, so replacing
the analytic jacobian with a central-difference one moves the answer only by the
jacobian's own error, O(step²). With the step in its optimal band (h ≈ eps^(1/3)·L
where L is the scale over which an angle turns by O(1) — the star distance ~2×10⁵ au
for position, c ~3×10⁵ km/s for velocity — giving ~1 au / ~1 km/s), that error is
~10⁻¹² relative. Measured directly: the recovered bias is **identical to the
reported precision (1356.47 au / 1200.9 km/s) across four decades of step size**
(h ∈ [0.1, 100]) — utterly negligible against a signal ten orders of magnitude
above the recovery floor. The step is an implementation parameter of the probe,
not a physics tolerance (documented inline; precedent: the suite's own
FD-vs-analytic jacobian tests carry FD steps).

**Result (v1 primary — the full solve).** Feeding the EXACT measurements to the
classical navigator, its best-fit state is biased by a **median ~1356 au** in
position and **~1201 km/s** in velocity — roughly 400× and 600× the Bailer-Jones
anchor's own errors. The bias is ~12 orders of magnitude above the zero-noise
recovery floor.

**Linearized cross-check (disclosed, order-of-magnitude only).** The first-order
map δstate = (JᵀJ)⁻¹Jᵀ dθ (exact jacobian) gives median 1196 au — agreeing with
the full solve to ~12% at the median (and up to ~330% in the tail), because the
~500 arcsec model error is far outside the linear regime. It is reported as a
cross-check, never as the headline (the full solve is v1 primary — B2 amendment).

## Every tolerance / golden, and why

**No new golden number is introduced** (B-review confirmed, no override needed):
- Part A checks against the existing golden `ABERRATION_MAX_DEG_AT_0P1C = 5.74`
  (the Galilean max); the exact max is DERIVED from the `SR_ABER_PHI_RAD` oracle;
  arcsin(β) is derived in-test.
- Part B recovery keys off the deployed `SOLVER_RECOVERY_TOL_AU/_KMS`,
  `SOLVER_STEP_TOL_*`, `SOLVER_MAX_ITERS` — the point is the DEPLOYED navigator.
- Part C's payload gate is STRUCTURAL with a concrete floor (median |δpos| > 1 au;
  measured ~1350, i.e. orders above the floor), so no threshold golden is needed.
- `GALILEAN_MAX_ITERS = 60` is an experiment-local convergence budget for the
  wrong-physics fit (its residual never reaches zero), NOT a golden and NOT the
  deployed budget — documented in the module.

## Every test, and what it would catch

- **T1 (Part A magnitudes):** Galilean max == arcsin(β) and matches the golden;
  exact max ≈ 5.746° > Galilean; gap 25–27 arcsec. Catches a dropped γ or a
  small-angle shortcut.
- **T2 (γ discriminator):** exact peak (92.87°) < Galilean peak (95.74°). "Peak
  > 90°" holds for BOTH forms and does NOT discriminate; the ordering does.
  Catches a dropped γ that T1's value check alone could miss.
- **T7 (classical predictor sanity):** `_classical_aberrate` is the identity at
  β = 0 and slides a perpendicular star toward the motion at β ≠ 0. Catches a
  sign error or a broken normalization in the wrong-physics function.
- **T3 (Part B recovery):** the exact `solve_state` recovers the true 6-state at
  0.1c under the deployed recovery tolerances. Catches a truth/nav aberration
  mismatch at relativistic speed.
- **T4 (Part C payload):** the classical navigator's median position bias > 1 au
  (orders above the recovery floor) AND the per-angle model error is 100–2000
  arcsec (the ~500-arcsec truth, not 26). Catches a Part-C wiring that zeroes the
  bias or a payload that re-quotes the 26-arcsec max-gap.
  - *Disclosed blind spot (spec-review):* the > 1 au floor sits ~3 orders of
    magnitude UNDER the measured ~1350 au, so the test proves only that the bias
    is catastrophic, not its magnitude — the exact ~1350 au headline is pinned
    only by the blessed npz, not by a test. Left deliberately loose (no new
    golden); tightening it to, say, "> 100 au" is a student call at the
    ratification sitting (item (dd)).
- **T5 (determinism):** same seed → identical ensemble outputs.
- **T6 (outputs + replot):** the npz carries every plotted array; the figure
  regenerates from it alone.

## What E7 does NOT do (scope)

- No acceleration (constant velocity over the snapshot).
- No light-travel-time / retardation, no parallax-over-time — a SINGLE-EPOCH
  snapshot; star directions are taken at reception.
- No Doppler / photometric aberration, no time-dilation of the measurement
  epoch, no gravitational light bending.
- Does NOT modify `galnav/` (the aberration is already exact both sides).
- The Galilean predictor is experiment-local WRONG physics for the demonstration
  only; it is never used by the real navigator.

## Where this sits, and what is next

E7 is the last resource-free card. It closes the "relativistic armor" line: the
navigator's exact-aberration machinery is not decoration — at 0.1c it is the
whole ballgame. Everything remaining is blocked on the user (Spec 9 PINT
dependency, E4 NICER/HEASoft data, the pulsar closest-vector solver's
fpylll-vs-numpy decision) or on the students (the ratification sitting).

## Measured headline (full run, seed 42)

Part A: Galilean max 5.7392° (peak 95.74°) vs exact 5.7464° (peak 92.87°), gap
26.0 arcsec. Part B: exact recovery at 0.1c to 1.2e-9 au / 8.0e-10 km/s. Part C:
per-angle model error median 402 arcsec; classical-navigator bias median 1356 au
/ 1201 km/s (linearized cross-check 1196 au). Blessed numbers in the logbook and
the archive Contents entry.
