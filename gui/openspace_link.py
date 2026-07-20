"""Live bridge from GalNav to a RUNNING OpenSpace planetarium.

Where gui/openspace_export.py writes a static .asset file for the user to drag
into OpenSpace, THIS module pushes the same geometry into an already-open
OpenSpace over its Server module socket, so the web app's "Show ... in OpenSpace"
buttons make markers appear live while the user walks the pipeline pages.

WIRE PROTOCOL (verified against the official client, OpenSpace/openspace-api-
python, src/openspace/src/socketwrapper.py + api.py, and the OpenSpace Server
module source):
  * transport: a plain TCP socket to 127.0.0.1:4681 (localhost is in the server's
    default AllowAddresses, no password);
  * framing: each message is one JSON object terminated by a single '\\n' -- the
    client does ``sendall((json + "\\n").encode())`` and splits incoming data on
    '\\n'. That is the whole framing; there is no length prefix on this socket.
  * envelope: ``{"topic": <int>, "type": "luascript", "payload": {"script": <lua>,
    "return": false, "shouldBeSynchronized": true}}`` -- ``type`` sits at the top
    level (api.py startTopic), and the ``luascript`` topic runs the payload's
    ``script`` on the OpenSpace Lua state (openspace.addSceneGraphNode /
    removeSceneGraphNode / pathnavigation.flyTo / ...).

Because every push here is fire-and-forget (return:false, no reply awaited), the
client is a few lines of the standard-library ``socket`` -- NO asyncio, NO new
dependency. This deliberately keeps the web backend stdlib-only (the whole demo's
offline guarantee), and it means importing this module never requires OpenSpace,
a network, or the ``openspace-api`` PyPI package to be installed. The official
asyncio library exists for a *persistent* callback connection; a one-shot marker
push does not need it.

FRAME + MARKER REUSE: the barycentric-ICRS-au -> galactic-metre conversion and
the sphere/label marker Lua are REUSED from gui.openspace_export (its rotation is
verified against astropy). This module only adapts them for RUNTIME luascript:
the parent is the plain "SolarSystemBarycenter" identifier string and textures
are ABSOLUTE paths (asset.resource resolves only inside .asset files).

Every node identifier this module creates starts with "GalNavLive", and every
stage push is PREFIXED with a guarded clear (hasSceneGraphNode + pcall) that
removes any existing GalNavLive* nodes -- so re-pushing a stage, or switching
stages, never raises a duplicate/absent-identifier error.

Truth wall: navigator side. Imports gui.openspace_export (galnav.units only) and
numpy; never galnav.truth.
"""

import json
import socket
from pathlib import Path

import numpy as np

from gui.openspace_export import (
    AMBER,
    CYAN,
    _marker,
    _pos,
    _rgb01,
    icrs_au_to_galactic_m,
)

OPENSPACE_HOST = "127.0.0.1"
OPENSPACE_PORT = 4681  # the Server module TCP interface (openspace.cfg default)

# All live node identifiers share this prefix so the clear script can target only
# our nodes and never touch OpenSpace's own scene graph.
LIVE_PREFIX = "GalNavLive"
STAR_PREFIX = "GalNavLiveStar"
LINE_PREFIX = "GalNavLiveLine"
FIX_ID = "GalNavLiveFix"
TRUTH_ID = "GalNavLiveTruth"
MISS_ID = "GalNavLiveMissLine"

# Marker sphere radii, metres. A fix sits ~47 au out, so 8e9 m reads there (same
# as the exporter). Stars sit PARSECS out (Proxima ~3.086e16 m); a marker must be
# huge to subtend a visible angle at that range, so STAR_RADIUS_M = 3e14 m
# (~2000 au) shows as a small glow at ~1 pc. The RenderableLabel (screen-space
# MinMaxSize-clamped) is what actually names the star at any distance; the sphere
# is only a pickable anchor.
FIX_RADIUS_M = 8.0e9
STAR_RADIUS_M = 3.0e14

