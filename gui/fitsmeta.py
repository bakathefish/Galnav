"""Tiny FITS metadata helpers: pull the observation time out of a header and
turn it into a catalog age. Kept separate from platesolve.py so the WCS code
stays focused.

The catalog epoch is Gaia DR3's J2016.0 = JD 2457388.5 (TDB). New Horizons
LORRI frames carry their UTC in SPCUTCAL, not the standard DATE-OBS, so we try
several keys in order.
"""

from astropy.io import fits
from astropy.time import Time

JD_J2016 = 2457388.5  # Gaia DR3 reference epoch 2016.0 (TDB), matches E3
JULIAN_YEAR_DAYS = 365.25

# Header keys that may carry the observation UTC, most-standard first. LORRI
# "pwcs2" frames use SPCUTCAL; generic images use DATE-OBS.
_TIME_KEYS = ("DATE-OBS", "SPCUTCAL", "DATE", "DATE_OBS")


def header_observation_jd(header):
    """Observation time (JD, TDB) from a FITS header, or None if absent.

    header: an astropy.io.fits Header.
    Returns: float Julian Date in the TDB scale, or None if no recognised time
        key is present/parseable.
    """
    for key in _TIME_KEYS:
        val = header.get(key)
        if not val:
            continue
        s = str(val).strip()
        try:
            return float(Time(s, scale="utc").tdb.jd)
        except (ValueError, TypeError):
            pass
        # Digitised sky-survey plates (POSS/DSS) sometimes carry a nonstandard
        # time field -- e.g. decimal minutes "06:75" in a 1950 Barnard header --
        # that astropy rejects, but the DATE is still good. Retry with the date
        # part alone (before 'T' or a space) so the observation year survives.
        date_part = s.split("T")[0].split()[0]
        if date_part and date_part != s:
            try:
                return float(Time(date_part, scale="utc").tdb.jd)
            except (ValueError, TypeError):
                pass
    return None


def observation_jd(path):
    """Observation time (JD, TDB) from a FITS file, or None.

    path: path to a FITS image. Non-FITS files (PNG/JPG) or files without a
        time key return None.
    Returns: float JD (TDB) or None.
    """
    try:
        with fits.open(path) as hdul:
            for hdu in hdul:
                jd = header_observation_jd(hdu.header)
                if jd is not None:
                    return jd
    except (OSError, ValueError):
        return None
    return None


def age_yr_since_j2016(jd):
    """Catalog age (Julian years since J2016.0) from a JD.

    jd: Julian Date (TDB).
    Returns: age in Julian years (jd - JD_J2016) / 365.25.
    """
    return (jd - JD_J2016) / JULIAN_YEAR_DAYS
