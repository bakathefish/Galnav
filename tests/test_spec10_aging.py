"""Spec 10 acceptance tests: the catalog-aging propagator (deterministic
linear-motion kinematics), built INDEPENDENTLY on both sides of the truth
wall.

E6 (the headline experiment) needs stars that move. This card adds the
deterministic straight-line propagator: the truth side moves the TRUE sky,
the nav side ages the CATALOG with its cataloged kinematics, and the two
implementations share only galnav/units.py. All stochastic degradation
(PM-error sampling, missing-RV modeling, binary wobble) is OUT of scope
(that is E6). These six tests pin the geometry, the unit conventions, the
NaN-RV policy, and the vectorized shapes.

AI-authored under the recorded ratification-pending exception (item (v)).
"""

from pathlib import Path

import numpy as np

from galnav.nav.catalog import (
    load_catalog as load_nav_catalog,
    propagate_positions_au as nav_propagate,
    star_velocities_kms as nav_star_velocities_kms,
)
from galnav.truth.sky import (
    load_catalog as load_truth_catalog,
    propagate_positions_au as truth_propagate,
    star_positions_au,
    star_velocities_kms as truth_star_velocities_kms,
)
from galnav.units import AU_PER_PC, KMS_PER_AU_YR, mas_to_rad, radec_to_unit
from tests.golden_numbers import ANGLE_TOL_RAD, RV_DRIFT_AU_PER_YR_AT_30KMS

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)


def _one_star_catalog(ra_deg, dec_deg, dist_au, pmra_mas_yr, pmdec_mas_yr, rv_kms):
    """A length-1 catalog dict (the shape both velocity builders consume)."""
    return {
        "ra_rad": np.deg2rad(np.array([ra_deg])),
        "dec_rad": np.deg2rad(np.array([dec_deg])),
        "dist_au": np.array([dist_au]),
        "pmra_mas_yr": np.array([pmra_mas_yr]),
        "pmdec_mas_yr": np.array([pmdec_mas_yr]),
        "rv_kms": np.array([rv_kms]),
    }


def test_t1_zero_age_identity_both_sides():
    # Propagating 0 years must return the starting positions BIT-for-BIT on
    # both sides. Run on post-fill FINITE velocities (fill NaN RVs first):
    # NaN*0 = NaN would break identity spuriously. Catches any propagator
    # that adds a nonzero baseline or mishandles t=0.
    truth_cat = load_truth_catalog(CATALOG_CSV)
    nav_cat = load_nav_catalog(CATALOG_CSV)
    tv = truth_star_velocities_kms(truth_cat, rv_fill_kms=0.0)
    nv = nav_star_velocities_kms(nav_cat, rv_fill_kms=0.0)
    tpos = star_positions_au(truth_cat)
    npos = nav_cat["star_pos_au"]
    assert np.all(np.isfinite(tv)) and np.all(np.isfinite(nv))
    assert np.array_equal(truth_propagate(tpos, tv, 0.0), tpos)
    assert np.array_equal(nav_propagate(npos, nv, 0.0), npos)


def test_t2_radial_drift_matches_golden():
    # External oracle: a star with pure radial velocity 30 km/s and zero
    # proper motion drifts RV_DRIFT_AU_PER_YR_AT_30KMS au after one Julian
    # year, along the line of sight. Independent of distance and direction.
    from tests.golden_numbers import SPEC10_DRIFT_REL_TOL  # single-source tol

    cat = _one_star_catalog(
        ra_deg=0.0,
        dec_deg=0.0,
        dist_au=AU_PER_PC,  # u_hat = (1, 0, 0)
        pmra_mas_yr=0.0,
        pmdec_mas_yr=0.0,
        rv_kms=30.0,
    )
    u_hat = radec_to_unit(cat["ra_rad"], cat["dec_rad"])
    pos0 = u_hat * cat["dist_au"][:, None]
    v = truth_star_velocities_kms(cat, rv_fill_kms=0.0)
    dr = truth_propagate(pos0, v, 1.0) - pos0  # one Julian year
    drift_au = float(np.linalg.norm(dr))

    rel = abs(drift_au - RV_DRIFT_AU_PER_YR_AT_30KMS) / RV_DRIFT_AU_PER_YR_AT_30KMS
    assert rel < SPEC10_DRIFT_REL_TOL
    # direction: along the line of sight (u_hat)
    assert np.max(np.abs(dr[0] / drift_au - u_hat[0])) <= ANGLE_TOL_RAD


