"""Reproducibly fetch the E4 (real NICER photon-folding) dataset from HEASARC.

E4 is the project's ARMOR experiment (only run once the spine is green): real
NICER X-ray photon analysis of three millisecond pulsars. For each observation
we fold the barycentred photon arrival times against the pulsar ephemeris,
inject a known orbit-ephemeris/clock bias, and recover it from the phase
residuals; pass = bias recovery within 2 sigma on three independent pulsars.
The companion armor card Spec 9 requires PINT `photonphase` agreement to
< 1e-9 in phase (hence the WSL/longdouble ARMOR env in requirements-armor.txt).

For each ObsID this fetches exactly the two files that folding needs:
  - xti/event_cl/ni{ObsID}_0mpu7_cl.evt.gz : the level-2 CLEANED photon event
        list (the 7-MPU merged, screened arrival times = the measurements).
  - auxil/ni{ObsID}.orb.gz               : the ISS orbit ephemeris for that
        observation. Barycentering (PINT/barycorr) splines the spacecraft
        position from this file to move each photon to the Solar-System
        barycentre. Without the .orb, the event times cannot be barycentred.

Three pulsars, two ObsIDs each (one minimal per pulsar is enough; the second
gives an independent epoch), 12 files, ~90 MB total:
  - PSR J0030+0451  (Riley/Bogdanov 2019 NICER mass-radius campaign)
  - PSR B1937+21 = J1939+2134 (the original millisecond pulsar; NICER MSP timing)
  - PSR J0437-4715  (Choudhury 2024 NICER dataset; nearest/brightest MSP)

Source (primary): HEASARC public archive, no auth, directory pattern
    https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs/{YYYY_MM}/{ObsID}/
Mirror (fallback, tried only if HEASARC 404s/stalls after one retry):
    https://nasa-heasarc.s3.amazonaws.com/nicer/data/obs/{YYYY_MM}/{ObsID}/
NICER data are in the public domain (US Government / NASA GSFC work).

The script downloads the 12 files into an archive-relative layout under this
directory, streams each to disk while computing its sha256, and verifies every
file three ways: (1) the bytes written equal the server Content-Length (catches
truncation), (2) the .gz decompresses fully with gzip (catches corruption /
HTML error pages), and (3) the byte size is plausible against the HEASARC
listing sizes recorded below (catches a wrong/placeholder file). It then prints
a manifest of (path, bytes, sha256). Idempotent: files already present and
non-empty are kept and re-verified, not re-downloaded. Requires only the Python
standard library.

Run:  python data/e4_nicer/fetch_e4_data.py
Retrieved for GalNav on 2026-07-16 (this file is the provenance record; the
~90 MB of fetched raw data is git-ignored and re-fetchable from HEASARC above).
"""

import gzip
import hashlib
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "galnav-e4/1.0 (ISEF research; stdlib urllib)"
PRIMARY = "https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs"
MIRROR = "https://nasa-heasarc.s3.amazonaws.com/nicer/data/obs"
CHUNK = 1 << 16  # 64 KiB streaming reads

# One row per ObsID. Fields: pulsar, ObsID, YYYY_MM, UTC date, exposure (ks),
# and the HEASARC directory-listing sizes for the event and orbit files
# (approximate, "M" = 1e6 bytes) used for the size-plausibility check.
# All 12 files confirmed present on HEASARC by directory listing 2026-07-16.
OBS = (
    ("PSR J0030+0451", "1060020263", "2018_01", "2018-01-19", 29.5, 2.9e6, 2.7e6),
    ("PSR J0030+0451", "1060020113", "2017_08", "2017-08-04", 29.2, 20e6, 2.7e6),
    ("PSR B1937+21", "1070020148", "2017_09", "2017-09-16", 29.0, 3.0e6, 2.7e6),
    ("PSR B1937+21", "1070020147", "2017_09", "2017-09-16", 21.6, 8.5e6, 1.9e6),
    ("PSR J0437-4715", "1060010188", "2017_12", "2017-12-07", 19.7, 1.1e6, 1.8e6),
    ("PSR J0437-4715", "1060010157", "2017_10", "2017-10-13", 19.1, 37e6, 2.2e6),
)


def _targets():
    """Yield one (relpath, out_path, size_hint_bytes) per file to fetch.

    relpath is archive-relative (below .../obs/); out_path is the local absolute
    path mirroring that layout under this directory. Units: bytes.
    """
    for _pulsar, obsid, ym, _date, _ks, evt_hint, orb_hint in OBS:
        stem = f"{ym}/{obsid}"
        evt = f"{stem}/xti/event_cl/ni{obsid}_0mpu7_cl.evt.gz"
        orb = f"{stem}/auxil/ni{obsid}.orb.gz"
        yield evt, os.path.join(HERE, *evt.split("/")), evt_hint
        yield orb, os.path.join(HERE, *orb.split("/")), orb_hint


