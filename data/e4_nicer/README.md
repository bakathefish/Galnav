# E4 dataset — real NICER photon folding (armor experiment)

Real-spacecraft X-ray data for Experiment **E4** (the project's *armor* track,
run only once the spine is green): fold the barycentred photon arrival times of
three millisecond pulsars against their ephemerides, inject a known
orbit-ephemeris / clock bias, and recover it from the phase residuals.
**Pass = bias recovery within 2σ on three independent pulsars.** The companion
armor card **Spec 9** requires PINT `photonphase` agreement to `< 1e-9` in phase
(this is why E4 runs in the WSL/longdouble ARMOR env — see
`requirements-armor.txt`; native Windows `np.longdouble` is only float64).

This is real NICER (Neutron star Interior Composition Explorer, on the ISS)
event data, the X-ray counterpart to E3's optical New-Horizons anchor.

## Provenance

- **Instrument:** NICER X-ray Timing Instrument (XTI), 56 co-aligned MPU/FPM
  modules on the ISS. The event files here are the **7-MPU merged, level-2
  CLEANED** photon lists (`_0mpu7_cl`).
- **Archive:** NASA HEASARC public archive (no authentication). Directory
  pattern per observation:
  `https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs/{YYYY_MM}/{ObsID}/`
  - event list: `xti/event_cl/ni{ObsID}_0mpu7_cl.evt.gz`
  - orbit file: `auxil/ni{ObsID}.orb.gz`
- **AWS mirror (fallback, NOT needed for this retrieval):** the same tree is
  mirrored at `https://nasa-heasarc.s3.amazonaws.com/nicer/data/obs/{YYYY_MM}/{ObsID}/`.
  All 12 files came cleanly from HEASARC on the first attempt; the mirror was
  never used.
- **License:** NICER data are in the public domain (work of the US Government /
  NASA GSFC). Redistribution is permitted; we do **not** vendor the ~90 MB of
  raw FITS into git (it is re-fetchable from HEASARC).
- **Retrieved:** 2026-07-16 for GalNav, via `fetch_e4_data.py` (Python stdlib
  only — `urllib.request`, `hashlib`, `gzip`).
- **Verification (existence):** each ObsID's HEASARC directory listing was
  fetched and both files confirmed present, 2026-07-16.
- **Verification (integrity, by the fetch script):** for every file the bytes
  written equal the server `Content-Length`, the `.gz` decompresses fully, and
  the byte size is plausible against the listing size (all 12 within 1.02–1.07×).
