# Journal Entry — E6a: the truth-side sampled sky

## The one-sentence purpose

The headline experiment E6 ("how does navigation decay as the catalog
ages?") is only meaningful if the TRUE sky differs from the public catalog.
Until now it did not — truth used the catalog's central numbers as exact
truth, so aging a perfect catalog cost nothing. This card builds
`galnav/truth/sampling.py::sample_true_skies`, which draws many true skies by
scattering each star's parallax, proper motion, and radial velocity by the
error bars Gaia quotes — and, most importantly, gives the 554 stars with no
catalog radial velocity a real ~30 km/s motion the navigator cannot see.

## What gets sampled, one symbol at a time

For each trial and each star we draw independent standard normals `z` (mean
0, standard deviation 1) and shift the catalog value by its error bar:

- **Parallax:** `plx_sampled = plx + sigma_plx * z`. We sample in PARALLAX
  space, not distance space, because Gaia fits the parallax and quotes a
  Gaussian error on IT; the distance `d = 1/parallax` is a derived,
  non-Gaussian quantity. Distance then comes from
  `parallax_mas_to_dist_au(plx_sampled)`.
- **Proper motion:** `pmra_sampled = pmra + sigma_pmra * z`,
  `pmdec_sampled = pmdec + sigma_pmdec * z`, each component its own
  independent draw. (`pmra` is Gaia's `pmra* = mu_alpha·cos(dec)`, cos(dec)
  already inside — the Spec 10 convention, unchanged.)
- **Radial velocity — the important one:**
  - stars WITH a catalog RV: `rv_sampled = rv + sigma_rv * z` (scatter around
    the measured value);
  - stars WITHOUT one (554 of 1941): `rv_sampled = missing_rv_scale_kms * z`
    — a **zero-mean** draw at the caller's scale (E6 uses 30 km/s, plan
    section 7). Zero-mean because the navigator's only sane guess for an
    unknown RV is 0, so truth scatters the real RV symmetrically around what
    the navigator will assume. This is the term that makes catalog aging
    bite: an unmodeled 30 km/s drifts a star **633 au in 100 years** (see
    the magnitudes below).

The sampled position at the catalog epoch is `u_hat * d_sampled` (the
direction `u_hat` is NOT resampled — see below), and the sampled velocity is
built by the same truth-side `star_velocities_kms` used in Spec 10, now fed
the sampled kinematics.

`sample_true_skies` returns two `(n_trials, N, 3)` arrays — positions (au) and
velocities (km/s) — at the epoch. E6b will propagate each trial forward by
the cell's age with the Spec 10 straight-line propagator.

### Determinism and the fixed draw order

All randomness flows through the passed `rng` (no global seed). The four `z`
streams are drawn in a FIXED order — parallax, pmra, pmdec, rv, each shape
`(n_trials, N)` — so one seed reproduces the sky exactly. Test T3 relies on
this: it redraws the same stream in the same order and reconstructs the sky
bit-for-bit.

## What this does NOT model — with the magnitudes MEASURED, not asserted

The card calls several skipped terms "negligible." Negligible is a
measurement, not an opinion, so here are the actual numbers (computed over
the 20 nearest stars — the Bailer-Jones anchor set E6 uses — from the real
catalog; script in the session scratch, evidence in the logbook):

| skipped term | measured magnitude | vs the missing-RV term |
|---|---|---|
| ra/dec angle-error position shift | 4.5e-5 – 2.9e-4 au (median 9.1e-5 au) | ~7 orders below |
| proper-motion-error aging, 100 yr | 7.2e-3 – 4.6e-2 au (median 1.4e-2 au) | ~4–5 orders below |
| missing-RV drift, 100 yr @ 30 km/s | 632.8 au | — (the driver) |

The missing-RV term is **~4.4e4×** the median PM-error aging term over 100
years — about four to five orders of magnitude. That single ratio is why the
missing radial velocities, not the sampled measurement errors, dominate
catalog aging, and why the skipped terms are honestly negligible rather than
conveniently ignored.

Two more skipped things, measured:

- **The ra/dec direction is not resampled at all.** The angle errors are
  ~0.02–0.05 mas; the transverse position they would move a nearby star is
  the ~1e-4 au in the table, three to four orders below the parallax term —
  so `u_hat` is treated as exact and only the distance along it is sampled.
- **The parallax → distance skew (Jensen / Lutz–Kelker).** Because
  `d = 1/parallax` is convex, the mean sampled distance is inflated by about
  `(sigma_plx/plx)^2` relative to `1/plx_central`. Measured across the whole
  catalog: **median 1.6e-7**, worst-case **3.9e-3** (0.4%, at the single star
  with the smallest parallax_over_error, ~16). This is not a bug — it is the
  physically correct consequence of sampling where the error actually is
  (parallax); recorded so the students know its size. Cite: this
  parallax-vs-distance asymmetry is [BJ15].

## Why independent Gaussians are honest here (the correlation note)

Gaia quotes a pmra/pmdec correlation of ~0.63 for many stars, and other
correlation coefficients too; v1 ignores all of them and samples independent
Gaussians. Two reasons, both recorded:

