"""Offline, deterministic test suite for the gui/ demo package. Runs from the
repo root (`python -m pytest tests_gui -q`); the repo-root conftest.py puts the
repo root on sys.path. Kept out of the default `pytest` gate (pytest.ini
testpaths = tests), mirroring tests_armor/.
"""
