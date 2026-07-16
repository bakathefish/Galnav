"""The armor tier's PINT toolbox: two independent routes to photon phases.

This module is the CODE UNDER TEST for Spec 9 (and the shared machinery E4
reuses). It runs ONLY inside the WSL2 longdouble environment recorded in
journal/environment-armor.md.

The physics chain, one step at a time (full derivation in
journal/spec-9-photon-phase.md):

  1. A NICER "cleaned event" is one detected X-ray photon with an arrival
     TIME stamped by the instrument on the ISS (topocentric, i.e. where the
     telescope actually was).
  2. The ISS moves: around Earth (~7.7 km/s, 92-min orbit) while Earth moves
     around the Solar System Barycentre (SSB, ~30 km/s). A photon's arrival
     time therefore depends on WHERE the ISS was -- up to +-23 ms of
     light-travel time across the ISS orbit alone (orbit radius ~6780 km,
     divided by c) and +-8 min across Earth's orbit.
  3. BARYCENTERING moves each arrival time to the SSB: PINT interpolates the
     ISS position from the .orb file, adds Earth's position from the JPL
     ephemeris (DE440 here, the par file's own EPHEM), applies the clock
     chain and the Roemer/Shapiro delays, giving the time the wavefront
     crossed the SSB.
  4. The pulsar spins predictably: its rotational PHASE at barycentric time
     t is the spin-down polynomial phi(t) = F0*(t-PEPOCH) +
     F1*(t-PEPOCH)^2/2 (+ F2/6 ...), with F0 ~ 205.53 Hz for J0030+0451.

THE PRECISION LESSON this module is built around (measured while making T1
and T2 pass; full story in the journal; binades re-verified by the
2026-07-16 doubt-everything sweep): our data sit ~3.39e10 turns past
PEPOCH -- inside the 2^34 binade (2^35 = 34,359,738,368 sits just above) --
so a single longdouble total-phase carries a grid of 2^(34-63) = 2^-29 ~
1.86e-9 turns; and a barycentric epoch written as ONE longdouble MJD
(58137 days, the 2^15 binade) is far coarser still, 2^-48 day ~ 0.31 ns ~
6.3e-8 turns of J0030 phase. NO independent re-computation that recombines whole turns
with the fraction, or that round-trips through a bary-MJD, can agree with
another to 1e-9 turns. PINT therefore (a) keeps phases as an (integer
turns, fraction) PAIR and (b) keeps time as (tdbld - PEPOCH) and the delay
SEPARATE, never materializing a barycentric MJD. Every function here
follows the same two disciplines, and the T2 reference mirrors PINT's
evaluation order operation by operation so the comparison is made on equal
terms.

Phase convention: PINT's Phase pair (int, frac) with frac in [-0.5, 0.5) is
re-expressed as n = whole turns (int64) and f = fraction in [0, 1)
(float64), the same [0, 1) fraction `photonphase --addphase` writes to its
PULSE_PHASE column (source, pint 1.1.4 photonphase.py line 269:
``phases = phss.value % 1``) -- so the two routes are directly comparable.
The pair is NEVER summed into one longdouble.

Units: file paths are strings/Path; phases are dimensionless turns split as
(int64 turns, float64 fraction in [0,1)); times in the T2 chain are
longdouble SECONDS from PEPOCH; positions km.
"""

import subprocess
import tempfile
from pathlib import Path

import numpy as np

VENV_BIN = "/opt/galnav/venv/bin"


def _floor_split_pair(int_ld, frac_ld):
    """Re-express PINT's (int, frac in [-0.5,0.5)) pair as floor convention.

    n = whole turns (int64), f = fraction in [0, 1) (float64), computed
    WITHOUT ever summing the pair into one longdouble (summing quantizes
    the fraction at the total's longdouble grid -- 2^-29 at these ~3.39e10
    turn counts -- measured as a constant one-grid-step 2^-29 T1 failure
    before this function existed; the re-split rounding itself is <= 2^-30).

    int_ld/frac_ld: longdouble arrays (PINT Phase .int/.frac values).
    Returns: (int64 turns, float64 fraction in [0, 1)).
    """
    int_ld = np.asarray(int_ld, dtype=np.longdouble)
    frac_ld = np.asarray(frac_ld, dtype=np.longdouble)
    frac01_ld = frac_ld % np.longdouble(1.0)  # the CLI's own transform
    carry = np.asarray(frac_ld < 0, dtype=np.int64)
    n = np.asarray(int_ld, dtype=np.int64) - carry
    return n, np.asarray(frac01_ld, dtype=np.float64)


