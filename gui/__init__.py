"""GalNav demo GUI: upload spacecraft star-field images, plate-solve them,
identify nearby (<=20 pc) Gaia catalog stars in each frame, accumulate
line-of-position constraints across images, and report WHERE the spacecraft
is (position in au, error ellipsoid). The catalog AGE is handled both ways:
the user can SET the age (catalog is propagated forward before matching) and
the tool can ESTIMATE it from the image geometry (chi2 scan over age).

THE TRUTH WALL: this package is a NAVIGATOR-SIDE consumer. It imports only
stdlib, numpy, scipy, astropy, matplotlib, and the navigator half of the
project (galnav.nav.*, galnav.units, galnav.geometry, galnav.parallax). It
NEVER imports galnav.truth. The repo's tests/test_truth_wall.py only guards
galnav/nav; tests_gui/test_wall.py holds gui/ to the same standard by AST
inspection.

This is a DEMO layer above the finished spine, not spine science: it touches
zero golden numbers and adds zero new dependencies (tkinter and Pillow, via
matplotlib, are already present).
"""
