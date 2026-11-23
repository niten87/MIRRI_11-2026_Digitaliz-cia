#!/usr/bin/env python3
"""Tests for the indicators checker (NASTROJ-C3). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.csvio import write_csv  # noqa: E402

_spec = importlib.util.spec_from_file_location("cin", _TOOL / "checks" / "check_indicators.py")
cin = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cin)

COLS = ["nazov", "definicia", "merna_jednotka", "vychodiskova_hodnota", "planovana_hodnota", "typ"]
CFG = {"file": "indicators/indicators.csv", "min_main": 1, "max_main": 3, "min_secondary": 1,
       "max_secondary": 3, "max_total": 6, "require_dissemination_secondary": True}


def ind(nazov, defin, typ):
    return {"nazov": nazov, "definicia": defin, "merna_jednotka": "počet",
            "vychodiskova_hodnota": "0", "planovana_hodnota": "2", "typ": typ}


VALID = [
    ind("Počet výskumníkov", "FTE na projekte", "hlavny"),
    ind("Patentové prihlášky", "Podané počas projektu", "hlavny"),
    ind("Publikácie", "Diseminácia výsledkov", "vedlajsi"),
]


def _run(rows, cfg=CFG):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_csv(root / "indicators" / "indicators.csv", COLS, rows)
        return cin.check_indicators(cfg, root)


def ids(f):
    return {x.check_id for x in f}


def test_valid_indicators_no_major():
    assert not any(x.severity in ("major", "blocker") for x in _run(VALID))


def test_no_main_is_missing_main():
    rows = [ind("Publikácie", "Diseminácia", "vedlajsi")]
    assert "missing_main" in ids(_run(rows))


def test_no_dissemination_secondary():
    rows = [ind("Výskumníci", "FTE", "hlavny"), ind("Prototyp", "Funkčný prototyp", "vedlajsi")]
    assert "missing_dissemination_secondary" in ids(_run(rows))


def test_too_many_total_out_of_range():
    rows = VALID + [ind(f"X{i}", "Diseminácia", "vedlajsi") for i in range(5)]
    assert "indicators_count_out_of_range" in ids(_run(rows))


def test_empty_field_is_minor():
    bad = dict(VALID[0], planovana_hodnota="")
    f = _run([bad, VALID[1], VALID[2]])
    assert any(x.check_id == "indicator_field_missing" and x.severity == "minor" for x in f)


def test_missing_file_is_major():
    with tempfile.TemporaryDirectory() as d:
        f = cin.check_indicators(CFG, Path(d))
    assert any(x.check_id == "indicators_file_missing" for x in f)


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