def _floor_split_total(total_ld):
    """Split a single-longdouble total phase into floor convention.

    Only for quantities that genuinely ARE one longdouble (PINT's
    spindown_phase returns one longdouble array; T2 compares two such
    totals computed in bit-identical operation order, so the shared
    ~2^-28 grid cancels out of the comparison).

    total_ld: np.longdouble array of total turns.
    Returns: (int64 whole turns, float64 fraction in [0, 1)).
    """
    total_ld = np.asarray(total_ld, dtype=np.longdouble)
    n = np.floor(total_ld)
    frac = total_ld - n  # exact: Sterbenz subtraction of nearby values
    return np.asarray(n, dtype=np.int64), np.asarray(frac, dtype=np.float64)


def phases_photonphase_cli(evt_path, par_path, orb_path, ephem):
    """Route A -- the tool under test: PINT's `photonphase` CLI, end to end.

    Runs the installed photonphase exactly as a mission analyst would:
      photonphase <evt> <par> --orbfile <orb> --ephem <ephem> --addphase
                  --outfile <tmp>
    and reads back the PULSE_PHASE column it wrote.

    evt_path/par_path/orb_path: paths (str/Path) to the NICER cleaned event
        FITS (.evt.gz is fine), the timing model (.par), and the ISS orbit
        FITS (.orb.gz).
    ephem: JPL ephemeris name (str), e.g. "DE440" -- pinned explicitly so a
        default can never drift (the CLI's own default is DE421).
    Returns: float64 array of fractional pulse phases in [0, 1), one per
        photon, in the event file's row order.
    """
    from astropy.io import fits

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "phased.fits"
        cmd = [
            f"{VENV_BIN}/photonphase",
            str(evt_path),
            str(par_path),
            "--orbfile",
            str(orb_path),
            "--ephem",
            ephem,
            "--addphase",
            "--outfile",
            str(out),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        with fits.open(out) as hdul:
            frac = np.array(hdul["EVENTS"].data["PULSE_PHASE"], dtype=np.float64)
    return frac % 1.0


def phases_library(evt_path, par_path, orb_path, ephem):
    """Route B -- our own independent walk of PINT's public library API.

    Deliberately does NOT call the photonphase script: it registers the ISS
    orbit as a satellite observatory, loads the photon events as TOAs,
    computes the barycentric delay chain, and evaluates the model's absolute
    phase. If our understanding of ANY step differs from what the CLI does
    (orbit interpolation, clock chain, ephemeris, TZR reference), the two
    routes disagree and Spec 9's gate fails.

    Clock-chain note (MEASURED against the installed photonphase source,
    pint 1.1.4, pint/scripts/photonphase.py lines 189-196): the photon
    pipeline builds its TOAs with get_event_TOAs(..., include_bipm=
    args.use_bipm) and the --use_bipm flag defaults to OFF -- satellite
    photon TOAs are microsecond-class, far above the tens-of-ns
    TT(TAI)->TT(BIPM) refinement -- so Route B mirrors include_bipm=False
    and uses the SAME get_event_TOAs constructor. The par's CLOCK
    TT(BIPM2019) line matters for radio-TOA fitting, not for this photon
    pipeline; recorded in the journal.

    Arguments as in phases_photonphase_cli.
    Returns: (model, toas, phase_int, phase_frac) -- the PINT model and TOAs
        objects (reused by other helpers), int64 whole turns, float64
        fraction in [0, 1), one per photon, event row order preserved.
    """
    import pint.logging

    pint.logging.setup(level="WARNING")

    from pint.event_toas import get_event_TOAs
    from pint.models import get_model
    from pint.observatory.satellite_obs import get_satellite_observatory

    model = get_model(str(par_path))
    get_satellite_observatory("NICER", str(orb_path), overwrite=True)
    planets = "PLANET_SHAPIRO" in model.params and bool(model.PLANET_SHAPIRO.value)
    ts = get_event_TOAs(
        str(evt_path),
        "nicer",
        ephem=ephem,
        include_bipm=False,
        planets=planets,
    )
    ph = model.phase(ts, abs_phase=True)
    phase_int, phase_frac = _floor_split_pair(ph.int.value, ph.frac.value)
    return model, ts, phase_int, phase_frac


def parse_spindown_longdouble(par_path):
    """Read F0, F1, F2, PEPOCH from the par TEXT at full longdouble width.

    The par file stores e.g. F0 = 205.53069907954086655 Hz -- 20 significant
    digits, more than float64's ~16. The whole point of this parser is that
    the string is converted DIRECTLY to np.longdouble (float128 here), never
    passing through a float64 that would silently round it.

    par_path: path to the .par file.
    Returns: dict with keys F0 (Hz), F1 (Hz/s), F2 (Hz/s^2, 0.0 if absent),
        PEPOCH (MJD, TDB) -- every value np.longdouble.
    """
    values = {"F2": np.longdouble("0.0")}
    wanted = {"F0", "F1", "F2", "PEPOCH"}
    for line in Path(par_path).read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] in wanted:
            # np.longdouble(str) parses the full precision; 'D' exponents
            # (FORTRAN style) normalized just in case.
            values[fields[0]] = np.longdouble(fields[1].replace("D", "e"))
    missing = {"F0", "F1", "PEPOCH"} - set(values)
    if missing:
        raise ValueError(f"par file lacks {sorted(missing)}")
    return values


