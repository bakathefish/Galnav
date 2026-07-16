# E3 — Real New Horizons navigation by line-of-position triangulation

Written 2026-07-16. AI-authored under the build-night ratification-pending
pattern (user granted full build authority 2026-07-16). Built in two parts in
one session: the navigator core + exact synthetic tests
(`galnav/nav/triangulate.py`), then the real-data experiment
(`experiments/e3_new_horizons.py`) that recovers New Horizons from Lauer et al.
2025's real LORRI star measurements and confirms the fix against the JPL
ephemeris. Both parts are complete and green.

## Where this sits in the project

E1 and E6 are simulation results. E3 is the REAL-DATA anchor: it uses actual
New Horizons photographs of two nearby stars (Proxima Centauri, Wolf 359) to
fix the spacecraft's 3D position, and checks it against the JPL Horizons
ephemeris. Lauer et al. (2025, AJ 170, 1) did this: their recovered position
MISSED the JPL truth by 0.351 au, inside a 1-sigma error ellipsoid with
semi-axes 0.441 x 0.233 x 0.206 au (a 0.94-sigma agreement). IMPORTANT: the
widely quoted "0.44 au" is the LARGEST ELLIPSOID SEMI-AXIS (the uncertainty),
NOT the miss distance (0.351 au) -- plan section 12 conflates the two, and our
journal/figure must keep them distinct or a reader of Lauer will catch it. Our
job is to re-derive their navigation INDEPENDENTLY and confirm it. This turns
"our simulator says X" into "and here it is on a real spacecraft's photos."

This navigator is DIFFERENT from E1's Gauss-Newton pair-angle solver. There we
measured angles BETWEEN pairs of stars; here we measure the DIRECTION to each
star and intersect lines of position.

## The method, one symbol at a time

Each star `i` sits at a known 3D position `p_i` (au, barycentric). From the
spacecraft it is seen in a measured unit direction `d_i`. So the spacecraft
must lie somewhere on the line through `p_i` pointing along `d_i` — its "line
of position." With two or more stars, the lines intersect at the spacecraft.

The maximum-likelihood position minimises the summed squared PERPENDICULAR
distances from `x` to all `N` lines. The perpendicular part of a vector is
taken by the projector onto the plane orthogonal to `d_i`:

    q_i = I - d_i d_i^T          (3x3, symmetric; q_i d_i = 0)

- `I` = 3x3 identity.
- `d_i d_i^T` = outer product; subtracting it removes the component along `d_i`.
- `q_i v` = the part of `v` perpendicular to the line direction.

Weighting each star by inverse-square distance (a distant star's transverse
position error grows with distance, so trust it less):

    w_i = q_i / |p_i|^2          (weighted)   or   w_i = q_i   (unweighted)

The position that minimises `sum_i (x - p_i)^T w_i (x - p_i)` solves the normal
equations `(sum_i w_i) x = sum_i w_i p_i`, i.e.

    x = (sum_i w_i)^{-1} (sum_i w_i p_i)

- `x` = spacecraft position, au.
- `xcov = (sum_i w_i)^{-1}` = the unscaled covariance; multiplied by the
  per-measurement angular variance it gives the position error in au^2.
- `chi2 = sum_i (x - p_i)^T w_i (x - p_i)` = the residual; ~0 when the lines are
  exactly consistent.

This is exactly the closed-form solver `n_star_solve` in Lauer et al.'s
notebook (`data/e3_new_horizons/repo/nhparallax.ipynb`, [Lauer25-data]),
re-implemented here from the formula, not copied.

## What the code does — and does NOT do

DOES: `galnav/nav/triangulate.py::n_star_solve(star_pos_au, directions_unit,
weighted=True)` returns `(x, xcov, chi2)` for N >= 2 stars in one closed-form
solve (no iteration). It lives on the NAV side and imports only numpy —
truth-wall clean.

Does NOT (this increment): load the real data, extract the measured directions
from the images, or produce the New Horizons fix / figure — that is E3 part 2.
It also does not model measurement noise or reject outliers (two-star fixes
have no redundancy to reject with); it does not iterate (the problem is linear
once directions are fixed); and it does not choose the star catalogue or frame
(the caller supplies `p` in the frame it wants `x` in).

## Tolerances — and why each is what it is

The four SYNTHETIC tests here introduce no new tolerance: they assert exact
recovery to the FROZEN golden `SOLVER_RECOVERY_TOL_AU = 1e-8` au — the same
"noiseless recovery to machine precision" gate the Gauss-Newton solver uses.
It is appropriate because, with exactly consistent directions, the closed-form
solve returns the true position up to rounding dust (measured ~1e-11 au at the
tested geometry); a wrong projector, weight, or normal-equation sign misses by
astronomical amounts. These four tests PROVE the algorithm exactly.

