"""The physics glue. Turns plate-solved images + the aged public catalog into
a spacecraft position fix, by reusing the project's own navigator:

  - galnav.nav.catalog  ages the catalog forward (proper motion + RV),
  - galnav.nav.triangulate.n_star_solve  intersects the lines of position,
  - galnav.units  owns every arcsec/rad conversion.

TRUTH WALL: everything here is navigator-side. It reads the public Gaia CSV
(catalog DATA a real spacecraft carries) and the observer's own measured pixel
directions. It imports nothing from galnav.truth.
"""

import functools
import os
import warnings
from dataclasses import dataclass

import numpy as np
from astropy.coordinates import SkyCoord

from galnav.nav.catalog import (
    load_catalog,
    propagate_positions_au,
    star_velocities_kms,
)
from galnav.nav.triangulate import n_star_solve
from galnav.units import arcsec_to_rad, deg_to_rad, radec_to_unit


@functools.lru_cache(maxsize=8)
def _load_catalog_cached(csv_path, _mtime):
    """Cache the raw CSV read (catalog + source ids) keyed on path+mtime.

    load_catalog re-parses the ~2000-row CSV (~22 ms) on every call; an age scan
    calls it dozens of times. The returned objects are treated as READ-ONLY by
    load_aged_catalog (the aging math builds fresh arrays), so sharing them is
    safe. _mtime is part of the key so editing the CSV busts the cache.
    """
    catalog = load_catalog(csv_path)
    source_id = np.loadtxt(
        csv_path, delimiter=",", skiprows=1, usecols=0, dtype=np.int64
    )
    return catalog, np.atleast_1d(source_id)


def load_aged_catalog(csv_path, age_yr, rv_fill_kms=0.0):
    """Load the public catalog and propagate it forward by age_yr.

    Wraps the navigator: load_catalog -> star_velocities_kms(rv_fill) ->
    propagate_positions_au(age_yr). The catalog's own source_id column (dropped
    by load_catalog) is re-read from CSV column 0 so matches can be labelled.
    The aged sky coordinates (ra/dec/dist) are recomputed from the aged
    Cartesian positions, so they reflect the propagated, not the epoch, sky.
    The raw CSV read is cached (see _load_catalog_cached) so repeated calls in an
    age scan do not re-parse the file.

    csv_path: path to data/gaia_dr3_nav_subset.csv.
    age_yr: catalog age in Julian years since the J2016.0 epoch (0 = epoch).
    rv_fill_kms: radial velocity (km/s) substituted for stars Gaia has no RV
        for (a documented navigator policy; 0 is a safe default for a demo).
    Returns: dict with
        positions_au: (N, 3) aged BCRS/ICRS positions, au;
        ra_rad, dec_rad: (N,) aged sky coordinates, radians;
        dist_au: (N,) aged distance, au;
        source_id: (N,) int64 Gaia source ids (CSV column 0 order);
        sigma_dist_au: (N,) catalog 1-sigma distance error, au (passthrough).
    """
    key = str(csv_path)
    catalog, source_id = _load_catalog_cached(key, os.path.getmtime(key))
    vel = star_velocities_kms(catalog, rv_fill_kms=rv_fill_kms)
    positions = propagate_positions_au(catalog["star_pos_au"], vel, age_yr)
    dist = np.linalg.norm(positions, axis=1)
    ra = np.arctan2(positions[:, 1], positions[:, 0])
    dec = np.arcsin(np.clip(positions[:, 2] / dist, -1.0, 1.0))
    return {
        "positions_au": positions,
        "ra_rad": ra,
        "dec_rad": dec,
        "dist_au": dist,
        "source_id": np.atleast_1d(source_id),
        "sigma_dist_au": catalog["sigma_dist_au"],
    }


def _unit_to_skycoord(unit_vectors):
    """(K, 3) unit vectors -> ICRS SkyCoord (vectorised)."""
    u = np.atleast_2d(np.asarray(unit_vectors, dtype=float))
    ra = np.rad2deg(np.arctan2(u[:, 1], u[:, 0]))
    dec = np.rad2deg(np.arcsin(np.clip(u[:, 2], -1.0, 1.0)))
    return SkyCoord(ra=ra, dec=dec, unit="deg", frame="icrs")