def pulsar_frame_dt_seconds(model, toas, pepoch_mjd_ld):
    """Time from PEPOCH at the pulsar, mirroring PINT's own decomposition.

    PINT's Spindown component (pint/models/spindown.py, get_dt) computes

        dt = (tdbld - PEPOCH) [longdouble days] * u.day - delay [seconds]

    and converts to seconds only afterwards. The subtraction of two nearby
    longdouble MJDs is EXACT (Sterbenz), so dt carries the full precision a
    barycentric MJD could not (see the module docstring's precision
    lesson). This helper reproduces that chain operation by operation --
    including astropy's unit bookkeeping, which converts the float64 delay
    to days by MULTIPLYING with the float64 factor 1/86400 before the
    subtraction, then scales the result back by 86400:

        dt_s = ((tdbld - PEPOCH) - float64(delay) * float64(1/86400))
               * longdouble(86400)

    model/toas: the pair returned by phases_library.
    pepoch_mjd_ld: PEPOCH (MJD, TDB) as np.longdouble -- from
        parse_spindown_longdouble, whose string parse lands on the same
        longdouble bits as PINT's own parameter parse.
    Returns: np.longdouble array of seconds since PEPOCH at the pulsar, one
        per photon.
    """
    tdbld = np.asarray(toas.table["tdbld"], dtype=np.longdouble)
    delay_s = model.delay(toas).to_value("s")  # float64 seconds, as in PINT
    delay_day = np.asarray(delay_s) * np.float64(1.0 / 86400.0)
    dt_day = (tdbld - pepoch_mjd_ld) - np.asarray(delay_day, dtype=np.longdouble)
    return dt_day * np.longdouble("86400.0")


