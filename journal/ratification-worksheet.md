# GalNav Ratification Worksheet — consolidated open decisions

**What this is.** This worksheet was AI-drafted as a decision aid on 2026-07-15.
It gathers, in one place, every open student-ratification item that had
accumulated across the logbook so you can run a single ratification sitting
instead of hunting through `journal/logbook.md`.

**Read this before you start:**

- Every "AI-recommended ruling" below is a **recommendation only** — a starting
  point for your discussion, never a decision. The decision is yours, written on
  the STUDENT RULING line.
- **Nothing in this worksheet changes any code, any test, or any golden number.**
  It is a reading aid. Acting on a ruling (editing a test, adding a golden value,
  writing a spec card) is separate work you authorize afterward.
- `journal/logbook.md` remains the **authoritative record**. Where this worksheet
  and the logbook ever disagree, the logbook wins; this file is a convenience
  index into it.
- The letters (a)–(t) are the labels the logbook already gave these items, kept
  so you can trace each one back. They are **grouped by decision type, not in
  alphabetical order** — the map below shows where each letter landed. Item (q)
  is included as CLOSED so no letter appears to be missing.

**How to run the sitting.** Go section by section. For each item: read *What it
is* aloud, look at *Evidence*, discuss, then write your ruling and initials.
Section 1 items should go fast. Section 2 items are genuine judgment calls.
Section 3 items each become a future spec/test card if you approve them.

**Letter map.**

| Section | Items |
|---|---|
| 1 — Quick rulings (ratify as recorded) | (a) (c) (j) (o) (n) (h) (t) (q, closed) |
| 2 — Real decisions (genuine judgment) | (b) (e) (f) (k) (l) (m) (r) (s) (g) + two legacy test items + (i) pointer |
| 3 — Would spawn a new spec/test card | E1 catalog swap, (d), (p), replot script, spec-7 direction |

Total open items: **25** (twenty lettered a–t including the closed (q); five
non-lettered: two legacy test items and three new-card items).

---

## Section 1 — Quick rulings (the record already shows the answer)

### (a) — Ratify the Spec 7 card (read aloud, re-derive the floor, confirm the tests)
- **What it is:** Spec 7 (the catalog covariance card) was AI-drafted on your
  explicit "you're in charge" instruction, so the standing rule that students
  write the tests was set aside for that one card. Before the card counts as
  yours, read `journal/spec-7-catalog-covariance.md` aloud, re-derive the
  per-star floor formula by hand, and confirm the four acceptance tests test
  what you mean.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, checklist item (a);
  `journal/spec-7-catalog-covariance.md`.
