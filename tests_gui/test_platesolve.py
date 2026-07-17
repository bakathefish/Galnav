"""Tests for gui.platesolve -- where the WCS comes from.

All backends are exercised OFFLINE: fits-header on real bytes written to
tmp_path; wsl/nova as monkeypatched failures for the ordering test; nova's full
parse against a monkeypatched urlopen returning canned JSON + canned WCS bytes.
No network, no subprocess, no WSL required.
"""

import io

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from gui import platesolve

# The round-trip must reproduce the injected TAN geometry; astropy stores the
# header in float64, so agreement is ~1e-9. We check to 1e-6 deg (~0.004 arcsec)
# in centre and 1e-3 arcsec/px in scale -- tight enough to catch a swapped
# CDELT sign or a celestial/pixel confusion, loose against header rounding.
CENTER_TOL_DEG = 1e-6
SCALE_TOL_ARCSEC = 1e-3


def _tan_header(ra, dec, scale_arcsec_px, nx, ny):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix = [(nx + 1) / 2.0, (ny + 1) / 2.0]
    w.wcs.crval = [ra, dec]
    w.wcs.cdelt = [-scale_arcsec_px / 3600.0, scale_arcsec_px / 3600.0]
    w.wcs.cunit = ["deg", "deg"]
    return w


def test_fits_header_round_trip(tmp_path):
    """A FITS with a WCS header must yield a PlateSolution whose centre and
    scale match what was written -- the core of the free/offline backend."""
    nx, ny, ra, dec, scale = 128, 128, 210.5, -30.25, 3.2
    w = _tan_header(ra, dec, scale, nx, ny)
    header = w.to_header()
    data = np.zeros((ny, nx), dtype=np.float32)
    path = tmp_path / "wcs_frame.fits"
    fits.writeto(path, data, header, overwrite=True)

    sol = platesolve.fits_header_solution(path)
    assert sol is not None
    assert sol.source == "fits-header"
    assert (sol.width, sol.height) == (nx, ny)
    cra, cdec = sol.center_radec_deg
    assert abs(cra - ra) < CENTER_TOL_DEG
    assert abs(cdec - dec) < CENTER_TOL_DEG
    assert abs(sol.scale_arcsec_per_px - scale) < SCALE_TOL_ARCSEC


def test_fits_header_returns_none_without_wcs(tmp_path):
    """A plain image FITS (no celestial keywords) must return None so the
    orchestrator falls through to a blind solver instead of guessing."""
    path = tmp_path / "plain.fits"
    fits.writeto(path, np.zeros((32, 32), dtype=np.float32), overwrite=True)
    assert platesolve.fits_header_solution(path) is None


def test_solve_image_tries_in_order_and_aggregates(tmp_path, monkeypatch):
    """When every backend fails, solve_image must try them in the requested
    order and raise ONE error naming each failure -- so a user sees why all
    three routes were unavailable, not just the first."""
    path = tmp_path / "plain.fits"
    fits.writeto(path, np.zeros((16, 16), dtype=np.float32), overwrite=True)

    calls = []

    def fake_wsl(*a, **k):
        calls.append("wsl")
        raise RuntimeError("no solve-field here")

    def fake_nova(*a, **k):
        calls.append("nova")
        raise RuntimeError("no api key here")

    monkeypatch.setattr(platesolve, "wsl_solve", fake_wsl)
    monkeypatch.setattr(platesolve, "nova_solve", fake_nova)

    with pytest.raises(RuntimeError) as exc:
        platesolve.solve_image(path, prefer=("fits-header", "wsl", "nova"))
    msg = str(exc.value)
    assert calls == ["wsl", "nova"]  # fits-header returned None, no exception
    assert "fits-header" in msg and "no solve-field here" in msg
    assert "no api key here" in msg
    assert "nova.astrometry.net" in msg  # tells the user how to enable a backend


