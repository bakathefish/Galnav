"""Fetch the WIDE (~100 pc) Gaia DR3 navigation catalog for the GalNav demo.

This produces data/gaia_dr3_nav_100pc.csv — the catalog the web GUI uses for
its "trace any spacecraft image" mode. It is NOT used by the frozen science
spine (that stays on data/gaia_dr3_nav_subset.csv, the ~20 pc file, which is
frozen byte-for-byte). Same column set and order as the 20 pc file, so the
existing loader galnav/nav/catalog.py::load_catalog reads it unchanged.

Stdlib only (urllib) — astroquery is NOT an allowed dependency. Because a
100 pc query returns far more than the 2000-row synchronous limit, this uses
the ESA Gaia TAP ASYNC (UWS) job workflow: submit -> poll -> download.

Re-runnable and offline-reproducible against the static DR3 release.

Size guard
----------
The 20 pc file measures ~0.32 KB/row. A raw 100 pc cut is ~266.5k rows
(~85 MB) which blows the "keep it committable" budget, so when the base cut
would exceed ~350,000 rows OR ~45 MB, we add a brightness cut
`phot_g_mean_mag < 16.5`. That keeps every navigationally useful star
(Proxima G~9, Wolf 359 G~13.5) and drops only the faint late-M / white-dwarf
tail. The decision is made from a cheap COUNT(*) first, so we never download
the oversized full file just to throw it away.
"""

import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TAP_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
TAP_ASYNC = "https://gea.esac.esa.int/tap-server/tap/async"
UA = {"User-Agent": "galnav-fetch/1.0 (stdlib urllib; ISEF research)"}

OUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gaia_dr3_nav_100pc.csv"
)

# EXACT column set and order of data/gaia_dr3_nav_subset.csv (the frozen file's
# header wins — the loader reads by name, but we match order too).
COLUMNS = (
    "source_id, ra, dec, parallax, parallax_error, pmra, pmra_error, "
    "pmdec, pmdec_error, radial_velocity, radial_velocity_error, "
    "phot_g_mean_mag, ra_error, dec_error, ra_dec_corr, ra_parallax_corr, "
    "dec_parallax_corr, ra_pmra_corr, ra_pmdec_corr, dec_pmra_corr, "
    "dec_pmdec_corr, parallax_pmra_corr, parallax_pmdec_corr, "
    "pmra_pmdec_corr, ruwe"
)

# Same quality cuts as the frozen file, just parallax > 10 (100 pc) instead of
# > 50 (20 pc). pmra/pmdec forced finite because load_catalog RAISES on a
# non-finite proper motion (its "no NaN out" propagation guarantee).
BASE_WHERE = (
    "parallax > 10 AND parallax_over_error > 10 AND ruwe < 1.4 "
    "AND pmra IS NOT NULL AND pmdec IS NOT NULL"
)
MAG_CUT = " AND phot_g_mean_mag < 16.5"

BYTES_PER_ROW = 320  # measured on the 20 pc file (~0.32 KB/row)
ROW_GUARD = 350_000
SIZE_GUARD_MB = 45


def _post(url, fields, timeout=180):
    """POST form-encoded fields; return (status, headers, body_bytes).

    Does NOT follow redirects, so the async submit can read the Location
    header of the 303 that points at the new UWS job.
    """
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers=UA)

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:  # 303 lands here (redirect blocked)
        return e.code, e.headers, e.read()


def _get(url, timeout=180):
    """GET a URL; return body bytes (follows redirects)."""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def count(where):
    """Synchronous COUNT(*) for a WHERE clause — one cheap row back."""
    q = "SELECT COUNT(*) AS n FROM gaiadr3.gaia_source WHERE " + where
    fields = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q}
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(TAP_SYNC, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read().decode()
    return int(body.strip().splitlines()[-1])


def submit_async(where):
    """Submit the full SELECT as an async UWS job; return the job URL."""
    query = (
        "SELECT "
        + COLUMNS
        + " FROM gaiadr3.gaia_source WHERE "
        + where
        + " ORDER BY parallax DESC"
    )
    status, headers, _ = _post(
        TAP_ASYNC,
        {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "PHASE": "RUN",
            "QUERY": query,
        },
    )
    location = headers.get("Location")
    if not location:
        raise RuntimeError(f"async submit gave no Location (HTTP {status})")
    return location


def poll(job_url, max_wait_s=600):
    """Poll <job>/phase with backoff until a terminal phase; return it."""
    waited, delay = 0.0, 2.0
    while waited < max_wait_s:
        phase = _get(job_url + "/phase").decode().strip()
        print(f"  phase={phase} (t+{waited:.0f}s)", flush=True)
        if phase in ("COMPLETED", "ERROR", "ABORTED", "HELD"):
            return phase
        time.sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 20.0)  # backoff, cap 20 s
    raise TimeoutError(f"job did not finish within {max_wait_s}s")


def download(job_url, out_path):
    """Stream the job results to disk."""
    req = urllib.request.Request(job_url + "/results/result", headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(out_path, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def main():
    n_full = count(BASE_WHERE)
    est_mb = n_full * BYTES_PER_ROW / 1e6
    print(f"base 100 pc cut: {n_full:,} rows (~{est_mb:.0f} MB estimated)")

    use_mag_cut = n_full > ROW_GUARD or est_mb > SIZE_GUARD_MB
    where = BASE_WHERE + (MAG_CUT if use_mag_cut else "")
    if use_mag_cut:
        n_cut = count(where)
        print(
            f"size guard tripped -> adding {MAG_CUT.strip()}: "
            f"{n_cut:,} rows (~{n_cut * BYTES_PER_ROW / 1e6:.0f} MB est.)"
        )

    print("submitting async job...", flush=True)
    job_url = submit_async(where)
    print(f"  job: {job_url}", flush=True)
    phase = poll(job_url)
    if phase != "COMPLETED":
        msg = _get(job_url + "/error").decode(errors="replace")
        raise RuntimeError(f"job ended {phase}:\n{msg}")

    download(job_url, OUT_PATH)
    size_mb = os.path.getsize(OUT_PATH) / 1e6
    with open(OUT_PATH, "rb") as f:
        rows = sum(1 for _ in f) - 1  # minus header
    print(f"wrote {OUT_PATH}: {rows:,} rows, {size_mb:.1f} MB")
    if size_mb > SIZE_GUARD_MB:
        print(
            f"NOTE: {size_mb:.1f} MB exceeds the {SIZE_GUARD_MB} MB soft "
            f"guard even after the G<16.5 cut (the only designated "
            f"fallback). Shipping it; flag for a tighter cut if needed."
        )


if __name__ == "__main__":
    sys.exit(main())
