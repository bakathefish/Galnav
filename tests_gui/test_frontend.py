"""Static, offline tests for the main page frontend (gui/web/app.js + index.html).

These are DELIBERATELY static string/structure assertions on the served files --
no browser, no network, deterministic (the pattern proven in
tests_gui/test_space_view.py). Each fix from do.txt was exercised live in a real
browser during development; these tests pin the SOURCE HOOKS that make each fix
so a later edit cannot silently drop them.

app.js is fetched through the SAME static route the web app serves it from
(gui.webapp.static_file), so a regression in the route or the file both fail
here. index.html is read via the same expression the / route handler evaluates
((WEB_DIR / "index.html").read_bytes()) -- there is no handler-free function for
/, so this is exactly the bytes the browser receives.

These tests assert on app.js / index.html only: the new server endpoints
(/api/remove_upload, /api/solver_status, the locate line-mode payload) are a
parallel contract and are NOT required to exist for this file to pass.
"""

import re

from gui import webapp


def _app_js():
    """app.js the browser would receive, decoded, via the real static route."""
    got = webapp.static_file("app.js")
    assert got is not None, "app.js must be served by the static route"
    ctype, body = got
    assert ctype.startswith("application/javascript")
    return body.decode("utf-8")


def _index_html():
    """index.html exactly as the / route serves it (same read the handler does)."""
    return (webapp.WEB_DIR / "index.html").read_bytes().decode("utf-8")


# --- do.txt item 1: "image selector too buggy" -------------------------------


def test_file_input_value_cleared_after_every_attempt():
    """do.txt item 1 (a) -- the core 'upload looks frozen' bug: choosing the same
    file twice never fired change because the input kept its value. The change
    handler must snapshot the FileList and clear the input's value BEFORE the
    (possibly failing) upload runs, so a re-select always fires -- success AND
    failure paths both covered by one unconditional reset."""
    js = _app_js()
    assert 'e.target.value = ""' in js
    # the old single-file hard-code must be gone
    assert "e.target.files[0]" not in js


def test_multi_file_upload_sequential_with_honest_summary():
    """do.txt item 1 (b) -- the picker accepts several files; app.js iterates the
    FileList sequentially (await each upload; one bad file must not abort the
    rest) and ends with an honest summary counting failures by name+reason."""
    src = _index_html()
    m = re.search(r'<input[^>]*id="file"[^>]*>', src, re.S)
    assert m is not None, "#file input must exist"
    assert "multiple" in m.group(0), "#file must accept multiple files"
    js = _app_js()
    assert "async function uploadMany" in js
    assert "await uploadOne(" in js  # sequential: each file awaited in the loop
    assert "failed.push(" in js  # a failure is recorded, not thrown
    assert "failed.length} failed" in js  # honest summary literal


def test_upload_remove_affordance_uploads_only():
    """do.txt item 1 (c) -- uploaded frames get a remove control that calls
    POST /api/remove_upload then refreshes; demo frames (ids f0..f11) get none,
    pinned by the up_ id guard around the control's creation."""
    js = _app_js()
    assert '"/api/remove_upload"' in js
    assert 'f.id.startsWith("up_")' in js  # only uploads get the x control
    assert "async function removeUpload" in js


def test_removed_frame_dropped_from_selection_and_focus():
    """do.txt item 1 (c) -- removing an upload that was selected/focused must
    drop it from BOTH, or the gallery and preview desync. removeUpload routes
    through the shared deselect helper that re-derives focus."""
    js = _app_js()
    body = js.split("async function removeUpload", 1)[1].split("\nasync function", 1)[0]
    assert "deselectId(id)" in body


def test_duplicate_upload_selects_existing_record():
    """do.txt item 1 (d) -- re-uploading identical bytes: the server flags
    "duplicate": true; the frontend must toast 'already uploaded' and select the
    existing record instead of stacking a copy in the gallery."""
    js = _app_js()
    assert "r.duplicate" in js
    assert "already uploaded" in js


def test_deselect_moves_focus_to_last_selected_or_null():
    """do.txt item 1 (e) -- the focus/selected desync: deselecting used to LEAVE
    focus on the deselected frame. Now selection order is tracked and focus
    moves to the most recently selected remaining frame, or null (the preview
    goes honestly empty)."""
    js = _app_js()
    assert "state.order[state.order.length - 1] : null" in js
    # the old unconditional focus-on-toggle (set even on DEselect) must be gone
    assert not re.search(r"function toggleFrame[^}]*state\.focus = id;", js), (
        "toggleFrame must not force focus on deselect"
    )


def test_age_radius_edits_debounced_img_src_only():
    """do.txt item 1 (f) -- editing age/radius used to rebuild the ENTIRE gallery
    DOM per commit (heavy: every thumbnail re-created). Now the edit is
    debounced (~400 ms) and only the <img> srcs are rewritten in place, keyed by
    a data-fid attribute, so the query params still propagate."""
    js = _app_js()
    assert "function debounce(" in js
    assert "debounce(refreshImages, 400)" in js
    assert "img[data-fid]" in js  # in-place src update, no gallery teardown
    assert 'data-fid="${fid}"' in js  # thumbnails carry their frame id


