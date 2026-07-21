"""Localhost WEB shell for the GalNav demo. Same physics as gui/app.py, but it
opens in a browser -- which actually shows up in a headless/remote session where
a tkinter window cannot.

STDLIB ONLY on the backend: http.server (ThreadingHTTPServer), json, io, os,
re, socket, threading, webbrowser, and a hand-rolled multipart parser (the cgi
module was removed in Python 3.13). Rendering uses matplotlib (already a dep,
Agg backend). ALL physics is the existing gui/ + galnav.nav pipeline -- nothing
is reimplemented here.

TRUTH WALL: this module imports only gui.* and galnav.nav.* / galnav.units
(transitively, via gui.*). It never imports galnav.truth; tests_gui/test_wall.py
covers every gui/*.py including this file.

The HTTP handler is THIN: it only routes and serialises. The real work lives in
plain module functions -- frames_payload(), render_frame_png(), locate_payload(),
age_payload(), handle_upload() -- so tests call them directly without a socket.

Run:  python -m gui.webapp
"""

import glob
import hashlib
import io
import json
import os
import re
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gui import gaiacone, openspace_link
from gui.age import drift_date, estimate_age
from gui.app import CATALOG_CSV, STAR_NAMES, load_grayscale
from gui.centroids import find_centroids
from gui.fitsmeta import age_yr_since_j2016, observation_jd
from gui.locate import (
    LineOfPosition,
    fix_position,
    identify_in_frame,
    line_of_position_summary,
    load_aged_catalog,
    measured_direction,
)
from gui.platesolve import (
    _wsl_available,
    _wsl_has_galnav_config,
    fits_header_solution,
    solve_image,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
NH_DIR = REPO_ROOT / "data" / "e3_new_horizons" / "repo"
WEB_DIR = Path(__file__).resolve().parent / "web"
# The narrow LITE blind-solve indexes (index-*.fits) the offline solver installs.
# /api/solver_status counts them so the UI can say whether a blind solve is ready.
ASTROMETRY_INDEX_DIR = REPO_ROOT / "data" / "astrometry-index"

NEWH_X_JPL = np.array([13.5495, -42.0195, -16.4573])  # JPL Horizons truth (E3)
PROXIMA_ID = 5853498713190525696
WOLF_ID = 3864972938605115520
DEFAULT_RV_FILL_KMS = 19.57  # Simbad Wolf 359 RV (our CSV lacks it); E3 value
RMSSIG_ARCSEC = 0.44  # Buie per-image astrometric sigma (E3)
AU_PER_PC = 206264.806  # arcsec per radian = au per pc

# The FROZEN 20-pc navigation catalog (byte-reproducible fixes) is CATALOG_CSV
# (imported from gui.app). The WIDE catalog (<= 100 pc, ~100-350k rows) is used
# ONLY for IDENTIFICATION labeling and for UPLOADED-frame navigation -- NEVER for
# the blessed demo fix, so 0.387 au / 4.286 yr stay byte-reproducible. If it is
# absent, or (mid-fetch) unparseable, labeling degrades to the 20-pc file.
WIDE_CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_100pc.csv"
_WIDE_LOCK = threading.Lock()  # serialise the one-time wide-catalog parse
_BAD_WIDE_MTIME = set()  # mtimes that failed to parse (partial file); skip them

# UI palette -- mirrors gui/web/style.css dark theme EXACTLY so the overlay plots,
# the page, and OpenSpace tell one colour story (cyan = data, amber = the answer).
# _FACE = --void (imaging black), _LINE = --line, and cyan/amber/dim/muted are the
# --cyan/--amber/--dim/--faint dark tokens verbatim.
_FACE = "#060a12"
_CYAN = "#3fcbef"
_AMBER = "#f2b444"
_DIM = "#93a6bf"
_MUTED = "#6f7f96"  # dim distance labels for identified-but-not-navigable stars
_LINE = "#26324a"

# Static files the /static/ route is allowed to serve (no path traversal).
# The pipeline-*.html pages are the step-by-step visualization (do.txt items 5+9).
# The old spacekit 3-D view (where-in-space.html + gui/web/vendor/) was removed
# outright 2026-07-21 -- OpenSpace is the only viewer.
_STATIC_ALLOW = {
    "app.js": "application/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
    "pipeline-1-raw.html": "text/html; charset=utf-8",
    "pipeline-2-detect.html": "text/html; charset=utf-8",
    "pipeline-3-identify.html": "text/html; charset=utf-8",
    "pipeline-4-angles.html": "text/html; charset=utf-8",
    "pipeline-5-lines.html": "text/html; charset=utf-8",
    "pipeline-6-fix.html": "text/html; charset=utf-8",
}

# --- frame cache ------------------------------------------------------------
_DEMO_INDEX = {}  # "f<n>" -> path
_CACHE = {}  # path -> record dict
_UPLOADS = {}  # "up_<n>" -> record dict
_UPLOAD_N = [0]
_UPLOAD_HASHES = {}  # sha256(file bytes) hex -> "up_<n>" (dedup: identical re-upload)

# Per-process cache of the WSL blind-solver probe (it shells out to `wsl which
# solve-field`, ~0.1-1 s). None = not yet probed. Kept as a plain module global
# so a test can override it (monkeypatch webapp._WSL_SOLVER_CACHE = True/False)
# without touching the real WSL.
_WSL_SOLVER_CACHE = None


def _demo_paths():
    return sorted(glob.glob(str(NH_DIR / "lor_*_pwcs2.fits")))


def _ensure_demo_index():
    if not _DEMO_INDEX:
        for i, path in enumerate(_demo_paths()):
            _DEMO_INDEX[f"f{i}"] = path


def _classify_field(plate):
    """(field_label, source_id) from the frame's WCS centre RA."""
    cra, _ = plate.center_radec_deg
    if abs(cra - 217.4) < 5.0:
        return "Proxima", PROXIMA_ID
    return "Wolf 359", WOLF_ID


def _demo_record(fid, path):
    """Plate-solve + centroid a demo frame once; cache by path."""
    if path in _CACHE:
        return _CACHE[path]
    plate = fits_header_solution(path)
    image = load_grayscale(path)
    field, sid = _classify_field(plate)
    jd = observation_jd(path)
    rec = {
        "id": fid,
        "name": Path(path).name,
        "path": path,
        "plate": plate,
        "image": image,
        "centroids": find_centroids(image),
        "field": field,
        "sid": sid,
        "obs_age_yr": age_yr_since_j2016(jd) if jd else 0.0,
        "is_demo": True,
    }
    _CACHE[path] = rec
    return rec


def _record_by_id(fid):
    if fid in _UPLOADS:
        return _UPLOADS[fid]
    _ensure_demo_index()
    if fid in _DEMO_INDEX:
        return _demo_record(fid, _DEMO_INDEX[fid])
    return None


def static_file(name):
    """Return (content_type, bytes) for an allowed static file, else None.

    Only the top-level allowlist is served (app.js, style.css, the six
    pipeline pages); everything else -- traversal ("..", absolute, NUL) and
    any non-allowlisted name -- is None. Used directly by the handler AND by
    the tests.
    """
    if ".." in name or name.startswith(("/", "\\")) or "\x00" in name:
        return None
    if name in _STATIC_ALLOW:
        return _STATIC_ALLOW[name], (WEB_DIR / name).read_bytes()
    return None


def frames_payload():
    """Metadata for the gallery: the 12 demo frames plus any uploads.

    Returns: list of {id, name, field, obs_age_yr}.
    """
    _ensure_demo_index()
    out = []
    # Snapshot both dicts before iterating: an /api/upload on another worker
    # thread mutates _UPLOADS mid-iteration otherwise, and dict "changed size
    # during iteration" would 500 the gallery. list() copies the item views.
    for fid, path in list(_DEMO_INDEX.items()):
        rec = _demo_record(fid, path)
        out.append(
            {
                "id": fid,
                "name": rec["name"],
                "field": rec["field"],
                "obs_age_yr": round(rec["obs_age_yr"], 4),
            }
        )
    for uid, rec in list(_UPLOADS.items()):
        out.append(
            {
                "id": uid,
                "name": rec["name"],
                "field": rec["field"],
                "obs_age_yr": round(rec.get("obs_age_yr", 0.0), 4),
            }
        )
    return out


def _nav_catalog_path(is_demo):
    """Catalog for NAVIGATION / position-capable matching.

    Demo frames MUST use the frozen 20-pc file so the blessed 0.387 au / 4.286 yr
    numbers stay byte-reproducible; uploaded frames use the widest catalog (more
    chances a position-capable nearby star is in frame).
    """
    if is_demo:
        return str(CATALOG_CSV)
    wide, _ = _widest_usable_path()
    return wide


def _widest_usable_path():
    """(path, is_wide): the 100-pc file if it exists AND its current mtime has
    not already failed to parse, else the frozen 20-pc file."""
    if WIDE_CATALOG_CSV.exists():
        try:
            mt = os.path.getmtime(WIDE_CATALOG_CSV)
        except OSError:
            mt = None
        if mt is not None and mt not in _BAD_WIDE_MTIME:
            return str(WIDE_CATALOG_CSV), True
    return str(CATALOG_CSV), False


def labeling_catalog(age_yr, rv_kms):
    """Aged catalog for IDENTIFICATION labeling, from the widest usable file.

    Tries the 100-pc catalog; if it is absent or (being written by another
    process) unparseable, records its mtime as bad and falls back to the frozen
    20-pc file. A lock serialises the one-time parse so concurrent requests do
    not each re-read the ~36 MB file.

    Returns: (aged_catalog_dict, path_used).
    """
    path, is_wide = _widest_usable_path()
    if not is_wide:
        return load_aged_catalog(path, age_yr, rv_fill_kms=rv_kms), path
    with _WIDE_LOCK:
        try:
            return load_aged_catalog(path, age_yr, rv_fill_kms=rv_kms), path
        except Exception:  # noqa: BLE001 -- partial/malformed mid-fetch file
            try:
                _BAD_WIDE_MTIME.add(os.path.getmtime(WIDE_CATALOG_CSV))
            except OSError:
                pass
    return (
        load_aged_catalog(str(CATALOG_CSV), age_yr, rv_fill_kms=rv_kms),
        str(CATALOG_CSV),
    )


def crossmatch_labels(
    plate, centroids_xy, aged_cat, position_capable_ids, tol_arcsec=None
):
    """Identify each centroid against a catalog by SKY POSITION, for labelling.

    This is an IDENTIFICATION match (tight, ~2 pixels), NOT the parallax-sized
    120-arcsec navigation match. It projects each catalog star's BARYCENTRIC
    direction through the WCS and matches the nearest centroid within tol_arcsec.
    Because nearby stars are displaced by parallax (tens of arcsec), this tight
    match deliberately picks up the DISTANT stars (whose apparent = barycentric
    to a pixel); the position-capable nearby stars come from the separate 120"
    navigation match and are passed in via position_capable_ids.

    plate: PlateSolution. centroids_xy: (M,2). aged_cat: load_aged_catalog dict.
    position_capable_ids: set of source ids that ARE navigation matches.
    tol_arcsec: identification tolerance (default 2 x the plate scale).
    Returns: list of {centroid_index, source_id, dist_pc, name, position_capable,
        sep_arcsec}.
    """
    if tol_arcsec is None:
        tol_arcsec = 2.0 * plate.scale_arcsec_per_px
    matches = identify_in_frame(
        plate, centroids_xy, aged_cat["positions_au"], match_radius_arcsec=tol_arcsec
    )
    dist_au = np.linalg.norm(aged_cat["positions_au"], axis=1)
    out = []
    for m in matches:
        si = m["star_index"]
        sid = int(aged_cat["source_id"][si])
        out.append(
            {
                "centroid_index": m["centroid_index"],
                "source_id": sid,
                "dist_pc": float(dist_au[si] / AU_PER_PC),
                "name": STAR_NAMES.get(sid),
                "position_capable": sid in position_capable_ids,
                "sep_arcsec": float(m["sep_arcsec"]),
            }
        )
    return out


def cone_label_set(plate, centroids_xy, cone, position_capable_ids, tol_arcsec=None):
    """Identify centroids against a FULL-DEPTH Gaia cone (deep identify tier).

    Same tight ~2-pixel identification match as crossmatch_labels, but the label
    text is parallax-quality aware: a known name, else a distance only when the
    parallax is trustworthy, else the G magnitude (see gaiacone.distance_label).
    Distant faint stars therefore get an honest "G 18.4" rather than a fabricated
    distance from a junk parallax.

    plate: PlateSolution. centroids_xy: (M,2). cone: gaiacone.cone_catalog dict.
    position_capable_ids: source ids that ARE navigation matches (drawn amber).
    tol_arcsec: identification tolerance (default 2 x the plate scale).
    Returns: list of {centroid_index, source_id, name, dist_pc|None,
        position_capable, text, sep_arcsec}. text may be None (marker only).
    """
    if tol_arcsec is None:
        tol_arcsec = 2.0 * plate.scale_arcsec_per_px
    matches = identify_in_frame(
        plate, centroids_xy, cone["positions_au"], match_radius_arcsec=tol_arcsec
    )
    out = []
    for m in matches:
        si = m["star_index"]
        sid = int(cone["source_id"][si])
        plx = float(cone["parallax_mas"][si])
        snr = float(cone["parallax_over_error"][si])
        gmag = float(cone["phot_g_mag"][si])
        name = STAR_NAMES.get(sid)
        dist_pc = float(1000.0 / plx) if np.isfinite(plx) and plx > 0 else None
        out.append(
            {
                "centroid_index": m["centroid_index"],
                "source_id": sid,
                "name": name,
                "dist_pc": dist_pc,
                "position_capable": sid in position_capable_ids,
                "text": gaiacone.distance_label(name, plx, snr, gmag),
                "sep_arcsec": float(m["sep_arcsec"]),
            }
        )
    return out


_OVERLAY_TIERS = ("none", "detected", "identified", "nav")


def render_frame_png(fid, age_yr, radius_arcsec, full_labels=True, overlay="nav"):
    """Render one frame log-stretched, with an overlay tier controlling the marks.

    The overlay tiers layer up (do.txt item 8 -- an uploaded raw image must be
    viewable with NO annotation before the pipeline runs):
      none       -- just the log-stretched image, no marks (a raw photo).
      detected   -- + a cyan circle on every centroid (blob detection).
      identified -- + small muted distance labels on the stars we can name/place
                    against the widest catalog (we know what these dots ARE).
      nav        -- + the big amber cross + name + distance on the position-capable
                    nearby stars (the 120-arcsec navigation matches). This is the
                    full default and is byte-for-byte the previous rendering.

    The pedagogical point of the identified-vs-nav split: we know what many dots
    are, yet only the amber ones are close enough for their parallax to reveal
    position. Dim labels are capped at the 25 brightest for readability; the
    caption reports the full counts. full_labels is set False for gallery
    thumbnails (fast: it skips the deep-identify catalog load); it composes with
    the tier -- a thumbnail at any tier simply omits the dim-label pass.

    fid: frame id. age_yr: catalog age. radius_arcsec: navigation match radius.
    overlay: one of "none"|"detected"|"identified"|"nav" (unknown -> "nav").
    Returns: PNG bytes. Raises KeyError if the id is unknown.
    """
    rec = _record_by_id(fid)
    if rec is None:
        raise KeyError(fid)
    if overlay not in _OVERLAY_TIERS:
        overlay = "nav"
    draw_circles = overlay in ("detected", "identified", "nav")
    draw_dim = overlay in ("identified", "nav")
    draw_amber = overlay == "nav"

    image = rec["image"]
    xy = rec["centroids"]["xy"]
    flux = rec["centroids"]["flux"]

    # Position-capable (navigation) matches -- demo frames on the frozen 20-pc.
    # Only computed when a tier actually needs them (identified needs the
    # position_capable flags + the identified count; nav also draws the crosses).
    # "none"/"detected" skip the catalog load entirely.
    nav = []
    nav_cat = None
    nav_dist_au = None
    position_capable_ids = set()
    nav_centroids = set()
    if draw_dim or draw_amber:
        nav_cat = load_aged_catalog(
            _nav_catalog_path(rec.get("is_demo", False)),
            age_yr,
            rv_fill_kms=DEFAULT_RV_FILL_KMS,
        )
        nav = identify_in_frame(
            rec["plate"], xy, nav_cat["positions_au"], radius_arcsec
        )
        nav_dist_au = np.linalg.norm(nav_cat["positions_au"], axis=1)
        position_capable_ids = {int(nav_cat["source_id"][m["star_index"]]) for m in nav}
        nav_centroids = {m["centroid_index"] for m in nav}

    labels = []
    identified_centroids = set(nav_centroids)
    if full_labels and draw_dim:
        # Deep-identify tier: prefer a cached full-depth Gaia cone (labels almost
        # every dot). allow_fetch=False so a render never blocks on the network;
        # a missing cone falls back to the nearby-catalog labels.
        cone = gaiacone.cone_catalog(rec["plate"], allow_fetch=False)
        if cone is not None:
            labels = cone_label_set(rec["plate"], xy, cone, position_capable_ids)
        else:
            wide_cat, _ = labeling_catalog(age_yr, DEFAULT_RV_FILL_KMS)
            labels = crossmatch_labels(rec["plate"], xy, wide_cat, position_capable_ids)
        identified_centroids |= {lab["centroid_index"] for lab in labels}

    fig = plt.figure(figsize=(6.4, 6.4), dpi=110)
    fig.patch.set_facecolor(_FACE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(_FACE)
    bg = np.median(image)
    ax.imshow(np.log1p(np.clip(image - bg, 0, None)), origin="lower", cmap="gray")
    if draw_circles and xy.shape[0]:
        ax.scatter(
            xy[:, 0],
            xy[:, 1],
            s=70,
            facecolors="none",
            edgecolors=_CYAN,
            linewidths=1.1,
        )

    # Dim labels for identified-but-not-navigable stars (cap 25 by flux). Cone
    # labels carry ready "text" (name / "N pc" / "G mag"); the nearby-catalog
    # fallback has only dist_pc, so format that. A None text draws no label.
    dim = [lab for lab in labels if lab["centroid_index"] not in nav_centroids]
    dim.sort(key=lambda lab: -float(flux[lab["centroid_index"]]))
    for lab in dim[:25]:
        txt = lab.get("text")
        if txt is None and lab.get("dist_pc") is not None:
            txt = f"{lab['dist_pc']:.0f} pc"
        if not txt:
            continue
        cx, cy = xy[lab["centroid_index"]]
        ax.annotate(
            txt,
            (cx, cy),
            color=_MUTED,
            fontsize=7,
            xytext=(5, 4),
            textcoords="offset points",
        )

    # Amber crosses + name + distance for the position-capable nearby stars.
    if draw_amber:
        for m in nav:
            sid = int(nav_cat["source_id"][m["star_index"]])
            cx, cy = xy[m["centroid_index"]]
            name = STAR_NAMES.get(sid, str(sid))
            d_pc = float(nav_dist_au[m["star_index"]] / AU_PER_PC)
            ax.plot(cx, cy, "+", color=_AMBER, ms=16, mew=2.2)
            ax.annotate(
                f"{name} ({d_pc:.2g} pc)",
                (cx, cy),
                color=_AMBER,
                fontsize=11,
                fontweight="bold",
                xytext=(8, 8),
                textcoords="offset points",
            )

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(_LINE)
    # Title reports only what the chosen tier actually annotated -- "none" shows
    # no counts (they would imply annotation on a raw photo).
    n_det = xy.shape[0]
    if overlay == "none":
        title = f"{rec['name']}  -  raw image (log-stretched)"
    elif overlay == "detected":
        title = f"{rec['name']}  -  {n_det} detected"
    elif overlay == "identified":
        title = (
            f"{rec['name']}  -  {n_det} detected, "
            f"{len(identified_centroids)} identified"
        )
    else:  # nav
        title = (
            f"{rec['name']}  -  {n_det} detected, {len(identified_centroids)} "
            f"identified, {len(nav_centroids)} position-capable"
        )
    ax.set_title(title, color=_DIM, fontsize=9.5, fontfamily="monospace")
    fig.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _lines_for(ids, age_yr, radius_arcsec, rv_kms, catalog_override=None):
    """Build lines of position across the given frames at one catalog age.

    Catalog choice: if catalog_override is given, that file is used (the age scan
    passes the frozen 20-pc nearby file, because a position fix is a NEARBY-star
    technique -- using the dense widest catalog would let a deep field spuriously
    match two far stars within the radius and fake a fix). Otherwise: if EVERY
    selected frame is a demo (known-JPL) frame, the frozen 20-pc file keeps the
    blessed fix byte-reproducible; if any frame is uploaded, the widest usable
    catalog is used. Returns (lines, all_demo) -- all_demo gates the miss-vs-JPL
    computation in locate_payload.
    """
    recs = [(fid, _record_by_id(fid)) for fid in ids]
    all_demo = all(
        rec is not None and rec.get("is_demo") for _, rec in recs if rec is not None
    ) and any(rec is not None for _, rec in recs)
    if catalog_override is not None:
        cat = load_aged_catalog(str(catalog_override), age_yr, rv_fill_kms=rv_kms)
    elif all_demo:
        cat = load_aged_catalog(str(CATALOG_CSV), age_yr, rv_fill_kms=rv_kms)
    else:
        cat, _ = labeling_catalog(age_yr, rv_kms)
    lines = []
    for fid, rec in recs:
        if rec is None:
            continue
        for m in identify_in_frame(
            rec["plate"], rec["centroids"]["xy"], cat["positions_au"], radius_arcsec
        ):
            si = m["star_index"]
            cxy = rec["centroids"]["xy"][m["centroid_index"]]
            ln = LineOfPosition(
                star_pos_au=cat["positions_au"][si],
                direction_unit=measured_direction(rec["plate"], cxy),
                star_source_id=int(cat["source_id"][si]),
                sep_arcsec=m["sep_arcsec"],
                image_name=rec["name"],
            )
            # The centroid pixel is not a LineOfPosition field, but the drawing
            # endpoints (/api/locate, /api/pipeline) need it; attach it here (the
            # dataclass has no __slots__, so an extra attribute is harmless and
            # line_of_position_summary/fix_position ignore it).
            ln.centroid_xy = [float(cxy[0]), float(cxy[1])]
            lines.append(ln)
    return lines, all_demo


def _line_json(ln):
    """A line of position as a drawing-grade JSON dict.

    Keeps the original reporting keys (star_name, image, resid_arcsec) and adds
    the geometry a renderer needs: the star id, the centroid pixel, the measured
    unit sightline, the star's aged barycentric position (au), and the raw
    identification separation (arcsec).
    """
    return {
        "star_name": STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id)),
        "image": ln.image_name,
        "resid_arcsec": round(ln.sep_arcsec, 2),
        "source_id": int(ln.star_source_id),
        "centroid_xy": [float(v) for v in ln.centroid_xy],
        "direction_unit": [float(v) for v in ln.direction_unit],
        "star_pos_au": [float(v) for v in ln.star_pos_au],
        "sep_arcsec": float(ln.sep_arcsec),
    }


