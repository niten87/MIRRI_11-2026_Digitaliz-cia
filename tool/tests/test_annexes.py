#!/usr/bin/env python3
"""Tests for the annex builder (token fill + context). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.csvio import write_csv  # noqa: E402

_spec = importlib.util.spec_from_file_location("ba", _TOOL / "checks" / "build_annexes.py")
ba = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(ba)

BCOLS = ["wp", "nazov_vydavku", "kategoria", "merna_jednotka", "pocet_jednotiek",
         "jednotkova_cena", "celkove_opravnene", "intenzita", "narokovane", "vecny_popis"]


def _project(d: Path):
    (d / "call-requirements.yaml").write_text(
        "version: 2\ncall:\n  name: \"Test\"\n  number: \"17I04-04-V05\"\nbudget:\n  file: \"budget/rozpocet.csv\"\n",
        encoding="utf-8")
    (d / "project.yaml").write_text(
        "project:\n  nazov: \"PredictAI\"\n  skratka: \"PAI\"\n  prioritne_domeny: [\"3-1\", \"3-2\"]\n"
        "applicant:\n  nazov: \"[ZIADATEL]\"\n  ico: \"[ICO]\"\n"
        "financovanie:\n  celkove_opravnene: 2086000\n  ziadana_ppm: 1251600\n  spolufinancovanie: 834400\n"
        "work_packages:\n  - id: \"3-1\"\n    aktivity:\n      - por: 1\n        nazov: \"A1\"\n        vystup: \"O1\"\n"
        "        zaciatok: \"2025-11-01\"\n        koniec: \"2026-06-30\"\n",
        encoding="utf-8")
    write_csv(d / "budget" / "rozpocet.csv", BCOLS,
              [{"wp": "3-1", "nazov_vydavku": "Personál", "kategoria": "521", "merna_jednotka": "m",
                "pocet_jednotiek": "1", "jednotkova_cena": "2086000", "celkove_opravnene": "2086000",
                "intenzita": "0.6", "narokovane": "1251600", "vecny_popis": ""}])


def test_fill_template_substitutes_and_reports_missing():
    text = "Firma {{applicant.nazov}} — COV {{financovanie.celkove_opravnene}}. Chýba {{neexistuje.x}}."
    filled, missing = ba.fill_template(text, {"applicant.nazov": "[ZIADATEL]",
                                              "financovanie.celkove_opravnene": "2 086 000,00 €"})
    assert "[ZIADATEL]" in filled and "2 086 000,00 €" in filled
    assert "{{neexistuje.x}}" in filled  # unknown token left intact
    assert missing == ["neexistuje.x"]


def test_build_context_core_tokens():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _project(root)
        ctx = ba.build_context(root)
    assert ctx["applicant.nazov"] == "[ZIADATEL]"
    assert ctx["project.nazov"] == "PredictAI"
    assert ctx["project.domeny"] == "3-1, 3-2"
    assert ctx["financovanie.celkove_opravnene"] == "2 086 000,00 €"
    assert ctx["project.obdobie"] == "2025-11-01 – 2026-06-30"
    assert "| WP |" in ctx["tables.rozpocet"] and "Personál" in ctx["tables.rozpocet"]


def test_missing_identity_defaults_to_placeholder():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _project(root)
        ctx = ba.build_context(root)
    # applicant.statutar not set in project.yaml → placeholder
    assert ctx["applicant.statutar"] == "[STATUTAR]"
    assert ctx["applicant.iban"] == "[IBAN]"


_PREDICTAI = _TOOL.parent / "applications" / "17I04-04-V05-RIS3-predictai"


def test_context_2b_tokens_present():
    ctx = ba.build_context(_PREDICTAI)
    for key in ("tables.identifikacia_ziadatel", "tables.intenzita", "tables.financny_prehlad",
                "tables.domeny_checklist", "tables.indikatory", "tables.milniky",
                "section.excelentnost", "aid.effective"):
        assert key in ctx and ctx[key], f"missing/empty token {key}"
    assert "60 %" in ctx["tables.intenzita"]           # 25+20+15 capped
    assert "☒ 3-1" in ctx["tables.domeny_checklist"]
    assert "Akceptačné kritérium" in ctx["tables.milniky"]


def test_build_opis_2b_full_structure():
    import tempfile as _t
    with _t.TemporaryDirectory() as d:
        out, missing = ba.build_opis(_PREDICTAI, output=str(Path(d) / "opis.docx"))
        md = (out.parent / "opis.md").read_text(encoding="utf-8")
        import zipfile as _z
        doc = _z.ZipFile(out).read("word/document.xml").decode()
    assert not missing, f"unfilled tokens: {missing}"
    assert doc.count("<w:tbl>") >= 10                   # full header + structured tables
    for marker in ("Identifikácia žiadateľa", "Intenzita pomoci", "Monitoring", "EXCELENTNOSŤ"):
        assert marker in md


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
