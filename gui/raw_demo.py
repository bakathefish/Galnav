"""Make a WCS-stripped ("raw") copy of a New Horizons LORRI demo frame.

The baked demo FITS frames already carry a plate solution (WCS) in their header,
so the app reads their sky coordinates for free. A REAL uploaded telescope /
spacecraft image usually has NO such header -- it needs a blind plate solve. This
tool writes a copy of a chosen demo frame with every WCS keyword removed, giving
you a genuine "raw image" (pixels only, no coordinates) to upload LIVE once a
blind solver is installed (WSL astrometry.net, or a nova API key). Uploading it
exercises the full raw path end to end -- plate-solve -> centroid -> identify ->
locate -- exactly what an arbitrary image goes through.

    python -m gui.raw_demo                       # default frame -> results/
    python -m gui.raw_demo <src.fits> <out_dir>  # choose the frame and folder

Reads the source read-only; writes one new FITS. Uses only astropy (already a
dependency).
"""

import sys
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SRC = (
    REPO / "data" / "e3_new_horizons" / "repo" / "lor_0449855930_0x633_pwcs2.fits"
)
DEFAULT_OUT = REPO / "results"  # git-ignored (results/*); a findable local folder

# Explicit WCS/SIP keywords to remove in addition to whatever astropy reports,
# so the copy has NO celestial solution and forces the blind-solve path.
_WCS_KEYS = {
    "WCSAXES",
    "CTYPE1",
    "CTYPE2",
    "CRVAL1",
    "CRVAL2",
    "CRPIX1",
    "CRPIX2",
    "CDELT1",
    "CDELT2",
    "CUNIT1",
    "CUNIT2",
    "CD1_1",
    "CD1_2",
    "CD2_1",
    "CD2_2",
    "PC1_1",
    "PC1_2",
    "PC2_1",
    "PC2_2",
    "CROTA1",
    "CROTA2",
    "LONPOLE",
    "LATPOLE",
    "RADESYS",
    "EQUINOX",
    "A_ORDER",
    "B_ORDER",
    "AP_ORDER",
    "BP_ORDER",
}


def strip_wcs(header, hdulist=None):
    """Delete every WCS/SIP keyword from a FITS header, in place.

    header: an astropy FITS Header (modified in place).
    hdulist: the parent HDUList, so a SIP-distorted WCS resolves before we read
        off its keyword names.
    """
    keys = set(_WCS_KEYS)
    try:
        keys |= set(WCS(header, hdulist, relax=True).to_header(relax=True).keys())
    except Exception:  # noqa: BLE001 -- no WCS to enumerate; the explicit set suffices
        pass
    # SIP polynomial terms: A_i_j / B_i_j / AP_i_j / BP_i_j (have a digit).
    for k in list(header.keys()):
        parts = k.split("_")
        if parts[0] in ("A", "B", "AP", "BP") and any(c.isdigit() for c in k):
            keys.add(k)
    for k in keys:
        if k in header:
            del header[k]


def make_raw_copy(src, out_dir):
    """Write a WCS-stripped copy of `src` into `out_dir`; return the output path.

    Raises AssertionError if any 2-D HDU still has a celestial WCS afterwards
    (the strip must be complete, or the "raw" image would not be raw).
    """
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (src.stem + "_RAW_no_wcs.fits")
    with fits.open(src) as hdul:
        for hdu in hdul:
            strip_wcs(hdu.header, hdul)
        hdul.writeto(out, overwrite=True)
    with fits.open(out) as hdul:
        for hdu in hdul:
            if hdu.data is not None and hdu.data.ndim >= 2:
                assert not WCS(hdu.header, hdul).has_celestial, "WCS not fully stripped"
    return out


def main(argv):
    src = Path(argv[1]) if len(argv) > 1 else DEFAULT_SRC
    out_dir = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT
    if not src.exists():
        print(f"source frame not found: {src}", file=sys.stderr)
        return 1
    out = make_raw_copy(src, out_dir)
    print(f"wrote raw (WCS-stripped) copy: {out}")
    print(
        "Upload it in the web app once a blind solver is installed "
        "(WSL astrometry.net or a nova API key)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
