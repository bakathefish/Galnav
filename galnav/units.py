"""All unit and frame conversions live here — nowhere else.

Internal units everywhere in GalNav: au (distance), km/s (velocity),
radians (angles). arcsec and mas appear only at I/O edges, and only via
functions in this module. Frames: BCRS/ICRS, catalog epoch J2016.0,
times in TDB.

Empty until its acceptance tests exist (the project rulebook: no code before tests).
"""
