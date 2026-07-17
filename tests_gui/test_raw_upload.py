"""End-to-end test of the RAW upload path: a real LORRI frame with its WCS
stripped is fed through the WHOLE chain -- plate-solve -> centroid -> identify ->
locate. The solver binary is the ONLY thing mocked: absent in one test (proving
the friendly three-backend error the user actually hits), and mocked to return
the frame's true plate in the other (proving every other line of the raw path
without needing astrometry.net installed). Offline, deterministic; the stripped
copy is written only to tmp_path (no new FITS is committed).
"""

from pathlib import Path

import numpy as np

from gui import platesolve, webapp
from gui.platesolve import fits_header_solution
from gui.raw_demo import make_raw_copy

SRC = webapp.NH_DIR / "lor_0449855930_0x633_pwcs2.fits"  # a Proxima-field frame

# The raw path reproduces the 2-frame teaching fix (uploaded Proxima + demo Wolf)
# to <1e-5 au (measured 2026-07-17): the stripped frame's pixels and the mock-
# recovered plate are byte-identical to demo frame f0, so [upload, f6] == [f0, f6].
# 1e-3 au is the gate.
MISS_2_AU = 0.98301
RAW_E2E_TOL_AU = 1e-3


def test_raw_upload_without_solver_gives_friendly_error(tmp_path, monkeypatch):
    """A raw (WCS-stripped) image with NO blind solver available must fail with
    the friendly multi-backend message -- the exact error a user hits before
    installing solve-field, so it must name all three routes."""
    raw = make_raw_copy(SRC, tmp_path)
    assert fits_header_solution(raw) is None  # genuinely raw: no WCS in the header
    monkeypatch.setattr(platesolve, "_wsl_available", lambda: False)
    monkeypatch.delenv("ASTROMETRY_NET_API_KEY", raising=False)
    r = webapp.handle_upload("myphoto.fits", raw.read_bytes(), api_key=None)
    assert r["ok"] is False
    for s in ("could not plate-solve", "astrometry.net", "nova"):
        assert s in r["message"]


def test_raw_upload_with_solver_identifies_and_locates(tmp_path, monkeypatch):
    """With the blind solver mocked to return the frame's true plate, the raw
    upload must succeed, identify Proxima, and -- combined with one demo Wolf 359
    frame -- produce a fix that reproduces the 2-frame teaching number. This
    exercises every line of the raw path except the solver binary itself."""
    true_plate = fits_header_solution(SRC)  # the frame's real plate solution
    raw = make_raw_copy(SRC, tmp_path)
    monkeypatch.setattr(platesolve, "wsl_solve", lambda path, **k: true_plate)
    # Pin the upload-path nav catalog to the frozen 20-pc file for determinism
    # (uploaded frames otherwise use the widest available catalog).
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())

    up = webapp.handle_upload("raw_proxima.fits", raw.read_bytes())
    assert up["ok"] is True and up["field"] == "uploaded"

    r = webapp.locate_payload([up["id"], "f6"], 4.31, 120, 19.57)
    assert r["ok"] is True and r["distinct_stars"] == 2
    assert "Proxima Cen" in [ln["star_name"] for ln in r["lines"]]  # identified
    miss = float(np.linalg.norm(np.array(r["x_au"]) - webapp.NEWH_X_JPL))
    assert abs(miss - MISS_2_AU) < RAW_E2E_TOL_AU
