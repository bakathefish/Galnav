"""Where does the WCS come from? Three ways to attach world coordinates
(RA/Dec per pixel) to an uploaded star-field image, tried in order:

  1. fits-header    -- the image already carries a solved WCS in its header
                       (e.g. the New Horizons LORRI "pwcs2" frames). Free,
                       offline, instant.
  2. wsl-astrometrynet -- shell out to a local astrometry.net "solve-field"
                       running inside WSL. Blind plate solve; needs index
                       files installed once.
  3. nova           -- upload to the nova.astrometry.net web service and poll
                       for the solution. Needs a free API key; uses the
                       network. stdlib urllib only (data/*/fetch-script
                       precedent).

The blind backends (2, 3) are OPTIONAL. With neither installed the tool still
works on any image that already has a WCS header, which every demo dataset in
this repo does. All network/subprocess code is isolated in small,
monkeypatchable functions so the tests stay offline.

Reference: astrometry.net blind solver, Lang, Hogg, Mierle, Blanton & Roweis
2010, AJ 139, 1782 ([AstrometryNet]); nova web API ([NovaAPI]).
"""

import io
import json
import os
import subprocess
import tempfile
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

NOVA_BASE = "http://nova.astrometry.net"


@dataclass
class PlateSolution:
    """One image's world-coordinate solution.

    wcs: astropy.wcs.WCS (2-D celestial) mapping pixel <-> ICRS RA/Dec.
    source: which backend produced it -- one of "fits-header",
        "wsl-astrometrynet", "nova", "mock".
    width, height: image size in pixels (NAXIS1, NAXIS2).
    """

    wcs: WCS
    source: str
    width: int
    height: int

    @property
    def center_radec_deg(self):
        """(ra_deg, dec_deg) of the image centre pixel (ICRS)."""
        sky = self.wcs.celestial.pixel_to_world(
            (self.width - 1) / 2.0, (self.height - 1) / 2.0
        )
        sky = sky.icrs
        return float(sky.ra.deg), float(sky.dec.deg)

    @property
    def scale_arcsec_per_px(self):
        """Plate scale in arcsec/pixel (mean of the two axis scales)."""
        scales_deg = proj_plane_pixel_scales(self.wcs.celestial)
        return float(np.mean(scales_deg) * 3600.0)


# --- backend 1: the image already carries a WCS -----------------------------
def fits_header_solution(path):
    """Read a WCS straight out of a FITS file's header, if it has one.

    path: path to a FITS image. The first HDU whose data is 2-D is used; its
        header (with the full HDU list passed so SIP distortion tables in
        later HDUs resolve) is turned into a WCS.
    Returns: PlateSolution (source="fits-header"), or None if no HDU has a
        celestial (RA/Dec) WCS -- the caller then falls back to a blind solve.
    Raises RuntimeError with a plain-English hint if the file is not FITS at all
        (e.g. a PNG/JPG), so the caller does not surface astropy's cryptic
        "No SIMPLE card found" message.
    """
    try:
        hdul = fits.open(path)
    except OSError:
        raise RuntimeError(
            "not a FITS file (no embedded WCS possible) -- a PNG/JPG needs a "
            "blind solve: enable WSL astrometry.net or a nova API key."
        )
    with hdul:
        for hdu in hdul:
            data = hdu.data
            if data is None or np.ndim(data) < 2:
                continue
            wcs = WCS(hdu.header, fobj=hdul)
            if not wcs.has_celestial:
                continue
            ny, nx = data.shape[-2:]
            return PlateSolution(
                wcs=wcs.celestial, source="fits-header", width=int(nx), height=int(ny)
            )
    return None


# --- backend 2: local astrometry.net via WSL --------------------------------
def _win_to_wsl_path(path):
    """Convert a Windows path (C:\\a\\b) to its WSL mount form (/mnt/c/a/b).

    path: a filesystem path (str or Path). On Windows, Path.resolve() anchors a
        relative or bare-POSIX input to the current drive (e.g. "img.fits" ->
        "C:/.../img.fits"), so it is mapped to /mnt/c/...; an already-absolute
        POSIX path (no drive letter) is returned unchanged.
    Returns: str path usable from inside `wsl`.
    """
    p = Path(path).resolve()
    s = p.as_posix()  # e.g. "C:/Users/x/f.fits"
    if len(s) >= 2 and s[1] == ":":
        drive = s[0].lower()
        return f"/mnt/{drive}{s[2:]}"
    return s


