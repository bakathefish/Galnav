# E2 — Convergence basins of the navigator

*AI-authored under the build-night ratification-pending pattern (user granted
full build authority 2026-07-16). Ruling on the failure-handling fork:
OPTION A, decided under that authority, ratification-flagged (worksheet item
(cc)); students can override at the sitting.*

## The one-sentence idea

E1 asked "when the navigator starts 173 au from the truth, how accurate is the
answer?" E2 asks the opposite question: **how far can the starting guess be
before the navigator can no longer find its way home?** That "how far" region is
the solver's *convergence basin*, and its size is the headline of this
experiment.

## Why this matters

A real spacecraft that has been coasting for years may only know where it is to
within light-years. Before it can refine that guess with star sightings, the
Gauss-Newton solver has to *converge* — and Gauss-Newton only converges if you
start it close enough to the answer. "Close enough" is exactly the basin. If the
basin is big, a coarse prior is fine; if it is small, you need a good prior
first. E2 measures the basin as a function of how many stars you look at.

## What the code does, one symbol at a time

Fix the spacecraft at distance `D = 1 pc` along E1's direction; call its true
position `x*` (au). For a chosen displacement magnitude `ρ` (au) and star count
`N`, we test many random *directions* `û` (unit vectors) and start the solver at

    x₀ = x* + ρ · û .

`û` is drawn **isotropically** — uniform over all directions on the sphere — by
normalising a 3-D standard-normal draw `g`:

    û = g / |g| ,  g ~ N(0, I₃) .

The standard normal is spherically symmetric, so this is genuinely uniform on
the sphere. (A tempting shortcut — draw a uniform cube `[-1,1]³` and normalise —
is NOT uniform on the sphere: it over-weights the cube's diagonals. Test T5
guards against that mistake.)

The measurements are **noise-free** (`σ = 0`). A convergence basin is a property
of the residual landscape itself, not of measurement noise; with `σ = 0` the true
position `x*` is an exact residual-zero fixed point, so a trial either climbs
back down to `x*` (a *capture*) or wanders off to some other stationary point or
to infinity (an *escape*).

A trial is a **capture** iff BOTH:

1. every coordinate of the solved position is finite, and
2. `|x_solved − x*| < SOLVER_RECOVERY_TOL_AU`.

The **capture fraction** of a cell is the fraction of the `n_trials` directions
that are captures. Sweeping `ρ` (columns) against `N` (rows) gives the basin map.
The **0.5-capture radius** for each `N` — the displacement at which half the
directions still converge — is the basin's median radius, read off by
log-interpolating the capture-fraction row through 0.5.

## The failure-handling fork (A vs B vs C vs D) — the load-bearing decision

The batched solver `solve_position` does one `np.linalg.solve(JᵀJ, Jᵀr)` for the
whole Monte-Carlo batch at once. Near the basin edge a start that begins
well-conditioned can **diverge and drive that one trial's `JᵀJ` singular at some
Gauss-Newton round**, and `np.linalg.solve` then raises `LinAlgError` for the
*entire batch* — one escaping trial kills the whole cell, exactly at the edge we
are trying to resolve. Four ways out were weighed:

- **A — per-trial failure isolation (CHOSEN).** Draw all directions batched up
  front, then loop the *solve call only*, per trial, in a `try/except
  LinAlgError`. An escaping trial is caught and counted as a non-capture; the
  rest of the cell is unaffected. ~10 lines; the reviewer measured it at seconds
  for the full grid.
- **B — damp/mask the solver.** Add Levenberg-Marquardt damping so `JᵀJ` is never
  singular. This changes the *shipped* solver, which would force a re-bless of
  E1, E6, and the Bailer-Jones anchor. Too invasive for an experiment.
- **C — hold for the ratification sitting.** Stalls the build for a decision the
  build authority already covers.
- **D — batched pre-solve condition screen.** Compute `JᵀJ`'s condition number
  for all trials before solving and skip the ill-conditioned ones. **This does
  not work**: the singularity first appears *mid-iteration* (a trial that is
  perfectly well-conditioned at round 1 goes singular at round 5), so a
  pre-solve screen is blind to it. Making D correct needs retry/bisection
  machinery inside the solver — more cleverness than the problem is worth.

The project rule: *"Simplicity beats cleverness. Always."* A is the simple, correct
choice. It **knowingly breaks the project's "no Python loops over Monte-Carlo
trials" rule**, and that exception is recorded here and flagged for ratification
(item (cc)): the rule exists for THROUGHPUT, but this loop is FAILURE ISOLATION,
not throughput — it runs in seconds, and there is no vectorised way to isolate a
mid-iteration singularity without re-writing the deployed solver.

## What the code does NOT do

- It does NOT add measurement noise — the basin is a landscape property (`σ = 0`).
- It does NOT change `solve_position` — it wraps it. E2 characterises the
  **deployed** navigator, so it reuses the shipped step tolerance
  (`SOLVER_STEP_TOL_AU`) and iteration budget (`SOLVER_MAX_ITERS`) unchanged.
- It does NOT sweep distance or camera noise — one distance (1 pc), so the
  figure's two axes are displacement and star count alone.
- It does NOT extrapolate a basin edge where none exists in range (the
  degenerate-field guard returns NaN for all-captured or all-failed rows).

