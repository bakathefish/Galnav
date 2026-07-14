"""TRUTH SIDE: the true sky. Loads the cached Gaia catalog and places
every star at its true 3D position. The navigator never imports this."""

import numpy as np

from galnav.units import deg_to_rad, parallax_mas_to_dist_au, radec_to_unit


def load_catalog(csv_path):
    """Read the cached Gaia DR3 subset into plain arrays.

    csv_path: path to data/gaia_dr3_nav_subset.csv.
    Returns: dict with ra_rad (radians), dec_rad (radians), dist_au (au),
             one entry per star, nearest first.
    """
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    return {
        "ra_rad": deg_to_rad(data["ra"]),
        "dec_rad": deg_to_rad(data["dec"]),
        "dist_au": parallax_mas_to_dist_au(data["parallax"]),
    }


def star_positions_au(catalog):
    """True 3D star positions: unit direction times distance.

    catalog: dict from load_catalog (angles in radians, distances in au).
    Returns: (N, 3) array of BCRS/ICRS positions in au.
    """
    unit = radec_to_unit(catalog["ra_rad"], catalog["dec_rad"])
    return unit * catalog["dist_au"][:, None]
