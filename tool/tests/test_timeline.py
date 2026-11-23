#!/usr/bin/env python3
"""Tests for the time-eligibility checker (NASTROJ-C8)."""
from __future__ import annotations
import importlib.util, sys, tempfile
from pathlib import Path
_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path: sys.path.insert(0, str(_TOOL))
_spec = importlib.util.spec_from_file_location("ct", _TOOL / "checks" / "check_timeline.py")
ct = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ct)

REQS = {"call": {"deadline": "2025-10-03", "realization_deadline": "2026-06-30"}}

def _run(zaciatok, koniec):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "project.yaml").write_text(
            f"work_packages:\n  - id: \"3-1\"\n    aktivity:\n      - por: 1\n        nazov: \"A1\"\n"
            f"        zaciatok: \"{zaciatok}\"\n        koniec: \"{koniec}\"\n", encoding="utf-8")
        return ct.check_timeline(REQS, root)

def test_within_window_passes():
    assert _run("2025-11-01", "2026-06-30") == []

def test_before_submission_is_major():
    f = _run("2025-09-01", "2026-06-30")
    assert any(x.check_id == "activity_before_submission" and x.severity == "major" for x in f)

def test_after_realization_is_major():
    f = _run("2025-11-01", "2026-08-31")
    assert any(x.check_id == "activity_after_realization" for x in f)

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try: t(); print(f"PASS {t.__name__}")
        except AssertionError as e: failed += 1; print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passed"); raise SystemExit(1 if failed else 0)
