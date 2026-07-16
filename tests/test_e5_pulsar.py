"""Acceptance tests for the pulsar comb + lattice-impossibility card (E5-lite).

AI-authored under the build-night ratification-pending pattern (see
journal/logbook.md 2026-07-16 and the ratification worksheet). Students:
read and own every assertion before ratifying.

The physics: a photon time-of-arrival measures a pulsar's rotational PHASE,
which repeats every period P. That pins the spacecraft's position along the
sightline n_hat only modulo one "comb spacing" s = c * P (the distance light
travels in one turn of the pulsar). K pulsars give K such comb constraints;
the set of positions consistent with all of them is a LATTICE, and the
largest prior uncertainty that still selects the correct integer on every
comb is the packing radius rho = lambda_1 / 2 (half the shortest lattice
vector). The finding: a star-only fix (~1 au) is 4+ orders of magnitude
coarser than even the widest comb (~10,073 km), so no comb can be locked.

Every oracle here is either computed inline (exact, golden-free) or read from
the FROZEN tests/golden_numbers.py. No new tolerance is introduced.
"""

import numpy as np

from galnav import pulsar
from galnav.units import C_KM_S, AU_KM
from tests.golden_numbers import (
    COMB_KM,
    COMB_MATCH_KM,
    COAST_DAYS_467KM_1CM_S,
    COAST_DAYS_467KM_1M_S,
)

SEC_PER_DAY = 86400.0  # SI seconds per day (same convention as units.py)


def test_comb_spacing_is_exactly_c_times_period():
    """T1 (exact, golden-free): comb spacing = c * P, bit-for-bit.

    The module must compute nothing more than the speed of light times the
    period. The test recomputes C_KM_S * P with the SAME constant and asks
    for bitwise equality (np.array_equal, zero tolerance). A wrong formula
    (an extra factor, a unit slip) cannot survive an exact-equality gate.
    """
    for name, period_s in pulsar.PULSAR_PERIODS_S.items():
        got = pulsar.comb_spacing_km(period_s)
        expected = C_KM_S * period_s
        assert np.array_equal(got, expected), name
    # vectorized path is the same math on an array
    periods = np.array(list(pulsar.PULSAR_PERIODS_S.values()))
    assert np.array_equal(pulsar.comb_spacing_km(periods), C_KM_S * periods)


def test_comb_spacings_match_frozen_section12_within_1km():
    """T2 (oracle = frozen COMB_KM): reproduce the six §12 comb spacings.

    Spec 8's acceptance criterion is "all six comb spacings match §12 to
    1 km". COMB_KM in golden_numbers.py holds the students' hand-derived
    §12 values; the module's c*P must land within 1 km of each. Widest
    measured gap is J0030+0451 at 0.51 km (its frozen 1459 km rounds up from
    c*P = 1458.49 km -- a sub-km bookkeeping quirk flagged for ratification,
    still well inside the 1 km spec). The match tolerance is the frozen golden
    COMB_MATCH_KM (= 1.0 km, authorized override #8): Spec 8's §12 rounding
    quantization, not a precision tolerance.
    """
    assert set(pulsar.PULSAR_PERIODS_S) == set(COMB_KM)
    for name, period_s in pulsar.PULSAR_PERIODS_S.items():
        got = pulsar.comb_spacing_km(period_s)
        assert abs(got - COMB_KM[name]) <= COMB_MATCH_KM, (name, got, COMB_KM[name])


def test_coast_time_matches_frozen_467km_budgets():
    """T3 (oracle = frozen COAST_DAYS): the 467 km comb coast budgets.

    coast_time_days uses the HALF-comb (packing-radius / lock-loss) window:
    T = (s/2) / sigma_v. For the 467 km comb this is 270.25 d at 1 cm/s and
    2.70 d at 1 m/s; rounded to each frozen value's own stated precision they
    equal COAST_DAYS_467KM_1CM_S (270.0, 0 dp) and COAST_DAYS_467KM_1M_S
    (2.7, 1 dp). Rounding to the oracle's precision needs no invented
    tolerance. The 100x span between the two budgets mirrors the 100x span
    in sigma_v, checked exactly.
    """
    s467 = COMB_KM["B1937+21"]
    t_1cm = pulsar.coast_time_days(s467, 1e-5)  # 1 cm/s
    t_1m = pulsar.coast_time_days(s467, 1e-3)  # 1 m/s
    assert round(t_1cm, 0) == COAST_DAYS_467KM_1CM_S
    assert round(t_1m, 1) == COAST_DAYS_467KM_1M_S
    # exact formula and exact 100x scaling (golden-free)
    assert np.array_equal(
        pulsar.coast_time_days(s467, 1e-5), 0.5 * s467 / 1e-5 / SEC_PER_DAY
    )
    assert np.isclose(t_1cm / t_1m, 100.0, rtol=0, atol=1e-9)


def test_star_fix_cannot_lock_any_comb_four_order_gap():
    """T4 (the finding): a ~1 au star fix is 4+ orders past every comb.

    A starlight position fix at the Bailer-Jones scale is ~1 au. In km that
    is AU_KM ~ 1.5e8; the widest comb is the Crab at 10,073 km. The ratio is
    ~1.5e4 -- more than four orders of magnitude (the pre-registered E5-lite
    prediction). Against the finest comb (467 km) it is ~3e5. These are the
    scientific inequalities the headline rests on, with orders of margin, so
    they are strict > comparisons, not tolerance checks.
    """
    star_fix_km = 1.0 * AU_KM
    widest_comb = max(COMB_KM.values())
    finest_comb = min(COMB_KM.values())
    assert star_fix_km / widest_comb > 1e4
    assert star_fix_km / finest_comb > 1e5


def test_orthonormal_lattice_shortest_vector_is_the_comb():
    """T5a (exact lattice oracle, golden-free): pin the lattice math.

    For three orthonormal sightlines and equal combs s0, the ambiguity
    lattice generator is s0 * I, so the shortest nonzero lattice vector is
    exactly s0 (take m = a unit integer vector). Bitwise-exact oracle: any
    error in inv(N) @ diag(s) or in the shortest-vector search is caught.
    """
    N = np.eye(3)
    s0 = 10073.0
    combs = np.array([s0, s0, s0])
    B = pulsar.ambiguity_lattice_generator(N, combs)
    assert np.array_equal(pulsar.shortest_vector_km(B), s0)
    assert np.array_equal(pulsar.packing_radius_km(B), 0.5 * s0)


def test_packing_radius_is_km_scale_and_cannot_lock_a_star_fix():
    """T5b: for a real 3-pulsar geometry the packing radius stays km-scale.

    Three spread-out sightlines with the real comb spacings give a packing
    radius on the km scale (bounded above by the widest comb), so a 1 au
    star fix exceeds it by >1e4 -- the impossibility, now via the lattice
    packing radius rather than a single comb. Determinism is asserted too
    (same inputs -> bit-identical lambda_1), since the experiment reuses it.
    """
    # three well-separated unit sightlines (not coplanar)
    N = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.5, 0.5, np.sqrt(0.5)],
        ]
    )
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    combs = np.array([COMB_KM["B0531+21"], COMB_KM["B1937+21"], COMB_KM["J0030+0451"]])
    B = pulsar.ambiguity_lattice_generator(N, combs)
    rho = pulsar.packing_radius_km(B)
    assert 0.0 < rho <= max(combs)
    assert (1.0 * AU_KM) / rho > 1e4
    assert np.array_equal(pulsar.packing_radius_km(B), rho)  # deterministic
