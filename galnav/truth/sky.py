"""TRUTH SIDE: the true sky. Loads the cached Gaia catalog and places
every star at its true 3D position, and (Spec 10) moves the true sky
forward in time along straight lines. The navigator never imports this;
its own kinematics live independently in galnav/nav/catalog.py, sharing
only the unit conversions in galnav/units.py."""

import numpy as np

from galnav.units import (
    KMS_PER_AU_YR,
    deg_to_rad,
    mas_to_rad,
    parallax_mas_to_dist_au,
    radec_to_unit,
)


def load_catalog(csv_path):
    """Read the cached Gaia DR3 subset into plain arrays.

    csv_path: path to data/gaia_dr3_nav_subset.csv.
    Returns: dict, one entry per star (nearest first), with
        ra_rad (radians), dec_rad (radians), dist_au (au),
        pmra_mas_yr (mas/yr; Gaia's pmra IS pmra* = mu_alpha*cos(dec),
            the cos(dec) factor already included),
        pmdec_mas_yr (mas/yr),
        rv_kms (radial velocity, km/s; NaN where Gaia has none — 554 of
            1941 rows — to be filled explicitly by the caller),
        and the RAW catalog uncertainties E6a samples the true sky from
        (kept raw, in parallax space, NOT converted to a distance sigma —
        the errors are Gaussian in parallax, not in distance):
        parallax_mas, parallax_error_mas (mas),
        pmra_error_mas_yr, pmdec_error_mas_yr (mas/yr),
        rv_error_kms (km/s; NaN wherever rv_kms is NaN).
    Raises ValueError if any pmra/pmdec is non-finite: the propagator's
    "no NaN out" guarantee (given an explicit RV fill) relies on every
    star having finite proper motion.
    """
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    pmra = np.asarray(data["pmra"], dtype=float)
    pmdec = np.asarray(data["pmdec"], dtype=float)
    if not np.all(np.isfinite(pmra)) or not np.all(np.isfinite(pmdec)):
        raise ValueError("catalog pmra/pmdec must be finite for propagation")
    return {
        "ra_rad": deg_to_rad(data["ra"]),
        "dec_rad": deg_to_rad(data["dec"]),
        "dist_au": parallax_mas_to_dist_au(data["parallax"]),
        "pmra_mas_yr": pmra,
        "pmdec_mas_yr": pmdec,
        "rv_kms": np.asarray(data["radial_velocity"], dtype=float),
        "parallax_mas": np.asarray(data["parallax"], dtype=float),
        "parallax_error_mas": np.asarray(data["parallax_error"], dtype=float),
        "pmra_error_mas_yr": np.asarray(data["pmra_error"], dtype=float),
        "pmdec_error_mas_yr": np.asarray(data["pmdec_error"], dtype=float),
        "rv_error_kms": np.asarray(data["radial_velocity_error"], dtype=float),
    }


def star_positions_au(catalog):
    """True 3D star positions: unit direction times distance.

    catalog: dict from load_catalog (angles in radians, distances in au).
    Returns: (N, 3) array of BCRS/ICRS positions in au.
    """
    unit = radec_to_unit(catalog["ra_rad"], catalog["dec_rad"])
    return unit * catalog["dist_au"][:, None]


