#!/usr/bin/env bash
# =============================================================================
# GalNav - one-time setup for the OFFLINE blind plate-solver (astrometry.net).
#
# This lets the demo "eat any image": for a photo with no built-in sky
# coordinates (no WCS), astrometry.net figures out where the camera pointed
# by pattern-matching the star field -- entirely offline, no internet.
#
# It installs TWO tiers of star-pattern index files:
#   * WIDE  fields (>~0.5 deg): the apt Tycho-2 package (astrometry-data-tycho2).
#   * NARROW fields (<~0.5 deg, e.g. New Horizons LORRI at 0.29 deg): the
#     Gaia-based 5200 LITE index files (scales 3-5), pre-downloaded into the
#     repo at  data/astrometry-index/  by the download step. This script does
#     NOT download them; it just points the solver at whatever is there.
#
# You only run this ONCE. The baked-in New Horizons demo does NOT need it
# (those frames already carry their WCS); it is only for arbitrary uploads.
#
# HOW TO RUN (from a normal Windows terminal - PowerShell or Terminal):
#     wsl bash "/mnt/c/Users/rudra/OneDrive/Desktop/spacenav/gui/install-offline-solver.sh"
# or open WSL/Ubuntu yourself and run:
#     bash /mnt/c/Users/rudra/OneDrive/Desktop/spacenav/gui/install-offline-solver.sh
#
# You will be asked for your Linux (WSL) password once -- that is `sudo`
# installing the solver. Nothing here touches Windows or the repo.
# =============================================================================
set -e

# --- work out where THIS script lives, so the index path survives a repo move.
# The script sits in gui/, so the repo root is one level up, and the narrow
# index files live in <repo>/data/astrometry-index. Because you run this
# through WSL, $0 is the /mnt/c/... form, and `pwd` returns that same mount
# path -- exactly what solve-field (running inside WSL) needs in its config.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX_DIR="$REPO_ROOT/data/astrometry-index"
CFG="$HOME/.galnav-astrometry.cfg"

echo ">> [1/4] Updating package lists..."
sudo apt-get update

echo ">> [2/4] Installing astrometry.net + the wide-field sky index (Tycho-2, ~160 MB)..."
# astrometry.net           = the blind solver (gives you `solve-field`)
# astrometry-data-tycho2   = index files for fields roughly 0.5 deg .. 30 deg
sudo apt-get install -y astrometry.net astrometry-data-tycho2

echo ">> [3/4] Writing solver config -> $CFG"
# This config is what the GalNav web app passes via `--config`. It lists BOTH
# index locations so one solver call can handle wide AND narrow fields:
#   inparallel                 -> search the index scales concurrently (faster)
#   autoindex                  -> REQUIRED: auto-load every index file found in
#                                 the add_path dirs. Without it the engine sees
#                                 add_path as search-paths-only and aborts with
#                                 "You must list at least one index" (measured).
#   add_path /usr/share/astrometry  -> the apt Tycho-2 wide-field indexes
#   add_path <repo>/.../astrometry-index -> our pre-downloaded 5200 narrow ones
cat > "$CFG" <<CFGEOF
inparallel
autoindex
add_path /usr/share/astrometry
add_path $INDEX_DIR
CFGEOF
echo "    wrote:"
sed 's/^/      /' "$CFG"

echo ">> [4/4] Verifying..."
if command -v solve-field >/dev/null 2>&1; then
    echo "    OK: solve-field is installed at $(command -v solve-field)"
    # Count the narrow-field index files actually present in the repo dir.
    if [ -d "$INDEX_DIR" ]; then
        n_narrow="$(find "$INDEX_DIR" -maxdepth 1 -name 'index-*.fits' 2>/dev/null | wc -l)"
    else
        n_narrow=0
    fi
    echo "    Narrow-field 5200 index files found in repo: $n_narrow"
    echo "        (dir: $INDEX_DIR)"
    if [ "$n_narrow" -eq 0 ]; then
        echo "    NOTE: no narrow-field indexes present yet. Wide fields (>~0.5 deg)"
        echo "    will still solve via the Tycho-2 package. To solve NARROW fields"
        echo "    (e.g. LORRI 0.29 deg), run the download step that fills"
        echo "    data/astrometry-index/ with the 5200 LITE files (scales 3-5)."
    fi
    echo
    echo "Done. The GalNav web app's Upload button uses this automatically"
    echo "(it shells out to 'wsl solve-field --config ~/.galnav-astrometry.cfg')."
    echo
    echo "Test it yourself on any star image with:"
    echo "    wsl solve-field --config ~/.galnav-astrometry.cfg --overwrite --no-plots <image>"
else
    echo "    ERROR: solve-field not found after install." >&2
    echo "    Check the apt output above. On some Ubuntu versions the wide" >&2
    echo "    index package is named differently; try: apt search astrometry" >&2
    exit 1
fi
