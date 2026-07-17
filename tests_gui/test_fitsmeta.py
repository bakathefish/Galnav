"""gui.fitsmeta must recover the observation year even from digitised-plate
headers whose time field is nonstandard (e.g. decimal minutes '06:75' in a 1950
POSS header), so the truth line still shows for old-plate uploads.
"""

from astropy.io import fits
from astropy.time import Time

from gui.fitsmeta import header_observation_jd


def _year(jd):
    return Time(jd, format="jd", scale="tdb").decimalyear


def test_decimal_minute_dateobs_tolerated():
    """A DATE-OBS with an invalid decimal-minute time must fall back to the date
    part rather than yielding None -- the observation year is still recoverable."""
    h = fits.Header()
    h["DATE-OBS"] = "1950-05-24T06:75:00"  # '75' is not a valid minute
    jd = header_observation_jd(h)
    assert jd is not None
    assert abs(_year(jd) - 1950.39) < 0.05  # 1950-05-24 ~ 1950.39


def test_plain_date_and_full_datetime_still_parse():
    """The fallback must not regress the normal cases: a bare date and a full
    ISO datetime both parse to the right year."""
    h1 = fits.Header()
    h1["DATE-OBS"] = "1953-04-15"  # the real POSS-I Wolf 359 plate date
    jd1 = header_observation_jd(h1)
    assert jd1 is not None and abs(_year(jd1) - 1953.29) < 0.05

    h2 = fits.Header()
    h2["DATE-OBS"] = "2020-04-23T00:00:00"
    jd2 = header_observation_jd(h2)
    assert jd2 is not None and abs(_year(jd2) - 2020.31) < 0.05


def test_no_time_key_returns_none():
    """A header with no recognised time key returns None (not a crash)."""
    assert header_observation_jd(fits.Header()) is None
