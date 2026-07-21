# GalNav web demo

A browser version of the GalNav demo. It opens in your browser — so it actually
shows up in a headless/remote session where the tkinter window (`gui/app.py`)
cannot. Same physics, nicer shell.

## Run it

From the repo root:

```
python -m gui.webapp
```

It prints `GalNav web demo running -> http://127.0.0.1:PORT   (Ctrl+C to stop)`
(first free port from 8000) and opens your browser. If no browser is available
(headless), the server still runs — just open the printed URL yourself.

The page is **upload-first**: the primary card is **Add your own image** — drop in
a raw star-field image (no coordinates needed) and the pipeline plate-solves,
identifies, and locates. Below it is the **reproducible New Horizons demo** (the
offline anchor): click **Quick demo (2 frames)** or **Full solve (all 12)**, then
**Locate spacecraft** or **Estimate catalog age**.

## What it does

The same five-stage pipeline as the rest of `gui/`, reused unchanged:
plate-solve → centroid → age the catalog → identify nearby stars → intersect the
lines of position. On the 12 real New Horizons LORRI frames it recovers the
spacecraft to **0.387 au** of the JPL Horizons truth (matching Lauer et al.'s
0.351 au 12-line solve) and estimates the catalog age to **4.286 ± 0.055 yr**
(true ~4.31). The 2-frame teaching case gives ~0.98 au — the difference is
centroid-noise averaging, not aberration (see `journal/gui-wrapper.md`).

## Uploading a raw image (the primary flow)

