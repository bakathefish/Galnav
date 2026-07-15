"""TRUTH SIDE: draw the SAMPLED true sky.

Until now truth used the catalog's central values as the exact true sky, so
the true sky equalled the public catalog bitwise and catalog aging cost
nothing. E6 needs the TRUE sky to differ from the catalog by the cataloged
uncertainties. This module scatters each star's parallax, proper motion, and
radial velocity by their catalog error bars — and, crucially, gives the 554
stars whose catalog RV is missing a real ~30 km/s radial motion the navigator
cannot see (the dominant aging term).

TRUTH-side only: the navigator never imports this. It shares only unit
conversions (galnav/units.py) and the truth-side velocity builder
(galnav/truth/sky.py, same side of the wall).

What this does NOT model (documented simplifications, see the E6a journal):
- ra/dec angle errors (transverse position ~3-4 orders below the parallax
  term — measured, recorded in the journal); not sampled.
- pmra/pmdec correlations and the other Gaia correlation coefficients:
  independent Gaussians per the plan's error list (the pmra/pmdec cross-term
  rides orthogonal tangent vectors and PM aging is ~4-5 orders below the
  missing-RV term — recorded); ratification-flagged.
- binary-companion contamination: NOT here (the plan gives an amplitude but
  no contaminated fraction; inventing one would be fake science). Deferred
  with a prominent flag for the students to source the fraction.
"""

import numpy as np

from galnav.truth.sky import star_velocities_kms
from galnav.units import parallax_mas_to_dist_au, radec_to_unit


def sample_true_skies(catalog, n_trials, rng, missing_rv_scale_kms):
    """Draw n_trials true skies by scattering the catalog by its errors.

    Sampling is done in PARALLAX space (Gaia's errors are Gaussian in
    parallax, not in distance) and each error source is an independent
    Gaussian. For each trial and star, drawing standard normals z:
        parallax:  plx + sigma_plx * z    -> distance = 1/parallax
        pmra*:     pmra + sigma_pmra * z   (Gaia pmra already carries cos dec)
        pmdec:     pmdec + sigma_pmdec * z
        radial v:  finite-RV stars -> rv + sigma_rv * z;
                   missing-RV stars -> missing_rv_scale_kms * z (zero-mean:
                   the navigator's best guess is 0, so truth scatters the
                   true RV around 0 at the given scale).
    The z streams are drawn in a FIXED order — parallax, pmra, pmdec, rv,
    each shape (n_trials, N) — so a fixed rng seed reproduces the sky exactly
    (relied on by the E6a exact-reconstruction test).

    catalog: dict from galnav.truth.sky.load_catalog. Uses ra_rad, dec_rad
        (radians, (N,)); parallax_mas, parallax_error_mas (mas);
        pmra_mas_yr, pmra_error_mas_yr, pmdec_mas_yr, pmdec_error_mas_yr
        (mas/yr); rv_kms, rv_error_kms (km/s, NaN where the RV is missing).
    n_trials: number of independent true skies to draw (count).
    rng: np.random.Generator — ALL randomness flows through here; no global
        seed.
    missing_rv_scale_kms: 1-sigma radial-velocity scale (km/s) assigned to
        stars with no catalog RV. REQUIRED (no default) — the missing-RV
        policy is the caller's explicit choice (plan section 7: ~30 km/s).
    Returns: (positions_au, velocities_kms), each of shape
        (n_trials, N, 3), au and km/s, at the catalog epoch (J2016.0). No
        NaNs.
    Raises ValueError if any sampled parallax is <= 0 (distance = 1/parallax
        would be non-physical). Our subset has parallax_over_error > 10 (min
        ~16), so a non-positive draw is astronomically unlikely and this
        guard should never fire in practice; it exists so a future looser
        catalog cannot silently produce garbage distances.
    """
    ra, dec = catalog["ra_rad"], catalog["dec_rad"]
    n_stars = ra.shape[0]
    shape = (n_trials, n_stars)
    z_plx = rng.standard_normal(shape)
    z_pmra = rng.standard_normal(shape)
    z_pmdec = rng.standard_normal(shape)
    z_rv = rng.standard_normal(shape)

    sampled_plx = (
        catalog["parallax_mas"][None, :]
        + catalog["parallax_error_mas"][None, :] * z_plx
    )
    if np.any(sampled_plx <= 0.0):
        raise ValueError("sampled parallax <= 0; distance = 1/parallax undefined")
    sampled_dist = parallax_mas_to_dist_au(sampled_plx)

    u_hat = radec_to_unit(ra, dec)  # (N, 3)
    positions = u_hat[None, :, :] * sampled_dist[..., None]  # (T, N, 3)

    sampled_pmra = (
        catalog["pmra_mas_yr"][None, :] + catalog["pmra_error_mas_yr"][None, :] * z_pmra
    )
    sampled_pmdec = (
        catalog["pmdec_mas_yr"][None, :]
        + catalog["pmdec_error_mas_yr"][None, :] * z_pmdec
    )
    finite = np.isfinite(catalog["rv_kms"])
    sampled_rv = np.where(
        finite[None, :],
        catalog["rv_kms"][None, :] + catalog["rv_error_kms"][None, :] * z_rv,
        missing_rv_scale_kms * z_rv,
    )

    sampled_catalog = {
        "ra_rad": ra,
        "dec_rad": dec,
        "dist_au": sampled_dist,
        "pmra_mas_yr": sampled_pmra,
        "pmdec_mas_yr": sampled_pmdec,
        "rv_kms": sampled_rv,
    }
    # sampled_rv is already NaN-free, so rv_fill_kms is never consulted.
    velocities = star_velocities_kms(sampled_catalog, rv_fill_kms=0.0)
    return positions, velocities
