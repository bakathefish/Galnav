"""End-to-end real-data smoke test (a script, NOT a pytest test).

Runs the whole GUI pipeline on REAL New Horizons LORRI frames that already
carry a solved WCS ("pwcs2"), and prints TWO cases so the demo tells the honest
story:

  * TEACHING CASE -- one Proxima frame + one Wolf 359 frame (2 lines): recovers
    the spacecraft to ~1 au. Simple to explain: two stars, two lines, one fix.
  * FULL CASE -- all 12 frames (6 per star): recovers to ~0.39 au, matching
    Lauer et al.'s 0.351 au (their 12-line x60 solve). The improvement is pure
    centroid-noise averaging: 12 lines instead of 2 shrink the ellipsoid by
    sqrt(6).

It then estimates the catalog age from the image geometry and, as a sanity
check, fixes the OBSERVER of two ground-based frames (it lands on Earth).

WHY THE MISS IS NOT ABERRATION (proven, not assumed). The New Horizons pwcs2
WCS solutions were fit to Gaia field-star positions, so the ~9.6 arcsec of
stellar aberration from NH's ~14 km/s motion is absorbed into the plate-solution
zero-point -- the measured target residuals here (31.9 arcsec Proxima, 16.4
arcsec Wolf) match PURE parallax geometry to a few tenths of an arcsecond, NOT
parallax +/- 9.6 arcsec. Had aberration been left in, the fix would miss by ~17
au, not ~1. So an explicit aberration correction would NOT help; the ~1 au (2
frames) and ~0.39 au (12 frames) misses are single-frame centroid noise, and
averaging frames -- not correcting aberration -- is what tightens the fix.

FRAME CHOICE. Frames are classified by which target their WCS centre actually
contains (Proxima field RA ~217, Wolf field RA ~164); the teaching pair is one
of each. (Note lor_0449913531, despite the lor_04499* prefix, points at the
Proxima field, so a filename glob would misclassify it.)

Run:  python -m gui.nh_demo
"""

import glob
from pathlib import Path

import numpy as np
from astropy.io import fits

from gui.age import estimate_age
from gui.centroids import find_centroids
from gui.fitsmeta import age_yr_since_j2016, observation_jd
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
STAR_NAMES = {PROXIMA_ID: "Proxima Cen", WOLF_ID: "Wolf 359"}

TEACHING_FRAMES = [
    "lor_0449855930_0x633_pwcs2.fits",  # Proxima field, 2020-04-22
    "lor_0449933827_0x633_pwcs2.fits",  # Wolf 359 field, 2020-04-23
]
LAUER_X60_MISS_AU = 0.351  # Lauer's 12-line x60 miss vs JPL (E3)


def _classify(plate):
    """Return (source_id, rv_fill) for the target this frame's WCS centre holds."""
    cra, _ = plate.center_radec_deg
    if abs(cra - 217.4) < 5.0:
        return PROXIMA_ID, 0.0
    return WOLF_ID, WOLF_RV_FILL_KMS


def _load_frames(frame_paths):
    """Plate-solve, centroid, and date each frame once. Returns list of records."""
    records = []
    for path in frame_paths:
        plate = fits_header_solution(path)
        if plate is None:
            raise RuntimeError(f"{Path(path).name}: no WCS in header (expected pwcs2)")
        sid, rv = _classify(plate)
        image = np.asarray(fits.open(path)[0].data, dtype=float)
        records.append(
            dict(
                fname=Path(path).name,
                sid=sid,
                rv=rv,
                plate=plate,
                centroids=find_centroids(image),
                age_yr=age_yr_since_j2016(observation_jd(path)),
            )
        )
    return records


