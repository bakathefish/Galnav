"""NAV SIDE: the public star catalog as the NAVIGATOR holds it — positions
AND their quoted uncertainties. Never imports galnav/truth/. Both sides read
the same public CSV: that is catalog DATA (what a real spacecraft carries),
not truth state; the wall forbids truth imports and truth-derived inputs,
not shared public inputs."""

import numpy as np

from galnav.units import deg_to_rad, parallax_mas_to_dist_au, radec_to_unit


def load_catalog(csv_path):
    """Read the public Gaia DR3 subset the way the navigator uses it.

    csv_path: path to data/gaia_dr3_nav_subset.csv.
    Returns: dict with
        star_pos_au: (N, 3) catalog star positions, au (BCRS/ICRS, J2016.0),
                     nearest star first;
        sigma_dist_au: (N,) 1-sigma catalog distance error per star, au —
                     first-order parallax propagation: d = 1/pi gives
                     sigma_d = (sigma_pi / pi) * d.
    """
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    dist_au = parallax_mas_to_dist_au(data["parallax"])
    unit = radec_to_unit(deg_to_rad(data["ra"]), deg_to_rad(data["dec"]))
    return {
        "star_pos_au": unit * dist_au[:, None],
        "sigma_dist_au": (data["parallax_error"] / data["parallax"]) * dist_au,
    }