def _wsl_available():
    """True if `wsl which solve-field` finds the blind solver in WSL."""
    try:
        out = subprocess.run(
            ["wsl", "which", "solve-field"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return out.returncode == 0 and out.stdout.strip() != ""
    except (OSError, subprocess.SubprocessError):
        return False


def wsl_solve(
    image_path, scale_low_arcsec_px=None, scale_high_arcsec_px=None, timeout_s=300
):
    """Blind-solve an image with astrometry.net's solve-field inside WSL.

    image_path: path to the image to solve (FITS/PNG/JPG).
    scale_low_arcsec_px, scale_high_arcsec_px: optional plate-scale bracket in
        arcsec/pixel; narrows and speeds the blind search when known.
    timeout_s: hard wall-clock limit for the solve subprocess (seconds).
    Returns: PlateSolution (source="wsl-astrometrynet").
    Raises RuntimeError if WSL/solve-field is unavailable (message carries the
        one-line install hint) or if no .wcs file is produced.
    """
    if not _wsl_available():
        raise RuntimeError(
            "WSL solve-field not found. Install once: "
            "`wsl sudo apt install astrometry.net` plus index files "
            "(astrometry-data-*; e.g. 4100/4200 series for wide fields)."
        )
    src_wsl = _win_to_wsl_path(image_path)
    with tempfile.TemporaryDirectory() as tmp:
        out_wsl = _win_to_wsl_path(tmp)
        cmd = [
            "wsl",
            "solve-field",
            "--overwrite",
            "--no-plots",
            "--dir",
            out_wsl,
            src_wsl,
        ]
        if scale_low_arcsec_px is not None and scale_high_arcsec_px is not None:
            cmd += [
                "--scale-units",
                "arcsecperpix",
                "--scale-low",
                str(scale_low_arcsec_px),
                "--scale-high",
                str(scale_high_arcsec_px),
            ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        stem = Path(image_path).stem
        wcs_path = Path(tmp) / f"{stem}.wcs"
        if not wcs_path.exists():
            raise RuntimeError(
                f"solve-field produced no {stem}.wcs (blind solve failed; "
                "check index-file coverage for this field of view)."
            )
        return _plate_from_wcs_bytes(
            wcs_path.read_bytes(), source="wsl-astrometrynet", image_path=image_path
        )


# --- backend 3: nova.astrometry.net web API ---------------------------------
def _http_json(url, payload_json=None):
    """POST request-json=<...> (or GET) and return the parsed JSON dict.

    url: full nova API URL.
    payload_json: dict to send as the URL-encoded field "request-json"; None
        makes it a GET.
    Returns: parsed JSON response (dict).
    """
    if payload_json is None:
        req = Request(url)
    else:
        body = ("request-json=" + json.dumps(payload_json)).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_bytes(url):
    """GET url and return the raw response bytes (used for the .wcs download)."""
    with urlopen(Request(url), timeout=60) as resp:
        return resp.read()


def _nova_multipart(session, image_path, scale_est_arcsec_px=None):
    """Build the (headers, body) of a nova /api/upload multipart POST.

    session: nova session token from _http_json login.
    image_path: file to upload.
    scale_est_arcsec_px: optional scale estimate (arcsec/px) -> sent as a
        +-20% arcsecperpix bracket.
    Returns: (url, headers_dict, body_bytes).
    """
    req = {"session": session, "publicly_visible": "n", "allow_modifications": "d"}
    if scale_est_arcsec_px is not None:
        req.update(
            {
                "scale_units": "arcsecperpix",
                "scale_type": "ul",
                "scale_lower": scale_est_arcsec_px * 0.8,
                "scale_upper": scale_est_arcsec_px * 1.2,
            }
        )
    boundary = "===============GalNavNovaUpload=="
    data = Path(image_path).read_bytes()
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        b"Content-Type: text/plain\r\nMIME-Version: 1.0\r\n"
        b'Content-disposition: form-data; name="request-json"\r\n\r\n'
    )
    parts.append((json.dumps(req) + "\r\n").encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        b"Content-Type: application/octet-stream\r\nMIME-Version: 1.0\r\n"
        b'Content-disposition: form-data; name="file"; filename="'
        + Path(image_path).name.encode()
        + b'"\r\n\r\n'
    )
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return NOVA_BASE + "/api/upload", headers, body


def nova_solve(image_path, api_key=None, scale_est_arcsec_px=None, timeout_s=600):
    """Blind-solve an image through the nova.astrometry.net web service.

    image_path: path to the image to solve.
    api_key: nova API key; falls back to env ASTROMETRY_NET_API_KEY.
    scale_est_arcsec_px: optional plate-scale estimate (arcsec/px).
    timeout_s: overall wall-clock budget for login+upload+polling (seconds).
    Returns: PlateSolution (source="nova").
    Raises RuntimeError on missing key, login failure, or timeout.
    """
    key = api_key or os.environ.get("ASTROMETRY_NET_API_KEY")
    if not key:
        raise RuntimeError(
            "no nova API key (pass api_key= or set ASTROMETRY_NET_API_KEY; "
            "get one free at https://nova.astrometry.net/api_help)."
        )
    login = _http_json(NOVA_BASE + "/api/login", {"apikey": key})
    if login.get("status") != "success":
        raise RuntimeError(f"nova login failed: {login}")
    session = login["session"]
    url, headers, body = _nova_multipart(session, image_path, scale_est_arcsec_px)
    up = json.loads(
        urlopen(Request(url, data=body, headers=headers), timeout=120)
        .read()
        .decode("utf-8")
    )
    if up.get("status") != "success":
        raise RuntimeError(f"nova upload failed: {up}")
    subid = up["subid"]
    deadline = time.monotonic() + timeout_s
    jid = None
    while jid is None:
        sub = _http_json(f"{NOVA_BASE}/api/submissions/{subid}")
        jobs = [j for j in sub.get("jobs", []) if j]
        if jobs:
            jid = jobs[0]
            break
        if time.monotonic() > deadline:
            raise RuntimeError(f"nova submission {subid} did not start a job in time")
        time.sleep(5)
    while True:
        job = _http_json(f"{NOVA_BASE}/api/jobs/{jid}")
        status = job.get("status")
        if status == "success":
            break
        if status == "failure":
            raise RuntimeError(f"nova job {jid} failed to solve")
        if time.monotonic() > deadline:
            raise RuntimeError(f"nova job {jid} timed out")
        time.sleep(5)
    wcs_bytes = _http_bytes(f"{NOVA_BASE}/wcs_file/{jid}")
    return _plate_from_wcs_bytes(wcs_bytes, source="nova", image_path=image_path)


def _plate_from_wcs_bytes(wcs_bytes, source, image_path=None):
    """Parse a .wcs FITS blob into a PlateSolution.

    wcs_bytes: raw bytes of a WCS-header FITS file (from solve-field / nova).
    source: provenance string for the PlateSolution.
    image_path: the solved image, used to recover width/height when the .wcs
        header omits IMAGEW/IMAGEH.
    Returns: PlateSolution.
    """
    with fits.open(io.BytesIO(wcs_bytes)) as hdul:
        header = hdul[0].header
        with warnings.catch_warnings():
            # A .wcs file is a header with no image (NAXIS=0); astropy warns
            # that the 2-axis WCS exceeds the 0-axis HDU. Expected and benign.
            warnings.simplefilter("ignore")
            wcs = WCS(header).celestial
        w = header.get("IMAGEW") or header.get("NAXIS1")
        h = header.get("IMAGEH") or header.get("NAXIS2")
    if (w is None or h is None) and image_path is not None:
        import matplotlib.pyplot as plt

        arr = plt.imread(image_path)
        h, w = arr.shape[:2]
    return PlateSolution(wcs=wcs, source=source, width=int(w), height=int(h))


# --- orchestrator -----------------------------------------------------------
def solve_image(path, api_key=None, prefer=("fits-header", "wsl", "nova"), **hints):
    """Attach a WCS to an image, trying each backend in `prefer` order.

    path: image path (FITS/PNG/JPG).
    api_key: nova API key (used only by the "nova" backend).
    prefer: backend order; subset/reorder of ("fits-header", "wsl", "nova").
    hints: optional scale hints -- scale_low_arcsec_px, scale_high_arcsec_px
        (wsl) and scale_est_arcsec_px (nova).
    Returns: the first successful PlateSolution.
    Raises RuntimeError listing every backend's failure reason plus how to
        enable each, if all backends fail.
    """
    reasons = []
    for backend in prefer:
        try:
            if backend == "fits-header":
                sol = fits_header_solution(path)
                if sol is not None:
                    return sol
                reasons.append("fits-header: no celestial WCS in the FITS header")
            elif backend == "wsl":
                return wsl_solve(
                    path,
                    scale_low_arcsec_px=hints.get("scale_low_arcsec_px"),
                    scale_high_arcsec_px=hints.get("scale_high_arcsec_px"),
                )
            elif backend == "nova":
                return nova_solve(
                    path,
                    api_key=api_key,
                    scale_est_arcsec_px=hints.get("scale_est_arcsec_px"),
                )
            else:
                reasons.append(f"{backend}: unknown backend")
        except Exception as exc:  # noqa: BLE001 -- aggregate every reason
            reasons.append(f"{backend}: {exc}")
    raise RuntimeError(
        "could not plate-solve "
        + str(Path(path).name)
        + ". Backends tried:\n  - "
        + "\n  - ".join(reasons)
        + "\nEnable a blind solver: local `wsl sudo apt install astrometry.net` "
        "(+index files), or a free nova key at "
        "https://nova.astrometry.net/api_help ."
    )
