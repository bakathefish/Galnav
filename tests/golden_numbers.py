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
# vel_err_kms and n_runs added 2026-07-15 under the authorized-override
# procedure, provenance [BJ21] full text: "the position and velocity of
# the spacecraft can be determined to within 3 au and 2 km/s" (Abstract,
# Sec. 5), every reported statistic being a MEDIAN of the 3D error
# magnitude over 100 runs with randomly drawn truths (Secs. 3.2, 4.1-4.2).
# Scenario provenance, made precise 2026-07-15 (verification fleet): the
# oft-quoted measured 2.8 au (1.3-5.8) is his Fig. 8, the scenario WITH
# 10 km/s radial velocities; the ANGLES-ONLY scenario these tests mirror
# is his Figs. 9/13, ~10% looser in position (~3.1 au) and identical in
# velocity — the 3.0/2.0 gate values below are the Abstract/Sec-5
# angles-only numbers and are correct as frozen. The 100-run median's own
# sampling fuzz (~10%, confirmed by a 200-seed ensemble: 2.87 +/- 0.27 au)
# is what makes tol_factor 2.0 meaningful. NOTE for the students: plan
# section 7 says "anchor within 30%" while this frozen dict says factor
# 2.0 — the discrepancy is recorded in the logbook (2026-07-15) for your
# ruling; the test uses THIS file, as always.
BAILER_JONES_ANCHOR = dict(
    n_stars=20,  # stars used in the fix (the Sun + the 19 nearest)
    sigma_theta_arcsec=1.0,  # per-angle noise, arcsec
    pos_err_au=3.0,  # expected median 3D position error, au
    vel_err_kms=2.0,  # expected median 3D velocity error, km/s
    n_runs=100,  # runs behind the median, per [BJ21]
    tol_factor=2.0,  # a test passes within this factor (two-sided)
)

# --- Anchor: New Horizons parallax observations --------------------------------
NH_PROXIMA_SHIFT_ARCSEC = 32.4  # Lauer et al. 2025, NOT 36
NH_WOLF359_SHIFT_ARCSEC = 15.7
NH_DIST_AU = 47.12  # New Horizons distance at observation, au

# --- Hand-derived scale checks --------------------------------------------------
RV_DRIFT_AU_PER_YR_AT_30KMS = 6.33  # au/yr position drift at 30 km/s
BINARY_WOBBLE_MAS_1AU_5PC = 200.0  # mas wobble: 1 au orbit seen from 5 pc
# arcsin(0.1) -- the v << c (Galilean) formula's maximum deflection. The
# exact special-relativistic maximum at 0.1c is 5.7464 deg (26 arcsec
# more); students re-derive this value at the E7 card ([Lauer25] Eq. 1 is
# explicitly the non-relativistic form -- see citations.md, 2026-07-15).
ABERRATION_MAX_DEG_AT_0P1C = 5.74
# r_perp^2 / 2D at D = 157 pc; exact arithmetic gives 656.9 au (0.14% gap,
# already on the logbook's books) -- students re-derive at its spec card.
J0437_CURV_CORR_AU_AT_1PC = 656.0
# Days to drift HALF the 467 km comb spacing (the +/- c*P/2 lock-loss
# window, packing-radius criterion) -- NOT the full comb, which takes 2x
# longer. (Labels corrected 2026-07-15; both values were and are right
# for the half-comb definition: 233.5 km at 1 cm/s = 270.25 d, at
# 1 m/s = 2.70 d.)
COAST_DAYS_467KM_1CM_S = 270.0
COAST_DAYS_467KM_1M_S = 2.7


