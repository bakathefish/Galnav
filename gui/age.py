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
    sigma_centroid_px=0.3,
):
    """Date an image by SINGLE-STAR DRIFT when a position fix is impossible.

    A position fix needs >= 2 distinct nearby stars whose lines of sight cross.
    An old plate often shows just ONE fast-moving nearby star (e.g. a 1953 POSS
    plate with Wolf 359). We can still date it: a nearby star's Gaia position,
    propagated to the wrong epoch, lands off the detected blob; propagated to the
    right epoch, it lands on it. So for each nearby catalog star we scan the age
    grid and track its predicted-position -> nearest-centroid separation
    (arcsec); the epoch is where that separation is minimised.

    Multiple stars/frames are combined by SUMMING squared separations (a
    chi2-like objective); the GLOBAL grid minimum is parabola-refined for a
    sub-grid age, and the reliability guard and reported separation use that
    refined age, not a grid node. (Resolving a sharp true minimum that falls
    between coarse nodes requires a FINE grid AND a refine at the global argmin --
    refining around a coarse local node picks the wrong one.)

    UNCERTAINTY -- physical and grid-invariant. The reported sigma is NOT a curve
    curvature (that swings with the grid step the user picks and is not a real
    error). It is the noise-propagated 1-sigma:

        sigma_age = sigma_centroid / omega_mover                (single mover)
        sigma_age = 1 / sqrt( sum_i (omega_i / sigma_centroid_i)^2 )   (general)

    where omega_i is star i's on-sky angular speed (total proper motion, arcsec/yr,
    = |P x dP/da| / |P|^2 at the fitted age) and sigma_centroid_i is the
    centroiding 1-sigma in arcsec for the frame it is in. Derivation: near the
    minimum the mover's predicted position moves omega arcsec per year of age
    error, so a centroiding error sigma_centroid maps to an age error
    sigma_centroid/omega; independent constraints add in inverse-variance (Fisher).
    sigma_centroid defaults to 0.3 px x the plate scale -- a conservative,
    survey-typical centroiding floor (MC-validated to ~1% against
    perturb-the-centroids trials). Grid-invariant by construction.

    Guard: if the best RMS separation at the refined minimum is >= threshold_arcsec,
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
    self-exclude); see static_occupied_centroids. The mask is a HARD veto (a
    masked centroid cannot be matched). It has NO proper-motion column, so it
    leans on static_tol_px: safe for the low-PM field stars that create decoys
    (2 px over a ~40-66 yr baseline at ~1.7 arcsec/px tolerates ~52 mas/yr), but a
    true blob landing within static_tol_px of a cataloged star is a genuine
    position-only ambiguity the mask cannot resolve (documented; neither a
    best-match exemption -- which would revive the decoy -- nor a uniform soft
    penalty cleanly fixes it, so the honest veto is kept). cone_fn=None keeps the
    plain behaviour sparse fields never need.

    PERFORMANCE. The navigator ages positions linearly (r(t)=r0+v*t, Cartesian),
    so this samples the catalog at ages 0 and 1 to recover (r0, v) per star and
    computes r(a)=r0+a*v analytically at every grid age -- avoiding
    load_aged_catalog's full re-propagation (and its unused ra/dec/dist
    transcendentals) at each of ~1000 fine-grid ages (~10x faster). For a caller
    whose motion is non-linear over the grid (a synthetic ra/dec-linear scene)
    this is a chord approximation whose deviation over a realistic 0.1 deg
    proper-motion arc is < 0.1 arcsec, far below the detection tolerances.

    frames: list of (plate, centroids_xy, name) tuples.
    age_grid_yr: 1-D array of candidate ages (Julian yr since J2016.0), evenly
        spaced; NEGATIVE ages (epochs before 2016) are the whole point here. Use a
        step fine enough to resolve the sharp true minimum (the app uses 0.1 yr).
    aged_catalog_fn: callable age_yr -> dict with positions_au (N,3) and
        source_id (N,); the caller closes over the catalog + rv choice.
    threshold_arcsec: reliability threshold on the refined best RMS separation.
    cone_fn: optional callable plate -> full-depth cone dict (positions_au,
        source_id) or None, for static-star exclusion (default None = off).
    static_tol_px: coincidence radius (pixels) for calling a centroid a static
        cone star (default 2.0, the identification tolerance).
    age0_window_yr: |age| below which a mover's own cone entry is exempt from
        masking (default 1.0 yr; the fastest movers are still within a couple of
        pixels of their catalog spot there).
    sigma_centroid_px: centroiding 1-sigma in PIXELS for the noise-propagated age
        error (default 0.3 px; converted to arcsec per frame by its plate scale).
    Returns: dict with either
        {ok:False, message:<why>} if no star dates the image reliably, or
        {ok:True, mode:"single-star drift", age_hat_yr, sigma_age_yr (or NaN),
         ages, sep_arcsec (RMS-separation curve, arcsec, +inf where the candidate
         set is not all in frame), best_sep_arcsec, n_stars, note}.
    """
    ages = np.asarray(age_grid_yr, dtype=float)
    rad2arcsec = 180.0 / np.pi * 3600.0

    # Linear propagation model (see docstring): (r0, v) from two catalog samples.
    c0 = aged_catalog_fn(0.0)
    c1 = aged_catalog_fn(1.0)
    pos0 = np.atleast_2d(np.asarray(c0["positions_au"], dtype=float))
    vel = np.atleast_2d(np.asarray(c1["positions_au"], dtype=float)) - pos0
    sids = np.atleast_1d(np.asarray(c0["source_id"]))
    row_of = {int(s): k for k, s in enumerate(sids)}

    # Static-star masks (one per frame, age-independent apart from the near-age-0
    # self-exclusion exemption). Cone stars are fetched once per frame; a missing
    # cone (None) simply disables exclusion for that frame -- graceful degrade.
    mask_far = [None] * len(frames)
    mask_near = [None] * len(frames)
    if cone_fn is not None:
        mover_ids = set(int(s) for s in sids)
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

    def seps_at(a):
        """{(frame_index, source_id): nearest-centroid sep (arcsec)} at age a."""
        pos = pos0 + a * vel
        near_zero = abs(a) < age0_window_yr
        out = {}
        for fi, (plate, cen_xy, _name) in enumerate(frames):
            mask = mask_near[fi] if near_zero else mask_far[fi]
            for sid, sep in star_seps_in_frame(
                plate, cen_xy, pos, sids, exclude_centroid_mask=mask
            ).items():
                out[(fi, int(sid))] = sep
        return out

    per_key = {}  # (frame_index, source_id) -> separation array over ages
    for k, a in enumerate(ages):
        for key, sep in seps_at(float(a)).items():
            arr = per_key.get(key)
            if arr is None:
                arr = np.full(len(ages), np.nan)
                per_key[key] = arr
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

    cand_keys = list(cand.keys())
    stack = np.vstack([cand[key] for key in cand_keys])  # (C, A)
    n = stack.shape[0]
    sq = stack**2
    obj = np.where(np.all(np.isfinite(sq), axis=0), np.sum(sq, axis=0), np.inf)
    if not np.isfinite(obj).any():
        return {
            "ok": False,
            "message": "no reliable drift date: candidate stars are never all in "
            "frame at a single age.",
        }

    sep_curve = np.sqrt(obj / n)  # RMS separation per age (arcsec); +inf stays inf

    # Refine the GLOBAL grid minimum to sub-grid resolution (a sharp true minimum
    # can fall between coarse nodes -- resolving it needs a fine grid AND a vertex
    # refine at the global argmin, not a refine around a local coarse node).
    i = int(np.argmin(obj))
    note = ""
    if 0 < i < len(ages) - 1:
        y0, y1, y2 = float(obj[i - 1]), float(obj[i]), float(obj[i + 1])
        curv = y0 - 2.0 * y1 + y2
        if np.all(np.isfinite([y0, y1, y2])) and curv > 0.0:
            h = float(ages[i + 1] - ages[i])
            age_hat = float(ages[i] + h * (y0 - y2) / (2.0 * curv))
        else:
            age_hat = float(ages[i])
    else:
        age_hat = float(ages[i])
        note = "drift minimum at a scan edge -- widen the range to confirm it"

    # Reliability guard + reported separation at the REFINED age (not a grid node).
    seps_hat = seps_at(age_hat)
    present = [
        seps_hat[key] for key in cand_keys if np.isfinite(seps_hat.get(key, np.nan))
    ]
    if not present:
        best_sep = float(np.sqrt(obj[i] / n))  # fall back to the grid node
    else:
        best_sep = float(np.sqrt(np.mean(np.square(present))))
    if best_sep >= threshold_arcsec:
        return {
            "ok": False,
            "message": (
                f"no reliable drift date: best separation {best_sep:.1f} arcsec "
                f"exceeds the {threshold_arcsec:.0f} arcsec reliability threshold."
            ),
        }

    # Physical, grid-invariant sigma: inverse-variance sum of (omega / sigma_c)^2
    # over the stars still in frame at the fitted age (see docstring).
    info = 0.0
    for key in cand_keys:
        if not np.isfinite(seps_hat.get(key, np.nan)):
            continue
        fi, sid = key
        j = row_of.get(sid)
        if j is None:
            continue
        p = pos0[j] + age_hat * vel[j]
        omega = float(np.linalg.norm(np.cross(p, vel[j])) / float(p @ p)) * rad2arcsec
        scale = frames[fi][0].scale_arcsec_per_px
        sigma_c = sigma_centroid_px * scale
        if omega > 0.0 and sigma_c > 0.0:
            info += (omega / sigma_c) ** 2
    sigma_age = float(1.0 / np.sqrt(info)) if info > 0.0 else float("nan")
    if not np.isfinite(sigma_age):
        note = (note + "; " if note else "") + (
            "sigma unavailable (no in-frame mover with finite proper motion at "
            "the minimum)"
        )

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
