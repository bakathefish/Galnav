# The GalNav GUI, explained — a photo in, a position out

This is the read-aloud walkthrough of the demo app. You drag in a picture of
stars taken by a spacecraft, press a button, and the tool tells you **where
the spacecraft was** when it took the picture — a real position in space, with
an error bar — and, as a bonus, **how old the star catalog is**, read from how
far the stars have drifted.

It is a **demo**. It adds no new science. Every hard sum it does is borrowed,
unchanged, from the finished GalNav spine: the same navigator
(`galnav.nav.triangulate.n_star_solve`), the same catalog aging
(`galnav.nav.catalog.propagate_positions_au`), and the same units module.
If the demo agrees with the science, it is because they are the same code
underneath.

**Two shells, one pipeline.** The primary demo is now a **local web app**,
`python -m gui.webapp` — it opens in your browser (so it works even on a
headless or remote machine, where a desktop window cannot), and the
`Start GalNav Demo.bat` launcher opens it for you. The older desktop window,
`python -m gui.app` (tkinter), remains as a fallback, and `python -m gui.nh_demo`
is a headless script that prints the numbers. All three are thin shells over the
**same five small files**, each testable on its own; the physics below is
identical whichever shell you open. The web app adds three things on top — a
four-tier star-label overlay (`overlay=none|detected|identified|nav`, so an
upload can be seen exactly as the camera saw it), a six-page **pipeline walk**
that shows every stage's real numbers and math, and a live hand-off to
**OpenSpace**, the NASA/AMNH planetarium, as the show viewer — plus one extra
reading of the same age math, the **chronometer**; all are described near the
end of this document.

Sources for this document: the code in `gui/*.py`, the GUI journal entry
`journal/gui-wrapper.md`, `gui/README.md`, and `gui/web/README.md`. The
two-frame and twelve-frame numbers quoted here were measured by driving the real
`gui/` pipeline — including the web app's own `locate_payload`/`age_payload` —
on the New Horizons data on 2026-07-17.

## The five small jobs, in order

When you press **Locate spacecraft**, the tool does five things:

1. **Plate-solve** each image — figure out which patch of sky each pixel looks
   at (the WCS: an RA/Dec for every pixel).
2. **Centroid** — find the bright dots (stars) and their exact pixel positions.
3. **Age the catalog** — move every catalog star forward in time to the age you
   set, because stars drift.
4. **Identify** — match the catalog stars that fall inside the frame to the
   dots we found.
5. **Fix** — turn each matched star into a line the spacecraft must lie on, and
   intersect the lines to get the position.

Each job lives in its own file: `gui/platesolve.py`, `gui/centroids.py`,
`gui/locate.py` (jobs 3-5), and `gui/age.py` (the age estimate).

---

## Stage 1 — Plate-solve (`gui/platesolve.py`)

**In:** an image file (FITS/PNG/JPG). **Out:** a `PlateSolution` — an astropy
WCS that maps every pixel to an RA/Dec, plus the image size and which backend
solved it.

The tool tries three backends **in order** (`solve_image`), and if all fail it
raises one error that explains each failure and how to enable it:

1. **`fits-header`** (`fits_header_solution`) — the image already carries a
   solved WCS in its header. Free, offline, instant. Every demo frame in
   `data/e3_new_horizons/repo/` (the `*_pwcs2.fits` LORRI frames) is like this.
   Nothing to install. The reader walks the HDU list and returns the first HDU
   whose data is 2-D and whose header has a celestial (RA/Dec) WCS, passing the
   full HDU list so SIP distortion tables in later HDUs resolve.
2. **`wsl`** (`wsl_solve`) — a *blind* solve via astrometry.net's `solve-field`
   inside WSL, for an image with no WCS. One-time setup (`wsl sudo apt install
   astrometry.net` plus index files sized to the field of view). The tool
   converts Windows paths to `/mnt/c/...` form automatically
   (`_win_to_wsl_path`).