# Threshold on OBSERVER DISPLACEMENT, not just calendar spread. A single-point
# fix assumes one observer at one instant; Earth moves ~6.28 au/yr, so a baseline
# of ~0.1 au (about the point where different-epoch lines stop crossing cleanly)
# is reached in 0.1 au / 6.28 au/yr ~= 0.016 yr. We round to 0.02 yr: it flags
# Earth-rate uploads a few days apart AND the decades-apart DSS/HST plates, while
# the real New Horizons campaign (measured span 0.0032 yr = 1.2 days, one instant)
# stays silent with 6x margin. (0.2 yr, the first pass, was observer-agnostic and
# silently passed a 1.26 au Earth baseline.)
_EPOCH_SPAN_WARN_YR = 0.02


def _epoch_span_warning(ids):
    """A plain-English warning if the selected frames were taken at spread-out
    epochs, else None.

    A single-point position fix assumes ONE observer at ONE instant. Frames
    taken apart in time are different observers at different places, so their
    lines of position do not cross at a real point -- the fix comes back as a
    nonsense |r| (measured 22-35 au on mixed-era DSS/HST groups). The AGE
    estimate is unaffected (each frame still dates itself), so we steer the user
    there instead of hiding the hazard. Span is max-min of obs_age_yr (yr since
    J2016.0) across the selection; the threshold is an Earth-displacement budget
    (see _EPOCH_SPAN_WARN_YR).
    """
    epochs = [
        rec["obs_age_yr"] for fid in ids if (rec := _record_by_id(fid)) is not None
    ]
    if len(epochs) < 2:
        return None
    span = float(max(epochs) - min(epochs))
    if span <= _EPOCH_SPAN_WARN_YR:
        return None
    return (
        f"frames span {span:.1f} yr - observers at different epochs; the position "
        f"fix is not meaningful, use the age estimate."
    )


