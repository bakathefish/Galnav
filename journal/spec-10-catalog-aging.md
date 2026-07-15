# Journal Entry — Spec 10: Catalog Aging Propagator (stars that move)

## The one-sentence purpose

E6 — the project's headline experiment, "how does navigation accuracy decay
as the star catalog ages?" — needs stars that MOVE. This card builds the
deterministic engine that moves them: a straight-line, constant-velocity
propagator, written INDEPENDENTLY on both sides of the truth wall. The
truth side moves the true sky; the navigator ages its public catalog with
the catalog's own quoted motions. Nothing random happens yet — that is E6.

## Why a star moves in our model, one symbol at a time

A star is not nailed to the sky. It drifts, because it has a real velocity
through space. We split that velocity into two pieces we can read off the
catalog:

- **Radial velocity `v_r`** (km/s): how fast the star moves straight toward
  or away from us. Gaia measures this for most stars (it is the
  `radial_velocity` column). 554 of our 1941 stars have no measured RV —
  more on that below.
- **Proper motion** (`pmra`, `pmdec`, in milliarcseconds per year): how
  fast the star slides ACROSS the sky, in the two sky directions (east =
  increasing right ascension, north = increasing declination).

The full 3-D velocity is

    v = v_r * u_hat  +  v_t

where every symbol is:

