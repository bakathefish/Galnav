"""Pulsar phase combs and the navigation-ambiguity lattice (public physics).

This module is NEITHER truth nor nav: it holds only PUBLIC facts a real
mission would read from a pulsar catalogue (rotational periods) plus the
textbook geometry of phase-comb navigation. It imports nothing from
galnav/truth or galnav/nav, so it cannot carry state across the truth wall.

The idea, one symbol at a time:
  - A pulsar spins with period P (seconds). A photon time-of-arrival measures
    its rotational PHASE, which is the same after every full turn. So a phase
    measurement fixes the spacecraft's position along the sightline n_hat only
    up to an unknown whole number of turns.
  - One turn of light travel is the COMB SPACING s = c * P (kilometres): the
    distance light covers in one period. Position along n_hat is known modulo s.
  - K pulsars give K such "modulo s_j" constraints. The positions consistent
    with all of them form a LATTICE L = { N^{-1} (s . m) : m in Z^K }, where N
    stacks the K unit sightlines and (s . m) scales integer turn-counts m by the
    comb spacings. The shortest nonzero vector of L is lambda_1; the PACKING
    RADIUS rho = lambda_1 / 2 is the largest position uncertainty for which the
    correct integer turn-count is still unambiguous on every comb.
  - COAST TIME to lost lock: once locked, a velocity error sigma_v drifts the
    position; after T = (s/2) / sigma_v the drift reaches half a comb and the
    integer can slip. That half-comb window is the packing-radius criterion.

Internal units: km for lengths, km/s for velocity, seconds for period, days
for coast time. Only numpy and galnav.units are imported.
"""

import numpy as np

from galnav.units import C_KM_S

SEC_PER_DAY = 86400.0  # SI seconds per day (same convention as units.py)

# The six millisecond/young pulsars of the project's §12 golden table, with
# their rotational periods P in SECONDS (ATNF Pulsar Catalogue values; see
# journal/citations.md [ATNF]). comb_spacing_km(P) reproduces the frozen
# COMB_KM oracles to within 1 km (Spec 8's stated match).
PULSAR_PERIODS_S = {
    "B0531+21": 0.0336,  # Crab, 33.6 ms
    "B1937+21": 0.001558,  # 1.558 ms
    "J0218+4232": 0.002323,  # 2.323 ms
    "B1821-24": 0.003054,  # 3.054 ms
    "J0030+0451": 0.004865,  # 4.865 ms
    "J0437-4715": 0.005757,  # 5.757 ms
}


def comb_spacing_km(period_s):
    """Phase-comb spacing s = c * P.

    period_s: pulsar rotational period in seconds (scalar or array).
    Returns: comb spacing in km (scalar or array), the distance light travels
        in one period -- the along-sightline position ambiguity.
    """
    return C_KM_S * np.asarray(period_s, dtype=float)


def coast_time_days(comb_km, sigma_v_kms):
    """Coast time to lost lock: T = (s/2) / sigma_v, in days.

    Uses the HALF-comb (packing-radius) window: the integer turn-count slips
    once a velocity error has drifted the position by half a comb spacing.

    comb_km: comb spacing s in km (scalar or array).
    sigma_v_kms: velocity uncertainty in km/s (scalar or array).
    Returns: coast time in days (scalar or array).
    """
    comb_km = np.asarray(comb_km, dtype=float)
    sigma_v_kms = np.asarray(sigma_v_kms, dtype=float)
    return 0.5 * comb_km / sigma_v_kms / SEC_PER_DAY


def ambiguity_lattice_generator(sightlines_unit, comb_km):
    """Generator matrix B of the phase-comb ambiguity lattice.

    For K = 3 full-rank sightlines the position is r = N^{-1} (phase + s . m)
    for integer turn-counts m, so the ambiguity offsets are B m with
        B = N^{-1} diag(s),
    where N stacks the unit sightlines as rows.

    sightlines_unit: (3, 3) array of three UNIT sightline vectors (one per
        row). v1 handles exactly K = 3 (square, full rank).
    comb_km: (3,) array of the three comb spacings in km.
    Returns: (3, 3) generator matrix B (entries in km); its integer
        combinations B m are the lattice of position ambiguities, in km.
    """
    N = np.asarray(sightlines_unit, dtype=float)
    s = np.asarray(comb_km, dtype=float)
    if N.shape != (3, 3):
        raise ValueError("v1 ambiguity lattice needs exactly 3 sightlines (3x3)")
    return np.linalg.inv(N) @ np.diag(s)


def shortest_vector_km(B, search=2):
    """Shortest nonzero lattice vector lambda_1, by bounded enumeration.

    Enumerates integer turn-count vectors m in [-search, search]^3 and returns
    the smallest nonzero ||B m||. This ASSUMES a well-conditioned N (spread-out
    sightlines): then the shortest vector is a small-integer combination, so a
    radius-2 box suffices (radius 1 already finds it for orthonormal
    sightlines). For a near-degenerate N the true lambda_1 could be a
    larger-integer combination needing a bigger search box. This is NOT a
    general closest-vector solver -- that (LAMBDA/LLL or fpylll) is a deferred
    follow-up card.

    B: (3, 3) lattice generator (from ambiguity_lattice_generator), km.
    search: dimensionless integer half-width of the turn-count search box
        (default 2).
    Returns: lambda_1 in km (scalar).
    """
    B = np.asarray(B, dtype=float)
    rng = range(-search, search + 1)
    best = np.inf
    for i in rng:
        for j in rng:
            for k in rng:
                if i == 0 and j == 0 and k == 0:
                    continue
                v = B @ np.array([i, j, k], dtype=float)
                best = min(best, float(np.linalg.norm(v)))
    return best


