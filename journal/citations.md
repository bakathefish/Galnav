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
  ~2 km/s; also the 1/sqrt(N) scaling (100 stars → 1.3 au) and the
  "accuracy proportional to measurement noise" scaling.
- Where in repo: `tests/golden_numbers.py` (BAILER_JONES_ANCHOR); future
  experiment E1 pass/fail gate.
- Verified: abstract wording re-checked against arXiv on 2026-07-14.

**[Lauer25]** Lauer, T. R., et al. (2025). "A Demonstration of Interstellar
Navigation Using New Horizons." arXiv:2506.21666.
https://arxiv.org/abs/2506.21666
- Used for: measured New Horizons parallax shifts (Proxima Centauri
  32.4 arcsec, Wolf 359 15.7 arcsec, spacecraft at 47.12 au); their 0.44 au
  position-fix benchmark; the exact aberration formula
  phi = arctan(sin(theta) / (beta + cos(theta))) (their Eq. 1) for the
  relativistic experiment.
- Where in repo: `tests/golden_numbers.py` (NH_* values); future
  experiments E3 and E7.
- Verified: 32.4/15.7 values cross-checked against NASA press material on
  2026-07-14 (see [NASA20]).

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

## Standard mathematics (textbook results, not original to any paper)

**[DOT]** The identity a·b = |a| |b| cos(angle) for vectors — standard
linear algebra (any textbook, e.g. Strang, *Introduction to Linear
Algebra*).
- Where in repo: `galnav/geometry.py` (angle_between), derived and
  explained in `journal/spec-1-angle-geometry.md`.

**[SMALL]** Small-angle approximation arctan(x) ≈ x with relative error
x²/3 — standard calculus (Taylor series). Right-triangle definition
tan(angle) = opposite/adjacent — standard trigonometry.
- Where in repo: `galnav/parallax.py` (exact arctan(D/d) formula);
  `tests/test_parallax.py` (shortcut-vs-exact test and its
  DISPLACEMENT_REL_TOL headroom argument); `journal/spec-2-parallax.md`.

## Software (cite in the paper's methods section)

**[NumPy]** Harris, C. R., et al. (2020). "Array programming with NumPy."
*Nature*, 585, 357–362.
**[Python]** Python Software Foundation. Python Language Reference.
**[pytest]** Krekel, H., et al. pytest. https://pytest.org

## Learning resources consulted (log for the ISEF logbook, not paper refs)

- Khan Academy, "Defining the angle between vectors."
  https://www.khanacademy.org/math/linear-algebra/v/defining-the-angle-between-vectors
- 3Blue1Brown, "Essence of Linear Algebra," chapters 1 and 9.
  https://www.youtube.com/watch?v=fNk_zzaMoSs and
  https://www.youtube.com/watch?v=LyGKycYT2v0
