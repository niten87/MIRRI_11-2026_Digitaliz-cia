#!/usr/bin/env python3
"""Generate the call's applicant annexes from tokenized templates (NASTROJ-D4b).

The framework fills the whole call, not just the Opis: for each annex declared in
`templates/annexes/<call-number>/annexes.yaml` it takes a tokenized markdown
template (authentic structure of the official document with `{{token}}` slots),
fills the tokens from the application model (project.yaml + computed budget), and
writes filled markdown + a binary DOCX to `publication/annexes/`.

Identity fields default to anonymization placeholders ([ZIADATEL] …); they are
replaced with real values only at finalization (from the reverse key). Available
tokens are the keys returned by build_context() — see applicants/annex tokens.
"""
from __future__ import annotations

import argparse
import re
import sys as _sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in _sys.path:
    _sys.path.append(str(_TOOL))
from grantlib.paths import resolve_project_path  # noqa: E402
from grantlib.csvio import read_rows  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402
from grantlib.docxio import write_docx  # noqa: E402

TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def _f(cell: str) -> float:
    try:
        return float((cell or "").strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _eur(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " €"


def _ident(applicant: dict[str, Any], key: str, placeholder: str) -> str:
    val = applicant.get(key)
    return str(val) if val else placeholder


def build_context(project_root: Path) -> dict[str, str]:
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
    applicant = proj.get("applicant") or {}
    fin = proj.get("financovanie") or {}
    msp = applicant.get("msp") or {}
    wps = project.get("prioritne_domeny") or [w.get("id") for w in (proj.get("work_packages") or [])]

    ctx: dict[str, str] = {
        "call.name": str(call.get("name", "")),
        "call.number": str(call.get("number", "")),
        "call.deadline": str(call.get("deadline", "")),
        "call.realization_deadline": str(call.get("realization_deadline", "")),
        "applicant.nazov": _ident(applicant, "nazov", "[ZIADATEL]"),
        "applicant.ico": _ident(applicant, "ico", "[ICO]"),
        "applicant.dic": _ident(applicant, "dic", "[DIC]"),
        "applicant.ic_dph": _ident(applicant, "ic_dph", "[IC_DPH]"),
        "applicant.statutar": _ident(applicant, "statutar", "[STATUTAR]"),
        "applicant.adresa": _ident(applicant, "adresa", "[ADRESA]"),
        "applicant.iban": _ident(applicant, "iban", "[IBAN]"),
        "applicant.banka": _ident(applicant, "banka", "[BANKA]"),
        "applicant.telefon": _ident(applicant, "telefon", "[TELEFON]"),
        "applicant.email": _ident(applicant, "email", "[EMAIL]"),
        "msp.zamestnanci": str(msp.get("zamestnanci", "")),
        "msp.obrat_eur": str(msp.get("obrat_eur", "")),
        "msp.suvaha_eur": str(msp.get("suvaha_eur", "")),
        "msp.size_category": str(msp.get("size_category", "")),
        "project.nazov": str(project.get("nazov", "")),
        "project.skratka": str(project.get("skratka", "")),
        "project.miesto_realizacie": str(project.get("miesto_realizacie", "")),
        "project.trl_start": str(project.get("trl_start", "")),
        "project.trl_end": str(project.get("trl_end", "")),
        "project.domeny": ", ".join(str(w) for w in wps),
        "financovanie.celkove_opravnene": _eur(_f(str(fin.get("celkove_opravnene", 0)))),
        "financovanie.ziadana_ppm": _eur(_f(str(fin.get("ziadana_ppm", 0)))),
        "financovanie.spolufinancovanie": _eur(_f(str(fin.get("spolufinancovanie", 0)))),
    }

    # --- identity extras + program structure + contact ---
    kont = proj.get("kontakt") or (proj.get("personnel") or [{}])[0]
    ctx.update({
        "applicant.pravna_forma": _ident(applicant, "pravna_forma", "[PRAVNA_FORMA]"),
        "applicant.platitel_dph": "Áno" if not (reqs.get("budget") or {}).get("vat_included", False) else "Nie",
        "applicant.koresp_adresa": _ident(applicant, "koresp_adresa", ""),
        "call.komponent": str(call.get("komponent", "17 – Digitálne Slovensko")),
        "call.investicia": str(call.get("investicia", "Investícia 4: Podpora projektov zameraných na vývoj a aplikáciu špičkových digitálnych technológií")),
        "kontakt.meno": str(kont.get("meno", "[STATUTAR]")),
        "kontakt.telefon": str((proj.get("kontakt") or {}).get("telefon", "[TELEFON]")),
        "kontakt.email": str((proj.get("kontakt") or {}).get("email", "[EMAIL]")),
    })

    # obdobie realizácie z prvej/poslednej aktivity
    starts, ends = [], []
    for wp in proj.get("work_packages") or []:
        for a in wp.get("aktivity") or []:
            if a.get("zaciatok"):
                starts.append(str(a["zaciatok"]))
            if a.get("koniec"):
                ends.append(str(a["koniec"]))
    ctx["project.obdobie"] = f"{min(starts)} – {max(ends)}" if starts and ends else ""
    ctx["project.dlzka_realizacie"] = f"od: {min(starts)}  do: {ends and max(ends) or call.get('realization_deadline','')}" if starts else ""

    def _kv(rows: list[tuple[str, str]]) -> str:
        out = ["| Údaj | Hodnota |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in rows]
        return "\n".join(out)

    def _tbl(headers: list[str], rows: list[list[Any]]) -> str:
        out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
        out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
        return "\n".join(out)

    # --- hlavičkové tabuľky Opisu 2b ---
    ctx["tables.vykonavatel"] = _kv([
        ("Názov vykonávateľa", "Ministerstvo investícií, regionálneho rozvoja a informatizácie SR"),
        ("Adresa vykonávateľa", "Pribinova 4195/25, 811 09 Bratislava – Staré Mesto"),
        ("IČO vykonávateľa", "50349287")])
    ctx["tables.programova_struktura"] = _kv([
        ("Názov výzvy", ctx["call.name"]), ("Číslo výzvy", ctx["call.number"]),
        ("Komponent", ctx["call.komponent"]), ("Investícia/Reforma", ctx["call.investicia"])])
    ctx["tables.identifikacia_ziadatel"] = _kv([
        ("Názov", ctx["applicant.nazov"]), ("IČO", ctx["applicant.ico"]), ("DIČ", ctx["applicant.dic"]),
        ("Platiteľ DPH", ctx["applicant.platitel_dph"]), ("IČ DPH", ctx["applicant.ic_dph"]),
        ("Právna forma", ctx["applicant.pravna_forma"]), ("Adresa", ctx["applicant.adresa"]),
        ("Štatutárny zástupca", ctx["applicant.statutar"])])
    ctx["tables.financovanie_platba"] = _kv([("Číslo IBAN", ctx["applicant.iban"]), ("Banka", ctx["applicant.banka"])])
    ctx["tables.kontaktne_osoby"] = _kv([
        ("Meno a priezvisko", ctx["kontakt.meno"]), ("Telefonický kontakt", ctx["kontakt.telefon"]),
        ("Email", ctx["kontakt.email"])])
    ctx["tables.financny_prehlad"] = _kv([
        ("Celkové oprávnené výdavky projektu bez DPH", ctx["financovanie.celkove_opravnene"]),
        ("Žiadaná výška prostriedkov mechanizmu bez DPH", ctx["financovanie.ziadana_ppm"]),
        ("Výška povinného spolufinancovania bez DPH", ctx["financovanie.spolufinancovanie"])])
    ctx["tables.identifikacia_projekt"] = _kv([
        ("Názov projektu", ctx["project.nazov"]), ("Skratka", ctx["project.skratka"]),
        ("Dĺžka realizácie projektu", ctx["project.dlzka_realizacie"]),
        ("Miesto realizácie projektu", ctx["project.miesto_realizacie"])])

    # doménový checklist 3-1..3-4
    DOM = {"3-1": "Inteligentné a prepojené senzory a zariadenia",
           "3-2": "Zvýšenie úžitkovej hodnoty všetkých druhov údajov a databáz",
           "3-3": "Inteligentné energetické systémy",
           "3-4": "Kybernetická bezpečnosť a kryptografia"}
    ctx["tables.domeny_checklist"] = "\n".join(
        f"- {'☒' if k in wps else '☐'} {k}: {v}" for k, v in DOM.items())

    # tabuľka intenzity pomoci (režim A, experimentálny vývoj)
    aid = reqs.get("aid_intensity") or {}
    size = str(msp.get("size_category", ""))
    base = float(aid.get("base_rate", 0.25))
    su = float((aid.get("size_uplift") or {}).get(size, 0.0))
    m = ctx["project.miesto_realizacie"].lower()
    region_ok = ("mimo" in m) or not ("bratislav" in m or "ba kraj" in m)
    ru = float(aid.get("region_uplift", 0.0)) if region_ok else 0.0
    eff = min(base + su + ru, float(aid.get("call_cap", 0.60)))
    pct = lambda x: f"{x*100:.0f} %"
    ctx["tables.intenzita"] = _tbl(["Intenzita pomoci", "% z COV"], [
        ["Základná intenzita – experimentálny vývoj", pct(base)],
        [f"Veľkostná kategória podniku ({size})", pct(su)],
        ["Podporovaný región podľa čl. 107 ods. 3 a) ZFEÚ", pct(ru)],
        ["**Spolu – uplatnená intenzita pomoci** (max 60 %)", f"**{pct(eff)}**"]])
    ctx["aid.effective"] = pct(eff)

    # štruktúrované tabuľky Aktivity / Míľniky / Riziká / Personál / Indikátory
    ar = []
    for wp in proj.get("work_packages") or []:
        for a in wp.get("aktivity") or []:
            ar.append([a.get("por", ""), a.get("nazov", ""), wp.get("id", ""), a.get("vystup", ""),
                       a.get("zaciatok", ""), a.get("koniec", "")])
    ctx["tables.aktivity"] = _tbl(["Por.", "Názov aktivity", "WP", "Výstup", "Začiatok", "Koniec"], ar)
    ctx["tables.milniky"] = _tbl(["Por.", "Názov míľnika", "Aktivity", "Akceptačné kritérium", "Začiatok", "Koniec"],
        [[m.get("por", ""), m.get("nazov", ""), ", ".join(str(x) for x in (m.get("aktivity") or [])),
          m.get("akceptacne_kriterium", ""), m.get("zaciatok", ""), m.get("koniec", "")]
         for m in (proj.get("milestones") or [])])
    # plain-text zoznamy (pre bunky Prílohy 5 — nie vnorené tabuľky)
    ctx["tables.aktivity_list"] = "; ".join(
        f"A{a.get('por')} (WP {wp.get('id')}): {a.get('nazov','')}"
        for wp in (proj.get("work_packages") or []) for a in (wp.get("aktivity") or []))
    ctx["tables.personnel_list"] = "; ".join(
        f"{p.get('pozicia','')} ({p.get('fte','')} FTE)" for p in (proj.get("personnel") or []))
    ctx["tables.rizika"] = _tbl(["Por.", "Názov rizika", "Typ", "Pravdepodobnosť", "Dopad", "Opatrenie"],
        [[r.get("por", ""), r.get("nazov", ""), r.get("typ", ""), r.get("pravdepodobnost", ""),
          r.get("dopad", ""), r.get("opatrenie", "")] for r in (proj.get("risks") or [])])
    ctx["tables.personnel"] = _tbl(["Meno", "Pozícia", "FTE"],
        [[p.get("meno", ""), p.get("pozicia", ""), p.get("fte", "")] for p in (proj.get("personnel") or [])])

    # indikátory
    icfg = reqs.get("indicators") or {}
    ipath = resolve_project_path(project_root, str(icfg.get("file", "indicators/indicators.csv")))
    if ipath.is_file():
        _, irows = read_rows(ipath)
        ctx["tables.indikatory"] = _tbl(["Názov", "Definícia", "MJ", "Východisko", "Plán", "Typ"],
            [[r.get("nazov", ""), r.get("definicia", ""), r.get("merna_jednotka", ""),
              r.get("vychodiskova_hodnota", ""), r.get("planovana_hodnota", ""), r.get("typ", "")] for r in irows])
    else:
        ctx["tables.indikatory"] = ""

    # VaV track-record (references/source-registry.yaml)
    reg = resolve_project_path(project_root, "references/source-registry.yaml")
    if reg.is_file():
        rdata = load_yaml(reg) or {}
        ctx["tables.vav"] = _tbl(["Názov VaV projektu", "Rok", "RIS3 doména", "Obsah a výsledok", "Doklad", "Pozícia"],
            [[s.get("title", ""), s.get("year", ""), s.get("domain", ""),
              f"{s.get('obsah','')} {s.get('vysledok','')}".strip(), s.get("doklad", ""), s.get("pozicia", "prijímateľ")]
             for s in (rdata.get("sources") or [])])
    else:
        ctx["tables.vav"] = ""

    # obsah sekcií Opisu (manuscript/*.md, bez ### nadpisu)
    for sec in reqs.get("sections") or []:
        sid = str(sec.get("id", ""))
        mpath = resolve_project_path(project_root, str(sec.get("manuscript", "")))
        if sid and mpath.is_file():
            body = mpath.read_text(encoding="utf-8")
            # drop only the section's own top-level heading (### Title); keep #### subheadings
            out2 = [ln for ln in body.splitlines()
                    if not (ln.strip().startswith("### ") and not ln.strip().startswith("#### "))]
            ctx[f"section.{sid}"] = "\n".join(out2).strip()

    # rozpočet tabuľka
    bcfg = reqs.get("budget") or {}
    bpath = resolve_project_path(project_root, str(bcfg.get("file", "budget/rozpocet.csv")))
    if bpath.is_file():
        _, brows = read_rows(bpath)
        lines = ["| WP | Názov výdavku | Kat. | COV bez DPH | Nárokované |", "|---|---|---|---|---|"]
        for r in brows:
            lines.append(f"| {r.get('wp','')} | {r.get('nazov_vydavku','')} | {r.get('kategoria','')} "
                         f"| {_eur(_f(r.get('celkove_opravnene','')))} | {_eur(_f(r.get('narokovane','')))} |")
        ctx["tables.rozpocet"] = "\n".join(lines)

        # ISPO rozpad po oficiálnych kategóriách + PPM vs vlastné zdroje
        CLASS = {"521": "Osobné náklady", "518": "Služby"}
        groups: dict[str, list] = {"Osobné náklady": [], "Služby": [], "Ostatné výdavky": []}
        for r in brows:
            cls = CLASS.get((r.get("kategoria") or "").strip(), "Ostatné výdavky")
            cov = _f(r.get("celkove_opravnene", "")); nar = _f(r.get("narokovane", ""))
            groups[cls].append((r.get("nazov_vydavku", ""), nar, cov - nar))
        ilines = ["| Kategória | Názov výdavku | Suma z PPM bez DPH | Vlastné zdroje bez DPH |",
                  "|---|---|---|---|"]
        for cls, items in groups.items():
            if not items:
                continue
            for naz, ppm, vl in items:
                ilines.append(f"| {cls} | {naz} | {_eur(ppm)} | {_eur(vl)} |")
            ilines.append(f"| **{cls} – SPOLU** |  | **{_eur(sum(i[1] for i in items))}** | **{_eur(sum(i[2] for i in items))}** |")
        ctx["tables.rozpocet_ispo"] = "\n".join(ilines)
    return ctx


def fill_template(text: str, ctx: dict[str, str]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in ctx:
            return ctx[key]
        missing.append(key)
        return m.group(0)

    return TOKEN_RE.sub(repl, text), missing


def _md_to_blocks(md: str) -> list[tuple[str, Any]]:
    blocks: list[tuple[str, Any]] = []
    for para in md.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.lstrip().startswith("|") and "---" in para:
            rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
                    for ln in para.splitlines() if ln.strip().startswith("|") and "---" not in ln]
            if rows:
                blocks.append(("table", (rows[0], rows[1:])))
            continue
        if para.startswith("#"):
            blocks.append(("h", para.lstrip("# ").strip()))
        else:
            blocks.append(("p", " ".join(l.strip() for l in para.splitlines())))
    return blocks


def build_opis(project_root: Path, output: str = "publication/opis.docx",
               repo_root: Path | None = None) -> tuple[Path, list[str]]:
    """Render the full Opis projektu (Príloha 2b) from the tokenized template.

    Reproduces the whole official 2b structure (header tables + sections + structured
    activity/milestone/risk/indicator tables) and renders real Word tables via
    _md_to_blocks. Returns (docx_path, missing_tokens)."""
    repo_root = repo_root or _TOOL.parent
    reqs = load_yaml(resolve_project_path(project_root, "call-requirements.yaml"))
    number = str((reqs.get("call") or {}).get("number", "")).strip()
    tpl = repo_root / "templates" / "opis" / number / "opis-2b.md"
    out = resolve_project_path(project_root, output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not tpl.is_file():
        write_docx(out, [("h", "Opis projektu"), ("p", f"(chýba šablóna {tpl})")])
        return out, [f"template:{tpl.name}"]
    ctx = build_context(project_root)
    filled, missing = fill_template(tpl.read_text(encoding="utf-8"), ctx)
    (out.parent / "opis.md").write_text(filled, encoding="utf-8")
    write_docx(out, _md_to_blocks(filled))
    return out, missing


def build_annexes(project_root: Path, repo_root: Path | None = None) -> list[tuple[str, Path, list[str]]]:
    repo_root = repo_root or _TOOL.parent
    reqs = load_yaml(resolve_project_path(project_root, "call-requirements.yaml"))
    number = str((reqs.get("call") or {}).get("number", "")).strip()
    manifest_path = repo_root / "templates" / "annexes" / number / "annexes.yaml"
    if not manifest_path.is_file():
        return []
    manifest = load_yaml(manifest_path) or {}
    ctx = build_context(project_root)
    out_dir = resolve_project_path(project_root, "publication/annexes")
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, Path, list[str]]] = []
    for annex in manifest.get("annexes") or []:
        aid = str(annex.get("id", "annex"))
        tpl = manifest_path.parent / str(annex.get("template", f"{aid}.md"))
        if not tpl.is_file():
            continue
        filled, missing = fill_template(tpl.read_text(encoding="utf-8"), ctx)
        (out_dir / f"{aid}.md").write_text(filled, encoding="utf-8")
        docx = out_dir / f"{aid}.docx"
        write_docx(docx, _md_to_blocks(filled))
        results.append((aid, docx, missing))
    return results


def main() -> int:
    p = argparse.ArgumentParser(description="Generate the call's Opis 2b and/or applicant annexes.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--opis", action="store_true", help="build the full Opis projektu (2b) DOCX")
    args = p.parse_args()
    root = args.project_root.resolve()
    if args.opis:
        out, missing = build_opis(root)
        rel = out.relative_to(root) if out.is_relative_to(root) else out
        note = f"  ⚠ nevyplnené tokeny: {sorted(set(missing))}" if missing else ""
        print(f"Opis 2b → {rel}{note}")
        return 0
    results = build_annexes(root)
    if not results:
        print("No annex manifest for this call (templates/annexes/<call-number>/annexes.yaml).")
        return 0
    for aid, docx, missing in results:
        rel = docx.relative_to(root) if docx.is_relative_to(root) else docx
        note = f"  ⚠ nevyplnené tokeny: {sorted(set(missing))}" if missing else ""
        print(f"Annex `{aid}` → {rel}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
