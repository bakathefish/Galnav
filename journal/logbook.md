# GalNav Project Logbook

Dated record of every working session: what was done, what was decided and
why, what was proven, what's pending. Written so the paper's methods
section and the ISEF logbook can be reconstructed from this file alone.
Newest entries at the bottom. Commit hashes let anyone replay history.

Reminder: AI-use disclosure entries (which student drove, what was asked
of Claude Code) live separately in `ai_sessions/` — students only.

---

## 2026-07-12/13 — Session 1: repository scaffolding

- Created the repository and the full project skeleton (commit `fafba47`).
- Files created: CLAUDE.md rulebook; truth-wall package skeleton
  (`galnav/truth/`, `galnav/nav/`, all docstring-only stubs);
  `tests/golden_numbers.py` seeded from the master plan document §12;
  `tests/test_truth_wall.py` (AST test: nav/ may never import truth/);
  permission padlocks in `.claude/settings.json` denying Claude Code any
  edit to CLAUDE.md, golden_numbers.py, test_truth_wall.py, ai_sessions/;
  a bash-guard hook; the /spec card workflow; two read-only auditor agents
  (truth-wall-auditor, spec-reviewer).
- Design decision: the "truth wall" — simulator and navigator share
  nothing; the only interface is the measurement vector. Rationale: makes
  "the navigator can't cheat by peeking at the true answer" a provable,
  judge-defensible property.

## 2026-07-14 (night) — Session 2: Spec 1 acceptance test authored

- Wrote `tests/test_geometry.py`: five hand-checkable cases for
  angle_between (90 deg, 0 deg, 180 deg, argument-order symmetry,
  length-independence). No implementation code yet — test-first rule.
- Wrote first draft of `journal/spec-1-angle-geometry.md` (plain-English
  explainer of the dot-product angle formula).

## 2026-07-14 — Session 3: Spec 1 implemented, verified, and documented

- Implemented `galnav/geometry.py::angle_between` — 5 lines: dot product,
  two norms, divide, clip to [-1,1], arccos. Formula source: standard
  identity a·b = |a||b|cos(angle) [DOT in citations.md].
- `pytest -q`: 6/6 green (5 geometry + truth wall). Commit `af47aaf`.
- Independent audits: truth-wall-auditor PASS (nav/ has zero imports; new
  module imports only numpy). spec-reviewer PASS on 7/8 rules; flagged
  that the 1e-12 tolerance is hard-coded in the test file instead of
  living in golden_numbers.py. Students chose Option B (move it to
  golden_numbers.py); paste pending as of this entry.
- Git policy decision: no AI attribution lines in git history (rewrote the
  scaffolding commit message before anything was ever pushed; no remote
  exists). Rationale: AI disclosure is handled by the dedicated
  ai_sessions/ log and the paper's AI-use statement, not commit metadata.
  Verified zero matches for "claude" across all commit messages.
- Added THE JOURNAL RULE to the /spec workflow (commit `701aff4`): every
  card must end with a journal entry giving the exact formula, what the
  code does/does not do, why every tolerance value, why every test case,
  and (added later this session) citations for every outside fact.
- Upgraded `journal/spec-1-angle-geometry.md` with the "why 1e-12" section.

### Golden-number verification (triple check), 2026-07-14

1. **Recomputed from first principles** (Python, session transcript):
   PC_AU and RAD_ARCSEC = 648000/pi ✓; all six pulsar combs = c x P within
   1 km ✓; RV drift 6.328 au/yr ✓; wobble 200 mas ✓; aberration
   arcsin(0.1) = 5.739 deg ✓; curvature 656.9 au vs filed 656 (0.1% gap —
   depends on the pulsar distance used; students to re-derive when its
   spec card arrives); coast times 270.25 d and 2.70 d ✓; per-star floor
   412.5 au at 0.2%/1 pc ✓.
2. **Published anchors re-checked against sources**: Bailer-Jones numbers
   confirmed against the arXiv abstract [BJ21]; New Horizons 32.4/15.7
   arcsec confirmed against NASA press material [NASA20] / [Lauer25].
3. **Proposed new tolerances proven empirically before freezing**:
   - ANGLE_TOL_RAD = 1e-12: worst rounding error provoked in 20,000
     random scale-invariance trials = 3.6e-14 → 28x headroom.
   - PARALLAX_REL_TOL = 1e-6: true gap between exact geometry and the
     1-arcsec definition (dominated by the rounded PC_AU constant) =
     1.2e-9 → 840x headroom.
   - DISPLACEMENT_REL_TOL = 1e-5: built-in error of the D/d shortcut at
     the closest test star (D/d = 1e-3) = 3.3e-7 → 30x headroom.