An arbitrary telescope/spacecraft image usually has **no coordinates** in its
header, so it needs a blind plate solve. The upload path tries, in order:
the FITS header (instant if present), a local **astrometry.net** via WSL, then
**nova.astrometry.net** (paste a free API key under "No coordinates in the
image?"). While the solve runs, the card shows a staged indicator
(*solving field… identifying… locating…*). If no solver is installed, it shows
the friendly three-backend message prominently — the exact error a user hits
before `solve-field` is set up, with the one-line install hint.

**Try it without a telescope.** `gui/raw_demo.py` writes a WCS-stripped copy of a
demo LORRI frame — a genuine "raw" image (pixels only) — so you can exercise the
whole upload path live once a solver is installed:

```
python -m gui.raw_demo                       # -> results/lor_..._RAW_no_wcs.fits
python -m gui.raw_demo <src.fits> <out_dir>  # choose the frame and folder
```

The raw path is proven end-to-end by `tests_gui/test_raw_upload.py`: with the
solver mocked absent it returns the friendly error; with the solver mocked to
return the frame's true plate the upload identifies Proxima and the fix
reproduces the 2-frame teaching number — every line of the raw chain except the
solver binary itself.

## Centroid accuracy (moment vs PSF)

Centroids default to the robust flux-weighted (moment) centre. `gui/centroids.py`
also has an **optional** Gaussian-PSF refinement (`refine=True`), but it is OFF by
default: measured on the demo, PSF refinement did NOT improve the headline
12-frame miss (0.38659 → 0.40864 au, slightly worse — the 12-frame average of
moment centroids beats locking in the fit's small systematic), though it helped
the noisier 2-frame case (0.98301 → 0.72284 au). A null result, kept behind the
parameter and recorded in `journal/gui-wrapper.md`.

## Identifying stars in the frame (labels + distances)

The preview labels every star it can. Cyan circles mark every **detected** blob.
A star that also cross-matches the catalog by sky position is **identified** and
gets its distance shown; a star close enough that its parallax shift reveals the
spacecraft's position is **position-capable** and gets the big amber cross +
name + distance (e.g. `Proxima Cen (1.3 pc)`). The caption reads
`N detected - M identified - K position-capable`.

Two different matches drive this: a tight (~2-pixel) *identification* cross-match
by sky position, and the generous 120-arcsec *navigation* match that swallows
parallax. Because nearby stars are displaced tens of arcsec by parallax, the
tight identification picks up the DISTANT stars, while the position-capable
nearby ones come from the navigation match — exactly the pedagogical split.

**Honest scope of "identified".** The demo catalog only reaches ~100 pc, and a
narrow LORRI frame near the galactic plane holds ~100 detected blobs of which
only a couple are within 100 pc (the rest are faint kpc-distant field stars in
no nearby catalog). So on the demo frames you will typically see
`100 detected - 2 identified - 1 position-capable`: the tool labels what it
*can*, and the lesson is that almost everything you see is too far to navigate
by. Labelling "nearly every dot" would require a full-depth Gaia field catalog,
not a nearby-star subset.

**Which catalog is used, and why it is split:**

- `/api/locate` and `/api/estimate_age` for the 12 baked-in New Horizons frames
  use the **frozen 20-pc catalog** (`data/gaia_dr3_nav_subset.csv`) so the
  blessed 0.387 au / 4.286 yr numbers stay byte-reproducible.
- The **identification labels** (and the navigation path for **uploaded**
  frames) use the widest catalog available — `data/gaia_dr3_nav_100pc.csv` if
  present, else the 20-pc file. If that wide file is absent, or mid-write and
  unparseable, labeling degrades gracefully to the 20-pc catalog.

## Backend (stdlib only)

No new dependencies. The server is Python's `http.server.ThreadingHTTPServer`;
JSON via `json`; PNGs via matplotlib (already a dependency, Agg backend);
multipart uploads parsed by hand (the `cgi` module was removed in Python 3.13).
All physics is the existing `gui/*` + `galnav.nav.*` code.

### Endpoints

| method + path | returns |
|---|---|
| `GET /` | the HTML page |
| `GET /static/{app.js,style.css}` | the frontend assets (allowlisted; no traversal) |
| `GET /api/frames` | `[{id, name, field, obs_age_yr}]` for the 12 demo frames + uploads |
| `GET /api/image?id=&age=&radius=[&thumb=1]` | PNG: the frame log-stretched, cyan circles on every detected star, amber cross + name + distance on position-capable nearby stars, muted distance labels on other identified stars (`thumb=1` = fast nav-only overlay for gallery thumbnails) |
| `POST /api/locate` `{ids, age, radius, rv}` | `{ok, x_au, r_au, r_pc, ellipsoid_au, chi2, n_lines, distinct_stars, lines, miss_au, message}` |
| `POST /api/estimate_age` `{ids, radius, rv, min, max, step}` | `{ok, age_hat_yr, sigma_age_yr, ages, chi2s, note, truth_yr}` |
| `POST /api/upload` (multipart) | plate-solves the upload and adds it to the gallery, or `{ok:false, message}` |

Errors are returned as `{ok:false, message:"..."}` with HTTP 200, so the
frontend can always parse them — no stack traces reach the browser. The handler
is thin; all logic lives in plain module functions (`frames_payload`,
`render_frame_png`, `locate_payload`, `age_payload`, `handle_upload`,
`static_file`) that the tests call directly without a socket.

## Offline story

Everything above works offline against the committed demo dataset — no network.
The one online path is uploading an image that has **no WCS in its header**: a
blind plate solve is then required, via either a local astrometry.net install
(WSL) or a free nova.astrometry.net API key (paste it into the "nova API key"
field, or set `ASTROMETRY_NET_API_KEY`). FITS files that already carry a WCS
(like the demo frames) need neither.

## See it in OpenSpace (the live viewer)

The pipeline's viewer is a running **OpenSpace** (the NASA/AMNH open-source
planetarium; not vendored — the optional show layer). The main page's panel
shows a reachability chip, walks the six pipeline pages (each pushes its stage
live: stars → lines → fix), and after a successful Locate pushes the recovered
fix (amber) with the JPL truth (cyan) and the white miss line between.

**Confirmed, not assumed.** Every push goes through
`gui/openspace_link.run_lua_confirmed`: the chunk ends with a `return 1`
sentinel and OpenSpace's reply frame carries it back **after the chunk
executes** (measured on a live 0.22.0, 2026-07-21 — a failing chunk replies
with an empty payload, so execution failure is distinguishable too). The UI
reports *confirmed* / *sent (no execution confirmation)* / a failure pointing
at the OpenSpace log. With OpenSpace not running, everything degrades to an
honest "start OpenSpace" message.

An earlier in-page 3-D view (vendored spacekit.js) was **removed outright on
2026-07-21** — page, vendored tree and tests. The citations for what it once
shipped remain in `journal/citations.md` ([Spacekit], [WhereInSpace-data]).

## Truth wall

`gui/webapp.py` imports only `gui.*` and (transitively) `galnav.nav.*` /
`galnav.units` — never `galnav.truth`. `tests_gui/test_wall.py` enforces this by
AST inspection over every `gui/*.py`.