def identify_in_frame(
    plate, centroids_xy, aged_positions_au, match_radius_arcsec=120.0
):
    """Match catalog stars that fall inside the frame to detected centroids.

    Every aged catalog star's BARYCENTRIC direction (unit vector of its aged
    position) is projected through the WCS to a predicted pixel. Stars landing
    inside the image are matched to the nearest centroid within
    match_radius_arcsec; the matching is one-to-one (a star and a centroid pair
    exactly once, closest pair wins).

    PHYSICS NOTE -- why the match radius is generous. We predict from the
    barycentric direction, but the spacecraft sees the PARALLACTIC direction:
    a spacecraft r au from the barycentre sees a star d au away displaced by up
    to ~r/d rad (47 au vs Proxima's 268,000 au ~ 36 arcsec). Stellar aberration
    from the observer's ~14 km/s motion is another ~9.6 arcsec, but for the New
    Horizons pwcs2 frames it is already absorbed into the plate-solution
    zero-point (the field stars are aberrated by the same amount), so the
    measured residuals here are essentially pure parallax; the 9.6 arcsec is
    only budgeted for FOREIGN images whose WCS did not absorb it. The 120 arcsec
    default swallows both for outer-solar-system demos; push it higher (a UI
    knob) for farther-out spacecraft where r/d grows.

    plate: PlateSolution for this image.
    centroids_xy: (M, 2) detected (x, y) pixel centroids (find_centroids order).
    aged_positions_au: (N, 3) aged catalog positions, au (from load_aged_catalog).
    match_radius_arcsec: match tolerance in arcsec.
    Returns: list of matches, each a dict with
        star_index (int, row into aged_positions_au),
        centroid_index (int, row into centroids_xy),
        sep_arcsec (float, predicted-to-centroid separation),
        predicted_xy (2-tuple, the star's predicted pixel).
    """
    positions = np.atleast_2d(np.asarray(aged_positions_au, dtype=float))
    n_stars = positions.shape[0]
    dist = np.linalg.norm(positions, axis=1)
    units = positions / dist[:, None]

    # Cheap angular gate first: only invert the WCS for stars near the field.
    # Projecting the whole sky through a SIP-distorted WCS makes the inverse
    # solver diverge (and warn) for far-off-field points; the gate keeps just
    # the handful that could possibly land in-frame.
    cra, cdec = plate.center_radec_deg
    center_unit = radec_to_unit(deg_to_rad(cra), deg_to_rad(cdec))
    cosang = units @ center_unit
    half_diag_arcsec = (
        0.5 * np.hypot(plate.width, plate.height) * plate.scale_arcsec_per_px
    )
    gate_rad = arcsec_to_rad(half_diag_arcsec + match_radius_arcsec)
    near_idx = np.nonzero(cosang > np.cos(gate_rad))[0]

    px = np.full(n_stars, np.nan)
    py = np.full(n_stars, np.nan)
    if near_idx.size > 0:
        sky = _unit_to_skycoord(units[near_idx])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            px_near, py_near = plate.wcs.celestial.world_to_pixel(sky)
        px[near_idx] = np.atleast_1d(np.asarray(px_near, dtype=float))
        py[near_idx] = np.atleast_1d(np.asarray(py_near, dtype=float))

    # Pixel-edge convention: pixel-centre index i covers [i-0.5, i+0.5], so the
    # detector spans [-0.5, width-0.5]. Using this (rather than [0, width-1])
    # keeps an exact-corner star in-frame even when the WCS round-trip lands it a
    # sub-picometre outside 0 (measured: pixel (0,0) round-trips to y=-2e-12).
    in_frame = (
        np.isfinite(px)
        & np.isfinite(py)
        & (px >= -0.5)
        & (px <= plate.width - 0.5)
        & (py >= -0.5)
        & (py <= plate.height - 0.5)
    )
    cen = np.atleast_2d(np.asarray(centroids_xy, dtype=float))
    if cen.shape[0] == 0 or not np.any(in_frame):
        return []

    radius_px = match_radius_arcsec / plate.scale_arcsec_per_px
    # Candidate (star, centroid) pairs within the radius, cheapest first.
    candidates = []
    star_ids = np.nonzero(in_frame)[0]
    for si in star_ids:
        d = np.hypot(cen[:, 0] - px[si], cen[:, 1] - py[si])
        ci = int(np.argmin(d))
        if d[ci] <= radius_px:
            candidates.append((float(d[ci]), int(si), ci))
    candidates.sort()  # by pixel separation

    used_star, used_cen, matches = set(), set(), []
    for sep_px, si, ci in candidates:
        if si in used_star or ci in used_cen:
            continue
        used_star.add(si)
        used_cen.add(ci)
        matches.append(
            {
                "star_index": si,
                "centroid_index": ci,
                "sep_arcsec": sep_px * plate.scale_arcsec_per_px,
                "predicted_xy": (float(px[si]), float(py[si])),
            }
        )
    matches.sort(key=lambda m: m["star_index"])
    return matches


