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

## The web shell (so it actually shows up)

The tkinter window (`gui/app.py`) opens a desktop window — which never appears
in a headless or remote session, so the user could not see it. `gui/webapp.py`
adds a second front door that opens in a **browser** instead: `python -m
gui.webapp` starts a localhost server (Python's stdlib `http.server`, first free
port from 8000), prints the URL, and opens it. It reuses the SAME physics as the
tkinter app — nothing is reimplemented. The five stages, `n_star_solve`, the
catalog aging, the identify/age code are all the existing `gui/*` functions.

What it adds and how it stays honest:

- **Zero new dependencies.** Backend is pure stdlib (`http.server`, `json`,
  `io`, `re`, `socket`, `threading`, `webbrowser`); the star-field PNGs use
  matplotlib (already a dependency); uploads are parsed by a small hand-rolled
  multipart reader because Python 3.13 removed the `cgi` module. The frontend is
  three static files (`gui/web/index.html`, `style.css`, `app.js`) served from
  localhost — plain `fetch()` to the app's own API, no framework.
- **Thin HTTP layer.** The request handler only routes and serialises; every bit
  of work lives in plain functions — `frames_payload`, `render_frame_png`,
  `locate_payload`, `age_payload`, `handle_upload`, `static_file` — so the tests
  (`tests_gui/test_webapp.py`) exercise the real code paths WITHOUT a socket.
- **Truth wall preserved.** `webapp.py` imports only `gui.*` and (transitively)
  `galnav.nav.*` / `galnav.units`, never `galnav.truth`; the existing AST scan in
  `tests_gui/test_wall.py` already covers it. The `/static/` route serves a
  two-file allowlist and rejects any name with a separator or `..`, so the
  browser cannot read arbitrary files.
- **The single-age model.** The web UI applies ONE catalog age to all selected
  frames (the tkinter app and `nh_demo` age each frame to its own epoch). Over
  the two demo nights (2020-04-22/23) the frames' true ages differ by <0.003 yr,
  so this changes nothing measurable: the 12-frame fix is 0.38659 au (vs the
  per-frame 0.387) and the 2-frame teaching case is 0.983 au (vs 0.976). Both
  numbers are frozen as measured test constants.
- **Verified in a real browser.** Driven with Playwright: the full-solve preset →
  Locate returns 0.387 au / 12 lines / ellipsoid 0.441·0.233·0.206, and Estimate
  age draws the chi2-vs-age curve with the 4.29-yr minimum marked; dark and light
  themes both render cleanly (tokens mirror docs/PIPELINE-FLOWCHART.html).

### Labelling every star, and the honest limit of "we know what it is"

A later request: label EVERY star in the preview, not just the navigable ones,
so a viewer sees what the tool knows. The render now distinguishes three tiers:

- **detected** — every centroid, a cyan circle (what the camera saw);
- **identified** — a centroid that cross-matches the catalog by SKY POSITION
  (a tight ~2-pixel match), labelled with its distance ("81 pc");
- **position-capable** — a nearby star whose parallax shift can fix position;
  the big amber cross + name + distance ("Proxima Cen (1.3 pc)").

Two matches feed this, and the split is itself the lesson. The tight
identification match projects each catalog star's BARYCENTRIC direction and
matches within ~2 pixels; the navigation match uses the generous 120-arcsec
radius that swallows parallax. Nearby stars are displaced tens of arcsec by
parallax (that displacement IS the navigation signal), so the tight match
deliberately catches the DISTANT stars, and the position-capable nearby ones
come from the 120-arcsec match. Caption: "N detected - M identified - K
position-capable".

**The honest number, and a correction to the framing.** The request imagined the
tool would "know what nearly every dot is". It does not — and cannot, with the
catalogue it has. The widest catalog is <=100 pc; a narrow LORRI frame near the
galactic plane holds ~100 detected blobs, of which only ~2 are within 100 pc
(measured: the Proxima frame reads "100 detected - 2 identified - 1
position-capable"; the second identified star sits at 80.8 pc, labelled but not
navigable). The other ~98 blobs are faint kpc-distant field stars in no nearby
catalog. Labelling nearly every dot would need a full-depth Gaia field catalog
(hundreds of millions of stars), not a nearby-star subset. So the feature is
built to be truthful: it labels what it CAN identify, shows the distance, and the
caption's M << N makes the real point — almost everything in the sky is too far
to navigate by; only the amber stars move with viewpoint.

