# The ARMOR environment (WSL2) — exact record and every "why"

*Written 2026-07-16. Sibling of `journal/environment.md` (the native-Windows
SPINE environment). This file records the second, separate environment that
exists ONLY for the armor tier — Spec 9 (PINT photon phase) and E4 (real
NICER data). Nothing about the spine environment changed.*

## 1. Why a second environment exists at all

Spec 9's acceptance gate is "PINT `photonphase` agreement with reference to
`< 1e-9` in phase" (compass §6). Getting pulsar photon phases right over
years of elapsed time means tracking ~10^11–10^12 pulsar turns (seconds
since the timing epoch, ~10^8–10^9 s, divided by a millisecond period)
while still caring about a *billionth* of one turn. Ordinary 64-bit floats
carry about 16 significant digits (machine epsilon 2.2e-16 — epsilon is
the smallest relative gap between two adjacent representable numbers), and
PINT itself refuses to run its precision-critical paths unless the platform
provides an *extended* 80-bit float: it demands
`np.finfo(np.longdouble).eps < 2e-19` (`check_longdouble_precision`).

Measured on this project's two platforms on 2026-07-16:

| platform | `np.longdouble` | eps | PINT verdict |
|---|---|---|---|
| Windows 11 native (spine env, Py 3.13.3 + numpy 2.4.1) | `float64` (MSVC `long double` == `double`) | 2.220446049250313e-16 | FAIL — reduced-precision mode, gate unreachable |
| WSL2 Ubuntu 24.04 x86-64 (this env) | `float128` (x87 80-bit) | 1.084202172485504434e-19 | PASS — `check_longdouble_precision() == True` |

