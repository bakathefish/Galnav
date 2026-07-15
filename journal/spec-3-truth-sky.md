# Journal Entry 3 — Building the Pretend Sky (the Truth Simulator)

## Why a pretend sky at all

You can't test spaceship navigation with a real spaceship. So we build a
pretend universe where WE secretly know where everything is — every star,
and the spaceship itself. Then we hand the navigator only what a real
camera would see, and check whether it figures out the spaceship's
position. Because we know the true answer, we can grade its homework
exactly. The pretend universe is called the TRUTH side, and it lives in
`galnav/truth/` — behind a wall the navigator can never see through.

## What got built (three small files)

**1. `galnav/units.py` — the unit-conversion office.** Project rule: all
conversions between "sky units" and our internal units happen in this one
file, nowhere else. Two conversions opened for business today:

- Sky coordinates to a 3D arrow. Astronomers describe a star's direction
  with two angles: RA (how far around, like longitude) and Dec (how far
  up/down, like latitude). The formula, one symbol at a time:

      x = cos(dec) * cos(ra)
      y = cos(dec) * sin(ra)
      z = sin(dec)

  This is the standard recipe for turning "two angles on a globe" into an
  arrow of length exactly 1 — the same sphere-to-xyz trigonometry from any
  math textbook. z is how high above the equator plane (sin(dec)); the
  cos(dec) shrinks the flat part of the arrow the way circles of latitude
  shrink toward the poles; cos(ra)/sin(ra) point around that circle.

- Parallax to distance:

      distance in parsecs = 1000 / (parallax in milliarcseconds)
      distance in au = that * (648000 / pi)

  The 1000 is just milli-to-whole (Gaia reports thousandths of an
  arcsecond). The 648000/pi IS the parsec definition from Spec 2 —
  derived in code from pi, never typed in as a decimal, so it cannot be
  mistyped.

**2. `galnav/truth/sky.py` — the star placer.** Reads our cached catalog
of 1,941 real nearby stars and computes each star's true 3D position:
arrow-of-length-1 times distance. Ten lines.

**3. `galnav/truth/observer.py` — the pretend camera.** Given the true
star positions, the spaceship's true position, and a list of star pairs:
for each pair it computes the exact angle the camera would see (same
dot-product-then-arccos math as Spec 1, but for many pairs at once), then
adds camera blur: `measured = true + sigma * random_wiggle`. The random
wiggle comes ONLY from an `rng` handed in by the caller — the project's
determinism rule, so every experiment can be replayed exactly.

## What this does NOT do (yet)

- The truth sky currently equals the catalog exactly. In reality the
  catalog is slightly wrong about every star (measurement errors), and a
  future card will make the TRUE sky a random draw around the catalog
  values using each star's full error information (we already downloaded
  the ten correlation numbers per star for exactly this). Until then:
  perfect catalog, imperfect camera.
- No proper motion, no time. Stars stand still — catalog aging comes in
  a much later card (it's the headline experiment, done properly).
- The navigator half of the universe is still empty stubs. Nothing here
  helps it cheat: truth code writes no files and shares no variables.

## Every tolerance used, and why

- **ANGLE_TOL_RAD = 1e-12** (zero-noise test): with the camera blur set
  to zero the simulator and the hand-built check compute the same
  geometry through different code paths; only rounding dust may separate
  them. (2026-07-15 re-measurement: generic pairs agree to ~1e-16..1e-13,
  but at the suite's closest pair — 61 Cygni A/B, ~60 arcsec — arccos
  amplifies rounding to ~4e-13 measured, ~8e-13 versus a 50-digit
  reference, leaving only ~2.6x margin under this gate. The old
  "~3.6e-14" figure came from a stress test that understates true error.
  Whether to keep gating that pair is an OPEN STUDENT DECISION — see
  logbook 2026-07-15.)
- **SKYCOORD_AGREE_MAS = 1.0** (astropy cross-check, new this card): our
  conversion and astropy's compute the same textbook trigonometry, so
  disagreement beyond rounding dust means one of us is wrong. 1 mas —
  the project plan's week-2 gate — is about 5e-9 radians: generous
  against dust (~1e-16 per component), fatal to any real formula error
  (a wrong sign or swapped axis is off by ~1, two hundred million times
  the ceiling).
- **The comparison trick worth reading twice:** we compare the two unit
  arrows by the LENGTH OF THEIR DIFFERENCE, not by Spec 1's angle tool.
  Reason (discovered in Spec 2): arccos gets fuzzy near zero angle —
  about 3 mas of fake fuzz for genuinely identical arrows — which would
  spuriously fail a 1 mas gate. The difference-length has no such
  weakness: for tiny angles it IS the angle, precise down to rounding
  dust. Same lesson as Spec 2, now used in anger.
- **The determinism test needs no tolerance** — same seed must give
  byte-for-byte identical results, and does.

## Which tests prove it, and what each would catch

1. **Zero-noise vs analytic** (5 pairs among the 10 nearest real stars,
   spaceship parked ~1.8 pc out): catches indexing mistakes (wrong star
   in a pair), sign errors (star minus ship vs ship minus star), and any
   geometry slip — with zero noise there is nowhere to hide.
2. **Astropy cross-check** (50 real stars): catches formula errors in
   the RA/Dec recipe — swapped sin/cos, degrees-vs-radians mixups, axis
   order — by comparing against software maintained by professional
   astronomers for two decades.
3. **Seed reproducibility**: catches hidden global randomness. If someone
   sneaks a `np.random.seed()` or an un-passed generator into the code,
   same-seed runs stop being identical and this test fails.

## Where this fits, and what's next

Bricks 1–2 were tools; this is the first piece of the actual instrument —
the world we'll run every experiment inside. Next (Spec 4): the
navigator's side of the mirror — "IF I were at position X, what angles
WOULD I see?" plus how sensitive those predicted angles are to being
wrong about X. That sensitivity (the Jacobian) is what lets Spec 5 solve
the real puzzle: measured angles in, spacecraft position out.
