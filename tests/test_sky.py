"""Spec 3 acceptance test: the truth simulator (pretend sky).

Loads the real cached Gaia DR3 subset, places stars at their true 3D
positions, and generates the star-pair angles a spacecraft camera would
measure. Three promises are tested: (1) with noise OFF the simulator's
angles equal independently-computed analytic values to machine precision;
(2) our home-built sky-coords -> 3D direction math agrees with astropy's
professional implementation to better than 1 milliarcsecond; (3) noise is
reproducible -- same seed, same measurements; different seed, different.
"""

from pathlib import Path

import numpy as np

from galnav.geometry import angle_between
from galnav.truth.observer import observed_pair_angles
from galnav.truth.sky import load_catalog, star_positions_au
from galnav.units import radec_to_unit
from tests.golden_numbers import (
    ANGLE_TOL_RAD,
    RAD_ARCSEC,
    SKYCOORD_AGREE_MAS,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

# A made-up but fixed spacecraft position, ~1.8 pc from the Sun, so the
# test exercises genuinely interstellar geometry (setup value, not a
# tolerance).
OBS_POS_AU = np.array([1.0e5, -2.0e5, 3.0e5])


def test_zero_noise_angles_equal_analytic_values():
    # With sigma = 0 the simulator has nowhere to hide: every pair angle
    # must equal the value computed independently, arrow by arrow, with
    # Spec 1's tool. Catches any indexing, sign, or geometry mistake.
    cat = load_catalog(CATALOG_CSV)
    pos = star_positions_au(cat)[:10]  # ten nearest stars
    pairs = np.array([[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]])
    got = observed_pair_angles(pos, OBS_POS_AU, pairs, 0.0, np.random.default_rng(0))
    for k, (i, j) in enumerate(pairs):
        expected = angle_between(pos[i] - OBS_POS_AU, pos[j] - OBS_POS_AU)
        assert abs(got[k] - expected) < ANGLE_TOL_RAD


def test_direction_vectors_agree_with_astropy():
    # Cross-check our ra/dec -> unit-vector conversion against astropy,
    # the tool professional astronomers use. Compared by the length of the
    # difference arrow (the chord), which for tiny angles IS the angle in
    # radians -- and unlike arccos it stays precise near zero.
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    cat = load_catalog(CATALOG_CSV)
    n = 50
    ours = radec_to_unit(cat["ra_rad"][:n], cat["dec_rad"][:n])
    sc = SkyCoord(
        ra=cat["ra_rad"][:n] * u.rad, dec=cat["dec_rad"][:n] * u.rad, frame="icrs"
    )
    theirs = np.stack(
        [sc.cartesian.x.value, sc.cartesian.y.value, sc.cartesian.z.value], axis=-1
    )
    tol_rad = SKYCOORD_AGREE_MAS * 1.0e-3 / RAD_ARCSEC  # mas -> radians
    assert np.all(np.linalg.norm(ours - theirs, axis=1) < tol_rad)


def test_noise_is_reproducible_and_seed_dependent():
    # Same seed must give byte-identical measurements (so every experiment
    # can be rerun exactly); a different seed must give different ones
    # (so the noise is actually random, not constant).
    cat = load_catalog(CATALOG_CSV)
    pos = star_positions_au(cat)[:10]
    pairs = np.array([[0, 1], [2, 3], [4, 5]])
    sigma_rad = 1.0 / RAD_ARCSEC  # 1 arcsec of camera noise, in radians
    a = observed_pair_angles(
        pos, OBS_POS_AU, pairs, sigma_rad, np.random.default_rng(42)
    )
    b = observed_pair_angles(
        pos, OBS_POS_AU, pairs, sigma_rad, np.random.default_rng(42)
    )
    c = observed_pair_angles(
        pos, OBS_POS_AU, pairs, sigma_rad, np.random.default_rng(43)
    )
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
