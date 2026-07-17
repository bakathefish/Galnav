"""Pixels -> star positions. Find the bright compact sources (stars) in a
2-D image and return their sub-pixel centres and brightnesses. Pure
numpy/scipy; no per-pixel Python loops (it loops only over the handful of
labelled components, which scipy does in C).
"""

import numpy as np
from scipy import ndimage
from scipy.optimize import least_squares


def _refine_gaussian(img, x_guess, y_guess, half=3):
    """Sub-pixel refine one star by fitting a 2-D circular Gaussian in a stamp.

    Fits A*exp(-((x-x0)^2+(y-y0)^2)/(2 sigma^2)) + b over a
    (2*half+1) x (2*half+1) stamp centred on the rounded moment centroid, using
    scipy.optimize.least_squares (no new dependency). The offset b absorbs the
    background so the raw image is fit directly. Returns the refined (x, y) if
    the fit is sane, else the input moment centroid unchanged -- specifically it
    FALLS BACK when: the star is too close to an edge to cut a full stamp; the
    stamp has no positive amplitude; the star is SATURATED (a flat top -- many
    pixels at the peak -- where a Gaussian centre is ill-defined); the solver did
    not converge; the fitted amplitude is non-positive; or the fitted centre
    moved >= 1.5 px from the moment centroid (a runaway fit).

    img: (H, W) real image. x_guess, y_guess: moment centroid (global pixels).
    half: stamp half-width in pixels (stamp is 2*half+1 square; default 3 -> 7x7).
    Returns: (x, y) float pixel centroid.
    """
    ny, nx = img.shape
    xi, yi = int(round(x_guess)), int(round(y_guess))
    if xi - half < 0 or yi - half < 0 or xi + half + 1 > nx or yi + half + 1 > ny:
        return x_guess, y_guess  # too close to an edge for a full stamp
    stamp = img[yi - half : yi + half + 1, xi - half : xi + half + 1].astype(float)
    base = float(np.median(stamp))
    peak = float(stamp.max())
    amp0 = peak - base
    if amp0 <= 0.0:
        return x_guess, y_guess
    # Saturation guard: a resolved Gaussian core peaks in ~1 pixel; a flat top
    # (many pixels within 2% of the peak) is a saturated star -- keep the robust
    # flux-weighted centroid rather than fit a Gaussian to a plateau.
    if np.count_nonzero(stamp >= peak - 0.02 * amp0) > 4:
        return x_guess, y_guess

    ys, xs = np.mgrid[yi - half : yi + half + 1, xi - half : xi + half + 1]
    xs = xs.astype(float)
    ys = ys.astype(float)

    def resid(p):
        amp, x0, y0, sig, off = p
        model = amp * np.exp(-((xs - x0) ** 2 + (ys - y0) ** 2) / (2.0 * sig**2)) + off
        return (model - stamp).ravel()

    p0 = [amp0, float(x_guess), float(y_guess), 1.5, base]
    lo = [0.0, x_guess - half, y_guess - half, 0.3, -np.inf]
    hi = [np.inf, x_guess + half, y_guess + half, float(half), np.inf]
    try:
        res = least_squares(resid, p0, bounds=(lo, hi), max_nfev=300)
    except Exception:  # noqa: BLE001 -- any solver failure -> keep the moment
        return x_guess, y_guess
    amp, x0, y0, _sig, _off = res.x
    if not res.success or amp <= 0.0 or np.hypot(x0 - x_guess, y0 - y_guess) >= 1.5:
        return x_guess, y_guess
    return float(x0), float(y0)


def find_centroids(
    image_2d,
    threshold_sigma=5.0,
    min_pixels=3,
    max_sources=200,
    refine=False,
    stamp_half=3,
):
    """Detect stars and return their flux-weighted pixel centroids.

    Detection: robust background = median(image); robust noise =
    1.4826 * MAD (median absolute deviation, the normal-consistent estimator
    of sigma); a pixel is "bright" if image > background + threshold_sigma *
    noise. Connected bright pixels are grouped (scipy.ndimage.label);
    groups smaller than min_pixels are dropped as noise spikes; each surviving
    group's centre is its flux-weighted centroid (center_of_mass on the
    background-subtracted image) and its flux is the summed excess.

    Optional PSF refinement (refine=True): after the flux-weighted centroid, a
    2-D circular Gaussian is fit in a small stamp around each star and its centre
    replaces the moment centroid when the fit is sane (see _refine_gaussian for
    the fall-back rules -- edge, no amplitude, saturation, non-convergence, or a
    >=1.5 px runaway all keep the moment centroid). The moment centroid is a
    robust default; the Gaussian fit is the more accurate estimator for a
    well-sampled, unsaturated star. Off by default; adopt only if measured to
    help (see journal/gui-wrapper.md, "PSF-centroid accuracy trial").

    image_2d: (H, W) real-valued image (row = y, col = x).
    threshold_sigma: detection threshold in units of the robust noise sigma.
    min_pixels: minimum connected pixels for a real source (rejects hot pixels).
    max_sources: keep at most this many, brightest first.
    refine: if True, PSF-refine each centroid with a Gaussian fit (see above).
    stamp_half: half-width (px) of the refinement stamp; 3 -> a 7x7 stamp.
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

    if refine and xy.shape[0]:
        xy = np.array(
            [_refine_gaussian(img, x, y, stamp_half) for x, y in xy], dtype=float
        )
    return {"xy": xy, "flux": flux}