- Created `journal/citations.md` (citation registry, where-used mapping)
  and this logbook.
- Environment note: CLAUDE.md pins Python 3.11; the machine currently
  runs Python 3.13. All tests pass on 3.13. Students should either
  install 3.11 or update the pin — decide before the first real
  experiment runs.

### Authorized override, 2026-07-14 (recorded for full transparency)

- The students explicitly authorized Claude Code to lift the edit-lock and
  perform the two pending pastes directly, after the paste contents had
  been shown to them in full, verified, and approved in conversation.
- What was changed under the override: (1) the three test tolerances
  (ANGLE_TOL_RAD, PARALLAX_REL_TOL, DISPLACEMENT_REL_TOL — values and
  empirical proof documented above) appended to `tests/golden_numbers.py`;
  (2) THE JOURNAL RULE section and one definition-of-done bullet added to
  `CLAUDE.md`. Nothing else in either file was touched.
- The deny-lock in `.claude/settings.json` was restored immediately after,
  and remains in force. `tests/test_truth_wall.py` stayed locked throughout.
- Attribution note for the paper: these three tolerance values were
  derived and empirically validated by Claude Code, then reviewed and
  approved by the students — unlike the rest of golden_numbers.py, which
  is student-hand-derived from the plan and verified 2026-07-14.

### Environment bug found and fixed, 2026-07-14

- Symptom: `from tests.golden_numbers import ...` failed even though the
  file exists. Cause: a stray top-level `tests` package (containing only a
  `test_e2e.py`) was left in Python 3.13's site-packages by some earlier
  pip install, and Python prefers a regular site-packages package over our
  plain `tests/` folder.
- Fix: added `tests/__init__.py`, making our folder a proper package that
  wins the name lookup. Suite green afterward (6/6).
- Follow-up (optional, low priority): identify and uninstall whichever pip
  package polluted site-packages with a bare `tests` folder.

### Option B completed, 2026-07-14

- `tests/test_geometry.py` now imports ANGLE_TOL_RAD from golden_numbers
  instead of hard-coding 1e-12 (five occurrences replaced; values
  identical, so this changes organization, not behavior). Suite 6/6 green.

### Pending at end of session 3

1. Student entries in `ai_sessions/` for sessions 1–3 (ISEF requirement).
2. Spec 2 (parallax engine): test cases drafted in conversation; awaiting
   final student "yes", then test file + implementation.
3. Delete accidental `node_modules/` folder (already gitignored).
4. Python version: CLAUDE.md pins 3.11, machine runs 3.13 — students
   decide which to standardize on.

## 2026-07-14 — Session 3 (continued): Spec 2, parallax engine

- Students gave the go-ahead via /spec. Test written FIRST
  (`tests/test_parallax.py`, three cases approved in conversation):
  (1) parsec definition — 1 au baseline at 1 pc gives exactly 1 arcsec
  within PARALLAX_REL_TOL; (2) shortcut rule shift ≈ D/d vs exact over
  d = 1e3..1e9 au within DISPLACEMENT_REL_TOL, plus a vectorization shape
  assert; (3) cross-check against Spec 1's angle_between via an explicit
  3D construction at a wide angle, within ANGLE_TOL_RAD.
- Suite confirmed RED (module missing), then implemented
  `galnav/parallax.py::parallax_angle` — one line of math:
  arctan(baseline/distance), exact for perpendicular displacement, numpy
  arrays in/out. Suite GREEN: 9/9.
- Numerical finding worth remembering: the arccos-based angle_between
  from Spec 1 has ~5e-11 rad rounding fuzz at 1-arcsec scale (fine for
  its own spec, too fuzzy for tiny-angle cross-checks). Documented in
  journal/spec-2-parallax.md; future specs needing tiny-angle precision
  should consider the arctan2(|cross|, dot) formulation — only when a
  spec card calls for it, per the one-card-at-a-time rule.
- Cross-check test therefore uses a wide angle (~5.7 deg) where both
  methods are fully precise; the tiny-angle regime is already covered by
  the six-orders-of-magnitude test against the analytic shortcut.
- Journal entry: `journal/spec-2-parallax.md` (thumb-parallax explainer,
  formula symbol by symbol, tolerances with measured headroom, what each
  test would catch). Citations: [IAU15]/[SMALL] where-used updated — no
  new outside sources this card.
