"""End-to-end real-data smoke test (a script, NOT a pytest test).

Runs the whole GUI pipeline on two REAL New Horizons LORRI frames that already
carry a solved WCS ("pwcs2"): one Proxima Centauri frame and one Wolf 359
frame. It plate-solves from the FITS header, centroids the stars, ages the
public Gaia catalog to each frame's epoch, identifies the target star in the
frame, builds one line of position per frame, and fixes the spacecraft
position -- then compares to the JPL Horizons ephemeris. Finally it estimates
the catalog age from the image geometry and compares to the true ~4.31 yr.

FRAME CHOICE -- a deviation from the orchestrator brief. The brief suggested a
Wolf frame glob `lor_04499*`, but that also matches lor_0449913531, which
actually points at the PROXIMA field (RA 217, not Wolf's RA 164). We therefore
select frames by which target their WCS centre actually contains: Proxima frame
lor_0449855930, Wolf 359 frame lor_0449933827.

HONEST LIMITS -- do NOT read the ~1 au miss as a failure. Lauer et al. (2025)
reached 0.35 au by averaging 6 carefully-registered line-of-sight vectors per
star AND correcting stellar aberration (~10 arcsec at NH's ~14 km/s). We use a
single frame per star, a quick 5-sigma centroid, and NO aberration correction.
A ~1 au fix from two raw frames is exactly the expected order of magnitude.

Run:  python -m gui.nh_demo
"""

from pathlib import Path

import numpy as np
from astropy.io import fits

from gui.age import estimate_age
from gui.centroids import find_centroids
from gui.fitsmeta import observation_jd, age_yr_since_j2016
from gui.locate import (
    LineOfPosition,
    fix_position,
    identify_in_frame,
    load_aged_catalog,
    measured_direction,
)
from gui.platesolve import fits_header_solution

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"
NH_DIR = REPO_ROOT / "data" / "e3_new_horizons" / "repo"

# JPL Horizons truth (au, ICRS equatorial, SSB) -- from E3 (nhparallax.ipynb).
NEWH_X_JPL = np.array([13.5495, -42.0195, -16.4573])
PROXIMA_ID = 5853498713190525696
WOLF_ID = 3864972938605115520
WOLF_RV_FILL_KMS = 19.57  # Simbad value Lauer used (our CSV lacks Wolf's RV)
RMSSIG_ARCSEC = 0.44  # Buie per-image astrometric sigma (E3)
MATCH_RADIUS_ARCSEC = 120.0

# (frame file, target source_id, RV fill km/s). Selected by actual field centre.
FRAMES = [
    ("lor_0449855930_0x633_pwcs2.fits", PROXIMA_ID, 0.0),
    ("lor_0449933827_0x633_pwcs2.fits", WOLF_ID, WOLF_RV_FILL_KMS),
]


def _load_frames():
    """Plate-solve and centroid each frame once. Returns a list of records."""
    records = []
    for fname, sid, rv in FRAMES:
        path = NH_DIR / fname
        plate = fits_header_solution(path)
        if plate is None:
            raise RuntimeError(f"{fname}: no WCS in header (expected a pwcs2 frame)")
        image = np.asarray(fits.open(path)[0].data, dtype=float)
        centroids = find_centroids(image)
        jd = observation_jd(path)
        age = age_yr_since_j2016(jd)
        records.append(
            dict(
                fname=fname,
                sid=sid,
                rv=rv,
                plate=plate,
                centroids=centroids,
                age_yr=age,
            )
        )
    return records


