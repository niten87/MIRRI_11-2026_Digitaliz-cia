"""Dependency-free XLSX (OOXML) writer and reader (NASTROJ-B).

`write_xlsx` produces a minimal but valid .xlsx (ZIP of XML parts) that Excel and
LibreOffice open; text cells use inlineStr, numbers are written as numeric cells.
`read_xlsx` reads such a workbook back (inlineStr + shared strings + numbers),
returning {sheet_name: [[cell, ...], ...]}. Only the standard library is used.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    "{sheet_overrides}"
    "</Types>"
)
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)
_SS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _cell_xml(col: int, row: int, value: Any) -> str:
    ref = f"{_col_letter(col)}{row}"
    if value is None or value == "":
        return f'<c r="{ref}"/>'
    if _is_number(value):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'


def _sheet_xml(rows: list[list[Any]]) -> str:
    body = []
    for ri, row in enumerate(rows, start=1):
        cells = "".join(_cell_xml(ci, ri, v) for ci, v in enumerate(row, start=1))
        body.append(f'<row r="{ri}">{cells}</row>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="{_SS}"><sheetData>{"".join(body)}</sheetData></worksheet>')


def write_xlsx(path: str | Path, sheets: list[tuple[str, list[list[Any]]]]) -> None:
    """Write sheets = [(sheet_name, rows), ...]; rows = list of list of cell values."""
    if not sheets:
        sheets = [("Sheet1", [])]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheets) + 1))
    sheets_xml = "".join(
        f'<sheet name="{escape(name)[:31]}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(sheets, start=1))
    workbook = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<workbook xmlns="{_SS}" xmlns:r="{_R}"><sheets>{sheets_xml}</sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join(f'<Relationship Id="rId{i}" Type="{_R}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                         for i in range(1, len(sheets) + 1))
               + "</Relationships>")

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES.format(sheet_overrides=sheet_overrides))
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        for i, (_, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))


# ---- reader ----
_CELL_RE = re.compile(r'<c\b([^>]*?)(?:/>|>(.*?)</c>)', re.DOTALL)
_ROW_RE = re.compile(r"<row\b[^>]*>(.*?)</row>", re.DOTALL)
_T_RE = re.compile(r"<t\b[^>]*>(.*?)</t>", re.DOTALL)
_V_RE = re.compile(r"<v>(.*?)</v>", re.DOTALL)
_REF_RE = re.compile(r'r="([A-Z]+)(\d+)"')
_TYPE_RE = re.compile(r't="([^"]+)"')


def _unescape(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def read_xlsx(path: str | Path) -> dict[str, list[list[str]]]:
    """Read an .xlsx into {sheet_name: [[cell_str, ...], ...]}."""
    with zipfile.ZipFile(Path(path)) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            ss = z.read("xl/sharedStrings.xml").decode("utf-8")
            shared = [_unescape("".join(_T_RE.findall(si))) for si in re.findall(r"<si>(.*?)</si>", ss, re.DOTALL)]
        wb = z.read("xl/workbook.xml").decode("utf-8")
        sheet_names = re.findall(r'<sheet [^>]*name="([^"]*)"[^>]*r:id="(rId\d+)"', wb)
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        rid_target = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))

        result: dict[str, list[list[str]]] = {}
        for idx, (name, rid) in enumerate(sheet_names, start=1):
            target = rid_target.get(rid, f"worksheets/sheet{idx}.xml")
            part = "xl/" + target.lstrip("/")
            if part not in names:
                continue
            xml = z.read(part).decode("utf-8")
            rows_out: list[list[str]] = []
            for row_xml in _ROW_RE.findall(xml):
                cells: dict[int, str] = {}
                for m in _CELL_RE.finditer(row_xml):
                    attrs = m.group(1) or ""
                    inner = m.group(2) or ""
                    ref = _REF_RE.search(attrs)
                    col = _col_index(ref.group(1)) if ref else len(cells) + 1
                    ctype = _TYPE_RE.search(attrs)
                    t = ctype.group(1) if ctype else None
                    if t == "inlineStr":
                        val = _unescape("".join(_T_RE.findall(inner)))
                    elif t == "s":
                        v = _V_RE.search(inner)
                        val = shared[int(v.group(1))] if v else ""
                    else:
                        v = _V_RE.search(inner)
                        val = v.group(1) if v else ""
                    cells[col] = val
                width = max(cells) if cells else 0
                rows_out.append([cells.get(c, "") for c in range(1, width + 1)])
            result[name] = rows_out
        return result


def read_xlsx_rows(path: str | Path, sheet: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
    """csvio-compatible: first row = header; returns (fieldnames, list of row dicts)."""
    data = read_xlsx(path)
    if not data:
        return [], []
    rows = data[sheet] if sheet and sheet in data else next(iter(data.values()))
    if not rows:
        return [], []
    header = [str(c) for c in rows[0]]
    out = []
    for r in rows[1:]:
        out.append({header[i]: (r[i] if i < len(r) else "") for i in range(len(header))})
    return header, out
