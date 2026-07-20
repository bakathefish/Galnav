"""Export a GalNav position fix into an OpenSpace .asset file.

OpenSpace (openspaceproject.com) renders the real solar system + Gaia stars
with a seamlessly zooming camera -- the booth show layer. Its scene graph
lives in GALACTIC-frame METRES, with solar-system objects parented to
SolarSystemBarycenter (OpenSpace source: the scene root is galactic; the
J2000-equatorial<->galactic matrix ships in modules/skybrowser/src/
utility.cpp). GalNav fixes are barycentric ICRS-equatorial au (the repo's
frame doctrine, galnav/units.py), so this exporter performs exactly two
conversions -- the fixed ICRS->galactic rotation and au->metres via the
repo-owned AU_KM -- and emits a self-contained Lua asset:

  * an amber sphere + label at the RECOVERED fix,
  * optionally a cyan sphere + label at the TRUTH position (e.g. JPL), and
  * a line between the two -- the miss, made visible in a planetarium.

OpenSpace's plain RenderableSphere cannot take a solid colour (it wants a
texture), so the exporter also writes two tiny solid-colour PNGs next to
the asset and uses RenderableSphereImageLocal. Drop the .asset (plus PNGs)
into OpenSpace's ``user/data/assets/`` folder and enable it from the
in-app asset panel, or run ``openspace.asset.add(...)`` in the Lua console.

Usage (recovered fix only):
    python -m gui.openspace_export --x 13.4 --y -41.8 --z -16.3 \
        --label "GalNav fix" --out galnav_fix.asset

With a truth marker (the New Horizons booth story):
    python -m gui.openspace_export --x ... --y ... --z ... \
        --truth-x 13.5495 --truth-y -42.0195 --truth-z -16.4573 \
        --truth-label "New Horizons (JPL)" --out galnav_fix.asset

Navigator side of the truth wall: imports galnav.units only.
"""

import argparse
from pathlib import Path

import numpy as np

from galnav.units import AU_KM

AU_M = AU_KM * 1000.0

