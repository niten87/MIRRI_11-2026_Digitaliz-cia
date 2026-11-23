#!/usr/bin/env python3
"""Tests for the legislation freshness gate (NASTROJ-H3). Dependency-free."""
from __future__ import annotations

import datetime
import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("cg", _TOOL / "checks" / "check_legislation.py")
cg = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cg)

TODAY = datetime.date(2026, 7, 8)


def _run(yaml_text):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "legislation.yaml").write_text(yaml_text, encoding="utf-8")
        return cg.check_legislation(root, today=TODAY)


def ids(f):
    return {x.check_id for x in f}


def test_fresh_source_no_findings():
    f = _run('sources:\n  - id: "gber"\n    retrieved_at: "2026-07-01"\n')
    assert f == []


def test_stale_source_is_minor():
    f = _run('sources:\n  - id: "gber"\n    retrieved_at: "2026-01-01"\n')
    assert any(x.check_id == "legislation_stale" and x.severity == "minor" for x in f)


def test_unpinned_source_is_minor():
    f = _run('sources:\n  - id: "gber"\n    url: "https://x"\n')
    assert any(x.check_id == "legislation_unpinned" for x in f)


def test_expired_manual_doc_is_major():
    f = _run('manual_portals:\n  - id: "rt"\n    validity: "3 mesiace"\n    retrieved_at: "2026-01-01"\n')
    assert any(x.check_id == "manual_doc_expired" and x.severity == "major" for x in f)


def test_valid_manual_doc_ok():
    f = _run('manual_portals:\n  - id: "rt"\n    validity: "3 mesiace"\n    retrieved_at: "2026-06-01"\n')
    assert f == []


def test_absent_file_no_findings():
    with tempfile.TemporaryDirectory() as d:
        assert cg.check_legislation(Path(d), today=TODAY) == []


def test_custom_window_honored():
    f = _run('freshness_window_days: 400\nsources:\n  - id: "gber"\n    retrieved_at: "2026-01-01"\n')
    assert f == []  # 189 days < 400-day window


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
