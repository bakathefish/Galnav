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

Then: click **Quick demo (2 frames)** or **Full solve (all 12 frames)**, then
**Locate spacecraft**, or **Estimate catalog age**. Or select individual frames
from the gallery and add your own image.

## What it does

The same five-stage pipeline as the rest of `gui/`, reused unchanged:
plate-solve → centroid → age the catalog → identify nearby stars → intersect the
lines of position. On the 12 real New Horizons LORRI frames it recovers the
spacecraft to **0.387 au** of the JPL Horizons truth (matching Lauer et al.'s
0.351 au 12-line solve) and estimates the catalog age to **4.286 ± 0.055 yr**
(true ~4.31). The 2-frame teaching case gives ~0.98 au — the difference is
centroid-noise averaging, not aberration (see `journal/gui-wrapper.md`).

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

## Truth wall

`gui/webapp.py` imports only `gui.*` and (transitively) `galnav.nav.*` /
`galnav.units` — never `galnav.truth`. `tests_gui/test_wall.py` enforces this by
AST inspection over every `gui/*.py`.
