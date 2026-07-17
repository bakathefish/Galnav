# GalNav GUI — starlight navigation demo

Upload spacecraft star-field image(s); the tool plate-solves each frame,
identifies nearby (≤ 20 pc) Gaia catalog stars in it, accumulates a line of
position per matched star across all your images, and reports **where the
spacecraft is** — a position in au with a 1-σ error ellipsoid. It also handles
the star catalog's **age both ways**: you can *set* the age (the catalog is
propagated forward before matching), and the tool can *estimate* the age from
how far the stars have drifted (a χ² scan over age).

This is a **demo layer** on top of the finished GalNav spine. Every physics step
reuses the vetted navigator (`galnav.nav.triangulate.n_star_solve`, the
`galnav.nav.catalog` aging, and `galnav.units`). It touches no science golden
numbers and adds no new dependencies.

## Run it

From the repo root:

```
python -m gui.app          # open the window
python -m gui.nh_demo       # real New Horizons smoke test (prints numbers)
```

Requirements: the project's existing stack (Python 3.11+, numpy, scipy, astropy,
matplotlib). `tkinter` is part of the Python standard library. PNG/JPG reading
uses Pillow, an **optional** matplotlib dependency that is already installed in
this environment (Pillow 11.3.0) — it is not bundled with matplotlib, but no new
`pip install` is needed here; FITS never needs it. **No new pip installs.**

### Using the window

1. **Add image(s)…** — pick one or more FITS/PNG/JPG star-field frames.
2. **Solve fields** — attach a WCS to each (runs in a background thread; per-image
   status shows in the list).
3. Set **catalog age** (years since J2016.0; auto-filled from a FITS observation
   time if present), **RV fill**, and **match radius**.
4. **Locate spacecraft** — prints the position, |r|, the error ellipsoid, χ², and
   which star from which frame contributed. One image alone yields only a *line*
   of position; the tool says so and asks for a second, different nearby star.
5. **Estimate catalog age** — scans χ² over an age grid (min/max/step are UI
   fields), prints `age_hat ± σ`, and draws the χ²-vs-age curve.

The image panel shows the selected frame (log stretch), detected centroids as
circles, and matched catalog stars as labelled crosses (Proxima Cen and Wolf 359
are named; others show their Gaia source id).

## The three plate-solve backends

`solve_image` tries these in order and, if all fail, raises one error explaining
each failure and how to enable it.

1. **`fits-header`** — the image already carries a solved WCS in its header. Free,
   offline, instant. Every demo frame in `data/e3_new_horizons/repo/` (the
   `*_pwcs2.fits` LORRI frames) is like this. Nothing to install.

2. **`wsl` (local astrometry.net)** — a blind solve via `solve-field` inside WSL.
   One-time setup:
   ```
   wsl sudo apt install astrometry.net
   # plus index files sized to your field of view, e.g. the 4100/4200 series:
   wsl sudo apt install astrometry-data-4208 astrometry-data-4207   # (examples)
   ```
   Index files must cover your image's angular scale — wide fields need the
   4100/4200 series; narrow fields need higher-numbered (finer) indexes. The tool
   converts Windows paths to `/mnt/c/...` form automatically.

3. **`nova` (nova.astrometry.net web API)** — a blind solve in the cloud. Get a
   free API key from <https://nova.astrometry.net/api_help> (sign in, copy the
   key from your profile). Pass it in the window's *nova API key* field or set
   `ASTROMETRY_NET_API_KEY` in your environment. Uses only the Python standard
   library `urllib` (no new dependency); requires network access.

The blind backends (2, 3) are **optional** — with neither installed the tool
still fully works on any image that already has a WCS.

## Honest physics limits

- **Pointing is always available; position needs geometry.** A single star gives
  a *direction* (a line of position). You need ≥ 2 **distinct** nearby stars,
  across the session's images, for the lines to cross at a point.
- **Match radius must swallow parallax.** The tool predicts a star's pixel from
  its *barycentric* direction, but the spacecraft sees it shifted by ≈ r/d
  (spacecraft distance ÷ star distance) — e.g. ~36″ for a 47 au spacecraft and
  Proxima. Stellar aberration from the observer's ~14 km/s motion is another
  ~9.6″, but on the New Horizons pwcs2 frames that shift is already **absorbed
  into the plate solution** (the field stars are aberrated by the same amount),
  so the measured residuals here are essentially pure parallax; the 9.6″ is only
  budgeted for *foreign* images whose WCS did not absorb it. The 120″ default
  covers outer-solar-system demos; raise it (a UI knob) for spacecraft farther
  out.
