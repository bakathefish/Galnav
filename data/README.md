# data/ — cached external datasets

## gaia_dr3_nav_subset.csv

Snapshot of every well-measured Gaia DR3 star within ~20 parsecs.
Retrieved 2026-07-14 from the official ESA Gaia archive TAP service
(`https://gea.esac.esa.int/tap-server/tap/sync`), stdlib urllib only.

**Exact query (ADQL):**

```sql
SELECT source_id, ra, dec, parallax, parallax_error, pmra, pmra_error,
       pmdec, pmdec_error, radial_velocity, radial_velocity_error,
       phot_g_mean_mag, ra_error, dec_error, ra_dec_corr, ra_parallax_corr,
       dec_parallax_corr, ra_pmra_corr, ra_pmdec_corr, dec_pmra_corr,
       dec_pmdec_corr, parallax_pmra_corr, parallax_pmdec_corr,
       pmra_pmdec_corr, ruwe
FROM gaiadr3.gaia_source
WHERE parallax > 50 AND parallax_over_error > 10 AND ruwe < 1.4
ORDER BY parallax DESC
```

**What the filters mean (plain English):**
- `parallax > 50` — parallax bigger than 50 milliarcseconds means the star
  is closer than 20 parsecs (distance in pc = 1000 / parallax in mas).
  The E1 experiment grid runs 1–20 pc, so this covers it.
- `parallax_over_error > 10` — the distance measurement is at least 10x
  bigger than its own error bar: keep only stars Gaia measured well.
- `ruwe < 1.4` — Gaia's standard "the astrometric solution is trustworthy"
  cut; filters out badly-fit sources (often unresolved binaries).

**Contents check (2026-07-14):** 1,941 stars; nearest is Proxima Centauri
(parallax 768.07 mas = 1.30 pc — matches the known value, our sanity
anchor); farthest 50.0 mas = 19.99 pc; 554 stars have no radial velocity
(these become the "missing RV" population in the catalog-aging experiment
E6 — a feature, not a flaw).

**Known limitation:** Gaia struggles with extremely bright stars, and the
RUWE cut removes messy binaries — so a few famous neighbors (e.g.
Alpha Centauri A/B, Sirius A) may be absent. Fine for simulation (any
honest star field works); revisit only if an experiment card needs a
specific named star.

**Columns:** positions (ra, dec, epoch J2016.0, ICRS), parallax, proper
motions, radial velocity, G magnitude — each with its error — plus the ten
correlation coefficients needed to build each star's full covariance
matrix (used from Spec 3/Spec 7 onward).

**Citation [GaiaDR3] in journal/citations.md**: Gaia Collaboration,
Vallenari, A., et al. (2023), A&A 674, A1. Data: ESA Gaia Archive,
DR3 (static release — this exact query is reproducible byte-for-byte).

## gaia_dr3_nav_100pc.csv

Snapshot of well-measured Gaia DR3 stars out to ~100 parsecs. This is the
**web GUI's wide "trace any spacecraft image" catalog** — it is NOT used by
the frozen science spine, which stays on `gaia_dr3_nav_subset.csv` (the ~20 pc
file, frozen byte-for-byte; every blessed number depends on it). Same column
set and order as the 20 pc file, so `galnav/nav/catalog.py::load_catalog`
reads it unchanged.

Retrieved 2026-07-17 from the official ESA Gaia archive TAP service, stdlib
`urllib` only. Because 100 pc returns far more than the 2000-row synchronous
limit, this used the **TAP async (UWS) job workflow** (submit → poll → download)
against `https://gea.esac.esa.int/tap-server/tap/async`. The re-runnable fetch
script is `data/fetch_gaia_100pc.py`.

**Exact query (ADQL):**

```sql
SELECT source_id, ra, dec, parallax, parallax_error, pmra, pmra_error,
       pmdec, pmdec_error, radial_velocity, radial_velocity_error,
       phot_g_mean_mag, ra_error, dec_error, ra_dec_corr, ra_parallax_corr,
       dec_parallax_corr, ra_pmra_corr, ra_pmdec_corr, dec_pmra_corr,
       dec_pmdec_corr, parallax_pmra_corr, parallax_pmdec_corr,
       pmra_pmdec_corr, ruwe
FROM gaiadr3.gaia_source
WHERE parallax > 10 AND parallax_over_error > 10 AND ruwe < 1.4
      AND pmra IS NOT NULL AND pmdec IS NOT NULL
      AND phot_g_mean_mag < 16.5
ORDER BY parallax DESC
```

