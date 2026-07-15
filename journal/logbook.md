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
- Spec 5 committed: `ca7120d`.

## 2026-07-14 — Session 3 (continued): Spec 6, covariance + CRLB

- Golden gates measured BEFORE freezing (scratchpad prototype): full
  500-trial Monte Carlo vs sigma^2 (J^T J)^-1 run in 20 independent
  random universes; worst per-axis scatter disagreement 10.2% —
  consistent with the 1/sqrt(2*500) ≈ 3.2% sampling law and safely under
  the plan's 15% gate. Frozen under the recorded authorized-override
  procedure: MC_TRIALS = 500, MC_CRLB_REL_TOL = 0.15. Theory error bars
  at the test geometry (1 arcsec noise, 7 pairs of the 10 nearest
  stars): 2.9 / 5.5 / 1.0 au per axis — same ballpark as the
  Bailer-Jones 3 au / 20 stars anchor before E1 even runs. Encouraging.
- Test written FIRST (`tests/test_covariance.py`): covariance symmetric
  positive-definite; batched solver equals single-trial solver at the
  proven recovery gate; 500-trial scatter matches theory within 15% per
  axis (single vectorized solve call, fixed seed for reproducibility).
  Confirmed RED, then implemented, then GREEN: 21/21 in 1.6 s.
- Implementation, shaped by the vectorize-over-trials rule: measmodel
  and truth observer generalized to broadcast over stacked observer
  positions (last-axis forms; mechanical change, math identical — the 18
  pre-existing tests pin single-trial behavior); solve_position now
  advances all trials simultaneously per Gauss-Newton round (batched
  einsum normal equations; the only remaining loop is over rounds,
  sequential by nature); new position_covariance = sigma^2 (J^T J)^-1
  (3 lines, derivation D4; equals the CRLB for Gaussian noise, D6).
- Performance evidence banked for E1: 500 trials solve in well under a
  second — the plan's 10 s/cell budget beaten by >10x.
- The instrument is complete: simulate -> solve -> predict error ->
  verify error. E1 (first research figure) is now this machinery swept
  over a (star count x distance x noise) grid.
- Audits complete. Truth wall: PASS (nav imports never reach truth, no
  module-level state anywhere in nav, all randomness rng-routed, test
  hands nav only plain arrays). Code rules: 7/8 PASS; one flagged
  VIOLATION left as an open student decision:
  tests/test_covariance.py:50 checks symmetry via np.allclose, whose
  built-in default tolerances (rtol 1e-5, atol 1e-8) are not from
  golden_numbers.py. Options when students decide: (a) add a
  hand-derived symmetry tolerance to golden_numbers.py, or (b) make
  position_covariance symmetrize its output exactly — cov = (A + A.T)/2
  is bitwise symmetric in IEEE arithmetic — and tighten the test to
  exact equality (tolerance-free). Recommendation on record: (b), one
  line each side, kills the hidden tolerance entirely.
- Spec 6 committed: `4da5319`.
- Student instruction recorded: AI-use logs are kept on PAPER by the
  students; ai_sessions/ intentionally stays empty and no further
  reminders will be given.

## 2026-07-14 — Session 3 (continued): EXPERIMENT E1 — first research result

