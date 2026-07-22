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
  on 2026-07-15. Peer-reviewed venue confirmed 2026-07-16, article locator corrected by
  the 2026-07-17 sweep via Crossref: AJ 170, 22 (2025) — "170, 1" was the
  issue, not the article; the 0.44 au result is a 0.441 x 0.233 x 0.206 au error ellipsoid
  vs JPL (notebook cell, 2026-07-16).
- CONCLUDING CLAIM (verbatim, sighted 2026-07-22): "We conclude that the
  best astrometric approach to navigating spacecraft on their departures to
  interstellar space is to use a single pair of the closest stars as
  references, rather than a large sample of more distant stars." It is
  asserted as a RECOMMENDATION from their analysis, not proven as a theorem
  — the seed of a PROPOSED pair-vs-ensemble CRLB card (awaiting student
  ruling).

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

**[TESS-TPF]** NASA/MAST, "TESS Science Data Products Description Document"
(EXP-TESS-ARC-ICD-0014) — Target Pixel File (TPF) format. https://archive.stsci.edu/missions-and-data/tess
- Used for: the demo's arbitrary-image loader. A SPOC/TESScut target-pixel
  file stores its imagery as a `FLUX` column of per-cadence 2-D cutouts in a
  binary-table HDU (EXTNAME `PIXELS`); the only IMAGE HDU is the `APERTURE`
  mask (integer bit-flags, ~all ones over the cutout). `gui/app.py`
  `load_grayscale` therefore detects the PIXELS table and returns the
  pixel-wise MEDIAN over cadences (NaN gaps ignored) so a TPF centroids like
  any other frame, instead of loading the flat aperture mask.
- Where in repo: `gui/app.py` (`_tpf_median_frame`, `load_grayscale`);
  `tests_gui/test_load_grayscale.py` (synthetic TPF, no data committed).
- Retrieval note: verified 2026-07-17 against a real MAST TESScut cutout of
  Proxima (Sector 11, 30x30 px) held only in git-ignored `data/candidates/`.

**[DSS]** STScI Digitized Sky Survey (POSS-I Palomar Schmidt; POSS-II Oschin
Schmidt; AAO/UKST southern). https://archive.stsci.edu/cgi-bin/dss_form
- REQUIRED ACKNOWLEDGMENT (verbatim, STScI DSS copyright terms): "The Digitized
  Sky Surveys were produced at the Space Telescope Science Institute under U.S.
  Government grant NAG W-2166. The images of these surveys are based on
  photographic data obtained using the Oschin Schmidt Telescope on Palomar
  Mountain and the UK Schmidt Telescope."
- Used for: the six real POSS/DSS plate cutouts (Wolf 359, Proxima, Barnard) that
  stress-test the single-star drift chronometer (negative catalog ages, dense-field
  false-minimum fix). WCS read straight from each header.
- Where used: displayed in the web demo when a DSS plate is loaded, so the
  acknowledgment also appears verbatim in the page footer (`gui/web/index.html`,
  `.credits`); data in git-ignored `data/candidates/dss/` (see its MANIFEST.md).
- License: public domain (US Gov/STScI); free for research per the DSS copyright
  terms. Retrieved 2026-07-17.

