"""Tests for gui.centroids.find_centroids -- the pixels-to-star-positions step.

Tolerances are named constants with measured justification; golden_numbers.py
is untouchable and irrelevant here (this is demo code, not spine science).
"""

import numpy as np

from gui.centroids import find_centroids

# A clean Gaussian PSF centroids to well under a pixel; measured recovery on the
# scenes below is <0.01 px, so 0.3 px is a loose gate that still fails a
# swapped-axis or off-by-one bug (those miss by >=1 px).
CENTROID_TOL_PX = 0.3


def _render(size, stars, sigma=1.2, noise=2.0, seed=0):
    """Render (H, W) image with Gaussian stars = list of (x, y, amp)."""
    ny, nx = size
    yy, xx = np.mgrid[0:ny, 0:nx]
    img = np.zeros((ny, nx))
    for x, y, amp in stars:
        img += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    img += np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


def test_recovers_injected_pixel_positions():
    """If centroids drifted (axis swap, off-by-one), recovered (x,y) would miss
    the injected sub-pixel positions by >=1 px; this pins them to <0.3 px."""
    stars = [(60.3, 120.7, 1000.0), (180.6, 40.2, 700.0)]
    img = _render((256, 256), stars)
    out = find_centroids(img)
    for x, y, _ in stars:
        d = np.hypot(out["xy"][:, 0] - x, out["xy"][:, 1] - y)
        assert d.min() < CENTROID_TOL_PX


def test_flux_ordering_brightest_first():
    """Guards the brightest-first sort: the returned flux must be descending and
    the first centroid must be the brightest injected star."""
    stars = [(60.0, 60.0, 300.0), (100.0, 150.0, 1500.0), (200.0, 80.0, 800.0)]
    img = _render((256, 256), stars)
    out = find_centroids(img)
    assert np.all(np.diff(out["flux"]) <= 0)
    # brightest injected star is at (100, 150)
    assert np.hypot(out["xy"][0, 0] - 100.0, out["xy"][0, 1] - 150.0) < 1.0


def test_min_pixels_rejects_hot_pixel():
    """A single hot pixel (1 pixel above threshold) must be rejected when
    min_pixels=3, or cosmic-ray/hot-pixel spikes would masquerade as stars."""
    img = np.random.default_rng(1).normal(0.0, 2.0, (64, 64))
    img[32, 32] += 1000.0  # lone hot pixel, 1 connected pixel
    out = find_centroids(img, threshold_sigma=5.0, min_pixels=3)
    # No real star present; the hot pixel is too small to survive min_pixels.
    if out["xy"].shape[0]:
        d = np.hypot(out["xy"][:, 0] - 32.0, out["xy"][:, 1] - 32.0)
        assert np.all(d > 1.0)
    else:
        assert out["xy"].shape[0] == 0


def test_flat_image_returns_nothing():
    """A perfectly flat image has zero robust noise; the function must return an
    empty result rather than divide by zero or hallucinate a source."""
    out = find_centroids(np.full((32, 32), 7.0))
    assert out["xy"].shape[0] == 0