**Catalog split (byte-reproducibility preserved).** The demo navigation
(`/api/locate`, `/api/estimate_age` on the 12 baked frames) is pinned to the
FROZEN 20-pc file, so 0.387 au / 4.286 yr stay bit-identical even when the wider
100-pc catalog is present (a test asserts this). Only the identification labels,
and the navigation path for UPLOADED frames, use the widest catalog. The
wide-catalog loader degrades gracefully — if the 100-pc file is absent, or
mid-write and unparseable (it is fetched by a separate process), it marks that
file state bad and falls back to the 20-pc file, under a lock so concurrent
requests do not each re-parse the ~36 MB CSV. Thumbnails render nav-only
(`thumb=1`) to stay fast; only the big preview pays the wide-catalog load.

**Two cosmetic fixes after a real-browser review (no physics touched).**

1. *Opaque sticky topbar.* The bar was `background: color-mix(in srgb, var(--bg)
   88%, transparent)` with an 8px blur, so scrolled hero content ghosted through
   it. Fixed to `background: var(--bg)` — fully opaque in BOTH themes, because
   `--bg` is a solid hex in each `:root` (`#eef2f7` light, `#0a0e16` dark). The
   blur is dropped (pointless under an opaque fill).

2. *chi2-curve bowl clip.* The age-scan curve drew a sharp sawtooth on the left.
   It is NOT noise and NOT non-finite points (the default 0–10 yr grid has no
   unmatchable ages): it is real chi2 jumping DISCONTINUOUSLY where the matched
   star SET changes, because the fix then sums a different number of terms. Drawn
   as one polyline that is misleading — those segments are not a continuation of
   the same chi-squared. The drawn curve (`drawCurve` in `app.js`) now shows only
   the contiguous run around the minimum where chi2 stays within `30x` the
   minimum (absolute floor `30`, so a near-zero minimum still shows a few points;
   falls back to the full set if no clear bowl exists). This is DISPLAY-ONLY —
   every value stays in the returned `chi2s` array (the self-test confirms 41/41
   finite chi2s are still returned), so the saved arrays remain fully
   regenerable. Measured on the 12-frame default scan: the minimum is at 4.25 yr
   (chi2 7.13), the parabola vertex 4.286 yr; the clip draws ages 4.00–5.00 (five
   points spanning the vertex) and drops the two match-set cliffs at 2.00→2.25
   (21267→4954) and 3.75→4.00 (5117→33.8) plus the uninformative 12k–21k ramps.
   The `30x` window is a readability heuristic on an unchanged array, not a
   science threshold; it earns its number by cleanly separating the ~7–500 bowl
   from the ~5000–21000 clutter on the actual data.

**Wiring the offline solver's config (conditionally).** The offline-solver setup
script writes `~/.galnav-astrometry.cfg`, which lists BOTH the apt Tycho-2 wide
indexes and our narrow 5200 LITE indexes so one `solve-field` call handles wide
AND narrow fields. `wsl_solve` now passes `--config ~/.galnav-astrometry.cfg`,
but ONLY when that file exists in WSL — probed once per process with a LOGIN
shell (`wsl bash -lc 'test -f ~/.galnav-astrometry.cfg && echo ok'`, so `~`
expands). Why conditional: an unconditional `--config` would break a pre-existing
stock astrometry.net install that has no such file (solve-field errors on a
missing config), so with no cfg we simply omit the flag and let solve-field use
its default. Two tests pin it: cfg-present → the flag is in the argv; cfg-absent
→ it is omitted (both stub the WSL probes, so they need no real WSL).

**Deep identify — labelling (nearly) every dot, honestly.** The earlier honest
limit ("100 detected, 2 identified") was a CATALOGUE-DEPTH limit, not a physics
one: the nearby catalogs only hold stars close enough to navigate by. To label
the rest, `gui/gaiacone.py` fetches the FULL-DEPTH Gaia DR3 stars inside each
frame's footprint (ESA Gaia TAP async, stdlib urllib, `TOP 5000` brightest,
radius = half-diagonal + 10%) and caches one CSV per footprint on disk. Two hard
separations keep it safe:

