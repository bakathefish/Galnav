# Vendored assets — provenance

All files below are served **locally** by the GalNav web app. Nothing here is
fetched from the network at runtime (see `../INTEGRATION-RECIPE.md`, "Offline proof").

- **Library:** spacekit.js (Ian Webster / typpo)
- **Repo:** https://github.com/typpo/spacekit
- **Version pinned:** `master` @ commit `aa93d3f21c3bd983e8c55af88a175f06c3d32fc8`
  (fetched 2026-07-17). The npm `package.json` in that tree reads `0.1.0`; the
  meaningful version identifier is the commit hash.
- **License:** MIT — Copyright (c) 2019 Ian Webster. Full text in
  `../spacekit-master/LICENSE` (in the staging tree). The built bundle also
  embeds **three.js** (MIT, © three.js authors) — no separate three.js file is
  needed; it is compiled into `spacekit.js`.

| Vendored file | Bytes | Source | Notes |
|---|---:|---|---|
| `spacekit.js` | 750,287 | https://typpo.github.io/spacekit/build/spacekit.js | Prebuilt UMD bundle exposing the global `Spacekit`. Includes three.js. gzips to ~190 KB. |
| `assets/sprites/fuzzyparticle.png` | 1,887 | repo `src/assets/sprites/fuzzyparticle.png` @ pinned commit | Default point sprite; used for the amber marker. |
| `assets/sprites/smallparticle.png` | 439 | repo `src/assets/sprites/smallparticle.png` | Default planet particle sprite. |
| `assets/sprites/lensflare0.png` | 78,758 | repo `src/assets/sprites/lensflare0.png` | Sun glow sprite (`SpaceObjectPresets.SUN`). |
| `assets/skybox/eso_milkyway.jpg` | 2,475,382 | repo `src/assets/skybox/eso_milkyway.jpg` | Deep-space backdrop (`SkyboxPresets.ESO_GIGAGALAXY`). Underlying image: ESO GigaGalaxy Zoom Milky Way panorama, credit **ESO / S. Brunier** (CC BY). |
| `data/processed/bsc.json` | 338,088 | repo `src/data/processed/bsc.json` | Bright-star point catalog used by `viz.createStars()` in the au scene. Derived from the **Yale Bright Star Catalog**. |
| `data/gaia_20pc.json` | 49,372 | baked from GalNav repo `data/gaia_dr3_nav_subset.csv` by `../bake_gaia.py` | 1,941 stars within 20 pc as heliocentric-ecliptic XYZ (parsecs) + labels for the 5 nearest famous stars. Used by the pc scene's `createStaticParticles`. Provenance below. |

**Total vendored: 3,694,213 bytes (3.52 MB).**

## Assets deliberately NOT vendored
`spacekit.js` references these tokens; the PoC does not request them, so they
are omitted to stay lean. Add them only if a future view needs them:

- `assets/skybox/eso_lite.png` (612 KB, `SkyboxPresets.ESO_LITE`) — lighter skybox.
- `assets/skybox/nasa_tycho.jpg` (6.8 MB, `SkyboxPresets.NASA_TYCHO`) — heavy skybox.
- `assets/sprites/{sunsprite,fuzzyparticle-circled}.png` — unused sprite variants.
- `data/processed/natural-satellites.json` (94 KB) — only for moon ephemerides.

## Asset path mechanism (why the folder layout is what it is)
`spacekit.js` builds asset URLs from two tokens and the `basePath` option
(`util.getFullUrl`):

```
{{assets}}  ->  `${basePath}/assets`
{{data}}    ->  `${basePath}/data`
```

So with `basePath: './vendor'`, `{{assets}}/sprites/smallparticle.png`
resolves to `./vendor/assets/sprites/smallparticle.png`. The `assets/` and
`data/` subfolders MUST be preserved exactly. If `basePath` is omitted,
spacekit falls back to `https://typpo.github.io/spacekit/src` — **always set
basePath** to stay offline. (`data/gaia_20pc.json` is fetched by the PoC
directly, not through the token mechanism.)

## Scene data provenance (the hardcoded numbers)

### Gaia 20-pc star cloud (`data/gaia_20pc.json`)
Baked offline by `../bake_gaia.py` from the GalNav repo's own
`data/gaia_dr3_nav_subset.csv` (1,941 stars, **Gaia DR3**). For each star:
`dist_pc = 1000 / parallax_mas`; equatorial-ICRS unit vector from (ra, dec);
scaled by distance; then rotated to the ecliptic (obliquity 23.43928°). The 5
labeled stars are the 5 nearest in the subset, verified by Gaia `source_id`:

| Star | Gaia DR3 source_id | dist |
|---|---|---:|
| Proxima Centauri | 5853498713190525696 | 1.30 pc |
| Barnard's Star | 4472832130942575872 | 1.83 pc |
| Wolf 359 | 3864972938605115520 | 2.41 pc |
| Lalande 21185 | 762815470562110464 | 2.55 pc |
| Ross 154 | 4075141768785646848 | 2.98 pc |

(Sirius and Alpha Centauri are absent from the subset — too bright for Gaia's
faint-source pipeline. Amber sightlines are drawn to Proxima and Wolf 359.)

### Spacecraft & Eris markers (au scene, hardcoded in `poc.html`)
"Roughly-current" positions: heliocentric distance (au) + sky direction
(equatorial ICRS deg), converted to ecliptic in-page. Distances are 2025-2026
values; directions are each probe's published escape/asymptote heading.

| Object | dist (au) | RA,Dec used | Source (retrieved 2026-07-17) |
|---|---:|---|---|
| Voyager 1 | ~172 | 259.06°, +12.37° (Ophiuchus) | NASA "Where Are Voyager 1 & 2 Now"; TheSkyLive (Mar 2026) |
| Voyager 2 | ~140 | 303.75°, −59.71° (Pavo) | TheSkyLive voyager2-info (2026) |
| Pioneer 10 | ~139 | 68.98°, +16.51° (toward Aldebaran/Taurus) | Wikipedia "Pioneer 10" (Jul 2025) |
| Pioneer 11 | ~117 | 283.0°, −8.0° (Scutum/Aquila) | Wikipedia "Pioneer 11" (2026) |
| New Horizons (today) | ~64.5 | 289.62°, −20.17° (Sagittarius) | JHUAPL "Where is New Horizons"; TheSkyLive (Apr 2026) |
| Eris | ~95 | 26.0°, −2.0° (Cetus, near aphelion) | Wikipedia "Eris"; TheSkyLive eris-info (2026) |

These are labeled "~N au" and framed as approximate. The **amber** marker is a
distinct thing: the demo's 2020 recovered fix at 47.4 au (equatorial ICRS
[13.386, −42.369, −16.486] au). New Horizons' *today* marker (~64 au) lies along
nearly the same ecliptic direction as that 2020 fix — the probe simply moved
outward — which is why they appear radially aligned.

Sources:
- https://science.nasa.gov/mission/voyager/where-are-voyager-1-and-voyager-2-now/
- https://theskylive.com/voyager1-info , https://theskylive.com/voyager2-info
- https://en.wikipedia.org/wiki/Pioneer_10 , https://en.wikipedia.org/wiki/Pioneer_11
- https://pluto.jhuapl.edu/Mission/Where-is-New-Horizons.php , https://theskylive.com/newhorizons-info
- https://en.wikipedia.org/wiki/Eris_(dwarf_planet) , https://theskylive.com/eris-info