def locate_payload(ids, age_yr, radius_arcsec, rv_kms):
    """Fix the spacecraft from the selected frames. Never raises to the caller.

    Returns a JSON-ready dict: on success {ok:True, x_au, r_au, r_pc,
    ellipsoid_au, chi2, n_lines, distinct_stars, lines:[{star_name, image,
    resid_arcsec, source_id, centroid_xy, direction_unit, star_pos_au,
    sep_arcsec}], miss_au (or None), truth_x_au (only when miss_au is non-null),
    warning (or None), message:""}.

    On a degenerate geometry, {ok:False, message, n_lines, warning}. When the
    failure is exactly the ONE-nearby-star case (one line, or several lines of
    the SAME star), the result additionally carries mode:"line" and a drawable
    line-of-position (lop:{...}) -- the fix is still ok:False (one star is a line,
    not a point) but the web layer can DRAW that line. Zero lines stays a plain
    error (nothing to draw).
    """
    lines, all_demo = _lines_for(ids, age_yr, radius_arcsec, rv_kms)
    warning = _epoch_span_warning(ids)
    try:
        fix = fix_position(lines, rmssig_arcsec=RMSSIG_ARCSEC)
    except ValueError as exc:
        out = {
            "ok": False,
            "message": str(exc),
            "n_lines": len(lines),
            "warning": warning,
        }
        # One nearby star (>=1 line, all from a single source id) IS a line of
        # position -- degenerate for a point fix, but drawable. Zero lines is not.
        distinct = {ln.star_source_id for ln in lines}
        if lines and len(distinct) == 1:
            lop = line_of_position_summary(lines)
            lop["star_name"] = STAR_NAMES.get(lop["source_id"], str(lop["source_id"]))
            out["mode"] = "line"
            out["lop"] = lop
        return out
    x = fix["x_au"]
    r_au = float(np.linalg.norm(x))
    miss = float(np.linalg.norm(x - NEWH_X_JPL)) if all_demo else None
    out = {
        "ok": True,
        "x_au": [float(v) for v in x],
        "r_au": r_au,
        "r_pc": r_au / AU_PER_PC,
        "ellipsoid_au": [float(v) for v in fix["ellipsoid_au"]],
        "chi2": fix["chi2"],
        "n_lines": fix["n_lines"],
        "distinct_stars": fix["distinct_stars"],
        "lines": [_line_json(ln) for ln in lines],
        "miss_au": miss,
        "warning": warning,
        "message": "",
    }
    # The JPL truth vector rides along only for the known-demo sets (where miss is
    # meaningful), so a renderer can draw truth-vs-fix without a second request.
    if miss is not None:
        out["truth_x_au"] = [float(v) for v in NEWH_X_JPL]
    return out


