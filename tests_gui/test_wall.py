"""Holds gui/ to THE TRUTH WALL. The repo's tests/test_truth_wall.py guards
only galnav/nav; the demo GUI is also a navigator-side consumer, so this test
(a copy of that AST style, NOT an edit of it) asserts no module under gui/ ever
imports galnav.truth. It also confirms gui only imports the allowed navigator
surface.
"""

import ast
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent.parent / "gui"

# The only galnav modules the GUI is permitted to import (navigator side).
ALLOWED_GALNAV_PREFIXES = (
    "galnav.nav",
    "galnav.units",
    "galnav.geometry",
    "galnav.parallax",
)


def _imported_names(py_file):
    """Every module name a .py file imports (same logic as tests/test_truth_wall)."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names.append(node.module)
            else:
                for alias in node.names:
                    names.append(alias.name)
    return names


def test_gui_never_imports_truth():
    """Any galnav.truth import from gui/ is a wall breach -- the GUI must see
    only measurements + public catalog, exactly like a real spacecraft."""
    offenders = []
    for py_file in sorted(GUI_DIR.rglob("*.py")):
        if any("truth" in name for name in _imported_names(py_file)):
            offenders.append(str(py_file))
    assert not offenders, f"TRUTH WALL BREACH in gui/: {offenders}"


def test_gui_only_imports_allowed_galnav_modules():
    """gui/ may reach into galnav only through the navigator surface; a stray
    galnav.truth or galnav.estimator import would be caught here too."""
    offenders = []
    for py_file in sorted(GUI_DIR.rglob("*.py")):
        for name in _imported_names(py_file):
            if name.startswith("galnav") and not name.startswith(
                ALLOWED_GALNAV_PREFIXES
            ):
                offenders.append(f"{py_file.name}: {name}")
    assert not offenders, f"gui/ imports a non-navigator galnav module: {offenders}"