def _sha256_file(path):
    """Return the hex sha256 of the file at path (str). Streams; no size limit."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_one(url, out):
    """Stream url -> out, returning (bytes_written:int, sha256_hex:str).

    Raises IOError if the server sends a Content-Length that disagrees with the
    number of bytes actually written (a truncated transfer).
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=180) as r:
        cl = r.headers.get("Content-Length")
        expected = int(cl) if cl and cl.isdigit() else None
        with open(out, "wb") as fh:
            while True:
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                fh.write(chunk)
                h.update(chunk)
                n += len(chunk)
    if expected is not None and n != expected:
        raise IOError(f"truncated: wrote {n} of {expected} bytes")
    return n, h.hexdigest()


def _download(relpath, out):
    """Fetch one archive-relative file to out, returning (bytes, sha256, source).

    Tries HEASARC, then HEASARC once more (the one retry), then the AWS mirror.
    Raises RuntimeError only if all three attempts fail (caller then skips it).
    Idempotent: an existing non-empty file is kept and re-hashed (source
    "cached"), never re-downloaded.
    """
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return os.path.getsize(out), _sha256_file(out), "cached"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    attempts = (
        ("heasarc", PRIMARY),
        ("heasarc-retry", PRIMARY),
        ("aws-mirror", MIRROR),
    )
    last = None
    for source, base in attempts:
        try:
            n, sha = _download_one(f"{base}/{relpath}", out)
            return n, sha, source
        except Exception as e:  # noqa: BLE001 - any failure -> next source
            last = e
            if os.path.exists(out):
                os.remove(out)
            time.sleep(2)
    raise RuntimeError(f"all sources failed for {relpath}: {last!r}")


def _gzip_ok(path):
    """True iff path decompresses fully as gzip (reads to EOF). Catches
    truncation and HTML error pages masquerading as .gz."""
    try:
        with gzip.open(path, "rb") as g:
            while g.read(1 << 20):
                pass
        return True
    except Exception:  # noqa: BLE001 - any gzip/OS error means "not valid"
        return False


def main():
    rows = []  # (relpath, bytes, sha, source, gz_ok, size_ratio)
    skipped = []
    for relpath, out, hint in _targets():
        try:
            n, sha, source = _download(relpath, out)
        except Exception as e:  # noqa: BLE001 - record and continue (armor: minimal set is 1 ObsID/pulsar)
            print(f"SKIP  {relpath}\n      {e}")
            skipped.append((relpath, str(e)))
            continue
        gz = _gzip_ok(out)
        ratio = n / hint if hint else float("nan")
        flag = "ok" if source == "cached" else source
        note = "" if gz else "  !! GZIP FAILED"
        if not (0.5 <= ratio <= 2.0):
            note += f"  !! SIZE {ratio:.2f}x listing"
        print(f"{flag:>12}  {n:>9} B  ratio {ratio:4.2f}  {relpath}{note}")
        rows.append((relpath, n, sha, source, gz, ratio))

    print("\n" + "=" * 78)
    print("E4 NICER MANIFEST  (path, bytes, sha256)")
    print("=" * 78)
    for relpath, n, sha, _source, gz, ratio in rows:
        print(
            f"{relpath}\n    {n} bytes  sha256={sha}  gzip_ok={gz}  size_ratio={ratio:.3f}"
        )

    total = sum(n for _, n, _, _, _, _ in rows)
    bad_gz = [r[0] for r in rows if not r[4]]
    bad_sz = [r[0] for r in rows if not (0.5 <= r[5] <= 2.0)]
    print("=" * 78)
    print(
        f"files present: {len(rows)}/12    total bytes: {total} (~{total / 1e6:.1f} MB)"
    )
    if bad_gz:
        print(f"GZIP VERIFY FAILED for {len(bad_gz)}: {bad_gz}")
    if bad_sz:
        print(f"SIZE-PLAUSIBILITY WARN for {len(bad_sz)}: {bad_sz}")
    if skipped:
        print(f"SKIPPED {len(skipped)}: {[s[0] for s in skipped]}")
    ok = len(rows) == 12 and not bad_gz
    print("E4 dataset ready under" if ok else "E4 dataset INCOMPLETE under", HERE)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