def SR_ABER_PHI_RAD(beta, theta_rad):
    """Special-relativistic aberration oracle (added 2026-07-15, override).

    The apparent angle from the velocity apex, for a star at true angle
    theta from the apex, seen by an observer moving at beta = v/c:
        phi = atan2(sin(theta), gamma (beta + cos(theta))),
        gamma = 1/sqrt(1 - beta^2).
    Source: [SR-ABER] (Rindler 2006, ch. 4) — the EXACT form, with the
    Lorentz factor ([Lauer25]'s Eq. 1 is the v << c version; see the
    2026-07-15 citations correction). This is the trusted outside answer
    the aberration acceptance test compares the code against — WITHOUT
    it, a consistently Galilean implementation on both sides of the
    truth wall cancels its own error and passes every internal test
    (measured 2026-07-15: it even lands inside the anchor gate).

    Args:
        beta: v/c, dimensionless.
        theta_rad: true angle from the velocity apex, radians.

    Returns:
        Apparent (aberrated) angle from the apex, radians.
    """
    import numpy as np

    gamma = 1.0 / np.sqrt(1.0 - beta**2)
    return np.arctan2(np.sin(theta_rad), gamma * (beta + np.cos(theta_rad)))


def PER_STAR_FLOOR_AU(sigma_pi_over_pi, D_pc):
    """v1.1-A per-star catalog floor.

    Args:
        sigma_pi_over_pi: fractional parallax error (dimensionless).
        D_pc: the SPACECRAFT's distance from the barycenter, in parsecs.
            NOT the star's distance -- the star's own distance cancels
            (its misplacement grows with d while the visible transverse
            fraction shrinks as 1/d; derivation D7, spec-7 journal).
            Passing the star's distance overstates the floor ~20x at the
            Spec 7 test geometry. (Docstring corrected 2026-07-15 under
            the authorized-override procedure; formula and value
            untouched.)

    Returns:
        Position-error floor contributed by that star, in au (valid for
        far stars, d >> D, at 90-degree Sun-craft-star geometry).
    """
    return sigma_pi_over_pi * D_pc * PC_AU


# --- Test tolerances (proven 2026-07-14, see journal/logbook.md) --------------
# A tolerance = wiggle room. Computers round every decimal a tiny bit, so tests
# ask "within this much of correct?", never "exact?". Each value below sits far
# ABOVE the measured rounding noise (correct code always passes) and far BELOW
# any real mistake (wrong code always fails).

# Angle agreement, radians. (Evidence re-measured 2026-07-15, science
# audit.) Against a 50-digit reference, angle_between's true rounding
# error on 20,000 random pairs is up to ~1.1e-13 (the original 3.6e-14
# came from scale-invariance trials, which understate it); at the
# suite's closest pair (61 Cygni A/B, ~60 arcsec from the test observer)
# arccos amplifies rounding by 1/sin(angle) to ~8e-13 -- inside this
# gate, but with thin margin. A real formula error overshoots by ~1e9x.
# The 61 Cyg pair's gating is an OPEN STUDENT DECISION (see logbook
# 2026-07-15); the value here is unchanged.
ANGLE_TOL_RAD = 1e-12

# "1 pc / 1 au / 1 arcsec" definition check, relative. (Evidence corrected
# 2026-07-15, science audit.) The test computes arctan(1/PC_AU)*RAD_ARCSEC
# with the SAME rounded constant in both roles, so PC_AU's rounding error
# cancels identically; the true measured gap is the arctan cubic term
# 1/(3*PC_AU^2) = 7.8e-12, making this gate ~130,000x safe (not the 840x
# previously claimed -- the old 1.2e-9 figure was PC_AU's rounding vs the
# exact 648000/pi, a comparison the test never performs).
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

# --- Solver gates (proven 2026-07-14, see journal/logbook.md) -----------------
# With a PERFECT camera (zero noise) the solver has no excuse: it must land
# on the exact true position, limited only by rounding dust. Measured floor
# from four different 1000-au starting offsets: worst 3.4e-10 au. This gate
# sits 29x above that floor -- and 1e-8 au is about 1.5 km of error on a
# five-light-year problem, a part in 3e14, so "machine precision" is honest.
# (Analogy corrected 2026-07-15: the old "golf ball across five light-years"
# overstated the precision ~35,000x; the value itself was and is right.)
SOLVER_RECOVERY_TOL_AU = 1e-8

