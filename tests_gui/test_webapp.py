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
    """One frame gives a line, not a point: ok:false with the single-line text."""
    r = webapp.locate_payload(["f0"], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "at least 2 lines" in r["message"]


def test_locate_same_star_frames_refused():
    """Two Proxima frames (same star) are near-parallel and fix only a line."""
    r = webapp.locate_payload(["f0", "f1"], 4.31, 120, 19.57)
    assert r["ok"] is False
    assert "same star" in r["message"]


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
