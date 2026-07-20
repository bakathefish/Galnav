"""Enforces THE TRUTH WALL: galnav/nav/ must never import from galnav/truth/.

Never edit this file to make code pass.
"""

import ast
from pathlib import Path

NAV_DIR = Path(__file__).resolve().parent.parent / "galnav" / "nav"


def imported_names(py_file):
    """Return every module name that one .py file imports (list of str)."""
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
                # "from .. import truth" style: the imported names ARE modules
                for alias in node.names:
                    names.append(alias.name)
    return names


def test_nav_never_imports_truth():
    offenders = []
    for py_file in sorted(NAV_DIR.rglob("*.py")):
        if any("truth" in name for name in imported_names(py_file)):
            offenders.append(str(py_file))
    assert not offenders, f"TRUTH WALL BREACH: {offenders}"
