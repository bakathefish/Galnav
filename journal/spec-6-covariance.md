# Journal Entry 6 — Error Bars: How Wrong Is the Answer?

## Why "where am I?" is only half the question

Spec 5's solver finds A position. But with a real, noisy camera, every
measurement session would give a slightly different answer. Run it a
thousand times and the answers form a CLOUD around the truth. A navigator
who reports "I'm at X" without "give or take Y" is dangerous — the whole
point of this project is mapping exactly how big Y gets under different
conditions. Today: predict the cloud's size with a formula, then bombard
the formula with 500 simulated universes to check it tells the truth.

## The formula, symbol by symbol (derivation D4)

    Cov = sigma^2 * (J^T J)^-1

- **sigma** = the camera's per-measurement noise, radians. Squared
  because statisticians work with variances (spread-squared) — they add
  nicely, spreads don't.
- **J** = Spec 4's sensitivity table: how much each pair angle changes
  per au of position change. **J^T J** is the tiny 3x3 "information
  matrix": how much the measurements collectively pin down each direction
  of space. Big entries = strong grip.
- **(...)^-1** = matrix inverse — the flip from "how firmly measurements
  grip position" to "how far position can wiggle": a strong grip
  (big information) means a small wiggle (small covariance). Where the
  measurements grip weakly, the cloud stretches.
- The result is a 3x3 matrix in au². Its diagonal, square-rooted, is the
  per-axis error bar in au. Off-diagonals say how errors lean together
  (the cloud is a tilted ellipsoid, not a ball).

Where it comes from: push measurement noise through the solver's own
normal equations (Spec 5) with first-year algebra — the same J that
CORRECTS the guess also tells you how noise SHAKES the answer. One
matrix, two jobs.

**The bonus meaning (derivation D6):** for Gaussian noise this same
formula is the CRAMER-RAO LOWER BOUND — a theorem that NO unbiased
navigator, however clever, can beat this error bar. So when experiment E1
shows our solver's cloud matching this formula, we're not just saying
"our code agrees with our math" — we're saying "our navigator is as good
as physics allows." That's the theory spine of the whole project.

## What got built (and one rule that shaped everything)

Your project rule says: vectorize over Monte Carlo trials — NO Python
loops over trials. 500 trials must be solved as one batch of arrays, not
500 laps of a loop. So this card taught the EXISTING functions to accept
stacks:

- **`measmodel.py` (upgraded, same math):** every function now accepts
  either one position (3,) or a stack (T, 3), returning matching stacks.
  The change is mechanical — operate on the LAST axis instead of a
  numbered one — and the 18 pre-existing tests pin that single-position
  behavior didn't move by one bit.
- **`observer.py` (upgraded):** hand the pretend camera T copies of the
  true position and it returns T independent noisy measurement sets in
  one call, all randomness still through the rng argument.
- **`solve_position` (upgraded):** the SAME solver now advances all 500
  trials simultaneously each Gauss-Newton round — the only remaining loop
  is over rounds, which are sequential by nature (each needs the last).
  The 3x3 solves happen batched (numpy solves 500 little systems at
  once). A dedicated test proves batch answers equal single-trial answers.
- **`position_covariance` (new, 3 lines):** the D4 formula itself.

Payoff measured: the full 500-trial Monte Carlo runs in well under a
second — the E1 experiment budget (500 trials per grid cell in under
10 s) is beaten by more than an order of magnitude before E1 even exists.

## Every tolerance, and why (measured before freezing)

- **MC_TRIALS = 500** (plan value): enough trials that the scatter
  estimate is trustworthy, few enough to stay fast. At 500, statistics
  itself makes any measured scatter fuzzy by about 1/sqrt(2*500) ≈ 3.2%
  per axis — that fuzz is a law of sampling, not a code property.
- **MC_CRLB_REL_TOL = 0.15** (plan value, D4's "~10-15%"): we ran the
  full 500-trial comparison in 20 DIFFERENT random universes; the worst
  per-axis disagreement was 10.2%. So 15% is honest: statistically
  reachable fluctuation stays under it, while a real formula error
  (wrong J, missing sigma^2, transposed matrix) throws the comparison off
  by 2x or more. The committed test uses one fixed seed — deterministic
  and replayable — with the 20-seed sweep recorded in the logbook as
  evidence that no seed-luck is involved.
- **SOLVER_RECOVERY_TOL_AU** (reused): the batch-equals-single test
  demands agreement at the solver's own proven precision gate.

## Which tests prove it, and what each would catch

1. **Symmetric + positive-definite:** a covariance that fails either
   isn't a covariance — catches transposed or sign-flipped formulas
   before any statistics run.
2. **Batch equals single:** the vectorized solver must reproduce the
   proven single-trial solver exactly — otherwise the Monte Carlo would
   validate DIFFERENT code than the navigation actually uses. Guards the
   whole broadcast upgrade.
3. **The D4 checkpoint:** 500 noisy universes, one vectorized solve, and
   the per-axis scatter must match the formula within 15%. Catches a
   wrong Jacobian, a mis-scaled sigma, a biased solver — anything that
   makes theory and reality drift apart.

## What this does NOT do

- **No weights (W).** Every measurement counts equally today, so W is the
  identity and Cov = sigma^2 (J^T J)^-1. Per-star weighting — where a
  shaky catalog star counts less — arrives with Spec 7, whose test will
  make W earn its place.
- **No bias check beyond the scatter.** The mean of the cloud sitting on
  the truth is implicitly exercised (a biased cloud would blow the
  scatter gate), but a dedicated bias gate is a student decision if E1
  wants one.
- **Still no aging, no proper motion, no pulsars.**

## Where this fits

This card completes the instrument: simulate → solve → predict error →
verify error. Experiment E1 — the first research figure — is now just
this card's machinery swept over a grid (star count x distance x noise)
and drawn as a picture: Monte Carlo dots tracking the CRLB line. The
theory-vs-reality agreement we proved today at one point, E1 proves
everywhere — and then E6 breaks it on purpose, by aging the catalog.