# How far past the star, toward (and beyond) the Sun, to draw a line of position.
# Mirrors gui.locate._LOP_DISPLAY_MARGIN_AU (100 au clears Neptune + the New
# Horizons distance), so the drawn ray matches line_of_position_summary exactly.
_LOP_MARGIN_AU = 100.0

# Runtime marker textures live in a gitignored dir (OpenSpace spheres need a
# texture, not a solid colour). Written on demand by ensure_marker_textures().
REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = REPO_ROOT / ".galnav_openspace_runtime"
_AMBER_PNG = "galnav_live_amber.png"
_CYAN_PNG = "galnav_live_cyan.png"


# ------------------------------------------------------------------ textures
def marker_texture_paths():
    """Absolute paths to the amber/cyan marker textures -- PURE (no file write).

    Builders and tests use this to reference the texture; the file itself is
    written separately by ensure_marker_textures() (which needs Pillow + disk).
    Returns {"amber": <abs .png>, "cyan": <abs .png>}.
    """
    return {
        "amber": str(RUNTIME_DIR / _AMBER_PNG),
        "cyan": str(RUNTIME_DIR / _CYAN_PNG),
    }


def ensure_marker_textures():
    """Write the amber/cyan marker PNGs if absent; return their absolute paths.

    Reuses the exporter's tiny solid-colour PNG writer (Pillow). Called by the
    web layer just before a live push, never at import time.
    """
    from gui.openspace_export import _write_marker_png

    paths = marker_texture_paths()
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not Path(paths["amber"]).exists():
        _write_marker_png(paths["amber"], AMBER)
    if not Path(paths["cyan"]).exists():
        _write_marker_png(paths["cyan"], CYAN)
    return paths


def _lua_path(p):
    """A Lua string literal for a filesystem path.

    Forward-slashes it (OpenSpace/ghoul accept '/' on Windows, and it avoids Lua
    treating a backslash as an escape) and quotes it.
    """
    return '"' + str(p).replace("\\", "/").replace('"', '\\"') + '"'


# --------------------------------------------------------------- wire client
def lua_message(script, want_return=False):
    """The exact bytes to put on the OpenSpace socket to run ``script``.

    One JSON object, the {topic,type,payload} envelope, terminated by a single
    newline (the delimiter the OpenSpace Server socket reads on). want_return is
    false: we push and move on, awaiting no reply.
    """
    obj = {
        "topic": 1,
        "type": "luascript",
        "payload": {
            "script": script,
            "return": bool(want_return),
            "shouldBeSynchronized": True,
        },
    }
    return (json.dumps(obj) + "\n").encode("utf-8")


def is_running(host=OPENSPACE_HOST, port=OPENSPACE_PORT, timeout=0.3):
    """True iff something is listening on the OpenSpace socket (cheap TCP probe)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_lua(script, host=OPENSPACE_HOST, port=OPENSPACE_PORT, timeout=0.3):
    """Send one Lua script to OpenSpace. Returns True on success, False if the
    connection could not be made or the send failed -- never raises, so the web
    layer can report an honest 'start OpenSpace' instead of a stack trace."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(lua_message(script))
        return True
    except OSError:
        return False


# ----------------------------------------------------------- Lua node helpers
def _add(idents):
    """openspace.addSceneGraphNode() for each local table, parents before kids."""
    return "\n".join(f"openspace.addSceneGraphNode({i})" for i in idents)


def _static_pos_node(ident, gui_name, gal_m):
    """A hidden position-only node at a galactic-metre point under the barycentre.

    The line stages need standalone anchor/endpoint nodes (the RenderableNodeLine
    references them by identifier); this is the same StaticTranslation idiom the
    exporter's marker position node uses, without the sphere/label.
    """
    return f"""
local {ident} = {{
  Identifier = "{ident}",
  Parent = "SolarSystemBarycenter",
  Transform = {{
    Translation = {{
      Type = "StaticTranslation",
      Position = {{ {_pos(gal_m)} }}
    }}
  }},
  GUI = {{ Name = "{gui_name}", Path = "/GalNav", Hidden = true }}
}}"""


