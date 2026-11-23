#!/usr/bin/env python3
"""Tests for the grant budget checker (NASTROJ-C1). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.csvio import write_csv  # noqa: E402

_spec = importlib.util.spec_from_file_location("cb", _TOOL / "checks" / "check_budget.py")
cb = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cb)

COLS = ["wp", "nazov_vydavku", "kategoria", "merna_jednotka", "pocet_jednotiek",
        "jednotkova_cena", "celkove_opravnene", "intenzita", "narokovane", "vecny_popis"]

CFG = {
    "file": "budget/rozpocet.csv",
    "min_cov": 300000, "max_cov": 2200000,
    "categories": {"A": ["521", "518", "920"]},
    "pausal": {"A": {"code": "920", "rate": 0.20, "base_codes": ["521", "518"]}},
}


def row(wp, name, kat, pocet, cena, cov):
    return {"wp": wp, "nazov_vydavku": name, "kategoria": kat, "merna_jednotka": "os",
            "pocet_jednotiek": pocet, "jednotkova_cena": cena, "celkove_opravnene": cov,
            "intenzita": "0.6", "narokovane": "", "vecny_popis": ""}


# base_sum = 500000; paušál 920 = 0.20*500000 = 100000; total = 600000 (within envelope)
VALID_ROWS = [
    row("3-1", "Personál", "521", "10", "40000", "400000"),
    row("3-1", "Zmluvný výskum", "518", "1", "100000", "100000"),
    row("3-1", "Paušál", "920", "1", "", "100000"),
]


def _run(rows, cfg=CFG):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_csv(root / "budget" / "rozpocet.csv", COLS, rows)
        return cb.check_budget(cfg, root, regime="A")


def ids(findings):
    return {f.check_id for f in findings}


def test_valid_budget_has_no_findings():
    assert _run(VALID_ROWS) == []


def test_row_arithmetic_mismatch_is_major():
    bad = [dict(VALID_ROWS[0], celkove_opravnene="399999"), VALID_ROWS[1], VALID_ROWS[2]]
    f = _run(bad)
    assert any(x.check_id == "budget_row_mismatch" and x.severity == "major" for x in f)


def test_category_not_allowed_is_blocker():
    bad = VALID_ROWS + [row("3-1", "Neznáme", "999", "1", "1000", "1000")]
    f = _run(bad)
    assert any(x.check_id == "category_not_allowed" and x.severity == "blocker" for x in f)


def test_pausal_wrong_is_major():
    bad = [VALID_ROWS[0], VALID_ROWS[1], dict(VALID_ROWS[2], celkove_opravnene="90000")]
    f = _run(bad)
    assert any(x.check_id == "pausal_wrong" and x.severity == "major" for x in f)


def test_below_envelope_is_blocker():
    small = [row("3-1", "Personál", "521", "1", "1000", "1000")]
    f = _run(small)
    assert any(x.check_id == "budget_out_of_envelope" and x.severity == "blocker" for x in f)


def test_missing_file_is_blocker():
    with tempfile.TemporaryDirectory() as d:
        f = cb.check_budget(CFG, Path(d), regime="A")
    assert any(x.check_id == "budget_file_missing" for x in f)


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