# --- do.txt item 7: "why are the controls a thing like they are" -------------


def test_age_input_auto_manual_modes():
    """do.txt item 7 (a) -- the Age input used to be stomped by syncAge on every
    selection change even after the user typed a value. Now it is dual-mode: an
    'auto' badge state follows the selection; typing switches to 'manual' which
    selection changes must NOT stomp; a small control returns to auto. The
    guard in syncAge is the load-bearing hook."""
    js = _app_js()
    assert 'state.ageMode !== "auto"' in js  # syncAge bails in manual mode
    assert 'setAgeMode("manual")' in js  # typing enters manual
    assert 'setAgeMode("auto")' in js  # the reset control returns to auto
    src = _index_html()
    assert 'id="age-mode"' in src  # visible badge (auto/manual)
    assert 'id="age-auto"' in src  # the back-to-auto control


def test_plain_english_control_explanations():
    """do.txt item 7 (b) -- every opaque control gets a one-line plain-English
    explanation: match radius, RV fill (assumed radial velocity used when aging
    the catalog), and the age-scan grid trio."""
    src = _index_html()
    assert "still count as that star" in src  # match radius, in arcseconds
    assert "no measured radial velocity" in src  # RV fill, honest physics
    assert "catalog ages the estimator tries" in src  # scan grid trio


def test_estimate_button_measures_age_input_assumes():
    """do.txt item 7 (c) -- the 'Estimate catalog age' button and the Age input
    read like the same thing; the sub-caption states the difference: the button
    MEASURES the age from stellar drift, the input ASSUMES one for locating."""
    src = _index_html()
    assert "MEASURES" in src
    assert "ASSUMES" in src


# --- do.txt item 9: line-of-position result card -----------------------------
# (3-D wiring deliberately absent: the viewer is moving to OpenSpace, and
# line-of-position display there lands in a later wave, not this one.)


def test_line_mode_result_card_is_honest():
    """do.txt item 9 -- on mode==="line" (one usable nearby star) the result
    card must SAY one star yields a line, not a point, and show the residual
    spread between sightings when the single star was seen in more than one
    line. No 3-D panel is wired for line mode."""
    js = _app_js()
    assert 'r.mode === "line"' in js  # line mode is handled, not an error card
    assert "not a point" in js
    assert "residual_spread_arcsec" in js
    assert "r.n_lines > 1" in js  # spread shown only when it means something


# --- do.txt item 6: solver install messaging ---------------------------------


def test_solver_status_swaps_install_hints_when_installed():
    """do.txt item 6 -- the page still told users to INSTALL the blind solver
    after it was installed natively. On load app.js fetches /api/solver_status;
    when wsl_solver && wsl_config the three static install hints swap to an
    installed-state line naming the index count; install instructions stay only
    while the solver is absent; an old server without the endpoint leaves the
    hints untouched."""
    js = _app_js()
    assert '"/api/solver_status"' in js
    assert "r.wsl_solver && r.wsl_config" in js
    assert "astrometry.net installed locally (WSL, " in js
    assert "narrow-field indexes" in js
    assert "leave install hints as-is" in js  # graceful 404/old-server path
    src = _index_html()
    # the three swappable hint anchors (upload card, advanced details, footer)
    assert 'id="solver-hint-formats"' in src
    assert 'id="solver-hint-install"' in src
    assert 'id="solver-hint-how"' in src
    # default (solver absent) text still carries the install instructions
    assert "install local" in src


# --- pivot: OpenSpace panel replaces the old spacekit iframe on the main page --


def test_main_page_has_openspace_panel_not_iframe():
    """The old 3-D spacekit iframe panel is retired from the user flow and
    replaced by an OpenSpace panel: a status chip, a step-through link, and a
    'show the fix in OpenSpace' button. where-in-space.html stays on disk (its
    own tests still pass) but the main page no longer routes users to it."""
    src = _index_html()
    assert 'id="openspace-panel"' in src
    assert 'id="os-chip"' in src  # connected / not-running chip
    assert 'id="walk-link"' in src  # step-through entry point
    assert 'id="os-show-fix"' in src  # show the fix in OpenSpace
    assert "OpenSpace" in src
    # the retired iframe view is gone from the main page
    assert 'id="space-iframe"' not in src
    assert "where-in-space.html" not in src


def test_app_js_wires_openspace_not_iframe():
    """app.js talks to the live-bridge endpoints and builds the step-through
    link carrying the current selection; the dead iframe code path is gone."""
    js = _app_js()
    assert '"/api/openspace/status"' in js  # chip refresh
    assert '"/api/openspace/show"' in js  # push the fix
    assert "pipeline-1-raw.html" in js  # step-through entry
    assert 'showInOpenSpace("fix")' in js  # the show-fix button pushes the fix stage
    # the retired iframe wiring must be gone (pivot to OpenSpace)
    assert "space-iframe" not in js
    assert "where-in-space.html" not in js