- *Identification vs navigation.* The cone feeds ONLY the identification tier (a
  tight ~2-pixel positional match: "which catalogued star is this dot?"). The
  position-capable / navigation tier is untouched — still the nearby catalog and
  the 120″ parallax match. A far star gets a label, never a vote in the fix; the
  frozen 0.387 au / 4.286 yr numbers are entirely unaffected.
- *Fetch vs render.* Rendering NEVER hits the network: `cone_catalog(...,
  allow_fetch=False)` returns a cached cone or None, so a preview cannot block.
  The prewarm script (`gui/prewarm_demo_cones.py`) does the one-time fetching; a
  cache hit is zero network. A miss or an offline TAP silently degrades to the
  nearby-catalog labels — never an error to the browser.

*Honest labels.* A known name wins; else a DISTANCE ("212 pc") but only when the
parallax is trustworthy (`parallax_over_error ≥ 5` and `parallax > 0`), since
faint far stars carry junk (often negative) parallaxes; else the Gaia G
MAGNITUDE ("G 16.8"). So we never fabricate a distance we cannot measure.

*Measured result (12 demo frames, cache active).* The footprint key collapses the
12 frames to 4 cones (2 Proxima at the 5000 cap near the galactic plane; 2 Wolf
at ~530 stars, high latitude). Caption counts jump from the 100-pc file's
"2 identified" to: **Proxima 100 detected → 100 identified, 1 position-capable**
(every dot now named), **Wolf 359 38 detected → 28 identified, 1
position-capable** (its sparse high-latitude cone holds only 531 stars, so ten
faint/artefact blobs stay unmatched). Dim labels are still capped at the 25
brightest for readability; the caption reports the full counts. The rendered
Proxima preview shows the amber "Proxima Cen (1.3 pc)" plus muted distances on
the bright field stars and one honest "G 11.6" where the parallax was junk.

**"Where in space" — the 3-D view.** After any successful Locate the web app
shows an interactive 3-D scene built on the vendored **spacekit.js** (MIT,
bundles three.js). It is the scout's proven `poc.html` ported close to as-is into
`gui/web/where-in-space.html`, hosted in an `<iframe>` under the result card. Two
scenes behind a scale toggle: the solar system in au (Sun, planets + Pluto with
orbits, asteroid + Kuiper belts, heliopause shell, Eris, the five escaping
spacecraft at ~2025-26 positions, and an **amber marker at the recovered fix**),
and the solar neighbourhood in pc (the project's real 1,941-star Gaia 20-pc cloud
built lazily on first toggle, the five nearest famous stars labelled, amber
sightlines to Proxima and Wolf 359, and a caption on why the whole solar system
collapses to one dot at interstellar scale).

- *The one frame subtlety.* `/api/locate` returns EQUATORIAL ICRS au; spacekit
  renders in the ECLIPTIC frame. The view rotates the fix about +X by the mean
  obliquity 23.43928° (`x` unchanged, `(y,z)` rotated) — the same transform the
  baked star cloud uses. `|x|` is rotation-invariant, so the distance label
  ("47.4 au") is right in either frame.
- *Why an iframe, and lazy.* The iframe isolates spacekit's full-screen CSS and
  global from the app, and its `src` is set only on the FIRST successful Locate
  (with the fix passed as `?x=<x,y,z>`), so the ~2.9 MB payload (spacekit.js +
  the 2.36 MB skybox JPEG) never loads on the initial page. `app.js` reveals the
  panel on a good fix and hides it on a failed fix, an age result, or Clear.
- *Static serving + guard.* `gui/webapp.py`'s static route now serves the whole
  `gui/web/vendor/` subtree verbatim (Content-Type by extension) with a traversal
  guard: no `..`, no absolute path, and the resolved target must stay inside
  `gui/web/vendor/`. Three tests pin it (vendored asset serves with the right
  type; `..`/absolute/missing all rejected). `basePath` is set to
  `./vendor/spacekit`, so the scene contacts NO external host — fully offline.
