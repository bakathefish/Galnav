"""E6a acceptance tests: the truth-side SAMPLED sky.

Today truth treats the catalog's central values as the exact true sky, so
truth == the nav catalog bitwise and aging costs nothing. E6 needs the TRUE
sky to differ from the catalog by the cataloged uncertainties. This card
builds galnav/truth/sampling.py::sample_true_skies, which draws T true skies
by scattering each star's parallax, proper motion, and radial velocity by
their catalog error bars (and giving the 554 RV-less stars a real ~30 km/s
radial motion the navigator cannot see). All of this is TRUTH-side.

These five tests need NO new golden numbers: they lean on bit-exact
identities (x + 0*z == x; a fixed rng stream reconstructed in the same
order) rather than statistical gates.

AI-authored under the recorded ratification-pending exception (item (w)).
"""

from pathlib import Path

import numpy as np

from galnav.truth.sampling import sample_true_skies
from galnav.truth.sky import (
    load_catalog as load_truth_catalog,
    star_velocities_kms,
)
from galnav.units import (
    KMS_PER_AU_YR,
    mas_to_rad,
    parallax_mas_to_dist_au,
    radec_to_unit,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)


def _cat(ra, dec, plx, plx_err, pmra, pmra_err, pmdec, pmdec_err, rv, rv_err):
    """A synthetic catalog dict with the keys sample_true_skies consumes.

    All arguments are same-length sequences; angles in degrees, parallax and
    its error in mas, proper motions and errors in mas/yr, radial velocity
    and error in km/s (NaN allowed in rv/rv_err to model a missing RV).
    """
    plx = np.asarray(plx, float)
    return {
        "ra_rad": np.deg2rad(np.asarray(ra, float)),
        "dec_rad": np.deg2rad(np.asarray(dec, float)),
        "dist_au": parallax_mas_to_dist_au(plx),
        "pmra_mas_yr": np.asarray(pmra, float),
        "pmdec_mas_yr": np.asarray(pmdec, float),
        "rv_kms": np.asarray(rv, float),
        "parallax_mas": plx,
        "parallax_error_mas": np.asarray(plx_err, float),
        "pmra_error_mas_yr": np.asarray(pmra_err, float),
        "pmdec_error_mas_yr": np.asarray(pmdec_err, float),
        "rv_error_kms": np.asarray(rv_err, float),
    }


def _head_star_velocities(catalog, rv_fill_kms):
    """The EXACT pre-generalization body of star_velocities_kms (uses the
    1-D [:, None] indexing). This is the oracle for "the unbatched (N,) path
    is bit-unchanged by the leading-batch-dim generalization" (amendment 3).
    """
    ra, dec = catalog["ra_rad"], catalog["dec_rad"]
    u_hat = radec_to_unit(ra, dec)
    sin_a, cos_a = np.sin(ra), np.cos(ra)
    sin_d, cos_d = np.sin(dec), np.cos(dec)
    e_east = np.stack([-sin_a, cos_a, np.zeros_like(ra)], axis=-1)
    e_north = np.stack([-sin_d * cos_a, -sin_d * sin_a, cos_d], axis=-1)
    pm_east = mas_to_rad(catalog["pmra_mas_yr"])
    pm_north = mas_to_rad(catalog["pmdec_mas_yr"])
    dist = catalog["dist_au"][:, None]
    v_t = dist * (pm_east[:, None] * e_east + pm_north[:, None] * e_north)
    v_t = v_t * KMS_PER_AU_YR
    rv = np.where(np.isfinite(catalog["rv_kms"]), catalog["rv_kms"], rv_fill_kms)
    return rv[:, None] * u_hat + v_t


def test_t1_zero_error_identity():
    # All error columns zero and every RV present: each sampled sky must be
    # the deterministic epoch sky exactly (x + 0*z == x in IEEE754), the same
    # for every trial. Catches any sampler that shifts the central value.
    cat = _cat(
        ra=[10.0, 200.0],
        dec=[20.0, -40.0],
        plx=[100.0, 50.0],
        plx_err=[0.0, 0.0],
        pmra=[300.0, -100.0],
        pmra_err=[0.0, 0.0],
        pmdec=[-200.0, 150.0],
        pmdec_err=[0.0, 0.0],
        rv=[25.0, -10.0],
        rv_err=[0.0, 0.0],
    )
    n_trials = 4
    pos, vel = sample_true_skies(
        cat, n_trials, np.random.default_rng(0), missing_rv_scale_kms=30.0
    )
    u = radec_to_unit(cat["ra_rad"], cat["dec_rad"])
    pos_ref = u * cat["dist_au"][:, None]
    vel_ref = star_velocities_kms(cat, rv_fill_kms=0.0)
    assert pos.shape == (n_trials, 2, 3)
    assert np.array_equal(pos, np.broadcast_to(pos_ref, pos.shape))
    assert np.array_equal(vel, np.broadcast_to(vel_ref, vel.shape))


def test_t2_determinism():
    cat = _cat(
        ra=[0.0, 90.0, 200.0],
        dec=[10.0, 60.0, -30.0],
        plx=[80.0, 120.0, 60.0],
        plx_err=[0.5, 1.0, 0.7],
        pmra=[100.0, -50.0, 30.0],
        pmra_err=[1.0, 2.0, 1.5],
        pmdec=[-80.0, 40.0, -20.0],
        pmdec_err=[1.2, 0.8, 1.1],
        rv=[20.0, np.nan, -15.0],
        rv_err=[3.0, np.nan, 2.0],
    )
    a = sample_true_skies(cat, 5, np.random.default_rng(7), missing_rv_scale_kms=30.0)
    b = sample_true_skies(cat, 5, np.random.default_rng(7), missing_rv_scale_kms=30.0)
    c = sample_true_skies(cat, 5, np.random.default_rng(8), missing_rv_scale_kms=30.0)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert not np.array_equal(a[0], c[0])
    assert not np.array_equal(a[1], c[1])


