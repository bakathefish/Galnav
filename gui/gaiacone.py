"""Deep identify: a per-frame, full-depth Gaia cone cache for LABELLING.

The nearby (<=20 pc / <=100 pc) navigation catalogs identify only the handful of
stars close enough to navigate BY. Most blobs in a LORRI frame are faint field
stars far beyond those catalogs. To label those too -- "we know which star this
is" -- we fetch the full-depth Gaia DR3 stars inside each frame's footprint from
the ESA Gaia TAP service and cache the result on disk, once per footprint.

TWO CLEAR SEPARATIONS keep this honest and safe:
  * IDENTIFICATION vs NAVIGATION. This cone feeds only the identification tier
    (a tight ~2-pixel positional match: "which catalogued star is this dot?").
    The position-capable / navigation tier is UNCHANGED -- it still uses the
    nearby catalog and the 120-arcsec parallax match. A far star gets a label,
    never a vote in the fix.
  * FETCH vs RENDER. Rendering NEVER hits the network: cone_catalog(..,
    allow_fetch=False) returns a cached cone or None, so a preview cannot hang.
    The prewarm script (gui/prewarm_demo_cones.py) does the one-time fetching so
    the booth demo runs fully offline. A cache HIT is zero network.

TRUTH WALL: navigator-side only. Imports stdlib + numpy + galnav.units. It reads
public Gaia catalog data (what a real spacecraft carries) and never touches
galnav.truth.

Stdlib only (urllib) -- astroquery is not an allowed dependency. The cone can
exceed the 2000-row synchronous TAP cap near the galactic plane (Proxima sits at
b ~ -2 deg), so this uses the ESA Gaia TAP ASYNC (UWS) job workflow -- submit ->
poll -> download -- copied from data/fetch_gaia_100pc.py.
"""

import csv
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from galnav.units import deg_to_rad, radec_to_unit

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "data" / "gaia_cones"

TAP_ASYNC = "https://gea.esac.esa.int/tap-server/tap/async"
UA = {"User-Agent": "galnav-cone/1.0 (stdlib urllib; ISEF research)"}

# 5000 BRIGHTEST stars in the footprint. That is plenty to label ~100 detected
# blobs in a 0.23 deg LORRI frame, and the ORDER BY keeps the useful bright ones
# when the cap bites. The columns are the minimum the label logic needs: an id,
# a sky position (for the tight identification match), a parallax + its S/N (to
# decide whether a distance is trustworthy), and the G magnitude (the fallback
# label for faint stars whose parallax is junk).
CONE_TOP = 5000
CONE_COLUMNS = "source_id, ra, dec, parallax, parallax_over_error, phot_g_mean_mag"

AU_PER_PC = 206264.806  # arcsec per radian = au per pc


def _footprint(plate):
    """(ra_deg, dec_deg, radius_deg) of a plate's footprint, each rounded to 0.01.

    Centre is the plate centre; radius is HALF the frame diagonal plus a 10%
    margin (LORRI ~ 0.23 deg). Rounding to 0.01 deg (~36 arcsec) is the cache
    key, so the several same-pointing LORRI frames collapse to ONE cone file.
    """
    ra, dec = plate.center_radec_deg
    half_diag_deg = (
        0.5 * float(np.hypot(plate.width, plate.height)) * plate.scale_arcsec_per_px
    ) / 3600.0
    radius_deg = half_diag_deg * 1.10
    return round(ra, 2), round(dec, 2), round(radius_deg, 2)


def _cache_path(plate, cache_dir):
    """Disk path for a plate's cone cache file (keyed on the rounded footprint)."""
    ra, dec, r = _footprint(plate)
    name = f"cone_ra{ra:.2f}_dec{dec:+.2f}_r{r:.2f}.csv"
    return Path(cache_dir) / name


# --- ESA Gaia TAP async (submit -> poll -> download), stdlib urllib ----------
def _post_no_redirect(url, fields, timeout=180):
    """POST form-encoded fields WITHOUT following redirects, so the async submit
    can read the Location header of the 303 that points at the new UWS job."""
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers=UA)

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers
    except urllib.error.HTTPError as e:  # 303 lands here (redirect blocked)
        return e.code, e.headers