**[HLA]** Hubble Legacy Archive (STScI), WFPC2 F814W drizzled product
`hst_05132_08_wfpc2_f814w_wf` (Proposal 5132, WFPC2 astrometry; TARGNAME
BD+4D3561 = Barnard's Star, DATE-OBS 1995-04-22). https://hla.stsci.edu
- Used for: a real HST frame in the candidate stress-test set (plate-solves via
  header WCS; trips a cosmetic astropy SIP/CTYPE warning noted in the journal).
- Where used: `data/candidates/hst/` (git-ignored); credit NASA/ESA HST, HLA/STScI.
- License: public domain. Retrieved 2026-07-17.

**[CC-Centaurus]** Till Credner (AlltheSky.com), "Constellation Centaurus,"
Wikimedia Commons, CC BY-SA 3.0.
https://commons.wikimedia.org/wiki/File:Constellation_Centaurus.jpg
- Where used: `data/candidates/raw_photos/centaurus_alphacen_credner.jpg`
  (git-ignored), a no-WCS wide-field photo exercising the blind-solve tier.

**[CC-Orion]** "Madonka," "Constellation Orion," Wikimedia Commons, CC0 (public
domain). https://commons.wikimedia.org/wiki/File:Constellation_Orion.jpg
- Where used: `data/candidates/raw_photos/orion_credner.jpg` (git-ignored),
  a no-WCS wide-field photo exercising the blind-solve tier.

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

**[AstrometryNet]** Lang, D., Hogg, D. W., Mierle, K., Blanton, M., &
Roweis, S. (2010). "Astrometry.net: Blind astrometric calibration of
arbitrary astronomical images." *The Astronomical Journal*, 139, 1782–1800.
doi:10.1088/0004-6256/139/5/1782
- Used for: the blind plate-solver behind the GUI demo's world-coordinate
  step (`gui/platesolve.py`). The tool reads a WCS three ways — straight from
  a solved FITS header (the New Horizons "pwcs2" frames), from a local
  astrometry.net `solve-field` run via WSL, or from the nova.astrometry.net
  web service — all three being astrometry.net-family solutions. NOT part of
  the science spine; a demo-layer convenience so a user can upload a raw
  star-field image and get RA/Dec per pixel.
- Where in repo: `gui/platesolve.py` (fits_header_solution, wsl_solve,
  nova_solve, solve_image); `journal/gui-wrapper.md`; `gui/README.md`.
- Verified: canonical astrometry.net paper (AJ 139, 1782), citation as used
  by the astrometry.net project itself; students should sight the original
  before any paper mention of the demo tool.

**[NovaAPI]** Astrometry.net. "nova.astrometry.net API documentation."
http://nova.astrometry.net/api_help (client protocol: session login,
image upload, submission/job polling, WCS-file download).
- Used for: the exact request sequence `gui/platesolve.py::nova_solve`
  implements with stdlib `urllib` (POST request-json login → multipart
  upload → poll `/api/submissions/{id}` then `/api/jobs/{id}` → download
  `/wcs_file/{id}`), mirroring the repo's stdlib-urllib data-fetch precedent.
- Where in repo: `gui/platesolve.py` (nova_solve and its `_http_json` /
  `_nova_multipart` helpers); `journal/gui-wrapper.md`; `gui/README.md`.
- Verified: API endpoint shapes taken from the public api_help page and the
  astrometry.net `client.py` reference protocol; the parse is covered offline
  by `tests_gui/test_platesolve.py` against a monkeypatched urlopen.

**[Spacekit]** Ian Webster, "spacekit.js" — JavaScript library for 3-D space
visualizations. MIT License, © 2019 Ian Webster. Vendored from
github.com/typpo/spacekit, master @ aa93d3f (build:
typpo.github.io/spacekit/build/spacekit.js), retrieved 2026-07-17. Bundles
three.js (MIT). Used for the "Where in Space" demo view (gui/web). Skybox image:
ESO GigaGalaxy Milky Way panorama, credit ESO/S. Brunier (CC BY). Bright stars:
Yale Bright Star Catalog. Equatorial-ICRS -> ecliptic conversion applied at
23.43928 deg obliquity.
- Where in repo: `gui/web/vendor/spacekit/` (spacekit.js + assets + data +
  `SOURCES.md` with the full per-file provenance table + LICENSE terms);
  `gui/web/where-in-space.html` (the two-scene view); `gui/web/app.js` (lazy
  iframe wiring); `journal/gui-wrapper.md`.
