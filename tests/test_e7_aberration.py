"""Acceptance tests for E7: relativistic aberration at 0.1c.

AI-authored under the build-night ratification-pending pattern (user granted
full build authority 2026-07-16; card adversarially reviewed by main, APPROVED
WITH AMENDMENTS — all folded). E7 is an EXPERIMENT: the aberration is already
exact special-relativistic on both sides of the truth wall, so E7 does not
modify galnav/. It demonstrates, at an interstellar cruise speed of 0.1c, that
the EXACT relativistic aberration is MANDATORY: a navigator using the classical
(Galilean, Lauer Eq. 1) form is biased by ~1300 au — relativity is the
difference between arriving and being lost.

Three distinct aberration-max quantities are kept separate (do NOT conflate):
  small-angle    beta            = 5.730 deg
  Galilean       arcsin(beta)    = 5.739 deg  (== golden ABERRATION_MAX_DEG_AT_0P1C)
  exact rel.     (gamma form)    = 5.746 deg
The exact-vs-Galilean MAX-deflection gap is 26 arcsec — a Part-A curiosity; the
Part-C payload is the far larger PER-ANGLE difference (~500 arcsec) in the real
hub geometry.

No new golden number is introduced (arcsin(beta) and the exact max are derived;
recovery reuses the deployed solver tolerances).
"""

import numpy as np

from experiments.e7_relativistic_aberration import (
    BETA_CRUISE,
    _classical_aberrate,
    build_network,
    compute,
    galilean_predicted_pair_angles,
    max_deflection,
    replot_from_npz,
    run_ensemble,
    save_outputs,
)
from galnav.truth.observer import observed_pair_angles_moving
from galnav.units import C_KM_S
from tests.golden_numbers import (
    ABERRATION_MAX_DEG_AT_0P1C,
    SOLVER_RECOVERY_TOL_AU,
    SOLVER_RECOVERY_TOL_KMS,
    SR_ABER_PHI_RAD,
)

NETWORK = build_network()  # (stars, pairs) — Sun + 19 nearest bright, 19 hub angles


def test_aberration_max_magnitudes():
    """T1 (Part A): Galilean max = arcsin(0.1); exact max is 26 arcsec larger.

    Checks the aberration magnitudes against the EXACT formulas, not the
    small-angle shortcut. Catches a dropped gamma (would collapse the exact
    max onto the Galilean one) or a small-angle approximation.
    """
    gal_max, _ = max_deflection(BETA_CRUISE, relativistic=False)
    exact_max, _ = max_deflection(BETA_CRUISE, relativistic=True)
    # Galilean maximum is exactly arcsin(beta).
    assert abs(gal_max - np.degrees(np.arcsin(BETA_CRUISE))) < 1e-4
    # ... and matches the frozen golden to its 2-decimal precision.
    assert abs(gal_max - ABERRATION_MAX_DEG_AT_0P1C) < 0.01
    # Exact relativistic maximum: derive the reference INDEPENDENTLY from the
    # SR_ABER_PHI_RAD oracle (fine-grid max of theta - phi) rather than hard-
    # coding 5.7464 — so a change in the oracle can never silently pass.
    theta = np.linspace(1e-6, np.pi - 1e-6, 2_000_001)
    ref_exact_max = np.degrees((theta - SR_ABER_PHI_RAD(BETA_CRUISE, theta)).max())
    assert abs(exact_max - ref_exact_max) < 1e-3
    assert exact_max > gal_max
    gap_arcsec = (exact_max - gal_max) * 3600.0
    assert 25.0 < gap_arcsec < 27.0


def test_gamma_pulls_peak_toward_perpendicular():
    """T2 (Part A discriminator): the exact peak is CLOSER to 90 deg.

    Both forms peak past 90 deg, so "peak > 90" does NOT discriminate. The
    Lorentz factor pulls the exact peak TOWARD perpendicular: exact ~92.9 deg
    sits below the Galilean peak at arccos(-beta) ~95.7 deg. Catches a dropped
    gamma, which T1's value check alone could miss if a magnitude coincided.
    """
    _, gal_peak = max_deflection(BETA_CRUISE, relativistic=False)
    _, exact_peak = max_deflection(BETA_CRUISE, relativistic=True)
    # Galilean peak is exactly arccos(-beta).
    assert abs(gal_peak - np.degrees(np.arccos(-BETA_CRUISE))) < 1e-2
    assert 90.0 < exact_peak < gal_peak  # gamma pulls it toward 90


