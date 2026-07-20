# GUI: OpenSpace export — the fix, shown in a planetarium

**What this is.** OpenSpace ([OpenSpace] in citations) is the open-source
planetarium program NASA and the American Museum of Natural History fund —
it draws the real solar system, real spacecraft on their real trajectories
(including New Horizons), and the real Gaia stars, with a camera that zooms
seamlessly from a planet's surface out to the whole galaxy. It is the booth
SHOW layer: `gui/openspace_export.py` turns a GalNav position fix into a
marker inside that world, so a visitor can fly out and stand next to where
our pipeline says the spacecraft is — right beside where NASA says it
actually is. OpenSpace never computes anything for us; nothing in any
result depends on it.

**The two conversions, tiny-by-tiny.** GalNav states every fix in
barycentric ICRS-equatorial coordinates, in au (the repo frame doctrine,
`galnav/units.py`). OpenSpace's scene graph instead measures everything in
METRES along GALACTIC axes (same origin once the node is parented to its
`SolarSystemBarycenter`). Same origin, different units, axes tilted by a
fixed rotation — so the exporter does exactly two things:

1. **Rotate.** `v_gal = R @ v_icrs`, where R is the classic Hipparcos
   (Vol. 1, Sect. 1.5.3) equatorial→galactic matrix — the very numbers
   OpenSpace ships in its own source (modules/skybrowser/src/utility.cpp),
   so we speak its dialect exactly. A rotation only tilts axes; lengths
   never change, and a test pins |out| = |in| to machine precision.
2. **Scale.** au → metres via `AU_KM * 1000`, reusing the repo's single
   owner of the au (`galnav.units.AU_KM`) rather than typing the number a
   second time.

**How we know the rotation is right.** astropy contains its own,
independently written galactic-frame transform. The test feeds 10 random
directions through both and demands agreement. Measured disagreement:
worst 1.19e-7 relative = **0.025 arcsec** — that is a genuine
definition-level difference (astropy's galactic frame is defined through
the old FK4 B1950 system; the Hipparcos matrix is the modern direct
definition), about 800 km at New Horizons range, or 1/10,000 of the marker
sphere we draw. The test's tolerance (5e-7, against the vector norm) sits
just above that measured floor and 7 orders of magnitude below what a
transposed or mislabeled-axis matrix would produce, which is the mistake
the test actually guards against. Documented in the test docstring.

**Why the spheres carry a tiny PNG.** OpenSpace's plain `RenderableSphere`
cannot take a solid colour — it wants a texture. So the exporter writes two
8x8 solid-colour PNGs (amber = recovered, cyan = truth, the GUI's own
palette) next to the .asset and uses `RenderableSphereImageLocal`. A
`RenderableNodeLine` connects the two markers: the 0.39 au miss, drawn as
a physical line you can fly along.

**The booth asset.** Generated from the frozen 12-frame New Horizons
numbers (`python -m gui.nh_demo`, this box, 2026-07-20):

    python -m gui.openspace_export \
        --x 13.386 --y -42.369 --z -16.486 \
        --label "GalNav fix (12 LORRI frames, 0.39 au miss)" \
        --truth-x 13.5495 --truth-y -42.0195 --truth-z -16.4573 \
        --truth-label "New Horizons (JPL truth)" \
        --out galnav_fix.asset

Load: copy `galnav_fix.asset` + the two PNGs into OpenSpace's
`user/data/assets/`, then enable it from the asset panel (or
`openspace.asset.add("galnav_fix")` in the in-app Lua console). The
generated files are throwaway artifacts (one CLI line recreates them), so
they are not committed.

**Tests** (`tests_gui/test_openspace_export.py`, 7, all offline):
au-metre constant reuses `AU_KM`; rotation vs astropy (measured-floor
tolerance, above); pure-rotation norm preservation; asset text contains
the barycenter parent + galactic-metre positions and NOT the raw au
values (the classic wrong-frame bug); truth marker + miss line appear
only when a truth vector is supplied; Lua braces balanced; CLI writes the
file + textures. Truth wall: the module imports `galnav.units` only, and
the existing `tests_gui/test_wall.py` sweep covers it automatically.

**Honest limits.** The marker is a static snapshot at the export epoch —
OpenSpace animates time, and our marker deliberately does not move with
it (the fix is a single-epoch statement; NH itself keeps flying). If the
booth clock is scrubbed decades away, the marker-to-spacecraft gap on
screen stops meaning "the miss." Demo script: park time near 2020-04-23
(the LORRI epochs) when telling the miss story.
