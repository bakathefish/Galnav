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

from gui import gaiacone
from gui.age import estimate_age
from gui.app import CATALOG_CSV, STAR_NAMES, load_grayscale
from gui.centroids import find_centroids
from gui.fitsmeta import age_yr_since_j2016, observation_jd
from gui.locate import (
    LineOfPosition,
    fix_position,
    identify_in_frame,
    load_aged_catalog,
    measured_direction,
)
from gui.platesolve import fits_header_solution, solve_image

REPO_ROOT = Path(__file__).resolve().parent.parent
NH_DIR = REPO_ROOT / "data" / "e3_new_horizons" / "repo"
WEB_DIR = Path(__file__).resolve().parent / "web"

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

# UI palette (matches docs/PIPELINE-FLOWCHART.html dark theme).
_FACE = "#0a0e16"
_CYAN = "#3fcbef"
_AMBER = "#f2b444"
_DIM = "#93a6bf"
_MUTED = "#6f7f96"  # dim distance labels for identified-but-not-navigable stars
_LINE = "#263248"

# Static files the /static/ route is allowed to serve (no path traversal).
_STATIC_ALLOW = {
    "app.js": "application/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
}

# --- frame cache ------------------------------------------------------------
_DEMO_INDEX = {}  # "f<n>" -> path
_CACHE = {}  # path -> record dict
_UPLOADS = {}  # "up_<n>" -> record dict
_UPLOAD_N = [0]


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

    The ONLY guard for the /static/ route: rejects any name not in the explicit
    allowlist or containing a path separator or "..", so no traversal is
    possible. Used directly by the handler AND by the tests.
    """
    if name not in _STATIC_ALLOW or "/" in name or "\\" in name or ".." in name:
        return None
    return _STATIC_ALLOW[name], (WEB_DIR / name).read_bytes()


def frames_payload():
    """Metadata for the gallery: the 12 demo frames plus any uploads.

    Returns: list of {id, name, field, obs_age_yr}.
    """
    _ensure_demo_index()
    out = []
    for fid, path in _DEMO_INDEX.items():
        rec = _demo_record(fid, path)
        out.append(
            {
                "id": fid,
                "name": rec["name"],
                "field": rec["field"],
                "obs_age_yr": round(rec["obs_age_yr"], 4),
            }
        )
    for uid, rec in _UPLOADS.items():
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
    Returns: list of {centroid_index, source_id, dist_pc, name, position_capable}.
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
        position_capable, text}. text may be None (marker only).
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
            }
        )
    return out


def render_frame_png(fid, age_yr, radius_arcsec, full_labels=True):
    """Render one frame log-stretched with detections + identified stars.

    Every centroid is a cyan circle (detected). Position-capable nearby stars
    (the 120-arcsec navigation matches) get the big amber cross + name + distance.
    When full_labels is True, every OTHER star we can IDENTIFY against the widest
    catalog gets a small muted distance label ("212 pc") -- visually secondary,
    the pedagogical point being that we know what many dots ARE, yet only the
    amber ones are close enough for their parallax to reveal position. Dim labels
    are capped at the 25 brightest for readability; the caption reports the full
    counts. full_labels is set False for gallery thumbnails (fast: nav only).

    fid: frame id. age_yr: catalog age. radius_arcsec: navigation match radius.
    Returns: PNG bytes. Raises KeyError if the id is unknown.
    """
    rec = _record_by_id(fid)
    if rec is None:
        raise KeyError(fid)
    image = rec["image"]
    xy = rec["centroids"]["xy"]
    flux = rec["centroids"]["flux"]

    # Position-capable (navigation) matches -- demo frames on the frozen 20-pc.
    nav_cat = load_aged_catalog(
        _nav_catalog_path(rec.get("is_demo", False)),
        age_yr,
        rv_fill_kms=DEFAULT_RV_FILL_KMS,
    )
    nav = identify_in_frame(rec["plate"], xy, nav_cat["positions_au"], radius_arcsec)
    nav_dist_au = np.linalg.norm(nav_cat["positions_au"], axis=1)
    position_capable_ids = {int(nav_cat["source_id"][m["star_index"]]) for m in nav}
    nav_centroids = {m["centroid_index"] for m in nav}

    labels = []
    identified_centroids = set(nav_centroids)
    if full_labels:
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
    if xy.shape[0]:
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
    ax.set_title(
        f"{rec['name']}  -  {xy.shape[0]} detected, {len(identified_centroids)} "
        f"identified, {len(nav_centroids)} position-capable",
        color=_DIM,
        fontsize=9.5,
        fontfamily="monospace",
    )
    fig.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _lines_for(ids, age_yr, radius_arcsec, rv_kms):
    """Build lines of position across the given frames at one catalog age.

    Catalog choice: if EVERY selected frame is a demo (known-JPL) frame, the
    frozen 20-pc file is used so the blessed fix stays byte-reproducible; if any
    frame is uploaded, the widest usable catalog is used. Returns (lines,
    all_demo) -- all_demo gates the miss-vs-JPL computation in locate_payload.
    """
    recs = [(fid, _record_by_id(fid)) for fid in ids]
    all_demo = all(
        rec is not None and rec.get("is_demo") for _, rec in recs if rec is not None
    ) and any(rec is not None for _, rec in recs)
    if all_demo:
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
            lines.append(
                LineOfPosition(
                    star_pos_au=cat["positions_au"][si],
                    direction_unit=measured_direction(
                        rec["plate"], rec["centroids"]["xy"][m["centroid_index"]]
                    ),
                    star_source_id=int(cat["source_id"][si]),
                    sep_arcsec=m["sep_arcsec"],
                    image_name=rec["name"],
                )
            )
    return lines, all_demo


def locate_payload(ids, age_yr, radius_arcsec, rv_kms):
    """Fix the spacecraft from the selected frames. Never raises to the caller.

    Returns a JSON-ready dict: on success {ok:True, x_au, r_au, r_pc,
    ellipsoid_au, chi2, n_lines, distinct_stars, lines:[{star_name, image,
    resid_arcsec}], miss_au (or None), message:""}; on a degenerate geometry
    {ok:False, message:<friendly text>, n_lines}.
    """
    lines, all_demo = _lines_for(ids, age_yr, radius_arcsec, rv_kms)
    try:
        fix = fix_position(lines, rmssig_arcsec=RMSSIG_ARCSEC)
    except ValueError as exc:
        return {"ok": False, "message": str(exc), "n_lines": len(lines)}
    x = fix["x_au"]
    r_au = float(np.linalg.norm(x))
    miss = float(np.linalg.norm(x - NEWH_X_JPL)) if all_demo else None
    return {
        "ok": True,
        "x_au": [float(v) for v in x],
        "r_au": r_au,
        "r_pc": r_au / AU_PER_PC,
        "ellipsoid_au": [float(v) for v in fix["ellipsoid_au"]],
        "chi2": fix["chi2"],
        "n_lines": fix["n_lines"],
        "distinct_stars": fix["distinct_stars"],
        "lines": [
            {
                "star_name": STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id)),
                "image": ln.image_name,
                "resid_arcsec": round(ln.sep_arcsec, 2),
            }
            for ln in lines
        ],
        "miss_au": miss,
        "message": "",
    }


def age_payload(ids, radius_arcsec, rv_kms, age_min, age_max, age_step):
    """Estimate the catalog age from the frame geometry over a grid.

    Returns: {ok, age_hat_yr, sigma_age_yr, ages, chi2s, note, truth_yr} or
    {ok:False, message} if the grid produces no fittable minimum at all.
    """
    grid = np.arange(age_min, age_max + 1e-9, age_step)
    if grid.size < 3:
        return {"ok": False, "message": "age grid needs at least 3 points"}
    try:
        res = estimate_age(
            lambda a: _lines_for(ids, a, radius_arcsec, rv_kms)[0],
            grid,
            rmssig_arcsec=RMSSIG_ARCSEC,
        )
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    truth = [
        _record_by_id(fid)["obs_age_yr"]
        for fid in ids
        if _record_by_id(fid) is not None
    ]
    chi2s = [None if not np.isfinite(c) else float(c) for c in res["chi2s"]]
    return {
        "ok": True,
        "age_hat_yr": res["age_hat_yr"],
        "sigma_age_yr": None if np.isnan(res["sigma_age_yr"]) else res["sigma_age_yr"],
        "ages": [float(a) for a in res["ages"]],
        "chi2s": chi2s,
        "note": res.get("note", ""),
        "truth_yr": float(np.mean(truth)) if truth else None,
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


def handle_upload(filename, data_bytes, api_key=None):
    """Save an uploaded image, plate-solve it, and add it to the gallery.

    Returns {ok:True, id, name, field, obs_age_yr} on success, else
    {ok:False, message:<friendly multi-backend error>}.
    """
    import tempfile

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
    return {
        "ok": True,
        "id": uid,
        "name": _UPLOADS[uid]["name"],
        "field": "uploaded",
        "obs_age_yr": round(_UPLOADS[uid]["obs_age_yr"], 4),
    }


# --- HTTP layer (thin) ------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    server_version = "GalNavWeb/1.0"

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
                # thumb=1 -> nav-only overlay (fast, no wide-catalog load).
                full = q.get("thumb", ["0"])[0] not in ("1", "true")
                self._send(
                    200,
                    "image/png",
                    render_frame_png(fid, age, radius, full_labels=full),
                )
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
