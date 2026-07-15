"""Spec 7 acceptance test: catalog covariance in W — the map's own error bars.

Until now the navigator trusted the star chart completely: the only error
budget was camera noise. But every catalog distance comes from a parallax
with an error bar, and a star whose distance is fractionally wrong by
sigma_pi/pi is a star slightly out of place — indistinguishable, through
that star, from the SPACECRAFT being out of place. Spec 7 teaches the
navigator's error-bar machinery about this: per-star catalog distance
uncertainty propagates into a dense pair-angle covariance R_cat (dense
because two pairs sharing a star share the SAME distance error), and the
predicted position covariance becomes (J^T R^-1 J)^-1 with
R = sigma_cam^2 I + R_cat.

The frozen hand formula being reproduced (golden PER_STAR_FLOOR_AU,
derivation in journal/spec-7-catalog-covariance.md): one star's floor is
    e = (sigma_pi/pi) x D
with D the SPACECRAFT's distance from the barycenter — the star's own
distance cancels (its misplacement grows with d, the visible fraction
shrinks as 1/d). Valid for far stars (d >> D) at 90-degree geometry; the
tests construct exactly that and separately pin the geometry factors.

These tests import NOTHING from galnav.truth — the first test file living
entirely on the navigator's side of the wall. Both sides read the same
public CSV: that is catalog DATA, not truth state.
"""

from pathlib import Path

import numpy as np

from galnav.nav.catalog import load_catalog
from galnav.nav.estimator import position_covariance
from galnav.nav.measmodel import (
    catalog_angle_covariance,
    pair_angle_dist_jacobian,
    per_star_floor_au,
    predicted_pair_angles,
)
from tests.golden_numbers import (
    CATALOG_FLOOR_REL_TOL,
    JACOBIAN_REL_TOL,
    PC_AU,
    PER_STAR_FLOOR_AU,
    RAD_ARCSEC,
    SOLVER_RECOVERY_TOL_AU,
)

CATALOG_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "gaia_dr3_nav_subset.csv"
)

# Same 7 pairs Specs 4-6 proved the instrument on (never pairs 8 with 9 —
# the 61 Cygni A/B lesson).
PAIRS = np.array([[0, 1], [2, 3], [4, 5], [6, 7], [8, 3], [0, 9], [3, 7]])


def _nav_catalog():
    return load_catalog(CATALOG_CSV)


def _perpendicular_unit(u_hat):
    """A unit vector at exactly 90 degrees to u_hat (robust axis choice)."""
    axis = np.zeros(3)
    axis[np.argmin(np.abs(u_hat))] = 1.0
    w = np.cross(u_hat, axis)
    return w / np.linalg.norm(w)


def test_per_star_floor_matches_hand_formula_at_1pc():
    # THE Spec 7 gate (plan section 6): for far stars at 90-degree
    # geometry, the code's per-star floor must reproduce the frozen hand
    # formula (sigma_pi/pi) x D within 10% at D = 1 pc. Uses the 8 most
    # DISTANT stars (~20 pc): the formula's far-star approximation is then
    # good to ~1e-3, so a pass means the code got the physics right, and a
    # wrong-physics implementation (star's distance instead of the
    # spacecraft's: 20x off; missing transverse projection: 100% off)
    # cannot sneak through. The oracle reads parallax columns straight
    # from the CSV — an independent route with no shared vector math.
    cat = _nav_catalog()
    pos, sd = cat["star_pos_au"], cat["sigma_dist_au"]
    raw = np.genfromtxt(CATALOG_CSV, delimiter=",", names=True)
    idx = np.argsort(np.linalg.norm(pos, axis=1))[-8:]
    for k in idx:
        u_hat = pos[k] / np.linalg.norm(pos[k])
        obs = PC_AU * _perpendicular_unit(u_hat)  # D = 1 pc, beta = 90 deg
        floor = per_star_floor_au(pos[[k]], sd[[k]], obs)[0]
        oracle = PER_STAR_FLOOR_AU(raw["parallax_error"][k] / raw["parallax"][k], 1.0)
        assert abs(floor / oracle - 1.0) < CATALOG_FLOOR_REL_TOL, (
            f"star {k}: floor {floor} au vs hand formula {oracle} au"
        )


