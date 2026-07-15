# Journal Entry — E6: Catalog Aging (the headline experiment)

## The result first, because this is the project's headline

E6 answers the flagship question: **how does navigation accuracy decay as the
star catalog ages?** It maps the Monte Carlo navigation error over a grid of
(catalog age × sensor precision) and shows three regions:

- an **epoch parallax floor** — even at age 0 the sampled catalog is imperfect,
  so navigation bottoms out at **~8.3 au** (measured 8.29 au at 1 pc, 20 nearest
  stars, finest sensor). This is the age-0-with-catalog-covariance baseline,
  realized *empirically* by E6a's parallax scatter — not a CRLB formula.
- an **aging-dominated region** at fine sensors, where the catalog's age, not
  the camera, sets the error. Measured at 10 mas: error grows 8.29 au → 17.81 au
  → 32.11 au at age 0 / 100 / 200 yr (**ratio 2.15× at 100 yr, 3.88× at 200 yr**).
- the **crossover** between them, **~51 years** at the 10 mas sensor (measured;
  design-review estimate ~55 yr).

The driver is the 554 stars (5 of the 20 nearest) with no catalog radial
velocity: their unmodeled ~30 km/s motion drifts them over decades, and the
navigator — assuming RV = 0 — cannot follow.

## The mechanics, one symbol at a time

For each grid cell (age `T`, sensor noise `sigma`), vectorized over `n_trials`:

**TRUTH side (generates reality):**
- `sample_true_skies` (E6a) draws `n_trials` true skies, scattering each star's
  parallax, proper motion, and radial velocity by its catalog error — and giving
  the RV-less stars a real ~30 km/s radial motion. Result: epoch positions and
  velocities, shape `(T, N, 3)`.
- the Spec-10 truth propagator ages each trial's sky by `T` years:
  `r_aged = r_epoch + v * T` (scalar-age branch — it broadcasts `(T,N,3)`
  correctly; E6 never uses the array-age branch, which does not, and the harness
  docstring says so).
- `observed_pair_angles` reads each trial's OWN aged sky against the one fixed
  observer (the true spacecraft position) and returns the noisy measured
  pair-angles `(T, P)`.

**NAV side (what a real spacecraft has):**
- ages its PUBLIC catalog by the same `T` years with the Spec-10 *nav* propagator,
  using the catalog's central proper motions and `rv_fill_kms = 0.0` (the
  navigator's best guess for a missing RV is zero — documented). Result: aged
  catalog positions `(N, 3)`.
- selects star pairs FROM THESE NAV POSITIONS (required — truth is now per-trial
  `(T,N,3)` and cannot feed `select_pairs`; this is the delta from E1, item (z)).
- E1's unweighted Gauss-Newton solver recovers each trial's position from the
  measurements + the aged nav positions + a plan-based start. It reads NOTHING
  truth-side — only the measurement vector and public catalog values (the E6a
  forward advisory, honored).

**Score:** `rms_au[age, sigma]` = RMS over trials of `|estimate − true position|`,
with the true spacecraft position equal to the plan position (no execution
error, as in E1).

## The truth wall in this experiment

The only thing that crosses from truth to nav is the **measurement vector** —
exactly what a real camera would hand the flight computer. The solver, the
covariance (not used in v1), and pair selection all read public/aged-catalog
values. No sampled-truth array and no `sampled_catalog` dict ever reaches a nav
function. This is the discipline the E6a audit flagged as binding, and it is
what makes the decay curve honest rather than an artifact.

## The student's in-session headline ruling (recorded)

The plan's sensor axis stopped at 10 arcsec. But the epoch parallax floor is
~8.3 au, and camera noise only *equals* that floor around **~19–20 arcsec**
(measured: age-0 error 9.14 au at 10″, 11.18 au at 19″, 11.46 au at 20″, 16.27 au
at 35″). So the sensor-limited region the figure needs to show lives ABOVE the
plan's original ceiling. The student ruled in-session (2026-07-16) to
**(A) extend the sensor axis to 60 arcsec** and **(B) annotate the epoch parallax
floor** on the figure. Both are applied; the grid runs 0.01″–60″, and the figure
labels the floor and the catalog-limited vs sensor-limited regions.

The age grid also gained 40 and 70 yr (design-review amendment): the knee is near
~55 yr and the plan's 50→100 gap was too coarse to resolve it.

## Measured evidence (mine, corroborating the design-review tables)

| quantity | measured (this session) | design review |
|---|---|---|
| epoch parallax floor (1 pc, 20 stars, finest sensor) | 8.29 au | ~8.3 au |
| aging ratio at 100 yr (10 mas) | 2.15× | ~2.0× |
| aging ratio at 200 yr (10 mas) | 3.88× | ~3.8× |
| crossover age (10 mas) | 51 yr | ~55 yr |
| camera noise ≈ floor | ~19–20 arcsec | ~19 arcsec |
| nearest-20 stars lacking RV | 5 of 20 | 5 of 20 |

Smoke-scale (T2, 40 trials) aging ratio at 100 yr over 6 seeds: **2.01, 2.03,
2.72, 2.23, 2.03, 2.26** (min 2.01); seed-42 ratio 2.17 (rms 7.52 → 16.27 au).
The 1.5 gate sits comfortably below the seed minimum — none approach it, so the
STOP condition (measured ratio ≤ 1.5) never triggered.

