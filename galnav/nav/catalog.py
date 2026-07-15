"""NAV SIDE: the public star catalog as the NAVIGATOR holds it — positions,
their quoted uncertainties, and (Spec 10) the cataloged kinematics used to
age the catalog forward in time. Never imports galnav/truth/. Both sides
read the same public CSV: that is catalog DATA (what a real spacecraft
carries), not truth state; the wall forbids truth imports and truth-derived
inputs, not shared public inputs. The propagation math here is written
INDEPENDENTLY of the truth-side version in galnav/truth/sky.py — only the
unit conversions in galnav/units.py are shared (aberration-card precedent)."""

import numpy as np

from galnav.units import (
    KMS_PER_AU_YR,
    deg_to_rad,
    mas_to_rad,
    parallax_mas_to_dist_au,
    radec_to_unit,
)


def load_catalog(csv_path):
    """Read the public Gaia DR3 subset the way the navigator uses it.

    csv_path: path to data/gaia_dr3_nav_subset.csv.
    Returns: dict with
        star_pos_au: (N, 3) catalog star positions, au (BCRS/ICRS, J2016.0),
                     nearest star first;
        sigma_dist_au: (N,) 1-sigma catalog distance error per star, au —
                     first-order parallax propagation: d = 1/pi gives
                     sigma_d = (sigma_pi / pi) * d;
        ra_rad, dec_rad: (N,) sky coordinates, radians (kept so the
                     navigator can rebuild the tangent basis for velocity);
        dist_au: (N,) distance, au;
        pmra_mas_yr, pmdec_mas_yr: (N,) proper motions, mas/yr (pmra is
                     Gaia's pmra* = mu_alpha*cos(dec), cos(dec) included);
        rv_kms: (N,) radial velocity, km/s (NaN where Gaia has none).
    Raises ValueError if any pmra/pmdec is non-finite (propagation needs
    finite proper motion for its "no NaN out" guarantee).
    """
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    ra_rad = deg_to_rad(data["ra"])
    dec_rad = deg_to_rad(data["dec"])
    dist_au = parallax_mas_to_dist_au(data["parallax"])
    pmra = np.asarray(data["pmra"], dtype=float)
    pmdec = np.asarray(data["pmdec"], dtype=float)
    if not np.all(np.isfinite(pmra)) or not np.all(np.isfinite(pmdec)):
        raise ValueError("catalog pmra/pmdec must be finite for propagation")
    return {
        "star_pos_au": radec_to_unit(ra_rad, dec_rad) * dist_au[:, None],
        "sigma_dist_au": (data["parallax_error"] / data["parallax"]) * dist_au,
        "ra_rad": ra_rad,
        "dec_rad": dec_rad,
        "dist_au": dist_au,
        "pmra_mas_yr": pmra,
        "pmdec_mas_yr": pmdec,
        "rv_kms": np.asarray(data["radial_velocity"], dtype=float),
    }


def star_velocities_kms(catalog, rv_fill_kms):
    """Reconstruct each star's 3D velocity from the PUBLIC kinematics.

    Independent twin of galnav/truth/sky.py::star_velocities_kms (only
    galnav/units.py shared). Same physics, deliberately different code:
        v = v_r * u + (d * KMS_PER_AU_YR) * (mu_a* * e_east + mu_d * e_north)
    where u is the star direction, e_east/e_north the local sky tangent
    basis, mu_a*/mu_d the proper motions (mas/yr -> rad/yr; mu_a* already
    holds cos(dec), so no extra cos(dec)), d the distance (au), and v_r the
    radial velocity (km/s). Missing radial velocities (NaN) are replaced by
    rv_fill_kms so the navigator never propagates a NaN.

    catalog: dict from load_catalog (ra_rad, dec_rad, dist_au, pmra_mas_yr,
             pmdec_mas_yr, rv_kms).
    rv_fill_kms: REQUIRED explicit fill (km/s) for stars with no catalog RV
             (no default — the missing-RV policy is a caller decision).
    Returns: (N, 3) velocity vectors, km/s, with no NaNs.
    """
    a, d = catalog["ra_rad"], catalog["dec_rad"]
    ca, sa = np.cos(a), np.sin(a)
    cd, sd = np.cos(d), np.sin(d)
    u = np.stack([cd * ca, cd * sa, sd], axis=-1)
    e_east = np.stack([-sa, ca, np.zeros_like(a)], axis=-1)
    e_north = np.stack([-sd * ca, -sd * sa, cd], axis=-1)
    mu_east = mas_to_rad(catalog["pmra_mas_yr"])  # rad/yr, cos(dec) included
    mu_north = mas_to_rad(catalog["pmdec_mas_yr"])  # rad/yr
    tan_kms = (catalog["dist_au"] * KMS_PER_AU_YR)[:, None]
    v_tan = tan_kms * (mu_east[:, None] * e_east + mu_north[:, None] * e_north)
    rv = np.where(np.isnan(catalog["rv_kms"]), rv_fill_kms, catalog["rv_kms"])
    return rv[:, None] * u + v_tan


def propagate_positions_au(positions_au, velocities_kms, age_yr):
    """Age the catalog: straight-line constant-velocity propagation.

    Independent twin of galnav/truth/sky.py::propagate_positions_au.
    r(t) = r0 + v*t, v converted km/s -> au/yr. Perspective acceleration is
    captured EXACTLY (it is a coordinate artifact of linear motion, not a
    force). NOT modeled: galactic/gravitational acceleration,
    light-travel-time change, and all stochastic catalog degradation (E6).

    positions_au: (N, 3) catalog positions at the catalog epoch, au.
    velocities_kms: (N, 3) velocities, km/s.
    age_yr: scalar age, or (A,) array of ages, Julian years.
    Returns: (N, 3) for a scalar age, else (A, N, 3), au — no Python loop
             over stars or ages.
    """
    r0 = np.asarray(positions_au, dtype=float)
    v_au_yr = np.asarray(velocities_kms, dtype=float) * (1.0 / KMS_PER_AU_YR)
    t = np.asarray(age_yr, dtype=float)
    if t.ndim == 0:
        return r0 + v_au_yr * t
    return r0 + t[:, None, None] * v_au_yr