# The solver stops iterating once its correction step shrinks below this
# (in au). 1e-9 au sits above the rounding floor but far below anything
# physical; measured: reaching it takes 4 rounds from a 1000-au offset.
SOLVER_STEP_TOL_AU = 1e-9

# Velocity twins of the two gates above, for the 6-state (position +
# velocity) solver — added 2026-07-15 under the authorized-override
# procedure, same "honestly above the measured floor" pattern:
# noiseless velocity-recovery floors measured across three independent
# prototype geometries (10% starts, speeds 0 to 0.5c) were
# 8.6e-11..6.2e-10 km/s, so 1e-8 km/s sits >= 16x above the floor —
# while omitting the Lorentz gamma at 0.3c misses by ~12 orders more.
# Post-convergence step rattle measured <= 1.7e-10 km/s; 1e-9 km/s is
# reached in <= 7 rounds from a 10% start, inside SOLVER_MAX_ITERS.
SOLVER_RECOVERY_TOL_KMS = 1e-8
SOLVER_STEP_TOL_KMS = 1e-9

# Project-plan gate: convergence in fewer than 10 rounds from a good start.
# Measured: 4 rounds from every direction tried -- 2.5x headroom. Slow
# creep past 10 would mean the Jacobian and residual disagree (a bug), as
# healthy Gauss-Newton doubles its correct digits every round.
# 6-state note (2026-07-15): the velocity+aberration anchor batch (100
# heterogeneous runs to 0.5c) meets the dual step tolerance at exactly
# round 10 at the committed seed -- zero headroom there; the anchor test
# gates the medians, not the round count, and the damped solver returns
# its best-so-far at the cap, so this is recorded rather than relaxed.
SOLVER_MAX_ITERS = 10

# --- Monte Carlo / covariance gates (proven 2026-07-14, see logbook) -----------
# Number of noisy trials per Monte Carlo check (project plan, D4 checkpoint
# and E1 grid). Statistics 101: estimating a scatter from T samples is
# itself fuzzy by about 1/sqrt(2T) -- at 500 trials, ~3.2% per axis.
MC_TRIALS = 500

# The 500-trial scatter must match the theory formula sigma^2 (J^T J)^-1
# within 15% per axis (project plan, D4: "~10-15% at 500 trials"). This is
# a STATISTICS gate, not a precision gate: measured worst per-axis
# disagreement over 20 independent seeds was 10.2% -- pure sampling
# fluctuation, since the same code at any single seed is deterministic. A
# real formula error (wrong J, missing sigma^2, variance where a standard
# deviation belongs) throws the ratio off by 2x or more, far past 15%.
# ("Transposed matrix" removed from the error list 2026-07-15: J^T J is
# exactly symmetric, so transposing it is a no-op and catches nothing.)
MC_CRLB_REL_TOL = 0.15

# Experiment E1 pass criterion (project plan): across every grid cell, the
# Monte Carlo RMS error must track the CRLB prediction within this factor
# in EITHER direction (ratio between 1/1.5 and 1.5). Looser than the
# single-cell 15% gate above because E1 sweeps many geometries, star
# counts, and noise levels -- systematic model breakdown shows up as
# ratios drifting past 1.5x, while measured behavior at the reference
# cell is agreement within ~2%.
E1_CRLB_TRACK_FACTOR = 1.5

# Spec 7 gate (project plan, section 6): the code's per-star catalog floor
# must reproduce the hand formula PER_STAR_FLOOR_AU above within 10%,
# relative, at D = 1 pc. The 10% is the plan's own number. It is honest
# because the hand formula is a far-star approximation: at the tested
# geometry (stars near 20 pc seen from 1 pc, 90-degree placement) the
# formula's built-in error is the D^2/2d^2 term ~ 1.3e-3 -- about 80x
# inside this gate -- while the plausible WRONG physics miss it hugely:
# using the star's own distance instead of the spacecraft's lands 20x off,
# and skipping the transverse projection lands 100% off. (Measured margins
# recorded in journal/spec-7-catalog-covariance.md.)
CATALOG_FLOOR_REL_TOL = 0.10
