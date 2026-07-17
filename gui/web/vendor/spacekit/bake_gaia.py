"""Bake the repo's 20-pc Gaia nav subset into an offline JSON for the PoC.

Reads (read-only) the repo CSV, computes heliocentric ECLIPTIC J2000 Cartesian
positions in parsecs, and emits a compact JSON the pc-scale scene loads locally.

Frame: equatorial ICRS unit vector (from ra,dec) * dist_pc, then rotated about
+X by the mean obliquity 23.43928 deg -> ecliptic (same transform the au scene
uses for the recovered marker). dist_pc = 1000 / parallax_mas.
"""

import csv, json, math
from pathlib import Path

# Paths are derived from this script's location so it is runnable from the repo:
# gui/web/vendor/spacekit/bake_gaia.py -> repo root is parents[4]. Reads the
# FROZEN 20-pc nav subset (read-only, public catalog) and rewrites the baked
# JSON in place next to this script.
_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[4]
SRC = str(_REPO / "data" / "gaia_dr3_nav_subset.csv")
OUT = str(_HERE.parent / "data" / "gaia_20pc.json")

TILT = math.radians(23.43928)

# famous stars we will label, keyed by Gaia DR3 source_id (verified present)
FAMOUS = {
    "5853498713190525696": "Proxima Centauri",
    "4472832130942575872": "Barnard's Star",
    "3864972938605115520": "Wolf 359",
}
# also try to catch a few more by sky position (deg) if they happen to be present
BY_POS = [  # (name, ra, dec, tol_deg)
    ("Sirius", 101.287, -16.716, 0.3),
    ("Alpha Centauri", 219.902, -60.834, 0.4),
    ("Lalande 21185", 165.834, 35.970, 0.3),
    ("Epsilon Eridani", 53.233, -9.458, 0.3),
    ("Ross 154", 282.456, -23.836, 0.3),
]


def eq_to_ec(x, y, z):
    return [
        x,
        math.cos(TILT) * y + math.sin(TILT) * z,
        -math.sin(TILT) * y + math.cos(TILT) * z,
    ]


points = []
labels = {}  # name -> {xyz, dist_pc, source_id}
nearest = []  # (dist, name-ish, xyz)

with open(SRC, newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        try:
            ra = math.radians(float(row["ra"]))
            dec = math.radians(float(row["dec"]))
            plx = float(row["parallax"])
        except (ValueError, KeyError):
            continue
        if plx <= 0:
            continue
        d = 1000.0 / plx  # parsecs
        ux = math.cos(dec) * math.cos(ra)
        uy = math.cos(dec) * math.sin(ra)
        uz = math.sin(dec)
        x, y, z = eq_to_ec(ux * d, uy * d, uz * d)
        xyz = [round(x, 4), round(y, 4), round(z, 4)]
        points.append(xyz)

        sid = row["source_id"]
        radeg, decdeg = float(row["ra"]), float(row["dec"])
        if sid in FAMOUS:
            labels[FAMOUS[sid]] = {"xyz": xyz, "dist_pc": round(d, 3), "source_id": sid}
        else:
            for name, rr, dd, tol in BY_POS:
                if (
                    abs(radeg - rr) < tol
                    and abs(decdeg - dd) < tol
                    and name not in labels
                ):
                    labels[name] = {
                        "xyz": xyz,
                        "dist_pc": round(d, 3),
                        "source_id": sid,
                    }
        nearest.append((d, sid, xyz))

nearest.sort()
out = {
    "frame": "heliocentric ecliptic J2000, parsecs",
    "tilt_deg": 23.43928,
    "star_count": len(points),
    "labels": labels,
    "points": points,
}
with open(OUT, "w") as f:
    json.dump(out, f, separators=(",", ":"))

import os

print("stars baked:", len(points))
print("labels found:", list(labels.keys()))
for name, info in labels.items():
    print(f"  {name:18s} d={info['dist_pc']:.3f} pc  xyz={info['xyz']}")
print("nearest 5 (d_pc, source_id):", [(round(d, 3), s) for d, s, _ in nearest[:5]])
print("out bytes:", os.path.getsize(OUT))
