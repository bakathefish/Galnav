# results/archive/ — the blessed, version-controlled evidence

Everything else in `results/` is a lab bench: every run writes new
timestamped files there, and git ignores them. THIS folder is the vault:
when a run becomes "the number the project quotes" — in the journal, the
logbook, or the paper — its exact `.npz` + `.png` are COPIED here and
committed, so the evidence behind every quoted number survives laptop
loss, cleanup accidents, and package upgrades.

Rules:

1. Never overwrite or delete anything here. Supersede with a new file
   and say so in `journal/logbook.md`.
2. Every file here must be traceable: which commit produced it, which
   journal entry explains it.
3. Figures are regenerable from the `.npz` arrays alone (project rule) —
   at any DPI, or in vector form for the paper.

Why keep copies in git instead of "just re-run the seed": NumPy only
guarantees that a seeded random Generator reproduces the same stream on
the SAME numpy build, in the SAME environment, on the SAME machine
(NEP 19 / the numpy.random compatibility policy — citation [NEP19] in
`journal/citations.md`, details in `journal/environment.md`). On any
other machine, or after an upgrade, a re-run is statistically
equivalent — same physics, same conclusions — but not byte-identical.
The archived arrays are therefore the primary record; regeneration is
the cross-check.

## Contents

- `e1_crlb_grid_20260715T052152Z.npz` / `.png` — the E1 paper run
  (commit `8025e78`, tag `e1-complete`): worst RMS/CRLB deviation
  factor 1.064 across 96 grid cells, pass gate 1.5. Explained in
  `journal/e1-crlb-grid.md`.
- `e1_crlb_grid_20260714T180112Z.npz` / `.png` — the superseded first
  E1 run (worst factor 1.052), produced by the pre-audit harness whose
  per-cell seeding was replaced before anything was committed (logbook,
  2026-07-15). Kept because the logbook quotes its number, and because
  the code that produced it was never committed — this file is its only
  record.
- `e6_catalog_aging_20260715T231348Z.npz` / `.png` — the E6 HEADLINE run
  (produced by commit `4f80687`; archived in commit `60a8d4e`): navigation
  error over 10 catalog ages x 10 sensor sigmas x 500 trials, seed 42,
  1 pc, 20 nearest stars (5 lacking Gaia RV), missing_rv_scale 30 km/s.
  Headline numbers: epoch parallax floor 7.66 au; at the 10 mas sensor the
  error ages 7.70 -> 17.07 -> 31.90 au (ratio 2.22x at 100 yr, 4.14x at
  200 yr); crossover age (rms = sqrt2 x rms(age 0)) rises 44.8 yr at the
  finest sensor to 161.9 yr at 60 arcsec; camera noise equals the floor in
  quadrature near ~15.9 arcsec. Explained in
  `journal/spec-e6b-aging-experiment.md`; figure regenerable from the .npz
  alone via `experiments.e6_catalog_aging.replot_from_npz`.