The 100-yr aging term is NOT the raw 633 au single-star drift: that motion is
mostly radial, and only the transverse fraction (~D/d ≈ 0.26–0.42 at 1 pc) shows
up as a position error, fused across 20 stars — an induced ~14.7 au aging term
that adds in quadrature over the ~8.3 au floor to give the ~2× ratio. (This is
exactly the correction that sank the first draft; see below.)

## Every tolerance, and why

- **T1** uses the existing `SOLVER_RECOVERY_TOL_AU = 1e-8 au`. Measured worst over
  all ages: **3.56e-11 au** (~280× inside the gate).
- **T2/T3** use `E6_AGING_SMOKE_MIN_FACTOR = 1.5` — **AUTHORIZED OVERRIDE #7**, a
  coarse WIRING alarm (aging must visibly hurt), not a precision claim. It sits
  below the seed-minimum aging ratio (2.01) and above the no-op ratio (~1.0), and
  bounds the sensor-limited flank from above (at 60″, 5 yr of aging gives ratio
  1.001).
- **T4/T5** are exact wiring/output checks — no tolerance.

No tolerance was invented; the two used constants are the existing recovery gate
and the one authorized override.

## The tests, and what each would catch

`tests/test_e6_harness.py`, a 2×2 smoke corner of the real grid, fixed seed:

- **T1 perfect-catalog null.** Errors zeroed, missing RVs filled identically 0.0
  on both sides, perfect camera: at every age the solver recovers the truth to
  the machine-precision gate. Catches any wiring/sign/frame bug (it lands orders
  past 1e-8). (The *bitwise* form the first draft used FALSE-FAILS — see below.)
- **T2 aging hurts.** Realistic sampling: 100-yr error > 1.5× age-0 error at a
  fine sensor. Catches a harness that doesn't actually age the truth, or ages the
  nav catalog to match (which would hide the decay).
- **T3 sensor-dominated flank.** At 60″, 5 yr of aging stays under 1.5×. Catches
  a harness that lets aging dominate even where the camera should — the
  degradation ordering is the qualitative headline.
- **T4 measurement provenance.** Perturbing one trial's sampled true sky moves
  only that trial's measurements; perturbing the nav catalog moves only the
  solution. The E6-adapted E1-swap wall proof.
- **T5 outputs + replot.** The npz carries every plotted array + params + seed,
  and the figure regenerates from the npz alone (closing the recorded
  no-replot-path finding for E6).

## The first-draft rejection history (recorded honestly)

The first E6b draft was **REJECTED by design review with measured evidence** —
two acceptance tests would have failed on *correct* code:

1. **T1 as a bitwise identity was wrong.** It assumed a perfect catalog makes
   truth and nav age to bit-identical positions. They don't: truth and nav use
   INDEPENDENT velocity builders (the aberration-card precedent, agreeing to
   ~1e-12, not bitwise), so their aged positions differ by ~1e-11 au and the
   bitwise assert false-fails. Fix: assert recovery to `SOLVER_RECOVERY_TOL_AU`
   (measured worst 3.56e-11 au, ~280× margin).
2. **T2's factor of 5.0 was wrong.** The first draft derived it from the raw
   ~633 au single-star drift at 100 yr. But that drift is mostly radial; the
   induced *position* error is the transverse-projected, 20-star-fused ~14.7 au
   term, giving a real ratio of ~2.0, not ~5. A 5.0 gate would fail correct code.
   Fix: `E6_AGING_SMOKE_MIN_FACTOR = 1.5` (override #7), below the measured seed
   minimum.

Recording this so the number 1.5 is never mistaken for a fudge: it is the
corrected, measured-and-margined wiring gate.

## What this does NOT do (deferred, flagged)

- **No aging-aware navigator.** The solver is E1's, oblivious to age; an
  age-inflated covariance `W` is a real design fork left as a future card.
- **No CRLB overlay** in v1 (the age-0 baseline is empirical, not theoretical) —
  a recorded student option.
- **No binary contamination** (inherited from E6a's deferral — the students must
  source a contaminated fraction first).

## Where this sits, and what's next

E6 is the capstone that everything since Spec 1 was built toward: the angle
geometry, the truth simulator, the Gauss-Newton solver, the CRLB, the catalog
covariance, the deterministic propagator (Spec 10), and the sampled sky (E6a) all
feed this one figure. **Next (after this commit and the two audits): run the FULL
grid** (10 ages × 10 sensors × 500 trials), archive the npz + PNG per the
blessed-results procedure, and log the headline numbers (crossover ages per
sensor, floor value, knee location). The team lead's instruction is explicit that
the full grid runs *after* the commit, not now.

## Ratification items and process note

Under the recorded exception, this card's text and its five tests were
AI-authored (ratification pending). Items for the students:
- **(x)** ratify the card and the student's own extend-sigma-to-60″ + annotate-floor
  headline ruling;
- **(y)** ratify the crossover DEFINITION: `rms(age) = sqrt(2)·rms(0)`, interpolated
  in log-age, censored where the curve exits the range;
- **(z)** ratify the nav pair-selection delta from E1 (E6 selects pairs from the
  nav catalog because truth is per-trial; E1-swap had left them on the shared
  array).