def star_seps_in_frame(
    plate,
    centroids_xy,
    aged_positions_au,
    source_ids,
    gate_margin_arcsec=180.0,
    exclude_centroid_mask=None,
):
    """Nearest-centroid separation (arcsec) for every catalog star that projects
    inside the frame -- the primitive for single-star drift dating.

    Same barycentric-direction -> WCS projection as identify_in_frame, but for
    the drift scan we want each in-frame star's raw nearest-centroid distance (no
    match radius, no one-to-one assignment): as a star's catalog age is varied,
    its predicted position sweeps across the frame and this separation traces a
    V whose minimum marks the epoch the image was taken. An angular pre-gate
    keeps the WCS inversion to the handful of stars near the field.

    exclude_centroid_mask lets the caller HIDE some centroids from the nearest-
    neighbour search: any True position is skipped as a match candidate. The
    drift dater passes the static-cone mask (see static_occupied_centroids) so a
    fast-moving star cannot be matched to a detection that is really a catalogued
    STATIC field star -- the fix for the dense-field false minimum. A star whose
    every in-frame centroid is masked simply gets no entry (no reliable match).

    plate: PlateSolution. centroids_xy: (M,2) detected pixels.
    aged_positions_au: (N,3) aged catalog positions, au. source_ids: (N,) ids.
    gate_margin_arcsec: extra angular margin beyond the frame half-diagonal for
        the pre-gate (a star just outside can still project in-frame).
    exclude_centroid_mask: optional (M,) bool; True centroids are ignored as
        match candidates (default None -> all centroids eligible).
    Returns: dict {source_id: nearest_centroid_sep_arcsec} for in-frame stars.
    """
    positions = np.atleast_2d(np.asarray(aged_positions_au, dtype=float))
    dist = np.linalg.norm(positions, axis=1)
    units = positions / dist[:, None]
    cen = np.atleast_2d(np.asarray(centroids_xy, dtype=float))
    ids = np.atleast_1d(np.asarray(source_ids))
    out = {}
    if cen.shape[0] == 0:
        return out

    keep = np.ones(cen.shape[0], dtype=bool)
    if exclude_centroid_mask is not None:
        keep = ~np.asarray(exclude_centroid_mask, dtype=bool)
    if not keep.any():
        return out
    cen_kept = cen[keep]

    cra, cdec = plate.center_radec_deg
    center_unit = radec_to_unit(deg_to_rad(cra), deg_to_rad(cdec))
    cosang = units @ center_unit
    half_diag_arcsec = (
        0.5 * np.hypot(plate.width, plate.height) * plate.scale_arcsec_per_px
    )
    gate_rad = arcsec_to_rad(half_diag_arcsec + gate_margin_arcsec)
    near = np.nonzero(cosang > np.cos(gate_rad))[0]
    if near.size == 0:
        return out

    sky = _unit_to_skycoord(units[near])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        px, py = plate.wcs.celestial.world_to_pixel(sky)
    px = np.atleast_1d(np.asarray(px, dtype=float))
    py = np.atleast_1d(np.asarray(py, dtype=float))
    scale = plate.scale_arcsec_per_px
    for j, si in enumerate(near):
        x, y = px[j], py[j]
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        if x < -0.5 or x > plate.width - 0.5 or y < -0.5 or y > plate.height - 0.5:
            continue
        d_px = float(np.hypot(cen_kept[:, 0] - x, cen_kept[:, 1] - y).min())
        out[int(ids[si])] = d_px * scale
    return out