- Verified: offline (basePath set to `./vendor/spacekit`, so no external host is
  contacted — the recipe's headless network log showed 8/8 requests local); the
  static-serving + traversal guard is covered by `tests_gui/test_webapp.py`, and
  a browser drive confirmed both scenes render (WebGL canvas, 19 au-scene labels,
  the 5 famous-star pc labels).
- REMOVED 2026-07-21: the vendored tree, the view page and their tests were
  deleted outright (OpenSpace is the only viewer). Entry kept as the record of
  what shipped 2026-07-17 → 2026-07-21.

**[WhereInSpace-data]** Nearby-stars scene: Gaia DR3, GalNav
`data/gaia_dr3_nav_subset.csv` (1,941 stars within 20 pc; `dist_pc =
1000/parallax`), baked to ecliptic XYZ by `gui/web/vendor/spacekit/bake_gaia.py`.
Spacecraft positions (Voyager 1/2, Pioneer 10/11, New Horizons) and Eris are
approximate 2025-2026 values from NASA/JHUAPL mission pages, Wikipedia, and
TheSkyLive — full per-object sources in
`gui/web/vendor/spacekit/SOURCES.md` ("Scene data provenance").
- Where in repo: `gui/web/vendor/spacekit/data/gaia_20pc.json` (baked cloud),
  `gui/web/where-in-space.html` (hardcoded spacecraft markers, labelled "~N au"
  and framed as approximate), `gui/web/vendor/spacekit/SOURCES.md`.
- REMOVED 2026-07-21 together with the [Spacekit] tree (see above); kept for
  the record.

**[OpenSpace]** OpenSpace project — open-source (MIT) astrovisualization
software, NASA/AMNH/LiU-funded, openspaceproject.com; v0.22.0 (2026-06-12),
Windows build from data.openspaceproject.com/release/0.22.0/. NOT vendored and
NOT part of the pipeline or any result: it is the optional booth SHOW layer.
GalNav exports a fix into it via `gui/openspace_export.py`. Frame facts used
(from the OpenSpace source): scene graph is galactic-frame METRES with
solar-system objects parented to `SolarSystemBarycenter`; the J2000-equatorial
<-> galactic rotation it ships (modules/skybrowser/src/utility.cpp) is the
Hipparcos Vol. 1 Sect. 1.5.3 matrix, which `gui/openspace_export.py` mirrors.
- Where in repo: `gui/openspace_export.py` (exporter + CLI),
  `tests_gui/test_openspace_export.py`, `journal/gui-openspace.md`.
- Verified: rotation cross-checked against astropy's independent galactic
  frame (worst 0.025 arcsec definition-level disagreement, measured, see the
  test docstring); norm preservation exact; asset text pinned by tests.

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

**[SEXTANT18]** Winternitz, L. B., et al. (2018). SEXTANT on NICER/ISS —
the first real-time, in-space autonomous XNAV demonstration (Nov 2017),
4 MSPs (J0437-4715, J0030+0451, B1821-24, J0218+4232).
- Used for: related work bounding E4/E5 — flight XNAV is demonstrated IN
  EARTH ORBIT with a tight dynamical prior; the error reached and held below
  10 km RSS within ~7.5 h (goal < 10 km worst-direction). E5's interstellar
  no-bootstrap claim is untouched by it (an Earth-orbit prior is nothing like
  a ~1 au starlight fix).
- Where in repo: journal/findings-compilation.md (F14 / E5 framing); future
  paper related-work.
- Verified: 2026-07-22 via the 2018 on-orbit-results papers; the exact NTRS
  report ID could not be individually pinned — students should locate the
  canonical citation before drafting.

**[ZhengHXMT19]** Zheng, S.-J., et al. (2019). "In-orbit Demonstration of
X-Ray Pulsar Navigation with the Insight-HXMT Satellite." *The Astrophysical
Journal Supplement Series*, 244, 1. doi:10.3847/1538-4365/ab3718.
arXiv:1908.01922.
- Used for: related work, the same positioning as [SEXTANT18] — Crab, a
  5-day observation (2017 Aug 31 - Sep 5), position within 10 km (3-sigma)
  and velocity within 10 m/s (3-sigma) by the SEPO method; also the SEPO
  lineage that NinjaSat later reuses.
- Where in repo: journal/findings-compilation.md (F14 / E5 framing); future
  paper related-work.
- Verified: abstract + ADS, 2026-07-22.

**[NinjaSat26]** Ota, N., et al. (2026). "In-orbit Demonstration of X-ray
Pulsar Navigation with NinjaSat." *Journal of Astronomical Telescopes,
Instruments, and Systems*, 12, 018002. doi:10.1117/1.JATIS.12.1.018002.
arXiv:2602.14166.
- Used for: related work for E5/F14 framing — a 6U CubeSat with two Gas
  Multiplier Counters (16 cm^2/module at 6 keV, 2-50 keV), Crab ~100 ks;
  timing stable within 100 us; the Crab line-of-sight constrained to ~40 km
  and 3-D position 27-370 km depending on epoch. It is the FIRST experimental
  verification that SEPO accuracy depends on seasonal geometry (the paper's
  explicit "first" — it does NOT claim "first CubeSat XNAV" primacy; record
  the nuance). The XNAV instrument class is shrinking toward CubeSat
  mass/power, which strengthens the relevance of the interstellar
  acquisition/hold analysis.
- Where in repo: journal/findings-compilation.md (F14 / E5 framing); future
  paper related-work.
- Verified: primary sighted via arXiv, 2026-07-22.

**[PulsarClock26]** Iyer, V., & Bandi, T. N. (2026). "Pulsars as Natural
Oscillators for Long-Term Deep-Space Missions." *NAVIGATION: Journal of the
Institute of Navigation*, 73(1), navi.733. doi:10.33012/navi.733.
- Used for: related work for the TIME leg ("when you are") — NANOGrav 15-yr
  data, 68 MSPs; several pulsars enable sub-kilometre-equivalent range
  stability over averaging periods of 100 days to >15 years, an onboard
  pulsar ensemble reaching ~1e-16 fractional stability over 10+ yr. Treats
  pulsars as onboard OSCILLATORS built from ground-PTA data; a
  simulation/timescale analysis only — no autonomous absolute-time recovery
  from real spacecraft photon data (the gap a proposed E9 card would fill;
  awaiting student ruling).
- Where in repo: journal/findings-compilation.md (time leg); future paper
  related-work.
- Verified: primary sighted via navi.ion.org, 2026-07-22.

**[AbsAstro50]** Høg, E. (2014). "Absolute astrometry in the next 50
years." arXiv:1408.2190. https://arxiv.org/abs/1408.2190 (author corrected
by the 2026-07-17 sweep — the arXiv record's sole author is Erik Høg; the
earlier "Malbet/Hobbs et al." attribution was wrong)
- Used for: related work bounding E6. The astrometric community KNOWS catalog
  accuracy degrades with epoch as proper-motion errors accumulate (Gaia position
  error grows ~1.76 mas in 2026 -> ~3.5 mas 2036 -> ~8.8 mas 2066). E6's novelty
  is therefore NOT "catalogs age" (known) but the systematic MAP of interstellar
  NAVIGATION error over (catalog age x sensor precision) with the crossover locus
  and epoch-parallax floor — which the 2026-07-16 sweep found unpublished.
