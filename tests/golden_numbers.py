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
