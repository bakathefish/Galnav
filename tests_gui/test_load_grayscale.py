"""Tests for gui.app.load_grayscale image loading -- specifically the TESS/Kepler
target-pixel-file (TPF) path, where the imagery lives in a binary table and the
only IMAGE HDU is the (all-ones) aperture mask.

Synthetic FITS written with astropy -- no network, no committed data.
"""

import numpy as np
from astropy.io import fits

from gui.app import load_grayscale
from gui.centroids import find_centroids


def _write_tpf(path, ny=20, nx=20, ncad=6, star_yx=(11, 8), amp=500.0, sigma=1.4):
    """Write a minimal TESS-style target-pixel file: PRIMARY, a PIXELS binary
    table whose FLUX column is a per-cadence 2-D image cube (a Gaussian star plus
    small noise, with one all-NaN gap cadence to exercise the NaN-tolerant
    median), and an all-ones APERTURE image (the trap the old loader fell into).
    """
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:ny, 0:nx]
    star = amp * np.exp(
        -((xx - star_yx[1]) ** 2 + (yy - star_yx[0]) ** 2) / (2.0 * sigma**2)
    )
    flux = np.empty((ncad, ny, nx), dtype=np.float32)
    for i in range(ncad):
        flux[i] = star + rng.normal(0.0, 2.0, size=(ny, nx))
    flux[0] = np.nan  # a gap cadence -- nanmedian must ignore it
    time_col = fits.Column(name="TIME", format="D", array=np.arange(ncad, dtype=float))
    flux_col = fits.Column(
        name="FLUX", format=f"{ny * nx}E", dim=f"({nx},{ny})", array=flux
    )
    pixels = fits.BinTableHDU.from_columns([time_col, flux_col], name="PIXELS")
    aperture = fits.ImageHDU(np.ones((ny, nx), dtype=np.float32), name="APERTURE")
    fits.HDUList([fits.PrimaryHDU(), pixels, aperture]).writeto(path, overwrite=True)
    return star_yx


def test_load_grayscale_tess_tpf_uses_flux_median(tmp_path):
    """A TPF must load the median-over-time FLUX frame, NOT the aperture mask.

    If the loader grabbed the APERTURE image HDU (the pre-fix bug), the frame
    would be all ones (max == 1.0) and centroid nothing. The FLUX median has a
    real star, so its peak is near the injected amplitude, it is not uniform, and
    the NaN gap cadence leaves no non-finite pixels."""
    path = tmp_path / "tess_tpf.fits"
    (sy, sx) = _write_tpf(path)
    frame = load_grayscale(path)
    assert frame.shape == (20, 20)
    assert np.all(np.isfinite(frame))  # the all-NaN cadence was ignored
    assert not np.allclose(frame, 1.0)  # NOT the all-ones aperture mask
    assert frame.max() > 100.0  # real flux, not a 0/1 mask
    peak_row, peak_col = np.unravel_index(int(np.argmax(frame)), frame.shape)
    assert abs(peak_row - sy) <= 1 and abs(peak_col - sx) <= 1


def test_load_grayscale_tess_tpf_is_centroidable(tmp_path):
    """The derived frame must actually centroid the injected star -- proving the
    TPF is usable by the pipeline (the aperture mask detects nothing)."""
    path = tmp_path / "tess_tpf.fits"
    (sy, sx) = _write_tpf(path)
    frame = load_grayscale(path)
    cen = find_centroids(frame)
    assert cen["xy"].shape[0] >= 1
    d = np.hypot(cen["xy"][:, 0] - sx, cen["xy"][:, 1] - sy).min()
    assert d < 1.0  # detection lands on the injected star (x=col, y=row)


def test_load_grayscale_plain_image_fits_unaffected(tmp_path):
    """A normal single-image FITS (no PIXELS table) still loads its 2-D data --
    the TPF branch must not disturb ordinary frames (e.g. the NH LORRI set)."""
    path = tmp_path / "plain.fits"
    img = np.arange(20, dtype=np.float32).reshape(4, 5)
    fits.PrimaryHDU(img).writeto(path, overwrite=True)
    out = load_grayscale(path)
    assert out.shape == (4, 5)
    assert np.array_equal(out, img)
