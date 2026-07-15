# Journal Entry — E1 Catalog Swap (closing the latent truth-wall flag)

## The one-sentence result

The E1 experiment now feeds its navigator the **public star catalog** a
real spacecraft carries, instead of the simulator's **true** star
positions — and because those two lists of positions are byte-for-byte
identical today, **every E1 number is unchanged to the last bit** (checked:
0.0 difference across all 96 grid cells, and a bit-for-bit match to the
blessed paper run).

## What was actually wrong (in plain English)

Our project has a "truth wall." One half of the code, `galnav/truth/`, is
the pretend universe: it knows where every star *really* is and it makes
the fake camera pictures. The other half, `galnav/nav/`, is the spaceship's
brain: it is only allowed to know what a real spaceship would know — the
measurements it just took, plus the published star catalog it launched
with. The whole point of the wall is that the brain can never peek at the
true answer, so when it navigates well we know it earned it.

The E1 experiment script sits *outside* the wall — it is the referee that
holds both sides and passes notes between them. Before this card, the
referee was lazy: it loaded the star positions **once**, from the truth
side (`galnav.truth.sky`), and handed that *same* list to BOTH the camera
(to make pictures) AND the spaceship's brain (to navigate with). Today that
is harmless, because the true positions and the catalog positions are
exactly equal — no catalog errors exist yet. But the moment a later card
makes the catalog *wrong on purpose* (the whole point of the "how does
navigation decay as the catalog ages?" study), that lazy wiring would
secretly hand the brain the TRUE positions. The headline figure would then
show perfect navigation no matter how stale the catalog was — a silent lie.

This card fixes the wiring **now, while it is provably a no-op**, so the
fix itself can be trusted (nothing changes) and the trap is disarmed before
it can ever spring.

## The change, one moving part at a time

There is no new math here — this is a plumbing change. The "formula" is a
data-flow rule:

    measurements  <- generated from  TRUTH star positions
    solver        <- reads only      CATALOG star positions
    covariance    <- reads only      CATALOG star positions

Concretely, the workhorse function `run_cell` used to take one star array:

    run_cell(stars_all_au, ...)          # one list, used for everything

It now takes two:

    run_cell(stars_all_au, nav_stars_all_au, ...)

- `stars_all_au` — the TRUTH positions. Used to (1) generate the noisy
  measurements and (2) decide which star *pairs* are far enough apart to be
  worth measuring (a property of the real sky the camera looks at).
- `nav_stars_all_au` — the public CATALOG positions. This is the **only**
  sky knowledge the navigator gets. It flows into exactly two calls:
    - `solve_position(measured, nav_stars, ...)` — the Gauss-Newton solver
      that recovers where the spaceship is;
    - `position_covariance(nav_stars, plan_pos, ...)` — the CRLB error-bar
      prediction.

The experiment's `main()` now builds both lists side by side:

    stars_all     = star_positions_au(load_catalog(CSV))       # truth sky
    nav_stars_all = load_nav_catalog(CSV)["star_pos_au"]        # public catalog

using the nav-side loader `galnav/nav/catalog.py` that was written for
Spec 7 — the same public-catalog path Spec 7 already uses for its
covariance card. The two loaders read the *same public CSV* (that is
allowed — the CSV is public catalog data, not truth state) and do the exact
same arithmetic, which is why their outputs are identical today.

### One extra, deliberately-tiny cleanup: `true_pos` -> `plan_pos`

The covariance call used to be `position_covariance(stars, true_pos, ...)`.
Two things about the old arguments were truth-flavored: the star positions
(`stars`, now `nav_stars`) and the point where the error bars are evaluated
(`true_pos`). The second one was never really "truth data" — in E1 the
spacecraft flies its plan exactly, so the code literally sets
`true_pos = plan_pos`, and `plan_pos` is public mission-design knowledge
(`direction x distance`) the navigator is allowed to hold. I renamed the
argument to `plan_pos` so that **every** input to the navigator's own
error-bar prediction is spelled with a public name. This changes **no
number** (they are the same value, bit for bit) and is also more correct
for the future: when a later card (E2) adds steering error so the true
position drifts from the plan, the navigator's *predicted* error bars must
be evaluated at where it *believes* it is (`plan_pos`), not where it truly
is. The score line just below — `solved - true_pos` — deliberately keeps
`true_pos`, because *grading* the answer against the truth is the referee's
job, not the navigator's.

## What this code does — and, just as important, what it does NOT do

It DOES:
- route the solver and the covariance through the public catalog;
- keep truth generating the measurements;
- expose the exact measurement vector each cell used (a new `"measured"`
  key in `run_cell`'s returned dict), so a test can *prove* the physics was
  untouched between two runs;
- leave every committed E1 number identical to the last bit.

It does NOT:
- change any physics, any formula, any tolerance, or any golden number;
- touch `galnav/truth/` or `galnav/nav/` at all — the fix lives entirely in
  the referee (the experiment script) and its harness test, which is
  exactly where a note-passing bug belongs;
- reroute **pair selection**. Choosing which pairs are well-separated still
  reads the truth `stars` array. That is out of this card's scope on
  purpose: (a) the card names only the solver, the covariance, and the
  catalog sigma; (b) it is a property of what the real camera can resolve;
  and (c) rerouting it would let a wrong catalog change *which* pairs are
  measured, which would corrupt the very measurement-identity proof that
  Test 1 relies on. It is recorded, unchanged, for a future decision.
- reroute the **initial guess** (`starts`). The card explicitly leaves that
  separately-recorded LOW flag alone; it is built from `plan_pos` anyway.
- use the catalog's per-star distance uncertainty. The nav loader also
  returns `sigma_dist_au`, but E1's covariance is position-only
  (`sigma^2 (JᵀJ)^-1`, no `W`), so "the catalog sigma used in W where
  applicable" is **not applicable here**. It becomes applicable in the
  catalog-aging experiments, which will pass `sigma_dist_au` to the same
  `position_covariance` argument Spec 7 already built.

## Every tolerance touched, and why (there are none)

**No tolerance was touched, and none was needed.** This is worth stating
plainly because THE JOURNAL RULE demands a reason for every tolerance, and
the honest reason here is that all three acceptance tests are built on
**exact equality**, not "within some wiggle room":

- Test 2 and Test 3 assert `np.array_equal(...)` / `==` — bit-for-bit. They
  can afford to, because the whole claim of the card is that the swap is a
  *perfect* no-op today, so anything looser than exact equality would be
  under-claiming and could hide a real drift.
- Test 1 asserts two things change and one thing (the measurements) is
  exactly equal — again `np.array_equal`, no tolerance.

Because the tests need only exact equality, `tests/golden_numbers.py` was
**not opened**, and no new constant was invented. That is the cleanest
possible outcome for a wiring card.

## The three tests, and what each would catch if the code were wrong

All three live in `tests/test_e1_catalog_path.py`.

1. **`test_navigator_reads_catalog_not_truth`** — the real proof. It runs
   one small cell twice with the SAME truth stars (so the camera makes
   identical pictures) but, in the second run, flings ONE catalog star
   1000 au off one axis. It then asserts:
   - the measurement vectors are **exactly equal** (the physics was
     untouched — same truth, same pairs, same random draws), AND
   - the recovered position error (`rms_au`) and the predicted error bars
     (`crlb_au`) both **change**.
   If the solver or the covariance were secretly still reading truth, the
   flung star would be invisible to them and `rms`/`crlb` would be
   unchanged — the test would fail. It would also fail if the catalog
   perturbation leaked into the measurements. (I confirmed the flung star,
   index 0, appears in 7 of the 28 selected pairs at this geometry, so it
   genuinely drives the fit — the test cannot pass by the star being
   unused.)

2. **`test_catalog_and_truth_positions_bitwise_identical_today`** — the
   executable footnote. It asserts the truth positions and the catalog
   positions are `np.array_equal`. This is *why* the swap changes nothing
   today, written as code. The day someone edits the CSV, introduces a unit
   bug, or lands catalog aging, this test fails loudly — turning a silent
   divergence into an obvious one.

3. **`test_swap_preserves_results_bitwise`** — the no-op guarantee. It
   computes one cell's `(rms, crlb)` twice at the same seed: once with the
   truth positions handed to the navigator path, once with the catalog
   positions. It asserts they are `==`, bit for bit. This is self-contained
   (it compares two live runs, needs no stored golden number) and it is
   what lets us say "the committed E1 numbers are unchanged" with a straight
   face.

### Evidence beyond the unit tests

The unit tests check one cell each. I also re-ran the **full 96-cell grid**
two ways — navigator fed truth (the old behavior) versus navigator fed
catalog (this card) — at the real experiment's seed and grid:

- `rms` old-vs-new: **bit-identical** (max |difference| = 0.0 au),
- `crlb` old-vs-new: **bit-identical** (max |difference| = 0.0 au),
- new code vs the blessed archive
  (`results/archive/e1_crlb_grid_20260715T052152Z.npz`): **bit-identical**
  (max |difference| = 0.0), worst RMS/CRLB factor **1.064**, exactly the
  blessed headline.

The existing harness tests in `tests/test_e1_harness.py` were re-wired to
pass the catalog array to `run_cell` (an architecture change the card
authorizes), and **not one assertion or tolerance in them was weakened** —
they still pass with identical numbers, because truth equals catalog today.

## Where this sits in the big project, and what's next

This closes the **latent truth-wall flag** that has been recorded since the
E1 audit (logbook, 2026-07-15, first noted lines ~404–410 and re-confirmed
by the Session-5 skeptic sweep). It is the E1 twin of the swap Spec 7
already made on the covariance side: after this card, **both** of the
project's navigator entry points — the solver in E1 and the covariance in
Spec 7 — read the public catalog, never truth.

Why it matters for the headline science: the project's flagship question is
"how does navigation accuracy decay as the star catalog ages?" Answering it
means running E1-style grids with a catalog whose star positions are
*deliberately* wrong (aged parallaxes), while truth stays put. That
experiment is only meaningful if the navigator is genuinely blind to truth.
This card makes that blindness structural and proves, today, that switching
the blindfold on changed nothing — so any future decay we measure is real,
not an artifact of the plumbing.

What's next (not this card): the catalog-aging experiment itself will feed
`nav_stars_all` a perturbed catalog and pass `sigma_dist_au` into
`position_covariance`'s `W`. The pair-selection channel and the
initial-guess channel remain recorded, out-of-scope items for a student
decision.

## Process note (honest disclosure)

Under the project's recorded exception, this card's text and its three
acceptance tests were **AI-authored**; the standing "students write the
tests" rule is set aside for THIS CARD ONLY and remains in force otherwise.
**Student review and ratification of the card are pending** — tracked as
ratification checklist item **(u)** in the logbook.