def spindown_phase_reference(dt_seconds_ld, F0, F1, F2):
    """The hand-rolled reference: the spin-down polynomial in longdouble.

    phi(dt) = F0*dt + F1*dt^2/2 + F2*dt^3/6, evaluated EXACTLY the way
    PINT's taylor_horner evaluates it (pint/utils.py taylor_horner_deriv:
    coefficients [0, F0, F1, F2], Horner loop ``r = r*x/fact + c`` with
    fact counting down), so the two computations share every rounding step
    and the comparison is bit-for-bit meaningful. This is still the
    students' own formula -- Horner is just the bracketing
    phi = ((F2*dt/3 + F1)*dt/2 + F0)*dt/1 -- and if our reading of the
    timing model differed from PINT's in ANY term, the phases would
    disagree by far more than the gate.

    dt_seconds_ld: seconds since PEPOCH at the pulsar (np.longdouble), from
        pulsar_frame_dt_seconds.
    F0, F1, F2: spin frequency and derivatives (Hz, Hz/s, Hz/s^2),
        np.longdouble.
    Returns: (phase_int int64, phase_frac float64 in [0,1)) -- the
        polynomial split into whole turns and fraction, vectorized.
    """
    x = np.asarray(dt_seconds_ld, dtype=np.longdouble)
    coeffs = [np.longdouble("0.0"), F0, F1, F2]
    result = np.longdouble("0.0")
    fact = float(len(coeffs))
    for coeff in coeffs[::-1]:
        result = result * x / fact + coeff
        fact -= 1.0
    return _floor_split_total(result)


def pint_spindown_phase(model, toas):
    """PINT's own spin-down phase (the piece T2 compares against).

    Calls the Spindown component's spindown_phase(toas, delay) -- one
    longdouble total-phase array (this is the one place PINT itself uses a
    single longdouble; T2's reference mirrors its operation order exactly
    so both sit on the same representational grid).

    model/toas: the pair returned by phases_library.
    Returns: (phase_int int64, phase_frac float64 in [0,1)).
    """
    delay = model.delay(toas)
    phs = model.components["Spindown"].spindown_phase(toas, delay)
    return _floor_split_total(np.asarray(phs.value, dtype=np.longdouble))


def ssb_obs_positions_km(toas):
    """The observatory (ISS) position PINT actually used, per photon.

    toas: from phases_library.
    Returns: (n, 3) float64 array, SSB -> observatory vectors in km. If the
        orbit file were silently ignored these would sit at Earth's centre.
    """
    pos = toas.table["ssb_obs_pos"]
    return np.asarray(pos.quantity.to_value("km"), dtype=np.float64)


def earth_ssb_positions_km(toas, ephem):
    """Earth's geocentre position at the same times, from the ephemeris.

    Uses the SAME JPL ephemeris the barycentering used (cached at
    environment-build time; see journal/environment-armor.md), evaluated at
    each photon's topocentric TDB.

    toas: from phases_library. ephem: JPL ephemeris name (str).
    Returns: (n, 3) float64 array, SSB -> geocentre vectors in km.
    """
    from astropy.coordinates import get_body_barycentric, solar_system_ephemeris
    from astropy.time import Time

    t = Time(
        np.asarray(toas.table["tdbld"], dtype=np.float64),
        format="mjd",
        scale="tdb",
    )
    with solar_system_ephemeris.set(ephem.lower()):
        pos = get_body_barycentric("earth", t)
    return np.asarray(pos.xyz.to_value("km").T, dtype=np.float64)


def pulsar_unit_vector(model):
    """Unit vector from the SSB toward the pulsar (ICRS), from the model.

    model: from phases_library.
    Returns: (3,) float64 unit vector (dimensionless).
    """
    coords = model.coords_as_ICRS()
    xyz = np.asarray(coords.cartesian.xyz.value, dtype=np.float64).reshape(3)
    return xyz / np.linalg.norm(xyz)


def wrapped_abs_delta(frac_a, frac_b):
    """Wrap-aware |phase difference| in turns.

    Phases live on a circle: 0.9999 and 0.0001 are 0.0002 apart, not 0.9998.
    d = (a - b) mod 1; the distance is min(d, 1 - d).

    frac_a, frac_b: float64 arrays of fractional phases in [0, 1).
    Returns: float64 array of circular distances in [0, 0.5].
    """
    d = (
        np.abs(
            np.asarray(frac_a, dtype=np.float64) - np.asarray(frac_b, dtype=np.float64)
        )
        % 1.0
    )
    return np.minimum(d, 1.0 - d)