def test_t3_exact_reconstruction():
    # Draw the SAME rng stream in the documented order and rebuild the sampled
    # sky from the formula; the module must match bit-for-bit. Deterministic
    # exactness instead of a statistical gate -> no tolerance needed.
    cat = _cat(
        ra=[5.0, 95.0, 250.0],
        dec=[15.0, 55.0, -25.0],
        plx=[70.0, 130.0, 90.0],
        plx_err=[0.6, 1.1, 0.9],
        pmra=[110.0, -60.0, 25.0],
        pmra_err=[1.3, 2.1, 1.4],
        pmdec=[-70.0, 45.0, -18.0],
        pmdec_err=[1.1, 0.9, 1.2],
        rv=[22.0, np.nan, -12.0],
        rv_err=[3.1, np.nan, 2.2],
    )
    n_trials, seed, scale = 6, 3, 30.0
    pos, vel = sample_true_skies(
        cat, n_trials, np.random.default_rng(seed), missing_rv_scale_kms=scale
    )

    rng = np.random.default_rng(seed)
    n = len(cat["ra_rad"])
    z_plx = rng.standard_normal((n_trials, n))
    z_pmra = rng.standard_normal((n_trials, n))
    z_pmdec = rng.standard_normal((n_trials, n))
    z_rv = rng.standard_normal((n_trials, n))

    sampled_plx = (
        cat["parallax_mas"][None, :] + cat["parallax_error_mas"][None, :] * z_plx
    )
    sampled_dist = parallax_mas_to_dist_au(sampled_plx)
    u = radec_to_unit(cat["ra_rad"], cat["dec_rad"])
    pos_exp = u[None, :, :] * sampled_dist[..., None]

    sampled_pmra = (
        cat["pmra_mas_yr"][None, :] + cat["pmra_error_mas_yr"][None, :] * z_pmra
    )
    sampled_pmdec = (
        cat["pmdec_mas_yr"][None, :] + cat["pmdec_error_mas_yr"][None, :] * z_pmdec
    )
    finite = np.isfinite(cat["rv_kms"])
    sampled_rv = np.where(
        finite[None, :],
        cat["rv_kms"][None, :] + cat["rv_error_kms"][None, :] * z_rv,
        scale * z_rv,
    )
    scat = {
        "ra_rad": cat["ra_rad"],
        "dec_rad": cat["dec_rad"],
        "dist_au": sampled_dist,
        "pmra_mas_yr": sampled_pmra,
        "pmdec_mas_yr": sampled_pmdec,
        "rv_kms": sampled_rv,
    }
    vel_exp = star_velocities_kms(scat, rv_fill_kms=0.0)

    assert np.array_equal(pos, pos_exp)
    assert np.array_equal(vel, vel_exp)


def test_t4_missing_rv_policy():
    # Star 0 has a finite RV, star 1 has none. pm = 0 and plx_err = 0 so the
    # velocity is purely radial and the distance is exact: the whole velocity
    # is sampled_rv * u_hat. NaN rows must get missing_rv_scale*z (zero-mean),
    # finite rows rv + sigma_rv*z, and NOTHING may come out NaN.
    cat = _cat(
        ra=[0.0, 90.0],
        dec=[0.0, 45.0],
        plx=[100.0, 100.0],
        plx_err=[0.0, 0.0],
        pmra=[0.0, 0.0],
        pmra_err=[0.0, 0.0],
        pmdec=[0.0, 0.0],
        pmdec_err=[0.0, 0.0],
        rv=[50.0, np.nan],
        rv_err=[2.0, np.nan],
    )
    n_trials, seed, scale = 5, 2, 30.0
    _pos, vel = sample_true_skies(
        cat, n_trials, np.random.default_rng(seed), missing_rv_scale_kms=scale
    )
    assert np.all(np.isfinite(vel))  # the no-NaN-out guarantee

    rng = np.random.default_rng(seed)
    n = 2
    rng.standard_normal((n_trials, n))  # z_plx (consumed, unused here)
    rng.standard_normal((n_trials, n))  # z_pmra
    rng.standard_normal((n_trials, n))  # z_pmdec
    z_rv = rng.standard_normal((n_trials, n))
    exp_rv = np.where(
        np.isfinite(cat["rv_kms"])[None, :],
        cat["rv_kms"][None, :] + cat["rv_error_kms"][None, :] * z_rv,
        scale * z_rv,
    )
    u = radec_to_unit(cat["ra_rad"], cat["dec_rad"])
    assert np.array_equal(vel, exp_rv[..., None] * u)
    # star 1's radial motion is genuinely scattered (not a constant fill):
    assert exp_rv[:, 1].std() > 0.0


def test_t5_shapes_and_unbatched_path_unchanged():
    cat = load_truth_catalog(CATALOG_CSV)
    n_trials = 3
    pos, vel = sample_true_skies(
        cat, n_trials, np.random.default_rng(0), missing_rv_scale_kms=30.0
    )
    n = len(cat["ra_rad"])
    assert pos.shape == (n_trials, n, 3) and vel.shape == (n_trials, n, 3)
    assert np.all(np.isfinite(pos)) and np.all(np.isfinite(vel))

    # amendment 3: the unbatched (N,) star_velocities_kms path is bit-for-bit
    # what HEAD produced (the [:, None] form), unchanged by the batch
    # generalization the sampler relies on.
    v_now = star_velocities_kms(cat, rv_fill_kms=-30.0)
    v_head = _head_star_velocities(cat, rv_fill_kms=-30.0)
    assert np.array_equal(v_now, v_head)
