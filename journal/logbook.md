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

### Pending at end of session 3

1. Student paste into `tests/golden_numbers.py`: the three test
   tolerances (Claude Code is deny-locked from that file by design).
2. Student paste into `CLAUDE.md`: THE JOURNAL RULE section.
3. Student entries in `ai_sessions/` for sessions 1–3 (ISEF requirement).
4. Spec 2 (parallax engine): test cases drafted and approved in
   conversation; awaiting tolerance paste, then test file + implementation.
5. Delete accidental `node_modules/` folder (already gitignored).
