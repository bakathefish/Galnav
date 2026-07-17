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
matplotlib). `tkinter` is part of the Python standard library; image reading for
PNG/JPG uses Pillow, which already ships with matplotlib. **No new pip installs.**

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
  Proxima — plus ~10″ of stellar aberration at ~14 km/s. The 120″ default covers
  outer-solar-system demos; raise it (a UI knob) for spacecraft farther out.
- **No aberration correction.** We do not remove the ~10″ stellar-aberration
  shift from the spacecraft's own motion. This is the main reason a quick fix
  lands ~1 au from truth rather than ~0.3 au.
- **Age estimate leans on proper motion.** The χ² scan finds the epoch because
  nearby stars drift fast (Proxima ~3.85″/yr, Wolf 359 ~4.7″/yr); a wrong age
  puts each star many pixels off and the lines stop crossing. The `σ_age` error
  bar is a curvature (Δχ²=1) estimate, honest when the minimum is interior and
  the curve is convex.

## Measured results (`python -m gui.nh_demo`, 2026-07-17)

Two real New Horizons LORRI frames (Proxima `lor_0449855930`, Wolf 359
`lor_0449933827`, taken 2020-04-23):

| quantity | value |
|---|---|
| recovered position | `[12.694, −42.038, −16.926]` au (|r| = 47.06 au) |
| miss vs JPL Horizons truth | **0.976 au** |
| 1-σ error ellipsoid | `[1.08, 0.57, 0.504]` au (σ_θ = 0.44″) |
| catalog age estimate | **4.336 ± 0.134 yr** (true 4.309 yr; |diff| 0.027 yr) |

The ~1 au miss is *expected* and is printed with its explanation: single raw
frames, quick 5-σ centroids, and no aberration correction — whereas the spine's
E3 result (0.35 au) used 6 averaged, aberration-corrected sightlines per star.
Do not read the demo's ~1 au as the project's navigation accuracy; the vetted
number lives in the spine (E3).

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
