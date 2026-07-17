# GalNav — ISEF demo playbook (the booth script)

Everything you say and type at the booth, in order, with the exact commands and
the output to expect. Timings below were measured on the project laptop on
2026-07-17; a judge's patience, not the clock, sets the pace. Every number is
sourced from `journal/findings-compilation.md`.

## Before the booth (once)

- Fetch the real data (it is git-ignored, re-fetchable):
  `python data/e3_new_horizons/fetch_e3_data.py` (New Horizons frames for the
  GUI finale). The NICER photons for E4 are not needed live — you show a
  committed figure.
- `pip install -r requirements.txt`, then confirm `python -m pytest -q` says
  **84 passed**.
- Have `results/archive/e4_bias_recovery_20260716T154452Z.png` open in an image
  viewer as a backup slide.

## The 90-second opener (say this)

> "Imagine a spacecraft between the stars, no GPS, no signal from Earth. It has
> a camera and a star catalog. Our project asks three questions and answers all
> three with real NASA data.
>
> **Where are you?** The nearby stars give an absolute position fix — but a
> coarse one, good to about an astronomical unit. **When are you?** We can read
> the *year* off the sky, because nearby stars drift, and a stale catalog
> quietly poisons the fix. **How long can you trust it?** That is the headline:
> a star catalog has a navigation expiration date, and we mapped it.
>
> We also tested the tempting shortcut — pulsars, which tick like km-precise
> clocks. It fails at interstellar range, and we quantify exactly why: a
> one-au star fix is four orders of magnitude too coarse to lock onto a pulsar's
> integer count. Where you are, when you are, how long you can trust it — proven,
> and reproducible bit-for-bit."

## The live demo sequence

### 1. "It cannot cheat" — the truth wall (~6-10 s)

```
python -m pytest -q
```

Expect: **`84 passed`**. Say: *"The navigator is forbidden from ever seeing the
simulator that generates the measurements. This isn't a promise — this test
reads our own source code and fails the build if the navigator so much as
imports the truth side. A judge can't cheat, and neither can we."*

### 2. "Provably optimal" — E1, solver vs the theoretical floor (~90 s)

```
python -m experiments.e1_crlb_grid
```

Expect the last lines to read `cells: 96   worst RMS/CRLB deviation factor:
1.064` and a written PNG. Say: *"Across 96 cases — different distances, star
counts, camera noise — our navigator's error sits on the Cramér-Rao bound, the
theoretical best any estimator can do. Worst case, 6% above the floor. The dots
sit on the theory line: the navigator is provably optimal, not just 'good.'"*

### 3. THE HEADLINE — E6, the catalog expiration date (~25 s)

```
python -m experiments.e6_catalog_aging
```

Expect: `epoch parallax floor (age 0, finest sensor): 7.66 au` and a row of
crossover ages beginning **44.8** and ending **161.9** yr. Say: *"This is the
new result. As the catalog ages, navigation error grows on a schedule. The
crossover — the age at which a stale catalog hurts you more than a cheap camera
— runs from 44.8 years with a sharp camera to 161.9 years with a crude one. And
there's a floor of 7.66 au you can't beat with any camera, because the catalog's
own parallax uncertainty sets it. Nobody has mapped this before."*

### 4. THE FINALE — a real spacecraft, from its own photos (`python -m gui.app`)

Open the window, then:

1. **Add image(s)…** → select all twelve LORRI frames in
   `data/e3_new_horizons/repo/` (`lor_*_pwcs2.fits` — six Proxima-field, six
   Wolf-field).
2. **Solve fields** → each frame gets a WCS straight from its header (source
   `fits-header`), instantly.
3. **Locate spacecraft** → the Locate button accumulates every loaded image, so
   twelve lines of position give **miss ≈ 0.387 au** (|r| ≈ 47.39 au) — right on
   Lauer's own 0.351 au. (Under 0.1 s.)
4. **Estimate catalog age** → **4.286 ± 0.055 yr** against the true 4.310 yr.
   The all-frames scan takes a few to ~15 s and runs on a background thread, so
   the window stays alive.

Say: *"These are real photos a real NASA spacecraft took at 47 au. From twelve
pictures of two stars, the tool finds New Horizons to within 0.39 au — right on
the published result — and reads that the catalog is 4.3 years old from how far
the stars have drifted. Where you are, and when you are, from starlight."*

**Fast fallback — two frames.** For the ~5-second version, load just
`lor_0449855930_0x633_pwcs2.fits` (Proxima) and
`lor_0449933827_0x633_pwcs2.fits` (Wolf 359): miss ≈ 0.976 au, age 4.336 ± 0.134
yr (its age scan is ~5 s). The larger miss is one frame per star instead of six
— centroid-noise averaging, not a physics gap.

**Robust fallback** (if a click misbehaves live): run the deterministic script
`python -m gui.nh_demo`, which prints the fix and age with no clicking. If a
judge asks *"why is two frames worse than Lauer?"*, the answer is: *"one frame
per star versus his six averaged — and when we use all twelve frames we land at
0.387 au, right on his 0.351, with nothing but quick 5-sigma centroids."*

**If a command is risky to run live at all**, show the blessed figures in
`results/archive/` and tell the replot story: every figure regenerates from its
committed `.npz` arrays alone, so the picture on the poster is provably the
picture the data makes.

