"""OpenSpace live bridge (gui.openspace_link): pure Lua builders + a tiny
newline-framed TCP client. Offline and deterministic -- OpenSpace is NOT
required to run:

  * the Lua builders are pure string functions (no sockets, no OpenSpace);
  * is_running() is probed against a guaranteed-dead port;
  * run_lua() is exercised against an in-process fake TCP server, so the exact
    wire framing (newline-terminated JSON, the {topic,type,payload} envelope
    the OpenSpace Server module expects) is pinned without a real planetarium.

The wire framing is the one the official client uses: each JSON message is
terminated by a single '\\n' (OpenSpace/openspace-api-python
src/openspace/src/socketwrapper.py: ``self._client.sendall((message + "\\n")
.encode())`` on send, split on ``"\\n"`` on receive); the message envelope is
``{"topic": <int>, "type": "luascript", "payload": {"script": ...}}`` (api.py
startTopic). These tests are the executable record of that contract.
"""

import json
import os
import re
import socket
import threading

import numpy as np

from galnav.units import AU_KM
from gui import openspace_link as osl
from gui.openspace_export import icrs_au_to_galactic_m

AU_M = AU_KM * 1000.0
_PC_AU = 206264.806  # au per parsec


# ------------------------------------------------------------- geometry fixtures
def _u(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _star_at(dist_pc, direction):
    """A star position (au) at dist_pc parsecs in a given ICRS direction."""
    return (_u(direction) * dist_pc * _PC_AU).tolist()


STARS = [
    {"name": "Proxima Cen", "star_pos_au": _star_at(1.30, [0.42, -0.69, 0.59])},
    {"name": "Wolf 359", "star_pos_au": _star_at(2.41, [-0.31, 0.80, 0.51])},
]

LINES = [
    {
        "star_name": "Proxima Cen",
        "star_pos_au": STARS[0]["star_pos_au"],
        "direction_unit": _u([0.41, -0.70, 0.58]).tolist(),
    },
    {
        "star_name": "Wolf 359",
        "star_pos_au": STARS[1]["star_pos_au"],
        "direction_unit": _u([-0.30, 0.79, 0.53]).tolist(),
    },
]

RECOVERED = np.array([13.4, -41.8, -16.3])
TRUTH = np.array([13.5495, -42.0195, -16.4573])


def _balanced(text):
    return text.count("{") == text.count("}") and text.count("(") == text.count(")")


def _identifiers(text):
    """Every Identifier = "X" value declared in a Lua block."""
    return re.findall(r'Identifier\s*=\s*"([^"]+)"', text)


def _free_dead_port():
    """A localhost port that is guaranteed closed (bound then released)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --------------------------------------------------------------- message framing
def test_lua_message_is_newline_framed_json():
    """A pushed message is exactly ONE newline-terminated JSON object with the
    OpenSpace envelope: top-level topic:int + type:'luascript', payload.script
    carrying the Lua, and return:false (we fire-and-forget, awaiting no reply)."""
    script = "openspace.printInfo('galnav')"
    msg = osl.lua_message(script)
    assert isinstance(msg, (bytes, bytearray))
    assert msg.endswith(b"\n")
    assert msg.count(b"\n") == 1  # exactly one message, one delimiter
    obj = json.loads(msg.decode("utf-8").rstrip("\n"))
    assert isinstance(obj["topic"], int)
    assert obj["type"] == "luascript"  # top-level, per api.py startTopic
    assert obj["payload"]["script"] == script
    assert obj["payload"]["return"] is False


# ------------------------------------------------------------- socket: is_running
def test_is_running_false_on_dead_port():
    assert osl.is_running(port=_free_dead_port(), timeout=0.2) is False


def test_run_lua_false_when_nothing_listening():
    """run_lua degrades honestly (returns False, never raises) when OpenSpace is
    not there -- the web layer turns that into a 'start OpenSpace' message."""
    assert (
        osl.run_lua("openspace.printInfo('x')", port=_free_dead_port(), timeout=0.2)
        is False
    )


def test_run_lua_sends_framed_script_to_fake_server():
    """Against a tiny in-process TCP server, run_lua delivers exactly the framed
    bytes lua_message() produces -- the end-to-end wire contract, no OpenSpace."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    received = []

    def serve():
        conn, _ = srv.accept()
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        received.append(buf)
        conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    script = "openspace.printInfo('hello galnav')"
    ok = osl.run_lua(script, host="127.0.0.1", port=port, timeout=2.0)
    t.join(2.0)
    srv.close()
    assert ok is True
    assert received and received[0].endswith(b"\n")
    obj = json.loads(received[0].decode("utf-8").rstrip("\n"))
    assert obj["type"] == "luascript"
    assert obj["payload"]["script"] == script


# ---------------------------------------------------------------- clear (item 1)
def test_clear_lua_removes_galnavlive_and_is_guarded():
    """The clear script targets ONLY GalNavLive* nodes and is idempotent: every
    removal is guarded (hasSceneGraphNode + pcall) so clearing when absent is a
    no-op, never a duplicate/absent error on re-push."""
    s = osl.clear_lua()
    assert "GalNavLive" in s
    assert "removeSceneGraphNode" in s
    assert "hasSceneGraphNode" in s and "pcall" in s
    assert _balanced(s)


# ---------------------------------------------------------------- stars (item 1)
def test_stars_lua_positions_are_galactic_metres():
    """Every star marker sits at the GALACTIC-METRE conversion of its aged ICRS
    au position (the classic wrong-frame bug the exporter also pins): the
    galactic-metre numbers appear, the raw au numbers do not."""
    text = osl.stars_lua(STARS)
    for star in STARS:
        gal = icrs_au_to_galactic_m(np.array(star["star_pos_au"]))
        for comp in gal:
            assert f"{comp:.6e}" in text
        # the raw au components (parsec-scale) must NOT appear as positions
        assert f"{star['star_pos_au'][0]:.6e}" not in text
    assert _balanced(text)


def test_stars_lua_labels_and_renderable_and_clear_prefix():
    text = osl.stars_lua(STARS)
    assert "RenderableSphereImageLocal" in text
    assert "RenderableLabel" in text
    for star in STARS:
        assert star["name"] in text  # the human label survives
    # a stars push clears any prior GalNavLive* first (idempotent re-push)
    assert "removeSceneGraphNode" in text


def test_stars_lua_texture_is_absolute_path_not_asset_resource():
    """luascript-pushed renderables need an ABSOLUTE Texture path -- asset.resource
    only resolves inside .asset files, so it must be absent here."""
    text = osl.stars_lua(STARS)
    m = re.search(r'Texture\s*=\s*"([^"]+)"', text)
    assert m is not None, "a RenderableSphereImageLocal Texture path must be present"
    assert os.path.isabs(m.group(1))
    assert m.group(1).lower().endswith(".png")
    assert "asset.resource" not in text


def test_stars_all_identifiers_are_galnavlive():
    for ident in _identifiers(osl.stars_lua(STARS)):
        assert ident.startswith("GalNavLive"), ident


# ---------------------------------------------------------------- lines (item 1)
def test_lines_lua_endpoint_math_through_rotation():
    """Each line draws star -> observer: anchor at the star, endpoint at
    anchor - (|anchor| + 100 au) * direction_unit (direction_unit points
    observer->star, so the observer-ward ray is MINUS it -- exactly
    line_of_position_summary). Both ends must be the galactic-metre conversion."""
    text = osl.lines_lua(LINES)
    for ln in LINES:
        anchor = np.array(ln["star_pos_au"], dtype=float)
        d = np.array(ln["direction_unit"], dtype=float)
        endpoint = anchor - (np.linalg.norm(anchor) + 100.0) * d
        for comp in icrs_au_to_galactic_m(anchor):
            assert f"{comp:.6e}" in text
        for comp in icrs_au_to_galactic_m(endpoint):
            assert f"{comp:.6e}" in text
    assert "RenderableNodeLine" in text
    assert _balanced(text)


def test_lines_all_identifiers_are_galnavlive():
    text = osl.lines_lua(LINES)
    for ident in _identifiers(text):
        assert ident.startswith("GalNavLive"), ident
    assert "removeSceneGraphNode" in text  # clear-before-add prefix


# ------------------------------------------------------------------ fix (item 1)
def test_fix_lua_recovered_only():
    text = osl.fix_lua(RECOVERED)
    assert "GalNavLiveFix" in text
    # the clear roster names GalNavLiveTruth (to wipe a stale one), but no truth
    # marker is ADDED and no miss line is drawn unless a truth vector is given
    assert "openspace.addSceneGraphNode(GalNavLiveTruth)" not in text
    assert "Truth (JPL)" not in text
    assert "RenderableNodeLine" not in text  # no miss line without truth
    for comp in icrs_au_to_galactic_m(RECOVERED):
        assert f"{comp:.6e}" in text
    assert _balanced(text)


def test_fix_lua_with_truth_adds_marker_and_miss_line():
    text = osl.fix_lua(RECOVERED, truth_au=TRUTH)
    assert "GalNavLiveTruth" in text
    assert "RenderableNodeLine" in text  # the miss, made flyable
    for comp in icrs_au_to_galactic_m(TRUTH):
        assert f"{comp:.6e}" in text
    assert _balanced(text)


def test_fix_lua_flyto_is_present_and_failure_tolerant():
    """After the fix push we fly the camera toward the fix node; the call is
    pcall-wrapped so a missing pathnavigation API can never break the push."""
    text = osl.fix_lua(RECOVERED)
    assert "pathnavigation.flyTo" in text
    assert "pcall" in text  # fly-to is failure-tolerant
    assert "GalNavLiveFixPos" in text  # flies to the fix's position node


def test_fix_all_identifiers_are_galnavlive():
    text = osl.fix_lua(RECOVERED, truth_au=TRUTH)
    for ident in _identifiers(text):
        assert ident.startswith("GalNavLive"), ident


# --------------------------------------------------------- node id bookkeeping
def test_node_id_helpers_are_galnavlive_prefixed():
    """The identifier rosters the web layer reports back as 'pushed' must match
    the builders' naming and all be GalNavLive-prefixed."""
    for ident in osl.star_node_ids(3):
        assert ident.startswith("GalNavLiveStar")
    for ident in osl.line_node_ids(2):
        assert ident.startswith("GalNavLiveLine")
    assert "GalNavLiveFix" in osl.fix_node_ids(with_truth=False)
    assert "GalNavLiveTruth" in osl.fix_node_ids(with_truth=True)


# --------------------------------------------------------- texture bookkeeping
def test_marker_texture_paths_are_absolute_pngs_without_writing(tmp_path):
    """The path helper is pure (no file write, so builders/tests need no PIL):
    it just reports where the amber/cyan textures live, as absolute .png paths."""
    paths = osl.marker_texture_paths()
    assert set(paths) == {"amber", "cyan"}
    for p in paths.values():
        assert os.path.isabs(p) and p.lower().endswith(".png")
