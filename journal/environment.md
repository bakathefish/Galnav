# The machine and software behind every number (reproducibility record)

Why this file exists: the project rule says every figure must be
regenerable from saved arrays and seeds. That promise silently depends
on the exact software versions, because NumPy's official policy — NEP 19
and the numpy.random "Compatibility policy" page, citation [NEP19] in
`journal/citations.md` — guarantees that a seeded Generator reproduces
the same stream only on "the same build of numpy, in the same
environment, on the same machine." Across numpy versions, distribution
streams MAY change so algorithms can improve.

What that means for us, in one sentence: **the archived `.npz` files in
`results/archive/` are the primary evidence; byte-identical regeneration
is guaranteed only in the environment recorded below; anywhere else a
re-run is statistically equivalent (same physics, same conclusions) but
not bit-for-bit.**

Re-snapshot rule: any time Python or a package is upgraded, add a new
dated section below — never edit an old one — and note the first commit
made under the new environment.

## Snapshot 2026-07-15 (E1 ran and was committed under this, `8025e78`)

- OS: Windows 11 Home Single Language, build 10.0.26200
- CPU: Intel Core Ultra 9 285H (16 cores, 16 threads), 31.4 GB RAM —
  every "wall clock" runtime claim in the journal (e.g. ~70 s for the
  96-cell E1 grid) means this laptop
- Python: 3.13.3
- numpy 2.4.1, scipy 1.17.0, astropy 7.2.0, matplotlib 3.10.8,
  pytest 9.0.2
- `requirements.txt` deliberately states only `>=` minimums; the exact
  versions above are what actually ran.

OPEN STUDENT DECISION (already in the logbook, now load-bearing for the
paper's reproducibility statement): the project rulebook says "Python 3.11" but
the machine runs 3.13.3. Pin one — and decide whether the science-freeze
environment gets an exact lock file (a `pip freeze` of these five
packages) so the frozen results stay regenerable bit-for-bit on this
machine.

## Seeds inventory (deterministic randomness, no global seeds anywhere)

- E1 full grid: seed 42 → `np.random.default_rng(42)`, spawned into one
  child stream per cell; the seed is also recorded inside every E1
  `.npz` file itself.
- Harness acceptance tests: `default_rng(0)` (pair-selection test and
  CRLB-tracking cells), `default_rng(3)` (byte-identical
  reproducibility test).
