"""Pre-fetch and cache the Gaia identification cones for the 12 demo frames.

Run this ONCE with the internet up. Afterwards the booth demo labels nearly
every dot FULLY OFFLINE, because a cached cone is a zero-network read. The 12
New Horizons frames repeat only a few distinct pointings, so only a handful of
TAP jobs actually run; same-footprint frames reuse the first cone file.

    python -m gui.prewarm_demo_cones
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from gui import gaiacone
from gui.platesolve import fits_header_solution
from gui.webapp import _demo_paths


def main():
    paths = _demo_paths()
    print(f"{len(paths)} demo frames; fetching one cone per distinct footprint...\n")
    seen = {}
    for p in paths:
        name = Path(p).name
        plate = fits_header_solution(p)
        fp = gaiacone._footprint(plate)
        cache_path = gaiacone._cache_path(plate, gaiacone.CACHE_DIR)
        if fp in seen:
            print(f"{name}: footprint {fp} -> shares {cache_path.name}")
            continue
        seen[fp] = cache_path
        existed = cache_path.exists()
        print(
            f"{name}: footprint {fp} -> "
            f"{'cached' if existed else 'fetching'} {cache_path.name} ...",
            flush=True,
        )
        cone = gaiacone.cone_catalog(plate, allow_fetch=True)
        if cone is None:
            print(
                "  FAILED (offline / TAP down) -- render falls back to nearby catalog"
            )
        else:
            n = int(cone["source_id"].shape[0])
            kb = cache_path.stat().st_size / 1024.0
            print(f"  {n} stars, {kb:.0f} KB")

    files = sorted(gaiacone.CACHE_DIR.glob("cone_*.csv"))
    total_kb = sum(f.stat().st_size for f in files) / 1024.0
    print(f"\n{len(files)} distinct cone file(s), {total_kb:.0f} KB total:")
    for f in files:
        print(f"  {f.name}  {f.stat().st_size / 1024.0:.0f} KB")


if __name__ == "__main__":
    main()