## The memorize-grade numbers (know these cold)

| number | meaning |
|---|---|
| 1.064 / 1.045 | worst MC-vs-CRLB ratios — the navigator is optimal (grid / CI cells) |
| 3.019 au / 2.028 km/s | Bailer-Jones (2021) anchor reproduced (his 3 / 2 published) |
| 0.3467 au | real New Horizons recovered vs JPL truth (E3 spine) |
| ~30 au | the miss if you skip epoch propagation (why it's mandatory) |
| 7.66 au | epoch-parallax floor, 1 pc / 20 stars |
| 44.8 → 161.9 yr | catalog-age crossover vs sensor (10 mas → 60″ camera) |
| ~15.9 arcsec | the knee below which a better camera stops helping at 1 pc |
| 286.02 km / 523,024× | pulsar-comb packing radius / how far a 1-au fix overshoots it |
| 100.000% / 8,000 | exact integer recovery inside the packing radius (Spec 8) |
| 1356 au / 1201 km/s | a classical (non-relativistic) navigator's bias at 0.1c |
| 270.3 d @ 1 cm/s | comb-lock coast budget (467 km comb) |
| 0.0 (bit-identical) | two-route photon-phase agreement, 152,107 real NICER photons |
| H = 874.1 | J0437 fold significance (binary pulsar model validated) |
| 76.15 km / 1.85 σ | 100 km orbit-bias recovery error and its honest size (E4) |

## Judge Q&A (the three you will get)

**"How do I know the navigator isn't cheating?"** Two independent guards. First,
the truth wall: `tests/test_truth_wall.py` reads the source and fails if
`galnav/nav/` ever imports `galnav/truth/` — the only channel between them is
the measurement vector. Second, we implement the key physics **twice**,
independently (e.g. the aberration on the truth side and the nav side are
separate code), and cross-check them — a shared bug would have to be made twice
in two forms.

**"What's actually new here?"** Two things. (1) **The map.** The astrometric
community has always known catalogs age; what was unpublished is the
*navigation-error* map over (catalog age × sensor precision), with its crossover
curve and its parallax floor. The novelty is the map, not "catalogs age." (2)
**The interstellar pulsar-bootstrap impossibility:** a one-au starlight fix
overshoots the pulsar comb's packing radius by **523,024×**, so the integer tick
counts are unrecoverable — pulsars beyond the Sun are an odometer, not a GPS.

**"Is it reproducible?"** Yes, bitwise, from a fresh clone. Every figure
regenerates from committed `.npz` arrays; every quoted number is byte-identical
to its archived run; the whole environment is pinned.

## Framing discipline — say it exactly this way

- **The pulsar result is NARROW.** Solar-system pulsar navigation is
  established and real (Deng 2013, Shemar 2016, Becker 2013). Our finding is
  *only* the **interstellar bootstrap** limit — pulsars can't be *acquired* from
  a coarse star fix at interstellar range. Never say "pulsars can't navigate."
- **The one-line distinguish** if a judge names pulsar-Doppler work: there is a
  same-named in-system sub-field — "X-ray pulsar / starlight-Doppler
  deeply-integrated navigation" (Liu & Fang 2015; Wang, Zheng & Zhang 2017) —
  that fuses pulsar timing with starlight **radial velocity** as a velocity aid.
  It never addresses interstellar **position** bootstrap or catalog aging, which
  is our question.
- **The E6 novelty is the map**, with a crossover locus and a floor — not the
  observation that stars drift.

## What NOT to claim (these will sink you if you overstate)

- **Do not say "pulsars can't navigate."** E5 is about the *interstellar
  bootstrap* only (see the framing above).
- **Do not quote the 26-arcsec max-deflection gap as a per-angle error.** At
  0.1c the classical navigator's *per-angle model error* is ~500 arcsec (which
  fuses into ~1356 au); 26 arcsec is a separate quantity (the peak deflection
  shift), not the error each angle carries.
- **Do not call 0.441 au "Lauer's miss."** 0.441 au is the largest **semi-axis
  of Lauer's error ellipsoid**; his actual miss vs JPL is 0.351 au, and we
  reproduce it at 0.3467 au.
- **Do not present the GUI's two-frame ~1 au as the project's accuracy.** The
  vetted number is E3's 0.3467 au; the demo's two-frame 0.976 au is one frame
  per star (centroid-noise averaging), and its twelve-frame fix is 0.387 au. Do
  not blame the two-frame miss on "uncorrected aberration" — that was measured
  false (the `pwcs2` WCS already absorbs aberration); the residual is per-frame
  systematics.

## Booth logistics

- **Everything except E4 is offline-safe** and runs on the laptop with no
  network. Run E1, E6, and the GUI live.
- **E4 / the armor track is NOT a live run.** It needs a WSL2 float128
  environment. Show the committed figure
  `results/archive/e4_bias_recovery_20260716T154452Z.png` and tell its story:
  three 100 km orbit biases injected into real NICER data, all three recovered
  within 2σ from the pulsar fold shifts.
- Keep `docs/GUI-EXPLAINED.md` handy for the deep "how does the fix work"
  follow-up, and `journal/findings-compilation.md` for any number a judge wants
  sourced.