def test_classical_aberrate_is_wrong_physics_but_sane():
    """T7: the experiment-local classical predictor is the Lauer-Eq.1 form.

    u' = normalize(u + beta): at zero velocity it is the identity; at nonzero
    velocity it shifts a perpendicular star TOWARD the direction of motion
    (same sign as the truth aberration). This is deliberately WRONG physics
    (no gamma) — the whole point of Part C.
    """
    u = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert np.allclose(_classical_aberrate(u, np.zeros(3)), u)  # beta = 0 -> identity
    vel = np.array([0.1, 0.0, 0.0]) * C_KM_S  # 0.1c along +x
    out = _classical_aberrate(np.array([[0.0, 1.0, 0.0]]), vel)[0]  # perp star
    assert out[0] > 0.0  # slid toward +x (the motion)
    assert np.isclose(np.linalg.norm(out), 1.0)


def test_zero_noise_exact_recovery_at_0p1c():
    """T3 (Part B): the EXACT 6-state solver recovers the truth at 0.1c.

    With noise-free measurements, solve_state (the deployed, exact-aberration
    navigator) recovers the true position AND velocity at 0.1c to the deployed
    recovery tolerances — proving the truth and nav aberration implementations
    agree through a full inversion at relativistic speed.
    """
    stars, pairs = NETWORK
    res = run_ensemble(
        stars,
        pairs,
        beta=BETA_CRUISE,
        n_runs=40,
        sigma_arcsec=0.0,
        rng=np.random.default_rng(7),
    )
    assert res["recovery_pos_au_max"] < SOLVER_RECOVERY_TOL_AU
    assert res["recovery_vel_kms_max"] < SOLVER_RECOVERY_TOL_KMS


def test_galilean_navigator_is_catastrophically_biased():
    """T4 (Part C — THE PAYLOAD): ignoring relativity misses by ~1300 au.

    Feed the EXACT (relativistic) measurements to a navigator that uses the
    classical (Galilean) aberration. Its best-fit state is biased far beyond
    any camera-noise error: the median position bias is orders of magnitude
    above both 1 au and the zero-noise recovery floor. Structural gate with a
    concrete floor (no new golden); measured ~1260 au.
    """
    stars, pairs = NETWORK
    res = run_ensemble(
        stars,
        pairs,
        beta=BETA_CRUISE,
        n_runs=40,
        sigma_arcsec=0.0,
        rng=np.random.default_rng(7),
    )
    assert res["galilean_bias_pos_au_median"] > 1.0  # au — vs recovery floor ~1e-9
    assert res["galilean_bias_vel_kms_median"] > 1.0  # km/s
    # the per-angle exact-vs-Galilean difference is ~500 arcsec (NOT 26).
    assert 100.0 < res["dtheta_arcsec_median"] < 2000.0


def test_deterministic_ensemble():
    """T5: same seed -> identical ensemble outputs."""
    stars, pairs = NETWORK
    a = run_ensemble(stars, pairs, BETA_CRUISE, 24, 1.0, np.random.default_rng(3))
    b = run_ensemble(stars, pairs, BETA_CRUISE, 24, 1.0, np.random.default_rng(3))
    assert a["galilean_bias_pos_au_median"] == b["galilean_bias_pos_au_median"]
    assert a["recovery_pos_au_max"] == b["recovery_pos_au_max"]


def test_outputs_and_replot(tmp_path):
    """T6: npz carries every plotted array; the figure regenerates from it."""
    d = compute(n_runs=24, seed=42)
    path = save_outputs(d, out_dir=tmp_path)
    with np.load(path, allow_pickle=True) as z:
        for key in (
            "theta_grid_deg",
            "deflection_galilean_deg",
            "deflection_exact_deg",
            "galilean_bias_pos_au",
            "galilean_bias_vel_kms",
            "beta",
            "seed",
        ):
            assert key in z.files
    png = replot_from_npz(path)
    assert png.exists()