- *Honesty.* The amber marker is the measured fix; the spacecraft/Eris markers
  are approximate 2025-26 positions (distance + published heading), labelled
  "~N au" and cited in `gui/web/vendor/spacekit/SOURCES.md`. The pc cloud is baked
  from the repo's own frozen 20-pc CSV by `vendor/spacekit/bake_gaia.py` (paths
  made repo-relative so it regenerates the JSON in place). Citations added to
  `journal/citations.md`: [Spacekit] (typpo/spacekit @ aa93d3f, MIT; three.js;
  ESO skybox; Yale BSC) and [WhereInSpace-data].
- *Proof.* A headless browser drive at the running server confirmed: the panel
  appears after the 12-frame Locate; the iframe `src` carries the real fix
  (`x=13.38,-42.37,-16.48`); the au scene renders a WebGL canvas with 19 labels
  (Sun, all planets, Pluto, Eris, Voyager 1, RECOVERED) and the "RECOVERED
  POSITION · 47.4 au" header; the NASA Eyes link shows for the demo set; toggling
  builds the pc scene (second canvas) with the five famous-star labels (Proxima
  1.30, Barnard's 1.83, Wolf 359 2.41, Lalande 2.55, Ross 154 2.98 pc) and the
  collapse caption. Screenshots of both scenes saved for review.

**Upload-first UI + raw-path proof + a PSF-centroid trial.** Three changes,
one round.

1. *Upload-first layout.* The page now leads with **Add your own image** (a raw
   telescope/spacecraft image, no coordinates needed) as the primary card at the
   top of the left column, with the one-line promise "Raw image in: no
   coordinates needed -- the pipeline plate-solves, identifies, and locates." The
   reproducible New Horizons demo (gallery + presets) moved BELOW it under
   "Reproducible demo -- real New Horizons frames (offline)". The demo is kept,
   not deleted: it is the byte-reproducible anchor and the offline booth path.
   Upload UX: while the blind solve runs the card shows a staged indicator
   (solving field / identifying / locating); on failure it surfaces the friendly
   three-backend message PROMINENTLY in the card (a red box), not just a toast --
   because that "solve-field not installed yet" error is the one users actually
   hit. Verified in a browser: the demo Full-solve still returns 0.387 au and the
   3-D panel still appears; an uploaded raw image with no solver shows the full
   fits-header/wsl/nova error with install hints.

2. *Raw-path end-to-end proof.* `gui/raw_demo.py` writes a WCS-stripped copy of a
   demo LORRI frame (a genuine "raw" image, pixels only) so the user has
   something to upload live. `tests_gui/test_raw_upload.py` drives the WHOLE raw
   chain on a stripped real frame (in tmp_path, nothing committed): (a) solver
   mocked ABSENT -> the friendly three-backend error; (b) solver mocked to return
   the frame's TRUE plate -> the upload identifies Proxima and, with one demo
   Wolf frame, reproduces the 2-frame teaching fix to <1e-5 au (the stripped
   pixels + mock-recovered plate are byte-identical to demo frame f0). This
   proves every line of the raw path except the solver binary itself.

3. *PSF-centroid accuracy trial (a measured null result).* `gui/centroids.py`
   gained an optional Gaussian-PSF refinement (`refine=True`): after the moment
   centroid, fit a 2-D circular Gaussian in a 7x7 stamp and take its centre when
   the fit is sane (edge / no-amplitude / SATURATION / non-convergence / >=1.5 px
   runaway all fall back to the moment centroid). The one honest lever toward
   Lauer's 0.351 au -- so it was MEASURED, not assumed. Result on the demo:

   | case | miss OFF (moment) | miss ON (PSF) |
   |---|---|---|
   | 12-frame (headline) | 0.38659 au | 0.40864 au |
   | 2-frame | 0.98301 au | 0.72284 au |
   | age_hat | 4.2856 yr | 4.3425 yr |

   The headline 12-frame miss got WORSE by 0.022 au (the decision rule required a
   >0.01 au improvement to adopt), even though the noisier 2-frame case improved
   by 0.26 au. Reading: averaging 12 moment centroids already beats a single
   frame; the Gaussian fit adds a small coherent bias (the LORRI PSF is not a
   perfect circular Gaussian) that the 12-frame average locks in rather than
   cancels. DECISION: keep the default OFF, keep the code behind the `refine`
   parameter, change no frozen constant. A null result is a result -- recorded
   here with its numbers. Unit tests pin the method regardless: a clean synthetic
   Gaussian is recovered to <0.05 px with refine=True, and a saturated flat-top
   star falls back to the moment centroid (identical to refine=False).

**Single-star drift dating -- the F12 chronometer made tangible.** The science
spine's F12 "catalog chronometer" shows that a star's Gaia proper motion lets you
recover WHEN an image was taken from how far the star has drifted. This makes it
something a student can do in the browser: date a real 1953 photographic plate.

The physics. A position FIX needs >= 2 nearby stars whose sight-lines cross. An
old sky-survey plate often shows just ONE fast-moving nearby star (a 1953 POSS-I
plate of Wolf 359). You can still date it: propagate the star's Gaia position to
the wrong epoch and it lands off the detected blob; propagate to the right epoch
and it lands on it. So `gui/age.py::drift_date` scans the age grid and, for each
nearby catalogued star, tracks its predicted-position -> nearest-centroid
separation (arcsec); the epoch is where that separation is minimised. Multiple
stars/frames sum squared separations (chi2-like); the minimum is parabola-refined.

- *Automatic mode switch.* `age_payload` tries the position-fit chi2 scan first
  and uses it whenever the fix ever runs (>= 2 distinct crossing lines, e.g. the
  New Horizons set -- unchanged, still 4.2856 yr). If the fix can NEVER run
  (a single nearby star), it falls back to `drift_date`. Two subtleties made this
  correct: (a) the age scan builds its lines from the sparse frozen 20-pc nearby
  catalog, not the dense widest catalog -- otherwise a deep plate spuriously
  matches two far stars within the radius and fakes a position fit; (b) the drift
  grid defaults to a wide -75..+25 yr (NEGATIVE ages -- epochs before 2016) so it
  reaches the plate era.
- *The sigma, honestly.* It is the parabola's delta-chi2 = 1 half-width after
  normalising the separation objective by the best-age RMS residual (so reduced
  chi2 == 1 at the minimum by construction). It is a RESIDUAL-CURVATURE,
  SINGLE-STAR sigma: it measures how sharply the separation rises around the
  minimum and ASSUMES the star is the correct match there. The real safety check
  is the reliability guard: if the best RMS separation over the whole scan is
  >= 3 arcsec, no star tracks a detection well enough -- "no reliable drift date".
- *Negative ages everywhere.* Propagation is linear in age and already handled
  negatives (a test pins it: the -50 yr state equals the epoch minus 50x the 1 yr
  velocity). The UI age input lost its `min=0`; the separation-vs-age curve plots
  negative x; and the result shows the calendar YEAR (2016.0 + age) headline --
  "1953.3" lands harder than "-62.7 yr".
- *Old-plate headers.* Digitised POSS/DSS headers sometimes carry a nonstandard
  time (decimal minutes "06:75" in a 1950 Barnard header) that astropy rejects;
  `gui/fitsmeta.py` now falls back to the DATE part alone, so the truth year still
  shows.

*Measured, real plate.* The 1953-04-15 POSS-I Wolf 359 plate (WCS in header)
runs through /api/estimate_age in single-star-drift mode and returns **age
-62.69 +/- 0.19 yr -> year 1953.3**, best separation **0.89 arcsec**, versus the
DATE-OBS truth 1953.29 -- reproducing the hand measurement (1953.4, 0.9 arcsec).
Verified in the browser (year headline, mode, and the negative-age separation
curve all render). Tests are synthetic-only (a one-star scene recovers an
injected -48.5 yr to <1 yr; the guard fires on a starless field; negative
propagation is linear; fitsmeta tolerates the decimal-minute date) -- nothing
depends on the git-ignored data/candidates/ plates.

## 2026-07-17 -- drift-dater dense-field fix, TESS TPF loading, epoch-span honesty

A candidate-hunter stress-tested the chronometer on six never-seen DSS plates.
Three dated true (Wolf'53 -> 1953.3, Proxima'76 -> 1976.0, Proxima'97 -> 1996.9),
Wolf'95 was sloppy (1991.4 vs 1995.2), and BOTH Barnard plates hit a *false
minimum* at +19.5 yr ("2035.5" instead of 1950/1991). Three fixes this round.

### 1. The dense-field false minimum -- static-star exclusion

*The failure, precisely.* Barnard's Star moves 10.4 arcsec/yr. Over the -75..+25
yr scan its track sweeps the whole 30-arcmin frame, and at +19.5 yr the predicted
position passes an *unrelated bright field star* at 1.70 arcsec -- closer than it
ever sits to its own true-epoch blob (2.15 arcsec). The single-star objective
(sum of squared nearest-centroid separations) has no way to tell a real match
from a coincidental one, so the false minimum wins and the 3-arcsec reliability
guard cannot catch it (the decoy is also sub-3 arcsec).

*The fix (my lead's idea, measured and adopted).* A centroid that lands on a
catalogued STATIC field star cannot be the fast mover we are dating -- at the
true epoch the mover sits where the catalog shows NOTHING (it has moved far from
its own 2016 Gaia spot). So `gui/locate.py:static_occupied_centroids` projects
every star of the frame's full-depth Gaia cone (already warmed on disk;
`cone_catalog(allow_fetch=False)`, zero network) through the WCS and marks each
centroid within ~2 px of one. `star_seps_in_frame` gained an
`exclude_centroid_mask` argument; `drift_date` builds the mask per frame and
hides those detections, so the mover can only match a blank-catalog detection.

  formula, one symbol at a time (the mask test for centroid j, cone star k):
    occupied_j  =  OR over unmasked cone stars k of  [ dist_px(centroid_j, proj_k) <= tol_px ]
  where proj_k is cone star k's CATALOG-epoch (J2016.0, "static") sky direction
  pushed through the plate WCS to a pixel, dist_px is Euclidean pixel distance,
  and tol_px = 2.0 (the identification tolerance already used elsewhere). A
  masked centroid is dropped from the mover's nearest-neighbour search.

*The near-age-0 exemption (thought through, documented).* The cone lists the
NEARBY movers too, at their 2016 positions. On a MODERN plate (age ~ 0) a mover
legitimately sits at its own catalog spot, so its own cone entry must not mask
the detection it belongs to. `drift_date` therefore drops the nearby-catalog
source ids from the mask whenever |age| < 1.0 yr (`age0_window_yr`); the fastest
movers are still within a couple of pixels of their catalog spot there. Away from
age 0 the mover has left that spot, so it is a legitimate static exclusion again.
The threshold is 1.0 yr because a 10 arcsec/yr mover at a ~1 arcsec/px plate has
moved ~10 px in a year -- unambiguously "not at its catalog spot" beyond that.

*Why this alone, no flux prior.* The brief authorised a second lever (require the
match among the brightest N) only if exclusion alone failed. It did not: measured
on all six real plates, exclusion fixes both Barnard plates and leaves the four
others exactly as they were, so the flux prior was not added (simplest thing that
works). Barnard diagnostic at +19.5: 155 of 200 centroids are catalogued static
stars; the decoy is one of them, so Barnard's separation there jumps 1.70 -> 172
arcsec, while its true-epoch blob (2.02 arcsec, where the catalog is blank)
survives masking and becomes the global minimum.

  Six-plate table, single-star drift, grid -75..+25 @0.5, cone exclusion:

  | plate (star)            | truth  | BEFORE (off) | AFTER (on) | verdict          |
  |-------------------------|--------|--------------|------------|------------------|
  | poss1red wolf359 1953   | 1953.3 | 1953.3       | 1953.3     | OK (unchanged)   |
  | poss2blue proxima 1976  | 1976.2 | 1976.0       | 1976.0     | OK (unchanged)   |
  | poss2red proxima 1997   | 1997.2 | 1996.9       | 1996.9     | OK (unchanged)   |
  | poss2red wolf359 1995   | 1995.2 | 1991.4       | 1991.4     | ~ no regression  |
  | poss1red barnard 1950   | 1950.5 | 2035.6 FALSE | **1950.6** | FIXED            |
  | poss2red barnard 1991   | 1991.5 | 2035.6 FALSE | **1991.5** | FIXED            |

  Wolf'95 is a *different* failure (a sparse high-latitude field where Wolf 359's
  slower 4.7 arcsec/yr track over a short 21-yr baseline gives a shallow V with a
  competing minimum 3.8 yr away); static exclusion neither helps nor hurts it, as
  the brief required. Left honest, not papered over.

  What it does NOT do: it does not add a new dependency, touch the position-fit
  (chi2-scan) path, or change any NH demo number -- the NH frames are position-fit
  and never reach `drift_date`; a single NH frame forced onto the drift path
  returns "no reliable drift date" both before and after (at 47 au the spacecraft
  sees Proxima's 36-arcsec PARALLAX, not its proper motion, so barycentric drift
  prediction misses by >3 arcsec -- Earth-based DSS plates have no such offset,
  which is exactly why drift dating is an old-plate technique).

### 2. TESS target-pixel files load their imagery, not the aperture mask

A SPOC/TESScut target-pixel file keeps its pictures in a binary TABLE (EXTNAME
`PIXELS`) as a `FLUX` column of one 2-D cutout per cadence; the only IMAGE HDU is
the `APERTURE` bit-mask (~all ones). The old "first 2-D HDU" loader skipped the
table (its `.data` is a 1-D record array) and grabbed the mask -- so a TESS frame
had nothing to centroid. `gui/app.py:_tpf_median_frame` now detects the PIXELS
table and returns the pixel-wise MEDIAN over cadences (NaN gap cadences ignored
via `nanmedian`), which is a clean single frame the pipeline centroids normally.
On the real Proxima Sector-11 cutout this recovers 8 detections (matching the
hunter's derived-frame count); a normal single-image FITS is untouched.

### 3. Multi-epoch honesty -- the position fix warns when it is meaningless

DSS/HST plates are Earth observations years apart: different observer, different
place, so their lines of position do not cross at one real point and the fix
returns a nonsense |r| (measured 22-35 au on mixed-era groups). `locate_payload`
now computes the span of the selected frames' observation epochs (max-min of
obs_age_yr) and, when it exceeds 0.2 yr, attaches a plain-English `warning`
steering the user to the AGE estimate (which is per-frame and unaffected). The
NH campaign is one instant, so it never trips; a Barnard'91 + Wolf'95 pair
produces |r| = 35 au WITH the warning, exactly as intended. The web result card
renders it as an amber banner.

### 4. Noted, not patched -- HLA WFPC2 SIP warning

The hunter's Hubble Legacy Archive WFPC2 drizzled products trip an astropy
warning ("SIP coefficients present but CTYPE missing -SIP suffix -- coordinates
might be incorrect"). `fits_header_solution` still returns a usable solution
(warns, does not fail); the WCS may be marginally off for these drizzled
products. Cosmetic and instrument-specific -- recorded here per the brief, no
code change (suppressing it in the core solver risks hiding real WCS problems).

*Tolerances touched.* `static_tol_px = 2.0` px: the identification tolerance
already used for tight positional matches; measured to mask the Barnard decoy
(and 155/200 dense-field centroids) while leaving the true-epoch blob unmasked.
`age0_window_yr = 1.0` yr: the |age| below which a mover's own catalog spot is
exempt; justified above. `_EPOCH_SPAN_WARN_YR = 0.2` yr: below the ~0.3-yr NH
campaign spread stays silent, above it flags the year-apart plate groups the
hunter measured at |r| 22-35 au.

*Tests (synthetic only -- nothing depends on the git-ignored plates).* A decoy
scene (one fast mover + a static decoy star placed where the mover's track
crosses at a false epoch, plus a one-star cone) is fooled onto the false epoch
without the cone and recovers the true -50 yr WITH it -- the Barnard fix in
miniature. A synthetic astropy-written TPF (PIXELS table + all-ones aperture, one
NaN gap cadence) proves `load_grayscale` returns the FLUX median (peak on the
injected star, not a flat mask) and that it centroids; a plain image FITS is
unaffected. The epoch-span warning fires on a spread-out pair and stays None on a
same-era pair and on the real 12 NH frames. tests_gui 64 -> 71; spine 84 held.