def static_occupied_centroids(
    plate,
    centroids_xy,
    cone_positions_au,
    cone_source_ids,
    tol_px=2.0,
    exclude_source_ids=None,
):
    """Which detected centroids sit on a catalogued STATIC field star.

    A full-depth Gaia cone (gaiacone.cone_catalog) lists the field stars in the
    footprint at the CATALOG epoch (J2016.0). Nearly all are low-proper-motion,
    so their catalog position IS essentially their plate position -- a static
    marker. A centroid within tol_px of any such projected cone star is that
    star's light, so it CANNOT be the fast-moving nearby star we are drift-dating:
    masking these removes the decoys that create dense-field false minima (a
    high-PM track sweeping the frame passes an unrelated field star closer, at a
    wrong epoch, than it sits to its own true-epoch blob).

    exclude_source_ids names cone stars NOT allowed to mark a centroid. The drift
    dater passes the nearby (mover) catalog's ids here ONLY when the scanned age
    is near 0: at ~J2016.0 every nearby star legitimately sits at its own catalog
    spot, so its own cone entry must not self-exclude the detection it belongs to
    (a modern plate). Away from age 0 the mover has left its catalog spot, so that
    spot is a legitimate static exclusion again and exclude_source_ids is None.

    plate: PlateSolution. centroids_xy: (M,2) detected pixels.
    cone_positions_au: (K,3) cone catalog-epoch positions (unit vectors ok).
    cone_source_ids: (K,) int cone source ids. tol_px: coincidence radius, pixels.
    exclude_source_ids: iterable of ids not permitted to mask (or None).
    Returns: (M,) bool mask; True = centroid coincides with a static cone star.
    """
    cen = np.atleast_2d(np.asarray(centroids_xy, dtype=float))
    mask = np.zeros(cen.shape[0], dtype=bool)
    if cen.shape[0] == 0:
        return mask
    positions = np.atleast_2d(np.asarray(cone_positions_au, dtype=float))
    if positions.shape[0] == 0:
        return mask
    dist = np.linalg.norm(positions, axis=1)
    dist[dist == 0.0] = 1.0
    units = positions / dist[:, None]
    ids = np.atleast_1d(np.asarray(cone_source_ids))
    excl = set(int(s) for s in exclude_source_ids) if exclude_source_ids else set()

    cra, cdec = plate.center_radec_deg
    center_unit = radec_to_unit(deg_to_rad(cra), deg_to_rad(cdec))
    cosang = units @ center_unit
    half_diag_arcsec = (
        0.5 * np.hypot(plate.width, plate.height) * plate.scale_arcsec_per_px
    )
    gate_rad = arcsec_to_rad(half_diag_arcsec + 180.0)
    near = np.nonzero(cosang > np.cos(gate_rad))[0]
    if near.size == 0:
        return mask

    sky = _unit_to_skycoord(units[near])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        px, py = plate.wcs.celestial.world_to_pixel(sky)
    px = np.atleast_1d(np.asarray(px, dtype=float))
    py = np.atleast_1d(np.asarray(py, dtype=float))
    for j, ci in enumerate(near):
        if int(ids[ci]) in excl:
            continue
        x, y = px[j], py[j]
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        if x < -0.5 or x > plate.width - 0.5 or y < -0.5 or y > plate.height - 0.5:
            continue
        mask |= np.hypot(cen[:, 0] - x, cen[:, 1] - y) <= tol_px
    return mask


def measured_direction(plate, centroid_xy):
    """Measured spacecraft->star unit direction from a centroid pixel.

    The WCS maps the centroid pixel to an apparent sky position; that apparent
    direction IS the spacecraft->star line of sight (this is what "apparent
    place" means). We return it as a unit vector for n_star_solve.

    plate: PlateSolution.
    centroid_xy: (x, y) pixel of the star's centroid.
    Returns: (3,) ICRS unit direction vector.
    """
    sky = plate.wcs.celestial.pixel_to_world(
        float(centroid_xy[0]), float(centroid_xy[1])
    ).icrs
    return radec_to_unit(deg_to_rad(sky.ra.deg), deg_to_rad(sky.dec.deg))


