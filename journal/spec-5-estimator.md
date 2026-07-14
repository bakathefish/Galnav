# Journal Entry 5 — The Solver: "Where Am I?" Answered

## The moment this project has been building toward

Four bricks are now stacked: measure an angle (1), know how motion shifts
stars (2), fake an honest sky (3), predict-and-differentiate from a guess
(4). Today they snap together into the thing itself: hand the navigator
nothing but measured angles, the public catalog, and a rough guess — and
it finds the spacecraft. With a perfect camera it lands within 3.4e-10 au
of the true spot. That's machine precision: about a golf ball's width of
error on a five-light-year measurement.

## The idea, with a hot-and-cold game

You're blindfolded in a room, guessing where you stand. A friend tells
you, for each of several landmarks, how DIFFERENT their compass bearings
look from your guess versus reality. From Spec 4 you also know exactly
how each bearing WOULD change if you stepped 1 meter in any direction. So
you can compute — not guess — the precise step that best cancels all the
disagreements at once. Take it. Repeat. Each round roughly DOUBLES the
number of correct digits in your position, which is why 4 rounds get from
1000-au wrong to machine-precision right.

## The exact math, symbol by symbol (derivation D3)

The one function, `solve_position`, in `galnav/nav/estimator.py`:

**Step A — the residual (the disagreement list):**

    r = measured - predicted(p)

**r** = a list with one number per star pair: measured angle (from the
camera) minus predicted angle (Spec 4's crystal ball at guess **p**).
Perfect guess → all zeros. Units: radians.

**Step B — the linearization (the only calculus in it):** near the
current guess, each predicted angle changes almost linearly with position
— and Spec 4's Jacobian **J** IS that linear map (P pairs x 3 directions,
radians per au). So if we step by **delta** (3 numbers, au):

    predicted(p + delta) ≈ predicted(p) + J·delta

**Step C — the best step (least squares):** we want J·delta to cancel r
as well as possible. With 7 disagreements and only 3 knobs, "as well as
possible" means minimizing the summed squared leftover — least squares.
School calculus (set the derivative to zero) turns that into the NORMAL
EQUATIONS:

    (J^T J) · delta = J^T · r

J^T J is a tiny 3x3 table; solving it for delta is one `np.linalg.solve`
call. We wrote the normal equations EXPLICITLY (rather than a black-box
least-squares call) because this is derivation D3 — the exact equation we
must reproduce on blank paper in judging interviews. The code is the
derivation.

**Step D — apply and repeat:**

    p <- p + delta ; stop when |delta| < step_tol_au

Each round re-predicts, re-differentiates, re-solves. This loop is
Gauss-Newton: Gauss invented least squares for exactly this job —
recovering the orbit of the lost asteroid Ceres in 1801 from a handful of
noisy telescope bearings. We are doing his problem in reverse: he found
the rock from the observatory; we find the observatory from the rocks.

## Every tolerance, and why (all measured before freezing)

- **SOLVER_RECOVERY_TOL_AU = 1e-8 au**: measured worst-case recovery
  error from four different 1000-au starting offsets is 3.4e-10 au — the
  gate sits 29x above the measured floor, yet a millionth of any
  physically meaningful error. "Machine precision" made checkable.
- **SOLVER_STEP_TOL_AU = 1e-9 au**: the "corrections have vanished"
  threshold — above the ~1e-10 rounding floor, far below anything
  physical. Passed IN by the caller (tests supply it from the answer
  key): the solver itself contains zero magic numbers.
- **SOLVER_MAX_ITERS = 10**: the plan's gate. Measured: 4 rounds, every
  start direction — 2.5x headroom. Because healthy Gauss-Newton doubles
  correct digits per round, needing more than 10 from a good start means
  the Jacobian and residual disagree — a bug, and this gate refuses to
  let it hide.

## Which tests prove it, and what each would catch

1. **Machine-precision recovery from four start directions** (axes and
   diagonal): a wrong residual sign diverges; a wrong Jacobian converges
   to the WRONG point; any systematic bias leaves a gap this gate sees.
2. **Fewer than 10 rounds, every direction**: catches
   slow-creep convergence — right answer reached the wrong way.
3. **Honest iteration counter**: starting EXACTLY at the answer must
   report at most one round. Catches an off-by-one or decorative counter
   before Spec 6 and the experiments start trusting it as a diagnostic.

## What this does NOT do (each deferred until its own test exists)

- **No noise handling beyond averaging.** Tests feed a perfect camera;
  noisy-camera statistics (error bars) are Spec 6's whole job.
- **No weights (the W in WLS).** All pairs count equally today. Per-star
  weighting arrives with catalog covariance in Spec 7.
- **No damping (Levenberg-Marquardt).** Plain Gauss-Newton, because from
  good starts it's provably enough (4 rounds, measured). Damping matters
  for BAD starts — that's experiment E2 territory, and choosing a damping
  strategy is a derivation-level decision the students make when its card
  arrives.
- **No attitude, no velocity.** Pair angles don't care which way the
  camera points; velocity enters with aberration later.

## Where this fits

This closes the core loop: truth makes measurements → navigator solves
position → we grade it. Spec 6 asks the money question for a NOISY
camera: "how wrong is the answer, statistically?" — and checks that the
scatter of many solved positions matches the theory formula (J^T W J)^-1.
That formula versus reality IS experiment E1, the project's first
research figure.