- **The ~1 au miss is single-frame centroid noise, not aberration.** The measured
  target residuals (31.9″ Proxima, 16.4″ Wolf) match *pure parallax* geometry to
  a few tenths of an arcsecond — not parallax ± 9.6″. Injecting the 9.6″
  aberration into the sightlines swings the miss to ~17 au, so if it were
  uncorrected the fix would be ~17 au off, not ~1. An explicit aberration
  correction would therefore **not** improve the fix. What tightens it is
  *averaging frames*: using all 12 LORRI frames (6 per star) instead of 2 pulls
  the miss to 0.387 au and shrinks the error ellipsoid by √6 (see below). The
  residual ~0.39 au floor is per-frame astrometric systematics (our quick
  centroids vs Buie's careful multi-frame astrometry), not aberration.
- **Age estimate leans on proper motion.** The χ² scan finds the epoch because
  nearby stars drift fast (Proxima ~3.85″/yr, Wolf 359 ~4.7″/yr); a wrong age
  puts each star many pixels off and the lines stop crossing. The `σ_age` error
  bar is a curvature (Δχ²=1) estimate, honest when the minimum is interior and
  the curve is convex. Ages that drift a star out of the match radius are scored
  as unmatchable (χ² = ∞) rather than crashing the scan.
- **Ground-based frames fix the OBSERVER — a feature, not a bug.** The included
  `lco_prox` / `wolf359_ULMT` frames carry valid WCS and their targets are
  identified, but the pipeline then fixes *whoever took the picture*: it lands on
  **Earth** (|r| = 1.149 au). The tool finds the observer, so mixing Earth frames
  with New Horizons frames in one fix is meaningless — keep a session to one
  spacecraft.

## Measured results (`python -m gui.nh_demo`, 2026-07-17)

Real New Horizons LORRI frames (Proxima field 2020-04-22, Wolf 359 field
2020-04-23), classified by which target their WCS centre contains:

| quantity | 2 frames (teaching) | all 12 frames (headline) |
|---|---|---|
| recovered position (au) | `[12.694, −42.038, −16.926]` | `[13.386, −42.369, −16.486]` |
| \|r\| (au) | 47.06 | 47.39 |
| **miss vs JPL Horizons** | **0.976 au** | **0.387 au** |
| 1-σ error ellipsoid (au) | `[1.08, 0.57, 0.504]` | `[0.441, 0.233, 0.206]` |
| χ² | 1.56e−13 | 3.16e−11 |
| catalog age estimate | 4.336 ± 0.134 yr | 4.286 ± 0.055 yr |

(σ_θ = 0.44″ Buie per-image sigma; ages vs true ~4.31 yr.) The **0.387 au**
all-frames miss matches Lauer et al.'s **0.351 au** (their 12-line ×60 solve),
and the ellipsoid is exactly √6 tighter than the 2-frame one — 12 lines instead
of 2, i.e. centroid-noise averaging. Do not read the 2-frame ~1 au as the
project's navigation accuracy; the vetted spine number lives in E3.

## Files

| file | job |
|---|---|
| `gui/platesolve.py` | WCS from FITS header / WSL astrometry.net / nova web API |
| `gui/centroids.py` | detect stars, sub-pixel centroids (robust threshold) |
| `gui/locate.py` | age the catalog, identify in-frame stars, fix the position |
| `gui/age.py` | estimate the catalog age (χ²-vs-age scan) |
| `gui/fitsmeta.py` | read the observation time (DATE-OBS / SPCUTCAL) → catalog age |
| `gui/app.py` | the tkinter window (thin shell over the above) |
| `gui/nh_demo.py` | real-data end-to-end smoke script |
| `tests_gui/` | offline, deterministic tests (`python -m pytest tests_gui -q`) |

## Truth wall

The GUI is navigator-side: it imports only stdlib/numpy/scipy/astropy/matplotlib
and the navigator surface (`galnav.nav.*`, `galnav.units`, `galnav.geometry`,
`galnav.parallax`) — never `galnav.truth`. `tests_gui/test_wall.py` enforces this
by AST inspection.