def star_velocities_kms(catalog, rv_fill_kms):
    """True 3D stellar velocity vectors from the cataloged kinematics.

    v = v_r*u_hat + v_t. Symbol by symbol:
      u_hat  — unit direction toward the star (radec_to_unit convention
               (cos d cos a, cos d sin a, sin d)).
      v_r    — radial velocity (km/s) along u_hat; NaN entries (stars with
               no Gaia RV) are replaced by rv_fill_kms so no NaN leaks out.
      v_t    — transverse velocity: d * (pmra*e_east + pmdec*e_north),
               with pmra, pmdec proper motions in mas/yr converted to
               rad/yr, times distance d (au) giving au/yr, then to km/s.
               Gaia's pmra already carries cos(dec) (pmra* = mu_alpha
               cos dec), so it multiplies e_east directly with NO extra
               cos(dec) factor.
      e_east  = (-sin a, cos a, 0)             — +RA tangent unit vector.
      e_north = (-sin d cos a, -sin d sin a, cos d) — +Dec tangent unit
               vector. Both are consistent with radec_to_unit and
               orthonormal to u_hat.

    catalog: dict from load_catalog (ra_rad, dec_rad radians, shape (N,);
             dist_au au; pmra_mas_yr, pmdec_mas_yr mas/yr; rv_kms km/s, may
             be NaN). The kinematic arrays (dist_au, pmra_mas_yr,
             pmdec_mas_yr, rv_kms) may carry LEADING BATCH DIMENSIONS
             (e.g. (T, N) sampled skies from E6a); ra_rad/dec_rad stay (N,)
             and broadcast. With plain (N,) inputs the result is bitwise
             identical to the un-batched Spec 10 version (the only change is
             [:, None] -> [..., None], a no-op for 1-D arrays).
    rv_fill_kms: REQUIRED fill value (km/s) for stars whose catalog RV is
             NaN — no default, so every caller states the policy (E6 will
             pass sampled/true RVs here, not a constant fill).
    Returns: (..., N, 3) velocity vectors, km/s (BCRS/ICRS), no NaNs — shape
             (N, 3) for (N,) input, (T, N, 3) for (T, N) kinematics.
    """
    ra, dec = catalog["ra_rad"], catalog["dec_rad"]
    u_hat = radec_to_unit(ra, dec)
    sin_a, cos_a = np.sin(ra), np.cos(ra)
    sin_d, cos_d = np.sin(dec), np.cos(dec)
    e_east = np.stack([-sin_a, cos_a, np.zeros_like(ra)], axis=-1)
    e_north = np.stack([-sin_d * cos_a, -sin_d * sin_a, cos_d], axis=-1)
    pm_east = mas_to_rad(catalog["pmra_mas_yr"])  # rad/yr, cos(dec) included
    pm_north = mas_to_rad(catalog["pmdec_mas_yr"])  # rad/yr
    dist = catalog["dist_au"][..., None]
    v_t = dist * (pm_east[..., None] * e_east + pm_north[..., None] * e_north)  # au/yr
    v_t = v_t * KMS_PER_AU_YR  # km/s
    rv = np.where(np.isfinite(catalog["rv_kms"]), catalog["rv_kms"], rv_fill_kms)
    return rv[..., None] * u_hat + v_t


def propagate_positions_au(positions_au, velocities_kms, age_yr):
    """Move star positions forward in time along straight lines.

    r(t0 + T) = r(t0) + v*T, with v converted km/s -> au/yr. This exactly
    captures perspective acceleration (the apparent curving of a star's
    sky track is a spherical-coordinate artifact of linear Cartesian
    motion, not a neglected force). It does NOT model galactic /
    gravitational acceleration or light-travel-time change (both
    second-order over <=200 yr at <=20 pc — see the Spec 10 journal), and
    it does NOT model any stochastic degradation (that is E6).

    positions_au: (N, 3) positions at the catalog epoch, au.
    velocities_kms: (N, 3) velocities, km/s.
    age_yr: scalar age, or (A,) array of ages, in Julian years.
    Returns: (N, 3) for a scalar age, or (A, N, 3) for an array of ages,
             au. No Python loop over stars or ages (pure broadcasting).
    """
    positions = np.asarray(positions_au, dtype=float)
    disp_per_yr = np.asarray(velocities_kms, dtype=float) / KMS_PER_AU_YR  # au/yr
    age = np.asarray(age_yr, dtype=float)
    if age.ndim == 0:
        return positions + disp_per_yr * age
    return positions[None, :, :] + age[:, None, None] * disp_per_yr[None, :, :]
