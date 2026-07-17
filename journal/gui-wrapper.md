# Journal Entry — The Demo Tool: A Photo In, A Position Out

## The big goal

Everything else in this project is code the two of us run from a terminal.
This piece is different: it is a little window with buttons. You drag in a
picture of stars taken by a spacecraft, press a button, and it tells you where
the spacecraft was when it took the picture — a real position in space, with an
error bar — and, as a bonus, it can tell you how OLD the star catalog is by
looking at how far the stars have drifted.

It is a DEMO. It does not add any new science. It is a friendly front door onto
the navigator we already built and tested. Every hard sum it does is borrowed,
unchanged, from the spine.

## The five small jobs, in order

When you press "Locate spacecraft," the tool does five things:

1. **Plate-solve** each image — figure out which patch of sky each pixel looks
   at (the "WCS": world coordinate system, i.e. an RA/Dec for every pixel).
2. **Centroid** — find the bright dots (stars) and their exact pixel positions.
3. **Age the catalog** — move every catalog star forward in time to the age you
   set, because stars drift (this reuses the spine's Spec 10 aging).
4. **Identify** — match the catalog stars that fall inside the frame to the
   dots we found.
5. **Fix** — turn each matched star into a "line the spacecraft must lie on,"
   and intersect the lines to get the position.

Each job lives in its own small file (`gui/platesolve.py`, `gui/centroids.py`,
`gui/locate.py`, `gui/age.py`), so each can be tested on its own. The window
itself (`gui/app.py`) is just buttons wired to these files.

## What is a "line of position"? (the heart of it)

Hold a straw and look at a lamp through it. You do not know how far along the
straw the lamp is — but you DO know the lamp is somewhere on the line the straw
points along. A star is the same: from a photo we learn the DIRECTION to the
star, and from the catalog we know WHERE the star is. So the spacecraft must sit
on the line that starts at the star and runs back along that direction. One star
gives a line. Two stars give two lines, and two lines cross at a point — that
point is the spacecraft.

## The exact math, one symbol at a time

### The fix (reused from `galnav/nav/triangulate.py`, from [Lauer25])

Star number *i* sits at a known place we call **p_i** (a point in space, in au).
From the photo we measure the direction to it, a unit arrow **d_i** (length 1).
The spacecraft, at unknown place **x**, must lie on the line through **p_i**
pointing along **d_i**.

For each star we build a little "flattening" matrix

    q_i = I − d_i d_iᵀ

- **I** is the identity (the "do nothing" matrix).
- **d_i d_iᵀ** is the part of any arrow that points ALONG the star direction.
- So **q_i** keeps only the SIDEWAYS part — the part that measures how far off
  the line you are. If you are exactly on the line, q_i times your offset is 0.

We weight each star by how close it is:

    w_i = q_i / |p_i|²

- **|p_i|²** is the star's distance squared. Dividing by it means "trust nearby
  stars more" — a faraway star's sideways position is fuzzier, so it gets a
  smaller vote. (This inverse-square weight is exactly Lauer et al.'s choice.)

Then the best position is

    x = ( Σ_i w_i )⁻¹ ( Σ_i w_i p_i )

- **Σ_i** means "add up over all the stars."
- In words: stack up everyone's sideways constraints and solve for the single
  point **x** that sits closest to ALL the lines at once. This is one matrix
  solve — no guessing, no loop.

The same routine also hands back **chi2** = Σ_i (how far x is from line i)²,
weighted the same way. If the lines cross cleanly, chi2 is tiny.

We did NOT re-derive this. `gui/locate.py::fix_position` calls the spine's
`n_star_solve` and only adds the plain-English error checks (need ≥2 stars, need
2 DIFFERENT stars, lines must not be parallel).

### The error ellipsoid (reused scaling from E3's `reproduce_lauer`)

The solve returns a bare covariance **xcov = (Σ w_i)⁻¹**. To turn it into a real
1-sigma error bar in au we multiply by the angle error of one measurement:

    ellipsoid semi-axes = sqrt(eigenvalues(xcov)) × σ_θ

- **eigenvalues(xcov)** are the squared sizes of the error blob along its three
  natural axes.
- **σ_θ** is the per-photo pointing error, in radians. We use 0.44 arcsec (the
  New Horizons per-image value from Buie, via [Lauer25]) turned into radians by
  `galnav.units.arcsec_to_rad`.

### Why the match radius must be generous (parallax)

We predict where a catalog star should appear using its BARYCENTRIC direction
(the direction from the Solar System's centre). But the spacecraft sees the star
from off to the side, so it appears shifted. The shift is about

    Δθ ≈ r / d

- **r** is how far the spacecraft is from the barycentre (au).
- **d** is how far the star is (au).
- Example: r = 47 au, Proxima at d ≈ 268,000 au → Δθ ≈ 1.8×10⁻⁴ rad ≈ 36
  arcsec. Stellar aberration from the observer's ~14 km/s motion is another
  9.6 arcsec — but on the New Horizons pwcs2 frames that shift is already baked
  into the plate solution (the field stars used to solve the WCS are aberrated
  by the same amount), so on THESE frames the star sits ~parallax arcsec from the
  barycentric prediction, not parallax + 9.6. The default 120 arcsec match radius
  swallows that with room to spare; it is a knob in the window for spacecraft even
  farther out (bigger r means bigger Δθ), and the 9.6 arcsec is budgeted for
  foreign images whose WCS did NOT absorb it. On the real New Horizons frames the
  measured offsets were 32 arcsec (Proxima) and 16 arcsec (Wolf 359) — comfortably
  inside 120.

### Estimating the catalog age (the chi2 scan)

Nearby stars move fast across the sky: Proxima drifts ~3.85 arcsec per year,
Wolf 359 ~4.7 arcsec per year. Over a few years that is many LORRI pixels. So if
you tell the tool the WRONG catalog age, it puts each star in the wrong place,
the lines of position stop crossing cleanly, and **chi2 goes up**. Scan the age,
watch chi2, and the bottom of the U-shaped curve is the true age.

To turn the bottom of the curve into an age WITH an error bar, we fit a parabola
through the three scan points around the lowest one:

    age_hat  = g₁ + h · (y₀ − y₂) / (2·(y₀ − 2y₁ + y₂))
    chi2''   = (y₀ − 2y₁ + y₂) / h²
    sigma_age = sqrt( 2 / chi2'' )

- **y₀, y₁, y₂** are the chi2 values at three ages spaced **h** apart, with y₁
  the lowest.
- **age_hat** is the parabola's true bottom (between grid points).
- **chi2''** is the curve's steepness (its second derivative). A steep, narrow
  valley means a confident age.
- **sigma_age** is the "delta-chi2 = 1" rule: how far you move in age before the
  fit gets one unit worse. That is the standard 1-sigma error — but ONLY if chi2
  is a properly-scaled chi-squared.

**One subtlety we had to get right.** The spine's chi2 is weighted by 1/|p_i|²,
so with stars ~10⁵ au away its raw value is around 10⁻¹³ — a fine number for
finding the bottom of the valley, but not on the "delta = 1" scale. To make
sigma_age a real 1-sigma error we divide the whole chi2 curve by σ_θ² (the same
0.44 arcsec pointing error, squared, in radians) — because a pointing error
σ_θ makes a sideways position error of about |p_i|·σ_θ, so raw_chi2 / σ_θ² is
the proper normalized statistic. On the real New Horizons data this turns a
meaningless "±63000 yr" into an honest **±0.13 yr**. The best-age value itself
does not move at all (dividing by a constant cannot shift where the bottom is);
only the error bar becomes truthful.

## What this tool does NOT do (important)

- **It cannot invent a WCS out of nothing.** If an image has no WCS in its
  header, the tool needs a blind solver (local astrometry.net via WSL, or the
  nova web service). With neither installed it still works on any image that
  already carries a WCS — which every demo frame in this repo does.
- **It does not correct stellar aberration — and does not need to, here.** The
  spacecraft's own motion shifts every star by ~9.6 arcsec, but on these New
  Horizons frames that shift is already absorbed by the plate solution, so an
  explicit correction would change nothing (see the correction note below). The
  ~1 au (2 frames) / ~0.39 au (12 frames) miss is single-frame centroid noise,
  not aberration.
- **It never touches the truth side.** The window only ever sees the photo and
  the public catalog — exactly what a real spacecraft carries. It imports
  nothing from `galnav/truth`. A test (`tests_gui/test_wall.py`) proves this by
  reading the code.
- **It is not spine science.** It changes zero golden numbers and adds zero new
  libraries. If it broke tomorrow, every result in the paper would be untouched.
- **One image alone cannot give a point.** One star is one line; the tool says
  so in plain words and asks for a second, DIFFERENT nearby star.

## Every tolerance we chose, and why (with measured evidence)

These live as named constants at the top of each `tests_gui/test_*.py` (the
project's real tolerances in `tests/golden_numbers.py` are off-limits and
irrelevant here — this is demo code).

- **Centroid recovery < 0.3 px** (`test_centroids.py`). A clean Gaussian star
  centroids to far better than a pixel; we MEASURED 0.0014 px on the test
  scenes. 0.3 px is loose enough never to fail by chance, but an axis-swap or
  off-by-one bug misses by ≥1 px and is caught.
- **Exact-line fix < 1e-6 au** (`test_locate.py`). With perfect directions the
  lines pass exactly through the spacecraft, so the answer is limited only by
  computer rounding; we MEASURED ~1e-10 au. 1e-6 au still fails any real algebra
  mistake (those are off by whole au).
- **Full pixel-chain fix < (far-star distance × 2-pixel angle)** (`test_locate.py`).
  We do not hardcode a magic number; we compute the bound from the scene as
  `max_dist_au × arcsec_to_rad(2 × plate_scale)`. Measured miss 0.011 au against
  a ~15 au bound — the bound is the honest physical ceiling (centroiding error
  times lever arm), and the real chain sits far under it.
- **Age recovery < 0.5 yr, true age inside age_hat ± 3σ, convex minimum**
  (`test_age.py`). The scan step is 0.25 yr; the sub-grid parabola MEASURED
  0.001 yr accuracy. 0.5 yr fails if the minimum ever lands on the wrong grid
  node.
- **WCS round-trip: centre < 1e-6 deg, scale < 1e-3 arcsec/px**
  (`test_platesolve.py`). Astropy stores headers in float64, so a write-then-read
  agrees to ~1e-9; the gates are tight enough to catch a flipped CDELT sign.

## Every test, and what it would catch

- `test_centroids.py` — recovers injected pixel positions, brightest-first
  ordering, rejects a lone hot pixel (min_pixels), and returns nothing for a
  flat image (guards the divide-by-noise). Catches a broken detector or a
  swapped (x,y) axis.
- `test_platesolve.py` — a real FITS round-trips; a WCS-less FITS returns None;
  `solve_image` tries backends in order and aggregates every failure reason;
  `nova_solve` walks the full web protocol against a monkeypatched `urlopen`
  (no network). Catches a broken backend chain or a mis-parsed WCS.
- `test_locate.py` — identify finds the right star by source id and rejects
  both a too-far centroid and filler stars; two stars competing for one centroid
  resolve one-to-one with the closer winning; an exact-corner star stays
  in-frame; the fix recovers the true position both exactly and through the full
  pixel chain, its ellipsoid is sorted descending, and the three degenerate cases
  (one line, same-star lines, parallel lines) raise clear errors. Catches a wrong
  pixel convention, a broken uniqueness guard, or a silent bad fix.
- `test_age.py` — the full chain recovers a known (off-grid) injected age with a
  sane, magnitude-pinned error bar and a convex minimum, the sub-grid vertex
  beats the grid node, and a scan with unmatchable ages returns a finite age
  without crashing (falling back to a NaN sigma + note when the minimum's
  neighbour is unmatchable). Catches a broken age scan, a mis-normalized sigma,
  or the default-settings crash.
- `test_wall.py` — no `gui/` file imports `galnav.truth`, and `gui/` reaches
  into galnav only through the navigator surface. Catches a truth-wall breach
  the eye would miss.

## Proof on real data

`python -m gui.nh_demo` runs the whole thing on REAL New Horizons LORRI frames
(Proxima field taken 2020-04-22, Wolf 359 field 2020-04-23, already carrying
solved WCS) in two cases. Measured this session:

- **2 frames (teaching case):** position [12.694, −42.038, −16.926] au,
  |r| = 47.06 au, miss vs JPL = **0.976 au**, ellipsoid [1.08, 0.57, 0.504] au,
  age **4.336 ± 0.134 yr** vs true 4.309.
- **All 12 frames (headline):** position [13.386, −42.369, −16.486] au, miss vs
  JPL = **0.387 au** (matching Lauer's 0.351 au 12-line ×60 solve), ellipsoid
  [0.441, 0.233, 0.206] au — exactly √6 tighter than the 2-frame ellipsoid — and
  age **4.286 ± 0.055 yr**.
- **Sanity:** fixing the OBSERVER of two ground-based frames lands on Earth,
  |r| = 1.149 au — the tool finds whoever took the picture.

## Correction: what we first wrote about the miss, and why it was wrong

This repo records its corrections openly, so here is one. The first draft of this
journal (and the demo) blamed the ~1 au miss on **uncorrected stellar aberration**
(the ~9.6 arcsec shift from New Horizons' ~14 km/s motion), saying a correction
would pull the miss toward Lauer's 0.35 au. An adversarial re-check proved that
wrong on two counts:

1. **The residuals are pure parallax.** The measured target offsets (31.9 arcsec
   Proxima, 16.4 arcsec Wolf) match the *geometric parallax* angle to a few
   tenths of an arcsecond — not parallax ± 9.6 arcsec. The New Horizons pwcs2 WCS
   was fit to Gaia field stars, which carry the same velocity aberration, so the
   aberration is absorbed into the plate-solution zero-point and `measured_direction`
   already returns aberration-corrected directions.
2. **Injecting aberration breaks it.** Adding a synthetic ±9.6 arcsec aberration
   to the sightlines swings the miss to ~17 au. So if aberration were truly
   uncorrected, the miss would be ~17 au, not ~1 — the opposite of a small
   residual. An explicit correction would therefore NOT improve the fix.

The real driver is **single-frame centroid noise**: our quick 5-σ centroids are
cruder than Buie's careful multi-frame astrometry. That is why *averaging* frames
helps — 12 frames (6 per star) pull the miss from 0.976 au to 0.387 au and shrink
the ellipsoid by √6 (12 lines vs 2). The remaining ~0.39 au floor is per-frame
astrometric systematics, honestly of unproven exact origin, but NOT aberration.
The lesson: measure before attributing a cause.

## Where this sits, and what's next

This is a DEMO LAYER standing on top of the finished spine. It reuses the exact
navigator (`n_star_solve`), the exact aging (`propagate_positions_au`), and the
exact units module — so if the demo agrees with the science, it is because they
are the same code underneath. It is the thing to open at a poster session: a
photo goes in, a position and an age come out.

Next, if we want it sharper: average more frames per star (already the biggest
lever — 12 frames reach 0.387 au), improve the centroiding toward Buie-grade
astrometry to chip at the ~0.39 au systematics floor, and let the blind solvers
(WSL astrometry.net / nova) carry raw amateur images that have no WCS yet. An
aberration correction is NOT on this list — on the pwcs2 frames it is already
absorbed and would not move the miss. None of that changes the spine; it only
polishes the front door.
