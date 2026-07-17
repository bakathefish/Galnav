"""Catalog age, both ways.

SET the age -- just call locate.load_aged_catalog(csv, age_yr): the catalog is
propagated forward before matching and solving. That is the whole "set" mode;
there is no extra code here.

ESTIMATE the age -- scan the fix quality (chi2) over a grid of ages and find
the minimum. This works because nearby stars have huge proper motions (Proxima
~3.85 arcsec/yr, Wolf 359 ~4.7 arcsec/yr): a wrong catalog age places each star
many LORRI pixels off its true track, the lines of position stop intersecting
cleanly, and chi2 rises. The chi2-vs-age minimum therefore marks the epoch the
images were actually taken.
"""

import numpy as np

from galnav.units import arcsec_to_rad
from gui.locate import fix_position, star_seps_in_frame, static_occupied_centroids


def estimate_age(build_lines_fn, age_grid_yr, rmssig_arcsec=1.0):
    """Estimate the catalog age from the image geometry via a chi2 scan.

    For each age on the grid, build_lines_fn(age) returns the list of
    LineOfPosition at that catalog age (the caller closes over the plates +
    centroids and re-matches at each age); fix_position(...)["chi2"] scores how
    well the lines intersect. A parabola through the three grid points around
    the minimum gives the sub-grid age and its curvature error:

        age_hat = g1 + h*(y0 - y2) / (2*(y0 - 2*y1 + y2))
        chi2''  = (y0 - 2*y1 + y2) / h^2
        sigma_age = sqrt(2 / chi2'')

    where y0,y1,y2 are the (NORMALISED, see next paragraph) chi2 at the three
    ages spaced by h, and sigma_age is the delta-chi2 = 1 half-width of the
    fitted parabola (chi2 ~ chi2_min + 0.5*chi2''*(age-age_hat)^2). This
    curvature error is honest ONLY when the minimum is interior to the grid and
    the curve is convex there; at an edge or with non-positive curvature it is
    returned as NaN and the raw curve should be inspected.

    NORMALISATION -- why rmssig_arcsec matters. n_star_solve's chi2 is the sum
    of squared PERPENDICULAR line distances weighted by 1/|p_i|^2 (per Lauer);
    with |p_i| ~ 1e5 au it is ~1e-13 in raw units, and the delta-chi2 = 1 rule
    only means "1-sigma" once chi2 is a proper chi-squared normalised by the
    per-measurement angular variance. The perpendicular position error a
    direction error sigma_theta induces at the spacecraft is ~ |p_i|*sigma_theta,
    so the proper statistic is raw_chi2 / sigma_theta^2. We therefore divide the
    curve by arcsec_to_rad(rmssig_arcsec)^2 -- the SAME rmssig that scales the
    position ellipsoid in fix_position (E3 covariance scaling), keeping the
    whole tool coherent. age_hat itself is scale-invariant (the parabola vertex
    does not move); only sigma_age depends on rmssig_arcsec.

    build_lines_fn: callable age_yr -> list[LineOfPosition].
    age_grid_yr: 1-D array of candidate ages (Julian years since J2016.0),
        assumed evenly spaced for the curvature formula.
    rmssig_arcsec: per-measurement angular 1-sigma (arcsec) used to normalise
        the chi2 curve into a proper chi-squared for the delta-chi2 = 1 error.
    Returns: dict with
        age_hat_yr: best-fit age (parabola vertex, or grid argmin at an edge);
        sigma_age_yr: 1-sigma age error from the parabola curvature (NaN if the
            minimum is at an edge, has a non-finite neighbour, or the curvature
            is non-positive);
        ages: the age grid (copy);
        chi2s: NORMALISED chi2 at each grid age (proper chi-squared; +inf at any
            age too degenerate to fix, i.e. fewer than 2 lines);
        note: "" on a clean parabolic fit, else a plain-English reason the
            sigma is unavailable (the caller should print it).
    """
    ages = np.asarray(age_grid_yr, dtype=float)
    norm = arcsec_to_rad(rmssig_arcsec) ** 2

    # Per-age guard: an age that drifts the stars out of the match radius yields
    # < 2 lines and fix_position raises. That age is simply unmatchable, i.e.
    # infinitely bad -- record chi2 = +inf and keep scanning. (Confirmed needed:
    # the app default 0..25 yr at 120" radius throws for ~1/3 of the grid.)
    chi2s = np.empty(len(ages))
    for k, a in enumerate(ages):
        try:
            chi2s[k] = fix_position(build_lines_fn(a))["chi2"] / norm
        except ValueError:
            chi2s[k] = np.inf

    i = int(np.argmin(chi2s))
    unfit = {
        "age_hat_yr": float(ages[i]),
        "sigma_age_yr": float("nan"),
        "ages": ages,
        "chi2s": chi2s,
        "note": "sigma unavailable (chi2 curve not parabolic at minimum -- "
        "widen the match radius or narrow the age grid)",
    }

    # The curvature sigma needs a finite, interior, convex minimum. Fall back to
    # the grid argmin (with sigma = NaN and a note) whenever that fails.
    if i == 0 or i == len(ages) - 1:
        return unfit
    y0, y1, y2 = float(chi2s[i - 1]), float(chi2s[i]), float(chi2s[i + 1])
    if not np.all(np.isfinite([y0, y1, y2])):
        return unfit
    curv = y0 - 2.0 * y1 + y2  # = chi2'' * h^2
    if curv <= 0.0:
        return unfit

    h = float(ages[i + 1] - ages[i])
    age_hat = ages[i] + h * (y0 - y2) / (2.0 * curv)
    chi2_second = curv / (h * h)
    sigma_age = float(np.sqrt(2.0 / chi2_second))
    return {
        "age_hat_yr": float(age_hat),
        "sigma_age_yr": sigma_age,
        "ages": ages,
        "chi2s": chi2s,
        "note": "",
    }


