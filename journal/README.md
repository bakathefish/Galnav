# journal/ — the paper's raw material (evidence map)

The ~20-page paper gets DRAFTED FROM THIS FOLDER. Rule of thumb: if a
number, decision, or surprise is not recorded here or in
`results/archive/`, the paper cannot use it. This page is the checklist form of the project rulebook, plus the
storage rules added 2026-07-15.

## Where everything lives

- `journal/spec-*.md`, `journal/e*-*.md` — one entry per card or
  experiment: the exact formula symbol by symbol, what the code does and
  does NOT do, every tolerance and why, every test and what it would
  catch, where the piece fits.
- `journal/citations.md` — every outside fact with full citation, where
  it is used, and its verification date. The paper's reference list is
  built FROM this file.
- `journal/logbook.md` — dated and append-only: what, why, measured
  evidence, commit hash. Corrections are new entries, never edits.
- `journal/environment.md` — the exact machine and software versions
  behind every committed number; re-snapshot on any upgrade (see
  [NEP19] — regeneration from seed is only guaranteed same-build,
  same-machine).
- `results/archive/` — the exact arrays and figures behind every quoted
  number, in version control (policy in its own README). Bench runs
  stay in `results/` and are git-ignored.
- `data/README.md` — dataset provenance: the exact query, retrieval
  date, and row-level sanity checks.
- `compass_artifact_*.md` §6/7/8 — spec-card order, experiment
  run-books with pre-registered predictions, and the calendar with its
  hard gates.

## End-of-card checklist (nothing is "done" until every box ticks)

1. `pytest -q` fully green — no failures, no skips.
2. Journal entry written (THE JOURNAL RULE).
3. Every new outside fact/number/formula/tool → `citations.md`, with a
   verification date.
4. Logbook entry: what, why, measured evidence; record the previous
   commit's hash per convention.
5. If an experiment ran: PNG + `.npz` (arrays + every parameter + the
   seed) written to `results/`; any run quoted in the journal or paper
   COPIED into `results/archive/`.
6. Environment unchanged? If anything was upgraded, add a new dated
   section to `environment.md` before committing results.
7. Any card touching `galnav/`: run `truth-wall-auditor` and
   `spec-reviewer`; record both verdicts in the logbook.
8. Commit, then grep the commit for AI attribution in message/metadata
   (must be none; the logbook documents AI use openly instead).
9. 5-line plain-English summary the students can read aloud.
10. AFTER ANY CRASH or interrupted run: before declaring the tree clean, run
    `git stash list` AND `git status --untracked-files=all`, not just a
    worktree/backup/.orig sweep. A crash can leave a `git stash` entry that a
    later `git stash pop` would silently re-inject — and a stash can carry a
    mutated GOLDEN value, which the deny-lock does not protect against
    (2026-07-16: a crash-era stash held a doubled-noise E1 mutant plus
    SOLVER_RECOVERY_TOL_AU 1e-8→1e-9; see the logbook).

## When the paper gets written (after science freeze, Oct 1)

- Methods = stitched from the spec journal entries — already in the
  students' own read-aloud voice.
- Results = figures regenerated from `results/archive/*.npz` at print
  quality (vector or high-DPI), numbers quoted from the archive.
- Limitations = the "what this does NOT claim" sections plus the honest
  findings in the logbook (anchor OPEN, upticks explained, gates cut).
- References = `citations.md`, filtered to what the text cites.
- Reproducibility statement = `environment.md` + seeds inventory +
  the archive policy.
- Before the related-work section is drafted: REDO the prior-art sweep
  (first sweep 2026-07-15 found no published navigation-accuracy-vs-
  catalog-age study; the field is active, so re-check).