def pipeline_payload(fid, age_yr, radius_arcsec, rv_kms=DEFAULT_RV_FILL_KMS):
    """Per-frame pipeline data for the step-by-step visualization pages.

    One JSON blob exposing each stage's output for ONE frame, reusing the exact
    machinery the renderer and locator use (no new geometry): every detected
    centroid, the per-dot IDENTIFICATION matches (deep Gaia cone if cached, else
    the widest labeling catalog -- same choice render_frame_png makes), and the
    enriched 120-arcsec navigation LINES for this frame.

    Returns {ok:True, id, name, centroids:[[x,y],...], matches:[{centroid_index,
    source_id, name, dist_pc, position_capable, sep_arcsec}, ...], lines:[<the
    _line_json shape>]} or {ok:False, message} for an unknown id.
    """
    rec = _record_by_id(fid)
    if rec is None:
        return {
            "ok": False,
            "message": f"unknown frame id {fid!r} -- not a demo frame or an "
            "uploaded image.",
        }
    xy = rec["centroids"]["xy"]
    # Navigation lines for this frame -- the same builder locate_payload uses; its
    # source ids are exactly the position-capable set for the identification tier.
    lines, _ = _lines_for([fid], age_yr, radius_arcsec, rv_kms)
    position_capable_ids = {ln.star_source_id for ln in lines}
    # Identification tier: cached deep cone first, else the widest labeling catalog.
    cone = gaiacone.cone_catalog(rec["plate"], allow_fetch=False)
    if cone is not None:
        labels = cone_label_set(rec["plate"], xy, cone, position_capable_ids)
    else:
        wide_cat, _ = labeling_catalog(age_yr, rv_kms or DEFAULT_RV_FILL_KMS)
        labels = crossmatch_labels(rec["plate"], xy, wide_cat, position_capable_ids)
    # NAVIGATION MATCHES FIRST. The label tiers above match STATIC catalog/cone
    # positions tightly, so a fast-moving nav star -- displaced by exactly the
    # parallax/drift signal we navigate on (Proxima sits ~31.9 arcsec from its
    # static cone spot) -- never appears in them. The nav identify (the lines)
    # is the honest source for position-capable rows: merge it in, first, with
    # its real separation. Found live in a browser (page 3 claimed '0
    # position-capable' on the Proxima frame), pinned by test.
    au_per_pc = 206264.806

    def _nearest_centroid_index(cxy):
        d2 = ((xy - np.asarray(cxy, dtype=float)) ** 2).sum(axis=1)
        return int(np.argmin(d2))

    # source_id is a STRING everywhere in THIS payload: Gaia ids exceed
    # float64's 53-bit exact-integer window, and the browser's JSON.parse
    # silently rounds them (measured: ...387072 rendered as ...387000 in the
    # page tables). /api/locate keeps ints -- nothing displays them raw there.
    nav_rows = [
        {
            "centroid_index": _nearest_centroid_index(ln.centroid_xy),
            "source_id": str(int(ln.star_source_id)),
            "name": STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id)),
            "dist_pc": round(float(np.linalg.norm(ln.star_pos_au)) / au_per_pc, 2),
            "position_capable": True,
            "sep_arcsec": round(float(ln.sep_arcsec), 2),
        }
        for ln in sorted(lines, key=lambda ln: float(ln.sep_arcsec))
    ]
    nav_ids = {r["source_id"] for r in nav_rows}
    matches = nav_rows + [
        {
            "centroid_index": lab["centroid_index"],
            "source_id": str(int(lab["source_id"])),
            "name": lab["name"],
            "dist_pc": lab["dist_pc"],
            "position_capable": bool(lab["position_capable"]),
            "sep_arcsec": lab["sep_arcsec"],
        }
        for lab in labels
        if str(int(lab["source_id"])) not in nav_ids
    ]
    return {
        "ok": True,
        "id": fid,
        "name": rec["name"],
        "centroids": [[float(x), float(y)] for x, y in xy],
        "matches": matches,
        "lines": [
            {**_line_json(ln), "source_id": str(int(ln.star_source_id))} for ln in lines
        ],
    }