def _lines_at(records, per_frame_age):
    """Build one LineOfPosition per frame at the given catalog age(s).

    records: from _load_frames.
    per_frame_age: either a scalar age applied to every frame, or a callable
        record -> age_yr (used to age each frame to its own epoch).
    Returns: list of LineOfPosition (target star only).
    """
    lines = []
    for rec in records:
        age = per_frame_age(rec) if callable(per_frame_age) else per_frame_age
        cat = load_aged_catalog(CATALOG_CSV, age, rv_fill_kms=rec["rv"])
        matches = identify_in_frame(
            rec["plate"],
            rec["centroids"]["xy"],
            cat["positions_au"],
            match_radius_arcsec=MATCH_RADIUS_ARCSEC,
        )
        for m in matches:
            si = m["star_index"]
            if int(cat["source_id"][si]) != rec["sid"]:
                continue
            direction = measured_direction(
                rec["plate"], rec["centroids"]["xy"][m["centroid_index"]]
            )
            lines.append(
                LineOfPosition(
                    star_pos_au=cat["positions_au"][si],
                    direction_unit=direction,
                    star_source_id=rec["sid"],
                    sep_arcsec=m["sep_arcsec"],
                    image_name=rec["fname"],
                )
            )
    return lines


def main():
    """Run the fix + age estimate on the two real frames and print results."""
    records = _load_frames()
    print("=== GalNav GUI real-data smoke: New Horizons, 2 LORRI frames ===")
    for rec in records:
        n = rec["centroids"]["xy"].shape[0]
        print(
            f"  {rec['fname']}: source={rec['plate'].source}, "
            f"{rec['plate'].width}x{rec['plate'].height}px, "
            f'scale={rec["plate"].scale_arcsec_per_px:.3f}"/px, '
            f"age={rec['age_yr']:.4f} yr, {n} centroids"
        )

    # Fix at each frame's own epoch (correct: Proxima/Wolf imaged hours apart).
    lines = _lines_at(records, lambda rec: rec["age_yr"])
    print(f"\n  built {len(lines)} line(s) of position:")
    for ln in lines:
        name = {PROXIMA_ID: "Proxima Cen", WOLF_ID: "Wolf 359"}.get(
            ln.star_source_id, str(ln.star_source_id)
        )
        print(f'    {name} in {ln.image_name}: match residual {ln.sep_arcsec:.2f}"')

    fix = fix_position(lines, rmssig_arcsec=RMSSIG_ARCSEC)
    miss = float(np.linalg.norm(fix["x_au"] - NEWH_X_JPL))
    r_au = float(np.linalg.norm(fix["x_au"]))
    print("\n  FIX:")
    print(f"    recovered x = {np.round(fix['x_au'], 3)} au  (|r| = {r_au:.2f} au)")
    print(f"    JPL truth   = {NEWH_X_JPL} au")
    print(f"    miss        = {miss:.3f} au")
    print(
        f"    1-sigma ellipsoid = {np.round(fix['ellipsoid_au'], 3)} au "
        f'(rmssig {RMSSIG_ARCSEC}"), chi2 = {fix["chi2"]:.3e}'
    )
    print(
        "    NOTE: a ~1 au miss is expected -- single raw frames, quick "
        "centroids, no aberration correction (~10\" at 14 km/s); Lauer's "
        "0.35 au used 6 averaged, aberration-corrected sightlines per star."
    )

    # Age estimate: scan 0..10 yr, compare to the true mean epoch.
    grid = np.arange(0.0, 10.0 + 1e-9, 0.25)
    age_res = estimate_age(
        lambda a: _lines_at(records, a), grid, rmssig_arcsec=RMSSIG_ARCSEC
    )
    true_age = float(np.mean([rec["age_yr"] for rec in records]))
    print("\n  AGE ESTIMATE (chi2 scan 0..10 yr, step 0.25):")
    print(
        f"    age_hat = {age_res['age_hat_yr']:.3f} +/- "
        f"{age_res['sigma_age_yr']:.3f} yr"
    )
    print(f"    true    = {true_age:.3f} yr (from FITS SPCUTCAL vs J2016.0)")
    print(f"    |age_hat - true| = {abs(age_res['age_hat_yr'] - true_age):.3f} yr")
    return fix, age_res


if __name__ == "__main__":
    main()
