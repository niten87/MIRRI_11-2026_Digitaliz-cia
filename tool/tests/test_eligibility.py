#!/usr/bin/env python3
"""Tests for the computed eligibility / MSP checker (NASTROJ-C6). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("ce", _TOOL / "checks" / "check_eligibility.py")
ce = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(ce)


def test_compute_micro():
    assert ce.compute_msp_size({"zamestnanci": 8, "obrat_eur": 1_000_000, "suvaha_eur": 900_000})[0] == "mikro"


def test_compute_small():
    assert ce.compute_msp_size({"zamestnanci": 8, "obrat_eur": 3_000_000, "suvaha_eur": 2_500_000})[0] == "maly"


def test_compute_medium():
    assert ce.compute_msp_size({"zamestnanci": 100, "obrat_eur": 30_000_000, "suvaha_eur": 20_000_000})[0] == "stredny"


def test_compute_large():
    assert ce.compute_msp_size({"zamestnanci": 300, "obrat_eur": 80_000_000, "suvaha_eur": 60_000_000})[0] == "velky"


def test_missing_headcount_incomputable():
    assert ce.compute_msp_size({"obrat_eur": 1_000_000})[0] is None


def _run(msp_yaml):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "project.yaml").write_text("applicant:\n  msp:\n" + msp_yaml, encoding="utf-8")
        return ce.check_eligibility({}, root)


def ids(f):
    return {x.check_id for x in f}


def test_declared_matches_computed_no_major():
    f = _run("    zamestnanci: 8\n    obrat_eur: 3000000\n    suvaha_eur: 2500000\n    size_category: \"maly\"\n")
    assert not any(x.severity in ("major", "blocker") for x in f)
    assert "msp_size_computed" in ids(f)


def test_declared_mismatch_is_major():
    f = _run("    zamestnanci: 8\n    obrat_eur: 1000000\n    suvaha_eur: 900000\n    size_category: \"maly\"\n")
    assert any(x.check_id == "msp_size_mismatch" and x.severity == "major" for x in f)


def test_large_is_not_eligible():
    f = _run("    zamestnanci: 300\n    obrat_eur: 80000000\n    suvaha_eur: 60000000\n")
    assert any(x.check_id == "eligibility_not_met" for x in f)


def _run_vav(sources_yaml: str, regime: str = "A"):
    import tempfile
    reqs = {"call": {"regime": regime},
            "eligibility": [{"id": "vav", "computed": "check_eligibility.py::vav"}]}
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "project.yaml").write_text(
            "applicant:\n  msp:\n    zamestnanci: 8\n    obrat_eur: 3000000\n"
            "    suvaha_eur: 2500000\n    size_category: \"maly\"\n", encoding="utf-8")
        (root / "references").mkdir()
        (root / "references" / "source-registry.yaml").write_text(sources_yaml, encoding="utf-8")
        return ce.check_eligibility(reqs, root)


_ONE = "sources:\n  - title: P1\n    year: 2024\n    domain: \"3-2\"\n"


def test_vav_sufficient_regime_a():
    f = _run_vav(_ONE)
    assert any(x.check_id == "vav_projekty_ok" for x in f)
    assert not any(x.severity in ("major", "blocker") for x in f)


def test_vav_insufficient_regime_b():
    # režim B potrebuje ≥2; 1 projekt → nedostatočné
    f = _run_vav(_ONE, regime="B")
    assert any(x.check_id == "vav_projekty_insufficient" and x.severity == "major" for x in f)


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