- Audits, both PASS. Truth wall: parallax.py imports only numpy, no
  constants copied from truth, nav/ and truth/ still zero-import stubs;
  standing note re-confirmed that top-level shared modules
  (geometry.py, parallax.py) sit outside the AST test's scan, so manual
  audit remains the compensating control there. Code review: all rules
  pass; one student decision flagged — the test converts radians to
  arcsec with the frozen RAD_ARCSEC constant instead of a galnav/units.py
  function, because units.py has no acceptance test yet. Students choose:
  accept the constant in tests, or write a units.py spec card.
- Spec 2 committed: `03cafc4`.

## 2026-07-14 — Session 3 (continued): Gaia DR3 nav subset cached

- Downloaded the navigation star subset from the official ESA Gaia
  archive (TAP sync endpoint, stdlib urllib — no new dependencies).
  Query: all gaiadr3.gaia_source stars with parallax > 50 mas (within
  20 pc, matching the E1 grid), parallax_over_error > 10, ruwe < 1.4;
  full astrometry + errors + all ten correlation coefficients + RV + G
  magnitude. Exact reproducible ADQL recorded in `data/README.md`.
- Result: `data/gaia_dr3_nav_subset.csv`, 1,941 stars, 613 KB, committed
  for reproducibility (DR3 is a static release).
- Sanity checks passed: nearest star is Proxima Centauri at parallax
  768.07 mas (1.30 pc) — matches the published value; distance range
  1.30–19.99 pc; 554 stars lack radial velocity (the future "missing RV"
  population for experiment E6).
- Known limitation recorded: very bright neighbors (Alpha Cen A/B,
  Sirius) may be absent due to Gaia bright-star handling and the RUWE
  cut. Acceptable for simulation work.
- Gaia cache committed: `9d291b4`.

## 2026-07-14 — Session 3 (continued): Spec 3, truth simulator

- Students questioned the catalog size (1,941 vs Gaia's 1.8 billion) —
  resolved: navigation needs nearby stars only (shift = move/distance
  makes distant stars useless as position references); the 20 pc cut
  matches the E1 experiment grid; count is consistent with the known
  solar-neighborhood census. Students then authorized proceeding.
- New golden number added under the same authorized-override procedure
  as before (lock lifted, one value added, lock restored immediately):
  SKYCOORD_AGREE_MAS = 1.0, the plan's week-2 astropy-agreement gate.
- Test written FIRST (`tests/test_sky.py`, three cases approved in
  conversation): zero-noise pair angles equal analytic values to
  ANGLE_TOL_RAD; radec_to_unit agrees with astropy SkyCoord within 1 mas;
  same-seed reproducibility and different-seed variation. Suite confirmed
  RED, then implementation, then GREEN: 12/12.
- Implemented: `galnav/units.py` (radec_to_unit spherical-to-Cartesian;
  parallax_mas_to_dist_au; AU_PER_PC derived as 648000/pi, never typed as
  a decimal), `galnav/truth/sky.py` (load_catalog, star_positions_au),
  `galnav/truth/observer.py` (observed_pair_angles, vectorized over
  pairs, noise only via the rng argument). First real code behind the
  truth wall.
- Design note: the astropy cross-check compares unit vectors by
  difference-norm (chord), not by angle_between — the Spec 2 finding in
  practice (arccos shows ~3 mas of false fuzz at zero angle, which would
  spuriously fail the 1 mas gate; the chord is precise there).
- Deferred, needs a student-authored test before code exists: drawing the
  TRUE sky from each star's full Gaia covariance (catalog values +
  correlated random draw) — currently truth equals catalog exactly.
  The ten correlation columns are already in the cache for this purpose.
- Audits complete. Truth wall: PASS, no violations — nav/ still
  zero-import stubs, units.py imports only numpy, no side channels, no
  truth constants anywhere, and the Gaia CSV confirmed as genuinely
  public catalog data (both sides may read it; when the nav-side loader
  is written it must parse independently, never import truth/sky.py).
  Spec review: one violation found and FIXED before commit — sky.py was
  converting degrees to radians itself; the conversion moved to
  galnav/units.py (deg_to_rad) where the rulebook says all conversions
  live. Suite re-verified green after the fix (12/12).
- Reviewer also asked to confirm SKYCOORD_AGREE_MAS provenance: added
  under the students' explicit authorized-override instruction, recorded
  earlier in this logbook — confirmed.
- Flagged for students (mild, no action forced): the test file converts
  mas/arcsec to radians inline using the frozen RAD_ARCSEC constant;
  strictly units.py could own helpers for this, but adding untested
  helper functions violates test-first. Decide whenever a units.py spec
  card happens.
- Spec 3 committed: `5d802d5`.

