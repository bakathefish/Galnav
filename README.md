# GalNav — the observability limits of interstellar starlight + pulsar navigation

GalNav is a two-student ISEF research project. It measures how well an
interstellar spacecraft can know **where it is** from the light of nearby
stars fused with the ticks of pulsars — and, just as importantly, how that
knowledge **decays as the spacecraft's star catalog ages**. Everything here
is built under one rule: the students write the specifications and the
acceptance tests, and every number in the paper is reproducible bit-for-bit
from a fresh clone. The science freeze is **October 1, 2026**.

This README is the front door. If you are a judge, a teacher, or a stranger
who just opened the repository, start here, then follow the links.

## The thesis in three legs

**Where you are. When you are. How long you can trust it.**

- **Where you are (leg 1 — the headline, E6).** Starlight gives an
  interstellar spacecraft an absolute but au-coarse position fix that
  **decays on a measurable schedule** as its star catalog ages.
- **When you are, and how long you can trust it (leg 2 — E5 + Spec 8).**
  Pulsars offer km-fine but integer-ambiguous ticks that an au-coarse fix
  can **never** bootstrap — a four-order-of-magnitude no-man's-land.
- **Anchored to reality (leg 3 — E3 + E4).** A real spacecraft (New
  Horizons) is found from its own star photos, and real X-ray photons
  surrender an injected spacecraft ephemeris error. Both legs stand on real
  NASA data, and everything is reproducible bit-for-bit from a fresh clone.

## The headline numbers

These are the memorize-grade numbers, copied from
[`journal/findings-compilation.md`](journal/findings-compilation.md) §5.
Every one is byte-reproducible from the archived arrays.