- **`u_hat`** — the unit arrow pointing from us toward the star, built the
  project's one way (`radec_to_unit`): `u_hat = (cos d cos a, cos d sin a,
  sin d)` with `a` = right ascension, `d` = declination.
- **`v_t`** — the transverse (across-the-sky) velocity:

      v_t = d * ( pmra* · e_east  +  pmdec · e_north )     [see units below]

  - **`d`** — the star's distance (au), from its parallax.
  - **`e_east = (-sin a, cos a, 0)`** — the unit arrow pointing east along
    the sky at the star.
  - **`e_north = (-sin d cos a, -sin d sin a, cos d)`** — the unit arrow
    pointing north. Together with `u_hat`, these three arrows are mutually
    perpendicular and each has length 1 (checked by hand: every dot product
    between them is zero, every self-dot is one). They are built to match
    `radec_to_unit`'s convention exactly — `e_north` is literally the
    derivative of `u_hat` with respect to declination, and `e_east` is the
    derivative with respect to right ascension divided by `cos d`.

### The one convention that will bite you if you get it wrong (D3)

Gaia's `pmra` column is **not** the raw rate of change of right ascension.
It is already multiplied by `cos(dec)`: the archive documents it as
`pmra = pmra* = mu_alpha* = mu_alpha · cos(dec)` (citation **[GaiaPM]**).
That cos(dec) turns "degrees of RA per year" (which are shorter near the
poles) into a true on-sky angular rate. **So we use `pmra` directly as the
coefficient of `e_east`, with NO extra cos(dec) factor.** Multiplying by
cos(dec) a second time is the single most likely bug on this card, and test
T3 is built specifically to catch it (see below).

### The units, spelled out so nothing is hidden

`pmra`, `pmdec` arrive in **mas/yr**. `d` is in **au**. `v_r` is in
**km/s**. To add the transverse and radial pieces they must share units
(km/s):

1. Convert the proper motions mas/yr → **rad/yr** with `units.mas_to_rad`.
2. `d (au) * pm (rad/yr)` = a transverse speed in **au/yr** (an angle times
   a radius is an arc length; over a year, a distance).
3. Convert au/yr → **km/s** with the new constant `KMS_PER_AU_YR` (below).

## Moving the star forward in time (D2)

The propagator itself is the simplest possible law of motion — a straight
line at constant velocity:

    r(t0 + T) = r(t0) + v * T

- `r(t0)` — the star's position at the catalog epoch (J2016.0), au.
- `v` — the velocity vector above, converted from km/s to **au/yr** by
  dividing by `KMS_PER_AU_YR`.
- `T` — how many **Julian years** we age the catalog.

**What this straight line quietly gets RIGHT.** You might expect a star's
apparent path across the sky to curve over time ("perspective
acceleration"), and that we would be neglecting it. We are not. Perspective
acceleration is entirely an artifact of describing straight-line motion in
sky angles; in the honest 3-D Cartesian picture the motion is exactly a
straight line, and this propagator reproduces it **exactly**. There is no
approximation here to bound.

**What this straight line genuinely does NOT model** (and why that is fine
for <=200 years at <=20 pc):

- **Galactic / gravitational acceleration** — the slow bending of the
  star's path by the Galaxy's gravity. Over a couple of centuries this
  changes a nearby star's velocity by a negligible fraction.
- **Light-travel-time change** — as a star's distance changes, the light we
  see left it at a slightly different time. A second-order effect at these
  distances and timescales.
- **All stochastic degradation** — proper-motion measurement error,
  modeling the missing radial velocities as a ~30 km/s population, binary
  wobble. These are the *whole point of E6* and are deliberately absent
  here. This card is the clean deterministic skeleton E6 will add noise to.

## The three new pieces in `units.py` (the one shared module)

The truth wall says truth and nav share no code — **except** unit
conversions, which live in `galnav/units.py` and nowhere else. Three
additions, each derived from already-cited constants, never typed as a raw
decimal:

- **`arcsec_to_rad(x)` = `deg_to_rad(x / 3600)`** — 1 arcsec = 1/3600 degree
  (exact).
- **`mas_to_rad(x)` = `arcsec_to_rad(x / 1000)`** — 1 mas = 1/1000 arcsec
  (exact). Feeding a mas/yr value returns rad/yr.
- **`KMS_PER_AU_YR` = `AU_KM / (365.25 * 86400)`** — how many km/s equal one
  au/year. `AU_KM` km per au ([IAU12]) divided by the seconds in one Julian
  year (365.25 days x 86400 s, citation **[JY]**). Value **4.740470...**
  km/s per au/yr. Used to move between the catalog's km/s kinematics and the
  au/yr displacements the propagator adds.

**Note for the students (this card FORCES an open decision).** Whether
`units.py` should own mas/arcsec→radian helpers has been an OPEN item since
Spec 3 (the logbook's ratification list, item (f)): tests were converting
mas inline. This card needed those helpers to build proper-motion
velocities, so it **makes the decision**: the helpers now live in
`units.py`, the module the rulebook says owns every conversion. Ratify or
overturn this as part of item (v).

## Independent implementations, and what that buys us

Following the aberration card's precedent, the truth-side kinematics
(`galnav/truth/sky.py`) and the nav-side kinematics
(`galnav/nav/catalog.py`) are written **separately** — different code,
different operation order — sharing only `units.py`. For example the truth
side computes `d * (...) * KMS_PER_AU_YR` while the nav side computes
`(d * KMS_PER_AU_YR) * (...)`; both are correct, and they agree to about 12
digits rather than bit-for-bit precisely because the float operations are
ordered differently. That non-identical-but-agreeing behavior is the *point*
— it is evidence the two were written independently, not copy-pasted.

**The load-bearing caveat (stated plainly, as the aberration card did with
its SR oracle).** Test T4 checks the two implementations agree. But two
implementations that share the *same wrong convention* would agree with
each other and still be wrong. Agreement is therefore NOT the safety net for
"is the physics right?" — that job is carried by the **external oracles**:
T2 (an independent 30 km/s → 6.33 au/yr radial-drift number) and T3 (an
exact-by-definition 1 au/yr tangential drift that a spurious cos(dec) would
break). T4 only catches a *divergence* between the two code paths.

## The missing radial velocities (D4)

554 stars have no Gaia radial velocity (their `radial_velocity` is NaN). If
we multiplied NaN by anything the NaN would spread into the velocity and
then into every propagated position. So the velocity-construction function
takes a **required** argument `rv_fill_kms` (no default): the caller MUST
state what radial velocity to assume for RV-less stars. We give it no
default on purpose — the real modeling choice (E6 will draw a ~30 km/s
population; the truth side there will use sampled/true RVs, not a constant
fill) is E6's to make, and a silent default would hide that decision. The
proper motions `pmra`/`pmdec`, by contrast, are present for **every** star
(verified: all 1941 finite), and `load_catalog` now raises if that ever
stops being true — the propagator's "no NaN out, given a fill" guarantee
depends on it.

## Every tolerance touched, and why that exact value

- **T1 (zero-age identity): NO tolerance — exact equality.** Propagating 0
  years must return the starting positions bit-for-bit (`np.array_equal`).
  It can, because `r + v*0 = r + 0 = r` exactly in floating point for finite
  `v` (which is why T1 fills the NaN RVs first — `NaN*0` would be `NaN` and
  break identity spuriously).
- **`SPEC10_DRIFT_REL_TOL = 1e-3` (T2).** The project plan (section 6, the
  Spec 10 line) says the radial-drift check must agree "within 0.1%". 1e-3
  is that 0.1%, no more, no less. **HONESTY NOTE the card demands:** the
  measured drift for 30 km/s over one Julian year is **6.328486 au**, versus
  the 3-significant-figure oracle `RV_DRIFT_AU_PER_YR_AT_30KMS = 6.33`. The
  relative gap is 0.000239 (**~4.2x inside** the 0.1% gate — the gate's
  looseness is simply the oracle's 3-sig-fig rounding). Crucially, this
  coarse gate does **not** pin the Julian-vs-calendar-year convention: a
  365-day year would give 6.3241 au, a 0.094% gap, which *also* squeaks
  inside 0.1%. What actually pins "365.25 days" is `KMS_PER_AU_YR`'s
  derivation from the cited [JY] constant in `units.py` — a code-review
  fact, not a test the T2 gate could enforce. Said plainly so no one
  mistakes T2 for a proof of the year length.
- **Reused `ANGLE_TOL_RAD = 1e-12` (T3, T4, T5).** These are
  exactness/agreement checks — "is this exactly 1.0?", "do the two
  implementations agree?", "does the code match the hand computation?" — at
  the float64 rounding scale. Rather than invent a new constant (the card
  forbids it, and adding one is a locked-file action), they reuse the
  project's existing 1e-12 machine-precision bar, `ANGLE_TOL_RAD`. It is
  named for angles, but its VALUE is the project's canonical "equal up to
  float64 dust" threshold, and that is exactly the role here. Flagged for
  ratification (item (v)) so the students can bless or rename the reuse.

## The tests, and what each would catch if the code were wrong

All six live in `tests/test_spec10_aging.py`.

- **T1 — zero-age identity, both sides, exact.** Catches any propagator that
  adds a nonzero baseline, scales wrongly at `T=0`, or lets a NaN through.
- **T2 — radial drift vs the golden number.** A star with pure 30 km/s
  radial velocity drifts 6.33 au in a Julian year, along the line of sight.
  Catches a wrong km/s↔au/yr conversion, a wrong year length beyond ~0.1%,
  or radial motion pointed the wrong way. (Its external oracle is what makes
  it more than a tautology.)
- **T3 — tangential drift is exactly 1 au/yr.** 1 arcsec/yr of proper motion
  at 1 pc must move a star exactly 1 au in a year — the parallax triangle,
  `AU_PER_PC = 648000/pi`, makes the conversion cancel to 1.0. The star sits
  at **dec = 60°** on purpose: with `pmdec = 0` the transverse speed is
  `d·pmra*` regardless of declination, so a bug that multiplied by an extra
  `cos(dec)` would give `cos 60° = 0.5` au/yr — a hard, unmissable failure —
  whereas at dec = 0 the bug would hide (cos 0 = 1). **And ra = 90°** is
  chosen so the drift is numerically clean: there the east direction is
  `(-1,0,0)`, so the 1-au motion lands entirely in x while the star's x
  position starts near zero — so measuring the drift as
  `|propagate(pos) - pos|` recovers ~1 au against a near-zero baseline
  instead of subtracting two ~1-parsec (2e5 au) numbers, which would lose
  ~11 digits and blow past the 1e-12 bar. (That cancellation is real: the
  naive ra = 45° version measured 1.0 + 7.9e-12, failing honestly, and
  drove this geometry choice.)
- **T4 — the two implementations agree to 1e-12 on the real catalog.**
  Catches a transcription divergence between the truth-side and nav-side
  kinematics (a swapped basis vector, a dropped factor on one side). Cannot,
  by construction, catch a shared wrong convention — that is T2/T3/T5's job.
- **T5 — velocity construction + no NaNs.** (a) Building velocities for the
  whole catalog with an explicit `rv_fill` yields zero NaNs, proving the 554
  RV-less stars are handled. (b) A single star at dec = 60° reproduces a
  velocity vector computed by hand, symbol by symbol, in the test — catching
  a wrong basis, a missing distance factor, or a unit slip.
- **T6 — vectorization shapes.** Positions `(N,3)`, velocities `(N,3)`, and
  a scalar OR `(A,)` array of ages go through with no Python loop over stars
  or ages; a scalar age returns `(N,3)`, an array returns `(A,N,3)`, and
  slice `a` of the array result equals the scalar call at `ages[a]`
  bit-for-bit. Catches a broadcasting bug or an accidental per-star loop.

## The golden constant this card could NOT add itself (must read)

Test T2 needs `SPEC10_DRIFT_REL_TOL = 1e-3` in `tests/golden_numbers.py`.
That file is deny-locked and the rulebook says never to edit it; the
project's override procedure is a **student (human)** action. In this build
session the instruction to add it came from an agent, and this assistant is
constrained from changing its own permission configuration or editing the
golden file on an agent's authorization. **So the constant was NOT added
here.** Everything else is complete and verified: with the constant injected
in memory, all six tests pass; without it, T2 is the only red (an
ImportError isolated to T2, so T1/T3/T4/T5/T6 run and pass now). The exact,
ready-to-paste addition — for a human to apply under the recorded override
procedure — is:

```python
# --- Spec 10 catalog-aging gate (plan section 6: "within 0.1%") ----------
# The deterministic radial-drift check (T2) compares 30 km/s over one Julian
# year against RV_DRIFT_AU_PER_YR_AT_30KMS = 6.33 au. Measured 6.328486 au;
# gap 0.000239 relative, ~4.2x inside this gate. The gate is the plan's own
# 0.1% and is loose only because the 6.33 oracle carries 3 significant
# figures; the Julian-year length itself is pinned by KMS_PER_AU_YR's [JY]
# derivation in units.py (code review), not by this gate.
SPEC10_DRIFT_REL_TOL = 1e-3
```

## Where this sits in the project, and what's next

With this card, the deterministic half of the catalog-aging machinery
exists on both sides of the wall: truth can move the real sky, the navigator
can age its catalog, and the two agree. **E6** is next: it makes the aging
*stochastic* — perturbing catalog positions by their proper-motion errors,
modeling the 554 missing radial velocities as a real ~30 km/s population,
and then running the E1-style solver against a catalog that is deliberately
wrong, to measure how navigation accuracy decays with catalog age. This card
is the clean skeleton that experiment hangs its noise on.

## Process note (honest disclosure)

Under the project's recorded exception, this card's text and its six
acceptance tests were **AI-authored**; the standing "students write the
tests" rule is set aside for THIS CARD ONLY and remains in force otherwise.
**Student review and ratification are pending** — logbook checklist item
**(v)**, which also covers the dec = 60° / ra = 90° test-geometry choices,
the `units.py` mas/arcsec-helper decision this card forced, and the reuse of
`ANGLE_TOL_RAD` as the 1e-12 exactness bar.
