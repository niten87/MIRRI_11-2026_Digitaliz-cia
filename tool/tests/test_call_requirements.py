#!/usr/bin/env python3
"""Tests for the grant call-requirements checker (v1 compat + v2 schema).

Dependency-free: run directly (`python3 tool/tests/test_call_requirements.py`)
or via pytest. Each test is a plain function with asserts.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
_REPO = _TOOL.parent
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib import schema as S  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402

_spec = importlib.util.spec_from_file_location("ccr", _TOOL / "checks" / "check_call_requirements.py")
ccr = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(ccr)


def test_v1_template_valid_under_v2_schema():
    data = load_yaml(_REPO / "templates" / "call-requirements-template.yaml")
    assert S.validate(data, ccr.CALL_REQUIREMENTS_SCHEMA) == []


def test_v2_template_valid():
    data = load_yaml(_REPO / "templates" / "call-requirements-v2-template.yaml")
    assert S.validate(data, ccr.CALL_REQUIREMENTS_SCHEMA) == []


def test_unknown_top_level_key_is_blocker():
    reqs = {"version": 2, "budgett": {}}
    with tempfile.TemporaryDirectory() as d:
        findings = ccr.check_call_requirements(reqs, Path(d))
    assert any(f.check_id == "invalid_requirements_schema" and f.severity == "blocker" for f in findings)


def test_conditional_annex_is_not_a_blocker():
    reqs = {
        "version": 2,
        "annexes": [{"id": "p5", "artifact": "annexes/p5.xlsx", "required_if": "komp9 == true"}],
    }
    with tempfile.TemporaryDirectory() as d:
        findings = ccr.check_call_requirements(reqs, Path(d))
    assert not any(f.check_id == "missing_required_annex" for f in findings)
    assert any(f.check_id == "conditional_annex_deferred" for f in findings)


def test_annex_wrong_format_is_major():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "annexes").mkdir()
        (root / "annexes" / "opis.pdf").write_text("x", encoding="utf-8")
        reqs = {"version": 2,
                "annexes": [{"id": "opis", "artifact": "annexes/opis.pdf", "required": True, "format": "docx"}]}
        findings = ccr.check_call_requirements(reqs, root)
    assert any(f.check_id == "annex_wrong_format" and f.severity == "major" for f in findings)


def test_missing_required_section_is_blocker():
    reqs = {"version": 2, "sections": [{"id": "ciele", "manuscript": "manuscript/ciele.md", "required": True}]}
    with tempfile.TemporaryDirectory() as d:
        findings = ccr.check_call_requirements(reqs, Path(d))
    assert any(f.check_id == "missing_required_section" and f.severity == "blocker" for f in findings)


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