- Where in repo: `journal/logbook.md` (2026-07-16 prior-art re-sweep); future
  paper related-work. Verified: via WebSearch summary, 2026-07-16 (students
  should sight the paper before the paper's methods; WebFetch was denied).

**[DSNcompare21]** Ely, T., Bhaskaran, S., Bradley, N., Lazio, T. J. W., &
Martin-Mur, T. (2022). "Comparison of Deep Space Navigation Using Optical
Imaging, Pulsar Time-of-Arrival Tracking, and/or Radiometric Tracking."
*The Journal of the Astronautical Sciences*, 69, 385-472.
doi:10.1007/s40295-021-00290-z. arXiv:2205.08652. (JPL authors; year
corrected 2021 -> 2022 from the primary, 2026-07-22 — the [DSNcompare21]
tag keeps its original name to preserve cross-references.)
- Used for: THE closest related work to the project's overall framing — it
  compares the same three modalities (optical / pulsar / radiometric) this
  project spans. EXACT RESULTS (from the primary): pulsar-only navigation
  21-72 km at Mars (best-4 vs all-8 SEXTANT pulsars) and 34-1310 km at
  Neptune; instrument model is 4 of the 56 SEXTANT collimators, A = 129 cm^2,
  3-hr integrations per pulsar per 24 h; method is a semi-analytic GDOP plus
  a Mars Monte Carlo; simulation only. MUST be cited and distinguished: it is
  a SOLAR-SYSTEM deep-space comparison, not an INTERSTELLAR catalog-aging
  trade study, and it does not map navigation error over (catalog age x
  sensor precision) or give the crossover. HONEST distinction (do not
  overclaim): Part 2's Monte Carlo DOES test combinations of the three data
  types, so the paper is not "no fusion" flatly — the precise absence is a
  UNIFIED SIMULTANEOUS fusion estimator; and it carries NO integer-ambiguity
  analysis and NO catalog-aging axis.
- Where in repo: journal/findings-compilation.md (F4 must-distinguish);
  future paper related-work.
- Verified: authors, venue (JAS 69, 385-472), year 2022, doi and
  arXiv:2205.08652 sighted from the primary (arXiv:2205.08652, open-access
  PMC9098647), 2026-07-22; students should sight the paper before drafting.

**[StarNAV19]** Christian, J. A. (2019). "StarNAV: Autonomous Optical
Navigation of a Spacecraft by the Relativistic Perturbation of Starlight."
*Sensors*, 19(19), 4064. doi:10.3390/s19194064.
https://www.mdpi.com/1424-8220/19/19/4064
- Used for: related work for the STARLIGHT leg — autonomous optical navigation
  by starlight aberration/relativistic perturbation. Adjacent method; does not
  address catalog aging or the fused-bootstrap pulsar limit. From the primary:
  the most-promising technique is velocity recovery from the CHANGE in the
  inter-star angle induced by stellar aberration; the relativistic-Doppler
  spectral approach is judged "ineffective in practice"; the work is a NASA
  NIAC Phase I/II concept. Author hedge RESOLVED: sole author John A.
  Christian (RPI).
- Where in repo: journal/findings-compilation.md (F13 must-cite); future
  paper related-work.
- Verified: primary sighted 2026-07-22 (author J. A. Christian; Sensors
  19(19):4064, doi:10.3390/s19194064; the aberration-vs-Doppler technique
  split read from the full text). Earlier record: title/venue via WebSearch,
  2026-07-16.

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
- Journal version (better sight-target, same group): Yucalan, D., & Peck,
  M. A. (2021). "Autonomous Navigation of Relativistic Spacecraft in
  Interstellar Space." *Journal of Guidance, Control, and Dynamics* 44(6),
  1106-1115. doi:10.2514/1.G005340.
- CONFLATION GUARD (recorded 2026-07-22): the "~3 au / ~2 km/s from 20 stars
  at 1 arcsec" figures circulating in surveys belong to [BJ21], NOT to
  Yucalan-Peck (their full text is paywalled, unverified here) — do not
  conflate the two when drafting related work.
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
Solar System." *Journal of Guidance, Control, and Dynamics* (accepted).
doi:10.2514/1.g009764. arXiv:2603.06247. (Sole author: Vittorio Franzese.)
- Used for: related work for the starlight leg — parallax-shift navigation
  demonstrated to 250 AU (Voyager/Pioneer/New Horizons regime), sub-au
  accuracy, FIXED catalog. Bounds E6/E1 from the near side: outer solar
  system, not interstellar, and no catalog aging. Cite and distinguish the
  range regime.
- IMPORTANT correction (2026-07-22, full text): the simulations propagate
  the HIPPARCOS catalog, NOT Gaia DR3 — Gaia appears only as intro context.
  This matters to positioning because GalNav's catalog-aging axis is built
  ON Gaia DR3. Pulsar navigation gets a single passing mention (not
  investigated); and there is NO catalog-aging / epoch-degradation analysis
  (proper motion enters the observation model only).
- Where in repo: journal/logbook.md (2026-07-16 dead-leg re-run); future
  paper related-work. Verified: abstract via Semantic Scholar, 2026-07-16;
  full text sighted via arXiv HTML, 2026-07-22 (Hipparcos-not-Gaia, the
  single passing pulsar mention, and the no-aging finding all read
  directly); students should sight before drafting.

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

**[PulsarDoppler]** Liu, J., & Fang, J. (2015). "X-ray pulsar/starlight
Doppler deeply-integrated navigation." *IEEE Aerospace & Electronic
Systems Magazine* (doi:10.1109/MAES.2014.140074); and Wang, Y., Zheng,
W., & Zhang, D. (2017). *Journal of Navigation*
(doi:10.1017/S0373463317000042); plus siblings (Liu & Fang, AST 2015;
formation-flight variants 2015-2021).
- Used for: related work the paper MUST cite and distinguish — an
  identically-NAMED decade-old sub-field ("X-ray pulsar + starlight
  navigation") found by the 2026-07-17 doubt-everything red-team. The
  distinction, in one sentence: that body fuses pulsar timing with
  starlight DOPPLER (spectrometer radial velocity) as a VELOCITY aid for
  SOLAR-SYSTEM navigation; this project's claims concern INTERSTELLAR
  POSITION — the (catalog age x sensor) navigation-error map (E6) and the
  starlight-fix-cannot-bootstrap-the-comb-integer impossibility (E5) —
  neither of which that literature addresses. E5/E6 novelty survives; the
  naming collision must be defused up front.
- Where in repo: `journal/findings-compilation.md` (F5/F6 framing);
  future paper related-work. Verified: DOIs live-confirmed by the sweep,
  2026-07-17; students should sight both before drafting.

**[OpenSpace API]** OpenSpace Server-module remote interface: OpenSpace/
OpenSpace source (modules/server: TCP 4681 + WebSocket 4682 defaults in
`openspace.cfg`, localhost in AllowAddresses, newline-framed JSON topic
messages, `luascript` topic executes Lua remotely); the mandatory first-
message `apiHandshake` (`{"type":"apiHandshake","apiVersion":{"major":1,
"minor":0,"patch":0}}`) from the official client OpenSpace/openspace-api-js
(`src/api.ts`, `_sendHandshake`); framing cross-checked against
OpenSpace/openspace-api-python (`socketwrapper.py`: JSON + `"\n"`).
- Used for: `gui/openspace_link.py` — the live bridge behind the pipeline
  pages' "Show in OpenSpace" buttons.
- Where in repo: `gui/openspace_link.py` (protocol + every measured wire
  fact in docstrings), `tests_gui/test_openspace_link.py` (executable
  record), `journal/gui-pipeline-live.md`.
- Verified: against a LIVE OpenSpace 0.22.0 on the demo box, 2026-07-20 —
  handshake requirement, message-delivery timing (0/2 vs 9/9), and the
  navigation API behavior (`pathnavigation` nil; `flyTo` distance-
  preserving; `setNavigationState` exact) all measured directly, not taken
  from documentation.

### F12 candidate refs (starlight-chronometer / catalog-epoch dating — 2026-07-22)

These correct and replace the 2026-07-17 STRUCK "He&Zhao 2025" / "SESCC
2026" strings (the scout mis-cited year/venue; the 2026-07-17 check searched
the bad strings). F12 is [PROPOSED], awaiting student ruling; these are the
real, citable references behind it. Titles are recorded verbatim from the
2026-07-22 live fetches; students should still sight each paper before
the reference list is finalized.

**[HeZhao24]** He, B., & Zhao, Y. (2024). "Determining the observation
epochs of star catalogs from ancient China using the generalized Hough
transform method." *Astronomical Techniques and Instruments*, 1(2), 150-155.
arXiv:2504.02182.
- Used for: F12 candidate — epoch-dating a star catalog from star positions
  via a generalized Hough transform (precession-dominated regime). First
  half of the corrected "He&Zhao" pair.
- Verified: fetched live 2026-07-22.

**[HeZhao25]** He, B., & Zhao, Y. (2025). "Determining the observational
epoch of the Shi's star catalog using the generalized Hough transform
method." Accepted, *Research in Astronomy and Astrophysics*. arXiv:2504.02186.
- Used for: F12 candidate — the companion Hough-transform epoch-dating paper
  (Shi's catalog). Second half of the corrected "He&Zhao" pair.
- Verified: fetched live 2026-07-22.

**[BaigetOrts25]** Baiget Orts, C. (2025). "Astronomical Refutation of the
New Chronology by Fomenko and Nosovsky: The 1151-Year Planetary Cycle and
Dating of the Almagest via Speed/Error Correlation." arXiv:2504.12962.
- Used for: F12 candidate — defines SESCC = Speed-Error Signals Cross
  Correlation, dating the Almagest by cross-correlating each star's
  proper-motion SPEED against its positional ERROR. Corrects the struck
  "SESCC 2026" string (real year 2025).
- Verified: fetched live 2026-07-22.

**[NAROO21]** Robert, V., et al. (2021). "The NAROO digitization center —
Overview and scientific program." *Astronomy & Astrophysics*, 652, A3.
doi:10.1051/0004-6361/202140472.
- Used for: F12 supporting ref — plate re-reduction reaching ~15 mas .. 50
  uas, evidence the plate-era positional signal F12 leans on is measurable.
- Verified: fetched live 2026-07-22.

**[LSPM05]** Lepine, S., & Shara, M. M. (2005). "A Catalog of Northern
Stars with Annual Proper Motions Larger than 0.15″ (LSPM-North Catalog)."
*The Astronomical Journal*, 129, 1483. doi:10.1086/427854.
- Used for: F12 supporting ref — proper motions derived FROM POSS-I/II plate
  differencing (~8 mas/yr), the same position-difference signal F12
  formalizes.
- Verified: fetched live 2026-07-22.

**[DASCH10]** Laycock, S., et al. (2010). "Digital Access to a Sky Century
at Harvard. II: Initial Photometry and Astrometry." *The Astronomical
Journal*, 140, 1062. arXiv:0811.2005.
- Used for: F12 supporting ref — century-baseline digitized-plate astrometry,
  the long-baseline end of the plate-dating signal.
- Verified: fetched live 2026-07-22.

## Learning resources consulted (log for the ISEF logbook, not paper refs)

- Khan Academy, "Defining the angle between vectors."
  https://www.khanacademy.org/math/linear-algebra/v/defining-the-angle-between-vectors
- 3Blue1Brown, "Essence of Linear Algebra," chapters 1 and 9.
  https://www.youtube.com/watch?v=fNk_zzaMoSs and
  https://www.youtube.com/watch?v=LyGKycYT2v0
