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
- ANCHOR PROTOCOL (extracted from the full text 2026-07-15, now
  load-bearing in the velocity+aberration card): measurements are N-1
  hub angles between one reference star (the Sun) and each other star —
  he explicitly declines all N(N-1)/2 pairs; every reported accuracy is
  the MEDIAN over 100 runs of the 3D error MAGNITUDE (Fig. 8 caption
  warns per-axis is sqrt(3) smaller); truths drawn isotropically at
  0.1-10 ly with velocity PARALLEL to position, uniform 0-0.5c; solver
  initialized uniform 0.9-1.1x truth per parameter (his footnote 4);
  his measured 20-star values: 2.8 au median with 1.3-5.8 au 16th-84th
  band in Fig. 8 (the WITH-10-km/s-RVs scenario), ~3.1 au angles-only
  (Figs. 9/13 — RVs at 10 km/s improve position only ~10%; the
  Abstract/Sec-5 "3 au / 2 km/s" are the angles-only round numbers);
  aberration via Klioner (2003) Eq. 10
  ([Klioner03]); his Sec. 4.1 control shows fixing the epoch leaves
  position/velocity accuracy unchanged (why our static-catalog 6-state
  solve is an honest mirror of his 7-state one).
- Where in repo: `tests/golden_numbers.py` (BAILER_JONES_ANCHOR — its
  apples-to-apples test now EXISTS: `tests/test_bj_anchor.py`);
  `tests/test_state_estimator.py`; `journal/e1-crlb-grid.md`;
  `journal/spec-velocity-aberration.md`.
- Verified: abstract re-checked 2026-07-14; full text fetched and the
  seven-parameter and 19-pair statements verified verbatim 2026-07-15;
  protocol details above quoted from Secs. 2.1-2.2.7, 3.1-3.2, 4.1-4.3,
  5 and Figs. 8/9/13 the same day.

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
  on 2026-07-15. Peer-reviewed venue confirmed 2026-07-16: AJ 170, 1
  (2025); the 0.44 au result is a 0.441 x 0.233 x 0.206 au error ellipsoid
  vs JPL (notebook cell, 2026-07-16).

**[Lauer25-data]** Lauer, T. R., et al. (2025). "Computational Notebook for
'A Demonstration of Interstellar Navigation Using New Horizons'." Zenodo.
**doi:10.5281/zenodo.15359866** (MIT license).
- Used for: the E3 REAL DATA — 12 New Horizons LORRI FITS images (Proxima Cen
  + Wolf 359, 2020-04-23, 47.1 au), 2 Earth-based FITS, `nearby100.txt` (100
  nearest stars, SIMBAD), `nhjpl_traj.txt` (JPL Horizons NH ephemeris = ground
  truth), and `nhparallax.ipynb` (the `n_star_solve` line-of-position
  triangulation and the recalibrated measured star directions). Delivered as a
  git bundle inside the deposit.
- Where in repo: `data/e3_new_horizons/` (git-ignored raw data + provenance
  README + `fetch_e3_data.py`); `journal/logbook.md` (2026-07-16 E3 data
  acquisition); Experiment E3 (to be built). Verified: fetched and the git
  bundle verified 2026-07-16; NH distance 47.12 au and parallaxes 32.4/15.7"
  match the golden NH_* constants.

**[SR-ABER]** Special-relativistic aberration of light,
tan(phi) = sin(theta) / (gamma (beta + cos(theta))) with
gamma = 1/sqrt(1 - beta^2) — standard textbook result, e.g. Rindler, W.
(2006). *Relativity: Special, General, and Cosmological* (2nd ed.),
Oxford University Press, ch. 4.
- Used for: the correction to [Lauer25]'s Eq. 1 above; the formula E7
  (0.1c experiment) implements via the SR_ABER_PHI_RAD oracle. Maximum
  deflection at beta = 0.1 is 5.7464 deg (peak 92.87 deg) vs the Galilean
  arcsin(0.1) = 5.7392 deg (peak 95.74 deg); E7's classical navigator
  (Lauer Eq. 1, no gamma) is biased ~1350 au at 0.1c (2026-07-16).
