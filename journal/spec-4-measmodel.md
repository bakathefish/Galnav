# Journal Entry 4 — The Navigator's Crystal Ball (and the Star That Fought Back)

## The big idea

The navigator can't see truth. All it can do is GUESS a position and ask:
"IF I were standing there, what angle WOULD the camera show between star A
and star B?" Then it compares those predictions to what the camera really
measured. Wrong guess → predictions disagree with measurements. The next
spec will use those disagreements to fix the guess. Today's card builds
the prediction machine and — the crucial part — the SENSITIVITY TABLE:
how much each predicted angle changes if the guess slides 1 au along x,
y, or z. Math people call that table the Jacobian.

## Every function, tiny part by tiny part

All of this lives in `galnav/nav/measmodel.py` — navigator territory. It
imports numpy and nothing else. It cannot see the truth side at all.

**`_unit_directions(star_pos_au, obs_pos_au)`** — "which way is each star?"
1. `towards = star positions - my position`: one arrow from me to each
   star. (Subtraction order matters: star minus me = pointing AT the star.)
2. `ranges = length of each arrow` (Pythagoras, done by numpy's norm).
3. Divide each arrow by its length → arrows of length exactly 1 that only
   carry direction. Returns both the unit arrows and the distances.

**`_pair_sin_cos(unit, pairs)`** — "for each pair of stars, the sine and
cosine of the angle between them," computed the robust way:
1. Pick out the two unit arrows of each pair, u_i and u_j.
2. `cos = u_i · u_j` (dot product — Spec 1's trick).
3. `sin = length of (u_i x u_j)` (CROSS product — new). The cross product
   of two arrows is a third arrow whose length equals sin(angle).
4. Why both? See "the star that fought back" below. Short version: cosine
   alone goes numerically blind for tiny angles; sine alone goes blind
   near 90 degrees... but the PAIR of them, fed to arctan2, is sharp
   everywhere.

**`predicted_pair_angles(star_pos_au, obs_pos_au, pairs)`** — the crystal
ball itself:
1. Get unit arrows from my guessed position.
2. Get each pair's sin and cos.
3. `angle = arctan2(sin, cos)` — like arccos, an "undo" button for
   trigonometry, but taking two ingredients instead of one, which keeps
   full precision at every angle from 0 to 180 degrees.

**`pair_angle_jacobian(star_pos_au, obs_pos_au, pairs)`** — the
sensitivity table. The formula, derived by chain rule (each step is
school calculus, reproducible on paper):

    angle = arccos(u_i . u_j)                      -- start from Spec 1's identity
    d(angle)/dp = -(1/sin) * d(u_i . u_j)/dp       -- derivative of arccos
    du/dp = (u u^T - I)/r                          -- how a unit arrow tilts
                                                      when the viewer moves
    put together:
    d(angle)/dp = -[ (cos*u_i - u_j)/r_i + (cos*u_j - u_i)/r_j ] / sin

Symbol by symbol: **p** = my guessed position (3 numbers, au). **u_i,
u_j** = unit arrows to the two stars. **r_i, r_j** = distances to them
(au). **cos, sin** = of the pair angle. The result is 3 numbers per pair:
radians of angle change per au of guess change, along x, y, z.

Two sanity properties you can feel: each star's term is divided by ITS
distance — near stars make angles twitchy, far stars barely matter (the
displacement rule from Spec 2, resurfacing). And if you push the guess
directly toward a star, that star's arrow doesn't tilt at all — the
formula automatically gives zero for that direction.

## The star that fought back (what failed, and why it's a good story)

First run: 2 of 3 tests FAILED. The test had mechanically paired up the
ten nearest stars, including pair [8, 9] — which turned out to be the two
members of **61 Cygni**, a famous binary system. Two stars of one system
sit in nearly the SAME direction (0.0165 degrees apart from our vantage
point). And here's the poetry: 61 Cygni is the star Bessel used in 1838
for the FIRST parallax measurement in history — the founding star of the
very technique this project navigates by, photobombing our test.

Is this a novel discovery? **No — and honesty matters here.** Astronomers
have known 61 Cygni is a binary for two centuries, and "close pairs are
numerically degenerate" is textbook. What it IS: a genuine engineering
finding — proof our test harness catches real-data traps — and a preview
of the binary-contamination theme in our headline catalog-aging
experiment. It also forced a real code improvement:

- **Failure 1 (prediction check):** our old arccos recipe (Spec 1) has
  rounding fuzz that BALLOONS for near-zero angles — for the binary pair,
  reference and model disagreed by 1.18e-12 rad, just over the 1e-12
  gate. The fuzz was in the REFERENCE, not the model. Fix: the model now
  uses arctan2(sin, cos), precise at all angles (the upgrade our Spec 2
  journal predicted we'd someday need — today was the day).
- **Failure 2 (sensitivity check):** a close pair's angle barely changes
  when the ship moves — its position signal is proportionally tiny. Tiny
  signal under fixed rounding noise = the numerical nudge check cannot
  certify one-part-in-a-million for that pair at small nudges. Like
  weighing a feather on a bathroom scale: the scale isn't broken, the
  feather is just below its resolution.
- **The decision (students', recorded):** never pair binary companions
  WITH EACH OTHER in this test — verified [8,9] is the only degenerate
  pair of all 45 combinations; both stars still appear, paired with
  distant partners. Real navigation does the same: close pairs carry no
  signal and get excluded.
- **The methodological lesson:** our catalog is sorted by distance, and
  binary companions sit at the SAME distance — so adjacent rows are
  LIKELY to be the same system. Mechanical "pair up neighbors in the
  list" walks straight into binaries. Worth remembering in every later
  experiment script.

## Every tolerance, and why

- **ANGLE_TOL_RAD = 1e-12** (prediction test): two code paths compute the
  same geometry; only rounding dust may separate them. Passes with the
  well-separated pairs; the binary pair showed the REFERENCE tool's dust
  exceeds this for near-zero angles (documented above, excluded by
  student decision).
- **JACOBIAN_REL_TOL = 1e-6** (new this card, from the project plan):
  nudge-testing has two error sources — too big a nudge feels the
  curvature of the angle function, too small drowns in rounding. Measured
  after the fix: worst disagreement over all 7 pairs and all 4 decades is
  6.8e-8 (at the 100 au nudge, curvature-dominated) — 15x headroom there,
  1,000-10,000x at the smaller nudges. A wrong formula (sign flip,
  missing term, wrong 1/distance) misses by factors of thousands to
  millions.
- **The physics-bound test needs no tolerance** — it checks an
  inequality: no pair's sensitivity may exceed 1/r_i + 1/r_j, the
  displacement rule's hard ceiling.

## Which tests prove it, and what each would catch

1. **Prediction vs independent construction** (7 pairs, real stars):
   indexing errors, sign errors, normalization slips.
2. **Analytic vs numerical Jacobian, 4 decades of nudge** (0.1 to 100
   au): ANY error in the derived formula. Passing at one nudge size can
   be luck; passing across four decades means the formula is right —
   truncation and rounding errors move OPPOSITE ways with nudge size, so
   no single wrong formula can dodge both ends.
3. **Displacement-rule ceiling**: a formula with the right shape but
   wrong scale (e.g., forgot to divide by distance) dies here.

## What this does NOT do

- No noise, no weights, no attitude: pair angles don't care which way the
  camera points (that's WHY Bailer-Jones navigation uses pair angles).
  Attitude enters only with pinhole-pixel measurements, a later card.
- It doesn't solve for position — it only predicts and differentiates.
  The solver (Spec 5) is next, and it is mostly plumbing around today's
  two functions.

## Where this fits

Spec 5 (Gauss-Newton solver) iterates: predict → compare to measurements
→ use the Jacobian to compute the fix-up step → repeat. Spec 6 reuses the
SAME Jacobian for error bars. The CRLB — the theoretical best-possible
accuracy that experiment E1 maps — is built from this exact matrix. This
card is the mathematical heart of the whole project.