def _canned_wcs_bytes(nx=200, ny=150, ra=45.0, dec=12.0, scale=2.5):
    w = _tan_header(ra, dec, scale, nx, ny)
    header = w.to_header()
    header["IMAGEW"] = nx
    header["IMAGEH"] = ny
    buf = io.BytesIO()
    fits.PrimaryHDU(header=header).writeto(buf)
    return buf.getvalue(), (nx, ny, ra, dec, scale)


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_nova_solve_parses_canned_response(tmp_path, monkeypatch):
    """nova_solve must walk login->upload->poll->download and parse the WCS
    without any network; breaks if the API step sequence or WCS parse regress."""
    img_path = tmp_path / "sky.fits"
    fits.writeto(img_path, np.zeros((150, 200), dtype=np.float32), overwrite=True)
    wcs_bytes, (nx, ny, ra, dec, scale) = _canned_wcs_bytes()

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        if "/api/login" in url:
            return _FakeResp(b'{"status": "success", "session": "sess"}')
        if "/api/upload" in url:
            return _FakeResp(b'{"status": "success", "subid": 7}')
        if "/api/submissions/7" in url:
            return _FakeResp(b'{"jobs": [99], "job_calibrations": []}')
        if "/api/jobs/99" in url:
            return _FakeResp(b'{"status": "success"}')
        if "/wcs_file/99" in url:
            return _FakeResp(wcs_bytes)
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(platesolve, "urlopen", fake_urlopen)

    sol = platesolve.nova_solve(img_path, api_key="dummy")
    assert sol.source == "nova"
    assert (sol.width, sol.height) == (nx, ny)
    cra, cdec = sol.center_radec_deg
    assert abs(cra - ra) < 1e-4 and abs(cdec - dec) < 1e-4
    assert abs(sol.scale_arcsec_per_px - scale) < 1e-2


def test_nova_solve_requires_key(tmp_path, monkeypatch):
    """With no key and no env var, nova_solve must fail fast with a helpful
    message rather than attempt an unauthenticated request."""
    monkeypatch.delenv("ASTROMETRY_NET_API_KEY", raising=False)
    img_path = tmp_path / "sky.fits"
    fits.writeto(img_path, np.zeros((8, 8), dtype=np.float32), overwrite=True)
    with pytest.raises(RuntimeError, match="API key"):
        platesolve.nova_solve(img_path)


def test_fits_header_solution_non_fits_message(tmp_path):
    """A PNG fed to the fits-header backend must raise a plain-English 'not a
    FITS file' hint, not astropy's cryptic 'No SIMPLE card' error, so the user
    knows a PNG needs a blind solve."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    png = tmp_path / "star.png"
    plt.imsave(png, np.random.default_rng(0).random((16, 16)), cmap="gray")
    with pytest.raises(RuntimeError, match="not a FITS file"):
        platesolve.fits_header_solution(png)
    # solve_image must surface that reason (no blind backend available here).
    with pytest.raises(RuntimeError, match="not a FITS file"):
        platesolve.solve_image(png, prefer=("fits-header",))


def _capture_wsl_cmd(monkeypatch, cfg_present):
    """Drive wsl_solve up to the solve-field call and return the argv it built.

    Stubs the two WSL probes (so no real `wsl` runs) and intercepts
    subprocess.run to snapshot the command, then aborts before the .wcs step.
    """
    monkeypatch.setattr(platesolve, "_wsl_available", lambda: True)
    monkeypatch.setattr(platesolve, "_wsl_has_galnav_config", lambda: cfg_present)
    captured = {}

    class _Stop(Exception):
        pass

    def fake_run(cmd, *a, **k):
        captured["cmd"] = list(cmd)
        raise _Stop()

    monkeypatch.setattr(platesolve.subprocess, "run", fake_run)
    with pytest.raises(_Stop):
        platesolve.wsl_solve("C:/tmp/img.fits")
    return captured["cmd"]


def test_wsl_solve_passes_config_when_present(monkeypatch):
    """When ~/.galnav-astrometry.cfg exists in WSL, solve-field must be invoked
    with `--config ~/.galnav-astrometry.cfg` so it sees our wide+narrow indexes;
    the input image stays the last (positional) argument."""
    cmd = _capture_wsl_cmd(monkeypatch, cfg_present=True)
    assert "--config" in cmd
    assert cmd[cmd.index("--config") + 1] == "~/.galnav-astrometry.cfg"
    assert cmd[0] == "wsl" and cmd[1] == "solve-field"
    assert cmd[-1] == "/mnt/c/tmp/img.fits"  # positional file last


def test_wsl_solve_omits_config_when_absent(monkeypatch):
    """When the config is NOT present, --config must be omitted entirely so a
    stock astrometry.net install (no GalNav cfg) is not broken by a missing
    config file."""
    cmd = _capture_wsl_cmd(monkeypatch, cfg_present=False)
    assert "--config" not in cmd
    assert cmd[-1] == "/mnt/c/tmp/img.fits"