def packing_radius_km(B, search=2):
    """Packing radius rho = lambda_1 / 2 of the ambiguity lattice.

    The largest position uncertainty for which the correct integer turn-count
    is still unambiguous on every comb.

    B: (3, 3) lattice generator, km.
    search: dimensionless integer half-width, passed through to
        shortest_vector_km.
    Returns: packing radius in km (scalar).
    """
    return 0.5 * shortest_vector_km(B, search=search)


def closest_lattice_point(B, targets_km):
    """Closest lattice point: which integer turn-counts m best explain t?

    A phase-comb fix pins position only up to an integer turn-count vector
    m (one whole turn per pulsar). Given a measured position offset t, the
    turn-counts most consistent with it are the ones whose lattice point B m
    sits nearest to t -- the CLOSEST-LATTICE-POINT (integer least-squares)
    problem

        m_hat = argmin over m in Z^3 of || B m - t ||       [km]

    The recipe, one symbol at a time:
      - `B^{-1} t` gives the (generally NON-integer) turn-counts that would
        land exactly on t. Rounding each coordinate to the nearest whole
        number is BABAI's nearest-lattice-point estimate [Babai86]:
            m0 = round( B^{-1} t ).
      - Babai's m0 can be off by one in a skewed (non-orthogonal) lattice, so
        we REFINE exactly over the 27-point offset box: for every
            delta in {-1, 0, +1}^3   (3 x 3 x 3 = 27 candidates, incl. delta=0)
        we form the candidate m0 + delta, measure || B (m0 + delta) - t ||, and
        keep the smallest:
            m_hat = m0 + argmin over delta of || B (m0 + delta) - t ||.
      - All of this is vectorized: n targets (shape (n, 1, 3)) broadcast
        against the 27 candidates (shape (1, 27, 3)) -- no Python loop over
        targets.

    WHY this is exact inside the packing radius (the guarantee the tests
    check): if the offset ||t - B m_true|| is smaller than the packing radius
    rho = lambda_1 / 2, then every OTHER lattice point is at least
    lambda_1 - rho = rho away from t -- farther than B m_true itself. So
    B m_true is the UNIQUE closest lattice point, and any exact closest-point
    search must return m_true. Inside rho the answer is not just close, it is
    provably the injected integer.

    B: (3, 3) lattice generator in km (from ambiguity_lattice_generator).
    targets_km: position offset(s) in km, shape (3,) for one target or
        (n, 3) for many.
    Returns: integer turn-count vector(s) m_hat, integer dtype, shape (3,) for
        a (3,) input or (n, 3) for an (n, 3) input, minimizing ||B m - t||.

    What this does NOT do (same well-conditioned caveat as shortest_vector_km):
    the +-1 box is verified sufficient ONLY for the project's spread-out §12
    geometries, where Babai's m0 lands within one step of the true integer
    (measured: exactly one L-inf step on the real T5b lattice, zero on the
    orthonormal one). It is NOT a general high-dimensional CVP solver and does
    NO lattice (LLL) reduction; a near-degenerate geometry could push the true
    point outside the +-1 box, which stays a deferred follow-up card
    (fpylll / LLL) if such a geometry ever appears. It also does not decide
    WHETHER the prior is inside rho -- past rho a neighbor is genuinely closer
    and the returned integer flips (that is the ambiguity, not an error).
    """
    B = np.asarray(B, dtype=float)
    if B.shape != (3, 3):
        raise ValueError("v1 closest-lattice-point needs a 3x3 generator B")
    t = np.asarray(targets_km, dtype=float)
    single = t.ndim == 1
    targets = np.atleast_2d(t)  # (n, 3)

    # Babai nearest-lattice-point estimate: round the lattice coordinates.
    m0 = np.rint(targets @ np.linalg.inv(B).T)  # (n, 3), integer-valued floats

    # The 27 integer offsets delta in {-1, 0, +1}^3 (includes 0, so m0 itself
    # is always a candidate and m_hat can never be worse than Babai's guess).
    axis = np.array([-1.0, 0.0, 1.0])
    deltas = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(
        -1, 3
    )

    candidates = m0[:, None, :] + deltas[None, :, :]  # (n, 27, 3)
    residuals = candidates @ B.T - targets[:, None, :]  # (n, 27, 3), each B m - t
    dist = np.linalg.norm(residuals, axis=-1)  # (n, 27)
    best = np.argmin(dist, axis=1)  # (n,)
    m_hat = candidates[np.arange(candidates.shape[0]), best, :]
    m_hat = np.rint(m_hat).astype(np.int64)  # exact: entries are small integers

    return m_hat[0] if single else m_hat