DRIFT_GRID = (-75.0, 25.0, 0.1)  # default single-star-drift scan (yr since J2016.0)
# 0.1 yr, NOT 0.5: a fast mover's true minimum is SHARP (Wolf 359's V is ~0.6 yr
# wide), and a 0.5-yr grid under-samples the true bottom while the broad false
# minima are well-sampled -- the recorded Wolf'95 "sparse-field" miss was really
# this grid-undersampling (0.5 -> 0.1 recovers 1991.4 -> 1995.2 with no other
# regression). drift_date's linear-propagation model keeps a 1000-node scan ~2 s.
J2016_YEAR = 2016.0  # calendar year of the catalog epoch


def age_payload(ids, radius_arcsec, rv_kms, age_min, age_max, age_step):
    """Estimate the image epoch, choosing the estimator automatically.

    POSITION-FIT mode (>= 2 distinct nearby stars, e.g. the New Horizons set):
    the chi2-of-fix vs age scan (estimate_age) over the requested grid. If the
    fix can never run (fewer than 2 distinct position-capable stars -- e.g. one
    old plate showing a single nearby star), fall back to SINGLE-STAR DRIFT mode
    (drift_date) over a wide grid reaching back decades (default -75..+25 yr),
    which reaches the plate epochs. "mode" reports which ran; "year_hat"
    (2016.0 + age) is the calendar year the image was taken.

    Returns: {ok, mode, age_hat_yr, year_hat, sigma_age_yr, ages, chi2s,
    curve_label, best_sep_arcsec, note, truth_yr} or {ok:False, message}.
    """
    grid = np.arange(age_min, age_max + 1e-9, age_step)
    if grid.size < 3:
        return {"ok": False, "message": "age grid needs at least 3 points"}
    truth = [
        _record_by_id(fid)["obs_age_yr"]
        for fid in ids
        if _record_by_id(fid) is not None
    ]
    truth_yr = float(np.mean(truth)) if truth else None

    # Try the position fix first: it succeeds (some chi2 is finite) only if the
    # frames ever yield >= 2 distinct crossing lines of position.
    try:
        res = estimate_age(
            lambda a: _lines_for(
                ids, a, radius_arcsec, rv_kms, catalog_override=CATALOG_CSV
            )[0],
            grid,
            rmssig_arcsec=RMSSIG_ARCSEC,
        )
    except ValueError:
        res = None
    if res is not None and np.any(np.isfinite(res["chi2s"])):
        chi2s = [None if not np.isfinite(c) else float(c) for c in res["chi2s"]]
        age_hat = res["age_hat_yr"]
        return {
            "ok": True,
            "mode": "position-fit",
            "age_hat_yr": age_hat,
            "year_hat": J2016_YEAR + age_hat,
            "sigma_age_yr": None
            if np.isnan(res["sigma_age_yr"])
            else res["sigma_age_yr"],
            "ages": [float(a) for a in res["ages"]],
            "chi2s": chi2s,
            "curve_label": "chi2 of fix",
            "best_sep_arcsec": None,
            "note": res.get("note", ""),
            "truth_yr": truth_yr,
        }

    # Single-star drift dating. Scans a wide (default -75..+25 yr) grid unless the
    # caller already asked for negatives. Uses the frozen 20-pc catalog -- the
    # high-proper-motion nearby stars that can date a plate all live there.
    # Drift always scans at a FINE step (<= 0.1 yr) so the sharp true minimum is
    # resolved -- the user's step was chosen for the position-fit scan and may be
    # too coarse. Range is the user's if they asked for negatives, else the wide
    # default that reaches the old-plate epochs.
    if age_min < 0:
        lo, hi, step = age_min, age_max, min(age_step, DRIFT_GRID[2])
    else:
        lo, hi, step = DRIFT_GRID
    dgrid = np.arange(lo, hi + 1e-9, step)
    frames = [
        (rec["plate"], rec["centroids"]["xy"], rec["name"])
        for fid in ids
        if (rec := _record_by_id(fid)) is not None
    ]
    d = drift_date(
        frames,
        dgrid,
        lambda a: load_aged_catalog(
            str(CATALOG_CSV), a, rv_fill_kms=rv_kms or DEFAULT_RV_FILL_KMS
        ),
        cone_fn=lambda p: gaiacone.cone_catalog(p, allow_fetch=False),
    )
    if not d["ok"]:
        return {"ok": False, "message": d["message"]}
    age_hat = d["age_hat_yr"]
    sep = [None if not np.isfinite(s) else float(s) for s in d["sep_arcsec"]]
    return {
        "ok": True,
        "mode": "single-star drift",
        "age_hat_yr": age_hat,
        "year_hat": J2016_YEAR + age_hat,
        "sigma_age_yr": None if np.isnan(d["sigma_age_yr"]) else d["sigma_age_yr"],
        "ages": [float(a) for a in d["ages"]],
        "chi2s": sep,
        "curve_label": "separation (arcsec)",
        "best_sep_arcsec": d["best_sep_arcsec"],
        "note": d.get("note", ""),
        "truth_yr": truth_yr,
    }