# ICRS/J2000-equatorial -> galactic rotation (rows = galactic axes in
# equatorial coordinates; Hipparcos Vol. 1 Sect. 1.5.3, the same matrix
# OpenSpace ships in modules/skybrowser/src/utility.cpp). v_gal = R @ v_icrs.
ICRS_TO_GALACTIC = np.array(
    [
        [-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
        [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
        [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669],
    ]
)

AMBER = (255, 166, 38)  # the GUI's "recovered" accent
CYAN = (46, 216, 255)  # the GUI's "truth" accent
AMBER_PNG = "galnav_amber.png"
CYAN_PNG = "galnav_cyan.png"


def icrs_au_to_galactic_m(x_au):
    """Barycentric ICRS-equatorial position (au) -> galactic metres.

    Pure rotation + scale; barycentre stays the origin on both sides.
    """
    x_au = np.asarray(x_au, dtype=float)
    return (ICRS_TO_GALACTIC @ x_au) * AU_M


def _pos(v):
    return ", ".join(f"{c:.6e}" for c in v)


def _rgb01(rgb):
    return ", ".join(f"{c / 255.0:.4f}" for c in rgb)


def _marker(
    ident,
    label,
    gal_m,
    png_name,
    rgb,
    radius_m,
    parent_expr=None,
    texture_expr=None,
):
    """Lua for one marker: hidden position node + textured sphere + label.

    parent_expr / texture_expr are Lua EXPRESSIONS (not values). They default to
    the .asset idioms this exporter emits -- the parent via the sun-transforms
    require, the texture via ``asset.resource`` -- so the asset output is
    unchanged. gui.openspace_link overrides them for RUNTIME luascript pushes,
    where asset.resource does not resolve: it passes a plain "SolarSystemBary-
    center" parent string and an ABSOLUTE texture path, reusing this one marker
    idiom instead of duplicating the sphere/label Lua.
    """
    if parent_expr is None:
        parent_expr = "sunTransforms.SolarSystemBarycenter.Identifier"
    if texture_expr is None:
        texture_expr = f'asset.resource("{png_name}")'
    return f"""
local {ident}Pos = {{
  Identifier = "{ident}Pos",
  Parent = {parent_expr},
  Transform = {{
    Translation = {{
      Type = "StaticTranslation",
      Position = {{ {_pos(gal_m)} }}
    }}
  }},
  GUI = {{ Name = "{label} (position)", Path = "/GalNav", Hidden = true }}
}}

local {ident} = {{
  Identifier = "{ident}",
  Parent = "{ident}Pos",
  Renderable = {{
    Type = "RenderableSphereImageLocal",
    Enabled = true,
    Texture = {texture_expr},
    Size = {radius_m:.6e},
    Segments = 32,
    Opacity = 0.92
  }},
  GUI = {{ Name = "{label}", Path = "/GalNav" }}
}}

local {ident}Label = {{
  Identifier = "{ident}Label",
  Parent = "{ident}Pos",
  Renderable = {{
    Type = "RenderableLabel",
    Enabled = true,
    Text = "{label}",
    Color = {{ {_rgb01(rgb)} }},
    FontSize = 70.0,
    Size = 11.0,
    MinMaxSize = {{ 4, 60 }},
    OrientationOption = "Camera View Direction",
    EnableFading = false
  }},
  GUI = {{ Name = "{label} label", Path = "/GalNav" }}
}}
"""


def asset_text(recovered_au, label, truth_au=None, truth_label="Truth", radius_m=8.0e9):
    """The complete Lua .asset text for a fix (and optional truth) marker."""
    rec_gal = icrs_au_to_galactic_m(recovered_au)
    nodes = ["GalNavFixPos", "GalNavFix", "GalNavFixLabel"]
    body = ['local sunTransforms = asset.require("scene/solarsystem/sun/transforms")']
    body.append(_marker("GalNavFix", label, rec_gal, AMBER_PNG, AMBER, radius_m))

    if truth_au is not None:
        tru_gal = icrs_au_to_galactic_m(truth_au)
        body.append(
            _marker("GalNavTruth", truth_label, tru_gal, CYAN_PNG, CYAN, radius_m)
        )
        nodes += ["GalNavTruthPos", "GalNavTruth", "GalNavTruthLabel"]
        body.append(f"""
local GalNavMissLine = {{
  Identifier = "GalNavMissLine",
  Parent = sunTransforms.SolarSystemBarycenter.Identifier,
  Renderable = {{
    Type = "RenderableNodeLine",
    Enabled = true,
    StartNode = "GalNavFixPos",
    EndNode = "GalNavTruthPos",
    Color = {{ 1.0, 1.0, 1.0 }},
    LineWidth = 3.0
  }},
  GUI = {{ Name = "GalNav miss line", Path = "/GalNav" }}
}}
""")
        nodes.append("GalNavMissLine")

    adds = "\n".join(f"  openspace.addSceneGraphNode({n})" for n in nodes)
    removes = "\n".join(
        f"  openspace.removeSceneGraphNode({n})" for n in reversed(nodes)
    )
    exports = "\n".join(f"asset.export({n})" for n in nodes)
    body.append(f"""
asset.onInitialize(function()
{adds}
end)

asset.onDeinitialize(function()
{removes}
end)

{exports}
""")
    return "\n".join(body)


def _write_marker_png(path, rgb):
    """An 8x8 solid-colour texture (OpenSpace spheres need a texture)."""
    from PIL import Image

    Image.new("RGB", (8, 8), rgb).save(path)


def write_asset(
    out_path, recovered_au, label, truth_au=None, truth_label="Truth", radius_m=8.0e9
):
    """Write the .asset plus its two texture PNGs next to it."""
    out_path = Path(out_path)
    out_path.write_text(
        asset_text(
            recovered_au,
            label,
            truth_au=truth_au,
            truth_label=truth_label,
            radius_m=radius_m,
        ),
        encoding="utf-8",
    )
    _write_marker_png(out_path.parent / AMBER_PNG, AMBER)
    if truth_au is not None:
        _write_marker_png(out_path.parent / CYAN_PNG, CYAN)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export a GalNav fix as an OpenSpace .asset marker."
    )
    parser.add_argument(
        "--x", type=float, required=True, help="recovered barycentric ICRS x, au"
    )
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--z", type=float, required=True)
    parser.add_argument("--label", default="GalNav fix")
    parser.add_argument("--truth-x", type=float, default=None)
    parser.add_argument("--truth-y", type=float, default=None)
    parser.add_argument("--truth-z", type=float, default=None)
    parser.add_argument("--truth-label", default="Truth")
    parser.add_argument(
        "--radius-m", type=float, default=8.0e9, help="marker sphere radius, metres"
    )
    parser.add_argument("--out", default="galnav_fix.asset")
    args = parser.parse_args(argv)

    truth = None
    truth_parts = [args.truth_x, args.truth_y, args.truth_z]
    if any(p is not None for p in truth_parts):
        if any(p is None for p in truth_parts):
            parser.error("--truth-x/--truth-y/--truth-z must all be given")
        truth = np.array(truth_parts)

    out = write_asset(
        args.out,
        np.array([args.x, args.y, args.z]),
        args.label,
        truth_au=truth,
        truth_label=args.truth_label,
        radius_m=args.radius_m,
    )
    print(f"wrote {out} (+ texture PNGs alongside)")
    print(
        "Load in OpenSpace: copy these files into user/data/assets/ and "
        "enable 'galnav_fix' in the asset panel, or run "
        f"openspace.asset.add('{out.stem}') in the Lua console."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
