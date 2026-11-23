#!/usr/bin/env python3
"""Tests for the cross-document consistency checker (NASTROJ-C4). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.csvio import write_csv  # noqa: E402

_spec = importlib.util.spec_from_file_location("cx", _TOOL / "checks" / "check_cross_document_consistency.py")
cx = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cx)

COLS = ["wp", "nazov_vydavku", "kategoria", "merna_jednotka", "pocet_jednotiek",
        "jednotkova_cena", "celkove_opravnene", "intenzita", "narokovane", "vecny_popis"]
# total_cov = 600000, sum_narokovane = 360000
ROWS = [
    {"wp": "3-1", "nazov_vydavku": "a", "kategoria": "521", "merna_jednotka": "os",
     "pocet_jednotiek": "1", "jednotkova_cena": "600000", "celkove_opravnene": "600000",
     "intenzita": "0.6", "narokovane": "360000", "vecny_popis": ""},
]
STD = [
    {"id": "cov", "left": "financovanie.celkove_opravnene", "right": "budget.total_cov", "op": "eq", "severity": "blocker"},
    {"id": "ppm", "left": "financovanie.ziadana_ppm", "right": "budget.sum_narokovane", "op": "eq", "severity": "blocker"},
    {"id": "spolu", "expr": "financovanie.spolufinancovanie == budget.total_cov - budget.sum_narokovane"},
    {"id": "trl", "expr": "6 <= project.trl_end <= 8"},
]


def _run(consistency, cov=600000, ppm=360000, spolu=240000, trl_end=7):
    reqs = {"version": 2, "budget": {"file": "budget/rozpocet.csv"}, "consistency": consistency}
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_csv(root / "budget" / "rozpocet.csv", COLS, ROWS)
        (root / "project.yaml").write_text(
            f"project:\n  regime: \"A\"\n  miesto_realizacie: \"Košice\"\n  trl_end: {trl_end}\n"
            f"financovanie:\n  celkove_opravnene: {cov}\n  ziadana_ppm: {ppm}\n  spolufinancovanie: {spolu}\n",
            encoding="utf-8")
        return cx.check_cross_document_consistency(reqs, root)


def ids(f):
    return {x.check_id for x in f}


def test_all_consistent_no_findings():
    assert cx and _run(STD) == []


def test_cov_mismatch_is_blocker():
    f = _run(STD, cov=500000)
    assert any(x.check_id == "consistency_failed:cov" and x.severity == "blocker" for x in f)


def test_spolufinancovanie_expr_mismatch_is_major():
    f = _run(STD, spolu=999)
    assert any(x.check_id == "consistency_failed:spolu" and x.severity == "major" for x in f)


def test_trl_out_of_range_fails():
    f = _run(STD, trl_end=3)
    assert any(x.check_id == "consistency_failed:trl" for x in f)


def test_missing_data_is_skipped_not_failed():
    f = _run([{"id": "komp9", "left": "priloha5.komp9_personal", "right": "project.personnel", "op": "eq"}])
    assert any(x.check_id == "consistency_skipped_missing_data" for x in f)
    assert not any(x.severity in ("major", "blocker") for x in f)


def test_bad_expression_is_minor():
    f = _run([{"id": "evil", "expr": "__import__('os').system('echo hi')"}])
    assert any(x.check_id == "consistency_bad_expression" and x.severity == "minor" for x in f)


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
