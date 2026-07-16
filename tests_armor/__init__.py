"""Armor-tier acceptance tests (Spec 9, E4).

These run ONLY inside the WSL2 longdouble environment described in
journal/environment-armor.md, never on native Windows -- PINT's
precision-critical paths require an 80-bit extended-precision long double
(np.longdouble eps ~1.08e-19) that native Windows/MSVC cannot provide. The
spine suite lives in tests/ and stays zero-skip green on Windows; this suite
is deliberately a SEPARATE root so the two never have to skip each other.

Run: /opt/galnav/venv/bin/python -m pytest tests_armor -q   (inside WSL)
"""
