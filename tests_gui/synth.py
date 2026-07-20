"""Shared synthetic-scene builder for the GUI tests. Deterministic and
offline: it uses the committed real Gaia subset (data/gaia_dr3_nav_subset.csv),
a hand-built TAN WCS, and a seeded RNG. No network, no truth-side imports.

A scene places a spacecraft at a known position r_au, ages the real catalog to
a known age, computes the TRUE spacecraft->star directions (which include
parallax and are what the frame actually records), projects them through the
WCS to pixels, and renders Gaussian star images plus filler stars and noise.
Every truth quantity used to build the frame is returned so a test can check
what the pipeline recovers against what was injected.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from astropy.wcs import WCS

from galnav.units import deg_to_rad, radec_to_unit
from gui.locate import load_aged_catalog
from gui.platesolve import PlateSolution

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"

# First six catalog source ids (nearest-first): Proxima, Barnard, Wolf 359, ...
PROXIMA_ID = 5853498713190525696
BARNARD_ID = 4472832130942575872
WOLF_ID = 3864972938605115520

# A well-isolated WIDE pair of nearby stars for the "two nearby stars, ONE image"
# demonstration: 10.56 deg apart on the sky (so a single wide-field TAN frame can
# hold both), each > 1.8 deg from any other catalog star (so identify_in_frame
# cannot grab a wrong neighbour), and both near (3.97 and 4.97 pc) for a short
# error lever. They are the widest such isolated near pair in the frozen 20-pc
# catalog; the three named stars above are 78-105 deg apart and never co-frame.
WIDE_PAIR_A_ID = 6583272171336048640  # 3.97 pc
WIDE_PAIR_B_ID = 6562924609150908416  # 4.97 pc


@dataclass
class Scene:
    """One synthetic frame's inputs.

    r_au: (3,) true spacecraft position, au (barycentric).
    source_ids: catalog source ids to place; the WCS centres on the first.
    age_yr: true catalog age (Julian years since J2016.0).
    scale_arcsec_px: plate scale (arcsec/pixel).
    size_px: (nx, ny) image size.
    seed: RNG seed for the noise (fully determines the frame).
    psf_sigma_px: Gaussian PSF sigma (pixels).
    peak: star peak amplitude (counts).
    noise_sigma: Gaussian read-noise sigma (counts).
    filler_xy: fixed (x, y) pixel positions of non-catalog "filler" stars.
    rv_fill_kms: RV fill for stars with no catalog RV (must match the solver).
    """

    r_au: np.ndarray
    source_ids: list
    age_yr: float = 4.5
    scale_arcsec_px: float = 4.0
    size_px: tuple = (256, 256)
    seed: int = 1234
    psf_sigma_px: float = 1.2
    peak: float = 1000.0
    noise_sigma: float = 5.0
    filler_xy: list = field(default_factory=lambda: [(40.0, 40.0), (200.0, 60.0)])
    rv_fill_kms: float = 0.0


def _tan_wcs(ra_deg, dec_deg, scale_arcsec_px, nx, ny):
    """Build a simple TAN WCS centred on (ra_deg, dec_deg)."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix = [(nx + 1) / 2.0, (ny + 1) / 2.0]  # 1-indexed centre pixel
    w.wcs.crval = [ra_deg, dec_deg]
    w.wcs.cdelt = [-scale_arcsec_px / 3600.0, scale_arcsec_px / 3600.0]
    w.wcs.cunit = ["deg", "deg"]
    return w


def _unit_to_radec_deg(u):
    """Unit vector -> (ra_deg, dec_deg)."""
    ra = np.rad2deg(np.arctan2(u[1], u[0])) % 360.0
    dec = np.rad2deg(np.arcsin(np.clip(u[2], -1.0, 1.0)))
    return ra, dec


def build_synthetic(scene):
    """Render one synthetic frame and return it with all injected truth.

    scene: a Scene.
    Returns: dict with
        image: (ny, nx) float frame (row=y, col=x);
        plate: PlateSolution wrapping the TAN WCS (source="mock");
        wcs: the astropy WCS;
        r_au: (3,) true spacecraft position;
        aged_cat: load_aged_catalog(...) dict at scene.age_yr (full catalog);
        star_indices: row indices into aged_cat for scene.source_ids;
        directions: (K, 3) TRUE spacecraft->star unit vectors (apparent);
        apparent_xy: (K, 2) star pixels from the apparent directions;
        bary_xy: (K, 2) star pixels from the BARYCENTRIC directions (what
            identify_in_frame predicts before parallax);
        in_frame: (K,) bool, which stars land inside the image;
        filler_xy: (F, 2) filler pixel positions.
    """
    nx, ny = scene.size_px
    aged = load_aged_catalog(REAL_CSV, scene.age_yr, rv_fill_kms=scene.rv_fill_kms)
    ids = aged["source_id"]
    star_indices = [int(np.nonzero(ids == sid)[0][0]) for sid in scene.source_ids]
    positions = aged["positions_au"][star_indices]  # (K, 3)

    # TRUE spacecraft->star directions (include parallax) and barycentric ones.
    dvec = positions - np.asarray(scene.r_au, dtype=float)
    directions = dvec / np.linalg.norm(dvec, axis=1, keepdims=True)
    bary = positions / np.linalg.norm(positions, axis=1, keepdims=True)

    # Centre the WCS on the first star's apparent direction.
    ra0, dec0 = _unit_to_radec_deg(directions[0])
    w = _tan_wcs(ra0, dec0, scene.scale_arcsec_px, nx, ny)

    def to_pix(units):
        ra = np.rad2deg(np.arctan2(units[:, 1], units[:, 0])) % 360.0
        dec = np.rad2deg(np.arcsin(np.clip(units[:, 2], -1.0, 1.0)))
        from astropy.coordinates import SkyCoord

        sky = SkyCoord(ra=ra, dec=dec, unit="deg", frame="icrs")
        px, py = w.world_to_pixel(sky)
        return np.column_stack([np.atleast_1d(px), np.atleast_1d(py)])

    apparent_xy = to_pix(directions)
    bary_xy = to_pix(bary)
    in_frame = (
        (apparent_xy[:, 0] >= 0)
        & (apparent_xy[:, 0] <= nx - 1)
        & (apparent_xy[:, 1] >= 0)
        & (apparent_xy[:, 1] <= ny - 1)
    )

    # Render.
    rng = np.random.default_rng(scene.seed)
    yy, xx = np.mgrid[0:ny, 0:nx]
    image = np.zeros((ny, nx), dtype=float)
    two_s2 = 2.0 * scene.psf_sigma_px**2
    for k in np.nonzero(in_frame)[0]:
        x, y = apparent_xy[k]
        image += scene.peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / two_s2)
    for x, y in scene.filler_xy:
        image += 0.6 * scene.peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / two_s2)
    image += rng.normal(0.0, scene.noise_sigma, size=image.shape)

    plate = PlateSolution(wcs=w, source="mock", width=nx, height=ny)
    return {
        "image": image,
        "plate": plate,
        "wcs": w,
        "r_au": np.asarray(scene.r_au, dtype=float),
        "aged_cat": aged,
        "star_indices": star_indices,
        "directions": directions,
        "apparent_xy": apparent_xy,
        "bary_xy": bary_xy,
        "in_frame": in_frame,
        "filler_xy": np.asarray(scene.filler_xy, dtype=float),
    }
