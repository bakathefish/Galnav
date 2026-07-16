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
- `e5_pulsar_lattice_20260716T045926Z.npz` / `.png` — the E5-lite pulsar
  lattice-impossibility figure (produced by commit `ba028fd`; archived in the
  commit below). Deterministic (no Monte Carlo), so byte-identical on re-run.
  Headline numbers: the six §12 comb spacings 467-10,073 km; a starlight fix
  of ~1 au is x14,851 the widest comb (Crab 10,073 km) and x320,285 the finest
  (B1937+21 467 km); the packing radius of (Crab, B1937+21, J0030+0451) is
  286 km, so 1 au / rho = 523,024 -- no comb's integer turn-count is lockable
  from a star fix. Coast on the 467 km comb: 270.3 d at 1 cm/s, 2.70 d at
  1 m/s (matching the plan's 9-month / 3-day oracles). The E6 epoch floor drawn
  on the star-fix band (7.70 au) is read live from the E6 archive above.
  Explained in `journal/spec-e5-pulsar-lattice.md`; figure regenerable from the
  .npz alone via `experiments.e5_pulsar_lattice.replot_from_npz`.
- `e3_new_horizons_20260716T071109Z.npz` / `.png` — the E3 REAL-DATA anchor
  (produced by commit `b788690`; archived in the commit below). Deterministic
  (no Monte Carlo), so byte-identical on re-run. Our fully independent pipeline
  — Gaia DR3 CSV -> select Proxima Cen + Wolf 359 by source_id -> propagate
  J2016.0 to the mean LORRI image epoch (age 4.3087 yr, PM+RV; skipping the
  propagation lands ~30 au off) -> `n_star_solve` on Lauer's measured star
  directions — recovers the real New Horizons position to **0.3467 au** vs the
  JPL Horizons ephemeris, ~8.7x inside the 3 au plan gate (JPL enters only the
  score, never the solver). Reproduction cross-check (fed Lauer's own inputs):
  matches his recovered x2 to 0.0065 au (8-digit fixture rounding), miss vs JPL
  0.3457 au. Reported, not gated: our 2-star 1-sigma ellipsoid 1.08/0.57/0.50 au
  vs Lauer's 12-line x60 ellipsoid 0.441/0.233/0.206 au (his miss 0.351 au; the
  famous "0.44 au" is the ellipsoid semi-axis, not the miss). Real star data from
  Zenodo doi:10.5281/zenodo.15359866 ([Lauer25], [Lauer25-data]). Explained in
  `journal/spec-e3-triangulation.md`; figure regenerable from the .npz alone via
  `experiments.e3_new_horizons.replot_from_npz`.
- `e2_convergence_basins_20260716T075137Z.npz` / `.png` — the E2 convergence-basin
  map (produced by commit `732cb50`; archived in the commit below). The capture
  fraction over (star count x initial-guess displacement) at 1 pc, zero noise,
  500 isotropic starts per cell, seed 42. Headline: the navigator's 0.5-capture
  radius (basin median radius) grows with the number of stars — 2.00 pc (5
  stars), 3.94 pc (10), 6.33 pc (20), 9.79 pc (50), 11.57 pc (100) — matching the
  design reviewer's independent probe (2.0 pc at 5 stars, 11.8 pc at 100). So a
  coarse interstellar prior (light-years off) is captured only with many stars,
  and the UNDAMPED Gauss-Newton solver already reaches ~2-12 pc without damping
  (evidence for worksheet item (r)). Failure handling = option A (per-trial
  try/except LinAlgError isolation; a start can drive J^T J singular
  mid-iteration). Explained in `journal/spec-e2-convergence-basins.md`; figure
  regenerable from the .npz alone via
  `experiments.e2_convergence_basins.replot_from_npz`.
