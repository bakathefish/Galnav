# Journal Entry E1 — The First Research Result

## What question E1 asks

The instrument (Specs 1–6) claims two things: it can find a spacecraft
from starlight, and it can predict its own error bars. E1 stress-tests
the second claim EVERYWHERE: 4 spacecraft distances (1–20 pc) x 6 star
counts (5–200) x 4 camera-noise levels (0.01–10 arcsec) = 96 different
navigation scenarios, 500 simulated universes each — 48,000 navigation
solves — asking one question each time: does the actual scatter of
answers match the theory formula sigma^2 (J^T J)^-1?

## The result

**Worst disagreement across all 96 cells: a factor of 1.064 (6.4%).**
The pass gate allowed 1.5x. The dots sit ON the lines across four decades
of noise and the whole tested volume of the solar neighborhood. Meaning:
the navigator is UNBIASED and EFFICIENT — it extracts essentially all
the position information physics puts in the measured angles (the
Cramer-Rao bound is not just an upper aspiration; it is achieved).

(The first run of E1, 2026-07-14, measured 1.052; the audit fixes below
changed how each cell's random stream is created, so the exact draws —
and only the draws — changed. Both numbers are ~10x inside the gate;
the ~1% wobble between them is itself a nice demonstration that the
result does not depend on which random numbers you happen to get.)

Files: `results/e1_crlb_grid_20260715T052152Z.png` (figure) and `.npz`
(every plotted number plus every experiment parameter — the figure is
regenerable from the arrays alone, per project rule).

## What the figure shows, physically

- **More stars → smaller error,** roughly like 1/sqrt(N) at first.
- **Then a flattening past ~50–100 stars:** the nearest stars carry
  almost all the signal (shift = move/distance!), so star #150 — five
  times farther than star #10 — barely helps. Adding faint far stars is
  not free navigation; this shape previews why catalog QUALITY beats
  catalog QUANTITY, the deeper theme of the aging experiment.
- **Slight uptick at (1 pc, 200 stars):** real and explainable — with the
  2000-pair memory cap, random pair subsampling swaps some strong
  near-star pairs for weak far-far pairs. Documented, not hidden.
- **Farther spacecraft → bigger error** at fixed star count: from 20 pc
  out, even the "nearby" stars are relatively farther, so every angle is
  stiffer. Navigation is genuinely harder out there.

## The honest surprise: we BEAT the published anchor, and why that's not a boast

Pre-registered expectation: ~3 au at (20 stars, 1 arcsec) — the
Bailer-Jones anchor. Measured: **0.41 au — 7x better.** Investigated
before celebrating; two real differences between the problems:

1. **He solves SIX unknowns, we solve three.** Bailer-Jones fits position
   AND velocity simultaneously (his spacecraft moves at relativistic
   speed, and aberration couples velocity into every measured angle).
   Extra unknowns dilute the same measurements.
2. **He measures far fewer pairs.** We feed the solver ALL well-separated
   pairs of 20 stars (187 measurements); his spacecraft measures angles
   among of order tens.

Both differences make OUR problem easier, in quantifiable directions —
consistent with a ~7x gap. Conclusion recorded: this is NOT the
apples-to-apples anchor reproduction. That test becomes possible only
when velocity + aberration join the state vector (a future spec, exactly
where the plan's week-5 hard gate expects it). Until then the anchor
stands OPEN, not passed — and the golden BAILER_JONES_ANCHOR numbers
stay untouched, waiting for the honest comparison.

## Every gate used, and why

- **E1_CRLB_TRACK_FACTOR = 1.5** (new golden, from the plan): across 96
  heterogeneous geometries, ratios drifting past 1.5x would signal model
  breakdown. Measured worst: 1.064 — 10x inside the gate.
- **Reused solver/statistics gates** via the harness acceptance tests
  (below); no other new tolerances.
- **Design parameters** (not tolerances, recorded in the .npz): pair
  separation floor 0.01 rad (the 61 Cygni lesson, institutionalized in
  code — near-coincident pairs never reach the solver); 2000-pair memory
  cap with seeded random subsampling; good-start offset 100 au;
  spacecraft direction fixed and recorded.

## The harness got its own acceptance tests (tests/test_e1_harness.py)

If the harness lies, the figure lies. Three tests, written before the
harness existed:
1. **Pair selection** excludes close pairs (61 Cygni can never sneak back
   in) and respects the memory cap.
2. **Four real grid cells** (near/far x few/many stars) must track CRLB
   within the golden factor — the experiment's own pass criterion,
   enforced forever in CI.
3. **Byte-identical reproducibility** of a cell under the same seed —
   every figure regenerable, exactly.

## What E1 does NOT claim

- No catalog errors yet (the catalog is treated as perfect — Spec 7 adds
  per-star error weighting, and with it the "catalog-limited plateau"
  annotation the plan wants on this figure).
- No velocity, no aberration — hence no anchor verdict (above).
- No bad starts (100 au offsets are "good starts"; capture-from-lost is
  experiment E2's question).

## The audits, and what they changed (2026-07-15)

Both project auditors reviewed E1 before it was committed. Every finding
and every fix, in plain English:

**Code-rule fixes (behavior checked before/after):**
- The experiment had re-typed its own copies of numbers that already
  live in one authoritative place: the parsec-to-au constant (now
  imported from `galnav/units.py`), the arcsec-to-radian conversion
  (now via `RAD_ARCSEC` from the golden file), and the solver's step
  tolerance and iteration cap (now imported from the golden file).
  Copies drift; imports cannot.
- `run_cell` returned two numbers nothing ever read (`ratio`,
  `iterations`, and later `n_pairs`) — removed, because the minimum-code
  rule exists precisely so every line has a test that would catch it.
- `run_grid` took an integer `seed` and built per-cell generators by
  seed arithmetic; the project rule says stochastic functions take an
  `rng` generator. It now takes `rng` and uses `rng.spawn()` — one
  child stream per cell, every cell still independently reproducible.
  This is the fix that changed the random draws (1.052 → 1.064 above);
  the full grid was re-run and re-saved.
- `run_grid`'s docstring now states the units of every argument.

**The truth-wall question (the important one).** The auditor flagged
that the solver's starting guess was computed as `true_pos + offset` —
literally reading the true position. The physics defense: the "true
position" in E1 IS the experiment's flight plan (`SPACECRAFT_DIR x
distance`); a real spacecraft absolutely knows its own flight plan, and
navigation's job is to refine it. The code now says exactly that:
`plan_pos` (mission design, navigator may hold it) is computed first;
truth independently realizes the plan; the navigator's start and pair
selection use ONLY `plan_pos`. Verified byte-identical — same arrays to
the last bit. What E1 still does NOT test is a navigator with no idea
where it is; that is E2 (convergence basins), exactly where the plan
put it.

**Flagged, deliberately not fixed here:**
- The experiment hands the navigator truth-side star positions. Today
  that leaks nothing — there is no catalog error yet, so truth's stars
  and the public catalog are the same numbers by construction. The
  moment Spec 7 adds catalog errors, this wiring MUST switch to a
  nav-side catalog path. Recorded so it cannot be forgotten.
- The harness test checks pair separation against a literal `0.01`
  that silently mirrors `MIN_PAIR_SEP_RAD`. Tests are student
  territory; flagged for the students to decide.

## Where this fits

This is the project's validation backbone: every later experiment (aging
catalogs in E6, real New Horizons data in E3) stands on "the instrument
is proven unbiased and physics-limited" — which is now a measured fact
with a figure, not a claim.
