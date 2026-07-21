"""Tests for gui.webapp -- the localhost web shell. Offline, deterministic, no
network: every test calls the plain module functions directly (no socket). The
web shell reuses the same physics as gui/app.py, so these pin the JSON payloads,
the deterministic fixes, and the static-file traversal guard.
"""

from pathlib import Path

import numpy as np

from galnav.units import deg_to_rad, radec_to_unit
from gui import webapp
from gui.platesolve import PlateSolution
from tests_gui.synth import _tan_wcs

# Measured 2026-07-17 (single catalog age applied to all frames, the web UI's
# model). 12 real LORRI frames at age 4.31, radius 120, rv 19.57:
MISS_12_AU = 0.38659  # matches Lauer's 0.351 au 12-line x60 solve
MISS_2_AU = 0.98301  # teaching pair (1 Proxima + 1 Wolf); ~Lauer-family
AU_PER_PC = 206264.806
AGE_HAT_12 = 4.2856  # chi2-scan best age (true ~4.31)


def _demo_ids():
    return [f["id"] for f in webapp.frames_payload() if f["id"].startswith("f")]


def _assert_lop_sane(lop):
    """A line-of-position summary must be geometrically consistent: a unit ray,
    and endpoint = anchor + span*ray (so a renderer can draw anchor->endpoint)."""
    ray = np.array(lop["ray_unit"], dtype=float)
    anchor = np.array(lop["anchor_au"], dtype=float)
    endpoint = np.array(lop["endpoint_au"], dtype=float)
    assert ray.shape == (3,) and anchor.shape == (3,) and endpoint.shape == (3,)
    assert abs(np.linalg.norm(ray) - 1.0) < 1e-9  # unit direction
    assert np.allclose(endpoint, anchor + lop["span_au"] * ray, atol=1e-6)
    assert lop["star_name"]  # a human name is attached


def test_frames_payload_classifies_all_twelve():
    """All 12 demo frames appear with a field tag; lor_0449913531 must be a
    Proxima field (its lor_04499* name would fool a filename glob)."""
    frames = webapp.frames_payload()
    demo = [f for f in frames if f["id"].startswith("f")]
    assert len(demo) == 12
    assert sum(f["field"] == "Proxima" for f in demo) == 6
    assert sum(f["field"] == "Wolf 359" for f in demo) == 6
    tricky = next(f for f in demo if "0449913531" in f["name"])
    assert tricky["field"] == "Proxima"


def test_render_frame_png_is_png(monkeypatch):
    """The overlay endpoint must return real PNG bytes (breaks if the figure
    render or the Content flow regresses). Pin the wide catalog to the frozen
    20-pc file so the full-label render path is deterministic and fast."""
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    png = webapp.render_frame_png("f0", 4.31, 120)
    assert isinstance(png, (bytes, bytearray)) and len(png) > 1000
    assert bytes(png[:8]) == b"\x89PNG\r\n\x1a\n"
    # thumbnail path (nav only) also renders
    thumb = webapp.render_frame_png("f0", 4.31, 120, full_labels=False)
    assert bytes(thumb[:8]) == b"\x89PNG\r\n\x1a\n"


