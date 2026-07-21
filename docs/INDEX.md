# GalNav docs index — want X? read Y

A one-screen map of the whole repository. Start at the top row and follow the
one that matches what you came for.

| I want to… | Read / run |
|---|---|
| Get the whole project in one page | [`README.md`](../README.md) (repo root) |
| Understand the science and every finding | [`journal/findings-compilation.md`](../journal/findings-compilation.md) — the paper source pack (findings F1–F15, the numbers table, the framing rules) |
| Know *why* a specific spec card is built the way it is | `journal/spec-N-*.md` and `journal/e*-*.md` — one entry per card/experiment, formula by formula |
| Check the source of any external fact or number | [`journal/citations.md`](../journal/citations.md) — every outside fact, with a verification date |
| Follow the day-by-day history and decisions | [`journal/logbook.md`](../journal/logbook.md) — dated, append-only; also the open AI-use record |
| Understand the demo app in full | [`docs/GUI-EXPLAINED.md`](GUI-EXPLAINED.md) — the pipeline, the web app, the pipeline walk + the live OpenSpace viewer, the chronometer |
| Run the demo | **`python -m gui.webapp`** (THE demo — a local browser app; `Start GalNav Demo.bat` opens it). Desktop fallback `python -m gui.app`; headless smoke test `python -m gui.nh_demo` |
| See the pipeline as a picture | [`docs/PIPELINE-FLOWCHART.html`](PIPELINE-FLOWCHART.html) — every stage, the data on each arrow, the 3-D and chronometer outputs |
| Read the year off an old photo, or fly to the fix in a planetarium | [`docs/GUI-EXPLAINED.md`](GUI-EXPLAINED.md) (chronometer + the OpenSpace pipeline walk), demoed in [`docs/ISEF-DEMO-PLAYBOOK.md`](ISEF-DEMO-PLAYBOOK.md) |
| Present at ISEF (booth script, Q&A, framing) | [`docs/ISEF-DEMO-PLAYBOOK.md`](ISEF-DEMO-PLAYBOOK.md) |
| Know the rules the code is held to | `tests/golden_numbers.py` + `tests/test_truth_wall.py` — the frozen truth wall the suite enforces |
| Reproduce a figure exactly | `results/archive/` — the blessed `.npz` arrays + PNG behind every quoted number |
| Check dataset provenance | [`data/README.md`](../data/README.md) (Gaia), `data/e3_new_horizons/README.md` (New Horizons), `data/e4_nicer/README.md` (NICER) |
| Run the tests | `python -m pytest -q` (84 spine) · `python -m pytest tests_gui -q` (153 GUI) · armor 8: WSL2 only, per [`journal/environment-armor.md`](../journal/environment-armor.md) |

The rule of thumb from `journal/README.md`: if a number, decision, or surprise
is not in `journal/` or `results/archive/`, the paper cannot use it.