def drift_date(
    frames,
    age_grid_yr,
    aged_catalog_fn,
    threshold_arcsec=3.0,
    cone_fn=None,
    static_tol_px=2.0,
    age0_window_yr=1.0,
):
    """Date an image by SINGLE-STAR DRIFT when a position fix is impossible.

    A position fix needs >= 2 distinct nearby stars whose lines of sight cross.
    An old plate often shows just ONE fast-moving nearby star (e.g. a 1953 POSS
    plate with Wolf 359). We can still date it: a nearby star's Gaia position,
    propagated to the wrong epoch, lands off the detected blob; propagated to the
    right epoch, it lands on it. So for each nearby catalog star we scan the age
    grid and track its predicted-position -> nearest-centroid separation
    (arcsec); the epoch is where that separation is minimised.

    Multiple stars/frames are combined by SUMMING squared separations, so the
    objective is chi2-like. The minimum is parabola-refined for a sub-grid age.
    The reported sigma is the parabola's delta-chi2 = 1 half-width AFTER
    normalising the objective by the best-age RMS separation (so reduced chi2 == 1
    at the minimum by construction). CAVEAT -- this is a RESIDUAL-CURVATURE,
    SINGLE-STAR sigma: it measures how sharply the separation rises around the
    minimum, and it ASSUMES the star is the correct match at that minimum. It is
    not an independent accuracy guarantee; a mis-identified star could give a
    sharp-but-wrong minimum. The reliability guard (below) is the real check.

    Guard: if the best RMS separation over the whole scan is >= threshold_arcsec,
    no star tracks a detection well enough to trust -- return ok=False.

    STATIC-STAR EXCLUSION (cone_fn) -- the dense-field fix. In a crowded
    galactic-plane field a fast mover's track (Barnard is 10.4 arcsec/yr) sweeps
    the whole frame and, at some WRONG epoch, passes an unrelated bright field
    star closer than it ever sits to its own true-epoch blob -- a false minimum
    the reliability guard cannot see (the decoy separation is also small). If
    cone_fn is given, each frame's full-depth Gaia cone (its catalogued STATIC
    field stars) masks every centroid that coincides with a cataloged star, so
    the mover can only match a detection where the catalog shows NOTHING -- which
    is exactly where a genuinely moved star lands. Near age 0 (|age| <
    age0_window_yr) the nearby movers still sit at their own catalog spots, so
    their own cone entries are exempted from masking (else a modern plate would
    self-exclude); see static_occupied_centroids. cone_fn=None keeps the plain
    behaviour (sparse fields never needed it).

    frames: list of (plate, centroids_xy, name) tuples.
    age_grid_yr: 1-D array of candidate ages (Julian yr since J2016.0), evenly
        spaced; NEGATIVE ages (epochs before 2016) are the whole point here.
    aged_catalog_fn: callable age_yr -> dict with positions_au (N,3) and
        source_id (N,); the caller closes over the catalog + rv choice.
    threshold_arcsec: reliability threshold on the best RMS separation.
    cone_fn: optional callable plate -> full-depth cone dict (positions_au,
        source_id) or None, for static-star exclusion (default None = off).
    static_tol_px: coincidence radius (pixels) for calling a centroid a static
        cone star (default 2.0, the identification tolerance).
    age0_window_yr: |age| below which a mover's own cone entry is exempt from
        masking (default 1.0 yr; the fastest movers are still within a couple of
        pixels of their catalog spot there).
    Returns: dict with either
        {ok:False, message:<why>} if no star dates the image reliably, or
        {ok:True, mode:"single-star drift", age_hat_yr, sigma_age_yr (or NaN),
         ages, sep_arcsec (RMS-separation curve, arcsec, +inf where the candidate
         set is not all in frame), best_sep_arcsec, n_stars, note}.
    """
    ages = np.asarray(age_grid_yr, dtype=float)

    # Static-star masks (one per frame, age-independent apart from the near-age-0
    # self-exclusion exemption). Cone stars are fetched once per frame; a missing
    # cone (None) simply disables exclusion for that frame -- graceful degrade.
    mask_far = [None] * len(frames)
    mask_near = [None] * len(frames)
    if cone_fn is not None and len(ages) > 0:
        mover_ids = set(
            int(s) for s in np.atleast_1d(aged_catalog_fn(float(ages[0]))["source_id"])
        )
        for fi, (plate, cen_xy, _name) in enumerate(frames):
            try:
                cone = cone_fn(plate)
            except Exception:  # noqa: BLE001 -- offline/absent cone must not crash
                cone = None
            if cone is None:
                continue
            cpos, csids = cone["positions_au"], cone["source_id"]
            mask_far[fi] = static_occupied_centroids(
                plate, cen_xy, cpos, csids, tol_px=static_tol_px
            )
            mask_near[fi] = static_occupied_centroids(
                plate,
                cen_xy,
                cpos,
                csids,
                tol_px=static_tol_px,
                exclude_source_ids=mover_ids,
            )

    per_key = {}  # (frame_index, source_id) -> separation array over ages
    for k, a in enumerate(ages):
        cat = aged_catalog_fn(float(a))
        pos, sids = cat["positions_au"], cat["source_id"]
        near_zero = abs(float(a)) < age0_window_yr
        for fi, (plate, cen_xy, _name) in enumerate(frames):
            mask = mask_near[fi] if near_zero else mask_far[fi]
            for sid, sep in star_seps_in_frame(
                plate, cen_xy, pos, sids, exclude_centroid_mask=mask
            ).items():
                arr = per_key.get((fi, sid))
                if arr is None:
                    arr = np.full(len(ages), np.nan)
                    per_key[(fi, sid)] = arr
                arr[k] = sep

    cand = {
        key: arr
        for key, arr in per_key.items()
        if np.isfinite(arr).any() and np.nanmin(arr) < threshold_arcsec
    }
    if not cand:
        return {
            "ok": False,
            "message": (
                f"no reliable drift date: no catalogued nearby star drifts to "
                f"within {threshold_arcsec:.0f} arcsec of a detection anywhere in "
                f"the {ages[0]:.0f}..{ages[-1]:.0f} yr scan."
            ),
        }

    stack = np.vstack(list(cand.values()))  # (C, A)
    n = stack.shape[0]
    sq = stack**2
    obj = np.where(np.all(np.isfinite(sq), axis=0), np.sum(sq, axis=0), np.inf)
    if not np.isfinite(obj).any():
        return {
            "ok": False,
            "message": "no reliable drift date: candidate stars are never all in "
            "frame at a single age.",
        }

    i = int(np.argmin(obj))
    best_sep = float(np.sqrt(obj[i] / n))
    if best_sep >= threshold_arcsec:
        return {
            "ok": False,
            "message": (
                f"no reliable drift date: best separation {best_sep:.1f} arcsec "
                f"exceeds the {threshold_arcsec:.0f} arcsec reliability threshold."
            ),
        }

    sep_curve = np.sqrt(obj / n)  # RMS separation per age (arcsec); +inf stays inf
    # Normalise by the best-age RMS separation so reduced chi2 == n at the
    # minimum; floor it so a (synthetic) near-perfect fit does not divide by zero.
    denom = max(best_sep, 1e-3) ** 2
    chi2 = obj / denom
    note = ""
    if i == 0 or i == len(ages) - 1:
        age_hat, sigma_age = float(ages[i]), float("nan")
        note = "sigma unavailable (drift minimum at a scan edge -- widen the range)"
    else:
        y0, y1, y2 = float(chi2[i - 1]), float(chi2[i]), float(chi2[i + 1])
        curv = y0 - 2.0 * y1 + y2
        if not np.all(np.isfinite([y0, y1, y2])) or curv <= 0.0:
            age_hat, sigma_age = float(ages[i]), float("nan")
            note = "sigma unavailable (drift curve not parabolic at the minimum)"
        else:
            h = float(ages[i + 1] - ages[i])
            age_hat = float(ages[i] + h * (y0 - y2) / (2.0 * curv))
            sigma_age = float(np.sqrt(2.0 / (curv / (h * h))))
    return {
        "ok": True,
        "mode": "single-star drift",
        "age_hat_yr": age_hat,
        "sigma_age_yr": sigma_age,
        "ages": ages,
        "sep_arcsec": sep_curve,
        "best_sep_arcsec": best_sep,
        "n_stars": n,
        "note": note,
    }
