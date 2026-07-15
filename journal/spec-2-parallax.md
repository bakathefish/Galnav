# Journal Entry 2 — Teaching the Computer About Parallax

## The big idea, with your thumb

Hold your thumb out at arm's length. Close one eye, then switch eyes. Your
thumb seems to jump sideways against the far wall. Now bring your thumb
closer to your face and do it again — it jumps MORE. That jump is called
parallax: when the viewer moves (your two eyes are two different viewing
spots), nearby things appear to shift more than faraway things.

A spaceship uses this exact trick in reverse. It can't feel itself moving
through empty space, but if a nearby star appears to shift against the
background, the ship KNOWS it moved — and by measuring how much the star
shifted, it can work out how far it moved. Nearby stars are the ship's
thumbs.

## The exact formula, one symbol at a time

    shift = arctan(D / d)

- **D** = how far the observer moved sideways, in au
  (1 au = the Earth-Sun distance — our ruler for this project).
- **d** = how far away the star is, also in au.
- **D / d** = just division: "my move, compared to the star's distance."
- **arctan** = the "undo tangent" button. Here's why it appears: the old
  viewing spot, the new viewing spot, and the star make a right triangle.
  The side opposite the shift-angle is D, the side next to it is d, and
  trigonometry says tan(shift) = D/d. To get the shift itself, press undo:
  shift = arctan(D/d). No approximation — this IS the exact answer for a
  sideways move.
- The answer comes out in **radians** (the math-native way to measure
  angles; multiply by 206,264.806 to get arcseconds, and that conversion
  number lives in our answer key, tests/golden_numbers.py).

Where the formula comes from: right-triangle trigonometry, the same
SOH-CAH-TOA from school. Citation [SMALL]/[DOT] class — textbook math, no
paper needed. The parsec definition it must reproduce is official:
IAU 2015 Resolution B2 [IAU15 in journal/citations.md].

## The magic checkpoint: why "1 parsec" exists at all

Astronomers invented a distance unit FROM this formula. One parsec
(PARallax-SECond) is DEFINED as: the distance where moving 1 au makes a
star shift by exactly 1 arcsecond (1/3600 of a degree). So our test asks:
star at 1 parsec, move 1 au — do we get exactly 1 arcsecond? If not, the
code is wrong. There's no wiggle-room debate possible: it's a definition,
like asking "is a meter 100 centimeters?"

## The shortcut rule (and why we test it)

For tiny angles, arctan(x) is almost exactly x itself. So:

    shift ≈ D / d      (the shortcut — no arctan needed)

This shortcut is what makes navigation math simple later. But "almost
exactly" needs proof, so the test slides the star from 1,000 au away to
1,000,000,000 au away — six jumps of 10x — and checks the shortcut agrees
with the exact formula everywhere. We test the extremes on purpose:
computer precision bugs hide at very small and very large numbers, not in
the comfortable middle.

## What this code does NOT do

- It does not know what a star or a catalog is. Numbers in, one number out.
- It only handles a PERPENDICULAR (sideways) move. Moving toward or away
  from the star, or diagonally, is a later spec's job.
- It does not add measurement noise. Real telescopes are blurry; faking
  that blur honestly is Spec 3 (the simulator).
- It remembers nothing between calls.

## Every tolerance used, and exactly why (measured, not guessed)

- **PARALLAX_REL_TOL = 1e-6** (one part in a million) for the parsec test.
  (Evidence corrected 2026-07-15, science audit.) The test uses the SAME
  rounded constant 206264.806 as both the distance and the rad→arcsec
  conversion, so the rounding cancels exactly; the true measured gap is
  the arctan Taylor term 1/(3·PC_AU²) = 7.8e-12, putting the tolerance
  ~130,000x above the floor. (The 1.2e-9 previously quoted here is
  PC_AU's rounding versus the exact 648000/π — a comparison the test
  never makes.) Any real formula mistake still blows past the gate by
  thousands of times.
- **DISPLACEMENT_REL_TOL = 1e-5** for the shortcut test. The shortcut
  itself is imperfect by (D/d)²/3 (the arctan series' first dropped
  term): at our closest test star, (1/1000)²/3 = 3.3e-7, measured. The
  tolerance sits 30x above the shortcut's own imperfection but far below
  any coding bug. (2026-07-15: an earlier wording here said "(D/d)^2",
  missing the 1/3 — the measured 3.3e-7 always matched the correct
  (D/d)²/3 law.)
- **ANGLE_TOL_RAD = 1e-12** for the cross-check test (below).

## The cross-check test, and an honest discovery about our own Spec 1 tool

Third test: build the whole scene as real 3D arrows — star straight ahead
at 10 au, slide 1 au sideways — and measure the shift with Spec 1's
angle_between instead. Two completely different roads must give the same
answer to a trillionth.

While designing this we found something worth writing down: Spec 1's
angle_between (which uses arccos) gets slightly fuzzy for VERY tiny angles
— at 1-arcsecond scale its rounding error (~5e-11 rad) is bigger than
ANGLE_TOL_RAD. Not a bug in what Spec 1 promised (its own tests all pass),
but a known limitation: for tiny-angle work in later specs there is a
better recipe (arctan2 of cross-product and dot-product), to be adopted
only when a spec card needs it. So the cross-check uses a deliberately
WIDE angle (about 5.7 degrees), where both methods are at full precision
and the comparison is fair.

## Which tests prove it, and what each would catch

1. **Parsec definition** — catches any wrong formula, wrong units, or
   flipped division (d/D instead of D/d gives ~324,000 arcsec — nearly a
   right angle instead of one arcsecond, off by 5.5 orders of magnitude
   — instantly caught; arithmetic corrected 2026-07-15).
2. **Six orders of magnitude** — catches precision loss at extreme
   distances and accidental use of a bad approximation. Also asserts the
   answer comes back as an array matching the input array (the project
   rule: vectorize, never loop).
3. **3D cross-check vs Spec 1** — catches a subtle wrong-geometry bug
   (e.g., measuring the wrong triangle side) that formula-only tests
   might miss, because it never uses the formula being tested.

## Where this fits, and what's next

This is brick #2. The navigator's whole job later is running this logic
backwards: "I measured these shifts, so where must I have moved to?"
Spec 3 builds the pretend sky (truth simulator) that generates realistic
noisy measurements; Spec 4 asks "how does the predicted angle change if my
position guess changes?"; Spec 5 solves for position. Every one of them
leans on this file and Spec 1's.
