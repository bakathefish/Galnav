"""FROZEN. Every value hand-derived by students. Tooling: read-only.

Every numerical tolerance and anchor value used in acceptance tests lives
here and nowhere else. If a test needs a number that is not in this file,
STOP — the students derive it by hand first.
"""

# --- Physical constants ------------------------------------------------------
AU_KM = 149597870.7  # kilometres per astronomical unit
C_KM_S = 299792.458  # speed of light, km/s
PC_AU = 206264.806  # astronomical units per parsec
RAD_ARCSEC = 206264.806  # arcseconds per radian (same number as PC_AU)

# --- Pulsar comb spacings, c * period, in km ----------------------------------
COMB_KM = {
    "B0531+21": 10073.0,  # 33.6 ms (Crab)
    "B1937+21": 467.0,  # 1.558 ms
    "J0218+4232": 696.0,  # 2.323 ms
    "B1821-24": 916.0,  # 3.054 ms
    "J0030+0451": 1459.0,  # 4.865 ms
    "J0437-4715": 1726.0,  # 5.757 ms
}

# --- Anchor: Bailer-Jones-style star-fix accuracy ------------------------------
BAILER_JONES_ANCHOR = dict(
    n_stars=20,  # stars used in the fix
    sigma_theta_arcsec=1.0,  # per-star angular noise, arcsec
    pos_err_au=3.0,  # expected position error, au
    tol_factor=2.0,  # a test passes within this factor
)

# --- Anchor: New Horizons parallax observations --------------------------------
NH_PROXIMA_SHIFT_ARCSEC = 32.4  # Lauer et al. 2025, NOT 36
NH_WOLF359_SHIFT_ARCSEC = 15.7
NH_DIST_AU = 47.12  # New Horizons distance at observation, au

# --- Hand-derived scale checks --------------------------------------------------
RV_DRIFT_AU_PER_YR_AT_30KMS = 6.33  # au/yr position drift at 30 km/s
BINARY_WOBBLE_MAS_1AU_5PC = 200.0  # mas wobble: 1 au orbit seen from 5 pc
ABERRATION_MAX_DEG_AT_0P1C = 5.74  # arcsin(0.1)
J0437_CURV_CORR_AU_AT_1PC = 656.0  # r_perp^2 / 2D at D = 157 pc
COAST_DAYS_467KM_1CM_S = 270.0  # days to cross the 467 km comb at 1 cm/s
COAST_DAYS_467KM_1M_S = 2.7  # days to cross the 467 km comb at 1 m/s


def PER_STAR_FLOOR_AU(sigma_pi_over_pi, D_pc):
    """v1.1-A per-star catalog floor.

    Args:
        sigma_pi_over_pi: fractional parallax error (dimensionless).
        D_pc: distance to the star, in parsecs.

    Returns:
        Position-error floor contributed by that star, in au.
    """
    return sigma_pi_over_pi * D_pc * PC_AU


# --- Test tolerances (proven 2026-07-14, see journal/logbook.md) --------------
# A tolerance = wiggle room. Computers round every decimal a tiny bit, so tests
# ask "within this much of correct?", never "exact?". Each value below sits far
# ABOVE the measured rounding noise (correct code always passes) and far BELOW
# any real mistake (wrong code always fails).

# Angle agreement, radians. Worst rounding error found in 20,000 stress trials
# of angle_between was 3.6e-14; this is 28x above that, and a real formula
# error would overshoot it by a factor of about a billion.
ANGLE_TOL_RAD = 1e-12

# "1 pc / 1 au / 1 arcsec" definition check, relative. True gap between exact
# geometry and the definition (mostly from our rounded PC_AU constant) is
# 1.2e-9; this sits 840x above it.
PARALLAX_REL_TOL = 1e-6

# Shortcut rule "shift = move/distance" vs exact geometry, relative. The
# shortcut's own built-in error at our closest test star (move/distance =
# 1/1000) is 3.3e-7; this sits 30x above it.
DISPLACEMENT_REL_TOL = 1e-5

# Our sky-coords -> 3D direction math must agree with astropy's
# professional implementation to better than one milliarcsecond (project
# plan gate, week 2). Both compute the same textbook trigonometry, so the
# only allowed disagreement is rounding dust -- 1 mas is a generous but
# meaningful ceiling for "we did the same math."
SKYCOORD_AGREE_MAS = 1.0

# The hand-derived Jacobian (sensitivity of each predicted angle to the
# position guess) must agree with brute-force numerical nudging to one
# part in a million, across FOUR decades of nudge size (project plan gate,
# Spec 4). Nudging has two error sources -- too big a nudge feels the
# curvature, too small drowns in rounding -- and at our geometry both stay
# below ~1e-7 across the whole 0.1..100 au nudge range, so 1e-6 passes
# honest code with margin while any formula error (wrong sign, wrong term,
# missing 1/distance) misses by many orders of magnitude.
JACOBIAN_REL_TOL = 1e-6