def test_dist_jacobian_matches_finite_differences_over_4_decades():
    # The catalog term stands on d(angle)/d(star distance). Same proof
    # style as the Spec 4 position-Jacobian gate: hand-derived sensitivity
    # vs brute-force nudging of one star's distance, across four decades
    # of nudge size, at every entry where the pair actually contains the
    # nudged star. Catches a wrong sign, a wrong 1/r, or a formula that
    # forgot which star moved.
    cat = _nav_catalog()
    stars = cat["star_pos_au"][:10]
    obs = PC_AU * np.array([1.0, -2.0, 3.0]) / np.linalg.norm([1.0, -2.0, 3.0])
    jac = pair_angle_dist_jacobian(stars, obs, PAIRS)
    dists = np.linalg.norm(stars, axis=1)
    units = stars / dists[:, None]
    for k in range(10):  # loop over stars/decades, test style (not trials)
        rows = np.nonzero((PAIRS == k).any(axis=1))[0]
        for h_au in (0.1, 1.0, 10.0, 100.0):
            plus, minus = stars.copy(), stars.copy()
            plus[k] = units[k] * (dists[k] + h_au)
            minus[k] = units[k] * (dists[k] - h_au)
            fd = (
                predicted_pair_angles(plus, obs, PAIRS)
                - predicted_pair_angles(minus, obs, PAIRS)
            ) / (2.0 * h_au)
            rel = np.abs(fd[rows] - jac[rows, k]) / np.abs(jac[rows, k])
            assert np.all(rel < JACOBIAN_REL_TOL), (
                f"star {k}, nudge {h_au} au: worst rel err {rel.max()}"
            )


def test_catalog_covariance_enters_W_and_floors_the_error():
    # Three facts that make R_cat a real error budget and not decoration:
    # (i) with a PERFECT camera the predicted error no longer vanishes —
    # the catalog floor exists; (ii) adding camera noise only ever ADDS
    # error; (iii) two pair angles sharing one uncertain star are
    # PERFECTLY correlated (both are multiples of the same delta_d — a
    # rank-1 error), which a diagonal-W shortcut gets wrong by the full
    # gate width. (iii) is what forces the dense matrix.
    cat = _nav_catalog()
    stars, sd = cat["star_pos_au"][:10], cat["sigma_dist_au"][:10]
    obs = PC_AU * np.array([1.0, -2.0, 3.0]) / np.linalg.norm([1.0, -2.0, 3.0])

    cov0 = position_covariance(stars, obs, PAIRS, 0.0, sigma_dist_au=sd)
    assert cov0.shape == (3, 3)
    assert np.allclose(cov0, cov0.T)
    assert np.all(np.linalg.eigvalsh(cov0) > 0)  # the floor exists

    cov1 = position_covariance(stars, obs, PAIRS, 1.0 / RAD_ARCSEC, sigma_dist_au=sd)
    assert np.all(np.linalg.eigvalsh(cov1 - cov0) > 0)  # noise only adds

    only3 = np.zeros(10)
    only3[3] = sd[3]
    r_cat = catalog_angle_covariance(stars, obs, PAIRS, only3)
    shared = np.nonzero((PAIRS == 3).any(axis=1))[0]  # rows 1, 4, 6
    for a in shared:
        for b in shared:
            if a == b:
                continue
            corr = np.abs(r_cat[a, b]) / np.sqrt(r_cat[a, a] * r_cat[b, b])
            assert abs(corr - 1.0) < CATALOG_FLOOR_REL_TOL, (
                f"pairs {a},{b} share star 3: |corr| {corr}, expected 1"
            )


def test_floor_vanishes_dead_ahead_and_at_home():
    # WHY the floor scales with spacecraft distance: a star dead AHEAD
    # (spacecraft on the Sun-star line) shows no parallax, so its distance
    # error charges nothing; and from home (the barycenter) the whole
    # catalog charges nothing. Both must vanish to machine precision —
    # which only the rejection-vector implementation achieves (the
    # sqrt(1 - dot^2) shortcut leaves ~1e-4 au of cancellation noise).
    cat = _nav_catalog()
    pos, sd = cat["star_pos_au"], cat["sigma_dist_au"]
    k = int(np.argmax(np.linalg.norm(pos, axis=1)))
    u_hat = pos[k] / np.linalg.norm(pos[k])
    ahead = per_star_floor_au(pos[[k]], sd[[k]], PC_AU * u_hat)[0]
    assert ahead < SOLVER_RECOVERY_TOL_AU
    home = per_star_floor_au(pos, sd, np.zeros(3))
    assert np.all(home < SOLVER_RECOVERY_TOL_AU)