def _node_line(ident, start_ident, end_ident, gui_name, rgb, width=2.0):
    """A RenderableNodeLine between two existing position nodes."""
    return f"""
local {ident} = {{
  Identifier = "{ident}",
  Parent = "SolarSystemBarycenter",
  Renderable = {{
    Type = "RenderableNodeLine",
    Enabled = true,
    StartNode = "{start_ident}",
    EndNode = "{end_ident}",
    Color = {{ {_rgb01(rgb)} }},
    LineWidth = {width:.1f}
  }},
  GUI = {{ Name = "{gui_name}", Path = "/GalNav" }}
}}"""


def _label(name):
    return name if name else "star"


# ------------------------------------------------------------------ builders
def clear_lua(max_index=64):
    """Lua that removes every GalNavLive* node, idempotently.

    Each removal is guarded (hasSceneGraphNode then a pcall'd removeSceneGraphNode)
    so clearing when a node is absent is a no-op -- re-pushing a stage never errors
    on a duplicate identifier, and switching stages wipes the previous one. The
    fixed fix/truth/miss roster plus an indexed sweep (0..max_index) of the
    star/line identifiers covers every node the builders below can create; the
    child renderables are removed before their parent position nodes.
    """
    fixed = [
        MISS_ID,
        f"{FIX_ID}Label",
        FIX_ID,
        f"{FIX_ID}Pos",
        f"{TRUTH_ID}Label",
        TRUTH_ID,
        f"{TRUTH_ID}Pos",
    ]
    removes = "\n".join(f'  _galnavRemove("{n}")' for n in fixed)
    return f"""local function _galnavRemove(id)
  if openspace.hasSceneGraphNode(id) then
    pcall(openspace.removeSceneGraphNode, id)
  end
end
{removes}
for i = 0, {max_index} do
  _galnavRemove("{STAR_PREFIX}" .. i .. "Label")
  _galnavRemove("{STAR_PREFIX}" .. i)
  _galnavRemove("{STAR_PREFIX}" .. i .. "Pos")
  _galnavRemove("{LINE_PREFIX}" .. i)
  _galnavRemove("{LINE_PREFIX}" .. i .. "A")
  _galnavRemove("{LINE_PREFIX}" .. i .. "B")
end
"""


def stars_lua(stars, texture=None, radius_m=STAR_RADIUS_M, clear=True):
    """Amber labelled markers at each identified star's aged barycentric position.

    stars: list of {"name"|"star_name", "star_pos_au":[x,y,z]} (au, ICRS). Each
    becomes a hidden position node + amber sphere + name label at the galactic-
    metre conversion of star_pos_au. These sit parsecs out (see STAR_RADIUS_M).
    """
    if texture is None:
        texture = marker_texture_paths()["amber"]
    parts = [clear_lua()] if clear else []
    tex = _lua_path(texture)
    for i, s in enumerate(stars):
        ident = f"{STAR_PREFIX}{i}"
        gal = icrs_au_to_galactic_m(np.asarray(s["star_pos_au"], dtype=float))
        label = _label(s.get("name") or s.get("star_name"))
        parts.append(
            _marker(
                ident,
                label,
                gal,
                None,
                AMBER,
                radius_m,
                parent_expr='"SolarSystemBarycenter"',
                texture_expr=tex,
            )
        )
        parts.append(_add([f"{ident}Pos", ident, f"{ident}Label"]))
    return "\n".join(parts)