def test_t3_tangential_drift_exactly_one_au_per_year():
    # Exact-by-definition oracle: pm = 1 arcsec/yr (pure pmra*, pmdec = 0)
    # at d = 1 pc gives tangential drift of EXACTLY 1 au/yr, because
    # AU_PER_PC = 648000/pi makes the pc*arcsec -> au conversion cancel to
    # 1.0. THE STAR SITS AT dec = 60 deg (nonzero): with pmdec = 0 the
    # transverse speed is d*pmra* regardless of dec, so a spurious extra
    # cos(dec) factor would give cos(60)=0.5 au/yr -- a hard fail here,
    # while at dec = 0 it would hide (cos 0 = 1). No new golden constant:
    # ANGLE_TOL_RAD (1e-12) is the project's float64 exactness bar.
    #
    # ra = 90 deg is chosen so the motion is (almost) cancellation-free: at
    # ra = 90 the +RA tangent e_east = (-1, 0, 0), so the 1-au drift lands
    # entirely in x while pos0_x = cos(dec)cos(90) ~ 0. Measuring the drift
    # as |propagate(pos0) - pos0| therefore does NOT subtract two ~1-parsec
    # (2e5 au) numbers -- which would lose ~11 digits and blow past 1e-12 --
    # it recovers the ~1-au displacement against a near-zero baseline.
    cat = _one_star_catalog(
        ra_deg=90.0,
        dec_deg=60.0,
        dist_au=AU_PER_PC,  # 1 pc
        pmra_mas_yr=1000.0,
        pmdec_mas_yr=0.0,
        rv_kms=0.0,  # 1000 mas/yr = 1 arcsec/yr
    )
    pos0 = radec_to_unit(cat["ra_rad"], cat["dec_rad"]) * cat["dist_au"][:, None]
    v = truth_star_velocities_kms(cat, rv_fill_kms=0.0)
    drift_au = float(np.linalg.norm(truth_propagate(pos0, v, 1.0) - pos0))
    assert abs(drift_au - 1.0) <= ANGLE_TOL_RAD


def test_t4_truth_and_nav_agree():
    # Cross-implementation agreement to 1e-12 relative, on the real catalog.
    # Agreement CANNOT catch a SHARED wrong convention (both sides carry the
    # same one) -- that load is carried by T2/T3/T5's external oracles, just
    # as the aberration card leaned on SR_ABER_PHI_RAD. What it DOES catch:
    # a transcription divergence between the two independently written
    # kinematics paths. The truth catalog dict carries every key both
    # builders read, so both see identical inputs.
    cat = load_truth_catalog(CATALOG_CSV)
    vt = truth_star_velocities_kms(cat, rv_fill_kms=-30.0)
    vn = nav_star_velocities_kms(cat, rv_fill_kms=-30.0)
    assert np.max(np.abs(vt - vn)) <= ANGLE_TOL_RAD * np.max(np.abs(vn))

    pos = star_positions_au(cat)
    ages = np.array([0.0, 100.0, 200.0])
    pt = truth_propagate(pos, vt, ages)
    pn = nav_propagate(pos, vn, ages)
    assert np.max(np.abs(pt - pn)) <= ANGLE_TOL_RAD * np.max(np.abs(pn))


def test_t5_velocity_construction_and_no_nans():
    # (a) The 554 stars with no Gaia RV must not leak NaNs: with an explicit
    # rv_fill the whole velocity array is finite.
    nav_cat = load_nav_catalog(CATALOG_CSV)
    v_all = nav_star_velocities_kms(nav_cat, rv_fill_kms=-30.0)
    assert np.all(np.isfinite(v_all))

    # (b) Hand-computed velocity for one star at dec = 60 deg, symbol by
    # symbol (explicit reconstruction, independent of the function body):
    #   ra = 30 deg, dec = 60 deg, parallax 100 mas -> d = 10 pc
    #   pmra* = 200 mas/yr (cos dec already in), pmdec = -150 mas/yr,
    #   rv = 25 km/s.
    #   u_hat   = (cos d cos a, cos d sin a, sin d)
    #   e_east  = (-sin a, cos a, 0)
    #   e_north = (-sin d cos a, -sin d sin a, cos d)
    #   v = rv*u_hat + d*(mas_to_rad(pmra*)*e_east
    #                      + mas_to_rad(pmdec)*e_north) * KMS_PER_AU_YR
    a, d = np.deg2rad(30.0), np.deg2rad(60.0)
    d_au = (1000.0 / 100.0) * AU_PER_PC  # 10 pc
    u_hat = np.array([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)])
    e_east = np.array([-np.sin(a), np.cos(a), 0.0])
    e_north = np.array([-np.sin(d) * np.cos(a), -np.sin(d) * np.sin(a), np.cos(d)])
    v_t = d_au * (mas_to_rad(200.0) * e_east + mas_to_rad(-150.0) * e_north)
    v_expected = 25.0 * u_hat + v_t * KMS_PER_AU_YR

    cat = _one_star_catalog(30.0, 60.0, d_au, 200.0, -150.0, 25.0)
    v_built = nav_star_velocities_kms(cat, rv_fill_kms=0.0)[0]
    assert np.max(np.abs(v_built - v_expected)) <= ANGLE_TOL_RAD * np.max(
        np.abs(v_expected)
    )


def test_t6_vectorized_shapes_and_consistency():
    # The propagator handles (N,3) positions + (N,3) velocities + a scalar
    # OR (A,) array of ages with no Python loop over stars or ages. Scalar
    # age -> (N,3); array age -> (A,N,3); and slice a of the array result
    # must equal the scalar-age call at ages[a] (bitwise).
    rng = np.random.default_rng(0)
    n = 5
    pos = rng.standard_normal((n, 3)) * 1.0e5
    vel = rng.standard_normal((n, 3)) * 10.0
    ages = np.array([0.0, 50.0, 200.0])

    for propagate in (truth_propagate, nav_propagate):
        assert propagate(pos, vel, 100.0).shape == (n, 3)
        out = propagate(pos, vel, ages)
        assert out.shape == (len(ages), n, 3)
        for i, age in enumerate(ages):
            assert np.array_equal(out[i], propagate(pos, vel, age))
