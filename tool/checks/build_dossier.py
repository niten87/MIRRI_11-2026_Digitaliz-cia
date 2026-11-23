#!/usr/bin/env python3
"""Assemble a submission dossier from the model (NASTROJ-D4, markdown slice).

Renders a single reviewable Markdown document from the project model: the Opis
sections (manuscript/*.md), a budget table with computed totals, the measurable
indicators, and a financial + aid-intensity summary. Output goes to
`publication/dossier.md` (gitignored). DOCX/XLSX binary rendering is a follow-up;
this markdown build is the dependency-free first target and QC-visible artifact.

The dossier keeps anonymization placeholders — de-anonymization (restore from the
local key) happens only at finalization (NASTROJ-I2), never in a committed build.
"""
from __future__ import annotations

import argparse
import sys as _sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in _sys.path:
    _sys.path.append(str(_TOOL))
from grantlib.paths import resolve_project_path  # noqa: E402
from grantlib.csvio import read_csv_rows, read_rows  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402
from grantlib.docxio import write_docx  # noqa: E402
from grantlib.xlsxio import write_xlsx  # noqa: E402


def _to_float(cell: str) -> float:
    try:
        return float((cell or "").strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", " ")


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_dossier(project_root: Path) -> str:
    reqs = {}
    rp = resolve_project_path(project_root, "call-requirements.yaml")
    if rp.is_file():
        reqs = load_yaml(rp)
    proj = {}
    pp = resolve_project_path(project_root, "project.yaml")
    if pp.is_file():
        proj = load_yaml(pp)

    call = reqs.get("call") or {}
    project = proj.get("project") or {}
    title = project.get("nazov") or call.get("name") or "Grantová žiadosť"

    parts: list[str] = [f"# {title}", ""]
    if call.get("number"):
        parts.append(f"**Výzva:** {call.get('name', '')} (`{call['number']}`)  ")
    if call.get("deadline"):
        parts.append(f"**Termín podania:** {call['deadline']}  ")
    if project.get("skratka"):
        parts.append(f"**Skratka projektu:** {project['skratka']}  ")
    parts.append("")

    # --- Opis sections (manuscript/*.md) ---
    man_dir = resolve_project_path(project_root, "manuscript")
    section_files = sorted(man_dir.glob("*.md")) if man_dir.is_dir() else []
    if section_files:
        parts.append("## Opis projektu\n")
        for f in section_files:
            parts.append(f.read_text(encoding="utf-8").strip() + "\n")
    else:
        parts.append("## Opis projektu\n\n_(žiadne sekcie v `manuscript/`)_\n")

    # --- Budget ---
    bcfg = reqs.get("budget") or {}
    bpath = resolve_project_path(project_root, str(bcfg.get("file", "budget/rozpocet.csv")))
    if bpath.is_file():
        _, brows = read_rows(bpath)
        total_cov = sum(_to_float(r.get("celkove_opravnene", "")) for r in brows)
        total_nar = sum(_to_float(r.get("narokovane", "")) for r in brows)
        parts.append("## Rozpočet\n")
        parts.append(_md_table(
            ["WP", "Názov výdavku", "Kat.", "Počet", "Jedn. cena", "COV bez DPH", "Nárokované"],
            [[r.get("wp", ""), r.get("nazov_vydavku", ""), r.get("kategoria", ""),
              r.get("pocet_jednotiek", ""), r.get("jednotkova_cena", ""),
              _eur(_to_float(r.get("celkove_opravnene", ""))), _eur(_to_float(r.get("narokovane", "")))]
             for r in brows]))
        parts.append("")
        parts.append(f"**Celkové oprávnené výdavky (COV):** {_eur(total_cov)}  ")
        parts.append(f"**Žiadaná výška PPM:** {_eur(total_nar)}  ")
        parts.append(f"**Spolufinancovanie:** {_eur(total_cov - total_nar)}  ")
        parts.append("")

    # --- Indicators ---
    icfg = reqs.get("indicators") or {}
    ipath = resolve_project_path(project_root, str(icfg.get("file", "indicators/indicators.csv")))
    if ipath.is_file():
        _, irows = read_csv_rows(ipath)
        parts.append("## Merateľné ukazovatele\n")
        parts.append(_md_table(
            ["Názov", "Merná j.", "Východisko", "Plán", "Typ"],
            [[r.get("nazov", ""), r.get("merna_jednotka", ""), r.get("vychodiskova_hodnota", ""),
              r.get("planovana_hodnota", ""), r.get("typ", "")] for r in irows]))
        parts.append("")

    parts.append("---\n_Vygenerované `tool/grant.py build`. Placeholdre sa nahrádzajú reálnymi údajmi až pri finalizácii (z `_anonymization-key.local.md`)._")
    return "\n".join(parts) + "\n"


def _model(project_root: Path) -> tuple[dict, dict]:
    reqs = {}
    rp = resolve_project_path(project_root, "call-requirements.yaml")
    if rp.is_file():
        reqs = load_yaml(rp)
    proj = {}
    pp = resolve_project_path(project_root, "project.yaml")
    if pp.is_file():
        proj = load_yaml(pp)
    return reqs, proj


def build_opis_docx(project_root: Path, output: str = "publication/opis.docx") -> Path:
    """Render the Opis (Príloha 2b) + budget/indicators tables as a binary DOCX."""
    reqs, proj = _model(project_root)
    call = reqs.get("call") or {}
    project = proj.get("project") or {}
    blocks: list[tuple[str, Any]] = [("h", project.get("nazov") or call.get("name") or "Opis projektu")]
    if call.get("number"):
        blocks.append(("p", f"Výzva: {call.get('name', '')} ({call['number']})"))

    man_dir = resolve_project_path(project_root, "manuscript")
    for f in sorted(man_dir.glob("*.md")) if man_dir.is_dir() else []:
        for chunk in f.read_text(encoding="utf-8").split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.startswith("#"):
                blocks.append(("h", chunk.lstrip("# ").strip()))
            else:
                blocks.append(("p", " ".join(line.strip() for line in chunk.splitlines())))

    bcfg = reqs.get("budget") or {}
    bpath = resolve_project_path(project_root, str(bcfg.get("file", "budget/rozpocet.csv")))
    if bpath.is_file():
        _, brows = read_rows(bpath)
        blocks.append(("h", "Rozpočet"))
        blocks.append(("table", (["WP", "Názov výdavku", "Kat.", "COV bez DPH", "Nárokované"],
                                  [[r.get("wp", ""), r.get("nazov_vydavku", ""), r.get("kategoria", ""),
                                    _eur(_to_float(r.get("celkove_opravnene", ""))),
                                    _eur(_to_float(r.get("narokovane", "")))] for r in brows])))

    out = resolve_project_path(project_root, output)
    write_docx(out, blocks)
    return out


# RIS3 domény pre nadpisy pracovných balíkov (oficiálny 2c layout)
_WP_NAMES = {
    "3-1": "Inteligentné a prepojené senzory a zariadenia",
    "3-2": "Zvýšenie úžitkovej hodnoty všetkých druhov údajov a databáz",
    "3-3": "Inteligentné energetické systémy",
    "3-4": "Kybernetická bezpečnosť a kryptografia",
}
_2C_HEADER = ["Názov výdavku", "Kategória výdavkov", "Merná jednotka", "Počet jednotiek",
              "Jednotková cena bez DPH (EUR)", "Celkové oprávnené výdavky bez DPH (EUR)",
              "Intenzita pomoci", "Nárokované oprávnené výdavky bez DPH (EUR)", "Vecný popis výdavku"]


def build_budget_xlsx(project_root: Path, output: str = "publication/rozpocet.xlsx") -> Path:
    """Render budget (Príloha 2c) + indicators as a binary XLSX, in the official
    per-work-package block layout (WP header + TRL row + column headers + rows +
    per-WP subtotal), then the paušál and the grand total."""
    reqs, proj = _model(project_root)
    sheets: list[tuple[str, list[list[Any]]]] = []

    bcfg = reqs.get("budget") or {}
    bpath = resolve_project_path(project_root, str(bcfg.get("file", "budget/rozpocet.csv")))
    if bpath.is_file():
        _, brows = read_rows(bpath)
        wp_order = [str(w) for w in (bcfg.get("work_packages") or ["3-1", "3-2", "3-3", "3-4"])]
        trl_by_wp = {str(w.get("id")): w.get("trl_start", "") for w in (proj.get("work_packages") or [])}

        def _row(r):
            return [r.get("nazov_vydavku", ""), r.get("kategoria", ""), r.get("merna_jednotka", ""),
                    _to_float(r.get("pocet_jednotiek", "")), _to_float(r.get("jednotkova_cena", "")),
                    _to_float(r.get("celkove_opravnene", "")), _to_float(r.get("intenzita", "")),
                    _to_float(r.get("narokovane", "")), r.get("vecny_popis", "")]

        # paušál per WP (pro-rata 20 % z priamych nákladov 521+518+551 daného WP) — oficiálny 2c layout
        regime = str((proj.get("project") or {}).get("regime", bcfg.get("regime", "A")))
        pcfg = (bcfg.get("pausal") or {}).get(regime) or {}
        prate = float(pcfg.get("rate", 0.20)); pcode = str(pcfg.get("code", "920"))
        base_codes = set(pcfg.get("base_codes", ["521", "518", "551"]))
        eff = float((reqs.get("aid_intensity") or {}).get("call_cap", 0.60))

        data: list[list[Any]] = [["PODROBNÝ ROZPOČET PROJEKTU"]]
        for wp in wp_order:
            wp_rows = [r for r in brows if (r.get("wp") or "").strip() == wp
                       and (r.get("kategoria") or "").strip() != pcode]
            if not wp_rows:
                continue
            data.append([f"PRACOVNÝ BALÍK: {wp} {_WP_NAMES.get(wp, '')}"])
            data.append([f"Úroveň technologickej pripravenosti (TRL): {trl_by_wp.get(wp, '')}"])
            data.append(list(_2C_HEADER))
            for r in wp_rows:
                data.append(_row(r))
            wp_base = sum(_to_float(r.get("celkove_opravnene", "")) for r in wp_rows
                          if (r.get("kategoria") or "").strip() in base_codes)
            wp_pausal = round(prate * wp_base, 2)
            data.append([f"Paušálna sadzba – ostatné výdavky ({int(prate*100)} %)", pcode, "projekt", 1, "",
                         wp_pausal, eff, round(wp_pausal * eff, 2), f"{int(prate*100)} % zo Σ(521+518+551) v {wp}"])
            sub_cov = sum(_to_float(r.get("celkove_opravnene", "")) for r in wp_rows) + wp_pausal
            sub_nar = sum(_to_float(r.get("narokovane", "")) for r in wp_rows) + round(wp_pausal * eff, 2)
            data.append([f"SPOLU - pracovný balík {wp}", "", "", "", "", sub_cov, "", sub_nar, ""])
            data.append([])

        total_cov = sum(_to_float(r.get("celkove_opravnene", "")) for r in brows)
        total_nar = sum(_to_float(r.get("narokovane", "")) for r in brows)
        data.append(["SPOLU -  oprávnené výdavky (zdroj POO)", "", "", "", "", total_cov, "", total_nar, ""])
        sheets.append(("Rozpočet 2c", data))

    icfg = reqs.get("indicators") or {}
    ipath = resolve_project_path(project_root, str(icfg.get("file", "indicators/indicators.csv")))
    if ipath.is_file():
        ihdr, irows = read_csv_rows(ipath)
        sheets.append(("Indikátory", [ihdr, *[[r.get(h, "") for h in ihdr] for r in irows]]))

    out = resolve_project_path(project_root, output)
    write_xlsx(out, sheets or [("Rozpočet", [])])
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Build a submission dossier / binary attachments.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--target", choices=("markdown", "docx", "xlsx"), default="markdown")
    p.add_argument("--output", default=None)
    args = p.parse_args()
    root = args.project_root.resolve()
    if args.target == "docx":
        out = build_opis_docx(root, args.output or "publication/opis.docx")
    elif args.target == "xlsx":
        out = build_budget_xlsx(root, args.output or "publication/rozpocet.xlsx")
    else:
        out = resolve_project_path(root, args.output or "publication/dossier.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_dossier(root), encoding="utf-8")
    rel = out.relative_to(root) if out.is_relative_to(root) else out
    print(f"Build ({args.target}) written: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
