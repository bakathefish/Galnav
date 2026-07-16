"""Reproducibly fetch the E3 (New Horizons interstellar navigation) dataset.

Source: Lauer, T. R., Munro, J., Spencer, J., et al. (2025), "A Demonstration
of Interstellar Navigation Using New Horizons," The Astronomical Journal 170, 1.
Data deposit: Zenodo, doi:10.5281/zenodo.15359866 (MIT licensed — "Anyone is
free to use either the code or the data however they wish", README.txt).

The Zenodo record holds three files:
  - nhparallax.pdf / .html : the analysis notebook rendered
  - nh2025aphj.bun         : a GIT BUNDLE (not a tarball) packing the full
                             analysis repo (12 New Horizons LORRI FITS images,
                             2 Earth-based FITS, nearby100.txt star catalogue,
                             nhjpl_traj.txt JPL ephemeris, nhparallax.ipynb).
This script downloads the three files, verifies the bundle, and `git clone`s it
into ./repo so the FITS + data + notebook are on disk. Idempotent: existing
files are left in place. Requires only the Python standard library + git.

Run:  python data/e3_new_horizons/fetch_e3_data.py
Retrieved for GalNav on 2026-07-16 (this file is the provenance record; the
147 MB of fetched data is git-ignored and re-fetchable from the DOI above).
"""

import os
import subprocess
import urllib.request

RECORD = "15359866"  # Zenodo record id behind doi:10.5281/zenodo.15359866
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ("nhparallax.pdf", "nhparallax.html", "nh2025aphj.bun")


def _download(key):
    out = os.path.join(HERE, key)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        print(f"exists: {key} ({os.path.getsize(out)} bytes)")
        return out
    url = f"https://zenodo.org/api/records/{RECORD}/files/{key}/content"
    req = urllib.request.Request(url, headers={"User-Agent": "galnav-e3/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as fh:
        fh.write(r.read())
    print(f"downloaded: {key} ({os.path.getsize(out)} bytes)")
    return out


def main():
    for key in FILES:
        _download(key)
    bundle = os.path.join(HERE, "nh2025aphj.bun")
    repo = os.path.join(HERE, "repo")
    subprocess.run(["git", "bundle", "verify", bundle], check=True)
    if not os.path.isdir(repo):
        subprocess.run(["git", "clone", "-q", bundle, repo], check=True)
        print(f"cloned bundle -> {repo}")
    else:
        print(f"repo already extracted: {repo}")
    print("E3 dataset ready under", HERE)


if __name__ == "__main__":
    main()
