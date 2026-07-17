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
from gui.locate import fix_position


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
            minimum is at an edge or the curvature is non-positive);
        ages: the age grid (copy);
        chi2s: NORMALISED chi2 at each grid age (proper chi-squared).
    """
    ages = np.asarray(age_grid_yr, dtype=float)
    norm = arcsec_to_rad(rmssig_arcsec) ** 2
    chi2s = np.array([fix_position(build_lines_fn(a))["chi2"] / norm for a in ages])
    i = int(np.argmin(chi2s))

    if i == 0 or i == len(ages) - 1:
        return {
            "age_hat_yr": float(ages[i]),
            "sigma_age_yr": float("nan"),
            "ages": ages,
            "chi2s": chi2s,
        }

    h = float(ages[i + 1] - ages[i])
    y0, y1, y2 = float(chi2s[i - 1]), float(chi2s[i]), float(chi2s[i + 1])
    curv = y0 - 2.0 * y1 + y2  # = chi2'' * h^2
    if curv <= 0.0:
        return {
            "age_hat_yr": float(ages[i]),
            "sigma_age_yr": float("nan"),
            "ages": ages,
            "chi2s": chi2s,
        }

    age_hat = ages[i] + h * (y0 - y2) / (2.0 * curv)
    chi2_second = curv / (h * h)
    sigma_age = float(np.sqrt(2.0 / chi2_second))
    return {
        "age_hat_yr": float(age_hat),
        "sigma_age_yr": sigma_age,
        "ages": ages,
        "chi2s": chi2s,
    }
