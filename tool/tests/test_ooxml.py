#!/usr/bin/env python3
"""Tests for dependency-free XLSX/DOCX writers+reader (NASTROJ-B). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
_REPO = _TOOL.parent
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.xlsxio import write_xlsx, read_xlsx, read_xlsx_rows  # noqa: E402
from grantlib.docxio import write_docx  # noqa: E402

_spec = importlib.util.spec_from_file_location("bd", _TOOL / "checks" / "build_dossier.py")
bd = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(bd)

_cbspec = importlib.util.spec_from_file_location("cb", _TOOL / "checks" / "check_budget.py")
cb = importlib.util.module_from_spec(_cbspec)
assert _cbspec and _cbspec.loader
_cbspec.loader.exec_module(cb)


def test_xlsx_roundtrip_numbers_strings_empties():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.xlsx"
        write_xlsx(p, [("S1", [["a", "b", "c"], ["x", "", 12.5], ["", 3, "z"]])])
        data = read_xlsx(p)
    rows = data["S1"]
    assert rows[0] == ["a", "b", "c"]
    assert rows[1][0] == "x" and rows[1][1] == "" and rows[1][2] == "12.5"
    assert rows[2][1] == "3"


def test_xlsx_all_parts_wellformed_and_multisheet():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.xlsx"
        write_xlsx(p, [("Rozpočet", [["h"], [1]]), ("Indikátory", [["k"], ["v"]])])
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith(".xml"):
                    ET.fromstring(z.read(n))
        data = read_xlsx(p)
    assert list(data) == ["Rozpočet", "Indikátory"]


def test_xlsx_rows_csvio_compatible():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "r.xlsx"
        write_xlsx(p, [("S", [["wp", "cov"], ["3-1", 400000]])])
        header, rows = read_xlsx_rows(p)
    assert header == ["wp", "cov"]
    assert rows[0]["wp"] == "3-1" and rows[0]["cov"] == "400000"


def test_docx_valid_and_contains_content():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "o.docx"
        write_docx(p, [("h", "Nadpis"), ("p", "Odsek text"),
                       ("table", (["A", "B"], [["1", "2"]]))])
        with zipfile.ZipFile(p) as z:
            assert "word/document.xml" in z.namelist()
            doc = z.read("word/document.xml").decode("utf-8")
            ET.fromstring(doc)
    assert "Nadpis" in doc and "Odsek text" in doc and "<w:tbl>" in doc


def test_build_binary_from_demo():
    with tempfile.TemporaryDirectory() as d:
        docx = bd.build_opis_docx(_REPO / "examples" / "budget-demo", output=str(Path(d) / "opis.docx"))
        xlsx = bd.build_budget_xlsx(_REPO / "examples" / "budget-demo", output=str(Path(d) / "roz.xlsx"))
        with zipfile.ZipFile(docx) as z:
            assert "[ZIADATEL]" in z.read("word/document.xml").decode("utf-8")
        data = read_xlsx(xlsx)
    rows = data["Rozpočet 2c"]
    assert any(r and str(r[0]).startswith("PRACOVNÝ BALÍK") for r in rows)  # per-WP blocks
    spolu = [r for r in rows if r and str(r[0]).startswith("SPOLU -  oprávnené")][0]
    assert spolu[5] == "600000.0" and spolu[7] == "360000.0"


def test_check_budget_reads_xlsx_input():
    cols = ["wp", "nazov_vydavku", "kategoria", "merna_jednotka", "pocet_jednotiek",
            "jednotkova_cena", "celkove_opravnene", "intenzita", "narokovane", "vecny_popis"]
    rows = [cols,
            ["3-1", "Personál", "521", "os", 10, 40000, 400000, 0.6, 240000, ""],
            ["3-1", "Zmluvný", "518", "p", 1, 100000, 100000, 0.6, 60000, ""],
            ["3-1", "Paušál", "920", "p", 1, "", 100000, 0.6, 60000, ""]]
    cfg = {"file": "budget/rozpocet.xlsx", "min_cov": 300000, "max_cov": 2200000,
           "categories": {"A": ["521", "518", "920"]},
           "pausal": {"A": {"code": "920", "rate": 0.20, "base_codes": ["521", "518"]}}}
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_xlsx(root / "budget" / "rozpocet.xlsx", [("Rozpočet", rows)])
        findings = cb.check_budget(cfg, root, regime="A")
    assert findings == []  # a valid .xlsx budget checks the same as a CSV one


def test_budget_2c_per_wp_subtotals_sum_to_total():
    import tempfile
    app = _REPO / "applications" / "17I04-04-V05-RIS3-predictai"
    with tempfile.TemporaryDirectory() as d:
        xlsx = bd.build_budget_xlsx(app, output=str(Path(d) / "r.xlsx"))
        rows = read_xlsx(xlsx)["Rozpočet 2c"]
    subs = [float(r[5]) for r in rows if r and str(r[0]).startswith("SPOLU - pracovný balík")]
    grand = [float(r[5]) for r in rows if r and str(r[0]).startswith("SPOLU -  oprávnené")][0]
    assert subs, "no per-WP subtotals"
    assert abs(sum(subs) - grand) < 0.02          # per-WP subtotals (incl. paušál) sum to grand total
    assert any(r and str(r[0]).startswith("Paušálna sadzba") for r in rows)  # paušál per WP present


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