## 2026-07-14 — Session 3 (continued): Spec 4, Measurement Model A + Jacobian

- New golden number JACOBIAN_REL_TOL = 1e-6 (plan's Spec 4 gate) added
  under the recorded authorized-override procedure (lock lifted, one
  block added, lock restored).
- Test written FIRST (`tests/test_measmodel.py`): predictions match
  independent construction (ANGLE_TOL_RAD); analytic Jacobian matches
  central differences over 4 decades of step (0.1/1/10/100 au) within
  JACOBIAN_REL_TOL; every pair's sensitivity bounded by the displacement
  rule 1/r_i + 1/r_j. Confirmed RED, then implemented
  `galnav/nav/measmodel.py` (first real NAV-side code):
  _unit_directions, _pair_sin_cos, predicted_pair_angles,
  pair_angle_jacobian. Chain-rule derivation reproduced in
  journal/spec-4-measmodel.md.
- TDD CATCH OF THE DAY: first run failed 2 tests. Root cause — test
  pair [8,9] is the 61 Cygni A/B binary (RA 316.75, Dec +38.76, both at
  parallax 286 mas; the star of Bessel's 1838 first-ever parallax
  measurement). Near-zero pair angle (0.0165 deg from the test vantage)
  exposed (a) arccos rounding fuzz in the REFERENCE tool exceeding the
  1e-12 gate (1.18e-12 measured) and (b) a fundamental nudge-test limit:
  close pairs carry position signal ~angle/r, so 1e-6 relative agreement
  is unreachable at h=0.1 au in float64 (1.55e-6 measured after the
  model fix). Honestly recorded as NOT scientifically novel (binaries
  and arccos conditioning are textbook) but a genuine harness catch and
  a preview of E6 binary contamination.
- Fixes: (1) CODE — model upgraded to arctan2(|cross|, dot) pair angles
  (precise at all angles; the upgrade forecast in the Spec 2 journal).
  (2) TEST, by explicit student decision (option A): binary companions
  are never paired with each other; verified [8,9] is the only
  degenerate pair among all 45 combinations (all others 20-156 deg);
  stars 8 and 9 remain in the test paired with distant partners.
- Methodological note for all future experiment scripts: the catalog is
  sorted by distance and binary companions share a distance, so ADJACENT
  CATALOG ROWS ARE LIKELY THE SAME SYSTEM. Never pair neighbors blindly.
- Final state: 15/15 green. Measured Jacobian agreement: worst 6.8e-8
  across all pairs/decades (15x headroom at h=100 au where curvature
  dominates; 1,000-10,000x elsewhere).
- Spec 1's arccos-based angle_between left untouched (its own contract
  holds; one-card rule). Flag for a future student decision: upgrade
  geometry.angle_between to the arctan2 form when a card needs it.
- Spec 4 committed: `6ff5d33`.

## 2026-07-14 — Session 3 (continued): Spec 5, Gauss-Newton solver

- Golden values measured BEFORE freezing (prototype in scratchpad, four
  1000-au starting offsets along axes and diagonal): worst recovery
  error 3.4e-10 au, convergence in 4 rounds from every direction. Frozen
  under the recorded authorized-override procedure:
  SOLVER_RECOVERY_TOL_AU = 1e-8 (29x above measured floor),
  SOLVER_STEP_TOL_AU = 1e-9 (caller-supplied stop threshold; the solver
  itself contains zero magic numbers), SOLVER_MAX_ITERS = 10 (plan gate;
  2.5x headroom over measured 4).
- Test written FIRST (`tests/test_estimator.py`): machine-precision
  noiseless recovery from all four start directions; convergence under
  10 rounds; honest iteration counter (starting exactly at the answer
  reports <= 1 round). Confirmed RED, then implemented
  `galnav/nav/estimator.py::solve_position` — explicit normal equations
  (JᵀJ)δ = Jᵀr matching derivation D3 (chosen over black-box lstsq so
  the code IS the equation the students must reproduce in interviews).
  GREEN: 18/18.
- Design decisions recorded: no damping (plain GN suffices from good
  starts — measured; Levenberg-Marquardt is a student decision when the
  bad-start/E2 card arrives); no weights yet (W enters with Spec 7's
  catalog covariance test); no attitude/velocity (pair angles are
  attitude-free by construction).
- First end-to-end navigation: truth generates measurements → navigator
  recovers position to 3.4e-10 au. The truth wall held: the solver saw
  only measured angles, catalog arrays, pair indices, and a guess.
- Audits: truth-wall-auditor and spec-reviewer launched; verdicts
  recorded before commit.
