# Journal Entry Spec 7 — The Map's Own Error Bars (catalog covariance in W)

## The idea in one breath

Until this card the navigator trusted the star chart completely: the only
thing that could be wrong was the camera. But every catalog distance comes
from a measured parallax with an error bar — the map itself is fuzzy. A
star slightly out of place on the map is indistinguishable, through that
star, from the SPACECRAFT being slightly out of place. Spec 7 teaches the
error-bar machinery that fact.

## The formula, one symbol at a time (derivation D7)

**Step 1 — a parallax error is a distance error.** A star's distance is
d = 1/π (parallax π). Wiggle π by its error σ_π and the distance wiggles
by the SAME fraction: σ_d = (σ_π/π) × d. The star's catalog position
s = d·û (û = the unit arrow from the Sun to the star) slides RADIALLY,
along û. (Gaia's ra/dec errors slide it sideways too — but about a
million times less than this, at this gate. See "does NOT do.")

**Step 2 — what the spacecraft sees.** From the spacecraft at p, the
star's apparent direction is u = (s − p)/r with r the range. Slide the
star radially by σ_d and only the part of that slide CROSSWISE to the
spacecraft's line of sight shows up. That crosswise fraction is
sin(α) = |û − u(u·û)| — the length of û's "rejection" from u — where α is
the angle at the star between its directions to the Sun and to the
spacecraft.

**Step 3 — the imposter principle.** A crosswise star-shift of size
σ_d·sin(α) changes the apparent direction by exactly the same angle as a
spacecraft displacement of that same size (the Spec 2 displacement rule,
run backwards). So one star's catalog fuzz is worth an equivalent
position error — the per-star floor:

    floor = σ_d · sin(α) = (σ_π/π) · d · sin(α)

**Step 4 — the star's own distance cancels.** By the sine rule in the
Sun–star–spacecraft triangle, sin(α) = (D/r)·sin(β), where D is the
SPACECRAFT's distance from the Sun and β the angle at the Sun between the
spacecraft and the star. For a far star, r ≈ d, so:

    floor ≈ (σ_π/π) · D · sin(β)   →   (σ_π/π) · D   at β = 90°

The d in σ_d and the 1/d in the visible fraction kill each other. A far
star's bigger misplacement is exactly compensated by how little of it you
can see. That is the frozen golden formula PER_STAR_FLOOR_AU — and note
carefully: **D is the spacecraft's distance, not the star's.** (The frozen
docstring says "D_pc: distance to the star" — misleading wording; flagged
for the students to fix under their own authority. Passing the star's
distance is 20× wrong at the tested geometry, and test 1 catches it.)

**How good is the approximation?** The far-star error is the D²/2d² term:
measured 1.25×10⁻³ for stars near 20 pc seen from 1 pc — 80× inside the
10% gate. (Proxima at 1.3 pc would be 21% off and FAIL — which is why the
test uses the eight most DISTANT stars, on purpose.)

**Step 5 — many pairs, one error: the dense matrix.** The pair angle
θ = arccos(u_i·u_j) responds to star i's distance by (chain rule, same
recipe as Spec 4's position Jacobian, just moving the star instead of the
observer):

    ∂θ/∂d_i = [cosθ·(û_i·u_i) − û_i·u_j] / (r_i · sinθ)

Collect these into G (one row per pair, one column per star; each row has
just two nonzero entries). The pair-angle error budget from the catalog is

    R_cat = G · diag(σ_d²) · G^T

and R_cat is DENSE: two pairs that share a star carry the SAME distance
error, so their errors are perfectly correlated (both are multiples of one
number — a rank-1 error). Measured: |correlation| = 1.000000000000000.
A diagonal shortcut (variances only) misstates the predicted per-axis
error by up to 1.91× in the standard 7-pair geometry — test 3 makes that
shortcut impossible.

**Step 6 — the covariance with the catalog in it.** The total measurement
error budget is R = σ²I + R_cat (camera plus map), and the predicted
position covariance becomes the weighted form of derivation D4:

    Cov = (J^T R⁻¹ J)⁻¹

With a PERFECT camera (σ = 0) this no longer vanishes — the catalog floor
stands. Measured at D = 1 pc with the 10 nearest stars and 7 pairs:
floor scale 11.1 au with a perfect camera, versus 2.75 au of camera-only
error at 1 arcsec. **At 1 pc, the map is already the binding constraint —
the first quantitative glimpse of the catalog-limited regime E6 maps.**
Typical single-star floors at D = 1 pc: 13–74 au (median 21 au) for the
20 nearest stars.

## What the new code does — and does NOT do