## Every tolerance, and why

Three existing goldens are reused, and ONE new golden is added (override #10):

- `SOLVER_RECOVERY_TOL_AU` — the capture radius (clause 2). It is the same
  exact-recovery tolerance E3's synthetic tests use; a captured trial has
  returned to the truth to within it.
- `SOLVER_STEP_TOL_AU`, `SOLVER_MAX_ITERS` — the deployed solver's own stopping
  rule and iteration cap. Using them (rather than bespoke values) is the point:
  E2 measures the basin of the navigator we actually ship.
- `E2_ISOTROPY_M4_TOL = 0.01` (authorized override #10) — the isotropy gate for
  the direction sampler (T5). A uniform unit vector on the sphere projects onto
  ANY unit vector as `Uniform(-1, 1)`, whose 4th moment is exactly `1/5`, so the
  axis and body-diagonal 4th moments must agree (`|m4_axis − m4_diag| ≈ 0`). A
  normalised-uniform-cube sampler — the bug this guards — instead gives axis
  ≈ 0.18 vs diagonal ≈ 0.21, a ≈ 0.033 gap. The *second* moment does NOT
  discriminate (both give variance ≈ 1/3), which is exactly why an earlier
  variance-based version of this test was WEAK and had to be replaced. At the
  test's `N = 200,000` draws the sample-4th-moment standard error is ≈ 6×10⁻⁴
  (`Var(m4) = (1/9 − 1/25)/N` for `Uniform(-1,1)`); the correct draw measures
  ≈ 2×10⁻⁴ at the fixed seed and ≤ ≈ 2.5×10⁻³ over 200 seeds, so 0.01 sits ~4×
  above the correct draw's worst case and ~3× below the cube bug.

## The grid, and why it is shaped this way

- `STAR_COUNTS = [5, 10, 20, 50, 100]` — more stars means more angle constraints
  and a wider, gentler residual bowl, so the basin should grow with `N`.
- `DISPS_PC = [0.1, 1, 2, 3, 5, 8, 12, 20, 100]` — the end anchors 0.1 pc and
  100 pc bracket "always captured" and "never captured"; the interior is dense
  across 1–20 pc because the measured 0.5-capture radius runs ~2 pc (5 stars) to
  ~12 pc (100 stars), so that is exactly where the basin edge must be resolved.
  (The first draft's grid wasted three of seven points below 1 pc and resolved
  the transition at roughly one-point resolution — reviewer amendment.)

## Every test, and what it would catch

- **T1 — off-grid anchor.** From `|START_OFFSET_AU|` ≈ 173 au (E1's proven good
  start, ~120× *smaller* than the smallest grid column, so explicitly OFF the
  grid) every direction sits deep in the basin: capture fraction must be exactly
  1.0. Catches a mis-wired solve or capture test.
- **T2 — monotonicity.** Per star count, capture at the smallest displacement ≥
  capture at the largest. The basin is a connected neighbourhood, so pushing
  farther can only lose directions. Catches a sign error or an inverted basin.
- **T2b — the basin is finite (headline pin).** Parameter-free, tolerance-free
  (strict inequalities only): at the smallest star count, capture at the largest
  displacement is strictly below that at the smallest AND strictly below 1.0 —
  there is a wall the solver cannot cross. Catches a basin that never closes
  (capture 1.0 everywhere), which would be physically wrong yet still pass T2.
- **T3 — capture predicate, BOTH clauses.** An exact hit captures; a finite-but-
  far point does NOT (distance clause); a NaN or inf does NOT (finiteness
  clause). Catches dropping either clause — dropping the distance clause would
  miscount the ~30% finite-but-wrong basin-edge population as captures.
- **T4 — determinism.** Same seed → bit-identical grid. Catches any hidden
  global randomness or an unstable draw order.
- **T5 — isotropy.** Directions are unit vectors, and the projection variance
  onto a coordinate axis equals that onto a body diagonal (true only for a
  spherically-uniform draw). Catches the normalised-cube mistake.
- **T6a — degenerate-field guard.** An all-captured or all-failed row returns NaN
  from the 0.5-radius finder, and a genuine crossing returns a value strictly
  inside the bracket. Catches a fake extrapolated basin edge.
- **T6b — outputs + replot.** The npz carries every plotted array and the figure
  regenerates from it alone. Catches a figure that secretly depends on a
  recompute.

## Where this sits, and what is next

E2 closes the "can the navigator even start from a coarse prior?" question and
supplies the **measured basin** as evidence for the standing solver-damping
question (worksheet item (r)): the undamped Gauss-Newton solver already captures
from ~2–12 pc at 1 pc with 5–100 stars, so a coarse interstellar prior is well
inside the basin without damping. Next in the build order: E7 (relativistic
aberration armour, pure-numpy), then the blocked cards (Spec 9 PINT, E4
NICER/HEASoft).

## Measured headline (reduced-trial probe, seed 42)

0.5-capture radius: 5 stars ≈ 1.9 pc, 10 ≈ 3.9, 20 ≈ 6.3, 50 ≈ 9.8, 100 ≈ 11.5 pc
— monotonic in star count, matching the design reviewer's independent probe
(2.0 pc at 5 stars, 11.8 pc at 100). The blessed full-grid numbers are recorded
in the logbook and the archive Contents entry.