def lines_lua(lines, clear=True):
    """One amber line of position per input line.

    lines: list of {"star_name"|"name", "star_pos_au":[3], "direction_unit":[3]}.
    direction_unit points observer->star, so the observer-ward ray is MINUS it:
    the segment runs from the star (anchor) to anchor - (|anchor| + 100 au) *
    direction_unit, i.e. through the plausible-observer window and out past the
    Sun -- exactly gui.locate.line_of_position_summary's geometry, drawn as a
    RenderableNodeLine between two galactic-metre position nodes.
    """
    parts = [clear_lua()] if clear else []
    for i, ln in enumerate(lines):
        anchor = np.asarray(ln["star_pos_au"], dtype=float)
        d = np.asarray(ln["direction_unit"], dtype=float)
        d = d / np.linalg.norm(d)
        endpoint = anchor - (np.linalg.norm(anchor) + _LOP_MARGIN_AU) * d
        a_gal = icrs_au_to_galactic_m(anchor)
        e_gal = icrs_au_to_galactic_m(endpoint)
        ident = f"{LINE_PREFIX}{i}"
        label = _label(ln.get("star_name") or ln.get("name"))
        parts.append(_static_pos_node(f"{ident}A", f"{label} (star)", a_gal))
        parts.append(_static_pos_node(f"{ident}B", f"{label} (observer end)", e_gal))
        parts.append(
            _node_line(
                ident,
                f"{ident}A",
                f"{ident}B",
                f"{label} line of position",
                AMBER,
            )
        )
        parts.append(_add([f"{ident}A", f"{ident}B", ident]))
    return "\n".join(parts)


def fix_lua(
    recovered_au,
    truth_au=None,
    texture_amber=None,
    texture_cyan=None,
    radius_m=FIX_RADIUS_M,
    fly_to=True,
    clear=True,
):
    """The recovered fix (amber) + optional truth (cyan) + white miss line.

    Reuses the exporter's marker idiom for both spheres. When truth_au is given, a
    white RenderableNodeLine draws the miss between the two position nodes. After
    the adds, a pcall'd pathnavigation.flyTo carries the camera to the fix -- the
    pcall makes the fly-to failure-tolerant (a missing/renamed API can never break
    the push). Identifiers: GalNavLiveFix*, GalNavLiveTruth*, GalNavLiveMissLine.
    """
    amber = texture_amber or marker_texture_paths()["amber"]
    parts = [clear_lua()] if clear else []
    rec_gal = icrs_au_to_galactic_m(np.asarray(recovered_au, dtype=float))
    parts.append(
        _marker(
            FIX_ID,
            "GalNav fix",
            rec_gal,
            None,
            AMBER,
            radius_m,
            parent_expr='"SolarSystemBarycenter"',
            texture_expr=_lua_path(amber),
        )
    )
    parts.append(_add([f"{FIX_ID}Pos", FIX_ID, f"{FIX_ID}Label"]))
    if truth_au is not None:
        cyan = texture_cyan or marker_texture_paths()["cyan"]
        tru_gal = icrs_au_to_galactic_m(np.asarray(truth_au, dtype=float))
        parts.append(
            _marker(
                TRUTH_ID,
                "Truth (JPL)",
                tru_gal,
                None,
                CYAN,
                radius_m,
                parent_expr='"SolarSystemBarycenter"',
                texture_expr=_lua_path(cyan),
            )
        )
        parts.append(_add([f"{TRUTH_ID}Pos", TRUTH_ID, f"{TRUTH_ID}Label"]))
        parts.append(
            _node_line(
                MISS_ID,
                f"{FIX_ID}Pos",
                f"{TRUTH_ID}Pos",
                "GalNav miss line",
                (255, 255, 255),
                width=3.0,
            )
        )
        parts.append(_add([MISS_ID]))
    if fly_to:
        parts.append(f'pcall(openspace.pathnavigation.flyTo, "{FIX_ID}Pos", 4.0)')
    return "\n".join(parts)


# ------------------------------------------------------- node id bookkeeping
def star_node_ids(n):
    """The visible star sphere identifiers a stars push creates (for reporting)."""
    return [f"{STAR_PREFIX}{i}" for i in range(n)]


def line_node_ids(n):
    """The line identifiers a lines push creates (for reporting)."""
    return [f"{LINE_PREFIX}{i}" for i in range(n)]


def fix_node_ids(with_truth=False):
    """The visible identifiers a fix push creates (for reporting)."""
    ids = [FIX_ID]
    if with_truth:
        ids += [TRUTH_ID, MISS_ID]
    return ids