# --- the step-by-step pipeline pages (do.txt items 5 + 9) --------------------
# Each page is served through the SAME static route the app uses, is fully
# offline (no external URL), and carries the hooks that make its stage real.

PIPELINE_PAGES = [
    "pipeline-1-raw.html",
    "pipeline-2-detect.html",
    "pipeline-3-identify.html",
    "pipeline-4-angles.html",
    "pipeline-5-lines.html",
    "pipeline-6-fix.html",
]


def _page(name):
    got = webapp.static_file(name)
    assert got is not None, f"{name} must be served by the static route"
    ctype, body = got
    assert ctype.startswith("text/html"), name
    return body.decode("utf-8")


def test_all_pipeline_pages_served_offline_and_chained():
    """Every pipeline page is servable HTML, stays offline (no http/https), reads
    the ?ids=&age=&radius= contract, shows a step indicator, and shows the
    OpenSpace status chip."""
    for name in PIPELINE_PAGES:
        src = _page(name)
        assert "http://" not in src and "https://" not in src, name
        assert "location.search" in src, name  # carries the URL contract
        assert "params.get('ids')" in src or 'params.get("ids")' in src, name
        assert "Step " in src, name  # step indicator
        assert "/api/openspace/status" in src, name  # status chip
        assert "/static/style.css" in src, name  # shared design tokens, offline


def test_pipeline_pages_prev_next_chain():
    """Pages are chained by Next/Prev redirects (the user wanted page-by-page
    links, not tabs): page 1 has Next, page 6 has Prev, the middle pages both."""
    first = _page("pipeline-1-raw.html")
    last = _page("pipeline-6-fix.html")
    assert "nextlink" in first
    assert "prevlink" in last
    for name in PIPELINE_PAGES[1:-1]:
        src = _page(name)
        assert "prevlink" in src and "nextlink" in src, name


def test_pipeline_1_raw_is_unlabeled_and_honest():
    """Page 1 shows the image with NO pre-drawn labels (overlay=none) and says
    plainly this raw frame is all a lost spacecraft has (do.txt item 8)."""
    src = _page("pipeline-1-raw.html")
    assert "overlay=none" in src
    assert "all a lost spacecraft has" in src


def test_pipeline_2_detect_shows_centroid_math():
    """Page 2 overlays the detected blobs and shows the moment-centroid math with
    this frame's real numbers pulled from /api/pipeline."""
    src = _page("pipeline-2-detect.html")
    assert "overlay=detected" in src
    assert "/api/pipeline" in src
    assert "centroid" in src.lower()
    assert "moment" in src.lower()  # the flux-weighted moment centroid


def test_pipeline_3_identify_has_match_table_and_openspace_button():
    """Page 3 lists the identification matches (name, source_id, dist_pc,
    sep_arcsec, position-capable) and offers 'Show these stars in OpenSpace'."""
    src = _page("pipeline-3-identify.html")
    assert "/api/pipeline" in src
    assert "source_id" in src and "dist_pc" in src
    assert "position-capable" in src.lower()
    assert "/api/openspace/show" in src
    assert 'data-stage="stars"' in src


def test_pipeline_4_angles_shows_tan_deprojection():
    """Page 4 shows, per position-capable star, the centroid -> direction_unit
    TAN deprojection: the actual 3-vector, RA/Dec, and the formula in plain HTML
    (no external math libs)."""
    src = _page("pipeline-4-angles.html")
    assert "/api/pipeline" in src
    assert "direction_unit" in src
    assert "RA" in src and "Dec" in src
    assert "tangent" in src.lower() or "gnomonic" in src.lower() or "TAN" in src


def test_pipeline_5_lines_shows_lop_and_openspace_button():
    """Page 5 explains the line of position (observer = star_pos - lambda *
    direction) with the anchor/direction numbers and a 'Show the line(s) in
    OpenSpace' button."""
    src = _page("pipeline-5-lines.html")
    assert "line of position" in src.lower()
    assert "anchor" in src.lower() and "direction" in src.lower()
    assert "/api/openspace/show" in src
    assert 'data-stage="lines"' in src


def test_pipeline_6_fix_intersection_miss_and_one_image_story():
    """Page 6 shows the least-squares intersection + ellipsoid + miss vs truth,
    a 'Show the fix in OpenSpace' button, and the one-star degenerate case with a
    'now add a second image' link that jumps to the SAME walk with ids=f0,f6."""
    src = _page("pipeline-6-fix.html")
    assert "/api/locate" in src
    assert "least" in src.lower() and "ellipsoid" in src.lower()
    assert "miss" in src.lower()
    assert "/api/openspace/show" in src
    assert 'data-stage="fix"' in src
    # the one-image -> two-image story (do.txt item 9)
    assert "a line, not a point" in src
    assert "ids=f0,f6" in src