3. **`nova`** (`nova_solve`) — a blind solve in the cloud via
   nova.astrometry.net. Needs a free API key (passed in the window or set as
   `ASTROMETRY_NET_API_KEY`) and network access. Uses only the Python standard
   library `urllib` — no new dependency.

The blind backends (2, 3) are **optional**. With neither installed the tool
still fully works on any image that already has a WCS — which every demo frame
in this repo does. All network and subprocess code is isolated in small,
monkeypatchable functions so the tests stay offline.

The `PlateSolution` also exposes two derived numbers the later stages need:
`center_radec_deg` (the sky coordinate of the centre pixel) and
`scale_arcsec_per_px` (the plate scale, mean of the two axis scales). On the
real LORRI frames the measured scale is 4.095 arcsec/pixel.

---

## Stage 2 — Centroid (`gui/centroids.py::find_centroids`)

**In:** the 2-D image array. **Out:** the sub-pixel (x, y) centres of the
bright compact sources, brightest first, plus each source's flux.

The detection is deliberately plain and robust:

- **Background** = `median(image)`.
- **Noise** = `1.4826 x MAD`, where MAD is the median absolute deviation. The
  factor 1.4826 makes the MAD a normal-consistent estimate of the standard
  deviation (it is not affected by a few bright stars the way a plain standard
  deviation would be).
- A pixel is **bright** if `image > background + threshold_sigma x noise`
  (default `threshold_sigma = 5`).
- Connected bright pixels are grouped (`scipy.ndimage.label`); groups smaller
  than `min_pixels` (default 3) are dropped as hot-pixel noise; each surviving
  group's centre is its **flux-weighted centroid** (`center_of_mass` on the
  background-subtracted image).

One careful detail: the returned `xy` uses `(x, y) = (column, row)`, matching
astropy's WCS pixel convention, so the centroids feed straight into the WCS
without an axis swap. A flat image (MAD and standard deviation both zero)
returns nothing rather than dividing by zero.

On the real Proxima frame this finds 100 centroids; on the Wolf 359 frame, 38.

---

## Stage 3 — Age the catalog (`gui/locate.py::load_aged_catalog`)

**In:** the public Gaia CSV, an age in years since the catalog epoch J2016.0,
and an optional radial-velocity fill for stars Gaia has no RV for. **Out:** the
catalog star positions **moved forward** to that age, with their aged sky
coordinates and distances.

This stage adds no physics of its own. It wraps the navigator:

```
load_catalog(csv)                 # galnav.nav.catalog: positions + sigma_d
star_velocities_kms(rv_fill)      # galnav.nav.catalog: 3-D velocities
propagate_positions_au(age_yr)    # galnav.nav.catalog: straight-line drift
```

Because stars move, "the catalog" is only true at one instant. Setting the age
propagates every star along its own velocity before matching and solving. The
aged RA/Dec/distance are recomputed **from the aged Cartesian positions** (with
`np.arctan2` and `np.arcsin`), so they reflect the propagated sky, not the
epoch sky. That is the whole "set the age" mode — there is no extra code for
it beyond this one call.

---

## Stage 4 — Identify (`gui/locate.py::identify_in_frame`)

**In:** the plate solution, the detected centroids, and the aged catalog
positions. **Out:** a list of matches, each pairing one catalog star to one
centroid, with the predicted-to-observed separation.

For each aged catalog star the tool takes its **barycentric direction** (the
unit vector of its aged position), projects it through the WCS to a predicted
pixel, keeps the stars that land inside the image, and matches each to the
nearest centroid within the match radius. The matching is one-to-one: the
closest (star, centroid) pair wins, then the next closest among what is left.

Two engineering details worth reading aloud:

- **A cheap angular gate first.** Projecting the whole sky through a
  SIP-distorted WCS makes the inverse solver diverge for far-off-field points.
  So the tool first keeps only the handful of stars within half a frame
  diagonal plus the match radius of the image centre (a dot-product test), and
  only inverts the WCS for those.