The real-data test lives in part 2 and needs ONE new golden,
`NH_NAV_TOL_AU = 3.0` au (authorized override #9, the plan section-7 E3 pass
gate). It gates the full-pipeline miss: our galnav path (CSV -> select stars by
source_id -> propagate J2016 -> image epoch -> `n_star_solve` on the measured
directions) must land within `NH_NAV_TOL_AU` of the JPL truth (measured miss
~0.347 au, comfortably inside 3 au). REPORTED but NOT gated (journal + figure):
the miss distances (0.347 ours / 0.346 our-propagation / 0.351 Lauer x60), the
1-sigma error ellipsoid (0.441 x 0.233 x 0.206 au), and the astrometric sigma
rmssig = 0.44". A separate cross-check reproduces the notebook's published `x2`
by feeding our solver Lauer's own inputs — it matches to ~0.006 au (that
residual is the 8-digit rounding of the extracted fixtures, NOT algorithm
error; the algorithm is already proven exactly by T1/T2), so it is reported,
not gated at 1e-8. The famous "0.44 au" is the ellipsoid semi-axis; the miss is
0.351 au — kept distinct throughout.

## Every test and what it would catch

`tests/test_e3_triangulation.py`, six tests:
- **T1 three-star exact recovery** — recovers a known position to
  `SOLVER_RECOVERY_TOL_AU`; checks `xcov` shape and near-zero `chi2`. Catches
  any error in `I - d d^T`, the `1/r^2` weight, the normal equations, or the
  solve.
- **T2 two-star exact recovery** — the New Horizons fix uses exactly two stars,
  so the two-line intersection must be exact. Documents the near-parallel
  silent-garbage failure mode (the real pair is 80.6 deg apart, well
  conditioned). Catches a solver that silently needs N >= 3.
- **T4 weighted/unweighted + covariance PSD** — both weightings recover exact
  data; `xcov` symmetric (to rounding) and positive-definite.
- **T5 determinism** — identical inputs give bit-identical outputs.
- **T3 real-data pipeline (THE ANCHOR)** — our full galnav pipeline recovers the
  REAL New Horizons position within `NH_NAV_TOL_AU` = 3.0 au of JPL. Catches a
  broken pipeline, a missing/incorrect epoch propagation (unpropagated lands
  ~30 au off), or a truth leak.
- **T6 reproduction cross-check** — fed Lauer's own inputs, `n_star_solve`
  lands within `NH_NAV_TOL_AU` of both his `x2` and JPL (coarse wiring guard;
  the precise ~0.006 au match is reported, not gated).

## Part 2 — the measured real-data result (2026-07-16)

Design-reviewed and APPROVED WITH AMENDMENTS; all amendments folded in.
`experiments/e3_new_horizons.py` runs two computations, both truth-wall clean
(`n_star_solve` never sees the JPL state — it enters only the scoring):

- **OUR PIPELINE (gated).** Load our Gaia DR3 catalogue, select Proxima +
  Wolf 359 by `source_id` (a small helper re-reads that column, which
  `load_catalog` drops), propagate J2016.0 -> the mean image epoch
  (JD 2458962.25, age **4.3087 yr**) with `galnav/nav/catalog.py`
  `star_velocities_kms` + `propagate_positions_au` (MANDATORY — unpropagated
  the miss is ~30 au), then triangulate on Lauer's measured directions.
  MEASURED MISS vs JPL: **0.347 au**, ~8.7x inside the 3 au gate. Wolf 359 has
  no RV in our catalogue; filled with the Simbad value (19.57 km/s) Lauer used
  (rv_fill = 0 shifts the miss ~0.03 au — documented, not material).
- **REPRODUCTION (reported).** Fed Lauer's own propagated positions +
  directions, our `n_star_solve` reproduces his recovered `x2` to **0.0065 au**
  (that residual is the 8-digit rounding of the extracted fixtures; the
  algorithm itself is proven exactly by T1/T2). Its miss vs JPL is 0.346 au.

REPORTED, not gated: the **0.351 au miss** (Lauer's 12-line `x60`), the 1-sigma
error ellipsoid **0.441 x 0.233 x 0.206 au** (Lauer's `x60`, `x60cov` scaled by
rmssig = 0.44"; our 2-star `x2` ellipsoid is looser, ~1.08 au, as expected from
2 vs 12 lines). The famous "0.44 au" is the ellipsoid semi-axis; the miss is
0.351 au — kept distinct. FLAGGED as a v1.1 refinement: full `x60` reproduction
needs the 12 per-image directions (extract from notebook cells 4-5); we quote
Lauer's `x60` ellipsoid rather than recomputing it. Aberration: the published
directions are Gaia-frame plate solutions, so bulk aberration cancels (no
correction applied, matching notebook cell 12); the deferred raw-FITS pipeline
would need to plate-solve against Gaia.

## What comes next

E3 v1.1: reproduce the 12-line `x60` solve + recompute the ellipsoid from the
per-image directions. Then E2 (convergence basins), the pulsar closest-vector
solver, and the armor experiments, in that order.