# --- upload -----------------------------------------------------------------
def _parse_multipart(body, content_type):
    """Extract (filename, file_bytes) from a multipart/form-data body.

    Minimal hand-rolled parser (cgi.FieldStorage was removed in Python 3.13):
    finds the boundary, walks the parts, returns the first part with a filename.
    Returns (None, None) if no file part is present.
    """
    m = re.search(r"boundary=([^;]+)", content_type or "")
    if not m:
        return None, None
    delim = ("--" + m.group(1).strip().strip('"')).encode()
    for part in body.split(delim):
        header_blob, sep, data = part.partition(b"\r\n\r\n")
        if not sep or b"filename=" not in header_blob:
            continue
        fn = re.search(rb'filename="([^"]*)"', header_blob)
        filename = fn.group(1).decode("utf-8", "replace") if fn else "upload"
        if not filename:
            continue
        return filename, data.rstrip(b"\r\n")
    return None, None


def _upload_result(uid, duplicate):
    """The success dict for an uploaded record (fresh or a dedup hit)."""
    rec = _UPLOADS[uid]
    return {
        "ok": True,
        "id": uid,
        "name": rec["name"],
        "field": "uploaded",
        "obs_age_yr": round(rec.get("obs_age_yr", 0.0), 4),
        "duplicate": duplicate,
    }