This is a **compiler/platform property, not a Python or numpy setting**: on
Windows, MSVC defines `long double` as 64-bit, so no native-Windows numpy
(pip or conda) can provide the 80-bit type. The only fixes are a different
OS personality (WSL2/Docker Linux) — chosen — or dropping the armor tier
(the Sep 5 gate's sanctioned "simulation-only" fallback).

**Consequence, stated plainly:** armor numbers (Spec 9 / E4) are produced
and reproduced ONLY in this environment. Spine numbers are produced and
reproduced ONLY in the native-Windows environment of
`journal/environment.md`. Neither side re-blesses the other's numbers.

## 2. What exactly is installed

- WSL 2.6.3.0 (was already installed on the box — no system change was
  needed), kernel `6.6.87.2-microsoft-standard-WSL2`.
- Distro: Ubuntu 24.04.4 LTS (Noble), `x86_64`, default WSL version 2.
- Virtualenv: `/opt/galnav/venv`, created from the distro's
  **Python 3.12.3**.
- Installed from `requirements-armor.txt` (repo root) via the project's
  allowed route (`python -m pip install -r ...`).

**Why Python 3.12.3 and not the spine's 3.13.3:** 3.12.3 is Ubuntu 24.04's
maintained default; matching 3.13.3 would require a third-party PPA
(deadsnakes) — more moving parts in an environment whose whole point is
byte-stable reproducibility. The two environments are already necessarily
different (different OS, different C library, different `long double`), so
version parity buys no scientific equivalence; instead the load-bearing
package — numpy — is pinned to the SAME 2.4.1 as the spine, and everything
else is recorded exactly below. Flagged for student ratification
(worksheet item gg).

Full `pip freeze` of the environment (2026-07-16):

```
PyYAML==6.0.3
astropy-iers-data==0.2026.7.13.0.54.2
astropy==8.0.1
contourpy==1.3.3
corner==2.3.0
cycler==0.12.1
emcee==3.1.6
fonttools==4.63.0
iniconfig==2.3.0
jplephem==2.24
kiwisolver==1.5.0
loguru==0.7.3
matplotlib==3.11.0
nestle==0.2.1
numdifftools==0.9.42
numpy==2.4.1
packaging==26.2
pillow==12.3.0
pint-pulsar==1.1.4
pluggy==1.6.0
pyerfa==2.0.1.5
pyparsing==3.3.2
pytest==9.1.1
python-dateutil==2.9.0.post0
scipy==1.18.0
six==1.17.0
uncertainties==3.2.3
```

(`pint-pulsar==1.1.4` is current as of 2026-07-16; the compass §5's 1.1.2
pin predates it and is superseded here — recorded, ratification item gg.)

**Amendment, same day (2026-07-16):** `pytest` was omitted from the first
build and added via `requirements-armor.txt` the moment Spec 9's TDD loop
needed its runner — resolved `pytest==9.1.1` (plus its two small
dependencies `pluggy==1.6.0`, `iniconfig==2.3.0`), already reflected in the
freeze above. pytest is on the project's allowed-command list verbatim; as a pure
test runner it touches no computed number, so its version is not
load-bearing.

## 3. Ephemeris determinism (the runtime-download landmine)

PINT and astropy download the solar-system ephemeris on first use. A
blessed number must never depend on whether a URL was reachable that day,
so the ephemerides were downloaded ONCE at environment build time and now
live in the distro's astropy cache (`/root/.cache/astropy`), recorded by
size and hash:

| file | bytes | sha256 |
|---|---|---|
| DE421 (JPL planetary ephemeris, 1900–2050) | 16,788,480 | a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc |
| DE440 (successor ephemeris, 1550–2650)     | 119,799,808 | a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5 |

Discovery recorded on the way: astropy 8's shorthand
`solar_system_ephemeris.set('de421')` currently 404s (its hardcoded URL
rotted), while **PINT's own loader**
(`pint.solar_system_ephemerides.load_kernel('de421')`) succeeded — so
PINT's loader is the blessed acquisition path, and it is also the code
path Spec 9/E4 actually exercise. Astropy 8 keeps its cache under
`~/.cache/astropy` (the old `~/.astropy` path is empty — noted so nobody
"cleans up" the wrong directory).

Remaining determinism items EXECUTED AT THE SPEC 9 CARD (this file just
pins the policy): pin the ephemeris NAME per test (`ephem="DE421"` explicit
in code, never a default); freeze PINT's auto-updating observatory clock
files at known versions with auto-update disabled for tests, so a clock
re-download can never change a blessed phase.

## 4. How to rebuild this environment from scratch

```
wsl --install -d Ubuntu-24.04        # only if the distro is absent
wsl -d Ubuntu -u root -- bash -lc "apt-get update && apt-get install -y python3-venv python3-pip"
wsl -d Ubuntu -u root -- bash -lc "mkdir -p /opt/galnav && python3 -m venv /opt/galnav/venv"
wsl -d Ubuntu -u root -- bash -lc "/opt/galnav/venv/bin/python -m pip install -U pip"
wsl -d Ubuntu -u root -- bash -lc "/opt/galnav/venv/bin/python -m pip install -r /mnt/c/Users/rudra/OneDrive/Desktop/spacenav/requirements-armor.txt"
wsl -d Ubuntu -u root -- bash -lc "/opt/galnav/venv/bin/python -c \"from pint.solar_system_ephemerides import load_kernel; load_kernel('de421'); load_kernel('de440')\""
```

Then verify the GO/NO-GO probe prints `eps 1.084...e-19` and
`check_longdouble_precision() == True`.

## 5. How armor code is invoked, and the wall between the suites

Every armor command runs as:

```
wsl -d Ubuntu -u root -- /opt/galnav/venv/bin/python <script or -m pytest ...>
```

The repo is visible inside WSL at
`/mnt/c/Users/rudra/OneDrive/Desktop/spacenav`.

Armor tests will live in `tests_armor/` (separate root, created at Spec 9)
and are run ONLY inside this environment. They are deliberately NOT under
`tests/`, because the spine's definition of done is `pytest -q` fully green
with **zero skips** on native Windows — armor tests on Windows would have
to skip, and this project does not ship skipping tests. One suite per
environment, each fully green where it lives.

## 6. What this environment does NOT do

It does not run, test, or re-bless any spine code or number. It adds no
package to the spine env (`requirements.txt` untouched). It does not touch
the truth wall (armor experiments obey the same wall rules as everything
else). And nothing in it is load-bearing for the six blessed experiments —
if this environment vanished tomorrow, E1–E7 would still reproduce
bitwise on the spine.