def _get_text(url, timeout=180):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def _fetch_cone_csv(ra_deg, dec_deg, radius_deg, out_path, max_wait_s=300):
    """Fetch the footprint's Gaia cone via an async TAP job and write it to disk.

    Isolated so tests can monkeypatch it. Writes atomically (via a .part file
    then os.replace) so a partial download is never left as a valid-looking
    cache. Raises on any HTTP/URL/timeout error -- the caller turns that into a
    silent None.
    """
    query = (
        f"SELECT TOP {CONE_TOP} {CONE_COLUMNS} FROM gaiadr3.gaia_source "
        f"WHERE 1=CONTAINS(POINT('ICRS',ra,dec),"
        f"CIRCLE('ICRS',{ra_deg},{dec_deg},{radius_deg})) "
        f"ORDER BY phot_g_mean_mag ASC"
    )
    status, headers = _post_no_redirect(
        TAP_ASYNC,
        {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "PHASE": "RUN",
            "QUERY": query,
        },
    )
    job_url = headers.get("Location")
    if not job_url:
        raise RuntimeError(f"async submit gave no Location (HTTP {status})")

    waited, delay = 0.0, 2.0
    while waited < max_wait_s:
        phase = _get_text(job_url + "/phase").strip()
        if phase == "COMPLETED":
            break
        if phase in ("ERROR", "ABORTED", "HELD"):
            raise RuntimeError(f"cone job ended {phase}")
        time.sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 15.0)
    else:
        raise TimeoutError(f"cone job did not finish within {max_wait_s}s")

    tmp = Path(str(out_path) + ".part")
    req = urllib.request.Request(job_url + "/results/result", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _parse_cone_csv(path):
    """Parse a cached cone CSV into arrays for identification labelling.

    Reads by column NAME (case-insensitive) so column order cannot silently
    corrupt it. Null parallax / magnitude cells become NaN. positions_au are
    UNIT direction vectors (magnitude 1): the identification match only uses the
    direction, and distances for labels come from parallax, not |position|, so a
    junk parallax never produces a bogus position.

    Returns a dict with positions_au (N,3), source_id (N,), ra_deg, dec_deg,
    parallax_mas, parallax_over_error, phot_g_mag (each (N,)); or None if the
    file has no data rows.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        keymap = {k.lower(): k for k in (reader.fieldnames or [])}

        def col(row, name):
            return row.get(keymap.get(name, name), "")

        sids, ras, decs, plx, snr, gmag = [], [], [], [], [], []

        def fnum(s):
            s = (s or "").strip()
            if s in ("", "null", "NaN", "nan"):
                return float("nan")
            return float(s)

        for row in reader:
            try:
                sids.append(int(col(row, "source_id")))
            except (TypeError, ValueError):
                continue
            ras.append(fnum(col(row, "ra")))
            decs.append(fnum(col(row, "dec")))
            plx.append(fnum(col(row, "parallax")))
            snr.append(fnum(col(row, "parallax_over_error")))
            gmag.append(fnum(col(row, "phot_g_mean_mag")))

    if not sids:
        return None
    ra_deg = np.asarray(ras, dtype=float)
    dec_deg = np.asarray(decs, dtype=float)
    units = np.array(
        [radec_to_unit(deg_to_rad(a), deg_to_rad(d)) for a, d in zip(ra_deg, dec_deg)],
        dtype=float,
    )
    return {
        "positions_au": units,
        "source_id": np.asarray(sids, dtype=np.int64),
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "parallax_mas": np.asarray(plx, dtype=float),
        "parallax_over_error": np.asarray(snr, dtype=float),
        "phot_g_mag": np.asarray(gmag, dtype=float),
    }


def cone_catalog(plate, cache_dir=None, allow_fetch=True):
    """Full-depth Gaia cone for a plate's footprint, from cache or (optionally) net.

    plate: PlateSolution (its footprint is the cache key and the query cone).
    cache_dir: where cone CSVs live (default gui.gaiacone.CACHE_DIR).
    allow_fetch: if the footprint is not cached, whether to fetch it. RENDERING
        passes False so a preview never blocks on the network; the prewarm script
        passes True. A cache HIT costs zero network either way.
    Returns: the parsed cone dict (see _parse_cone_csv), or None if there is no
        cache and (fetch disallowed OR the fetch failed for any reason). None is
        the caller's cue to fall back to the nearby-catalog labels -- never an
        error surfaced to the browser.
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(plate, cache_dir)
    if path.exists():
        try:
            return _parse_cone_csv(path)
        except Exception:  # noqa: BLE001 -- a corrupt cache must not crash a render
            return None
    if not allow_fetch:
        return None
    ra, dec, radius = _footprint(plate)
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        _fetch_cone_csv(ra, dec, radius, path)
    except Exception:  # noqa: BLE001 -- offline / TAP down -> degrade silently
        return None
    try:
        return _parse_cone_csv(path)
    except Exception:  # noqa: BLE001
        return None


def distance_label(name, parallax_mas, parallax_over_error, phot_g_mag):
    """The muted label text for one identified star -- honest about what we know.

    Precedence: a known common name wins; else a DISTANCE ("N pc") but ONLY when
    the parallax is trustworthy (parallax_over_error >= 5 and parallax > 0), since
    faint far stars have junk (often negative) parallaxes; else the G MAGNITUDE
    ("G 16.8") so the dot is still labelled with something real; else None (the
    marker alone). Units: parallax_mas in mas, phot_g_mag in Gaia G mag.
    """
    if name:
        return name
    if (
        parallax_over_error is not None
        and np.isfinite(parallax_over_error)
        and parallax_over_error >= 5.0
        and parallax_mas is not None
        and np.isfinite(parallax_mas)
        and parallax_mas > 0.0
    ):
        return f"{1000.0 / parallax_mas:.0f} pc"
    if phot_g_mag is not None and np.isfinite(phot_g_mag):
        return f"G {phot_g_mag:.1f}"
    return None
