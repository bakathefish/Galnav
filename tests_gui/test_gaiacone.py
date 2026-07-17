"""Tests for gui.gaiacone -- the deep-identify Gaia cone cache. All OFFLINE and
deterministic: the network fetch is monkeypatched or a cache file is planted, so
no test ever touches the TAP service. They pin the honest label rule, the
footprint cache key, the zero-network cache hit, and the silent degrade.
"""

import urllib.error

import numpy as np

from galnav.units import deg_to_rad, radec_to_unit
from gui import gaiacone, webapp
from gui.platesolve import PlateSolution
from tests_gui.synth import _tan_wcs

CONE_CSV = (
    "source_id,ra,dec,parallax,parallax_over_error,phot_g_mean_mag\n"
    "900100,150.0,20.0,50.0,100.0,10.2\n"  # 50 mas -> 20 pc, trustworthy
    "900200,150.01,20.01,-0.4,1.1,19.6\n"  # junk (negative) parallax, faint
    "900300,149.99,19.99,,,18.0\n"  # null parallax + snr -> NaN
)


def _plate(ra=150.0, dec=20.0, scale=4.0, nx=256, ny=256):
    return PlateSolution(
        wcs=_tan_wcs(ra, dec, scale, nx, ny), source="mock", width=nx, height=ny
    )


def test_distance_label_rules():
    """Name wins; a distance is shown ONLY for a trustworthy parallax; a junk
    parallax falls back to the G magnitude, never a fabricated distance."""
    assert gaiacone.distance_label("Proxima Cen", 768.0, 900.0, 9.0) == "Proxima Cen"
    assert gaiacone.distance_label(None, 5.0, 20.0, 12.0) == "200 pc"  # 1000/5
    # snr below 5 -> no distance, fall to magnitude
    assert gaiacone.distance_label(None, -0.4, 1.1, 19.6) == "G 19.6"
    # non-positive parallax even with high snr -> no distance
    assert gaiacone.distance_label(None, 0.0, 10.0, 15.0) == "G 15.0"
    # nothing usable -> None (marker only)
    nan = float("nan")
    assert gaiacone.distance_label(None, nan, nan, nan) is None


def test_footprint_cache_key_shared_by_near_identical_plates():
    """Two frames pointing within 0.01 deg (as the repeated LORRI frames do)
    must map to ONE cone file, so the same pointing is fetched once."""
    a = _plate(ra=150.000)
    b = _plate(ra=150.004)  # 0.004 deg apart -> rounds to the same key
    assert gaiacone._cache_path(a, "/x") == gaiacone._cache_path(b, "/x")


def test_cache_hit_costs_zero_network(tmp_path, monkeypatch):
    """A present cone file is parsed with NO network call at all."""

    def _boom(*a, **k):
        raise AssertionError("cache hit must not fetch")

    monkeypatch.setattr(gaiacone, "_fetch_cone_csv", _boom)
    plate = _plate()
    gaiacone._cache_path(plate, tmp_path).write_text(CONE_CSV, encoding="utf-8")
    cone = gaiacone.cone_catalog(plate, cache_dir=tmp_path, allow_fetch=True)
    assert cone is not None
    assert cone["source_id"].shape[0] == 3
    assert cone["positions_au"].shape == (3, 3)
    assert np.isnan(cone["parallax_mas"][2])  # the null cell parsed to NaN


def test_missing_cone_returns_none_without_fetch_when_disallowed(tmp_path, monkeypatch):
    """render passes allow_fetch=False: a missing cone yields None (no network)
    so a preview can never block on the TAP service."""
    monkeypatch.setattr(
        gaiacone,
        "_fetch_cone_csv",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no fetch allowed")),
    )
    cone = gaiacone.cone_catalog(_plate(), cache_dir=tmp_path, allow_fetch=False)
    assert cone is None


def test_network_failure_degrades_to_none(tmp_path, monkeypatch):
    """A network/TAP failure on a cache miss returns None (never raises) and
    leaves no half-written cache file behind."""

    def _offline(*a, **k):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(gaiacone, "_fetch_cone_csv", _offline)
    plate = _plate()
    cone = gaiacone.cone_catalog(plate, cache_dir=tmp_path, allow_fetch=True)
    assert cone is None
    assert not gaiacone._cache_path(plate, tmp_path).exists()


def _cone_scene():
    """A distortion-free plate + a 2-star cone at known in-frame pixels: one
    nearby star with a trustworthy parallax, one faint star with a junk one."""
    plate = _plate()
    pixels = [(128.0, 128.0), (60.0, 90.0)]
    plx = [50.0, -0.4]  # mas: 50 -> 20 pc; -0.4 junk
    snr = [100.0, 1.1]
    gmag = [10.2, 19.6]
    sids = [900100, 900200]
    positions = []
    for px, py in pixels:
        sky = plate.wcs.pixel_to_world(px, py).icrs
        positions.append(radec_to_unit(deg_to_rad(sky.ra.deg), deg_to_rad(sky.dec.deg)))
    cone = {
        "positions_au": np.array(positions, dtype=float),
        "source_id": np.array(sids, dtype=np.int64),
        "parallax_mas": np.array(plx, dtype=float),
        "parallax_over_error": np.array(snr, dtype=float),
        "phot_g_mag": np.array(gmag, dtype=float),
    }
    return plate, cone, np.array(pixels, dtype=float), sids


def test_cone_label_set_honest_labels_and_flags():
    """Deep-identify labelling: the good-parallax star gets a distance and is
    flagged position-capable when passed as such; the junk-parallax faint star
    gets a G magnitude (never a fabricated distance)."""
    plate, cone, centroids, sids = _cone_scene()
    labels = webapp.cone_label_set(
        plate, centroids, cone, position_capable_ids={sids[0]}
    )
    by = {lab["source_id"]: lab for lab in labels}
    assert len(labels) == 2
    assert by[sids[0]]["text"] == "20 pc"
    assert by[sids[0]]["position_capable"] is True
    assert by[sids[1]]["text"] == "G 19.6"
    assert "pc" not in by[sids[1]]["text"]
    assert by[sids[1]]["dist_pc"] is None
    assert by[sids[1]]["position_capable"] is False


def test_render_degrades_without_cone(monkeypatch):
    """With no cone available, render must still produce a PNG by falling back to
    the nearby-catalog labels -- the cone is a bonus, never a dependency."""
    from pathlib import Path

    monkeypatch.setattr(gaiacone, "cone_catalog", lambda *a, **k: None)
    monkeypatch.setattr(webapp, "WIDE_CATALOG_CSV", Path(webapp.CATALOG_CSV))
    monkeypatch.setattr(webapp, "_BAD_WIDE_MTIME", set())
    png = webapp.render_frame_png("f0", 4.31, 120)
    assert bytes(png[:8]) == b"\x89PNG\r\n\x1a\n"