@dataclass
class LineOfPosition:
    """One optical constraint: the spacecraft lies on the line through the
    star's known position along the measured direction to it.

    star_pos_au: (3,) aged catalog position of the star, au (barycentric).
    direction_unit: (3,) measured spacecraft->star unit direction.
    star_source_id: int64 Gaia source id of the star.
    sep_arcsec: predicted-to-observed separation at identification (diagnostic).
    image_name: which image this line came from (for reporting).
    """

    star_pos_au: np.ndarray
    direction_unit: np.ndarray
    star_source_id: int
    sep_arcsec: float
    image_name: str


# A pair of lines separated by angle gamma gives the summed-projector matrix a
# smallest eigenvalue of 1 - cos(gamma); below this floor the lines are within
# ~5 arcmin of parallel and the intersection is numerically meaningless.
_PARALLEL_EIG_FLOOR = 1e-6


def fix_position(lines, rmssig_arcsec=1.0):
    """Intersect the lines of position to fix the spacecraft.

    Reuses galnav.nav.triangulate.n_star_solve (weighted), which minimises the
    summed weighted squared perpendicular distances to the lines and returns
    the position x, the unscaled covariance xcov, and chi2. The 1-sigma error
    ellipsoid semi-axes are sqrt(eig(xcov)) * (rmssig in radians), exactly the
    E3 covariance scaling (reproduce_lauer).

    lines: list of LineOfPosition (>= 2, from >= 2 distinct stars).
    rmssig_arcsec: per-measurement angular 1-sigma (arcsec) that scales the
        covariance into an au error ellipsoid.
    Returns: dict with
        x_au: (3,) spacecraft position, au (barycentric);
        cov_au2: (3, 3) unscaled covariance (multiply by rmssig^2 for au^2);
        ellipsoid_au: (3,) 1-sigma semi-axes, au, sorted descending;
        chi2: weighted sum of squared perpendicular distances at x;
        n_lines: number of lines used;
        distinct_stars: number of distinct source ids among the lines.
    Raises ValueError (plain English), with a DISTINCT message for each of: zero
        lines (no nearby star in any frame), one line (single image = a line,
        not a point), all lines from one star, or directions within ~5 arcmin of
        parallel.
    """
    if len(lines) == 0:
        raise ValueError(
            "no nearby (within-20-pc) catalog stars fell inside any frame's "
            "footprint -- pointing is solved, but a position fix needs images "
            "that contain nearby stars (the catalog holds 1,941 of them). A "
            "larger match radius helps only if you expect a nearby star here."
        )
    if len(lines) < 2:
        raise ValueError(
            "need at least 2 lines of position to fix a position; a single "
            "image gives only a line the spacecraft lies on -- add an image of "
            "a different nearby star."
        )
    source_ids = {ln.star_source_id for ln in lines}
    if len(source_ids) < 2:
        raise ValueError(
            "all lines are from the same star, so they are (nearly) parallel "
            "and fix only a line of position, not a point -- add an image of a "
            "different nearby star."
        )
    star_pos = np.array([ln.star_pos_au for ln in lines], dtype=float)
    dirs = np.array([ln.direction_unit for ln in lines], dtype=float)
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)

    projectors = np.eye(3) - dirs[:, :, None] * dirs[:, None, :]
    smallest_eig = float(np.linalg.eigvalsh(projectors.sum(axis=0))[0])
    if smallest_eig < _PARALLEL_EIG_FLOOR:
        raise ValueError(
            "the lines of position are within ~5 arcmin of parallel, so they "
            "do not intersect at a well-defined point -- image stars in more "
            "separated directions."
        )

    x, xcov, chi2 = n_star_solve(star_pos, dirs, weighted=True)
    ellipsoid = np.sqrt(np.linalg.eigvalsh(xcov)) * arcsec_to_rad(rmssig_arcsec)
    return {
        "x_au": x,
        "cov_au2": xcov,
        "ellipsoid_au": np.sort(ellipsoid)[::-1],
        "chi2": float(chi2),
        "n_lines": len(lines),
        "distinct_stars": len(source_ids),
    }