def handle_upload(filename, data_bytes, api_key=None):
    """Save an uploaded image, plate-solve it, and add it to the gallery.

    Deduplicates by content hash: re-uploading identical bytes returns the
    EXISTING record with duplicate:True (no re-solve, no new id) instead of
    growing _UPLOADS forever. A fresh upload returns duplicate:False.

    Returns {ok:True, id, name, field, obs_age_yr, duplicate} on success, else
    {ok:False, message:<friendly multi-backend error>}.
    """
    import tempfile

    # Dedup BEFORE the (expensive) solve: identical bytes -> the existing record.
    digest = hashlib.sha256(data_bytes).hexdigest()
    seen = _UPLOAD_HASHES.get(digest)
    if seen is not None and seen in _UPLOADS:
        return _upload_result(seen, duplicate=True)

    suffix = Path(filename).suffix or ".fits"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "upload" + suffix)
        with open(path, "wb") as fh:
            fh.write(data_bytes)
        try:
            plate = solve_image(path, api_key=api_key)
            image = load_grayscale(path)
        except Exception as exc:  # noqa: BLE001 -- surface the friendly reason
            return {"ok": False, "message": str(exc)}
        jd = observation_jd(path)
        try:
            field, sid = _classify_field(plate)
        except Exception:  # noqa: BLE001
            field, sid = "uploaded", None
        _UPLOAD_N[0] += 1
        uid = f"up_{_UPLOAD_N[0]}"
        _UPLOADS[uid] = {
            "id": uid,
            "name": Path(filename).name,
            "plate": plate,
            "image": image,
            "centroids": find_centroids(image),
            "field": "uploaded",
            "sid": sid,
            "obs_age_yr": age_yr_since_j2016(jd) if jd else 0.0,
            "is_demo": False,
        }
        _UPLOAD_HASHES[digest] = uid
    return _upload_result(uid, duplicate=False)


def remove_upload(uid):
    """Remove an uploaded frame (and its dedup entry) from the gallery.

    Refuses to remove a built-in demo frame or an unknown id, with a plain-English
    reason. Returns {ok:True} on success, else {ok:False, message}.
    """
    _ensure_demo_index()
    if uid in _DEMO_INDEX:
        return {
            "ok": False,
            "message": f"{uid!r} is a built-in demo frame and cannot be removed.",
        }
    rec = _UPLOADS.pop(uid, None)
    if rec is None:
        return {"ok": False, "message": f"no uploaded image with id {uid!r} to remove."}
    for digest, mapped in list(_UPLOAD_HASHES.items()):
        if mapped == uid:
            _UPLOAD_HASHES.pop(digest, None)
    return {"ok": True}


def solver_status():
    """Report whether the offline blind solver is ready (do.txt item 6).

    wsl_solver: `solve-field` is on PATH inside WSL (probe cached per process,
        overridable in tests via _WSL_SOLVER_CACHE).
    wsl_config: the GalNav astrometry config exists in WSL (platesolve's cached
        probe -- lists the wide Tycho-2 + narrow LITE indexes).
    index_files: count of index-*.fits under ASTROMETRY_INDEX_DIR (0 if missing).
    """
    return {
        "ok": True,
        "wsl_solver": _wsl_solver_available(),
        "wsl_config": bool(_wsl_has_galnav_config()),
        "index_files": _count_index_files(),
    }


def _wsl_solver_available():
    """WSL blind-solver presence, probed once per process (see _WSL_SOLVER_CACHE)."""
    global _WSL_SOLVER_CACHE
    if _WSL_SOLVER_CACHE is None:
        _WSL_SOLVER_CACHE = bool(_wsl_available())
    return _WSL_SOLVER_CACHE


def _count_index_files():
    """How many index-*.fits blind-solve indexes are installed (0 if dir absent)."""
    if not ASTROMETRY_INDEX_DIR.is_dir():
        return 0
    return len(glob.glob(str(ASTROMETRY_INDEX_DIR / "index-*.fits")))


# --- OpenSpace live bridge (the pipeline's viewer/visualiser) ---------------
def openspace_status():
    """Whether a local OpenSpace is reachable -- a cheap boolean the UI turns
    into a connected/not-running chip. Never raises."""
    return {"ok": True, "running": bool(openspace_link.is_running())}


def _os_not_running():
    return {
        "ok": False,
        "message": "OpenSpace isn't running (nothing on 127.0.0.1:4681). Start "
        "OpenSpace on this machine, then this button works.",
    }


def _os_push(script, pushed, note):
    """Run one live push and shape the response; honest at every level. The
    engine's measured reply frame separates EXECUTED / chunk-FAILED / no-reply
    (gui.openspace_link.run_lua_confirmed), and the response says which."""
    status = openspace_link.run_lua_confirmed(script)
    if status == "failed":
        return {
            "ok": False,
            "message": "OpenSpace replied but the marker Lua did not execute -- "
            "check the OpenSpace log.",
        }
    if status in ("confirmed", "sent"):
        return {
            "ok": True,
            "pushed": pushed,
            "note": note,
            "confirmed": status == "confirmed",
        }
    return {
        "ok": False,
        "message": "OpenSpace is running but the marker push failed -- check the "
        "OpenSpace log.",
    }


def _line_segments(lines):
    """LineOfPosition objects -> the drawing dicts openspace_link.lines_lua wants."""
    return [
        {
            "star_name": STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id)),
            "star_pos_au": [float(v) for v in ln.star_pos_au],
            "direction_unit": [float(v) for v in ln.direction_unit],
        }
        for ln in lines
    ]