- Where in repo: `journal/citations.md` (this note);
  `tests/golden_numbers.py` ABERRATION_MAX_DEG_AT_0P1C comment;
  `experiments/e7_relativistic_aberration.py` (exact oracle for Part A and
  the deployed recovery) and `journal/spec-e7-relativistic-aberration.md`.
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

**[Klioner03]** Klioner, S. A. (2003). "A Practical Relativistic Model
for Microarcsecond Astrometry in Space." *The Astronomical Journal*,
125, 1580–1597.
- Used for: the vector form of exact special-relativistic aberration of
  a unit direction (his Eq. 10) — the formula truth's `_aberrate`
  implements (rearranged to stay finite at v = 0), and the same
  equation [BJ21] states his Eq. 7 is ("This is equation 10 of Klioner
  (2003)"). The scalar apex-angle form is [SR-ABER].
- Where in repo: `galnav/truth/observer.py` (docstring);
  `journal/spec-velocity-aberration.md`.
- Verified: via [BJ21]'s verbatim attribution in the fetched full text,
  2026-07-15, and by numerical equivalence of the two independent
  implementations; students should sight the Klioner original before
  the paper's reference list is finalized.

**[BJ15]** Bailer-Jones, C. A. L. (2015). "Estimating Distances from
Parallaxes." *Publications of the Astronomical Society of the Pacific*, 127,
994. arXiv:1507.02105.
- Used for: the fact that a catalog's astrometric error is Gaussian in
  PARALLAX (the fitted quantity), so E6a samples the true sky in parallax
  space; the derived distance d = 1/parallax is then a non-Gaussian,
  slightly biased estimator (mean inflated ~ (sigma_plx/plx)^2). Measured in
  our subset: relative distance-skew median 1.6e-7, worst 3.9e-3.
- Where in repo: `galnav/truth/sampling.py` (sample_true_skies samples
  parallax, not distance); `journal/spec-e6a-sampled-sky.md` (the measured
  Jensen/Lutz-Kelker magnitudes).
- Verified: standard Gaia-era distance-estimation reference; students should
  sight the original before the paper's methods section is finalized
  (WebFetch unavailable in the build session, 2026-07-16).

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

**[JY]** IAU recommendation: the Julian year is exactly 365.25 days of
86400 SI seconds (31,557,600 s); one light year = c x one Julian year.
- Used for: the light-year-to-au conversion behind the anchor test's
  spacecraft-distance range (Bailer-Jones draws distances in ly).
- Where in repo: `galnav/units.py` (AU_PER_LY, moved there 2026-07-15
  after the spec review — conversions live in units.py, nowhere else; and
  KMS_PER_AU_YR = AU_KM / (365.25 x 86400), added Spec 10 for catalog
  aging — km/s per au/yr, ~4.7405); used by `tests/test_bj_anchor.py` and
  `tests/test_spec10_aging.py`.
- Verified: definitional; cross-checked AU_PER_LY = 63,241.077 au
  against the standard value, 2026-07-15; KMS_PER_AU_YR = 4.740470... and
  the 30 km/s -> 6.3285 au/yr radial drift cross-checked 2026-07-16.

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
- Where in repo: `tests/golden_numbers.py` (COMB_KM); `galnav/pulsar.py`
  (PULSAR_PERIODS_S, the six periods used by comb_spacing_km);
  `tests/test_e5_pulsar.py`; `journal/spec-e5-pulsar-lattice.md`.
- Note: periods rounded to the digits shown; comb values verified to agree
  with c x P within 1 km (recomputed 2026-07-14; re-verified 2026-07-16 for
  the E5-lite card). Sub-km flag for ratification: J0030+0451's frozen COMB_KM
  1459 km rounds up from c x P = 1458.49 km (nearest integer 1458); the 0.51 km
  gap is inside Spec 8's 1 km spec but the frozen value is the non-nearest
  integer — recorded, not changed (golden file is frozen).

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

**[GaiaPM]** Gaia DR3 online documentation, `gaia_source` data model
(ESA/Gaia/DPAC, Gaia DR3 documentation, table gaiadr3.gaia_source, fields
`pmra`/`pmdec`). https://gea.esac.esa.int/archive/documentation/GDR3/
- Fact used: the `pmra` column is the proper motion in the RA *direction*
  ALREADY multiplied by cos(dec) — i.e. pmra = pmra* = mu_alpha* =
  mu_alpha·cos(dec) (the documentation writes "Proper motion in right
  ascension direction, pmRA = mu_alpha* = mu_alpha·cos(delta)"). `pmdec`
  is the plain proper motion in declination. CONSEQUENCE for Spec 10: the
  east tangential-velocity component is d·pmra with NO extra cos(dec)
  factor; applying one would halve the transverse speed at dec = 60 deg
  (the T3 trap).
- Where in repo: `galnav/truth/sky.py` and `galnav/nav/catalog.py`
  (star_velocities_kms, both independently); `tests/test_spec10_aging.py`
  (T3, T5); `journal/spec-10-catalog-aging.md`.
- Verified: the pmra*/cos(dec) convention is standard across Gaia DR1-DR3
  and stated in the gaia_source data-model docs; students should sight the
  online field description before the paper's methods section is finalized
  (WebFetch was unavailable in the build session, 2026-07-16).

**[NICERarch]** NICER (Neutron star Interior Composition Explorer) public
data archive, HEASARC, NASA GSFC.
https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs/
- Used for: the E4/Spec 9 RAW PHOTON DATA — six ObsIDs, two per pulsar:
  PSR J0030+0451 (1060020263, 1060020113 — the Riley et al. 2019 /
  Bogdanov et al. 2019 NICER campaign era), PSR B1937+21 (1070020148,
  1070020147), PSR J0437-4715 (1060010188, 1060010157 — the Choudhury et
  al. 2024 dataset era). Cleaned level-2 event files (cl.evt.gz) plus ISS
  orbit files (.orb.gz, required for barycentering). ~90.4 MB total.
- Where in repo: `data/e4_nicer/` (raw files git-ignored; committed
  `README.md` carries the full provenance table + sha256 manifest;
  `fetch_e4_data.py` re-fetches and re-verifies everything from scratch);
  Spec 9 tests (tests_armor/); experiment E4.
- Verified: each ObsID's archive directory listing fetched 2026-07-16 and
  both files confirmed present BEFORE download; after download every file
  passed byte-count, gzip-decompression, and sha256 recording; FITS headers
  confirm OBS_ID == path ObsID, OBJECT == claimed pulsar, EXPOSURE == the
  listed exposure for all six event files (astropy.io.fits, 2026-07-16).

**[NICER16]** Gendreau, K. C., Arzoumanian, Z., & Okajima, T. (2016). "The
Neutron star Interior Composition Explorer (NICER): design and development."
*Proc. SPIE*, 9905, 99051H.
- Used for: the instrument citation behind all E4/Spec 9 photon data (the
  paper's methods section must cite the instrument, not just the archive).
- Where in repo: `data/e4_nicer/README.md`; future paper methods.
- Verified: standard NICER instrument reference; students should sight the
  SPIE page before the paper's reference list is finalized.

**[NG15]** Agazie, G., et al. (NANOGrav Collaboration) (2023). "The
NANOGrav 15 yr Data Set: Observations and Timing of 68 Millisecond
Pulsars." *The Astrophysical Journal Letters*, 951, L9. Data release:
Zenodo, doi:10.5281/zenodo.16051178 (v2.1.0, 2025-07).
- Used for: the PSR J0030+0451 narrowband timing model
  (`data/e4_nicer/pars/J0030+0451_PINT_20220302.nb.par`, sha256 in
  data/e4_nicer/README.md) that anchors Spec 9's photon-phase tests and
  E4's folds. Internal NG15 processing fingerprint verified; physics
  cross-check F0 -> P = 4.86545 ms vs the frozen comb table's untruncated
  4.8654 ms (0.002%). Byte-verification against the 638.7 MB release
  tarball DEFERRED (recorded md5 557d42dd8486a5f8272d90dec9b228a8; one
  command at the ratification sitting).
- Where in repo: `data/e4_nicer/pars/`; `tests_armor/`;
  `journal/spec-9-photon-phase.md`; worksheet item (hh).
- Verified: Zenodo record fetched live 2026-07-16 (doi + tarball
  manifest); the ApJL bibliographic details should be sighted by the
  students before the paper's reference list is finalized.

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

**[deJager89]** de Jager, O. C., Raubenheimer, B. C., & Swanepoel, J. W. H.
(1989). "A powerful test for weak periodic signals with unknown light curve
shape in sparse data." *Astronomy & Astrophysics*, 221, 180.
- Fact/method used: the H-test STATISTIC for pulsation significance,
  H = max_{m<=20} (Z^2_m - 4m + 4) with Z^2_m the Rayleigh power summed
  over the first m harmonics. E4 uses it as the fold-cleanliness gate
  (frozen E4_HTEST_MIN, override #13) and it is the method the compass
  section-11 budget row itself names ("H-test / template"). The
  significance SHORTHAND p ~ exp(-0.4 H) is NOT from this paper — it is
  the later calibration of [deJagerBusching10]; the attribution was
  corrected by the 2026-07-16 doubt-everything sweep.
- Where in repo: `tests_armor/_e4_fold.py` (htest);
  `tests_armor/test_e4_injection.py` (T2); `tests/golden_numbers.py`
  (E4_HTEST_MIN comment); `journal/e4-nicer-injection.md`.
- Verified: standard X-ray pulsar-timing statistic (PINT ships the same
  test in pint.eventstats, cross-checked at Spec 9: hm() on the J0030
  fold matched our implementation's H = 77.4); students should sight the
  original before the paper's reference list is finalized.

**[deJagerBusching10]** de Jager, O. C., & Büsching, I. (2010). "The
H-test probability distribution revisited: improved sensitivity."
*Astronomy & Astrophysics*, 517, L9. arXiv:1005.4867.
- Fact/method used: the exponential false-alarm calibration of the H-test,
  p ~ exp(-0.4 H), valid over the full useful range — the form quoted in
  tests_armor/_e4_fold.py's htest docstring, the E4_HTEST_MIN golden
  comment's p-values, and the E4 journal tables (e.g. H = 20 -> p ~ 3e-4;
  H = 77.4 -> p ~ 4e-14).
- Where in repo: `tests_armor/_e4_fold.py` (htest);
  `journal/e4-nicer-injection.md`; `tests/golden_numbers.py`
  (E4_HTEST_MIN comment context).
- Verified: identified live by the 2026-07-16 doubt-everything sweep
  (arXiv:1005.4867), which caught the p-form's earlier misattribution to
  [deJager89]; students should sight the A&A letter before the reference
  list is finalized.

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

**[PINT]** Luo, J., Ransom, S., Demorest, P., Ray, P. S., et al. (2021).
"PINT: A Modern Software Package for Pulsar Timing." *The Astrophysical
Journal*, 911, 45. doi:10.3847/1538-4357/abe62f
- Used for: ALL armor-tier photon-phase computation (Spec 9 and E4) —
  satellite barycentering from the ISS orbit file, the clock chain, and
  the spin-down phase (pint-pulsar==1.1.4; environment in
  journal/environment-armor.md). Cite in the paper's methods alongside
  [NumPy]/[Astropy].
- Where in repo: `tests_armor/_pint_routes.py`;
  `journal/spec-9-photon-phase.md`; `requirements-armor.txt`.
- Verified: citation confirmed against the IOPscience article page,
  2026-07-16 (ApJ 911, 45; doi:10.3847/1538-4357/abe62f).

**[LAMBDA]** Teunissen, P. J. G. (1995). "The least-squares ambiguity
decorrelation adjustment: a method for fast GPS integer ambiguity
estimation." *Journal of Geodesy*, 70, 65-82.
- Fact/method used: the phase-comb navigation ambiguity is an INTEGER
  least-squares problem on a lattice (the same structure as GPS carrier-phase
  ambiguity resolution). The largest prior position uncertainty for which the
  correct integer set is still unambiguous is the packing radius rho =
  lambda_1 / 2 (half the shortest lattice vector). E5-lite uses only this
  packing-radius criterion — it does NOT run the LAMBDA decorrelation/search
  itself. UPDATE 2026-07-16: the d=3 closest-vector solver itself landed as
  `closest_lattice_point` (Spec 8b — Babai rounding + exact 27-box, see
  [Babai86]); LAMBDA-style decorrelation / general LLL for near-degenerate
  geometries stays the deferred follow-up.
- Where in repo: `galnav/pulsar.py` (ambiguity_lattice_generator,
  shortest_vector_km, packing_radius_km, closest_lattice_point);
  `tests/test_e5_pulsar.py`; `tests/test_spec8_cvp.py`;
  `journal/spec-e5-pulsar-lattice.md`; `journal/spec-8-cvp-solver.md`. The
  plan's E5-lite run-book (section 7) is the internal source that establishes
  this framing and the GPS analogy.
- Verified against the project plan's own citation; students should sight the
  Teunissen original before the paper's methods section (WebFetch unavailable
  in the build session, 2026-07-16).

**[Babai86]** Babai, L. (1986). "On Lovász' lattice reduction and the nearest
lattice point problem." *Combinatorica*, 6(1), 1–13. doi:10.1007/BF02579403
- Fact/method used: the nearest-lattice-point estimate m0 = round(B^{-1} t) —
  round the target's lattice coordinates to the nearest integers.
  `closest_lattice_point` uses this as its first guess, then refines exactly
  over the 27-point {-1,0,+1}^3 offset box to correct the off-by-one that
  simple rounding makes on a skewed lattice. This is the "rounding off"
  heuristic of the paper (Babai also gives a stronger "nearest plane"
  variant); at dimension 3, for the project's well-conditioned §12 geometries,
  rounding + the ±1 box is exact (measured: Babai lands within one L-inf step
  of the true integer here). NOT the general c^d-approximation LLL machinery —
  that stays the deferred fpylll/LLL follow-up card.
- Where in repo: `galnav/pulsar.py` (closest_lattice_point);
  `tests/test_spec8_cvp.py`; `journal/spec-8-cvp-solver.md`.
- Verified: citation details (author, title, Combinatorica vol. 6(1)
  pp. 1–13, 1986, doi:10.1007/BF02579403) confirmed via web 2026-07-16
  (Springer Nature Link, ACM DL, Semantic Scholar); students should sight the
  Babai original before the paper's methods section is finalized.

## Related work (prior-art re-sweep 2026-07-16 — positioning, not method sources)

**[Deng13]** Deng, X. P., Hobbs, G., You, X. P., et al. (2013). "Interplanetary
spacecraft navigation using pulsars." *Advances in Space Research*, 52, 1602.
arXiv:1307.5375. https://arxiv.org/abs/1307.5375
- Used for: related work bounding E5-lite. Demonstrates pulsar navigation IN THE
  SOLAR SYSTEM (Earth->Mars, 4 MSPs every 7 days -> ~20 km position, ~0.1 m/s).
  Establishes that pulsar comb navigation is a working solar-system technique;
  E5-lite's contribution is the INTERSTELLAR limit, where the star-fix prior is
  too coarse to lock the comb — NOT a claim that pulsar nav fails in general.
- Where in repo: `journal/spec-e5-pulsar-lattice.md` (related work); future
  paper related-work section. Verified: abstract via arXiv, 2026-07-16.

**[Becker13]** Becker, W., Bernhardt, M. G., & Jessner, A. (2013). "Autonomous
Spacecraft Navigation With Pulsars." *Acta Futura*, 7, 11. arXiv:1305.4842.
https://arxiv.org/abs/1305.4842
- Used for: the review that states pulsar navigation works "everywhere in the
  solar system AND BEYOND." E5-lite QUANTITATIVELY BOUNDS the "and beyond":
  beyond the solar system, without an au-or-better prior the comb integer is
  unresolvable from a ~1 au starlight fix (4+ order gap). This is the specific
  prior-art claim our finding sharpens.
- Where in repo: `journal/spec-e5-pulsar-lattice.md`; paper related work.
  Verified: abstract via arXiv, 2026-07-16.

**[AbsAstro50]** Malbet, F., et al. / Hobbs, D., et al. (2014). "Absolute
astrometry in the next 50 years." arXiv:1408.2190. https://arxiv.org/abs/1408.2190
- Used for: related work bounding E6. The astrometric community KNOWS catalog
  accuracy degrades with epoch as proper-motion errors accumulate (Gaia position
  error grows ~1.76 mas in 2026 -> ~3.5 mas 2036 -> ~8.8 mas 2066). E6's novelty
  is therefore NOT "catalogs age" (known) but the systematic MAP of interstellar
  NAVIGATION error over (catalog age x sensor precision) with the crossover locus
  and epoch-parallax floor — which the 2026-07-16 sweep found unpublished.
- Where in repo: `journal/logbook.md` (2026-07-16 prior-art re-sweep); future
  paper related-work. Verified: via WebSearch summary, 2026-07-16 (students
  should sight the paper before the paper's methods; WebFetch was denied).

**[DSNcompare21]** "Comparison of Deep Space Navigation Using Optical Imaging,
Pulsar Time-of-Arrival Tracking, and/or Radiometric Tracking." *The Journal of
the Astronautical Sciences* (2021). doi:10.1007/s40295-021-00290-z
- Used for: THE closest related work to the project's overall framing — it
  compares the same three modalities (optical / pulsar / radiometric) this
  project spans. MUST be cited and distinguished: it is a SOLAR-SYSTEM
  deep-space comparison, not an INTERSTELLAR catalog-aging trade study, and it
  does not map navigation error over (catalog age x sensor precision) or give
  the crossover. Students: retrieve authors + exact result and distinguish
  explicitly in related work. Verified: title/venue/doi via WebSearch,
  2026-07-16 (WebFetch denied; sight the paper before drafting).

**[StarNAV19]** Christian, J. A. (2019). "StarNAV: Autonomous Optical
Navigation of a Spacecraft by the Relativistic Perturbation of Starlight."
*Sensors*, 19(19), 4064. https://www.mdpi.com/1424-8220/19/19/4064
- Used for: related work for the STARLIGHT leg — autonomous optical navigation
  by starlight aberration/relativistic perturbation. Adjacent method; does not
  address catalog aging or the fused-bootstrap pulsar limit. (Author to be
  confirmed by students; StarNAV is the Christian-group concept.) Verified:
  title/venue via WebSearch, 2026-07-16.

**[YucalanPeck19]** Yucalan, D., & Peck, M. A. (2019). "A Static Estimation
Method for Autonomous Navigation of Relativistic Spacecraft." *IEEE Aerospace
Conference*. doi:10.1109/AERO.2019.8741804
- Used for: related work bounding E6 — the closest interstellar-StarNAV prior
  art found by the 2026-07-16 dead-leg re-run (Earth->Proxima at 0.2c, star
  tracker + spectrometer; "error stems principally from uncertainty in the
  star catalog"). The catalog is treated as a STATIC fixed-epoch error; no
  catalog-AGE sweep, no (age x sensor) map, no crossover — which is exactly
  E6's contribution. MUST cite and distinguish.
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run); future
  paper related-work. Verified: abstract via OpenAlex, 2026-07-16 (students
  should sight the paper before related-work is drafted).

**[YucalanPeck21]** Yucalan, D., & Peck, M. A. (2021). "An Optimal Navigation
Filter for Relativistic Spacecraft." *AIAA SciTech Forum*, AIAA 2021-1868.
doi:10.2514/6.2021-1868
- Used for: related work bounding E6 — interstellar EKF by the same group;
  catalog uncertainty named the dominant error floor, with future astrometry
  "up to five orders" better. Treats catalog PRECISION at a fixed epoch, not
  catalog AGE; no aging map. MUST cite and distinguish.
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run); future
  paper related-work. Verified: abstract via OpenAlex, 2026-07-16 (students
  should sight before drafting).

**[ZhangLiLiu26]** Zhang, D.-D., Li, M., & Liu, N. (2026). "Astrometric
Systematic Errors as a Limiting Factor in Stellar-Aberration-Based Autonomous
Navigation." *Universe*, 12(7), 197. doi:10.3390/universe12070197
- Used for: related work bounding E6 — propagates Gaia DR3 covariance and
  plate-model systematics to a SINGLE epoch (J2026.0) and derives a VELOCITY
  floor (0.9-2.5 m/s) for aberration-based navigation. Distinct twice over:
  single-epoch (no age sweep, no crossover) and a velocity floor from plate
  systematics, not E6's epoch-parallax POSITION floor. MUST cite and
  distinguish — closest published "systematics floor" result to E6's.
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run); future
  paper related-work. Verified: abstract via Semantic Scholar, 2026-07-16
  (students should sight before drafting).

**[Franzese26]** Franzese, V. (2026). "Star-based Navigation in the Outer
Solar System." *Journal of Guidance, Control, and Dynamics*.
doi:10.2514/1.g009764. arXiv:2603.06247
- Used for: related work for the starlight leg — parallax-shift navigation
  demonstrated to 250 AU (Voyager/Pioneer/New Horizons regime), sub-au
  accuracy, FIXED catalog. Bounds E6/E1 from the near side: outer solar
  system, not interstellar, and no catalog aging. Cite and distinguish the
  range regime.
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run); future
  paper related-work. Verified: abstract via Semantic Scholar, 2026-07-16
  (students should sight before drafting).

**[Shemar16]** Shemar, S., et al. (2016). "Towards practical autonomous
deep-space navigation using X-ray pulsar timing." *Experimental Astronomy*,
42, 101. doi:10.1007/s10686-016-9496-z
- Used for: related work bounding E5-lite — the ESA XNAV study (B1937+21,
  ~2-5 km position to 30 AU) reinforcing that solar-system pulsar navigation
  is ESTABLISHED. E5-lite's narrow claim starts where this ends: at
  interstellar range a ~1 au starlight fix cannot bootstrap the comb integer
  (4+ orders vs the packing radius). Strengthens the required narrow framing.
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run);
  journal/spec-e5-pulsar-lattice.md related work; future paper. Verified:
  abstract via OpenAlex, 2026-07-16 (students should sight before drafting).

## Learning resources consulted (log for the ISEF logbook, not paper refs)

- Khan Academy, "Defining the angle between vectors."
  https://www.khanacademy.org/math/linear-algebra/v/defining-the-angle-between-vectors
- 3Blue1Brown, "Essence of Linear Algebra," chapters 1 and 9.
  https://www.youtube.com/watch?v=fNk_zzaMoSs and
  https://www.youtube.com/watch?v=LyGKycYT2v0