DOES:
- `galnav/nav/catalog.py::load_catalog` — the navigator's OWN copy of the
  public chart: positions AND σ_d per star. This closes the truth-wall
  flag recorded 2026-07-15: nav no longer needs truth's star arrays for
  anything new. (Both sides read the same public CSV — that is catalog
  DATA, like a paper star atlas, not truth state.)
- `pair_angle_dist_jacobian`, `catalog_angle_covariance`,
  `per_star_floor_au` in `galnav/nav/measmodel.py` — the three formulas
  above, vectorized, machine-precision safe (the floor uses the rejection
  VECTOR's norm, never √(1−dot²), which loses ~9 digits exactly where the
  floor vanishes).
- `position_covariance(..., sigma_dist_au=None)` — one optional argument;
  omitted, the Spec 6 behavior is verbatim-identical (its tests run
  untouched and green).

Does NOT:
- NOT weight the solver. `solve_position` is untouched — the recorded
  derivation-level choice of this card: the Spec 7 gate never exercises
  the solve, the floor exists regardless of solver weights, and the
  weighted covariance IS the observability limit the experiments need.
  Revisit trigger: if E6's Monte-Carlo-vs-prediction tracking breaks the
  1.5× factor, the solver gets weights (and the unweighted solver's
  scatter follows the "sandwich" formula, not this CRLB — a known trap
  recorded here so nobody falls into it).
- NOT catalog aging — no proper motions, no epochs, no time argument
  (Spec 10's job).
- NOT ra/dec error terms or the Gaia correlation coefficients — parallax
  error dominates them by ~10⁶ at this gate; they wait for the card that
  needs them.
- NOT truth-side perturbation. Truth still equals the catalog exactly;
  drawing a "true" sky from the catalog covariance is E6/Spec 10
  territory. No Monte Carlo here either — the gate is a first-order
  propagation statement, proven the Spec 4 way (independent hand formula
  + finite differences), not a statistics claim.

## Every tolerance touched, and why that exact value

- **CATALOG_FLOOR_REL_TOL = 0.10 (NEW golden, authorized override).** The
  plan's own number (§6, Spec 7). Honest because: measured true deviation
  of code from hand formula at the tested geometry is 1.25×10⁻³ (the
  far-star term) — 80× inside — while wrong physics misses by 20×
  (star's distance for D) or 100% (no transverse projection). Also reused
  for the correlation check in test 3, where the measured deviation from
  1 is ~10⁻¹⁵ and a diagonal shortcut is off by the full gate width.
- **JACOBIAN_REL_TOL = 1e-6 (reused).** Same semantics as its Spec 4
  birth: hand-derived sensitivity vs 4-decade central differences.
  Measured worst here: 6.55×10⁻⁸ — 15× inside.
- **SOLVER_RECOVERY_TOL_AU = 1e-8 au (reused).** Same semantics: an
  au-valued quantity that must vanish to machine precision. Measured:
  dead-ahead floor 3.7×10⁻¹³ au, worst at-home floor 5.7×10⁻¹¹ au —
  ≥170× inside.

## The four tests, and what each would catch

1. **Floor vs hand formula (8 most distant stars, β = 90°, D = 1 pc).**
   The plan's gate. Catches: star-distance-for-D (20× off), missing
   projection (20× off here), any wrong power of D or d. The oracle reads
   parallax columns straight from the CSV — an independent route sharing
   no vector math with the code.
2. **Distance Jacobian vs finite differences (4 decades).** Catches: sign
   errors (star out vs observer in), wrong 1/r, wrong star moved.
3. **Covariance enters W.** Catches: catalog term dropped (perfect camera
   would predict zero error), camera noise subtracting instead of adding
   (Loewner monotonicity), and the diagonal-W shortcut (correlation of
   pairs sharing a star must be exactly 1; diagonal gives 0).
4. **Floor vanishes dead ahead and at home.** Catches: the √(1−dot²)
   precision trap (~10⁻⁴ au of fake floor), any formula that charges
   parallax penalty where no parallax exists — and demonstrates WHY the
   floor scales with D.

## Where this sits, and what comes next

Spec 7 is the bridge between "the instrument is perfect-map ideal" (Specs
1–6, E1) and "how fast does a real, aging map rot?" (Spec 10 + E6, the
headline). The numbers above already whisper the answer: at 1 pc the
catalog charges ~4× more error than a 1-arcsec camera. Next per plan:
the E1 figure's catalog-limited plateau annotation now has its formula;
Spec 8 (pulsar comb) and the students' velocity+aberration card (Aug-15
anchor gate) follow.

## Process note (recorded honestly)

This card's test and design were AI-drafted on explicit student
instruction (2026-07-15), via a three-lens isolated design panel plus an
independent hand derivation, with the students' review and ratification
pending — full record and ratification checklist in journal/logbook.md.
The golden number went in under the standing authorized-override
procedure, lock lifted and restored the same minute.
