"""OpenSpace export: a GalNav fix (barycentric ICRS, au) -> OpenSpace .asset.

OpenSpace's scene graph lives in GALACTIC-frame METRES with solar-system
objects parented to SolarSystemBarycenter (OpenSpace source:
modules/skybrowser/src/utility.cpp ConversionMatrix; scene root is galactic).
So the exporter owns exactly two conversions -- rotate ICRS->galactic and
scale au->metres -- plus the Lua text itself. The rotation is verified here
against astropy's own frame machinery (an independent implementation), the
scale against the repo's single-owner constant in galnav.units, and the Lua
against structural invariants (balanced braces, the identifiers OpenSpace
needs, truth marker + miss line only when a truth vector is supplied).
"""

import numpy as np
import pytest

from galnav.units import AU_KM
from gui.openspace_export import (
    AU_M,
    asset_text,
    icrs_au_to_galactic_m,
    main,
)


# ---------------------------------------------------------------- conversions
def test_au_m_reuses_repo_constant():
    """One owner for the au: the exporter's metre constant must be derived
    from galnav.units.AU_KM, not a second hand-typed value."""
    assert AU_M == AU_KM * 1000.0


def test_rotation_matches_astropy():
    """The hardcoded ICRS->galactic matrix must agree with astropy's
    independently implemented frame transform on random vectors.

    Tolerance 5e-7 is MEASURED, not wished: the Hipparcos/OpenSpace matrix
    and astropy's galactic frame (which chains through FK4 B1950) are two
    slightly different frame DEFINITIONS that disagree by at most 1.19e-7
    relative = 0.025 arcsec (worst of 50 random directions, this box).
    That is ~800 km at New Horizons range -- 1/10,000 of the marker sphere
    -- irrelevant for a planetarium display; the test exists to catch a
    transposed/wrong matrix (any axis mixup errs at O(1), 7 orders away)."""
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    rng = np.random.default_rng(42)
    for _ in range(10):
        v = rng.normal(size=3)
        v /= np.linalg.norm(v)
        ours = icrs_au_to_galactic_m(v)
        sky = SkyCoord(
            x=v[0],
            y=v[1],
            z=v[2],
            unit=u.au,
            frame="icrs",
            representation_type="cartesian",
        ).galactic.cartesian
        theirs = np.array(
            [sky.x.to_value(u.m), sky.y.to_value(u.m), sky.z.to_value(u.m)]
        )
        # Per-component delta relative to the VECTOR norm (a near-zero
        # component would fail any per-element rtol at machine noise).
        delta = np.max(np.abs(ours - theirs)) / np.linalg.norm(theirs)
        assert delta < 5e-7, (delta, ours, theirs)


def test_rotation_is_pure_rotation():
    """No scale, no translation: |out| == |in| * AU_M exactly (to fp)."""
    v = np.array([13.5495, -42.0195, -16.4573])  # NH-scale vector, au
    out = icrs_au_to_galactic_m(v)
    assert np.isclose(np.linalg.norm(out), np.linalg.norm(v) * AU_M, rtol=1e-14)


# ----------------------------------------------------------------- asset text
RECOVERED = np.array([13.4, -41.8, -16.3])
TRUTH = np.array([13.5495, -42.0195, -16.4573])


def test_asset_recovered_only():
    text = asset_text(RECOVERED, label="GalNav fix")
    assert "SolarSystemBarycenter" in text
    assert "StaticTranslation" in text
    assert "GalNavFix" in text  # sanitized identifier
    assert "GalNav fix" in text  # human label survives
    assert "GalNavTruth" not in text  # no truth marker unless asked
    assert "RenderableNodeLine" not in text
    assert text.count("{") == text.count("}")  # Lua braces balanced


def test_asset_with_truth_adds_marker_and_miss_line():
    text = asset_text(
        RECOVERED, label="GalNav fix", truth_au=TRUTH, truth_label="JPL truth"
    )
    assert "GalNavTruth" in text
    assert "JPL truth" in text
    assert "RenderableNodeLine" in text  # the miss made visible
    assert text.count("{") == text.count("}")


def test_asset_positions_are_galactic_metres():
    """The numbers in the Lua must be the galactic-metre conversion of the
    input, not raw ICRS au (the classic wrong-frame bug)."""
    text = asset_text(RECOVERED, label="x")
    gal = icrs_au_to_galactic_m(RECOVERED)
    for comp in gal:
        assert f"{comp:.6e}" in text
    # raw au values must NOT appear as positions
    assert "13.4," not in text


# ------------------------------------------------------------------------ CLI
def test_cli_writes_asset_file(tmp_path):
    out = tmp_path / "galnav_fix.asset"
    main(
        [
            "--x",
            "13.4",
            "--y",
            "-41.8",
            "--z",
            "-16.3",
            "--label",
            "GalNav fix",
            "--truth-x",
            "13.5495",
            "--truth-y",
            "-42.0195",
            "--truth-z",
            "-16.4573",
            "--out",
            str(out),
        ]
    )
    text = out.read_text(encoding="utf-8")
    assert "GalNavFix" in text and "GalNavTruth" in text
