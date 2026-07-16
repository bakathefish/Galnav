# E3 dataset — New Horizons interstellar navigation (Lauer et al. 2025)

Real-spacecraft data for Experiment E3: recover the 3D position of the New
Horizons spacecraft from optical images of two nearby stars, and compare to the
JPL Horizons ephemeris. This is the project's real-data anchor.

## Provenance

- **Paper:** Lauer, T. R., Munro, J., Spencer, J., et al. (2025). "A
  Demonstration of Interstellar Navigation Using New Horizons." *The
  Astronomical Journal*, 170, 1. arXiv:2506.21666. Citation key `[Lauer25]`.
- **Data deposit:** Zenodo, **doi:10.5281/zenodo.15359866** (record 15359866).
- **License:** MIT — "Anyone is free to use either the code or the data however
  they wish" (repo `README.txt`). Redistribution is permitted; we do NOT vendor
  the 147 MB of raw data into git (it is re-fetchable from the immutable DOI).
- **Retrieved:** 2026-07-16 for GalNav, via `fetch_e3_data.py` (stdlib + git).

## How to get the data (it is git-ignored)

```
python data/e3_new_horizons/fetch_e3_data.py
```

This downloads three Zenodo files and `git clone`s the bundle into `./repo`.
`nh2025aphj.bun` is a **git bundle** (magic bytes `# v2 git bundle`), not a
tarball — cloning it reconstructs Lauer's full analysis repo.

## What is in `repo/` after fetching

- **12 New Horizons LORRI FITS** `lor_04498*_0x633_pwcs2.fits` — Proxima Cen
  (two epochs x 3) and Wolf 359 (two epochs x 3), taken 2020-04-23 at 47.1 au.
  NOTE (repo README): the FITS header WCS was NOT used by Lauer — they
  recalibrated astrometry from Gaia DR3; the recalibrated star positions live
  in the notebook as data loads.
- **2 Earth-based FITS** `lco_prox_*.fits`, `wolf359_*.fits` — the parallax
  comparison images.
- **`nearby100.txt`** — the 100 nearest stars (SIMBAD; plx > 100 mas, V <= 15),
  columns: okay(1=nav candidate,0=binary), oid, ra_deg, dec_deg, plx_mas, vmag,
  main_id. Proxima (plx 768.07 mas) and Wolf 359 (plx 415.18 mas) are the two
  navigation targets.
- **`nhjpl_traj.txt`** — JPL Horizons ephemeris of New Horizons (barycentric,
  DE441, TDB) — the GROUND TRUTH for E3.
- **`nhparallax.ipynb`** — Lauer's analysis notebook. Holds the recalibrated
  measured star directions and the navigation solver `n_star_solve`.

## Key numbers (for cross-checking E3; already in tests/golden_numbers.py)

- New Horizons at observation epoch 2020-04-23: distance **47.12 au** (JPL);
  `NH_DIST_AU`.
- Measured parallax shifts vs Earth: Proxima **32.4"**, Wolf 359 **15.7"**;
  `NH_PROXIMA_SHIFT_ARCSEC`, `NH_WOLF359_SHIFT_ARCSEC`.
- Lauer's result: NH position recovered to a **0.441 x 0.233 x 0.206 au** error
  ellipsoid vs JPL (the "0.44 au" headline); per-image astrometric sigma 0.44".

## Lauer's navigation method (`n_star_solve`, to be re-implemented independently)

Line-of-position triangulation in closed form. Given star 3D positions `p_i`
and measured unit directions `d_i` to them from the spacecraft:

    w_i = (I - d_i d_i^T) / |p_i|^2      # projector orthogonal to d_i, 1/r^2 weight
    x   = (sum_i w_i)^{-1} (sum_i w_i p_i)   # least-squares line intersection

E3 re-implements this on our side of the truth wall (JPL ephemeris = truth,
Lauer's measured directions = measurements) and confirms the ~0.44 au recovery.

## Open student decision (flagged, not decided here)

Vendor-vs-refetch: we currently git-ignore all fetched data and keep only this
README + `fetch_e3_data.py`. If you want the small text inputs (`nearby100.txt`,
`nhjpl_traj.txt`, `nhparallax.ipynb`) committed for network-free reproducibility,
that is a one-line `.gitignore` change — rule on it before E3 is blessed.