- **Verification (readability, astropy):** all six event files open with
  `astropy.io.fits`; each `EVENTS` header `OBS_ID` matches its directory ObsID,
  `OBJECT` matches the claimed pulsar, and `EXPOSURE` matches the listed ks
  (see the table's row-count / exposure columns).

## The observations

Three pulsars × two ObsIDs each = 12 files. One ObsID per pulsar is the minimal
set for the experiment; the second gives an independent epoch.

| Pulsar | ObsID | YYYY_MM | Date (UTC) | Exp (ks) | evt size | orb size | EVENTS rows | NICER program / analysis |
|---|---|---|---|---|---|---|---|---|
| PSR J0030+0451 | 1060020263 | 2018_01 | 2018-01-19 | 29.5 | ~2.9 M | ~2.7 M | 152 107 | Riley et al. 2019 / Bogdanov et al. 2019 (NICER mass–radius) |
| PSR J0030+0451 | 1060020113 | 2017_08 | 2017-08-04 | 29.2 | ~20 M | ~2.7 M | 876 371 | Riley et al. 2019 / Bogdanov et al. 2019 (NICER mass–radius) |
| PSR B1937+21 (= J1939+2134) | 1070020148 | 2017_09 | 2017-09-16 | 29.0 | ~3.0 M | ~2.7 M | 128 383 | NICER MSP timing (the original millisecond pulsar) |
| PSR B1937+21 (= J1939+2134) | 1070020147 | 2017_09 | 2017-09-16 | 21.6 | ~8.5 M | ~1.9 M | 369 869 | NICER MSP timing (the original millisecond pulsar) |
| PSR J0437−4715 | 1060010188 | 2017_12 | 2017-12-07 | 19.7 | ~1.1 M | ~1.8 M | 50 279 | Choudhury et al. 2024 (NICER mass–radius) |
| PSR J0437−4715 | 1060010157 | 2017_10 | 2017-10-13 | 19.1 | ~37 M | ~2.2 M | 1 618 851 | Choudhury et al. 2024 (NICER mass–radius) |

These ObsIDs are individual early pointings from each pulsar's NICER observing
program; the co-added data from those programs underpin the cited analyses. The
`OBJECT` keyword for J0437−4715 reads `PSR_J0437-4715_opt1` (a NICER
pointing-optimisation label; still J0437−4715).

## How to get the data (it is git-ignored)

```
python data/e4_nicer/fetch_e4_data.py
```

Downloads the 12 files into an archive-relative layout, streams each while
computing its sha256, and re-verifies integrity + readability on every run
(idempotent — existing non-empty files are kept and re-checked, not
re-downloaded).

## Layout after fetching

```
data/e4_nicer/{YYYY_MM}/{ObsID}/xti/event_cl/ni{ObsID}_0mpu7_cl.evt.gz   # photons
data/e4_nicer/{YYYY_MM}/{ObsID}/auxil/ni{ObsID}.orb.gz                    # ISS orbit
```

- The **event list** is the measurement: screened photon arrival times (plus
  energy/detector columns) in the `EVENTS` extension.
- The **orbit file** is required for barycentering: PINT / `barycorr` splines the
  ISS position from `.orb` to move each photon time to the Solar-System
  barycentre. Without the `.orb`, the event times cannot be barycentred, and E4
  cannot fold.

## What E4 does with it (to be implemented on our side of the truth wall)

1. Barycentre the photon times using the ObsID's `.orb` file and a DE ephemeris.
2. Assign each photon a pulse phase from the pulsar ephemeris (PINT
   `photonphase`; Spec 9 gate `< 1e-9` phase).
3. Fold to a profile (H-test / template) to get a photon TOA (expected 1–50 µs).
4. Inject a known orbit-ephemeris / clock bias and recover it from the phase
   residuals; pass = recovery within 2σ on all three pulsars.

## sha256 manifest (fetched 2026-07-16)

Archive-relative path, bytes, sha256 — every file `gzip_ok=True`, size ratio to
listing in [1.02, 1.07]. Total **90 354 942 bytes (~90.4 MB)**, 12/12 present,
0 skipped, 0 retries, 0 mirror fallbacks.

```
2018_01/1060020263/xti/event_cl/ni1060020263_0mpu7_cl.evt.gz
    3030389   8c6caa23e60b3047c20fd00d973580513a4b985d4e4677a179b7680e4ed10972
2018_01/1060020263/auxil/ni1060020263.orb.gz
    2814016   0479ac1c9167fdaf35de95ac06e88c81410b75648c2408155f289fe0760bb1d3
2017_08/1060020113/xti/event_cl/ni1060020113_0mpu7_cl.evt.gz
    21153500  87a657886ab3a319da481efe2f5934f31d3dd09cdff546e263eb175d0fb7365f
2017_08/1060020113/auxil/ni1060020113.orb.gz
    2841055   6b1f4a3f3a02b2bb6f1cacf749ccd252b67fb0fca905a5e7e641902c710da546
2017_09/1070020148/xti/event_cl/ni1070020148_0mpu7_cl.evt.gz
    3152891   3f05e946510073a5211ee9715186d9b5140ef1962765d42fccd8093e5af4d769
2017_09/1070020148/auxil/ni1070020148.orb.gz
    2783199   8ab967a5b27465124a7033ef9019e4ae42be6fd1b2abbc2a780cafee6703f67f
2017_09/1070020147/xti/event_cl/ni1070020147_0mpu7_cl.evt.gz
    8898039   eb99d44e5864224f600df6a6478ad7a7d775fab8eec04bc67f10bf94dac15bbf
2017_09/1070020147/auxil/ni1070020147.orb.gz
    1942116   e87c0830b4e24b187c12dec544bdc680779c6f6dd0f21f78a9448691c852ec7a
2017_12/1060010188/xti/event_cl/ni1060010188_0mpu7_cl.evt.gz
    1160218   27891192c071300052e468df7d4a42d09438a6479dfad4bcc10ad81d42a91fcc
2017_12/1060010188/auxil/ni1060010188.orb.gz
    1916642   b5aa804d07d1ad00c0a17ed1855a585156afa58ef06cd05e74cfc22455895927
2017_10/1060010157/xti/event_cl/ni1060010157_0mpu7_cl.evt.gz
    38396462  58701480127b14b9905641e980ad1eeec5c7f8683f20f2726bda41b3c6bebdcb
2017_10/1060010157/auxil/ni1060010157.orb.gz
    2266415   c8685ae5f7874985009a7da786e4a2ff629762029899db5981fab934493cc4f7
```

## Open student decision (flagged, not decided here)

Same vendor-vs-refetch question as E3: we git-ignore all raw FITS and keep only
this README + `fetch_e4_data.py`. E4 is *armor*, so if HEASARC is unreachable at
run time the whole experiment is deferred anyway (per the Sep-5 gate in the
schedule, an unclean NICER fold sends E4 simulation-only). No small text inputs
here worth committing, so the refetch default is cleaner than for E3.

## Timing models (`pars/`, committed)

| file | pulsar | source | sha256 |
|---|---|---|---|
| `J0030+0451_PINT_20220302.nb.par` | PSR J0030+0451 | NANOGrav 15-yr data set, narrowband PINT par (release header: created 2022-03-02, PINT 0.8.4, WVU HPC) | c39900cc038a6be9431539d6ca5eb71224268f276625d7fe283748eabaea53a8 |

Provenance and verification status (2026-07-16): the file carries the NG15
processing fingerprint verbatim in its header and passes the physics
cross-check F0 = 205.53069907954086655 Hz -> P = 4.86545 ms against the
frozen comb table's untruncated 4.8654 ms (0.002%). The canonical archive
is the NANOGrav 15-Year Data Set on Zenodo, doi:10.5281/zenodo.16051178
(v2.1.0, single 638.7 MB tarball `NANOGrav15yr_PulsarTiming_v2.1.0.tar.gz`,
md5 557d42dd8486a5f8272d90dec9b228a8); a byte-level extraction check of
this par against that tarball is DEFERRED (disproportionate download for a
46 KB text file today) and flagged on the ratification worksheet -- the
recorded sha256 above makes it a one-command check at the sitting. Note:
both Spec 9 test routes share this par, so the Spec 9 gate is insensitive
to par authenticity; authenticity matters for E4's folds and the paper's
citation ([NG15] in journal/citations.md).

Timing-model additions (2026-07-16, E4): the canonical NG15 release tarball
(NANOGrav15yr_PulsarTiming_v2.1.0.tar.gz, 638,719,668 bytes) was downloaded
from Zenodo record 16051178 and its md5 MATCHED the record manifest
(557d42dd8486a5f8272d90dec9b228a8). Two further pars were extracted from
narrowband/par/ and committed; the previously-committed J0030 par
BYTE-MATCHED the tarball copy (sha256 identical), closing the deferred
verification recorded above.

| file | pulsar | sha256 |
|---|---|---|
| `B1937+21_PINT_20220306.nb.par` | PSR B1937+21 (isolated) | b38831170401abcac1e932906ec1994fcd3ea9b24003347ee7ed38a3118a6bcb |
| `J0437-4715_PINT_20220301.nb.par` | PSR J0437-4715 (BINARY DD) | 0fa244c25f3f580fe6f615a3ef356d82a3e9f88f93a17fe105df3dd358ec8862 |

F0 cross-checks vs the frozen comb table: B1937 641.928 Hz -> P = 1.5578 ms
(table: 1.558 ms); J0437 173.688 Hz -> P = 5.7575 ms (table: 5.757 ms).
