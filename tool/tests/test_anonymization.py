#!/usr/bin/env python3
"""Tests for the anonymization leak-scan (NASTROJ-C5). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("cl", _TOOL / "checks" / "check_anonymization_leaks.py")
cl = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cl)


def _scan(text, denylist=None):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "manuscript").mkdir()
        (root / "manuscript" / "10.md").write_text(text, encoding="utf-8")
        return cl.check_anonymization_leaks(root, targets=["manuscript"], denylist=denylist)


def ids(f):
    return {x.check_id for x in f}


def test_clean_placeholders_no_leak():
    f = _scan("Žiadateľ [ZIADATEL] (IČO [ICO]) rieši projekt; vedúci [OSOBA_1] a [OSOBA_2].")
    assert f == []


def test_email_is_blocker():
    f = _scan("Kontakt: jan.novak@firma.sk")
    assert any(x.check_id == "unanonymized_pii" and x.severity == "blocker" for x in f)


def test_iban_is_blocker():
    f = _scan("IBAN: SK8900000000000000000012")
    assert any(x.check_id == "unanonymized_pii" for x in f)


def test_phone_is_blocker():
    f = _scan("Tel: +421 900 123 456")
    assert any(x.check_id == "unanonymized_pii" for x in f)


def test_denylist_literal_is_company_leak():
    f = _scan("Projekt realizuje Tajná Firma s.r.o. v spolupráci.", denylist=["Tajná Firma s.r.o."])
    assert any(x.check_id == "company_identifier_leak" and x.severity == "blocker" for x in f)


def test_placeholder_not_flagged_as_leak():
    f = _scan("Osoby [OSOBA_1], [OSOBA_2], [STATUTAR]; firma [ZIADATEL].")
    assert not any(x.check_id == "company_identifier_leak" for x in f)
    assert f == []


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
