# Spec 8b — The closest-lattice-point (CVP) solver

Written 2026-07-16. AI-authored under the build-night ratification-pending
pattern — students read and own every line before ratifying (worksheet item ff).

## Where this sits in the project

Spec 8 has two halves. The FIRST half (E5-lite,
`journal/spec-e5-pulsar-lattice.md`) built the pulsar phase combs and the
ambiguity LATTICE, and computed its packing radius `rho` — the largest position
uncertainty for which the correct integer turn-count is still unambiguous. That
half proved a NEGATIVE result: a ~1 au starlight fix is 4+ orders of magnitude
too coarse to lock any comb.

This SECOND half builds the other side of the same coin: the solver that, when
the prior IS small enough (inside `rho`), actually recovers the injected integer
turn-counts. It is one new function, `closest_lattice_point`, in
`galnav/pulsar.py`. Together the two halves complete Spec 8: E5-lite says "here
is the window in which the integers are recoverable," and this card says "here is
the code that recovers them, and it recovers them exactly whenever you are inside
that window." The solver is the seed a potential future E5-FULL trade surface
would sweep (how large a prior can be while still recovering the comb), so it is
built now, minimally, against its own acceptance test.

Like the rest of `galnav/pulsar.py` it is PUBLIC physics: it imports only numpy
and `galnav.units` (transitively), touches neither the truth simulator nor the
navigator, and so carries nothing across the truth wall.

## The problem, and the formula one symbol at a time

A phase-comb measurement pins the spacecraft's position along each sightline
only up to a whole number of pulsar turns. With three pulsars the unknown is an
integer vector `m` (one turn-count per pulsar), and the position ambiguities are
the lattice points `B m`, where `B` is the 3×3 generator E5-lite built. Given a
measured position offset `t` (km), the turn-counts most consistent with it are
the ones whose lattice point sits nearest to `t`:

    m_hat = argmin over m in Z^3 of || B m - t ||          [km]

This is the CLOSEST-LATTICE-POINT problem (also called integer least squares).
The code solves it in two steps.

**Step 1 — Babai rounding (the first guess).** If we ignored the "must be whole
numbers" rule, the turn-counts landing exactly on `t` would be

    B^{-1} t          (generally NOT whole numbers)

Rounding each coordinate to its nearest whole number is Babai's nearest-lattice-
point estimate [Babai86]:

    m0 = round( B^{-1} t )

- `B^{-1}` = the inverse of the generator: it converts a position (km) back into
  turn-count coordinates.
- `round(...)` = nearest whole number, coordinate by coordinate (`np.rint`).
- `m0` = Babai's integer guess. For a square lattice (orthogonal sightlines)
  this guess is already exactly right. For a SKEWED lattice it can be off by one
  in a coordinate, because rounding each axis independently ignores the tilt.

**Step 2 — exact refinement over the 27-point box (fix the off-by-one).** We
check every whole-number nudge of Babai's guess by −1, 0, or +1 on each of the
three axes:

    delta in {-1, 0, +1}^3      → 3 × 3 × 3 = 27 candidates (delta = 0 included)

For each candidate `m0 + delta` we measure `|| B (m0 + delta) - t ||` and keep
the smallest:

    m_hat = m0 + argmin over delta of || B (m0 + delta) - t ||

Because `delta = 0` is one of the 27, the answer is never WORSE than Babai's
guess; the box can only improve it. The whole thing is vectorized — `n` targets
of shape `(n, 1, 3)` broadcast against the 27 candidates of shape `(1, 27, 3)`,
giving `(n, 27, 3)`; there is no Python loop over targets.

**Why the answer is EXACT inside the packing radius (the guarantee the tests
rest on).** Suppose the true offset is small: `||t - B m_true|| < rho`, where
`rho = lambda_1 / 2` is the packing radius (`lambda_1` = the shortest nonzero
lattice vector). Take ANY other lattice point `B m'`. By the triangle
inequality,

    || t - B m' ||  >=  || B m' - B m_true ||  -  || t - B m_true ||
                    >=  lambda_1  -  ||offset||
                    >   lambda_1  -  rho   =   rho   >   ||offset||   =   || t - B m_true ||.

So `B m_true` is strictly closer to `t` than every other lattice point — it is
the UNIQUE closest point. An exact closest-point search therefore MUST return
`m_true`. Inside `rho` the recovered integer is not merely close; it is provably
the injected one. This is exactly the criterion Compass §6 states
("recovers injected integers when prior < packing radius = ½·λ₁"), and it is why
test T2 can assert integer equality with ZERO tolerance.

## What the code does — and does NOT do

DOES: solve the 3-D closest-lattice-point problem by Babai rounding plus an exact
27-point `{-1,0,+1}³` refinement, fully vectorized over any number of targets;
accept a single `(3,)` offset or a batch `(n,3)` and return integer turn-counts
of the matching shape; and raise `ValueError` on a non-`(3,3)` generator, exactly
as `ambiguity_lattice_generator` does.