- **The measured direction comes back out of the WCS** (`measured_direction`):
  the centroid pixel maps through the WCS to an apparent sky position, and that
  apparent direction *is* the spacecraft-to-star line of sight — exactly what
  "apparent place" means. It is returned as a unit vector for the fix.

### Why the match radius must be generous — parallax

We predict where a star should appear from its **barycentric** direction (the
direction from the Solar System's centre). But the spacecraft sees the star
from off to the side, so it appears shifted. The dominant shift is parallax:

    Δθ ≈ r / d

- **r** is how far the spacecraft is from the barycentre (au).
- **d** is how far the star is (au).
- Example: r = 47 au, Proxima at d ≈ 268,000 au → Δθ ≈ 1.8×10⁻⁴ rad ≈ **36
  arcsec**; Wolf 359 (nearer than Proxima on the sky but farther in distance)
  works out to ~16 arcsec.

On the demo's New Horizons frames the measured match offsets are **31.88
arcsec** (Proxima) and **16.44 arcsec** (Wolf 359) — and these are essentially
**pure parallax**: they agree to about 0.05 arcsec with a parallax-only
prediction of 31.91 / 16.39 arcsec. Stellar aberration from the spacecraft's
own ~14 km/s motion (about **9.6 arcsec**) does *not* show up in these
residuals, because the frames carry Gaia-calibrated `pwcs2` plate solutions
whose WCS zero-point already **absorbs** the aberration.

The default **120 arcsec** match radius swallows all of this with room to
spare, and it is a knob in the window. Raise it for a spacecraft farther out
(bigger r means bigger parallax), or for a raw frame whose WCS does *not*
absorb aberration (then the ~9.6 arcsec matters too).

### A note on arctan2 vs arccos

Throughout GalNav, angles and directions are recovered with `arctan2`/`arcsin`
rather than `arccos`. The project learned early (Spec 2, recorded in the
logbook) that `arccos` carries a few milliarcseconds of false "fuzz" at very
small angles, while `arctan2(|cross|, dot)` stays precise everywhere. The GUI
follows the same convention: `load_aged_catalog` and the helper
`_unit_to_skycoord` both build sky coordinates with `np.arctan2`, so the demo's
geometry is as precise as the spine's.

---

## Stage 5 — Fix (`gui/locate.py::fix_position`)

**In:** two or more lines of position (from two or more *distinct* stars).
**Out:** the spacecraft position in au, a 1-sigma error ellipsoid, and the
fit's chi².

### What is a line of position? (the heart of it)

Hold a straw and look at a lamp through it. You do not know how far along the
straw the lamp is — but you **do** know the lamp is somewhere on the line the
straw points along. A star is the same: from a photo we learn the **direction**
to the star, and from the catalog we know **where** the star is. So the
spacecraft must sit on the line that starts at the star and runs back along
that direction. One star gives a line. Two stars give two lines, and two lines
cross at a point — that point is the spacecraft.

### The exact math, one symbol at a time

This is reused from `galnav/nav/triangulate.py::n_star_solve`, the same solver
E3 uses on the real spacecraft, following Lauer et al. (2025).

Star number *i* sits at a known place **p_i** (a point in space, in au). From
the photo we measure the direction to it, a unit arrow **d_i** (length 1). The
spacecraft, at unknown place **x**, must lie on the line through **p_i**
pointing along **d_i**. For each star we build a little flattening matrix

    q_i = I − d_i d_iᵀ

- **I** is the identity (the "do nothing" matrix).
- **d_i d_iᵀ** is the part of any arrow that points **along** the star
  direction.
- So **q_i** keeps only the **sideways** part — how far off the line you are.
  If you are exactly on the line, `q_i` times your offset is 0.

We weight each star by how close it is:

    w_i = q_i / |p_i|²

- **|p_i|²** is the star's distance squared. Dividing by it means "trust nearby
  stars more" — a faraway star's sideways position is fuzzier, so it gets a
  smaller vote. This inverse-square weight is exactly Lauer et al.'s choice.

Then the best position is one matrix solve — no guessing, no loop:

    x = ( Σ_i w_i )⁻¹ ( Σ_i w_i p_i )

The same routine hands back **chi2** = Σ_i (how far x is from line i)², weighted
the same way. If the lines cross cleanly, chi2 is tiny (on the real frames it is
~1.6×10⁻¹³ in raw units).

`fix_position` does **not** re-derive any of this. It calls `n_star_solve` and
adds only the plain-English guardrails: it needs at least two lines, at least
two **different** stars, and the lines must not be within ~5 arcmin of parallel
(checked via the smallest eigenvalue of the summed projector, floor 1e-6). Each
failure raises a sentence a student can read.

### The error ellipsoid

The solve returns a bare covariance `xcov = (Σ w_i)⁻¹`. To turn it into a real
1-sigma error bar in au we multiply by the angle error of one measurement:

    ellipsoid semi-axes = sqrt(eigenvalues(xcov)) × σ_θ

- **eigenvalues(xcov)** are the squared sizes of the error blob along its three
  natural axes.
- **σ_θ** is the per-photo pointing error, in radians. The demo uses **0.44
  arcsec** (the New Horizons per-image value from Buie, via Lauer 2025),
  converted by `galnav.units.arcsec_to_rad`. This is exactly E3's covariance
  scaling.

---

## Estimating the catalog age (`gui/age.py::estimate_age`)

Nearby stars move fast across the sky: Proxima drifts ~3.85 arcsec per year,
Wolf 359 ~4.7 arcsec per year. Over a few years that is many LORRI pixels. So
if you tell the tool the **wrong** catalog age, it puts each star in the wrong
place, the lines of position stop crossing cleanly, and **chi2 goes up**. Scan
the age, watch chi2, and the bottom of the U-shaped curve is the true age.

To turn the bottom of the curve into an age **with** an error bar, we fit a
parabola through the three scan points around the lowest one:

    age_hat   = g₁ + h · (y₀ − y₂) / (2·(y₀ − 2y₁ + y₂))
    chi2''    = (y₀ − 2y₁ + y₂) / h²
    sigma_age = sqrt( 2 / chi2'' )

- **y₀, y₁, y₂** are the chi2 values at three ages spaced **h** apart, with y₁
  the lowest.
- **age_hat** is the parabola's true bottom, between grid points.
- **chi2''** is the curve's steepness (its second derivative). A steep, narrow
  valley means a confident age.
- **sigma_age** is the "delta-chi2 = 1" rule: how far you move in age before the
  fit gets one unit worse. That is the standard 1-sigma error — but **only** if
  chi2 is a properly-scaled chi-squared.

**The one subtlety the code gets right.** `n_star_solve`'s chi2 is weighted by
1/|p_i|², so with stars ~10⁵ au away its raw value is around 10⁻¹³ — fine for
finding the bottom of the valley, but not on the "delta = 1" scale. To make
sigma_age a real 1-sigma error, `estimate_age` divides the whole chi2 curve by
σ_θ² (the same 0.44 arcsec pointing error, squared, in radians) — because a
pointing error σ_θ makes a sideways position error of about |p_i|·σ_θ, so
`raw_chi2 / σ_θ²` is the proper normalized statistic. On the real New Horizons
data this turns a meaningless error bar into an honest one — **±0.13 yr** from
the two teaching frames, and **±0.055 yr** over all twelve frames. The
best-age value itself does not move at all — dividing by a constant cannot shift
where the bottom is; only the error bar becomes truthful. If the minimum lands
at the edge of the grid or the curve is not convex there, sigma_age is returned
as NaN and you are told to inspect the raw curve.

---

## The star labels — detected, identified, position-capable (`gui/gaiacone.py`)

The web app draws every star it can, in **three tiers**, and captions the frame
`N detected - M identified - K position-capable`:

- **Detected** (cyan circle) — every bright blob `find_centroids` found. On a
  narrow LORRI frame near the galactic plane this is ~100 dots.
- **Identified** (distance label) — a detected blob that cross-matches the
  catalog by sky position, using a **tight ~2-pixel** match. These tend to be
  the *distant* stars, because a nearby star is displaced tens of arcsec by
  parallax and so misses the tight match.
- **Position-capable** (big amber cross + name + distance, e.g. `Proxima Cen
  (1.3 pc)`) — a star close enough that its parallax shift actually reveals the
  spacecraft's position. These come from the **generous 120-arcsec navigation
  match** that swallows parallax (Stage 4).

That two-match split is the pedagogy: the tight identification picks up the far
stars, the generous navigation match picks up the nearby position-capable ones.
The honest lesson a judge should hear is that on a real frame you typically see
something like `100 detected - 2 identified - 1 position-capable`: **almost
everything you can see is too far away to navigate by.** Labelling nearly every
dot would need a full-depth field catalog, not a nearby-star subset.

Two catalogs are used, on purpose. The 12 baked-in New Horizons frames fix and
age against the **frozen 20-pc catalog** (`data/gaia_dr3_nav_subset.csv`, 1,941
stars) so the blessed 0.387 au / 4.286 yr numbers stay byte-reproducible. The
**labels** — and the navigation path for **uploaded** frames — use the widest
catalog available (`data/gaia_dr3_nav_100pc.csv`, ~174,700 stars out to 100 pc)
if present, degrading gracefully to the 20-pc file if it is absent.

---

## The pipeline walk + OpenSpace — the live viewer

The pipeline is walkable **webpage by webpage**: six chained pages
(`/static/pipeline-1-raw.html` … `pipeline-6-fix.html`, linked by Next/Prev
carrying the selected frames, catalog age and match radius) show, in order:
the **raw** image with no marks at all ("this is everything a lost spacecraft
has"), **centroid detection** (the moment formula plus this frame's actual
centroid rows), **star identification** (the match table — name, Gaia
source_id, distance, separation, position-capable flag), the **measured
angles** (TAN deprojection to each star's unit direction vector), the **lines
of position** (observer = star − λ·direction, with the real anchors), and the
**fix** (the least-squares intersection, its error ellipsoid, and — on the
demo — the miss against JPL truth). One image with one nearby star ends,
honestly, at "a line, not a point", with an *add a second image* link that
re-runs the same walk with two frames — the one-image-then-two-images story.

The 3-D viewer is **OpenSpace** (openspaceproject.com), the open-source
planetarium NASA and AMNH fund. `gui/openspace_link.py` pushes each stage's
geometry into a *running* OpenSpace over its Server-module socket (TCP 4681,
newline-framed JSON; a mandatory `apiHandshake` first message, then a
`luascript` topic per push — the protocol facts were measured against a live
OpenSpace 0.22.0 and are documented, with numbers, in the module and its
tests). Stage pushes are idempotent (each script clears the previous
`GalNavLive*` nodes first); the fix stage lands the camera 6×10¹⁰ m from the
**amber recovered-fix sphere** with the **cyan JPL-truth sphere** 0.387 au
beside it and the white miss line between — the whole story in one view.
Nothing is computed in OpenSpace; it only displays what the pipeline
measured. Every push is **execution-confirmed**: the engine's reply frame
carries back a `return 1` sentinel after the chunk runs (measured on 0.22.0,
2026-07-21), so the note line says *confirmed* — or, honestly, *sent (no
execution confirmation)* or a failure pointing at the OpenSpace log. When
OpenSpace is not running, every button degrades to an honest "start
OpenSpace" message and the pages still show all the numbers. (An earlier,
self-contained in-page 3-D view was removed outright on 2026-07-21 —
OpenSpace is the only viewer.)

---

## The chronometer — reading the year off an old photograph (`gui/age.py::drift_date`)

The age scan above assumes at least two nearby stars (two lines that must cross).
The **chronometer** is the single-star version: give it one fast-moving nearby
star and it reads the **calendar year** the photo was taken, from drift alone. A
single star cannot fix a *position* (that needs two), but its motion across the
sky is a clock, and the chronometer reads it.

The catalog is a J2016.0 snapshot, so a photograph from decades earlier has a
**negative** catalog age — the stars must be run *backwards*. That needs no
special code: the propagator is `r(t) = r0 + v·t` with a signed `t`, so a
negative age just slides each star the other way. The scan sweeps a wide grid of
candidate years; the year whose back-propagated star best lands on the detected
dot is the plate epoch, and the curvature of the match gives a ± error bar. A
built-in reliability guard refuses to answer when no catalogued star drifts
clearly onto a detection, so it fails honestly rather than inventing a date.

On real sky-survey plates the result is striking: a genuine **1953 Palomar
Observatory Sky Survey (POSS-I) plate of Wolf 359 is dated to 1953.3**. Across a
set of real Palomar and UK-Schmidt survey plates spanning **1950–1997**, the
chronometer dates all six real survey plates (1950–1997) to within about a year.
The one genuine trap — in a dense galactic-plane field an unrelated background
star can masquerade as the drifted target — is **defused by the catalog**: a
blob sitting exactly where a catalogued static star already sits cannot be the
star that moved, so it is excluded (a very-high-proper-motion field star on a
deep plate remains a documented residual edge case). (Those survey plates are
credited to STScI/DSS; the full credit line is in the demo playbook and
`journal/citations.md`.)

---

## What this tool does NOT do (important, and mostly correct physics)

- **It applies no stellar-aberration correction of its own — and on these
  frames it does not need to.** The demo's `pwcs2` frames carry Gaia-calibrated
  plate solutions whose WCS zero-point already absorbs the ~9.6 arcsec
  aberration, so the two-frame ~1 au miss is **single-frame centroid noise**
  (~0.6 arcsec effective), *not* uncorrected aberration — averaging all twelve
  frames drives the miss to 0.387 au. A raw frame carrying its own naive WCS
  *would* need a correction: injecting a synthetic 9.6 arcsec aberration swings
  the miss to ~17 au. (The older "aberration is why it misses by ~1 au"
  explanation was measured to be false and has been removed.)
- **One image alone cannot give a point.** One star is one line. The tool says
  so in plain words and asks for a second, **different** nearby star. Two lines
  from the *same* star are still (nearly) parallel and fix only a line.
- **A random sky photo finds nothing — and that is the right answer.** The
  catalog holds only the 1,941 stars within ~20 pc. A snapshot of an arbitrary
  patch of sky contains none of them, so the tool can plate-solve it (tell you
  where the camera pointed) but cannot fix a position — there are no *nearby*
  stars in view to triangulate on. Pointing without a position fix is the
  correct physics of that situation, not a failure of the tool.
- **It cannot invent a WCS from nothing.** With no WCS in the header and no
  blind solver installed, the tool cannot plate-solve. It still works on any
  image that already carries a WCS — which every demo frame here does.
- **It never touches the truth side.** The window only ever sees the photo and
  the public catalog — exactly what a real spacecraft carries. It imports
  nothing from `galnav/truth`; `tests_gui/test_wall.py` proves this by reading
  the code.
- **It is not spine science.** It changes zero golden numbers and adds zero new
  libraries. If it broke tomorrow, every result in the paper would be untouched.

---

## Measured results on real data (2026-07-17)

The demo runs on the twelve real New Horizons LORRI frames in
`data/e3_new_horizons/repo/` — six looking at the Proxima Cen field (the first
taken 2020-04-22) and six at the Wolf 359 field (2020-04-23), each 256×256 px
at 4.095 arcsec/px, all carrying solved WCS. There are two results worth
showing, both measured this session.

**The headline — all twelve frames.** The Locate button accumulates every
loaded image, so feeding all twelve builds twelve lines of position:

| quantity | value |
|---|---|
| **miss vs JPL truth** | **0.387 au** (\|r\| = 47.39 au) |
| 1-sigma error ellipsoid | `[0.441, 0.233, 0.206]` au (σ_θ = 0.44″) |
| **catalog age estimate** | **4.286 ± 0.055 yr** (true 4.310 yr; \|diff\| 0.024 yr) |

**The quick teaching case — two frames** (Proxima `lor_0449855930` + Wolf 359
`lor_0449933827`), the fast version to show first:

| quantity | value |
|---|---|
| recovered \|r\| | 47.05 au |
| JPL Horizons truth | `[13.5495, −42.0195, −16.4573]` au |
| **miss vs truth** | **0.98 au** (web app, one catalog age) / 0.976 au (`nh_demo`, per-frame age) |
| 1-sigma error ellipsoid | `[1.08, 0.57, 0.504]` au (σ_θ = 0.44″) |
| **catalog age estimate** | **4.336 ± 0.134 yr** (true 4.309 yr; \|diff\| 0.027 yr) |

(The tiny 0.98-vs-0.976 gap is only the age model: the web app applies one
catalog age to both frames, while the headless `nh_demo` ages each frame to its
own epoch. Same physics, same ellipsoid, same age estimate.)

The headline ellipsoid is exactly **√6 tighter** than the two-frame one
(`[1.08, 0.57, 0.504] / √6 ≈ [0.441, 0.233, 0.206]`): six sightlines per star
average down the per-frame centroid noise, which is the whole reason twelve
frames beat two.

### The Earth sanity check (a nice booth story)

The same folder holds two ground-based calibration frames
(`lco_prox_20200422-0332.fits` and `wolf359_20200423_ULMT_...fits`). Feed those
two through the very same pipeline and it fixes **the observer who took them** —
recovering **\|r\| = 1.149 au**, i.e. Earth's distance from the Sun. The tool
finds *whoever* took the picture, spacecraft or telescope. (Never mix an Earth
frame with a spacecraft frame in one fix — they are two different observers.)

### The honest comparison to Lauer

Lauer et al. (2025) reached **0.351 au** on this spacecraft, and the GalNav
**spine** experiment E3 independently reproduces that — recovering New Horizons
to **0.3467 au** of the JPL ephemeris (six averaged, aberration-corrected
sightlines per star). The GUI's twelve-frame **0.387 au** lands right on
Lauer's 0.351 au — with nothing but quick 5-sigma centroids and no explicit
aberration step, because the Gaia-calibrated WCS already absorbs the aberration.
The two-frame **~0.98 au** is larger only because it uses **one** frame per star
instead of six; the difference is centroid-noise averaging, **not** aberration.
The remaining ~0.39 au floor is **residual per-frame systematics**, not a
missing aberration correction. Do not read the two-frame ~1 au as the project's
navigation accuracy — the vetted number is the spine's E3 (0.3467 au).

To go sharper still, the natural moves are more frames per star (the headline
already uses all twelve) and letting the blind solvers carry raw amateur images
that have no WCS yet. None of that changes the spine; it only polishes the
front door.

---

## Troubleshooting

| symptom | what it means | what to do |
|---|---|---|
| "could not plate-solve … no celestial WCS" | the image has no WCS and no blind solver is installed | install a backend: local `wsl sudo apt install astrometry.net` (+ index files sized to your field), or get a free nova key at nova.astrometry.net/api_help and pass it in the window / set `ASTROMETRY_NET_API_KEY` |
| no matches found | the catalog is aged wrong, or the star is farther off than the match radius | check the catalog age (a few years of drift moves nearby stars many pixels); raise the match radius (parallax grows with spacecraft distance) |
| "need at least 2 lines of position" | only one image / one star was matched | add an image of a **different** nearby star — one line is only a line |
| "all lines are from the same star" | the matched stars share a source id | image a second, distinct nearby star in a separated direction |
| "lines … within ~5 arcmin of parallel" | the two stars are nearly the same direction | choose stars farther apart on the sky |
| age error bar is `NaN` | the chi2 minimum sits at the edge of the age grid, or the curve is not convex there | widen or re-centre the age grid so the minimum is interior; inspect the raw chi2-vs-age curve |
| the two-frame fix is ~1 au off | expected — one frame per star, so single-frame centroid noise dominates (not aberration) | load all twelve frames to average it down to 0.387 au; the vetted 0.35 au number is the spine's E3 |
