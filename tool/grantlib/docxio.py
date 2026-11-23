"""Dependency-free DOCX (OOXML WordprocessingML) writer (NASTROJ-B/D4).

`write_docx(path, blocks)` produces a minimal but valid .docx that Word and
LibreOffice open. Blocks are simple tuples:
    ("h", text)            -> bold heading paragraph
    ("p", text)            -> normal paragraph
    ("table", (headers, rows))  -> bordered table (headers bold)
Only the standard library is used.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)


def _run(text: str, *, bold: bool = False) -> str:
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _para(text: str, *, bold: bool = False) -> str:
    return f"<w:p>{_run(text, bold=bold)}</w:p>"


def _cell(text: str, *, bold: bool = False) -> str:
    return f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>{_para(text, bold=bold)}</w:tc>'


def _table(headers: list[Any], rows: list[list[Any]]) -> str:
    border = ('<w:tblBorders>'
              + "".join(f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
                        for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
              + "</w:tblBorders>")
    tpr = f'<w:tblPr><w:tblW w:w="0" w:type="auto"/>{border}</w:tblPr>'
    trs = ["<w:tr>" + "".join(_cell(h, bold=True) for h in headers) + "</w:tr>"]
    for row in rows:
        trs.append("<w:tr>" + "".join(_cell(c) for c in row) + "</w:tr>")
    return f"<w:tbl>{tpr}{''.join(trs)}</w:tbl>"


def write_docx(path: str | Path, blocks: list[tuple[str, Any]]) -> None:
    body_parts: list[str] = []
    for kind, payload in blocks:
        if kind == "h":
            body_parts.append(_para(payload, bold=True))
        elif kind == "p":
            body_parts.append(_para(payload))
        elif kind == "table":
            headers, rows = payload
            body_parts.append(_table(headers, rows))
            body_parts.append(_para(""))  # spacer
    body = "".join(body_parts) + '<w:sectPr/>'
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>')

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("word/document.xml", document)