Does NOT: this carries the SAME well-conditioned-sightlines caveat as
`shortest_vector_km`. The `±1` box is verified sufficient only for the project's
spread-out §12 geometries, where Babai's guess lands within one step of the truth
(MEASURED: exactly one L∞ step off on the real T5b lattice, zero on the
orthonormal one — so the 27-box is genuinely load-bearing on the real geometry,
and is exactly wide enough). It is NOT a general high-dimensional CVP solver and
does NO lattice (LLL) reduction; a near-degenerate geometry could push the true
integer more than one step outside Babai's box and defeat it — that remains the
deferred `fpylll`/LLL follow-up card (the same fork E5-lite named). It also does
not DECIDE whether the prior is inside `rho`: past `rho` a neighboring lattice
point is genuinely closer and the returned integer flips (T3). That flip is the
navigation ambiguity itself, not a solver bug.

## Tolerances touched — and why (there are none)

**Zero new tolerances. Zero golden-number changes.** `tests/golden_numbers.py`
is untouched — no addition, no edit (unlike E5-lite, which added override #8).
Every oracle this card asserts against is one of:

- **Integer-exact (`np.array_equal`, zero tolerance).** T1 and T2 assert that the
  recovered turn-counts equal the injected ones bit-for-bit. Integers are exact
  in floating point, and the whole claim ("recovers the injected integers") is an
  equality, so no wiggle room is possible or wanted. A tolerance here would be
  meaningless.
- **Golden-free, derived from the lattice itself.** `rho = packing_radius_km(B)`
  and `lambda_1` (found by the same bounded `[-2,2]³` enumeration
  `shortest_vector_km` uses) are computed inline from `B`; the frozen `COMB_KM`
  is only READ, to build the same real lattice E5-lite's T5b uses. The T3
  boundary is a strict `<` comparison of two distances, which is the finding
  itself, not a precision gate.

This is the honest reason no golden value was needed: an integer-recovery claim
is verified by integer equality, and the one physical scale in the problem
(`rho`) is already computed by frozen code from Spec 8's first half.

## Every test and what it would catch

`tests/test_spec8_cvp.py`, four tests, SEED = 20260716:

- **T1 `test_recovers_injected_integers_on_lattice`** — for 200 random integer
  turn-counts on BOTH lattices (orthonormal and real T5b), a point exactly ON the
  lattice returns its integers bit-for-bit, and a single `(3,)` offset returns a
  `(3,)` integer array. Catches any error in the `B^{-1}` rounding, the 27-box
  search, the integer cast, or the single-vs-batch shape contract — a wrong
  formula lands on a neighboring integer and fails the exact-equality gate.
- **T2 `test_card_criterion_recovers_within_packing_radius`** — THE CARD
  CRITERION. 2000 random integers × 2000 random unit directions × 4 offset sizes
  (`frac ∈ {0.5, 0.9, 0.99, 0.999}` of `rho`) on the real T5b lattice: every one
  of the 8000 injected integers is recovered exactly. This is the exhaustive,
  zero-tolerance proof of "recovers injected integers when prior < packing
  radius." It would catch a solver that dropped the 27-box refinement (Babai
  alone lands one step off on this skewed lattice, so it would miss the
  worst-rounding cases) or that mis-scaled `rho`.
- **T3 `test_boundary_beyond_packing_radius_is_the_ambiguity`** — boundary
  honesty. Push the true point `1.5·rho = 0.75·lambda_1` straight along the
  shortest lattice vector `v1`; the neighbor `B(m_true + m_v1)` is then only
  `0.25·lambda_1` away — strictly closer than the injected point at
  `0.75·lambda_1`. A correct solver must NOT return `m_true`, and its answer must
  be strictly closer to `t` than `m_true` is. This documents that `rho` is the
  PHYSICAL boundary: beyond it the injected integer is no longer the closest
  point — the ambiguity, not a defect. It would catch a solver that blindly
  echoed its Babai seed or never searched neighbors (it would wrongly cling to
  `m_true`). MEASURED here: `lambda_1 = 571.96 km`, `rho = 285.98 km`;
  `m_true` sits at `428.97 km` from `t` while the solver's point sits at
  `142.99 km` (= `0.25·lambda_1`).
- **T4 `test_non_3x3_generator_raises`** — a non-`(3,3)` generator (a 2×2 and a
  non-square 3×2) raises `ValueError`, matching `ambiguity_lattice_generator`'s
  style, rather than silently computing a wrong inverse. Catches a missing shape
  guard.

## What comes next

The deferred follow-up is unchanged from E5-lite: the GENERAL closest-vector
integer solver for possibly near-degenerate geometries (LLL reduction, optionally
via `fpylll`) — the `fpylll`-vs-numpy-enumeration ruling the students must make.
The USER RULING 2026-07-16 already settled it for THIS card (hand-coded numpy is
exact at dimension 3 and `fpylll` has no native-Windows build), and the 27-box is
proven sufficient for the project's geometries; a bigger search or an LLL
pre-reduction is only needed if a future card introduces sightlines that are
nearly coplanar. With the solver in hand, a potential E5-FULL experiment could
map the recovery success rate as the prior grows through and past `rho`, turning
the single packing-radius number into a trade surface.
