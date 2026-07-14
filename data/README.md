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
