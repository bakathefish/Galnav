# GalNav Citation Registry

Every outside fact, number, formula, dataset, and tool this project uses,
with its source and exactly where we use it. Add to this file the moment a
new source is touched — the paper's reference list gets built FROM this file.

Format: full citation, then "Used for", then "Where in repo".

---

## Primary research papers

**[BJ21]** Bailer-Jones, C. A. L. (2021). "Lost in space? Relativistic
interstellar navigation using an astrometric star catalogue."
*Publications of the Astronomical Society of the Pacific*, 133, 074502.
arXiv:2103.10389. https://arxiv.org/abs/2103.10389
- Used for: the accuracy anchor we must reproduce — 20 nearest stars at
  1 arcsec measurement noise gives position to ~3 au and velocity to
  ~2 km/s; also the 1/sqrt(N) scaling (100 stars → 1.3 au, in HIS
  per-star-measurement setup) and the "accuracy proportional to
  measurement noise" scaling. NOTE (E1, 2026-07-14; corrected
  2026-07-15 against the full text): his estimator solves SEVEN
  unknowns — 3D position, 3D velocity, AND the barycentric time of
  measurement, via 7-dimensional MCMC ("we were forced to formally
  include the measurement time as a seventh unknown parameter") — from
  N-1 = 19 pair angles for 20 stars (he explicitly declines all
  N(N-1)/2 pairs), plus, in his nominal scenario, N-1 radial-velocity
  measurements at 10 km/s accuracy. Our current position-only,
  all-pairs setup measured 0.42 au at the same (20 stars, 1 arcsec)
  cell at 1 pc — 7x tighter, consistent with the much easier problem,
  NOT an anchor reproduction. Honest comparison deferred to the
  velocity+aberration card (plan week-5 gate).
- Where in repo: `tests/golden_numbers.py` (BAILER_JONES_ANCHOR, still
  awaiting its apples-to-apples test); `journal/e1-crlb-grid.md`.
- Verified: abstract re-checked 2026-07-14; full text fetched and the
  seven-parameter and 19-pair statements verified verbatim 2026-07-15.

**[Lauer25]** Lauer, T. R., et al. (2025). "A Demonstration of Interstellar
Navigation Using New Horizons." arXiv:2506.21666.
https://arxiv.org/abs/2506.21666
- Used for: measured New Horizons parallax shifts (Proxima Centauri
  32.4 arcsec, Wolf 359 15.7 arcsec, spacecraft at 47.12 au); their 0.44 au
  position-fix benchmark; the aberration formula
  phi = arctan(sin(theta) / (beta + cos(theta))) (their Eq. 1) — which
  the paper presents EXPLICITLY as the non-relativistic (v << c) case.
  CORRECTED 2026-07-15 (science audit): this entry previously called
  Eq. 1 "the exact aberration formula ... for the relativistic
  experiment." It is the Galilean form; the exact special-relativistic
  formula needs the Lorentz factor, tan(phi) = sin(theta) /
  (gamma (beta + cos(theta))) — see [SR-ABER]. E7 at 0.1c MUST use the
  gamma form: at beta = 0.1 the gamma-less formula errs by ~103 arcsec
  at theta = 90 deg (checked numerically 2026-07-15), enormous against
  our arcsecond-level measurement noise.
- Where in repo: `tests/golden_numbers.py` (NH_* values;
  ABERRATION_MAX_DEG_AT_0P1C carries the same v << c lineage, comment
  updated); future experiments E3 and E7.
- Verified: 32.4/15.7 values cross-checked against NASA press material on
  2026-07-14 (see [NASA20]); the "non-relativistic observer velocity,
  v << c" framing of Eq. 1 verified verbatim against the arXiv full text
  on 2026-07-15.

**[SR-ABER]** Special-relativistic aberration of light,
tan(phi) = sin(theta) / (gamma (beta + cos(theta))) with
gamma = 1/sqrt(1 - beta^2) — standard textbook result, e.g. Rindler, W.
(2006). *Relativity: Special, General, and Cosmological* (2nd ed.),
Oxford University Press, ch. 4.
- Used for: the correction to [Lauer25]'s Eq. 1 above; the formula E7
  (0.1c experiment) must implement. Maximum deflection at beta = 0.1 is
  5.7464 deg vs the Galilean arcsin(0.1) = 5.7392 deg.
- Where in repo: `journal/citations.md` (this note);
  `tests/golden_numbers.py` ABERRATION_MAX_DEG_AT_0P1C comment. No code
  uses it yet (E7's card will).
- Verified: reduces to the Galilean form at gamma -> 1; numerical check
  of the 103-arcsec discrepancy at beta = 0.1, theta = 90 deg run
  2026-07-15.

**[KHE26]** Khan, A., Hou, L., & Eggl, S. (2026). "Assessing the
Predictability of δ Scuti Variable Stars for Spacecraft Navigation."
arXiv:2606.30691. https://arxiv.org/abs/2606.30691
- Used for: related-work candidate — evidence the celestial-beacon
  navigation field is actively publishing (appeared ~3 weeks before our
  2026-07-15 prior-art sweep); same group as the XNAV cold-start work
  [HP24 anchor in plan §7]. Not used by any code.
- Where in repo: `journal/logbook.md` (2026-07-15 prior-art sweep
  entry); future paper related-work section.
- Verified: abstract read on arXiv, 2026-07-15.

**[NASA20]** NASA (2020). "NASA's New Horizons Conducts the First
Interstellar Parallax Experiment." Press release, June 2020.
https://www.nasa.gov/solar-system/nasas-new-horizons-conducts-the-first-interstellar-parallax-experiment/
- Used for: independent confirmation of the 32.4 and 15.7 arcsec shifts.
- Where in repo: verification record only (secondary source).

## Definitions and physical constants

**[IAU12]** IAU 2012 Resolution B2: the astronomical unit is exactly
149,597,870.7 km.
- Where in repo: `tests/golden_numbers.py` (AU_KM).

**[SI]** SI definition (17th CGPM, 1983): the speed of light is exactly
299,792,458 m/s (the metre is defined from it).
- Where in repo: `tests/golden_numbers.py` (C_KM_S); all pulsar comb
  spacings are c times spin period.

**[IAU15]** IAU 2015 Resolution B2: the parsec is exactly 648000/pi au
(follows from 1 arcsec = pi/648000 rad). Gives 206,264.806... au/pc, the
same number as arcseconds per radian.
- Where in repo: `tests/golden_numbers.py` (PC_AU, RAD_ARCSEC);
  `tests/test_parallax.py` (parsec-definition test);
  `journal/spec-2-parallax.md`.

## Data catalogs

**[ATNF]** Manchester, R. N., Hobbs, G. B., Teoh, A., & Hobbs, M. (2005).
"The Australia Telescope National Facility Pulsar Catalogue." *The
Astronomical Journal*, 129, 1993. https://www.atnf.csiro.au/research/pulsar/psrcat/
- Used for: pulsar spin periods behind the six comb spacings (Crab 33.6 ms,
  B1937+21 1.558 ms, J0218+4232 2.323 ms, B1821-24 3.054 ms,
  J0030+0451 4.865 ms, J0437-4715 5.757 ms).
- Where in repo: `tests/golden_numbers.py` (COMB_KM).
- Note: periods rounded to the digits shown; comb values verified to agree
  with c x P within 1 km (recomputed 2026-07-14).

**[GaiaDR3]** Gaia Collaboration, Vallenari, A., et al. (2023). "Gaia Data
Release 3: Summary of the content and survey properties." *Astronomy &
Astrophysics*, 674, A1.
- Used for: real star positions, parallaxes, proper motions, radial
  velocities, and full covariance information for all stars within 20 pc;
  typical fractional parallax error ~0.2% used in the per-star floor check.
- Where in repo: `data/gaia_dr3_nav_subset.csv` (1,941 stars, retrieved
  2026-07-14; exact reproducible query in `data/README.md`); consumed by
  Spec 3 (simulator) and Spec 7 (catalog covariance) onward.
- Data source: ESA Gaia Archive TAP service, gaiadr3.gaia_source table.

## Historical

**[Gauss1809]** Gauss, C. F. (1809). *Theoria Motus Corporum Coelestium*.
Least squares, invented for recovering the orbit of the asteroid Ceres
from noisy telescope bearings — the historical root of our solver.
- Used for: historical context for the Gauss-Newton estimator.
- Where in repo: `journal/spec-5-estimator.md`.

**[Bessel1838]** Bessel, F. W. (1838). "Bestimmung der Entfernung des
61sten Sterns des Schwans." *Astronomische Nachrichten*, 16, 65–96.
The first stellar parallax measurement in history — of 61 Cygni.
- Used for: historical context; 61 Cygni A/B is the close binary pair in
  our nearest-ten list whose near-zero separation angle exposed the
  arccos precision limit and the close-pair degeneracy (Spec 4).
- Where in repo: `tests/test_measmodel.py` (pair-selection comment),
  `journal/spec-4-measmodel.md`, logbook 2026-07-14.

## Standard mathematics (textbook results, not original to any paper)

**[DOT]** The identity a·b = |a| |b| cos(angle) for vectors — standard
linear algebra (any textbook, e.g. Strang, *Introduction to Linear
Algebra*).
- Where in repo: `galnav/geometry.py` (angle_between), derived and
  explained in `journal/spec-1-angle-geometry.md`;
  `galnav/truth/observer.py` (vectorized over star pairs).

**[SPH]** Spherical-to-Cartesian conversion x = cos(dec)cos(ra),
y = cos(dec)sin(ra), z = sin(dec) — standard trigonometry (any textbook).
- Where in repo: `galnav/units.py` (radec_to_unit), cross-checked against
  astropy in `tests/test_sky.py`; explained in
  `journal/spec-3-truth-sky.md`.

**[CROSS]** |a x b| = |a| |b| sin(angle), and the robust two-argument
angle recipe arctan2(|u_i x u_j|, u_i·u_j) — standard vector algebra /
numerical practice (precise at all angles, unlike arccos near 0/pi).
- Where in repo: `galnav/nav/measmodel.py` (_pair_sin_cos,
  predicted_pair_angles); rationale in `journal/spec-4-measmodel.md`.

**[CHAIN]** Jacobian of the pair angle by the chain rule:
d(angle)/dp = -[(cos·u_i - u_j)/r_i + (cos·u_j - u_i)/r_j]/sin, using
du/dp = (u uᵀ - I)/r — standard vector calculus, full derivation
reproduced step by step in `journal/spec-4-measmodel.md`.
- Where in repo: `galnav/nav/measmodel.py` (pair_angle_jacobian).

**[GN]** Gauss-Newton iteration for nonlinear least squares: linearize
the model, solve the normal equations (JᵀJ)δ = Jᵀr, apply, repeat —
standard optimization (any textbook, e.g. Nocedal & Wright, *Numerical
Optimization*). The students' derivation D3 reproduces it from χ²
minimization.
- Where in repo: `galnav/nav/estimator.py` (solve_position); derivation
  written out step by step in `journal/spec-5-estimator.md`.

**[COV]** First-order noise propagation through least squares:
Cov(p̂) = σ²(JᵀJ)⁻¹ (with weights, (JᵀWJ)⁻¹) — standard estimation
theory (any textbook). The students' derivation D4 reproduces it.
- Where in repo: `galnav/nav/estimator.py` (position_covariance);
  verified by 500-trial Monte Carlo in `tests/test_covariance.py`;
  explained in `journal/spec-6-covariance.md`.

**[CRLB]** Cramér-Rao lower bound: no unbiased estimator's covariance
can beat the inverse Fisher information; for Gaussian angle noise the
Fisher information is JᵀJ/σ², so the bound equals [COV]'s formula —
standard statistics (Cramér 1946; Rao 1945; any estimation textbook).
The students' derivation D6 covers the 1/sqrt(N) scaling consequence.
- Where in repo: `journal/spec-6-covariance.md`; the theory line of
  experiment E1's signature figure.

**[SAMPVAR]** Sampling fluctuation of an estimated standard deviation:
relative std ≈ 1/sqrt(2T) for T samples — standard statistics.
- Where in repo: MC_CRLB_REL_TOL and MC_TRIALS rationale in
  `tests/golden_numbers.py` and `journal/spec-6-covariance.md`.

**[CDIFF]** Central finite differences f'(x) ≈ (f(x+h) - f(x-h))/2h with
truncation error O(h²) and rounding error O(eps/h) — standard numerical
analysis (any textbook, e.g. Press et al., *Numerical Recipes*).
- Where in repo: `tests/test_measmodel.py` (4-decade Jacobian
  verification); step-size trade-off explained in
  `journal/spec-4-measmodel.md` and the JACOBIAN_REL_TOL comment in
  `tests/golden_numbers.py`.

**[SMALL]** Small-angle approximation arctan(x) ≈ x with relative error
x²/3 — standard calculus (Taylor series). Right-triangle definition
tan(angle) = opposite/adjacent — standard trigonometry.
- Where in repo: `galnav/parallax.py` (exact arctan(D/d) formula);
  `tests/test_parallax.py` (shortcut-vs-exact test and its
  DISPLACEMENT_REL_TOL headroom argument); `journal/spec-2-parallax.md`.

## Software (cite in the paper's methods section)

**[NumPy]** Harris, C. R., et al. (2020). "Array programming with NumPy."
*Nature*, 585, 357–362.
**[Astropy]** Astropy Collaboration (2022). "The Astropy Project:
Sustaining and Growing a Community-oriented Open-source Project and the
Latest Major Release (v5.0) of the Core Package." *The Astrophysical
Journal*, 935, 167.
- Used for: independent cross-check of our sky-coordinate conversions
  (`tests/test_sky.py`, SkyCoord agreement gate); later specs use it for
  frame/epoch checks.
**[Python]** Python Software Foundation. Python Language Reference.
**[pytest]** Krekel, H., et al. pytest. https://pytest.org

**[NEP19]** NumPy Developers. "NEP 19 — Random Number Generator Policy"
(accepted 2018-07), https://numpy.org/neps/nep-0019-rng-policy.html; and
"Compatibility policy," NumPy Reference Manual, numpy.random section,
https://numpy.org/doc/stable/reference/random/compatibility.html
- Used for: the fact that a seeded `np.random.Generator` is guaranteed
  to reproduce the same stream only on the same numpy build, in the same
  environment, on the same machine — and that distribution streams may
  change between numpy versions so algorithms can improve. This is why
  `results/archive/` keeps the exact result arrays in version control
  instead of relying on "just re-run the seed," and why
  `journal/environment.md` records the exact environment behind every
  committed result.
- Where in repo: `journal/environment.md`, `results/archive/README.md`.
- Verified: both pages checked on 2026-07-15 (policy wording: the
  same-build / same-environment / same-machine guarantee; cross-version
  stream changes allowed "with caution").

## Learning resources consulted (log for the ISEF logbook, not paper refs)

- Khan Academy, "Defining the angle between vectors."
  https://www.khanacademy.org/math/linear-algebra/v/defining-the-angle-between-vectors
- 3Blue1Brown, "Essence of Linear Algebra," chapters 1 and 9.
  https://www.youtube.com/watch?v=fNk_zzaMoSs and
  https://www.youtube.com/watch?v=LyGKycYT2v0