def openspace_show(stage, ids, age_yr, radius_arcsec, rv_kms):
    """Push one pipeline stage into a running OpenSpace. Never raises.

    stage: "stars" | "lines" | "fix" | "clear". The geometry is built with the
    SAME machinery /api/pipeline and /api/locate use (no new physics) and turned
    into a GalNavLive* Lua push by gui.openspace_link. Returns
    {ok:True, pushed:[node identifiers], note} on success, or
    {ok:False, message} when OpenSpace is not running or the push fails. The
    one-nearby-star case in the fix stage draws the line of position instead of a
    point and says so (do.txt item 9).
    """
    if not openspace_link.is_running():
        return _os_not_running()

    if stage == "clear":
        return _os_push(openspace_link.clear_lua(), [], "cleared GalNav markers")

    lines, _ = _lines_for(ids, age_yr, radius_arcsec, rv_kms)

    if stage == "stars":
        seen, stars = set(), []
        for ln in lines:
            if ln.star_source_id in seen:
                continue
            seen.add(ln.star_source_id)
            stars.append(
                {
                    "name": STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id)),
                    "star_pos_au": [float(v) for v in ln.star_pos_au],
                }
            )
        if not stars:
            return {
                "ok": False,
                "message": "no position-capable stars in this selection to show.",
            }
        tex = openspace_link.ensure_marker_textures()
        script = openspace_link.stars_lua(stars, texture=tex["amber"])
        return _os_push(
            script,
            openspace_link.star_node_ids(len(stars)),
            f"placed {len(stars)} star marker(s) at their catalog distances.",
        )

    if stage == "lines":
        segs = _line_segments(lines)
        if not segs:
            return {
                "ok": False,
                "message": "no lines of position in this selection to show.",
            }
        return _os_push(
            openspace_link.lines_lua(segs),
            openspace_link.line_node_ids(len(segs)),
            f"drew {len(segs)} line(s) of position toward the observer.",
        )

    if stage == "fix":
        loc = locate_payload(ids, age_yr, radius_arcsec, rv_kms)
        if loc["ok"]:
            truth = loc.get("truth_x_au")
            tex = openspace_link.ensure_marker_textures()
            script = openspace_link.fix_lua(
                loc["x_au"],
                truth_au=truth,
                texture_amber=tex["amber"],
                texture_cyan=tex["cyan"],
            )
            if loc.get("miss_au") is not None:
                note = f"fix placed; miss vs JPL truth {loc['miss_au']:.3f} au (white line)."
            else:
                note = "fix placed."
            return _os_push(
                script, openspace_link.fix_node_ids(with_truth=truth is not None), note
            )
        # Degenerate: one nearby star (or several of the same star) is a LINE, not
        # a point -- draw that line of position instead, and say so.
        if lines:
            return _os_push(
                openspace_link.lines_lua(_line_segments(lines)),
                openspace_link.line_node_ids(len(lines)),
                "one nearby star pins a LINE, not a point -- drew the line of "
                "position instead. Add a second, different nearby star to fix a point.",
            )
        return {"ok": False, "message": loc["message"]}

    return {"ok": False, "message": f"unknown OpenSpace stage {stage!r}"}


# --- HTTP layer (thin) ------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    server_version = "GalNavWeb/1.0"
    # Per-connection socket timeout (seconds). Without it a slowloris client --
    # a big Content-Length header followed by a trickle of body bytes -- pins a
    # worker thread forever. socketserver arms this on the request socket and the
    # resulting socket.timeout is already swallowed by the do_* try/except.
    timeout = 30

    def log_message(self, *args):  # keep the console quiet
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(
            code, "application/json; charset=utf-8", json.dumps(obj).encode("utf-8")
        )

    def _query(self):
        return parse_qs(urlparse(self.path).query)

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        route = urlparse(self.path).path
        try:
            if route == "/":
                self._send(
                    200,
                    "text/html; charset=utf-8",
                    (WEB_DIR / "index.html").read_bytes(),
                )
            elif route == "/favicon.ico":
                self._send(204, "image/x-icon", b"")  # silence the browser 404
            elif route.startswith("/static/"):
                got = static_file(route[len("/static/") :])
                if got is None:
                    self._send(404, "text/plain; charset=utf-8", b"not found")
                else:
                    self._send(200, got[0], got[1])
            elif route == "/api/frames":
                self._json(frames_payload())
            elif route == "/api/image":
                q = self._query()
                fid = q.get("id", [""])[0]
                age = float(q.get("age", ["4.31"])[0])
                radius = float(q.get("radius", ["120"])[0])
                # thumb=1 -> skip the deep-identify catalog load (fast). overlay
                # picks the annotation tier; unknown values fall back to "nav".
                full = q.get("thumb", ["0"])[0] not in ("1", "true")
                overlay = q.get("overlay", ["nav"])[0]
                self._send(
                    200,
                    "image/png",
                    render_frame_png(
                        fid, age, radius, full_labels=full, overlay=overlay
                    ),
                )
            elif route == "/api/pipeline":
                q = self._query()
                fid = q.get("id", [""])[0]
                age = float(q.get("age", ["4.31"])[0])
                radius = float(q.get("radius", ["120"])[0])
                self._json(pipeline_payload(fid, age, radius))
            elif route == "/api/solver_status":
                self._json(solver_status())
            elif route == "/api/openspace/status":
                self._json(openspace_status())
            else:
                self._json({"ok": False, "message": "unknown route"}, 404)
        except Exception as exc:  # noqa: BLE001 -- never leak a stack trace
            self._json({"ok": False, "message": str(exc)}, 200)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            if route == "/api/locate":
                b = json.loads(self._read_body() or b"{}")
                self._json(
                    locate_payload(
                        b.get("ids", []),
                        float(b.get("age", 4.31)),
                        float(b.get("radius", 120)),
                        float(b.get("rv", 0.0)),
                    )
                )
            elif route == "/api/estimate_age":
                b = json.loads(self._read_body() or b"{}")
                self._json(
                    age_payload(
                        b.get("ids", []),
                        float(b.get("radius", 120)),
                        float(b.get("rv", 0.0)),
                        float(b.get("min", 0.0)),
                        float(b.get("max", 25.0)),
                        float(b.get("step", 0.25)),
                    )
                )
            elif route == "/api/upload":
                api_key = (
                    self.headers.get("X-Api-Key")
                    or self._query().get("api_key", [None])[0]
                )
                filename, data = _parse_multipart(
                    self._read_body(), self.headers.get("Content-Type", "")
                )
                if not filename:
                    self._json({"ok": False, "message": "no file in upload"})
                    return
                self._json(handle_upload(filename, data, api_key=api_key))
            elif route == "/api/remove_upload":
                b = json.loads(self._read_body() or b"{}")
                self._json(remove_upload(b.get("id", "")))
            elif route == "/api/openspace/show":
                b = json.loads(self._read_body() or b"{}")
                self._json(
                    openspace_show(
                        b.get("stage", ""),
                        b.get("ids", []),
                        float(b.get("age", 4.31)),
                        float(b.get("radius", 120)),
                        float(b.get("rv", DEFAULT_RV_FILL_KMS)),
                    )
                )
            else:
                self._json({"ok": False, "message": "unknown route"}, 404)
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "message": str(exc)}, 200)


def create_server(host="127.0.0.1", start_port=8000):
    """Bind a ThreadingHTTPServer on the first free port >= start_port.

    start_port=0 binds an OS-assigned free port (used by the offline self-test).
    Returns the server (already listening; call serve_forever()).
    """
    port = start_port
    for _ in range(500):
        try:
            return ThreadingHTTPServer((host, port), _Handler)
        except OSError:
            if start_port == 0:
                raise
            port += 1
    raise RuntimeError(f"no free port found from {start_port}")


def main():
    """Start the server, open the browser, and serve until Ctrl+C."""
    server = create_server()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    print(f"GalNav web demo running -> {url}   (Ctrl+C to stop)", flush=True)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 -- headless: no browser, server still runs
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
