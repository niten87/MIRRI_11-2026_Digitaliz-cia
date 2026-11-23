#!/usr/bin/env python3
"""Tests for new-call / new-application scaffolding. Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("sc", _TOOL / "checks" / "scaffold.py")
sc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(sc)


def test_new_call_creates_skeleton():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        made, skipped = sc.new_call("Q-42", repo_root=root)
    rels = {m.replace(str(root) + "/", "") for m in made}
    assert "templates/opis/Q-42/opis-2b.md" in rels
    assert "templates/opis/Q-42/required-structure.yaml" in rels
    assert "templates/annexes/Q-42/annexes.yaml" in rels
    assert "calls/Q-42/SEMANTIC-MAP.md" in rels


def test_new_application_creates_skeleton_and_wires_call_number():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sc.new_application("Q-42", "acme", repo_root=root)
        app = root / "applications" / "Q-42-acme"
        assert (app / "project.yaml").is_file()
        assert (app / "budget" / "rozpocet.csv").is_file()
        assert len(list((app / "manuscript").glob("*.md"))) == 8
        cr = (app / "call-requirements.yaml").read_text(encoding="utf-8")
    assert 'number: "Q-42"' in cr  # call number wired into the copied template


def test_scaffold_never_overwrites():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sc.new_call("Q-42", repo_root=root)
        made2, skipped2 = sc.new_call("Q-42", repo_root=root)  # second run
    assert made2 == [] and skipped2, "second run should skip existing files, not overwrite"


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
