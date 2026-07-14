"""Marks tests/ as a package so `from tests.golden_numbers import ...` always
finds OUR file — a stray `tests` package in site-packages shadows the name
otherwise (see journal/logbook.md, 2026-07-14)."""
