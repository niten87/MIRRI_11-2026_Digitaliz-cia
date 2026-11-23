#!/usr/bin/env python3
"""Tests for the dossier builder (NASTROJ-D4, markdown slice). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
_REPO = _TOOL.parent
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("bd", _TOOL / "checks" / "build_dossier.py")
bd = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(bd)


def test_build_demo_dossier_has_all_sections():
    text = bd.build_dossier(_REPO / "examples" / "budget-demo")
    assert "## Opis projektu" in text
    assert "## Rozpočet" in text
    assert "600 000.00" in text            # computed COV total
    assert "Spolufinancovanie:** 240 000.00" in text
    assert "## Merateľné ukazovatele" in text
    assert "[ZIADATEL]" in text            # placeholders preserved (not de-anonymized)


def test_build_minimal_project_no_crash():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "project.yaml").write_text("project:\n  nazov: \"Test\"\n", encoding="utf-8")
        text = bd.build_dossier(root)
    assert text.startswith("# Test")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
