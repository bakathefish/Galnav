# Journal Entry — Velocity + Aberration (the anchor card)

## The result first, because it is the project's biggest so far

**The Bailer-Jones anchor is REPRODUCED.** With his exact protocol
mirrored — the Sun plus the 19 nearest bright stars, 19 hub angles at
1 arcsecond noise, 100 spacecraft placed isotropically at 0.1–10 light
years flying radially outward at 0 to 0.5c, solver started within 10%
of the truth — our navigator recovers:

- median 3D position error **3.019 au** (his angles-only "~3 au";
  precision note from the verification fleet: his oft-quoted measured
  2.8 au is the WITH-radial-velocities Fig. 8 scenario, and the
  angles-only scenario we mirror reads ~3.1 au — we sit between the
  two, 3% from the angles-only value)
- median 3D velocity error **2.028 km/s** (his "~2 km/s")
- our 16th–84th percentile position band **1.32–6.23 au** vs his
  Fig. 8 **1.3–5.8 au** — the error DISTRIBUTIONS match, not just the
  medians.

The plan's week-5 HARD GATE (Aug 15: "if the anchor is not reproduced,
cut the fusion leg") is passed on July 15 — a month early. The anchor
that E1 honestly left OPEN is now closed with an apples-to-apples test.

Three honest differences remain, disclosed in the test's own docstring:
we solve 6 unknowns to his 7 (our epoch is known; his Sec. 4.1 control
shows it costs nothing); our Gaia RUWE quality cut drops a few of his
famous nearest stars (alpha Cen A/B, Sirius — flagged binaries/bright),
so the 19-star lists differ in membership though not in character; and
he reports MCMC posterior medians where we take the damped Gauss-Newton
point estimate — the matching medians AND matching percentile bands are
the evidence those estimators agree here.

## The physics, one symbol at a time (derivation D8)

**Why a moving camera helps at all.** A camera flying at velocity v
sees every star slid toward the direction of motion (the apex) —
special-relativistic aberration. The slide depends only on v and the
star's angle from the apex, NOT on distance. So one snapshot of pair
angles carries velocity information: measured sensitivity on our
network, **0.38 arcsec of hub-angle change per km/s** (median). With
19 angles at 1 arcsec that's a ~2 km/s velocity fix — exactly what the
anchor delivers.

**The aberration map.** For a unit direction u (from craft toward the
star, in the rest frame) and b = v/c, gamma = 1/sqrt(1−|b|²):

    u' = (u + s·b) / D,   s = k(b·u) + gamma,   D = gamma(1 + b·u),
    k = gamma²/(gamma+1)

- u' — the direction the MOVING camera reports.
- k — the algebra trick that matters: the textbook coefficient
  (gamma−1)/|b|² is 0/0 at v = 0; since gamma−1 = k|b|², writing k
  keeps every quantity finite for a parked spacecraft.
- Checks a student can do: at v = 0, s = gamma = D = 1 and u' = u; a
  star dead ahead stays dead ahead; the scalar form of this map is
  exactly the golden oracle SR_ABER_PHI_RAD, phi =
  atan2(sin θ, gamma(β + cos θ)) — the [SR-ABER] formula (E7's
  formula, arriving one card early because the anchor needs it).
- Truth and nav each carry their OWN independently written
  implementation (truth: the Klioner 2003 Eq. 10 coefficient
  arrangement; nav: the k-form). The zero-noise recovery test inverts
  one through the other — if they ever disagree, that test fails.

**Sensitivity (the 6-column Jacobian).** The state is six numbers:
position (au) and velocity (km/s). Each pair angle's row has
- position columns: the Spec 4 chain, now passed THROUGH the
  aberration map — d(angle)/dp = g · (du'/du) · (du/dp), where
  du'/du = (I + k·bbᵀ − u'(gamma·b)ᵀ)/D and du/dp = −(I − uuᵀ)/r;
- velocity columns: the map differentiated in b itself,
  du'/dv = [sI + b(∇_b s)ᵀ − u'(∂D/∂b)ᵀ]/(D·c), with
  ∇_b s = k·u + gamma³((b·u)·dk/dgamma + 1)·b and
  ∂D/∂b = gamma³(1+b·u)·b + gamma·u — the gamma³ pieces are what a
  slow-speed derivation would miss, so the test runs a 0.3c leg.
- A lucky break of our unit choices: rad/au columns and rad/(km/s)
  columns come out comparable in size at parsec ranges, so plain
  Gauss-Newton needs no column scaling (measured: converges in
  5 rounds noiseless, 10 rounds worst-case in the anchor batch —
  genuine convergence, not cap truncation: raising the cap to 30
  changes nothing, byte-identical medians).

**The step control the verification fleet forced (and the design panel
had ruled out).** The judge's design said "no LM damping — measured
unnecessary." A 200-seed stress ensemble then falsified that: on ~1 in
10⁴ anchor trials (spacecraft very close AND very fast — e.g. 0.18 ly
at 0.496c), the raw Gauss-Newton step overshoots the velocity past the
SPEED OF LIGHT, where the Lorentz factor does not exist, and the solve
turns NaN; two of 200 seeds failed the anchor test that way. Forensics
on the worst trial showed the deeper cause: the first step (10⁴ au
against an 11,557-au range) already leaves the linear model's validity,
and position then runs away geometrically. The fix is the plan's own
"GN with LM damping" core in minimal form — per-trial step HALVING
until the residual does not increase (8 halvings max, then the step is
rejected outright: the solver never moves uphill; a NaN residual counts
as "worse"), plus a light-cone guard that pulls any at-or-beyond-c
candidate back to 0.99c so every state stays evaluable. Measured after
the fix: both failing seeds converge (the pinned worst trial: 6 rounds
to 1.85 au / 1.95 km/s — noise-limited); the committed-seed anchor
medians are unchanged to all displayed digits; away from the rounding
floor a descending full step is taken untouched. The once-failing
trial is now a permanent regression test with its exact inputs frozen.

