"""Pixels -> star positions. Find the bright compact sources (stars) in a
2-D image and return their sub-pixel centres and brightnesses. Pure
numpy/scipy; no per-pixel Python loops (it loops only over the handful of
labelled components, which scipy does in C).
"""

import numpy as np
from scipy import ndimage


def find_centroids(image_2d, threshold_sigma=5.0, min_pixels=3, max_sources=200):
    """Detect stars and return their flux-weighted pixel centroids.

    Detection: robust background = median(image); robust noise =
    1.4826 * MAD (median absolute deviation, the normal-consistent estimator
    of sigma); a pixel is "bright" if image > background + threshold_sigma *
    noise. Connected bright pixels are grouped (scipy.ndimage.label);
    groups smaller than min_pixels are dropped as noise spikes; each surviving
    group's centre is its flux-weighted centroid (center_of_mass on the
    background-subtracted image) and its flux is the summed excess.

    image_2d: (H, W) real-valued image (row = y, col = x).
    threshold_sigma: detection threshold in units of the robust noise sigma.
    min_pixels: minimum connected pixels for a real source (rejects hot pixels).
    max_sources: keep at most this many, brightest first.
    Returns: dict with
        xy: (M, 2) float array of (x, y) centroids in 0-indexed pixel
            coordinates matching astropy's WCS pixel convention (x = column,
            y = row), brightest source first;
        flux: (M,) summed background-subtracted flux, sorted brightest-first.
    """
    img = np.asarray(image_2d, dtype=float)
    bg = np.median(img)
    mad = np.median(np.abs(img - bg))
    noise = 1.4826 * mad
    # A perfectly flat region has MAD 0; fall back to std so the threshold is
    # finite and nothing spurious passes.
    if noise == 0.0:
        noise = np.std(img)
    if noise == 0.0:
        return {"xy": np.empty((0, 2)), "flux": np.empty((0,))}

    excess = img - bg
    mask = excess > threshold_sigma * noise
    labels, n = ndimage.label(mask)
    if n == 0:
        return {"xy": np.empty((0, 2)), "flux": np.empty((0,))}

    sizes = np.bincount(labels.ravel())  # sizes[0] = background
    keep = np.nonzero(sizes[1:] >= min_pixels)[0] + 1  # label ids, 1-based
    if keep.size == 0:
        return {"xy": np.empty((0, 2)), "flux": np.empty((0,))}

    weights = np.clip(excess, 0.0, None)
    coms = ndimage.center_of_mass(weights, labels, keep)  # list of (row, col)
    flux = ndimage.sum(weights, labels, keep)
    coms = np.atleast_2d(np.asarray(coms, dtype=float))
    flux = np.atleast_1d(np.asarray(flux, dtype=float))
    # (row, col) -> (x, y) = (col, row) for the WCS pixel convention.
    xy = np.column_stack([coms[:, 1], coms[:, 0]])

    order = np.argsort(flux)[::-1]
    xy = xy[order][:max_sources]
    flux = flux[order][:max_sources]
    return {"xy": xy, "flux": flux}
