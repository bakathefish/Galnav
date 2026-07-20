"""Static, offline tests for the 3-D 'Where in Space' view (gui/web/where-in-space.html).

These are DELIBERATELY static string/structure assertions on the served file --
no browser, no network, deterministic. The view's dynamic behaviour (wheel zoom
working on first hover, zoom staying centred on the Sun, the truth/ray markers)
was verified live in a real browser during development; these tests pin the
source hooks that make that behaviour so a later edit cannot silently drop them.

The file is fetched through the SAME static route the web app serves it from
(gui.webapp.static_file), so a regression in the route or the file both fail here.
"""

from gui import webapp


def _served_source():
    """The where-in-space.html the browser would receive, decoded to text.

    Goes through the real static route (allowlist + Content-Type), so this both
    proves the file is servable and gives us its bytes to assert on.
    """
    got = webapp.static_file("where-in-space.html")
    assert got is not None, "where-in-space.html must be served by the static route"
    ctype, body = got
    assert ctype.startswith("text/html")
    return body.decode("utf-8")


def test_served_by_static_route():
    """The iframe page is servable as HTML and is the real 3-D view."""
    src = _served_source()
    assert "<title>GalNav - Where in Space</title>" in src
    assert "./vendor/spacekit/spacekit.js" in src  # loads the vendored bundle
    assert len(src) > 5000


def test_offline_zero_external_url_loads():
    """The view must stay fully offline: NO http(s) URLs anywhere, and every
    asset path is the local vendored subtree. A CDN or protocol-relative load
    would break the offline guarantee the whole demo rests on."""
    src = _served_source()
    assert "http://" not in src
    assert "https://" not in src
    assert 'src="//' not in src and "src='//" not in src  # protocol-relative
    # positively: assets come from the local vendor tree
    assert "basePath: BASE" in src and "const BASE = './vendor/spacekit'" in src
    assert "fetch('./vendor/spacekit/data/gaia_20pc.json')" in src


def test_query_contract_params_parsed():
    """All documented query params are read by name (backward-compatible: x keeps
    its old meaning). If any parse line is dropped the contract silently breaks."""
    src = _served_source()
    for lit in (
        "params.get('x')",
        "params.get('truth')",
        "params.get('tlabel')",
        "params.get('ray')",
        "params.get('rlabel')",
    ):
        assert lit in src, f"missing query-param parse: {lit}"
    # the ?x default is still the New Horizons demo fix (equatorial ICRS au)
    assert "[13.386, -42.369, -16.486]" in src
    # the full contract is documented in the header comment
    assert "QUERY CONTRACT" in src


def test_wheel_zoom_fix_hook_present():
    """Item 4 -- wheel zoom must work on first hover with no clicks. The fix is a
    capture-phase, non-passive wheel handler on the WINDOW (the root of event
    propagation, so it sees every tick even when overlay labels sit under the
    cursor or Chrome would latch the gesture to the parent), which preventDefaults
    the host-page scroll and dollies the camera itself. OrbitControls' own wheel
    zoom is therefore turned off. A pointer-enter focus grab backs it up."""
    src = _served_source()
    assert "window.addEventListener('wheel'" in src
    assert "capture: true, passive: false" in src
    assert "e.preventDefault()" in src
    assert "ctr.enableZoom = false" in src  # OrbitControls wheel handled by us
    assert "const activeViz" in src  # picks the on-screen scene to dolly
    assert "window.focus()" in src  # focus grab on pointer-enter
    assert "get3jsCameraControls()" in src  # real spacekit/THREE control handle


def test_zoom_stays_centered_on_the_sun():
    """Item 2 -- zoom must always pivot on the Sun. The orbit target is pinned to
    the origin and panning is disabled so it can never drift; per-scene dolly
    clamps keep the view usable. The pan hint is gone from the on-screen text."""
    src = _served_source()
    assert "ctr.target.set(0, 0, 0)" in src  # Sun == origin, both scenes
    assert "ctr.enablePan = false" in src  # target cannot drift
    assert "DOLLY = { au: [2, 1500], pc: [0.3, 120] }" in src  # per-scene clamps
    assert "zoom toward the Sun" in src  # updated hint
    assert "right-drag = pan" not in src  # old pan hint removed
    # defensive against wheel scroll-chaining out to the host page
    assert "overscroll-behavior: none" in src


def test_truth_marker_and_miss_line():
    """Item 3 -- actual vs estimated. ?truth draws a distinct cyan marker, a line
    to the amber recovered marker, and a 3-decimal 'miss: N au' midpoint label,
    plus a truth legend row. Overlapping truth/recovered/miss labels are offset."""
    src = _served_source()
    assert "params.get('truth')" in src
    assert "NH at fix epoch (JPL truth)" in src  # default tlabel
    assert "'miss: ' + MISS_AU.toFixed(3) + ' au'" in src  # 3-decimal miss
    assert "lg-truth-row" in src  # truth legend row (shown w/ param)
    assert "truthc" in src  # cyan legend swatch class
    assert ".truth-label div" in src and ".miss-label div" in src  # offset labels
    assert "#4fd2ff" in src  # cyan truth family


def test_line_of_position_ray():
    """Item 3 -- ?ray draws an amber DASHED line-of-position with its label, and
    when ray is present without x the recovered marker (and its legend row) are
    suppressed for the 'one image = a line' page."""
    src = _served_source()
    assert "params.get('ray')" in src
    assert "line of position" in src  # default rlabel
    assert "LineDashedMaterial" in src  # dashed LOP ray
    assert "DRAW_RECOVERED = !(HAS_RAY && !HAS_X)" in src  # suppression rule
    assert "lg-fix-row" in src  # recovered legend row (hidden ray-only)


def test_new_horizons_today_relabelled():
    """Item 3 -- the ~64 au probe dot is explicitly the LATER epoch, so users stop
    conflating New Horizons today with the recovered 2020 fix."""
    src = _served_source()
    assert "New Horizons TODAY (~64 au, later epoch)" in src


def test_frame_transform_preserved():
    """The equatorial-ICRS -> ecliptic rotation (the reason inputs are au ICRS)
    must remain: it maps both positions and the ray's unit direction."""
    src = _served_source()
    assert "function eqToEcl" in src
    assert "23.43928" in src  # mean obliquity used for the rotation