- **Evidence:** five independent designs (three isolated agents + a judge + the
  session's own hand derivation) converged on the same floor formula, the same
  dense-covariance requirement, and the same test set; the physics check rebuilt
  R from finite differences and reproduced `position_covariance` to 1.6e-9, and a
  +1σ real-catalog distance perturbation shifted a full re-solve exactly as the
  linear prediction says (5e-5 relative).
- **AI-recommended ruling:** ratify after you have actually done the read-aloud
  and hand re-derivation — the derivation is textbook and multiply cross-checked,
  so this is a real ownership check, not a rubber stamp.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (c) — Ratify authorized overrides #2 and #3 (the added golden 0.10 and the comment fixes)
- **What it is:** Under the standing authorized-override procedure, the Spec 7
  card added exactly one golden value, `CATALOG_FLOOR_REL_TOL = 0.10`, and the
  28-agent science audit corrected several golden-file comments and docstrings.
  Confirm you accept the one new number and the wording fixes.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (c) and the
  "FIXES APPLIED" list (items 1–10); `tests/golden_numbers.py`.
- **Evidence:** 0.10 is the plan's own Spec 7 number; measured code-vs-hand-formula
  deviation is 1.25e-3 (80x inside the gate) while wrong physics misses by 20x.
  Every value in the frozen golden file was AST-verified unchanged through the
  edits — only the one pre-authorized addition — and all nine confirmed audit
  findings were documentation/rationale errors, no computed result or committed
  formula was wrong.
- **AI-recommended ruling:** ratify — the value is the plan's, the margin is 80x,
  and the AST proof shows only comments changed, not values.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (j) — Ratify the velocity + aberration (anchor) card
- **What it is:** Like Spec 7, the velocity+aberration card was AI-drafted on your
  standing instruction. To own it, read `journal/spec-velocity-aberration.md`
  aloud and re-derive both the aberration map and why a single snapshot of pair
  angles reveals the spacecraft's velocity.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (j);
  `journal/spec-velocity-aberration.md`.
- **Evidence:** the card reproduces the Bailer-Jones anchor — median 3.019 au /
  2.028 km/s vs his published ~3 au / ~2 km/s, and our 16th–84th band 1.32–6.23 au
  vs his 1.3–5.8 au (the distributions match, not just the medians). A seven-agent
  verification fleet plus both project audits passed; aberration matches a 50-digit
  SR reference to 1 ulp; measured velocity sensitivity 0.38 arcsec per km/s.
- **AI-recommended ruling:** ratify after the read-aloud — this is the project's
  hardest external check and it passes apples-to-apples against the published
  protocol.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (o) — Ratify the damping design (step-halving + light-cone guard) that overrode the panel
- **What it is:** The design panel ruled "no damping — measured unnecessary." A
  200-seed stress test then falsified that: rare close-and-fast trials sent the
  raw Gauss-Newton velocity step past the speed of light, producing NaN. The fix
  — per-trial step halving plus a light-cone guard — is the one place this card
  overrode its own panel, on measured evidence, so it needs your explicit sign-off.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (o) and
  "THE BUG THE FLEET CAUGHT"; `journal/spec-velocity-aberration.md`.
- **Evidence:** 2 of 200 seeds produced NaN medians (~1 in 10^4 trials, e.g.
  0.18 ly at 0.496c); after the fix both failing seeds converge (pinned worst
  trial: 6 rounds to 1.85 au / 1.95 km/s), the committed-seed anchor medians are
  unchanged to all displayed digits, and the failing inputs are frozen as
  `test_solver_survives_superluminal_overshoot`.
- **AI-recommended ruling:** ratify — measurement overruled the panel, the fix is
  a minimal domain guard (like the arccos clip), and it left every committed
  number identical. This pairs with (r), the open question of whether the
  position-only solver should get the same damping.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (n) — Acknowledge the SOLVER_MAX_ITERS zero-headroom note
- **What it is:** `SOLVER_MAX_ITERS = 10` has 2.5x headroom for the position-only
  solver (it converges in 4), but the 6-state anchor batch meets the dual step
  tolerance at exactly round 10 at the committed seed — zero headroom there. This
  was recorded rather than relaxed. Acknowledge you are comfortable with the note
  standing.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (n);
  `tests/golden_numbers.py` `SOLVER_MAX_ITERS` comment.
- **Evidence:** raising the cap to 30 changes nothing — byte-identical medians —
  so round 10 is genuine convergence at the rounding floor, not cap truncation;
  the anchor still passes with 5–12σ margins on the medians it actually gates.
- **AI-recommended ruling:** acknowledge and leave at 10 — raising the cap provably
  changes no result, and the note honestly documents the tight spot rather than
  hiding it.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (h) — Add the secondary-use notes to two golden-file comments (nicety)
- **What it is:** The spec-reviewer noted a cosmetic improvement: the golden
  comments for `CATALOG_FLOOR_REL_TOL` and `SOLVER_RECOVERY_TOL_AU` could mention
  their secondary uses (the correlation gate reuses the floor tolerance; the
  vanishing-floor test reuses the recovery tolerance).
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (h).
- **Evidence:** `CATALOG_FLOOR_REL_TOL` is reused for the test-3 correlation check
  (measured deviation from 1 is ~1e-15); `SOLVER_RECOVERY_TOL_AU` gates the
  dead-ahead/at-home vanishing floor (3.7e-13 / 5.7e-11 au).
- **AI-recommended ruling:** do it the next time you open the golden file under an
  authorized override — comment-only, no value changes; low value, low risk,
  purely for the reader.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (t) — Reword the results/archive README provenance line
- **What it is:** The `results/archive` README can be misread about which commit
  produced versus archived the blessed E1 run. The suggestion is to word it
  "produced by 8025e78 / archived in f9ed3e4" to preempt the misread.
- **Where recorded:** logbook 2026-07-15 triple-verification entry, item (t).
- **Evidence:** commit `8025e78` (tagged `e1-complete`) generated the blessed E1
  run; `f9ed3e4` is the hardening commit that added the archive; both resolve and
  the archive reproduces byte-identically.
- **AI-recommended ruling:** do it — a one-line wording fix to a README (not code,
  test, or golden) that removes an ambiguity in the paper's evidence trail.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### ~~(q) — E1 CRLB ratio-2.006 "threading flake"~~ — CLOSED
- **What it is:** ~~One skeptic-sweep investigator saw the E1 test fail at
  RMS/CRLB ratio 2.005857594980243 on early runs, then pass ~43 times, and guessed
  a BLAS/threadpool heisenbug. Item (q) asked for a clean-checkout, fixed-thread
  re-run to settle it.~~ **CLOSED by the Session 5 addendum** — listed here only so
  the a–t lettering has no gap.
- **Where recorded:** logbook 2026-07-15 Session 5 skeptic-sweep entry, item (q);
  closed in the 2026-07-15 Session 5 **addendum**.
- **Evidence:** the exact 4-cell computation ran 40x at 1 thread and 40x at 16
  threads with byte-identical ratios (same SHA-256 `bb404f03358759b9` in both),
  worst true ratio 1.045 vs the 1.5 gate; 250/250 clean reruns passed; the failing
  2.006 is a clean 2x of the true D=1pc/N=10 ratio — i.e. the sweep's own
  doubled-noise mutant, not a flake.
- **AI-recommended ruling:** none needed — already closed. The BLAS-threading
  mechanism is ruled out on this machine (honest caveat: not proven absent on
  other machines or BLAS builds).
- **STUDENT RULING:** _(closed — no ruling required)_
- **Date/initials:** ____________

---

## Section 2 — Real decisions (genuine judgment or taste)

### (b) — The Spec 7 split: covariance weighted, solver left unweighted, revisit at E6
- **What it is:** Spec 7 puts the catalog error into the predicted covariance
  (`Cov = (JᵀR⁻¹J)⁻¹`) but deliberately leaves `solve_position` unweighted. The
  reasoning: the floor exists regardless of solver weights, the Spec 7 gate never
  runs the solve, and the weighted covariance IS the observability limit the
  experiments need. Ratify (or overturn) that split and its revisit trigger.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (b);
  `journal/spec-7-catalog-covariance.md`, "Does NOT" section.
- **Evidence:** the recorded revisit trigger is E6 — if E6's Monte-Carlo-vs-
  prediction tracking breaks the 1.5x factor, the solver gets weights; the journal
  warns that an unweighted solver's scatter then follows the "sandwich" formula,
  not this CRLB (a recorded trap so nobody misreads it).
- **AI-recommended ruling:** ratify the split with the E6 trigger — it is the
  minimum code that answers the observability question, and the trigger is concrete
  and measurable; revisit only if E6 data forces it.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (e) — One canonical angle recipe project-wide? (arccos vs arctan2)
- **What it is:** The measurement model and geometry moved to the numerically
  better `arctan2(|cross|, dot)` pair-angle form, but `truth/observer.py` still
  uses `arccos`. Decide whether to adopt one canonical angle recipe everywhere.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (e); ties to the
  Spec 2/Spec 4 arccos-vs-arctan2 findings and to item (d).
- **Evidence:** `arctan2` is far better at tiny angles (true error at the
  61 Cygni pair 3.34e-17 rad vs arccos 1.179e-12 rad, 4–5 orders better); but
  arccos on the truth side is not currently wrong for any gate — its only exposed
  fragility is the 61 Cygni test-side pair (item (d)).
- **AI-recommended ruling:** keep the status quo for now and treat this as bundled
  with (d) — a project-wide recipe swap is a bigger change than the 61 Cygni fix
  needs. If you fix (d) by switching the reference recipe to `arctan2`, revisit
  whether to unify `truth/observer.py` at the same time. (Genuine taste: one
  consistent recipe vs not touching working truth-side code.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (f) — test_sky.py converts mas inline instead of through a units.py helper (the open units.py decision)
- **What it is:** Several tests convert mas/arcsec to radians inline using the
  frozen `RAD_ARCSEC` constant rather than a `galnav/units.py` helper, because
  `units.py` has no acceptance test for such a helper and test-first forbids
  adding untested code. The standing question is whether to write a `units.py`
  spec card that gives it the mas/arcsec helpers.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (f); re-confirmed
  Session 5 finding 6; first raised in the Spec 2 / Spec 3 entries.
- **Evidence:** the inline conversions are numerically correct and sit at genuine
  I/O edges; the deviation is architectural (the "one module owns all conversions"
  rule) not an error; `e1_crlb_grid.py` similarly divides by `RAD_ARCSEC` inline.
- **AI-recommended ruling:** defer to a small `units.py` spec card rather than
  change anything now — writing helpers without a test would break test-first. If
  you want the architecture clean, spec the card; otherwise leave the documented
  I/O-edge deviation. (Recommend status quo until a card is spec'd.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (k) — The anchor gate definition: plan's "within 30%" vs the frozen factor 2.0
- **What it is:** The plan (§7) says the Bailer-Jones anchor passes "within 30%,"
  but the frozen `BAILER_JONES_ANCHOR` uses `tol_factor = 2.0` (two-sided, a
  4x-wide window). These are different gates and you need to rule which governs.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (k);
  Session 5 finding 5; `tests/golden_numbers.py` `BAILER_JONES_ANCHOR` comment.
- **Evidence:** today's median 3.019 au vs the 3.0 au golden is 0.6% off — passes
  BOTH readings; the 2.0 factor is justified by the 100-run median's own ~10%
  sampling fuzz (a 200-seed ensemble measured 2.87 ± 0.27 au); the wide window is
  "fine because the physics is pinned elsewhere" by the FD/MC/SR-oracle tests, but
  weak standing alone.
- **AI-recommended ruling:** keep factor 2.0 as the frozen gate but record in the
  golden comment why it is looser than the plan's 30% (median sampling fuzz) — the
  result passes both, and 2.0 correctly reflects the estimator's run-to-run
  scatter; tightening to 30% risks a false fail on a correct solve. (Genuine
  taste; recommend documenting rather than tightening.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (l) — truth's _aberrate uses the v-and-c form, not kms_to_beta (consistency vs independence)
- **What it is:** The truth-side aberration works directly in v and c (Klioner
  arrangement) while the nav side uses the k-form via `kms_to_beta`. They are
  deliberately independent implementations, cross-checked by inverting one through
  the other. Your call is whether implementation independence (a stronger
  cross-check) is worth having two code paths.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (l);
  `journal/spec-velocity-aberration.md`, aberration-map section.
- **Evidence:** the two independent implementations are what make the zero-noise
  recovery test meaningful — if they ever disagree, that test fails; a single
  shared implementation on both sides would let a Galilean bug cancel itself
  (measured: a both-sides Galilean version passes every internal test, even the
  anchor, and is caught only by the external SR oracle).
- **AI-recommended ruling:** keep them independent (status quo) — the whole reason
  a Galilean bug is catchable is that truth and nav do NOT share the aberration
  code; independence buys a real cross-check and the consistency cost is two
  well-documented functions. (Genuine taste: independence vs one-recipe
  consistency; recommend independence.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (m) — AU_PER_LY's home: units.py (chosen) vs the golden file (the alternative)
- **What it is:** The light-year constant `AU_PER_LY` currently lives in
  `galnav/units.py`, put there to satisfy the "constants live in units.py, not
  tests" rule. The alternative home is `tests/golden_numbers.py`. Your call on
  where it belongs.
- **Where recorded:** logbook 2026-07-15 velocity+aberration entry, item (m);
  spec-reviewer FAIL-then-fixed note in the same entry.
- **Evidence:** the spec review flagged the constant living in the test file as a
  rule-4 violation and it was moved to `units.py` the way the rule demands;
  `AU_PER_LY` is a defined physical constant (like `AU_KM`, `C_KM_S`), not a test
  tolerance.
- **AI-recommended ruling:** keep it in `units.py` (status quo) — it is a
  unit/frame constant, which is exactly what `units.py` owns, and
  `golden_numbers.py` is for hand-derived test tolerances and anchors, not general
  constants. (Genuine taste; recommend units.py.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (r) — Should solve_position adopt the solve_state-style damping?
- **What it is:** The 6-state solver got step-halving + a light-cone guard after
  the anchor NaN bug, but the position-only `solve_position` is still plain
  undamped Gauss-Newton with no divergence guard. Decide whether to give it the
  same damping for robustness at close, poorly conditioned geometries.
- **Where recorded:** logbook 2026-07-15 Session 5 skeptic-sweep entry, finding 9
  and item (r).
- **Evidence:** one non-reproduced ~30x RMS blow-up in a single E1 regeneration
  was traced to environmental contamination (13/13 later controlled runs
  byte-identical to the blessed arrays), NOT a code defect; but undamped GN is a
  latent robustness risk at D = 1 pc with few stars; `solve_state`'s damping is
  proven to fix the analogous velocity overshoot.
- **AI-recommended ruling:** defer unless a real (non-contamination) divergence is
  observed — E1 passes 96/96 cells with the undamped solver and no reproduced
  blow-up exists, so adding damping now is unmotivated code; revisit at E2
  (lost-in-space starts) or E6 (close geometries) where bad conditioning is
  expected. (Recommend status quo; this is a robustness-vs-simplicity call.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (s) — Pin the reproducibility environment (Python 3.13.3 + numpy 2.4.1)
- **What it is:** Every blessed number in the project is a Python 3.13.3 /
  numpy 2.4.1 number, and NEP-19 byte-identity depends on the same numpy build.
  But the rulebook still says "Python 3.11." Reconcile the pin — ideally with a
  lockfile — so the paper's reproducibility statement is honest. (This subsumes
  the older 3.11-vs-3.13 open item.)
- **Where recorded:** logbook 2026-07-15 triple-verification entry, item (s);
  first flagged in the 2026-07-14 environment entry; `journal/environment.md`.
- **Evidence:** `journal/environment.md` records the full stack (Python 3.13.3,
  numpy 2.4.1, scipy 1.17.0, astropy 7.2.0, matplotlib 3.10.8, pytest 9.0.2); the
  anchor and E1 headline reproduce byte-identically on this stack; the machine's
  only complete scientific stack is 3.13, so all blessed numbers describe that box.
- **AI-recommended ruling:** pin the science-freeze environment to the measured
  3.13.3 / numpy 2.4.1 stack and update the rulebook to match (retire the 3.11
  line), ideally with an exact-version lockfile — the record already IS 3.13.3, so
  aligning the pin to reality is lower-risk than re-blessing everything on 3.11.
  (Real decision, but the evidence points one way.)
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (g) — Re-derive ABERRATION_MAX with the gamma form at the E7 card
- **What it is:** `ABERRATION_MAX_DEG_AT_0P1C = 5.74` is the Galilean (v ≪ c)
  maximum deflection; the exact special-relativistic maximum at 0.1c is 5.7464 deg
  (about 26 arcsec more). When the E7 card arrives, re-derive this with the
  Lorentz-factor form.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (g);
  `tests/golden_numbers.py` `ABERRATION_MAX` comment; `citations.md`
  [SR-ABER]/[Lauer25].
- **Evidence:** [Lauer25] Eq. 1 is explicitly the non-relativistic form; the exact
  SR oracle `SR_ABER_PHI_RAD` is already in the golden file and gives 5.7464 deg;
  at 0.1c the gamma-less form errs ~26 arcsec at the maximum (and ~103 arcsec at
  90° in the anchor regime).
- **AI-recommended ruling:** carry this forward to the E7 card (do not touch the
  value now) — E7 is the card that needs the relativistic maximum, and the oracle
  to re-derive it against already exists; this is a scheduled to-do, not a present
  decision.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (legacy-1) — The bare 0.01 in test_e1_harness.py silently mirrors MIN_PAIR_SEP_RAD
- **What it is:** The E1 harness test hard-codes `0.01` for the close-pair
  separation, which silently mirrors the harness's `MIN_PAIR_SEP_RAD`. If one is
  ever changed the other will not follow. Tests are your territory, so the fix is
  your call.
- **Where recorded:** logbook 2026-07-15 Session 4 E1-audit entry ("Flagged, NOT
  fixed"); `tests/test_e1_harness.py`.
- **Evidence:** the spec-reviewer flagged it during the E1 review; it is a
  maintenance hazard, not a current error — the two values agree today.
- **AI-recommended ruling:** replace the bare `0.01` with a reference to the same
  single source of truth the harness uses for the close-pair separation
  (`MIN_PAIR_SEP_RAD`), the same move you already approved for `ANGLE_TOL_RAD`
  under Option B — a one-line, behavior-preserving change that removes the drift
  hazard. Confirm first where that constant is defined so the test imports the
  authoritative one.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (legacy-2) — np.allclose symmetry tolerance in test_covariance.py
- **What it is:** `test_covariance.py` checks covariance symmetry with
  `np.allclose`, whose built-in default tolerances (rtol 1e-5, atol 1e-8) are not
  from `golden_numbers.py` — a hidden tolerance the rulebook says should not
  exist. Recorded options: (a) add a hand-derived symmetry tolerance to the golden
  file, or (b) make `position_covariance` symmetrize exactly
  (`cov = (A + Aᵀ)/2`, bitwise symmetric in IEEE) and tighten the test to exact
  equality.
- **Where recorded:** logbook 2026-07-14 Spec 6 entry (the flagged violation and
  recommendation); re-confirmed Session 5 finding 5; also bundled into item (i).
- **Evidence:** the on-record recommendation is (b) — one line each side kills the
  hidden tolerance entirely; Session 5 finding 5 notes the SPD check "cannot fail
  for any invertible Jacobian" since `σ²(JᵀJ)⁻¹` is symmetric-PSD by construction,
  so the gate is weak standing alone regardless.
- **AI-recommended ruling:** option (b) — symmetrize `position_covariance` exactly
  and assert exact equality, removing the hidden `np.allclose` tolerance. It is the
  on-record recommendation and needs a test change (yours) plus a one-line code
  change; since the SPD test is weak anyway, this at least makes the symmetry
  claim tolerance-free.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (i) — POINTER: the "still open from before" bundle
- **What it is:** Item (i) in the Spec 7 checklist was a reminder bundle, not a
  single decision: "velocity+aberration card before the Aug-15 gate; Python
  3.11-vs-3.13 pin; np.allclose symmetry tolerance; E1-harness nav-loader swap at
  E6." Each part is now tracked as its own worksheet item.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (i).
- **Evidence:** the velocity+aberration card is DONE (anchor reproduced — see items
  (j)–(o)); the Python pin is item (s); the np.allclose tolerance is legacy item
  (legacy-2); the E1 nav-loader swap is the "E1 catalog swap" item in Section 3.
- **AI-recommended ruling:** mark (i) resolved-by-redistribution — rule its four
  parts on their own lines; this entry stands only so the lettering is complete.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Section 3 — Items that would spawn a new spec/test card

*(Ordered by stakes: the E1 catalog swap first because it protects the headline
figure, then the smaller test/tooling/doc cards.)*

### E1 catalog swap — switch the E1 harness to the nav-side catalog path before E6
- **What it is:** `experiments/e1_crlb_grid.py` and `tests/test_e1_harness.py`
  currently feed the navigator truth-side star positions
  (`galnav.truth.sky.star_positions_au`). There is zero numerical leak today, but
  the moment catalog position-aging lands (E6/Spec 10), this wiring would silently
  hand the navigator the TRUE positions and make navigation look falsely perfect
  regardless of catalog error. E1 must switch to the nav-side catalog path — the
  same swap Spec 7 already made for its covariance card.
- **Where recorded:** logbook 2026-07-15 Session 4 E1-audit "truth-wall LATENT
  flag" and the Spec 7 end-of-card audit; re-confirmed Session 5 finding 1; also
  inside item (i).
- **Evidence:** `max|diff| = 0.0 au` over 1941 stars today, so no current leak;
  the AST truth-wall test cannot see it (it scans only `galnav/nav`, never
  `experiments/` or `tests/`); Spec 7 already built the nav-side loader
  (`galnav/nav/catalog.py`) this can reuse.
- **AI-recommended ruling:** schedule this as a required card before E6 lands — it
  is the highest-stakes open item because it protects the project's headline
  "accuracy vs catalog age" figure from a silent truth-wall leak, and the fix
  reuses the nav-side loader that already exists.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (d) — 61 Cygni close pair gated at 1e-12 in test_sky.py (fragile gate)
- **What it is:** `test_sky.py`'s pair (8,9) is the 61 Cygni A/B binary; the
  assertion gates it at `ANGLE_TOL_RAD = 1e-12`, but `angle_between`'s own true
  error at that pair already exceeds the gate, and the test passes today only by
  partial (~3.1x) correlated arccos-error cancellation. Recorded options: exclude
  the 8–9 pairing (Spec 4 precedent), use a per-pair tolerance, or switch the
  reference recipe to `arctan2`.
- **Where recorded:** logbook 2026-07-15 Spec 7 entry, item (d); re-confirmed
  Session 5 finding 3 and triple-verification refinement (ii);
  `tests/golden_numbers.py` `ANGLE_TOL_RAD` comment.
- **Evidence:** `angle_between`'s true error at the pair is 1.179e-12 rad vs the
  1e-12 gate; the test's asserted difference is 3.845e-13 rad (passes by
  cancellation); the `arctan2` recipe's true error at the same pair is 3.34e-17 rad
  — 4–5 orders better; only `test_sky.py` carries the fragility.
- **AI-recommended ruling:** switch the reference recipe in the test to `arctan2`
  (option 3) — it is the root fix (4–5 orders more headroom, makes the gate honest
  without excluding real data) and it lines up with the (e) question of one
  canonical angle recipe; needs a test-card since tests are yours. Excluding the
  pairing is the quicker but less principled fallback.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### (p) — Light-cone guard has zero test coverage
- **What it is:** The 6-state solver's light-cone guard
  (`galnav/nav/estimator.py`, `_inside_light_cone`) is never exercised by any
  test — neutering it to the identity leaves the whole suite green, because
  step-halving rejects the bad step before the 0.99c clamp is ever reached. A
  wrong clamp (bad scale, broadcasting bug) would slip through. The fix is a test
  that actually drives a trial velocity past c so the clamp executes.
- **Where recorded:** logbook 2026-07-15 Session 5 skeptic-sweep finding 2 and
  item (p); sharpened in triple-verification refinement (i).
- **Evidence:** with the guard neutered the suite still passes 34/34;
  instrumentation shows the maximum trial speed in the 100-run anchor batch is
  0.5004c with ZERO superluminal/NaN evaluations, so the clamp never fires under
  the current tests; the damping around it is well covered, only the clamp
  sub-component is dead with respect to the suite.
- **AI-recommended ruling:** write a small regression test that constructs a
  state/step forcing an at-or-beyond-c candidate and asserts the 0.99c re-entry —
  it closes a real coverage hole on a safety guard with one focused test; needs a
  test-card (yours).
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### replot script — a standalone load-npz → replot utility for the archive
- **What it is:** The archive rule says "figures are regenerable from the saved
  .npz arrays alone," but the only plotting code is `main()`, which recomputes the
  whole 96-cell, 48,000-solve Monte Carlo in the same pass. The archived arrays
  ARE sufficient, but a load-npz → replot script would have to be written for the
  claim to be literally true today.
- **Where recorded:** logbook 2026-07-15 Session 5 skeptic-sweep finding 8;
  triple-verification confirmed the arrays regenerate the figure.
- **Evidence:** the blessed figure was independently regenerated from its `.npz`
  alone during verification (the E1 headline factor recomputes to 1.063652 from the
  npz with no Monte-Carlo recompute), so the data is sufficient; only the
  convenience script is missing. The npz keys include `rms_au`, `crlb_au`,
  `dists_pc`, `star_counts`, `sigmas_rad`, `seed`, `n_trials`.
- **AI-recommended ruling:** write a short replot-from-npz utility (small,
  non-science tooling) so the archive claim is literally executable — low effort,
  and it makes the paper's "regenerable from arrays alone" statement demonstrable
  rather than merely true in principle. Not urgent; do it before the paper's
  methods section is finalized.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

### spec-7 direction — the Spec 7 journal's floor numbers don't state their observer direction
- **What it is:** The spec-7 journal quotes camera/catalog floors of 2.75 au /
  11.1 au at D = 1 pc, but those do not reproduce at the canonical test direction
  (re-derivation measured ~3.1 / ~13.7 au) because the floors are strongly
  observer-direction dependent and the journal does not say which direction the
  quoted pair came from. The qualitative claim (catalog ~4x camera, catalog-limited
  at 1 pc) holds at every direction, so this is documentation imprecision, not a
  physics error.
- **Where recorded:** logbook 2026-07-15 Session 5 skeptic-sweep finding 7;
  triple-verification refinement (iii); `journal/spec-7-catalog-covariance.md`.
- **Evidence:** across five observer directions the camera floor spans 2.57–3.69 au
  and the catalog floor 11.30–19.00 au (ratio 3.06x–6.13x); the
  catalog-dominates-at-1-pc claim holds at every direction; the numbers reproduce
  at ~3.1 / ~13.7 au at the canonical direction (+13% / +23% from the quoted pair).
- **AI-recommended ruling:** amend the spec-7 journal to state the observer
  direction the quoted floors were measured at (and ideally quote the
  canonical-direction 3.1 / 13.7 au pair) — a journal-only wording fix that makes
  the claim reproducible; the physics conclusion is unchanged. Do this before the
  paper cites those numbers.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (u) — E1 catalog swap (navigator reads the public catalog)

- **What:** the AI-authored change making experiments/e1_crlb_grid.py feed the
  SOLVER the public NAV catalogue instead of the truth-side star positions
  (closing the latent truth-wall flag before E6 added catalog errors).
- **Where recorded:** logbook build-night entry; commit 9e7f709.
- **Evidence:** results BITWISE UNCHANGED — 0.0 au difference across all 96 E1
  cells (truth == nav catalogue today), so the swap is provably a no-op on the
  numbers while making the navigator's dependence on the public catalogue
  explicit. Latent truth-wall flag CLOSED for new work.
- **AI-recommended ruling:** accept — a discipline fix with zero numeric effect,
  and the prerequisite that let E6/E7 add catalogue errors safely.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

## Item (v)/(vi) — Spec 10: catalog-aging propagator (+ override #6)

- **What:** the AI-authored deterministic catalog-aging propagator, implemented
  INDEPENDENTLY on both sides of the truth wall (truth twin + nav twin), that
  moves stars by proper motion + radial velocity over an age.
- **Where recorded:** logbook build-night entry; journal (spec-10);
  commit 16744a8.
- **Evidence:** the two independent implementations agree to ~1e-12; radial
  drift 6.3285 au/yr matches the 6.33 hand-derived oracle. AUTHORIZED OVERRIDE #6
  (SPEC10_DRIFT_REL_TOL = 1e-3, performed by the main session after the build
  agent correctly declined an agent-relayed authorization).
- **Sub-items to rule on:** (v) the card + independent-twin design; (vi) accept
  override #6 (SPEC10_DRIFT_REL_TOL = 1e-3) and its evidence.
- **AI-recommended ruling:** accept the card, the independent-twin construction
  (it is what keeps the propagator honest across the wall), and override #6.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

## Item (w) — E6a: truth-side sampled sky

- **What:** the AI-authored truth-side sky sampler that scatters the catalogue by
  its own error bars and supplies real radial velocities for the 554 stars whose
  RV is missing (the missing-RV term dominates the aging).
- **Where recorded:** logbook build-night entry; commit c5ae052.
- **Evidence:** the missing-RV unmodelled-motion term is ~4.4e4x the
  proper-motion-error aging term — i.e. the missing RVs, not PM errors, drive the
  decay; 5 of the 20 nearest stars lack RV.
- **AI-recommended ruling:** accept — the sampled sky is the truth-side input the
  E6 headline stands on; the missing-RV finding is a genuine physics result.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

## Item (x)/(y)/(z) — E6b: catalog-aging experiment (the headline)

- **What:** the AI-authored E6 experiment mapping navigation error over
  (catalog age x sensor precision), with the crossover locus and the epoch
  parallax floor — the project's headline figure.
- **Where recorded:** logbook build-night + E6 headline entries;
  journal/spec-e6b-aging-experiment.md; commits 4f80687 (experiment) + 60a8d4e
  (blessed archive).
- **Evidence (BLESSED grid, npz e6_catalog_aging_20260715T231348Z):** epoch
  parallax floor ~7.66 au (7.70 at 10 mas); aging 2.22x at 100 yr / 4.14x at
  200 yr; crossover rises 44.8 yr (finest sensor) -> 161.9 yr (60 arcsec); knee
  ~15.9 arcsec. AUTHORIZED OVERRIDE #7 (E6_AGING_SMOKE_MIN_FACTOR = 1.5).
- **Sub-items to rule on:** (x) the card + the student's own in-session
  extend-sigma-to-60-arcsec + annotate-the-floor ruling + override #7;
  (y) the crossover DEFINITION rms(age) = sqrt(2)*rms(0), log-age interpolated,
  cells exiting the range CENSORED (no extrapolation); (z) the nav pair-selection
  delta vs E1 (pairs selected from the aged NAV positions, required because truth
  is now per-trial).
- **AI-recommended ruling:** accept the card, override #7, the crossover
  definition, and the nav pair-selection change; the blessed grid numbers are
  authoritative (the pre-run probe numbers are superseded, per the E6 journal).
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

## Item (aa) — E5-lite / Spec 8 (comb part): pulsar lattice impossibility card

- **What:** the AI-authored E5-lite card, its module `galnav/pulsar.py`, tests
  `tests/test_e5_pulsar.py`, and experiment `experiments/e5_pulsar_lattice.py`
  (built 2026-07-16 under the build-night pattern). The result: a starlight
  fix (~1 au) is 4+ orders coarser than even the widest pulsar comb
  (~10,073 km), so pulsar-comb navigation cannot be bootstrapped from a star
  fix at interstellar range.
- **Where recorded:** logbook 2026-07-16 (E5-lite entry);
  `journal/spec-e5-pulsar-lattice.md`; citations [ATNF], [LAMBDA].
- **Evidence:** pytest 53 -> 59; comb spacings match frozen COMB_KM within
  0.51 km; coast on 467 km comb 270.25 d @1cm/s, 2.70 d @1m/s (== frozen
  270.0/2.7); 1 au / widest comb = 14,851; packing radius of (Crab, B1937+21,
  J0030+0451) = 286 km. AUTHORIZED OVERRIDE #8 (COMB_MATCH_KM = 1.0, the T2
  comb-match gate, main session) — reuses frozen COMB_KM + COAST_DAYS_* for
  everything else. (Correction 2026-07-16: this line previously read "No golden
  override", which was false — override #8 is real and logged; the E5 journal
  carried the same stale claim and is corrected too.)
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion).
  2. The DEFERRED-SOLVER fork: the general closest-vector integer-recovery
     solver needs an `fpylll`-vs-numpy-enumeration decision before it is built.
  3. The J0030+0451 sub-km flag: frozen COMB_KM 1459 km is the non-nearest
     integer to c*P = 1458.49 km (nearest 1458); 0.51 km, inside Spec 8's 1 km
     spec; recorded, not changed. Confirm you accept the frozen value.
  4. Figure label polish: the four tightly-spaced combs (467-1726 km) crowd
     their labels — a cosmetic fix before the figure is quoted/blessed.
  5. UNIT DEVIATION (rule-4 conscious sign-off, spec-reviewer should-fix #2):
     `galnav/pulsar.py` works in KILOMETRES for lengths (comb spacings,
     lattice, packing radius) and SECONDS/DAYS for time — NOT the project's
     internal au / km-s / rad. Km is the natural unit for comb navigation
     (combs are ~10^2-10^4 km; in au every number would be ~10^-6). Confirm you
     accept km/seconds/days as a documented LOCAL convention isolated to the
     pulsar module, converting to au only where it meets the starlight numbers
     (the experiment's star-fix band uses AU_KM).
  6. NICETY (spec-reviewer): test T3's exact 100x coast-ratio check uses a bare
     `atol=1e-9`. It is an exactness identity, not a physics tolerance; left
     as-is per main-session close-out. Rule whether to keep it inline or
     promote it to a golden constant.
- **AI-recommended ruling:** accept the card and the impossibility result;
  defer the full integer solver as its own card; keep the frozen J0030 value
  (inside spec) with the flag noted; accept km/s/days as the pulsar module's
  documented local unit convention; keep the atol inline; polish the figure
  labels before blessing.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (bb) — E3: real New Horizons interstellar-navigation anchor

- **What:** the AI-authored E3 card — the closed-form line-of-position solver
  `galnav/nav/triangulate.py::n_star_solve`, its tests
  `tests/test_e3_triangulation.py`, and the experiment
  `experiments/e3_new_horizons.py` (built 2026-07-16 under the build-night
  pattern). The result: OUR fully independent pipeline recovers the REAL New
  Horizons spacecraft position from optical measurements of two nearby stars
  (Proxima Cen, Wolf 359) to **0.3467 au** of the JPL Horizons ephemeris — the
  project's first real-data anchor, reproducing Lauer et al. (2025).
- **Where recorded:** logbook 2026-07-16 (E3 override-#9, design-review,
  part-1, part-2, END-OF-CARD, and blessed-run entries);
  `journal/spec-e3-triangulation.md`; `results/archive/` Contents entry;
  citations [Lauer25], [Lauer25-data], [LAMBDA]. Commits b788690 (card) /
  6e3832e (blessed archive).
- **Evidence:** pytest 63 -> 65, 0 skipped. Pipeline miss vs JPL 0.3467 au
  (~8.7x inside the 3 au gate); Gaia J2016.0 -> image-epoch propagation is
  MANDATORY (unpropagated miss ~30 au). Reproduction cross-check on Lauer's own
  inputs matches his x2 to 0.0065 au (miss vs JPL 0.3457 au). Reported ellipsoids:
  ours (2-star) 1.08/0.57/0.50 au, Lauer x60 (12-line) 0.441/0.233/0.206 au;
  Proxima-Wolf direction separation 80.6 deg. Both audits PASS (truth-wall:
  JPL enters only the score; spec-review: PASS with two fixes, applied).
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion; T1/T2 are the exact
     synthetic algorithm proof at SOLVER_RECOVERY_TOL_AU, T3 is the real-data
     gate, T6 the reproduction cross-check).
  2. AUTHORIZED OVERRIDE #9: golden `NH_NAV_TOL_AU = 3.0` — the project plan's
     own pre-registered section-7 pass gate (main session performed it; the
     build agent never edited golden_numbers.py). Confirm you accept the value
     and its evidence comment (which also pins the 0.351-au-MISS vs
     0.441-au-ELLIPSOID distinction permanently).
  3. The MISS vs ELLIPSOID distinction: Lauer's famous "0.44 au" is the largest
     1-sigma error-ellipsoid SEMI-AXIS, NOT the miss (his miss is 0.351 au;
     0.94-sigma Mahalanobis). Confirm the framing (kept distinct in journal,
     figure, golden comment, archive README).
  4. The reproduction is REPORTED, not gated at 1e-8: the extracted 8-digit
     fixtures give 0.0065 au (rounding), and our propagation differs from the
     notebook's by ~0.0035 au, so the identity is a reported cross-check while
     T1/T2 carry the exact proof. Confirm you accept reported-not-gated here.
  5. The Wolf 359 RV FILL = 19.57 km/s (Simbad, Lauer's value): our Gaia CSV
     lacks Wolf 359's radial velocity; rv_fill = 0 shifts the miss by only
     ~0.03 au. Confirm you accept the documented fill choice.
  6. ABERRATION: no per-star stellar-aberration correction is applied — the
     directions are Gaia-frame plate solutions whose bulk aberration cancels in
     the pair geometry; E7 handles the relativistic form separately. Confirm you
     accept this for the 2-star anchor.
  7. The DEFERRED x60 (v1.1): the 12-line x60 full reproduction + ellipsoid
     recompute from the 12 per-image directions (notebook cells 4-5) is flagged
     for a follow-up card; the quoted x60 ellipsoid stands in for now. Confirm
     you accept the deferral.
- **AI-recommended ruling:** accept the card and the real-data anchor result
  (0.3467 au); accept override #9 (the plan's own gate); accept the RV fill and
  the aberration simplification for the two-star anchor; keep the reproduction
  reported-not-gated (T1/T2 already prove the algorithm exactly); defer the x60
  full reproduction to a v1.1 card before the paper quotes the ellipsoid.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (cc) — E2: convergence basins + the OPTION-A failure-handling ruling

- **What:** the AI-authored E2 card — `experiments/e2_convergence_basins.py`
  and `tests/test_e2_basins.py` (built 2026-07-16 under the build-night
  pattern). The result: the navigator's convergence BASIN (how far the initial
  guess can be displaced and still converge) at 1 pc grows from a ~2 pc
  0.5-capture radius with 5 stars to ~12 pc with 100 stars.
- **Where recorded:** logbook 2026-07-16 (E2 entry);
  `journal/spec-e2-convergence-basins.md`; commits recorded in the logbook.
- **Evidence:** pytest 65 -> 73, 0 skipped. Reduced 200-trial probe (seed 42):
  0.5-capture radius 1.90 / 3.88 / 6.32 / 9.80 / 11.49 pc for N = 5 / 10 / 20 /
  50 / 100, matching the design reviewer's independent probe (2.0 pc @5,
  11.8 pc @100). Reuses SOLVER_RECOVERY_TOL_AU + SOLVER_STEP_TOL_AU +
  SOLVER_MAX_ITERS; ONE golden ADDED via authorized override #10
  (E2_ISOTROPY_M4_TOL = 0.01, main session).
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion).
  2. THE FAILURE-HANDLING RULING = OPTION A (per-trial `try/except LinAlgError`
     failure-isolation loop), AI-decided under the build authority. Confirm you
     accept A over: B (damp the solver — would re-bless E1/E6/anchor),
     C (hold), and D (batched pre-solve condition screen — REJECTED because the
     singularity first appears MID-iteration, so a pre-screen is blind to it).
     "Simplicity beats cleverness" (the project rule) drove the choice.
  3. THE NO-TRIAL-LOOPS EXCEPTION: the per-trial loop knowingly breaks the
     project's "vectorise over trials, no Python loops" rule. Confirm you accept
     it as documented FAILURE ISOLATION (the rule is for MC throughput; this
     loop runs in seconds and there is no vectorised way to isolate a
     mid-iteration singularity without re-writing the deployed solver).
  4. ZERO-NOISE basin definition: E2 studies the residual landscape, so it uses
     no measurement noise (true position is an exact fixed point). Confirm.
  5. `np.errstate` scoped around the isolated solve to silence the divide /
     invalid warnings that escaping trials legitimately raise (sin(theta) -> 0
     mid-divergence). Confirm you accept the scoped suppression.
  6. This card supplies the measured basin as EVIDENCE for item (r) (the
     undamped `solve_position`): the undamped solver already captures from
     ~2-12 pc, so a coarse interstellar prior is well inside the basin without
     damping. Rule (r) and (cc.2) together.
  7. AUTHORIZED OVERRIDE #10: golden `E2_ISOTROPY_M4_TOL = 0.01` (isotropy gate
     for the direction sampler, T5). Confirm you accept it. Note the honest
     history: the first T5 used a projection-VARIANCE check that was measured to
     PASS on the very cube bug it guards (the 2nd moment does not discriminate);
     T5 was rewritten to the 4th moment, which cleanly separates the correct
     draw (~2e-4) from the cube (~0.033), and the 0.01 gate was promoted to this
     golden. Derivation is in the golden comment + the E2 journal.
- **AI-recommended ruling:** accept the card and the basin result; accept
  option A and its documented no-trial-loops exception; accept the zero-noise
  definition and the scoped errstate; treat the measured basin as the evidence
  that resolves item (r) toward "no damping needed for a coarse prior."
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (dd) — E7: relativistic aberration at 0.1c (the relativistic armor)

- **What:** the AI-authored E7 card — `experiments/e7_relativistic_aberration.py`
  and `tests/test_e7_aberration.py` (built 2026-07-16 under the build-night
  pattern; card adversarially reviewed by main, APPROVED WITH AMENDMENTS). The
  result: at 0.1c a navigator using the classical (Galilean, Lauer Eq. 1)
  aberration mislocates the spacecraft by ~1350 au, while the exact navigator
  recovers to ~1e-9 au — the exact special-relativistic form is MANDATORY.
- **Where recorded:** logbook 2026-07-16 (E7 entry);
  `journal/spec-e7-relativistic-aberration.md`; citations [SR-ABER], [Klioner03],
  [Lauer25] Eq. 1 (all pre-existing). Commits recorded in the logbook.
- **Evidence:** pytest 73 -> 80, 0 skipped. Full run (seed 42): Part A Galilean
  max 5.7392 deg (peak 95.74) vs exact 5.7464 deg (peak 92.87), gap 26.0 arcsec;
  Part B exact recovery 1.2e-9 au / 8.0e-10 km/s; Part C per-angle model error
  median 402 arcsec, classical-navigator bias median 1356 au / 1201 km/s,
  linearized cross-check 1196 au. No golden override.
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion).
  2. E7 is an EXPERIMENT — it does NOT modify galnav/ (aberration already exact
     both sides). Confirm you accept the pure-experiment scope.
  3. The THREE distinct aberration maxima (small-angle 5.730 / Galilean 5.739 /
     exact 5.746 deg) and that the golden ABERRATION_MAX_DEG_AT_0P1C is the
     Galilean one. Confirm the framing.
  4. The PAYLOAD is the ~500 arcsec per-angle model error (median 402), NOT the
     26 arcsec max-deflection gap (a Part-A curiosity). Confirm.
  5. Part B uses the full 6-state solve_state (not position-only). Confirm.
  6. The recovery floor at 0.1c (1.2e-9 au) is ~6x under SOLVER_RECOVERY_TOL_AU,
     thinner than the golden comment's low-speed 16x margin (0.1c is a harder
     inversion). Confirm you accept the thinner-but-comfortable margin.
  7. (dd.7) THE GALILEAN PREDICTOR DESIGN: a NEW experiment-local WRONG-PHYSICS
     classical predictor (u' = normalize(u + beta)) + hand-rolled damped GN with
     a FINITE-DIFFERENCE jacobian, vectorized. Confirm you accept the
     finite-difference jacobian choice (vs analytic) and the wrong-physics
     labelling.
  8. (dd.8) THE CORRECTED d_theta PROVENANCE: the payload's ~500 arcsec is the
     per-angle exact-vs-Galilean difference in the real hub geometry, distinct
     from the 26 arcsec max-deflection gap — a first-draft conflation caught in
     review. Confirm the corrected number is the one the paper quotes.
  9. (dd.9) T4 DISCLOSED BLIND SPOT (spec-review): the payload test gates only
     median |d_pos| > 1 au, which sits ~3 orders UNDER the measured ~1350 au, so
     the test proves the bias is catastrophic but does NOT pin its magnitude —
     the ~1350 au headline is pinned only by the blessed npz. Decide whether to
     tighten the gate (e.g. "> 100 au") or leave it loose. (No new golden either
     way; a strict ">100 au" is still structural.)
  10. (dd.10) CONVERSION-PATH UNIFORMITY (nicety, not a bug): E1 converts
     arcsec via the raw RAD_ARCSEC constant while E3/E6/E7 use
     units.arcsec_to_rad. Same value; decide whether to unify E1 onto the edge
     helper for consistency.
- **AI-recommended ruling:** accept the card and the ~1350 au headline; accept
  the pure-experiment scope, the three-maxima framing, the corrected ~500 arcsec
  payload, the 6-state recovery, the thinner 0.1c recovery margin, and the
  finite-difference Galilean predictor as documented wrong-physics; keep the
  linearized bias as the disclosed cross-check.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (ee) — Maximum-correctness sweep: hardening niceties (NO numeric effect)

Surfaced by the user-authorized full-verification sweep (2026-07-16, four
independent legs + a mechanical pass; see the logbook's "final correctness
statement"). NONE of these change any computed number; they are uniformity /
documentation clean-ups for the students to accept or action.

- **(ee.1) J0030+0451 comb precision — the (aa.3) flag, now RESOLVED precisely:**
  the frozen `COMB_KM["J0030+0451"] = 1459` km is CORRECT — it is the nearest
  integer to c·P for the UNTRUNCATED ATNF period 4.8654 ms (c·P = 1458.63 →
  1459). The apparent "non-nearest" look came from the pulsar module's displayed
  truncated period 4.865 ms (c·P = 1458.49 → 1458). Documentation nit only;
  0.51 km gap, inside the 1 km gate. Confirm you accept 1459 as frozen (and,
  optionally, store the untruncated 4.8654 ms in the module to remove the
  apparent mismatch).
- **(ee.2) pair-selection source (truth-wall nicety):** E1 and E2 select star
  pairs from the TRUTH position array while E6 selects from the NAV array.
  Bitwise-identical today (truth == nav catalogue), and pair separation is a
  physical property, so this is not a leak — but E6's nav-side selection is the
  self-documenting pattern. Decide whether to standardize all experiments on
  nav-side pair selection for uniformity.
- **(ee.3) E7 build_network (truth-wall nicety):** E7 returns a single shared
  public-geometry star array rather than the explicit truth/nav two-array split
  the other experiments carry. Intentional — both the exact and the classical
  navigator use the same PUBLIC hub geometry, and truth enters only via the
  measurement generation and the score — but flagged for consistency review.
- **(ee.4) API-uniformity (mechanical pass):** E1 has no standalone
  `replot_from_npz` (its figure regenerates via a full `main()` recompute);
  E6's `replot_from_npz` returns a Figure while E2/E3/E5/E7 return a Path; and
  E1 converts arcsec via the raw `RAD_ARCSEC` while E3/E6/E7 use
  `units.arcsec_to_rad` (this last is also (dd.10)). Decide whether to unify the
  replot signature + add an E1 replot for a fully uniform archive-regeneration
  story. (The archive is already sufficient in every case — figures ARE
  regenerable; this is convenience/uniformity only.)
- **AI-recommended ruling:** accept 1459 as frozen (optionally de-truncate the
  displayed period); treat (ee.2)/(ee.3)/(ee.4) as low-priority uniformity
  clean-ups to batch before the paper's methods section is finalized — none is
  load-bearing and none affects a single quoted number.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (ff) — Spec 8b: closest-lattice-point (CVP) solver (completes Spec 8)

- **What:** the AI-authored `closest_lattice_point` in `galnav/pulsar.py`
  (Babai rounding + exact 27-point box, fully vectorized), tests
  `tests/test_spec8_cvp.py`, journal `journal/spec-8-cvp-solver.md`
  (2026-07-16, build-night pattern). Completes Spec 8: recovers the injected
  integer turn-counts whenever the prior offset is inside the packing radius
  rho = lambda_1/2.
- **Where recorded:** logbook 2026-07-16 (Spec 8b entry);
  `journal/spec-8-cvp-solver.md`; citation [Babai86] (+ the [LAMBDA] entry's
  deferred-solver note updated). Audits: truth-wall PASS, spec-review PASS.
- **Evidence:** pytest 80 -> 84, 0 skipped (RED first: 4 AttributeError
  failures before the code existed). NO golden override, NO new tolerance —
  a first for a pulsar card: integer recovery is proven by integer equality.
  T2 recovers all 8000 injected integers exactly inside rho; measured Babai
  margin 0 / exactly-1 L-inf step (orthonormal / T5b real lattice); T3
  boundary flip at 1.5·rho (lambda_1 = 571.956 km, rho = 285.978 km:
  injected residual 428.97 km loses to neighbor at 142.99 km).
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion, esp. that T2 is the
     compass §6 criterion — "recovers injected integers when prior < packing
     radius" — made exhaustive and tolerance-free).
  2. THE numpy-OVER-fpylll RULING (user ruling 2026-07-16): hand-coded numpy
     CVP because it is exact at dimension 3 and fpylll has no native-Windows
     build (conda-forge linux/macOS only) — a compiled dep would also
     endanger the byte-reproducibility story. Compass §5 sanctions the
     hand-coded path explicitly. Confirm you accept the trade study and that
     the general LLL/fpylll solver stays deferred.
  3. THE 27-BOX SUFFICIENCY ARGUMENT + caveat: the ±1 box is proven
     sufficient ONLY for the well-conditioned §12 geometries (measured Babai
     margin exactly 1 L-inf step on T5b — the box is load-bearing AND exactly
     wide enough); a near-degenerate geometry could defeat it (same caveat as
     shortest_vector_km, stated in the docstring). Confirm.
  4. SEED = 20260716 and frac choices {0.5, 0.9, 0.99, 0.999}: the fracs
     march up to the rho boundary to stress the tightest recoverable case.
     Confirm.
  5. T3 BOUNDARY DESIGN: one crafted offset at 1.5·rho along the shortest
     vector v1, where the neighboring lattice point is provably closer
     (0.25·lambda_1 < 0.75·lambda_1); asserting the solver does NOT return
     the injected integer and returns a strictly closer point — documenting
     that rho is the physical ambiguity boundary, not a solver defect.
     Confirm you accept this as the boundary proof.
- **AI-recommended ruling:** accept the card and the completed Spec 8;
  accept the numpy-over-fpylll ruling and the LLL deferral; accept the
  27-box with its well-conditioned caveat; accept the seed/frac/T3 design.
  Cleanest pulsar card so far — no golden change at all.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (gg) — The ARMOR environment: WSL2 + PINT for Spec 9 / E4

- **What:** a second, separate, fully-recorded environment (WSL2 Ubuntu
  24.04.4, /opt/galnav/venv, Python 3.12.3, pint-pulsar 1.1.4, numpy 2.4.1)
  stood up 2026-07-16 because PINT's < 1e-9 phase gate needs 80-bit long
  double, which native Windows/MSVC cannot provide. Full record with every
  version, hash, and why: `journal/environment-armor.md`;
  `requirements-armor.txt` at the repo root.
- **Where recorded:** logbook 2026-07-16 (armor environment entry);
  `journal/environment-armor.md` (the exact stack, the measured eps on both
  platforms, the ephemeris hashes, the rebuild recipe).
- **Evidence:** measured eps — Windows native 2.220446049250313e-16 (FAIL,
  MSVC long double == double) vs WSL2 float128 1.084202172485504434e-19
  (PASS; PINT `check_longdouble_precision() == True`). Spine untouched:
  requirements.txt zero-diff; spine suite still 84 passed / 0 skipped on
  native Windows. DE421/DE440 downloaded once and hash-pinned.
- **Sub-items to rule on:**
  1. THE TWO-ENVIRONMENT SPLIT itself: armor numbers (Spec 9/E4) are
     produced/reproduced only in WSL2; spine numbers only on native
     Windows; neither re-blesses the other. Accept this documented,
     one-way split (the alternative was the Sep-5 gate's sim-only
     fallback).
  2. PYTHON 3.12.3 (distro default) instead of the spine's 3.13.3 — no
     third-party PPA in a reproducibility-critical env; numpy pinned to
     the SAME 2.4.1 on both sides to minimize the delta. Confirm.
  3. requirements-armor.txt AS A SECOND REQUIREMENTS FILE (spine
     requirements.txt untouched) and pint-pulsar==1.1.4 superseding the
     compass §5 "1.1.2" pin (stale at build time). Confirm.
  4. TESTS_ARMOR/ SEPARATE TEST ROOT (created at Spec 9): armor tests run
     only inside WSL; they are deliberately NOT in tests/ because the
     spine's definition of done is zero-skip green on Windows, and this
     project does not ship skipping tests. One suite per environment,
     each fully green where it lives. Confirm.
  5. EPHEMERIS/CLOCK DETERMINISM POLICY: DE421/DE440 downloaded once at
     build time and hash-recorded (astropy's own de421 shorthand URL has
     rotted — PINT's loader is the blessed path); ephemeris name to be
     pinned explicitly in code and PINT clock files frozen at the Spec 9
     card. Confirm the policy.
- **AI-recommended ruling:** accept the split, the 3.12.3 choice, the
  second requirements file, the separate armor test root, and the
  determinism policy — the environment is fully rebuildable from the
  recorded recipe and touches nothing on the spine.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (hh) — Spec 9: PINT photon phase (armor; first card in tests_armor/)

- **What:** the AI-authored armor card — `tests_armor/_pint_routes.py`
  (photon->phase machinery, two independent routes), `tests_armor/
  test_spec9_photonphase.py` (T1-T4), `pytest.ini`, the committed NANOGrav
  15-yr par for J0030+0451, and golden override #12. Proves our use of
  PINT to < 1e-9 turns on 152,107 real NICER photons. Journal:
  `journal/spec-9-photon-phase.md`; logbook 2026-07-16 (Spec 9 entry).
- **Evidence:** armor suite 4 passed (204.6 s); T1 CLI-vs-library
  BIT-IDENTICAL (max dPhi = 0.0, all photons); T2 hand-rolled longdouble
  polynomial BIT-IDENTICAL to PINT incl. all ~3.39e10 turn integers; T3
  offline-subprocess sha256 match; T4 ISS band 6775-6788 km, sightline
  swing 13.16 ms. Windows spine unaffected: 84 passed, 0 skipped. Fold
  H-test 77.4.
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion and the [0,1) phase
     convention mirroring photonphase's PULSE_PHASE).
  2. PYTEST.INI (testpaths = tests): the no-arg spine `pytest -q` on
     Windows now, by configuration, never collects tests_armor/ (which
     would import PINT and fail there). One suite per environment, each
     zero-skip green where it lives. Confirm.
  3. THE COMMITTED PAR + DEFERRED BYTE-CHECK: pars/ is committed (KB-scale
     oracle-pinning text, gitignore exception) with NG15 fingerprint +
     F0-vs-comb-table cross-check (0.002%) as today's evidence; byte-level
     extraction check vs the 638.7 MB Zenodo tarball (md5 recorded) is
     DEFERRED to the sitting — one command, sha256 already recorded.
     Confirm the deferral. (UPDATE, same day: CLOSED at E4 — the canonical
     tarball was downloaded for the B1937/J0437 pars, its md5 matched the
     Zenodo manifest, and the committed J0030 par BYTE-MATCHED the tarball
     copy. See the E4 logbook entry.)
  4. OVERRIDE #12 (SPEC9_PHASE_AGREEMENT = 1e-9): the plan's own verbatim
     gate, frozen into golden_numbers.py; measured agreement is 0.0 so the
     gate is a pure regression tripwire. Confirm.
  5. INCLUDE_BIPM=FALSE MIRROR (measured tool finding): photonphase skips
     the TT(BIPM2019) refinement (--use_bipm defaults OFF); Route B
     mirrors the tool. Confirm you accept mirroring the tool's actual
     behavior over the par's radio-timing CLOCK line.
  6. THE T2 PRE-GREEN AMENDMENT (precision lesson 2): the first T2 draft
     routed through barycentric MJDs, which longdouble cannot carry at
     1e-9 turns (grid ~0.24 ns ~ 5e-8 turns at MJD 58137) — amended before
     the green run to PINT's (tdbld - PEPOCH) - delay decomposition,
     documented in the test docstring and journal §4. Confirm the
     amendment and own the lesson (with lesson 1, the 2^-29 recombination
     fingerprint).
  7. SEP-5 GATE CALL: fold H-test 77.4 (p ~ 4e-14) on real data satisfies
     "NICER fold clean" seven weeks early — E4 proceeds on REAL data, not
     simulation-only. Confirm this reading of the gate.
  8. SHARED-TOOLBOX PATTERN: E4's experiment imports
     tests_armor/_pint_routes.py (armor test root doubles as the armor
     toolbox; galnav/ stays spine-pure with no PINT import). Confirm.
- **Audit results (pre-commit):** truth-wall-auditor PASS (galnav/
  untouched; tests_armor imports neither truth nor nav; no side channels;
  golden change isolated at EOF; AST test intact). spec-reviewer PASS on
  all 8 code rules (its two notes are sub-items 4/5-adjacent student
  rulings: PINT-native km/s units in the armor tier, and pint-pulsar as
  the Spec-9-card-gated dependency). The truth-wall auditor also flagged
  two PRE-EXISTING non-breaching observations for the record: (a) E7
  seeds solve_state from a truth-derived start (a prior, not a
  measurement; defensible since E7 draws random truths — no plan exists
  to seed from); (b) E1/E2 select_pairs on truth positions (indices only;
  already item ee.2). Neither is Spec 9's.
- **AI-recommended ruling:** accept all eight — the two zeros are the
  strongest agreement evidence the card could produce, the amendment is a
  representation-theory necessity, and the gate call is measured, not
  hoped.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

## Item (ii) — E4: real NICER photons recover an injected orbit bias (the last experiment)

- **What:** the AI-authored E4 — machinery `tests_armor/_e4_fold.py`,
  gate `tests_armor/test_e4_injection.py`, experiment
  `experiments/e4_nicer_photon.py`, blessed archive
  `results/archive/e4_bias_recovery_20260716T154452Z.npz/.png`
  (regenerable from the npz alone), the B1937/J0437 NG15 pars, and golden
  override #13. Three seeded 100 km ISS-ephemeris biases injected (truth),
  each recovered in full 3-D from three real pulsar folds (nav) within
  2σ — the compass §7 pass criterion verbatim.
- **Where recorded:** logbook 2026-07-16 (E4 entry);
  `journal/e4-nicer-injection.md` (every measured table); citation
  [deJager89]; provenance data/e4_nicer/README.md.
- **Evidence:** armor suite 8 passed (343.6 s); spine 84 passed 0 skipped.
  Blessed run: |recovery error| 76.15 km on 100 km injections, worst
  components 1.84/1.88/1.85 σ (gate 2.0). Folds H = 43.8–874.1 after
  energy cuts; TOA σ 31.0/43/149 µs. J0030 par byte-matched the canonical
  NG15 tarball (md5-verified) — the item-(hh) deferred check is CLOSED.
- **Sub-items to rule on:**
  1. The card + tests themselves (own every assertion, incl. that T1 is
     the compass criterion verbatim and the recovery is rank-3).
  2. PER-PULSAR ENERGY BANDS (J0030/J0437 PI 30–150; B1937 PI 120–400 via
     a measured band scan ON TEMPLATE DATA — selection independent of the
     measurement): unfiltered J0030 folds at H=5.1 (93% background), the
     compass §11 background row made concrete. Same band both epochs
     (chromatic-profile rule). Confirm bands + the scan method.
  3. CROSS-EPOCH TEMPLATE DESIGN: template peak from the OTHER ObsID
     (independent photons → honest σ² = σ_m² + σ_t²); NG15 phase
     connection (~1 µs) is what makes it meaningful; the SHARED template
     correlates the three injections' errors (disclosed). Confirm.
  4. THE 76-km FROZEN-NOISE READING: near-identical recovery errors
     across injections = the shared template's single ~1.85σ noise draw
     mapped through the linear recovery — the honest-σ validation and the
     "template depth is the noise floor" mission lesson (16× deeper
     templates → ~20 km). Confirm this interpretation and its journal
     framing.
  5. BIAS_KM = 100 (stimulus): decisive vs 116–260 µs shift noise,
     under the 233 km / 0.5-turn wrap ceiling, and INSIDE one comb
     wavelength (|dr| < ρ = 286 km) — consistent with E5-lite's ambiguity
     finding (E4 measures differential shifts, not absolute combs).
     Confirm.
  6. OVERRIDE #13: E4_HTEST_MIN = 20.0 (2.2× below the weakest measured
     fold, 4–9× above noise) and E4_TOA_SIGMA_MAX_S = 50e-6 (§11's own
     upper bound; demonstrated by J0437 31.0 µs and B1937 ~43 µs;
     J0030's 134–149 µs recorded openly). T3's best-fold-demonstrates
     form + the 500 µs sanity ceiling. Confirm.
  7. FIRST-HARMONIC PEAK AS THE v1 ESTIMATOR, with the template-fit
     (matched-filter) TOA estimator recorded as the v1.1 deferral
     (E3-×60 pattern). Confirm the deferral.
  8. HEASOFT-FREE PIPELINE (already-screened cl.evt + PINT barycentering)
     and the constant-dr bias model as the honest reading of
     "orbit-ephemeris bias". Confirm.
- **Audit results (pre-commit):** truth-wall-auditor PASS — the injected
  dr_trues vector was traced to exactly three sites (the truth-side
  injection, the post-recovery scoring line, and the npz/figure record)
  and never reaches recover_bias, whose arguments are measurements +
  public pulsar facts only; galnav/ zero-diff and golden +25/−0 confirmed
  mechanically by git diff. spec-reviewer PASS on all 8 code rules, with
  two student-glance notes (neither blocking): the unused `projector`
  return of recover_bias (safe to delete later), and the standard 1e-12
  SVD rank epsilon at _e4_fold.py — the only inline numeric threshold
  outside golden_numbers.py; it decides matrix rank, not physics, and
  never bites with three separated sightlines (singular values ~1e-3).
- **AI-recommended ruling:** accept all eight — the gate is the plan's
  own, every number is measured, the weak spots (J0030's σ, the shared
  template) are disclosed rather than hidden, and the two lessons
  (background cuts, template depth) are the kind of real-data findings
  the paper's E4 section should lead with.
- **STUDENT RULING:** ____________
- **Date/initials:** ____________

---

*End of worksheet. Original 2026-07-15 draft consolidated twenty-five items
from `journal/logbook.md` (Spec 7 items a–i, velocity+aberration items j–o,
Session 5 skeptic-sweep items p–r, triple-verification items s–t, plus two
legacy test items and three new-card items). Build-night additions appended
after that draft: items u (E1 catalog swap), v/vi (Spec 10 propagator),
w (E6a sampled sky), x/y/z (E6b aging experiment), aa (E5-lite pulsar
lattice), bb (E3 New Horizons real-data anchor), cc (E2 convergence basins +
the option-A failure-handling ruling), dd (E7 relativistic aberration at
0.1c), ee (maximum-correctness sweep hardening niceties), ff (Spec 8b
closest-lattice-point CVP solver), gg (the WSL2 armor environment for
Spec 9/E4), hh (Spec 9 PINT photon phase), and ii (E4 real-NICER bias
injection/recovery — the final experiment) — see their logbook entries
for the full evidence. AI-drafted as a
decision aid; all rulings pending student sign-off; the logbook remains
authoritative.*