def test_locate_all_twelve_frames_hits_lauer():
    """The full 12-frame solve is deterministic: miss within 1e-3 of 0.387 au and
    exactly 2 distinct stars. This is the headline number."""
    r = webapp.locate_payload(_demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert r["distinct_stars"] == 2
    assert r["n_lines"] == 12
    assert abs(r["miss_au"] - MISS_12_AU) < 1e-3
    assert len(r["ellipsoid_au"]) == 3


def test_locate_two_teaching_frames():
    """The 2-frame teaching case recovers ~1 au (single-age model gives 0.983)."""
    r = webapp.locate_payload(["f0", "f6"], 4.31, 120, 19.57)
    assert r["ok"] is True and r["distinct_stars"] == 2
    assert abs(r["miss_au"] - MISS_2_AU) < 0.02


def test_locate_single_frame_is_a_line():
    """One frame gives a line, not a point: ok:false with the single-line text,
    now ALSO carrying a drawable line-of-position (mode 'line', lop:{...})."""
    r = webapp.locate_payload(["f0"], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "at least 2 lines" in r["message"]
    assert r["mode"] == "line"
    _assert_lop_sane(r["lop"])
    assert r["lop"]["star_name"] == "Proxima Cen"
    assert r["lop"]["n_lines"] == 1


def test_locate_same_star_frames_refused():
    """Two Proxima frames (same star) are near-parallel and fix only a line --
    returned as a drawable line-of-position, not merely an error string."""
    r = webapp.locate_payload(["f0", "f1"], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "same star" in r["message"]
    assert r["mode"] == "line"
    _assert_lop_sane(r["lop"])
    assert r["lop"]["star_name"] == "Proxima Cen"
    assert r["lop"]["n_lines"] == 2


def test_locate_zero_lines_has_no_lop(monkeypatch):
    """A frame with NO nearby star in it yields zero lines: that stays a plain
    error with no lop (there is nothing to draw a line from)."""
    monkeypatch.setattr(webapp, "_lines_for", lambda *a, **k: ([], False))
    r = webapp.locate_payload(["f0"], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "mode" not in r and "lop" not in r


def test_locate_miss_null_for_uploaded():
    """miss_au is reported only for the known-JPL demo set; an id that is not a
    demo frame would blank it -- here we assert the demo path DOES fill it."""
    r = webapp.locate_payload(_demo_ids(), 4.31, 120, 19.57)
    assert r["miss_au"] is not None


def test_age_payload_recovers_epoch():
    """The chi2-vs-age scan finds the image epoch within 0.05 yr with a sane
    curvature error, and reports the FITS truth for comparison."""
    r = webapp.age_payload(_demo_ids(), 120, 19.57, 0.0, 10.0, 0.25)
    assert r["ok"] is True
    assert abs(r["age_hat_yr"] - AGE_HAT_12) < 0.05
    assert 0.01 < r["sigma_age_yr"] < 0.3
    assert abs(r["truth_yr"] - 4.31) < 0.02
    assert len(r["ages"]) == len(r["chi2s"])


def test_age_payload_wide_grid_does_not_crash():
    """The app-default wide grid (0..25) must complete -- unmatchable ages are
    scored, not raised (the booth-critical guard, exercised via the web layer)."""
    r = webapp.age_payload(["f0", "f6"], 120, 19.57, 0.0, 25.0, 0.25)
    assert r["ok"] is True and np.isfinite(r["age_hat_yr"])


def test_static_file_guard_rejects_traversal():
    """The static route's ONLY guard must serve the allowlist and reject any
    traversal or unknown name -- no arbitrary file reads from the browser."""
    assert webapp.static_file("app.js") is not None
    assert webapp.static_file("style.css") is not None
    assert webapp.static_file("../webapp.py") is None
    assert webapp.static_file("../../README.md") is None
    assert webapp.static_file("secrets.env") is None
    assert webapp.static_file("sub/app.js") is None


# --- addendum: identification labeling + wide-catalog fallback --------------


def _mini_catalog_scene(nx=256, ny=256, scale=4.0):
    """A distortion-free plate + a tiny hand-built catalog whose stars sit at
    known in-frame pixels at chosen distances (barycentric = apparent here, so
    the tight identification match works). Returns (plate, aged_cat, centroids,
    dist_pc_by_index, source_ids)."""
    wcs = _tan_wcs(150.0, 20.0, scale, nx, ny)
    plate = PlateSolution(wcs=wcs, source="mock", width=nx, height=ny)
    pixels = [(128.0, 128.0), (60.0, 90.0), (200.0, 170.0)]
    dist_pc = [1.3, 55.0, 212.0]  # one nearby, two distant
    source_ids = [5853498713190525696, 900001, 900002]  # first = Proxima id
    positions = []
    for (px, py), dpc in zip(pixels, dist_pc):
        sky = plate.wcs.pixel_to_world(px, py).icrs
        u = radec_to_unit(deg_to_rad(sky.ra.deg), deg_to_rad(sky.dec.deg))
        positions.append(u * (dpc * AU_PER_PC))
    aged_cat = {
        "positions_au": np.array(positions, dtype=float),
        "source_id": np.array(source_ids, dtype=np.int64),
    }
    centroids = np.array(pixels, dtype=float)
    return plate, aged_cat, centroids, dist_pc, source_ids


def test_crossmatch_labels_identifies_and_flags():
    """Every catalogued star in frame is identified with its distance, and only
    the star whose id is passed as position-capable is flagged so -- the split
    the preview draws (amber navigable vs muted identified-only)."""
    plate, aged_cat, centroids, dist_pc, source_ids = _mini_catalog_scene()
    labels = webapp.crossmatch_labels(
        plate, centroids, aged_cat, position_capable_ids={source_ids[0]}
    )
    assert len(labels) == 3  # every injected star identified
    by_sid = {lab["source_id"]: lab for lab in labels}
    assert set(by_sid) == set(source_ids)
    for sid, dpc in zip(source_ids, dist_pc):
        assert abs(by_sid[sid]["dist_pc"] - dpc) < 0.5  # distance recovered
    assert by_sid[source_ids[0]]["position_capable"] is True  # the nearby one
    assert by_sid[source_ids[1]]["position_capable"] is False
    assert by_sid[source_ids[2]]["position_capable"] is False
    assert by_sid[source_ids[0]]["name"] == "Proxima Cen"  # STAR_NAMES hit


def test_crossmatch_labels_far_source_gets_distance_not_navigable():
    """A far filler star must be identified (labelled with a distance) yet NOT
    flagged position-capable -- the pedagogical 'we know what it is, but it's
    too far to navigate by' case."""
    plate, aged_cat, centroids, dist_pc, source_ids = _mini_catalog_scene()
    labels = webapp.crossmatch_labels(
        plate, centroids, aged_cat, position_capable_ids=set()
    )
    far = max(labels, key=lambda lab: lab["dist_pc"])
    assert far["dist_pc"] > 200 and far["position_capable"] is False


def test_labeling_catalog_falls_back_when_wide_absent(monkeypatch, tmp_path):
    """With no 100-pc file present, labeling must degrade to the frozen 20-pc
    file rather than fail."""
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", tmp_path / "absent.csv")
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    cat, path = webapp.labeling_catalog(4.31, 19.57)
    assert path == str(webapp.CATALOG_CSV)
    assert cat["positions_au"].shape[0] > 100


def test_labeling_catalog_falls_back_on_malformed(monkeypatch, tmp_path):
    """A partially-written / malformed 100-pc file (as during a concurrent
    fetch) must not crash labeling -- its mtime is marked bad and the 20-pc
    file is used."""
    bad = tmp_path / "wide.csv"
    bad.write_text("source_id,ra,dec,parallax\n1,2,3\n4,5\n")  # ragged rows
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", bad)
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    cat, path = webapp.labeling_catalog(4.31, 19.57)
    assert path == str(webapp.CATALOG_CSV)


def test_labeling_catalog_uses_wide_when_valid(monkeypatch, tmp_path):
    """When a valid wide catalog is present it is used (here a copy of the 20-pc
    file stands in for it, same schema)."""
    wide = tmp_path / "wide.csv"
    wide.write_bytes(Path(webapp.CATALOG_CSV).read_bytes())
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", wide)
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    cat, path = webapp.labeling_catalog(4.31, 19.57)
    assert path == str(wide)
    assert cat["positions_au"].shape[0] > 100


def test_demo_locate_uses_frozen_catalog_even_if_wide_present(monkeypatch, tmp_path):
    """The blessed demo fix must stay byte-reproducible regardless of the wide
    catalog: even with a (larger) wide file present, the 12-frame demo miss is
    still 0.38659 au because demo navigation is pinned to the frozen 20-pc file."""
    wide = tmp_path / "wide.csv"
    wide.write_bytes(Path(webapp.CATALOG_CSV).read_bytes())
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", wide)
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    r = webapp.locate_payload(_demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] and abs(r["miss_au"] - MISS_12_AU) < 1e-3


# --- retired 3-D view: spacekit page + vendored tree fully REMOVED -----------


def test_retired_spacekit_view_is_gone():
    """The old spacekit iframe page and the vendored spacekit tree are removed
    outright (user decision, 2026-07-21): the static route must 404 both, and
    the files must be gone from disk so nothing dead ships in the repo."""
    assert webapp.static_file("where-in-space.html") is None
    assert webapp.static_file("vendor/spacekit/spacekit.js") is None
    assert not (webapp.WEB_DIR / "where-in-space.html").exists()
    assert not (webapp.WEB_DIR / "vendor").exists()


def test_static_guard_survives_vendor_removal():
    """The traversal guard on the static route is unchanged by the removal:
    "..", absolute paths and non-allowlisted names all still 404."""
    assert webapp.static_file("../gui/webapp.py") is None  # ".."
    assert webapp.static_file("/etc/passwd") is None  # absolute
    assert webapp.static_file("vendor/../webapp.py") is None  # dead route stays dead
    assert webapp.static_file("nope.js") is None  # not on the allowlist


# --- multi-epoch honesty ----------------------------------------------------


def test_epoch_span_warning_flags_mixed_era_frames(monkeypatch):
    """Frames taken years apart are different observers: the fix is meaningless,
    so locate must carry a warning steering the user to the age estimate."""
    recs = {"a": {"obs_age_yr": -62.7}, "b": {"obs_age_yr": -20.8}}
    monkeypatch.setattr(webapp, "_record_by_id", lambda fid: recs.get(fid))
    w = webapp._epoch_span_warning(["a", "b"])
    assert w is not None
    assert "span" in w and "age estimate" in w
    assert "41" in w  # the measured span (62.7 - 20.8) rounds into the text


def test_epoch_span_warning_flags_few_year_span(monkeypatch):
    """A few-years span (Earth has moved >10 au between frames) must warn at the
    DEFAULT threshold. Pins the 0.02 yr default -- a mutant that widened it
    (0.02 -> 20) would miss this 2.2 yr span while the decades-apart test above
    would still pass, so this is the one that catches the mutant."""
    recs = {"a": {"obs_age_yr": -1.0}, "b": {"obs_age_yr": 1.2}}  # 2.2 yr span
    monkeypatch.setattr(webapp, "_record_by_id", lambda fid: recs.get(fid))
    w = webapp._epoch_span_warning(["a", "b"])
    assert w is not None and "span" in w and "age estimate" in w


def test_epoch_span_warning_silent_for_same_instant_campaign(monkeypatch):
    """A single-instant campaign (the NH frames span ~0.003 yr = ~1 day) must NOT
    warn: its lines of position DO cross at a real point."""
    recs = {"a": {"obs_age_yr": 4.31}, "b": {"obs_age_yr": 4.3132}}  # ~1.2 day span
    monkeypatch.setattr(webapp, "_record_by_id", lambda fid: recs.get(fid))
    assert webapp._epoch_span_warning(["a", "b"]) is None
    assert webapp._epoch_span_warning(["a"]) is None  # one frame: nothing to span


def test_locate_demo_has_no_epoch_span_warning():
    """The 12 real NH frames are one campaign: the fix is meaningful and the
    warning field is present-but-None (proves it is wired without false alarms)."""
    r = webapp.locate_payload(_demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert r["warning"] is None


# --- richer lines + JPL truth in /api/locate (item 2) -----------------------


def test_locate_lines_are_enriched_and_carry_truth():
    """Each line of a successful fix carries the drawing-grade fields (source_id,
    centroid_xy, direction_unit, star_pos_au, sep_arcsec) on TOP of the existing
    star_name/image/resid_arcsec, and the demo set adds the JPL truth vector."""
    r = webapp.locate_payload(["f0", "f6"], 4.31, 120, 19.57)
    assert r["ok"] is True
    assert len(r["lines"]) == 2
    need = {
        "star_name",
        "image",
        "resid_arcsec",
        "source_id",
        "centroid_xy",
        "direction_unit",
        "star_pos_au",
        "sep_arcsec",
    }
    for ln in r["lines"]:
        assert need <= set(ln)
        assert len(ln["centroid_xy"]) == 2
        d = np.array(ln["direction_unit"], dtype=float)
        assert d.shape == (3,) and abs(np.linalg.norm(d) - 1.0) < 1e-6
        assert len(ln["star_pos_au"]) == 3
        assert isinstance(ln["source_id"], int)
    # demo (known-JPL) set -> truth_x_au is the JPL vector, exactly
    assert "truth_x_au" in r
    assert np.allclose(r["truth_x_au"], webapp.NEWH_X_JPL, atol=1e-9)


# --- per-step pipeline data for the visualization pages (item 3) ------------


def test_pipeline_payload_shape(monkeypatch):
    """The /api/pipeline payload exposes every detected centroid, the per-dot
    identification matches, and the enriched nav lines for ONE frame -- reusing
    the cached centroids and the crossmatch/_lines_for machinery (no new math)."""
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    p = webapp.pipeline_payload("f0", 4.31, 120)
    assert p["ok"] is True
    assert p["id"] == "f0" and p["name"].endswith(".fits")
    rec = webapp._record_by_id("f0")
    n = rec["centroids"]["xy"].shape[0]
    assert len(p["centroids"]) == n and all(len(c) == 2 for c in p["centroids"])
    assert isinstance(p["matches"], list)
    for m in p["matches"]:
        assert {
            "centroid_index",
            "source_id",
            "name",
            "dist_pc",
            "position_capable",
            "sep_arcsec",
        } <= set(m)
        assert 0 <= m["centroid_index"] < n
        assert isinstance(m["position_capable"], bool)
    # the single 120" nav match for this Proxima frame, enriched
    assert len(p["lines"]) == 1
    ln = p["lines"][0]
    # source_id is a STRING in the pipeline payload (browser float64 precision)
    assert ln["star_name"] == "Proxima Cen"
    assert ln["source_id"] == str(webapp.PROXIMA_ID)
    assert len(ln["centroid_xy"]) == 2 and len(ln["direction_unit"]) == 3


def test_pipeline_nav_stars_lead_matches_and_ids_are_strings(monkeypatch):
    """Two bugs found by LIVE browser verification (2026-07-21), pinned:
    (1) The label tiers match STATIC catalog/cone positions tightly, so a
    fast-moving nav star -- displaced by exactly the parallax/drift signal we
    navigate on -- never appeared in matches: page 3 said '0 position-capable'
    on the PROXIMA frame and Proxima was absent from its own identification
    table. The nav identify (the lines) must be merged into matches, FIRST,
    flagged position-capable, with its real separation (the ~31.9 arcsec
    displacement that IS the navigation signal).
    (2) Gaia source_ids exceed float64's 53-bit exact-integer window, so the
    browser's JSON.parse silently rounded ...387072 to ...387000 in the page
    tables. Every source_id in THIS payload is therefore a STRING with exact
    digits; /api/locate keeps ints (nothing displays them raw there)."""
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    p = webapp.pipeline_payload("f0", 4.31, 120)
    assert p["ok"] is True
    first = p["matches"][0]
    assert first["name"] == "Proxima Cen"
    assert first["position_capable"] is True
    assert 25.0 < first["sep_arcsec"] < 40.0  # the displacement IS the signal
    assert first["source_id"] == str(webapp.PROXIMA_ID)  # exact digits, string
    assert all(isinstance(m["source_id"], str) for m in p["matches"])
    assert all(isinstance(ln["source_id"], str) for ln in p["lines"])
    ids = [m["source_id"] for m in p["matches"]]
    assert len(ids) == len(set(ids))  # the nav merge never duplicates a row


def test_pipeline_unknown_id():
    """An unknown frame id gets a plain-English error, not a stack trace."""
    p = webapp.pipeline_payload("nope_999", 4.31, 120)
    assert p["ok"] is False and "nope_999" in p["message"]


# --- overlay tiers on /api/image (item 4) -----------------------------------


def test_image_overlay_tiers(monkeypatch):
    """Every overlay tier renders a PNG: none (raw), detected (circles),
    identified (circles+labels), nav (everything = today's default)."""
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    for ov in ("none", "detected", "identified", "nav"):
        png = webapp.render_frame_png("f0", 4.31, 120, overlay=ov)
        assert bytes(png[:8]) == b"\x89PNG\r\n\x1a\n"
    # default overlay is nav -- unchanged behavior
    assert bytes(webapp.render_frame_png("f0", 4.31, 120)[:8]) == b"\x89PNG\r\n\x1a\n"
    # thumb path composes with a tier too
    t = webapp.render_frame_png("f0", 4.31, 120, full_labels=False, overlay="detected")
    assert bytes(t[:8]) == b"\x89PNG\r\n\x1a\n"


# --- upload management: dedup + removal (item 5) ----------------------------


def _mock_solver(monkeypatch):
    """Stub the solve/load/centroid pipeline so upload tests never touch a real
    solver or FITS file -- they exercise ONLY the dedup/removal bookkeeping."""
    monkeypatch.setattr(webapp, "solve_image", lambda path, api_key=None: object())
    monkeypatch.setattr(
        webapp, "load_grayscale", lambda path: np.zeros((16, 16), dtype=float)
    )
    monkeypatch.setattr(
        webapp,
        "find_centroids",
        lambda image: {"xy": np.zeros((0, 2)), "flux": np.zeros((0,))},
    )
    monkeypatch.setattr(webapp, "observation_jd", lambda path: None)


def test_upload_dedup_returns_existing(monkeypatch):
    """Re-uploading identical bytes returns the EXISTING record (duplicate:true,
    same id) instead of minting a new one; different bytes make a new record."""
    _mock_solver(monkeypatch)
    r1 = webapp.handle_upload("a.fits", b"RAW-BYTES-ONE")
    assert r1["ok"] is True and r1.get("duplicate") is False
    r2 = webapp.handle_upload("a-copy.fits", b"RAW-BYTES-ONE")  # identical content
    assert r2["ok"] is True and r2["duplicate"] is True
    assert r2["id"] == r1["id"]
    r3 = webapp.handle_upload("b.fits", b"RAW-BYTES-TWO")  # different content
    assert r3["ok"] is True and r3["id"] != r1["id"]
    webapp.remove_upload(r1["id"])
    webapp.remove_upload(r3["id"])


def test_remove_upload(monkeypatch):
    """remove_upload deletes an uploaded record; refuses demo ids and unknown
    ids with a plain-English message."""
    _mock_solver(monkeypatch)
    r = webapp.handle_upload("c.fits", b"REMOVE-ME-PLEASE")
    uid = r["id"]
    assert webapp.remove_upload(uid) == {"ok": True}
    again = webapp.remove_upload(uid)  # already gone
    assert again["ok"] is False and uid in again["message"]
    demo = webapp.remove_upload("f0")  # a built-in demo frame
    assert demo["ok"] is False and "demo" in demo["message"].lower()


def test_remove_upload_clears_dedup(monkeypatch):
    """After removal, the same bytes upload fresh again (the hash entry is gone,
    so it is NOT reported as a duplicate)."""
    _mock_solver(monkeypatch)
    r1 = webapp.handle_upload("d.fits", b"UNIQUE-DEDUP-BYTES")
    webapp.remove_upload(r1["id"])
    r2 = webapp.handle_upload("d.fits", b"UNIQUE-DEDUP-BYTES")
    assert r2["ok"] is True and r2.get("duplicate") is False
    assert r2["id"] != r1["id"]
    webapp.remove_upload(r2["id"])


# --- solver status probe (item 6) -------------------------------------------


def test_solver_status(monkeypatch, tmp_path):
    """solver_status reports the WSL solver/config booleans (from platesolve's
    probes) and the count of index-*.fits under the index dir."""
    idx = tmp_path / "astrometry-index"
    idx.mkdir()
    for i in range(3):
        (idx / f"index-4200-{i:02d}.fits").write_bytes(b"x")
    (idx / "not-an-index.txt").write_bytes(b"x")  # must NOT be counted
    monkeypatch.setattr(webapp, "ASTROMETRY_INDEX_DIR", idx)
    monkeypatch.setattr(webapp, "_WSL_SOLVER_CACHE", True)
    monkeypatch.setattr(webapp, "_wsl_has_galnav_config", lambda: True)
    s = webapp.solver_status()
    assert s["ok"] is True
    assert s["wsl_solver"] is True and s["wsl_config"] is True
    assert s["index_files"] == 3


def test_solver_status_missing_index_dir(monkeypatch, tmp_path):
    """A missing index dir counts as zero index files, and the probes still
    report cleanly (no shell-out: the WSL cache is overridden to False)."""
    monkeypatch.setattr(webapp, "ASTROMETRY_INDEX_DIR", tmp_path / "absent")
    monkeypatch.setattr(webapp, "_WSL_SOLVER_CACHE", False)
    monkeypatch.setattr(webapp, "_wsl_has_galnav_config", lambda: False)
    s = webapp.solver_status()
    assert s["ok"] is True
    assert s["index_files"] == 0
    assert s["wsl_solver"] is False and s["wsl_config"] is False


# --- OpenSpace live bridge: status + show (pipeline visualisation) -----------
# Offline: the openspace_link socket calls are mocked at the module boundary, so
# no real planetarium (and no network) is ever touched. These pin the JSON
# contract the pipeline pages and the main-page buttons speak to.
from gui import openspace_link  # noqa: E402


def _capture_lua(monkeypatch):
    """Mock run_lua to record the pushed Lua (and report success) without a
    socket, and force is_running True. Returns the list the scripts land in."""
    pushed = []
    monkeypatch.setattr(openspace_link, "is_running", lambda *a, **k: True)
    monkeypatch.setattr(webapp.openspace_link, "is_running", lambda *a, **k: True)

    def fake_run(script, *a, **k):
        pushed.append(script)
        return True

    def fake_confirmed(script, *a, **k):
        pushed.append(script)
        return "confirmed"

    monkeypatch.setattr(openspace_link, "run_lua", fake_run)
    monkeypatch.setattr(webapp.openspace_link, "run_lua", fake_run)
    monkeypatch.setattr(
        openspace_link, "run_lua_confirmed", fake_confirmed, raising=False
    )
    monkeypatch.setattr(
        webapp.openspace_link, "run_lua_confirmed", fake_confirmed, raising=False
    )
    # ensure_marker_textures writes PNGs (needs PIL + disk); stub it to the pure
    # path helper so the show flow stays offline and side-effect-free in tests.
    monkeypatch.setattr(
        webapp.openspace_link,
        "ensure_marker_textures",
        openspace_link.marker_texture_paths,
    )
    return pushed


def test_openspace_status_shape(monkeypatch):
    """/api/openspace/status reports whether OpenSpace is reachable -- a cheap
    boolean the UI turns into a connected/not-running chip."""
    monkeypatch.setattr(webapp.openspace_link, "is_running", lambda *a, **k: False)
    s = webapp.openspace_status()
    assert s == {"ok": True, "running": False}
    monkeypatch.setattr(webapp.openspace_link, "is_running", lambda *a, **k: True)
    assert webapp.openspace_status()["running"] is True


def test_openspace_show_not_running_is_honest(monkeypatch):
    """With OpenSpace absent, show never fakes success: it returns ok:false with
    a plain 'start OpenSpace' message -- and pushes no Lua."""
    monkeypatch.setattr(webapp.openspace_link, "is_running", lambda *a, **k: False)
    r = webapp.openspace_show("stars", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "OpenSpace" in r["message"]


def test_openspace_show_stars(monkeypatch):
    """The stars stage pushes an amber marker at each position-capable star's
    aged position -- galactic metres, GalNavLive identifiers, honest pushed list."""
    pushed = _capture_lua(monkeypatch)
    r = webapp.openspace_show("stars", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert len(pushed) == 1
    assert "RenderableSphereImageLocal" in pushed[0]
    assert all(n.startswith("GalNavLiveStar") for n in r["pushed"])
    assert len(r["pushed"]) == 2  # Proxima + Wolf (the 2 distinct nav stars)


def test_openspace_show_lines(monkeypatch):
    """The lines stage pushes one node line per nav line of position."""
    pushed = _capture_lua(monkeypatch)
    r = webapp.openspace_show("lines", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert "RenderableNodeLine" in pushed[0]
    assert all(n.startswith("GalNavLiveLine") for n in r["pushed"])


def test_openspace_show_fix_pushes_amber_and_truth(monkeypatch):
    """The fix stage runs the locate flow and pushes the amber fix + cyan truth +
    white miss line for the known-JPL demo set."""
    pushed = _capture_lua(monkeypatch)
    r = webapp.openspace_show("fix", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert "GalNavLiveFix" in pushed[0] and "GalNavLiveTruth" in pushed[0]
    assert "GalNavLiveFix" in r["pushed"]


def test_openspace_show_fix_one_star_draws_the_line(monkeypatch):
    """One nearby star is a LINE, not a point: the fix stage pushes the line of
    position instead and SAYS so (do.txt item 9, the one-image story)."""
    pushed = _capture_lua(monkeypatch)
    r = webapp.openspace_show("fix", ["f0"], 4.31, 120, 19.57)
    assert r["ok"] is True
    assert "RenderableNodeLine" in pushed[0]
    assert "line" in r["note"].lower()
    assert all(n.startswith("GalNavLiveLine") for n in r["pushed"])


def test_openspace_show_clear(monkeypatch):
    """The clear stage removes every GalNavLive* node and reports it."""
    pushed = _capture_lua(monkeypatch)
    r = webapp.openspace_show("clear", [], 4.31, 120, 19.57)
    assert r["ok"] is True
    assert "removeSceneGraphNode" in pushed[0]
    assert r["pushed"] == []


def test_openspace_show_reports_execution_confirmation(monkeypatch):
    """A successful push carries confirmed:true when the engine's measured
    reply frame acknowledged EXECUTION (run_lua_confirmed -> 'confirmed') --
    delivery is no longer taken on faith."""
    _capture_lua(monkeypatch)
    r = webapp.openspace_show("stars", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is True
    assert r["confirmed"] is True


def test_openspace_show_failed_chunk_is_honest(monkeypatch):
    """'failed' (the engine replied with an empty payload: the chunk did NOT
    execute) -> ok:false with a message pointing at the OpenSpace log --
    never fake success."""
    _capture_lua(monkeypatch)
    monkeypatch.setattr(
        webapp.openspace_link, "run_lua_confirmed", lambda *a, **k: "failed"
    )
    r = webapp.openspace_show("clear", [], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "log" in r["message"].lower()


def test_openspace_show_unconfirmed_send_is_flagged(monkeypatch):
    """'sent' (bytes delivered, no reply inside the window) stays ok:true --
    the old fire-and-forget guarantee -- but confirmed:false so the UI can
    say exactly that."""
    _capture_lua(monkeypatch)
    monkeypatch.setattr(
        webapp.openspace_link, "run_lua_confirmed", lambda *a, **k: "sent"
    )
    r = webapp.openspace_show("clear", [], 4.31, 120, 19.57)
    assert r["ok"] is True
    assert r["confirmed"] is False


def test_openspace_show_run_lua_failure_is_reported(monkeypatch):
    """If OpenSpace is reachable but the connection drops before the push
    lands (run_lua_confirmed -> 'down'), say so honestly."""
    monkeypatch.setattr(webapp.openspace_link, "is_running", lambda *a, **k: True)
    monkeypatch.setattr(
        webapp.openspace_link, "run_lua_confirmed", lambda *a, **k: "down"
    )
    monkeypatch.setattr(
        webapp.openspace_link,
        "ensure_marker_textures",
        openspace_link.marker_texture_paths,
    )
    r = webapp.openspace_show("stars", _demo_ids(), 4.31, 120, 19.57)
    assert r["ok"] is False
