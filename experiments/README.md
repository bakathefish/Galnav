# Experiments

The seven experiment scripts, one per spec card. Run any of them
from the repo root with `python -m experiments.<name>`:

- `e1_crlb_grid.py` — solver validation + Cramér–Rao lower bound observability
  grid (the signature figure; 500 Monte Carlo trials per cell).
  `python -m experiments.e1_crlb_grid`
- `e2_convergence_basins.py` — convergence basins of the Gauss–Newton navigator.
  `python -m experiments.e2_convergence_basins`
- `e3_new_horizons.py` — real New Horizons line-of-position triangulation, the
  real-data anchor (reproduces Lauer et al. 2025).
  `python -m experiments.e3_new_horizons`
- `e4_nicer_photon.py` — real NICER photons: inject a known orbit bias and
  recover it (armor tier; runs only in the WSL2 + PINT environment).
  `python -m experiments.e4_nicer_photon`
- `e5_pulsar_lattice.py` — the pulsar-comb lattice ambiguity impossibility
  (a headline result).
  `python -m experiments.e5_pulsar_lattice`
- `e6_catalog_aging.py` — navigation accuracy vs star-catalog age (THE headline
  figure).
  `python -m experiments.e6_catalog_aging`
- `e7_relativistic_aberration.py` — relativistic aberration at 0.1c (the
  relativistic armor).
  `python -m experiments.e7_relativistic_aberration`

Every script writes BOTH the PNG figures and the exact plotted arrays to
`results/` with timestamps, so any figure can be regenerated from the saved
arrays alone.

Experiment scripts are the ONLY place where truth and nav meet: they take
measurement vectors from `galnav/truth/` and pass them explicitly to
`galnav/nav/`.