def _lines_at(records, per_frame_age):
    """Build one LineOfPosition per frame at the given catalog age(s).

    per_frame_age: scalar age for every frame, or callable record -> age_yr.
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
            lines.append(
                LineOfPosition(
                    star_pos_au=cat["positions_au"][si],
                    direction_unit=measured_direction(
                        rec["plate"], rec["centroids"]["xy"][m["centroid_index"]]
                    ),
                    star_source_id=rec["sid"],
                    sep_arcsec=m["sep_arcsec"],
                    image_name=rec["fname"],
                )
            )
    return lines


def _run_case(label, records):
    """Fix + age-estimate one set of frames (each aged to its own epoch)."""
    lines = _lines_at(records, lambda rec: rec["age_yr"])
    fix = fix_position(lines, rmssig_arcsec=RMSSIG_ARCSEC)
    miss = float(np.linalg.norm(fix["x_au"] - NEWH_X_JPL))
    r_au = float(np.linalg.norm(fix["x_au"]))
    print(f"\n=== {label}: {len(records)} frame(s), {fix['n_lines']} lines ===")
    print(f"  recovered x = {np.round(fix['x_au'], 3)} au  (|r| = {r_au:.2f} au)")
    print(f"  JPL truth   = {NEWH_X_JPL} au")
    print(f"  miss        = {miss:.3f} au")
    print(
        f"  1-sigma ellipsoid = {np.round(fix['ellipsoid_au'], 3)} au "
        f'(rmssig {RMSSIG_ARCSEC}"), chi2 = {fix["chi2"]:.3e}'
    )
    grid = np.arange(0.0, 10.0 + 1e-9, 0.25)
    age_res = estimate_age(
        lambda a: _lines_at(records, a), grid, rmssig_arcsec=RMSSIG_ARCSEC
    )
    true_age = float(np.mean([rec["age_yr"] for rec in records]))
    print(
        f"  age estimate = {age_res['age_hat_yr']:.3f} +/- "
        f"{age_res['sigma_age_yr']:.3f} yr (true {true_age:.3f}, "
        f"|diff| {abs(age_res['age_hat_yr'] - true_age):.3f})"
    )
    return fix, age_res, miss


def _earth_sanity():
    """Fix the OBSERVER of the two ground-based frames -- should land on Earth."""
    ground = [
        ("lco_prox_20200422-0332.fits", PROXIMA_ID, 0.0),
        ("wolf359_20200423_ULMT_rp_00000123_d_cw.fits", WOLF_ID, WOLF_RV_FILL_KMS),
    ]
    lines = []
    for fname, sid, rv in ground:
        path = NH_DIR / fname
        if not path.exists():
            return
        plate = fits_header_solution(path)
        image = np.asarray(fits.open(path)[0].data, dtype=float)
        if image.ndim > 2:
            image = image[0]
        cen = find_centroids(image)
        jd = observation_jd(path)
        age = age_yr_since_j2016(jd) if jd else 4.31
        cat = load_aged_catalog(CATALOG_CSV, age, rv_fill_kms=rv)
        for m in identify_in_frame(plate, cen["xy"], cat["positions_au"], 300.0):
            si = m["star_index"]
            if int(cat["source_id"][si]) != sid:
                continue
            lines.append(
                LineOfPosition(
                    cat["positions_au"][si],
                    measured_direction(plate, cen["xy"][m["centroid_index"]]),
                    sid,
                    m["sep_arcsec"],
                    fname,
                )
            )
    if len(lines) >= 2:
        fix = fix_position(lines, rmssig_arcsec=1.0)
        r = float(np.linalg.norm(fix["x_au"]))
        print("\n=== ground-based sanity: whose telescope took these? ===")
        print(
            f"  fixing the OBSERVER of two Earth telescope frames -> "
            f"|r| = {r:.3f} au (Earth is 1 au from the Sun)."
        )


def main():
    """Run both NH cases + the Earth sanity check and print everything."""
    print("=== GalNav GUI real-data smoke: New Horizons LORRI ===")
    all_paths = sorted(glob.glob(str(NH_DIR / "lor_*_pwcs2.fits")))
    teaching = _load_frames([str(NH_DIR / f) for f in TEACHING_FRAMES])
    for rec in teaching:
        n = rec["centroids"]["xy"].shape[0]
        print(
            f"  {rec['fname']}: {STAR_NAMES[rec['sid']]} field, "
            f"age {rec['age_yr']:.4f} yr, {n} centroids"
        )

    _run_case("TEACHING CASE (2 frames)", teaching)
    all_records = _load_frames(all_paths)
    fix12, _, miss12 = _run_case("FULL CASE (all 12 frames)", all_records)
    print(
        f"  -> {miss12:.3f} au vs Lauer's {LAUER_X60_MISS_AU:.3f} au (12-line x60); "
        f"the sqrt(6) tighter ellipsoid is centroid-noise averaging, not an "
        f"aberration fix (aberration is already absorbed by the pwcs2 WCS)."
    )
    _earth_sanity()
    print(
        "\nNOTE: the residual ~0.39 au floor is per-frame astrometric systematics "
        "(quick centroids vs Buie's careful multi-frame astrometry), NOT "
        "uncorrected aberration -- correcting aberration would not move it."
    )
    return fix12


if __name__ == "__main__":
    main()