1. The pmra/pmdec cross-term rides the tangent basis vectors `e_east` and
   `e_north`, which are **orthogonal** (`e_east · e_north = 0`), so the
   correlation does not couple into the quantities that matter the way a
   naive fear would suggest (reviewer-verified).
2. More decisively, the ENTIRE proper-motion aging budget is ~4–5 orders
   below the missing-RV term (the table above). A correlation correction to a
   term that is already 40,000× too small to matter cannot change any E6
   conclusion.

So independent Gaussians are not a corner cut — they are honest at this
card's precision. It is still flagged for ratification (item (w)) so the
students own the simplification.

## The one code change outside the new module (amendment 3)

`sample_true_skies` needs to build velocities for `(T, N)` sampled kinematics,
so the truth-side `star_velocities_kms` was generalized to accept leading
batch dimensions — the ONLY change is `[:, None]` → `[..., None]`, which is a
no-op for 1-D arrays. Amendment 3 required proving the unbatched `(N,)` path
is bitwise unchanged. It is: the generalized function on the real catalog
matches the array HEAD produced with **`array_equal = True, max|diff| = 0.0`**
(scratch capture before the edit, compared after), and test T5 re-proves it
in the suite against an inline copy of HEAD's exact `[:, None]` body.

## The guard (amendment 1)

If any sampled parallax comes out `<= 0`, `sample_true_skies` raises
`ValueError` — `d = 1/parallax` would be non-physical. Our subset has
parallax_over_error > 10 (measured minimum ~16), so a non-positive draw is
astronomically unlikely (a >16-sigma excursion) and the guard should never
fire in practice; it exists so a future, looser catalog cannot silently
produce garbage distances. Stated in the docstring, as the card requires.

## Every tolerance touched, and why (there are none)

**No new golden numbers, and no tolerances at all.** Every test is a
bit-exact identity:

- T1 uses `x + 0*z == x` (IEEE754 exactness with zeroed errors).
- T3 and T4 redraw the same rng stream and reconstruct the sampled sky from
  the documented formula, asserting `np.array_equal` — deterministic
  exactness in place of a statistical gate.
- T5's "unchanged vs HEAD" is `np.array_equal` against HEAD's own formula.

That is the cleanest possible outcome: `tests/golden_numbers.py` was not
touched, no override was needed.

## The five tests, and what each would catch

All in `tests/test_e6_sampling.py`.

- **T1 — zero-error identity.** Zero all error columns, keep every RV: each
  sampled sky must equal the deterministic epoch sky bit-for-bit, the same
  for every trial. Catches a sampler that shifts the central value, mis-adds
  the error, or corrupts the "no error → no change" contract.
- **T2 — determinism.** Same seed → bitwise-identical output; different seed →
  different. Catches a global-seed leak or a non-reproducible draw.
- **T3 — exact reconstruction oracle.** Redraw the same rng stream in the
  documented order, rebuild parallax/pm/rv and the sky from the formula, and
  assert bit-equality. Catches a wrong draw order, a wrong error column, a
  parallax-vs-distance-space mistake, or a broadcasting slip — anywhere the
  module deviates from the documented formula.
- **T4 — missing-RV policy.** A finite-RV star and a missing-RV star:
  the missing star must get `missing_rv_scale·z` (zero-mean, genuinely
  scattered, NOT a constant fill), the finite star `rv + sigma_rv·z`, and
  NOTHING may come out NaN. Catches a NaN leak from the 554 RV-less rows or
  the wrong branch.
- **T5 — shapes + unbatched path unchanged.** `(T, N, 3)` outputs, all finite,
  no Python loop over trials or stars; and the `(N,)` velocity path is
  bit-for-bit HEAD (amendment 3). Catches a shape/broadcast bug or a
  regression in the generalized builder.

## What is deferred (prominent flags for the students)

- **Binary-companion contamination** is NOT in this card. The plan gives an
  amplitude anchor (200 mas wobble at 5 pc = 1 au) but NO contaminated
  fraction. Inventing a fraction without a citation would be fake science, so
  it is deferred: the students must source a contaminated fraction before any
  binary-sensitivity panel.
- **Correlations** (pmra/pmdec 0.63 and the rest): independent Gaussians in
  v1, justified above; ratification item (w).
- **ra/dec resampling:** skipped (magnitude measured above); ratification
  item (w).

## Where this sits, and what's next

This is the truth-side half of the E6 machinery: it makes the true sky
genuinely differ from the public catalog by the cataloged uncertainties plus
the unmodeled radial velocities. **E6b** (the headline experiment) consumes
it: for each (catalog age, sensor precision) cell it will sample true skies
here, propagate them with the Spec 10 truth-side propagator, generate
measurements, and run E1's navigator against the aged PUBLIC catalog — mapping
where aging, not the sensor, limits navigation.

## Process note (honest disclosure)

Under the recorded exception, this card's text and its five acceptance tests
were AI-authored; the students-write-tests rule is set aside for THIS CARD
ONLY and remains in force otherwise. Student review and ratification are
pending — logbook checklist item **(w)**, covering the independent-Gaussian
simplification, the skipped ra/dec sampling, the deferred binary fraction,
and the missing-RV zero-mean policy.
