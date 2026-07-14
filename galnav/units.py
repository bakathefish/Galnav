"""All unit and frame conversions live here — nowhere else.

Internal units everywhere in GalNav: au (distance), km/s (velocity),
radians (angles). arcsec and mas appear only at I/O edges, and only via
functions in this module. Frames: BCRS/ICRS, catalog epoch J2016.0,
times in TDB.
"""

import numpy as np

# IAU definitions, derived (not typed in as decimals): 1 arcsec is
# pi/648000 radians, and 1 parsec is the distance where 1 au subtends
# 1 arcsec, hence exactly 648000/pi au.
AU_PER_PC = 648000.0 / np.pi


def deg_to_rad(deg):
    """Degrees to radians (catalog I/O edge).

    deg: angle in degrees (scalar or array).
    Returns: angle in radians.
    """
    return np.deg2rad(deg)


def radec_to_unit(ra_rad, dec_rad):
    """ICRS sky coordinates to 3D unit direction vector(s).

    ra_rad: right ascension in radians (scalar or array).
    dec_rad: declination in radians (scalar or array).
    Returns: unit vector(s), shape (..., 3), dimensionless.
    """
    cos_dec = np.cos(dec_rad)
    return np.stack(
        [cos_dec * np.cos(ra_rad), cos_dec * np.sin(ra_rad), np.sin(dec_rad)],
        axis=-1,
    )


def parallax_mas_to_dist_au(parallax_mas):
    """Distance from parallax.

    parallax_mas: parallax in milliarcseconds (scalar or array).
    Returns: distance in au (d_pc = 1000/parallax_mas, then pc -> au).
    """
    return (1000.0 / np.asarray(parallax_mas, dtype=float)) * AU_PER_PC