| number | meaning | provenance |
|---|---|---|
| 1.064 (grid) / 1.045 (CI cells) | worst MC/CRLB ratios — optimal navigator | E1 archive + test_e1_harness |
| 3.019 au / 2.028 km/s | BJ21 anchor reproduced (3 / 2 published) | test_bj_anchor |
| 0.3467 au | real New Horizons recovered (JPL truth) | E3 archive |
| ~30 au | the miss if you skip epoch propagation | E3 journal |
| 7.66 au | epoch-parallax floor, 1 pc / 20 stars (sub-10-mas asymptote) | E6 journal (archive finest cell 7.70) |
| 44.8 -> 161.9 yr | catalog-age crossover vs sensor (10 mas -> 60") | E6 archive |
| ~15.9 arcsec | the knee below which cameras stop mattering at 1 pc | E6 archive |
| 286.02 km / 523,024x | comb packing radius / how far a 1-au fix overshoots it | E5 archive |
| 100.000% / 8,000 | exact integer recovery inside rho | Spec 8 tests |
| 1356 au / 1201 km/s | classical navigator's bias at 0.1c | E7 archive |
| 270.3 d @ 1 cm/s | comb-lock coast budget (467 km comb) | E5 archive |
| 0.0 (bit-identical) | two-route photon-phase agreement, 152,107 photons | Spec 9 |
| 3.39e10 turns | pulsar rotations tracked to 1e-9 of one turn | Spec 9 |
| 2^-29 exactly | the recombination bug's fingerprint | Spec 9 journal |
| H = 874.1 | J0437 fold significance (binary model validated) | E4 |
| 76.15 km / 1.85 sigma | 100 km bias recovery error / its honest size | E4 archive |
| 92 / 13 / 2 | tests / authorized overrides / pinned environments | repo |

The `92 / 13 / 2` row counts the two pinned science environments: **84 spine
tests** (the default gate) plus **8 armor tests** (WSL2-only). The GUI demo
adds **71 more tests** of its own; it is a friendly front door, not spine
science, so it is counted separately.

## Repo map

Every top-level item, one line each.

- **`galnav/`** — the physics library, split by the truth wall (see below):
  - `galnav/truth/` — the **SIMULATOR**. It holds the true state of the world
    and generates measurements.
  - `galnav/nav/` — the **NAVIGATOR**. It sees only measurements plus public
    catalog values — exactly what a real spacecraft would have.
  - `galnav/pulsar.py` — public pulsar physics (combs, ambiguity-lattice
    packing radius, coast time). Used by E5.
  - `galnav/units.py` — the single owner of every unit and frame conversion
    (au, km/s, radians internally; arcsec/mas only at the edges).
  - `galnav/geometry.py`, `galnav/parallax.py` — shared angle and parallax
    math used by both sides.
- **`experiments/`** — one script per research result; each writes a PNG plus
  the exact plotted arrays (`.npz`) to `results/` so every figure is
  regenerable from the arrays alone:
  - `e1_crlb_grid.py` — solver validation against the Cramér-Rao bound (the
    signature figure) — `python -m experiments.e1_crlb_grid`
  - `e2_convergence_basins.py` — how far "lost" the solver can start and still
    find home — `python -m experiments.e2_convergence_basins`
  - `e3_new_horizons.py` — recover the real New Horizons spacecraft from two
    star photos — `python -m experiments.e3_new_horizons`
  - `e4_nicer_photon.py` — inject and recover an orbit bias from real NICER
    X-ray photons (armor; WSL2 only) — `python -m experiments.e4_nicer_photon`
  - `e5_pulsar_lattice.py` — the pulsar-comb bootstrap impossibility —
    `python -m experiments.e5_pulsar_lattice`
  - `e6_catalog_aging.py` — navigation error vs catalog age (the headline) —
    `python -m experiments.e6_catalog_aging`
  - `e7_relativistic_aberration.py` — why relativity is mandatory at 0.1c —
    `python -m experiments.e7_relativistic_aberration`
- **`gui/`** — the demo app: a photo goes in, and a position, a catalog age,
  and a 3-D map come out. **`python -m gui.webapp`** is THE demo — a local
  browser app (the `Start GalNav Demo.bat` launcher opens it). The older
  desktop window is `python -m gui.app`, and `python -m gui.nh_demo` is a
  headless real-data smoke test. `gui/web/` holds the browser front-end
  (HTML/JS/CSS plus a vendored, fully offline spacekit.js for the 3-D view).
  See [`docs/GUI-EXPLAINED.md`](docs/GUI-EXPLAINED.md).
- **`data/`** — dataset provenance (never the raw bytes, which are
  git-ignored and re-fetchable): the Gaia DR3 nearby-star subset with its
  exact query, the New Horizons FITS deposit, and the NICER photon lists.
  `data/candidates/` is a git-ignored cache of fresh test images (DSS survey
  plates, TESS, HST, wide-field JPGs) the demo pipeline can be fed.
- **`docs/`** — the reader-facing guides: `INDEX.md` (the want-X-read-Y map),
  `GUI-EXPLAINED.md` (the demo app in prose), `ISEF-DEMO-PLAYBOOK.md` (the
  booth script), and `PIPELINE-FLOWCHART.html` (the pipeline as a visual
  data-flow graph).
- **`tests/`** — the **84-test spine gate**. `python -m pytest -q`.
- **`tests_armor/`** — the **8 armor tests** (real photon data; WSL2 float128
  only, run by explicit invocation — never by the default gate).
- **`tests_gui/`** — the **71 GUI tests** (offline, deterministic). `python -m
  pytest tests_gui -q`.
- **`results/`** — timestamped PNG + `.npz` outputs. `results/archive/` holds
  the *blessed* runs behind every quoted number, kept in version control.
- **`journal/`** — the evidence trail the paper is drafted from: one entry per
  spec card and experiment, `citations.md` (every outside fact),
  `logbook.md` (dated, append-only history), and
  `findings-compilation.md` (the single paper source pack).
- `requirements.txt` / `requirements-armor.txt` — the two pinned
  environments. `pytest.ini`, `conftest.py` — test configuration.

## How to reproduce everything

From a fresh clone, on the pinned native-Windows spine environment:

```
pip install -r requirements.txt
python -m pytest -q                      # 84 passed — the spine gate
python -m experiments.e1_crlb_grid       # signature figure (~90 s, 96 cells)
python -m experiments.e6_catalog_aging   # the headline figure (~25 s)
python -m gui.nh_demo                     # real New Horizons, photo -> position
```

Each experiment writes a timestamped PNG plus the exact arrays to `results/`.
The blessed runs behind every quoted number are kept in `results/archive/`,
so any figure in the paper regenerates from committed arrays alone.

The **armor track** (Spec 9 photon-phase and E4) runs only in a separate
WSL2 environment, because PINT's photon-phase precision needs 80-bit extended
long double that native Windows cannot provide (measured: `np.longdouble` is
float64 there). The exact route is in
[`journal/environment-armor.md`](journal/environment-armor.md), and the raw
NICER photons are re-fetchable per [`data/e4_nicer/README.md`](data/e4_nicer/README.md).

## The truth wall (why a judge can trust the results)

1. `galnav/truth/` is the simulator; `galnav/nav/` is the navigator.
2. The navigator may **never** import from the simulator — no shared globals,
   no shared files. The only interface is the measurement vector passed
   explicitly by an experiment script.
3. `tests/test_truth_wall.py` enforces this by reading the source code (AST
   inspection); it is deny-locked and never edited to make code pass.
4. Two independent human-style audits (`truth-wall-auditor`, `spec-reviewer`)
   re-check every card for leaks the AST test cannot see.
5. Result: "the navigator cannot cheat by peeking at the true answer" is a
   provable property, not a promise.

## A note on AI use

This is an ISEF-disclosed AI-assisted project. The students author the
specifications and the acceptance tests; the AI implements against them,
never the other way around. The AI workflow is documented openly and in
full in [`journal/logbook.md`](journal/logbook.md) — every session, every
decision, and every authorized change to a locked file is recorded there.
The students' own AI-use disclosure log is kept alongside the project and
filed with the ISEF paperwork.

## Where to go next

See [`docs/INDEX.md`](docs/INDEX.md) — "want X? read Y" — for a one-screen
map of the whole repository.
