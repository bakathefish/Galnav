# Experiments

Planned scripts, created one spec card at a time (see the project rulebook):

- `e1_solver.py` — solver observability grid (500 Monte Carlo trials per cell)
- `e2_basins.py` — convergence basins of the estimator
- `e3_newhorizons.py` — validation against the New Horizons parallax observations
- `e5_lattice.py` — pulsar-comb lattice ambiguity
- `e6_aging.py` — navigation accuracy vs star-catalog age

Every script writes BOTH the PNG figures and the exact plotted arrays to
`results/` with timestamps, so any figure can be regenerated from the saved
arrays alone.

Experiment scripts are the ONLY place where truth and nav meet: they take
measurement vectors from `galnav/truth/` and pass them explicitly to
`galnav/nav/`.