**Why the epoch is NOT a seventh unknown.** Bailer-Jones solves 7
parameters because HIS setup cannot assume the measurement time is
known. With our static catalog (no proper motions until Spec 10) the
epoch's sensitivity column is identically zero — a 7-state solve would
be singular. His own control experiment (Sec. 4.1) shows fixing the
time leaves position/velocity accuracy unchanged. Disclosed here, in
the test docstring, and in the anchor comparison.

## What the new code does NOT do

- No radial-velocity measurement channel: his headline is angles-only
  (his Figs. 9/13; 10 km/s RVs improve position by only 10%).
- No proper motions, no light-travel-time iteration (with static stars
  it collapses to nothing — becomes real at Spec 10), no catalog-error
  coupling into the 6-state (Spec 7's covariance stays orthogonal
  until a card marries them), no pulsars, no LM damping, no E7 grid,
  no lost-in-space starts (E2's question — the 10% start box is
  Bailer-Jones's own assumption, mirrored).

## Every tolerance touched, and why (measured this session)

- **SR_ABER_PHI_RAD** (new golden FUNCTION, override #4): the outside
  answer the code must match. Why it exists: a Galilean implementation
  on BOTH sides of the wall cancels its own error and passes recovery
  AND the anchor (measured: it lands inside the factor-2 gate!) —
  only an external oracle catches it. At the tested configs the
  Galilean miss is 102.9 arcsec (90°) and −473.9 arcsec (150°) against
  a gate of 2×10⁻⁷ arcsec (ANGLE_TOL_RAD, reused).
- **SOLVER_RECOVERY_TOL_KMS = 1e-8, SOLVER_STEP_TOL_KMS = 1e-9** (new
  goldens): velocity twins of the au gates. Measured noiseless floors
  here: 7.1e-10 au and 3.3e-10 km/s from all 64 corners of the 10%
  start box — 14x and 30x inside.
- **BAILER_JONES_ANCHOR + vel_err_kms = 2.0, n_runs = 100** (new keys):
  straight from the paper. The gate is TWO-SIDED at tol_factor 2.0 —
  landing 10x better would mean we solved an easier problem, not
  reproduced his. (Note for the students, recorded in the golden file:
  plan §7 says "anchor within 30%"; the frozen dict says factor 2.0;
  your ruling is pending. Today's 3.019 au vs 3.0 au would pass BOTH.)
- **JACOBIAN_REL_TOL reused**; position FD decades sit one notch below
  Spec 4's (0.01–10 au) because this network's nearest hub star is
  ~0.3 pc from the craft and the h² truncation of central differences
  was MEASURED at 1.37e-6 at h = 100 au (pure step-size error, scaling
  exactly as h²) — the tolerance is untouched, the probe step is test
  setup. Worst measured: position 1.8e-7, velocity 5.5e-7 (400 km/s
  leg), 4.4e-8 / 6.9e-8 (0.3c leg).

## The five tests, and the bug each one kills

1. **Aberration vs the golden oracle** — kills: no gamma (Galilean,
   the both-sides cancellation trap), wrong k coefficient (invisible
   at 90°, 474 arcsec at 150° — hence the oblique probe), aberrating
   the pair angle instead of each direction (exact when the reference
   is dead ahead — hence config B), sign-flipped velocity (the strict
   toward-apex inequality).
2. **State Jacobian vs finite differences** (two speed legs) — kills:
   reusing the static position block (144% wrong at 0.3c), dropped
   gamma³ terms, wrong 1/r, wrong star moved.
3. **Noiseless recovery from all 64 corners of the 10% box** — kills:
   anything that breaks the inversion; cross-checks the two
   independent aberration implementations; the iteration cap catches
   a solver limping on a wrong Jacobian.
4. **Batched equals single** (v = 0, 0.2c, 0.4c in one batch) — kills:
   trial-axis broadcasting bugs in the batched gamma/k scalars.
5. **The anchor** — the science gate, protocol-faithful, two-sided.

## Where this sits

The fusion leg of the project is now SECURE: the instrument solves the
same problem the published state of the art solves, to the published
accuracy, with the published protocol. E1's "we beat him 7x" footnote
is resolved the honest way — matched problem, matched answer. Next per
plan: Spec 10 (catalog aging propagator) opens E6, the headline; the
E1 figure can now also carry its velocity-state companion when the
students choose.

## Process note (recorded honestly)

Card text, tests, and code AI-drafted on standing student instruction
(2026-07-15): protocol extracted from the paper's full text by a
dedicated agent, three isolated designers + a judge converged on this
design, and a seven-angle verification fleet plus both project audits
ran before commit — verdicts in the logbook. Golden additions went in
under authorized override #4. Student ratification pending, checklist
in the logbook.