**Same quality cuts as the 20 pc file, three deliberate differences:**
- `parallax > 10` instead of `> 50` — stars closer than 100 pc (dist in pc =
  1000 / parallax in mas) rather than 20 pc.
- `pmra IS NOT NULL AND pmdec IS NOT NULL` — the loader RAISES on a non-finite
  proper motion (its "no NaN out" propagation guarantee), so we force finite
  proper motions at the source. (`parallax_over_error > 10` already keeps
  parallax finite.)
- `phot_g_mean_mag < 16.5` — a **brightness cut applied under the size guard**
  (next paragraph). Keeps every navigationally useful star and drops only the
  faint late-M / white-dwarf tail.

**Size guard / magnitude cut — honest trade:** the base 100 pc cut (no
brightness limit) returns **266,536 rows (~85 MB)**, which blows the
"keep it committable" budget. Per the fetch spec, when the base cut exceeds
~350,000 rows OR ~45 MB we add `phot_g_mean_mag < 16.5`. That is the single
designated fallback and it yields the shipped file. Note it is still slightly
over the 45 MB soft target — see the shipped size below — because 100 pc is
genuinely star-rich; `G < 16.5` is the only brightness cut in scope, so the
file ships as-is and the size is flagged rather than silently cut tighter.

**Contents check (2026-07-17):**
- **174,711 stars**, file size **56.8 MB** (56,784,491 bytes).
- Nearest (top row, `ORDER BY parallax DESC`) is **Proxima Centauri**,
  parallax 768.07 mas = **1.302 pc**, G = 8.98 — the same anchor row as the
  20 pc file.
- Farthest is parallax 10.000 mas = **100.000 pc** exactly (the cut edge).
- Both demo-critical stars are present: **Proxima** `5853498713190525696`
  (G 8.98) and **Wolf 359** `3864972938605115520` (G ~13.5) — both well
  inside the `G < 16.5` cut.
- Loader integration check passes (does not raise on non-finite pmra/pmdec):
  `load_catalog('data/gaia_dr3_nav_100pc.csv')` returns `star_pos_au` shape
  `(174711, 3)`, nearest distance 268,551 au (= Proxima at 1.302 pc).

**Columns:** identical to `gaia_dr3_nav_subset.csv` above (positions, parallax,
proper motions, radial velocity, G magnitude, each with its error, plus the ten
correlation coefficients). Stars beyond ~a few pc mostly have no Gaia radial
velocity, so `radial_velocity` is empty (→ NaN) for the large majority of rows;
that is expected and the loader/navigator handle it via the explicit
missing-RV fill policy.

**Citation [GaiaDR3] in journal/citations.md** (same static DR3 release as the
20 pc file — reproducible byte-for-byte via `data/fetch_gaia_100pc.py`).

Integrity: sha256 945c827d1c50dc04b63167e95f9382bae21c21e2b9d8ebc0a8c9174f760fd429 (56,784,491 bytes). Like the NICER raw data, this file
is git-ignored: reproduce it with `python data/fetch_gaia_100pc.py` (the exact
ADQL above; Gaia DR3 is a static release). The GUI degrades gracefully to the
20 pc subset when this file is absent.

## astrometry-index/  (narrow-field blind-solver index files)