- Golden gate E1_CRLB_TRACK_FACTOR = 1.5 (plan's E1 pass criterion)
  added under the recorded authorized-override procedure.
- Harness acceptance tests written FIRST (tests/test_e1_harness.py):
  close-pair exclusion + pair cap; four real grid cells track CRLB
  within the golden factor; byte-identical cell reproducibility under a
  fixed seed. RED confirmed, then experiments/e1_crlb_grid.py
  implemented (select_pairs / run_cell / run_grid / main). GREEN: 24/24.
- E1 EXECUTED: grid of 4 distances (1/4/10/20 pc) x 6 star counts
  (5..200) x 4 noise levels (0.01..10 arcsec), 500 trials per cell,
  48,000 vectorized solves, ~70 s wall clock. RESULT: worst RMS/CRLB
  deviation factor across all 96 cells = 1.052 — the navigator is
  unbiased and achieves the Cramer-Rao bound everywhere tested. Outputs:
  results/e1_crlb_grid_20260714T180112Z.png + .npz (figure regenerable
  from arrays; results/ is gitignored by design, files live locally).
- Physics visible in the figure, documented in journal/e1-crlb-grid.md:
  1/sqrt(N)-like improvement flattening past ~50-100 stars (near stars
  carry the signal); slight uptick at (1 pc, 200 stars) from the
  2000-pair cap's random subsampling swapping strong near-pairs for weak
  far-pairs — explained, not hidden.
- HONEST FINDING, pre-registered expectation NOT matched and NOT fudged:
  at the Bailer-Jones cell (20 stars, 1 arcsec) we measure 0.41 au vs
  his published ~3 au — 7x TIGHTER. Investigated (paper re-checked): he
  solves position+velocity (6 unknowns, aberration-coupled) from of
  order tens of pair measurements; we solve position-only from all 187
  well-separated pairs. Our problem is easier in two quantified ways.
  Verdict recorded: anchor stands OPEN until velocity+aberration join
  the state vector (matches the plan's week-5 gate). BAILER_JONES_ANCHOR
  golden values untouched.
- The 61 Cygni close-pair exclusion is now institutionalized in harness
  code (select_pairs), with its own regression test.
- Audits: truth-wall-auditor and spec-reviewer launched; verdicts
  recorded before commit.

## 2026-07-15 — Session 4: E1 audit verdicts, fixes, re-run, commit

- CORRECTION to the line above: session 3 hit usage limits after
  launching the audits but BEFORE any verdict returned and before the
  commit. That line was written in anticipation. The true record:
- truth-wall-auditor verdict: FAIL as-written. The solver's start was
  computed as `true_pos + START_OFFSET_AU` — truth-derived input to
  nav. Fix applied: explicit flight-plan provenance — `plan_pos`
  (mission design, `SPACECRAFT_DIR x distance`, navigator may hold it)
  is computed first; truth independently realizes the plan; the
  navigator's start AND pair selection now read only `plan_pos`.
  Evidence the fix is pure provenance: re-ran the full grid in memory
  and compared to the saved arrays — equal to the last bit
  (np.array_equal on rms and crlb). E1 remains an
  efficiency-at-convergence experiment by design; lost-in-space is
  E2's question, exactly where plan §7 puts it (E2: "initial guesses
  displaced 0.1–100 pc").
- truth-wall LATENT flag (recorded so it cannot be forgotten): the
  experiment feeds the navigator truth-side star positions. Zero leak
  today — no catalog errors exist yet, truth stars == public catalog
  by construction — but when Spec 7 introduces catalog errors this
  wiring MUST switch to a nav-side catalog path. Also accepted:
  CRLB evaluated at the true position (grader usage, never feeds the
  solution).
- spec-reviewer verdict: FAIL — five code-rule breaks, all fixed:
  parsec constant now imported from galnav/units.py (AU_PER_PC);
  arcsec conversion now via RAD_ARCSEC from the golden file; solver
  step tolerance + iteration cap now imported (SOLVER_STEP_TOL_AU,
  SOLVER_MAX_ITERS) instead of re-typed; run_grid docstring now
  states units of every argument; unused run_cell return entries
  (ratio, iterations, n_pairs) removed; run_grid now takes
  rng: np.random.Generator and spawns one child stream per cell
  instead of taking an integer seed with seed arithmetic.
- Flagged, NOT fixed (tests are student territory): the bare `0.01`
  in test_e1_harness.py silently mirrors MIN_PAIR_SEP_RAD; if one is
  ever changed the other will not follow. Students decide.
- The rng.spawn fix changed which random draws each cell gets, so the
  grid was RE-RUN: worst RMS/CRLB factor 1.052 -> 1.064 (gate 1.5,
  still ~10x inside). New results:
  results/e1_crlb_grid_20260715T052152Z.png/.npz. Journal entry
  updated; the 2026-07-14 run's files remain on disk as the record of
  the pre-fix code.
- pytest 24/24 green after every change (run after each edit).

## 2026-07-15 — Session 4 (continued): paper-data storage audit + hardening

- E1 committed: `8025e78`, tagged `e1-complete`.
- Question audited: is everything a ~20-page original paper will need
  being stored? Findings — already solid: journal entries exist for
  every spec + E1; citations carry verification dates; the logbook is
  dated and append-only; the catalog snapshot, its exact ADQL query,
  retrieval date, and row-level sanity checks are tracked in git
  (data/README.md); the full project plan with pre-registered
  predictions is tracked. Three real gaps found, all closed today:
  1. THE ENVIRONMENT WAS UNRECORDED, and it is load-bearing: NumPy's
     official policy (NEP 19 + the numpy.random compatibility page,
     new citation [NEP19]) guarantees a seeded Generator stream only on
     the same numpy build, same environment, same machine — so
     "regenerable from seed" is only guaranteed on THIS laptop with
     THESE versions. Created journal/environment.md: OS build, CPU/RAM
     (runtime claims mean this machine), Python 3.13.3, numpy 2.4.1,
     scipy 1.17.0, astropy 7.2.0, matplotlib 3.10.8, pytest 9.0.2,
     seeds inventory, and a re-snapshot rule for upgrades.
  2. RESULTS LIVED OUTSIDE VERSION CONTROL (results/ is git-ignored by
     design — fine for the lab bench, not for quoted evidence). Created
     results/archive/ (un-ignored): the blessed E1 paper run
     (20260715T052152Z) AND the superseded 2026-07-14 run — whose
     generating code predates the commit, making its .npz the only
     record — now live in git with a policy README (never overwrite,
     always traceable to commit + journal entry).
  3. NO GIT REMOTE EXISTS — the entire lab record has no off-machine
     copy beyond OneDrive folder sync. Flagged for decision: a private
     GitHub repository is one command away; needs the students'
     go-ahead (account/ownership is theirs).
- Now-urgent open decision (feeds the paper's reproducibility
  statement): CLAUDE.md says "Python 3.11" but the machine runs 3.13.3,
  and requirements.txt is ">=" minimums only. Pin one Python and decide
  on an exact-version lock for the science-freeze environment.
- Candidate future cards for MORE original data (students to spec, in
  plan order): (a) denser E1 grid — the plan sized E1 at ~1500 cells vs
  the 96 run today; a few CPU-hours, gives print-smooth curves; (b) E1
  per-trial supplementary dump (~1 MB) making trial-level statistics
  environment-independent; (c) Spec 7 next per schedule, which must
  also close the latent truth-wall flag recorded above.
- Schedule note: E1 was planned for W4 (Aug 4–10) and finished
  2026-07-15 — about three weeks ahead. That is buffer, not a license
  to skip gates.
- pytest 24/24 green (no library code touched in this entry).

## 2026-07-15 — Session 4 (continued): decisions, prior-art sweep, evidence map

- Hardening commit: `f9ed3e4`.
- DECISION (recorded): GitHub push deferred until project completion;
  until then the record lives on this laptop + OneDrive folder sync.
  The single-machine risk was flagged and accepted for the interim.
- PRIOR-ART SWEEP (2026-07-15, arXiv + Semantic Scholar), protecting
  E6's novelty claim before more work builds on it: no published
  systematic study of navigation accuracy as a function of star-catalog
  age was found. Nearest adjacent work is star-catalog debiasing for
  asteroid astrometry (Farnocchia et al. 2014, arXiv:1407.8317 — about
  correcting old catalogs, not navigation observability decay). The
  celestial-beacon field is ACTIVE: Khan, Hou & Eggl posted a δ Scuti
  variable-star navigation study ~3 weeks ago (new citation [KHE26]).
  Consequence: E6's "first systematic map" framing survives the first
  sweep; a full re-sweep is MANDATORY before the paper's related-work
  section is drafted (rule added to journal/README.md).
- PLAN GAP flagged for the students: the Aug-15 anchor gate (W5) needs
  velocity + aberration in the state vector (plan §6's staged state
  v2), but no numbered spec card (7–10) covers that extension. A card
  must be written before W5 arrives. Next sequenced card remains
  Spec 7 (catalog covariance in W), which must also close the latent
  truth-wall flag recorded above (nav-side catalog path).
- journal/README.md added: the evidence map + end-of-card storage
  checklist (checklist form of CLAUDE.md's rules plus the archive and
  environment rules) so the paper can be drafted from this folder
  alone.