Star-pattern ("skymark") index files that let the OFFLINE blind plate-solver
(astrometry.net's `solve-field`, run inside WSL) figure out where a NARROW-field
spacecraft camera pointed — e.g. a New Horizons LORRI frame (0.29 deg = 17.4
arcmin). These are used **only** by the web GUI's Upload button when someone
drops in an arbitrary star image with no WCS header. The baked-in New Horizons
demo never needs them: those frames already carry a solved WCS, so they solve
instantly from the header (backend 1 in `gui/platesolve.py`).

**Why a separate index set.** `solve-field` matches 4-star patterns ("quads")
whose size must sit inside the image's field of view. The apt package
`astrometry-data-tycho2` only covers wide fields (>~0.5 deg). A 17.4-arcmin
frame needs the small-scale Gaia-based **5200 series**. Index scale *N* covers
quads of roughly `[2·2^(N/2), 2.8·2^(N/2)]` arcmin — so for a 17.4-arcmin field
the useful scales are 3 (5.6–8′), 4 (8–11′) and 5 (11–16′); scale 6 (16–22′) is
marginal (quads barely fit) and was left out (see cap below).

**Source (exact):**
`https://portal.nersc.gov/project/cosmo/temp/dstn/index-5200/LITE/`
This is the **LITE** ("LIGHT") build of the 5200 series — smaller files with no
extra Gaia columns, which is all the solver needs. It is the location the
astrometry.net data root (`http://data.astrometry.net/`) now points to for the
5200 LIGHT series (the older `http://data.astrometry.net/5200/` path 404s / has
moved). Fetched with `curl` (streamed, resumable), stdlib only.

**What was fetched (2026-07-17):** scales **3, 4 and 5**, all 48 healpix tiles
each = **144 files, 3.99 GiB** (4,284,051,840 bytes):
- scale 4 `index-5204-00..47.fits` — 48 files, 1.136 GiB (the best match for LORRI)
- scale 5 `index-5205-00..47.fits` — 48 files, 0.573 GiB
- scale 3 `index-5203-00..47.fits` — 48 files, 2.281 GiB
Downloaded in that priority order (4, 5, then 3). **Scale 6** (0.287 GiB) was
intentionally skipped: adding it would push the total to 4.28 GiB, past the
**4.0 GiB hard cap** for this download, and scales 3–5 already cover the field.
Every file was verified to begin with the FITS magic `SIMPLE  =` and to match
its published `Content-Length` byte-for-byte.

**Git-ignored** (`data/astrometry-index/` in `.gitignore`): ~4 GB of
re-downloadable binary index files never belong in the repo. To recreate them,
re-run the download step, or grab scales 3–5 (`index-520{3,4,5}-*.fits`) from
the source URL above into this directory.

**How the solver finds them.** `gui/install-offline-solver.sh` (run once) writes
`~/.galnav-astrometry.cfg` with an `add_path` line pointing here (as the WSL
`/mnt/c/...` mount path), and the app calls
`solve-field --config ~/.galnav-astrometry.cfg`. Nothing else in the repo reads
this directory.

**Citation [AstrometryNet] in journal/citations.md**: Lang, Hogg, Mierle,
Blanton & Roweis (2010), AJ 139, 1782. Index series: 5200 (Tycho-2 + Gaia DR2),
LITE build, retrieved from the NERSC data mirror.

## `data/gaia_cones/` — deep-identify Gaia cone cache

The web demo's **deep identify** tier labels nearly every detected dot with the
star it is (not just the handful close enough to navigate by). It does this by
caching, once per frame footprint, the full-depth Gaia DR3 stars inside that
footprint. `gui/gaiacone.py` fetches them from the ESA Gaia TAP async service
and writes one CSV per footprint; a cached cone is a **zero-network** read, so
the booth demo runs fully offline after a one-time pre-warm.

- **Query (ADQL), per footprint:**
  `SELECT TOP 5000 source_id, ra, dec, parallax, parallax_over_error,
  phot_g_mean_mag FROM gaiadr3.gaia_source WHERE
  1=CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',<ra>,<dec>,<radius_deg>))
  ORDER BY phot_g_mean_mag ASC`. Radius = half the frame diagonal + 10%
  (LORRI ≈ 0.23°). The **TOP 5000** cap bounds each file to the brightest 5000
  stars — plenty to label ~100 blobs; near the galactic plane (the Proxima
  fields, b ≈ −2°) the cap bites, while high-latitude fields (Wolf 359, b ≈ +56°)
  return everything (~530 stars).
- **Cache key / filename:** the footprint centre RA/Dec and radius, each rounded
  to 0.01°, as `cone_ra<ra>_dec<dec>_r<radius>.csv`. The several same-pointing
  LORRI frames therefore share one file — the 12 demo frames collapse to **4**
  cones (~1.0 MB total; Proxima 2 × 472 KB at the 5000 cap, Wolf 2 × 47 KB).
- **Pre-warm (once, internet up):** `python -m gui.prewarm_demo_cones`. Retrieved
  **2026-07-17** from `https://gea.esac.esa.int/tap-server/tap/async` (Gaia DR3).
- **Git-ignored** (`data/gaia_cones/` in `.gitignore`): it is a re-fetchable
  cache, not source. A cache miss during a render never blocks (rendering passes
  `allow_fetch=False`) and never errors — it silently falls back to the nearby
  navigation catalog's labels.
- **Identification only.** These cones feed the *labelling* tier (a tight ~2-px
  positional match). They never enter a position fix — the navigation /
  position-capable tier still uses the frozen nearby catalog and the 120″
  parallax match. Distances shown come from `parallax` only when
  `parallax_over_error ≥ 5` and `parallax > 0`; otherwise the label is the Gaia
  `G` magnitude, never a fabricated distance.
