#!/usr/bin/env python3
"""Scaffolding for forking the repo to a NEW call / application.

Makes onboarding a new výzva repeatable and agent-friendly:
    grant.py new-call <number>            -> calls/<n>/ + templates/opis/<n>/ + templates/annexes/<n>/
    grant.py new-application <call> <app> -> applications/<call>-<app>/ skeleton
    grant.py tokens                       -> print the token vocabulary (docs/TOKENS.md)

Copies from templates/_starters/ and templates/*-template.yaml; never overwrites existing files.
"""
from __future__ import annotations

import argparse
import sys as _sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
_REPO = _TOOL.parent


def _write(path: Path, text: str, made: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    made.append(str(path))


def _read(rel: str) -> str:
    return (_REPO / rel).read_text(encoding="utf-8")


def new_call(number: str, repo_root: Path | None = None) -> tuple[list[str], list[str]]:
    r = repo_root or _REPO
    made: list[str] = []
    skipped: list[str] = []
    (r / "calls" / number / "source-md" / "oficialne").mkdir(parents=True, exist_ok=True)
    (r / "calls" / number / "source-md" / "ziadatel").mkdir(parents=True, exist_ok=True)
    _write(r / "calls" / number / "SEMANTIC-MAP.md",
           f"# Sémantická mapa — výzva {number}\n\n> STARTER. Po ingeste oficiálnych dokumentov sem zapíš:\n"
           "> inventár dokumentov, kľúčové fakty (alokácia, limity, lehoty, eligibilita), vzťahy a\n"
           "> kandidátov na `call-requirements.yaml`. Postup: `skills/onboard-call/SKILL.md`.\n",
           made, skipped)
    _write(r / "calls" / number / "source-md" / "oficialne" / "README.md",
           "Sem daj oficiálne dokumenty výzvy skonvertované do markdownu 1:1 (výzva, 2b Opis, 2c rozpočet, prílohy, schéma pomoci).\n",
           made, skipped)
    _write(r / "templates" / "opis" / number / "opis-2b.md",
           _read("templates/_starters/opis-2b.starter.md"), made, skipped)
    _write(r / "templates" / "opis" / number / "required-structure.yaml",
           _read("templates/_starters/required-structure.starter.yaml"), made, skipped)
    _write(r / "templates" / "annexes" / number / "annexes.yaml",
           _read("templates/_starters/annexes.starter.yaml"), made, skipped)
    return made, skipped


_SECTIONS = ["10_abstrakt", "20_ciel", "40_excelentnost", "50_technicke",
             "60_dopad", "70_aktivity", "80_rizika", "90_manazment"]


def new_application(call: str, applicant: str, repo_root: Path | None = None) -> tuple[list[str], list[str]]:
    r = repo_root or _REPO
    made: list[str] = []
    skipped: list[str] = []
    app = r / "applications" / f"{call}-{applicant}"
    cr = _read("templates/call-requirements-v2-template.yaml").replace(
        'number: "<kód výzvy, napr. 17I04-04-V05>"', f'number: "{call}"')
    _write(app / "call-requirements.yaml", cr, made, skipped)
    _write(app / "project.yaml", _read("templates/project-template.yaml"), made, skipped)
    _write(app / "legislation.yaml", _read("templates/legislation-template.yaml"), made, skipped)
    _write(app / "study_manifest.yaml",
           f'project:\n  title: "Žiadosť {call} — {applicant}"\n  short_name: "{applicant}-{call}"\n'
           'paths:\n  qc_reports_dir: "analysis/qc_reports"\n', made, skipped)
    _write(app / "budget" / "rozpocet.csv",
           "wp,nazov_vydavku,kategoria,merna_jednotka,pocet_jednotiek,jednotkova_cena,celkove_opravnene,intenzita,narokovane,vecny_popis\n",
           made, skipped)
    _write(app / "indicators" / "indicators.csv",
           "nazov,definicia,merna_jednotka,vychodiskova_hodnota,planovana_hodnota,typ\n", made, skipped)
    _write(app / "references" / "source-registry.yaml",
           "# Track-record žiadateľa (VaV projekty v doménach RIS3 za 2 roky).\nsources: []\n", made, skipped)
    for s in _SECTIONS:
        _write(app / "manuscript" / f"{s}.md", f"### {s.split('_', 1)[1]}\n\n[DOPLNIŤ: obsah sekcie]\n", made, skipped)
    _write(app / "README.md",
           f"# Žiadosť {call} — {applicant}\n\nVyplň `project.yaml` + `call-requirements.yaml`, píš `manuscript/*.md`,\n"
           "potom:\n```\npython3 tool/grant.py --project-root " + f"applications/{call}-{applicant}" +
           " build --target all\npython3 tool/grant.py --project-root " + f"applications/{call}-{applicant}" +
           " qc --mode final_publication --fail-on major\n```\nPostup a compliance-first disciplína: `skills/grant-prep/SKILL.md`.\n",
           made, skipped)
    return made, skipped


def print_tokens(project_root: Path) -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ba", _HERE / "build_annexes.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for k in sorted(m.build_context(project_root)):
        print("{{" + k + "}}")


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold a new call / application.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("new-call"); c.add_argument("number")
    a = sub.add_parser("new-application"); a.add_argument("call"); a.add_argument("applicant")
    t = sub.add_parser("tokens"); t.add_argument("--project-root", type=Path, default=Path.cwd())
    args = p.parse_args()

    if args.cmd == "tokens":
        print_tokens(args.project_root.resolve())
        return 0
    if args.cmd == "new-call":
        made, skipped = new_call(args.number)
        nxt = (f"1) daj oficiálne dokumenty do calls/{args.number}/source-md/oficialne/ (1:1 markdown)\n"
               f"2) napíš calls/{args.number}/SEMANTIC-MAP.md\n"
               f"3) prispôsob templates/opis/{args.number}/{{opis-2b.md, required-structure.yaml}} + templates/annexes/{args.number}/ podľa oficiálnych šablôn\n"
               f"4) grant.py new-application {args.number} <firma>")
    else:
        made, skipped = new_application(args.call, args.applicant)
        nxt = (f"1) vyplň applications/{args.call}-{args.applicant}/project.yaml + call-requirements.yaml\n"
               "2) píš manuscript/*.md, rozpočet, indikátory\n"
               "3) grant.py build --target all  &&  grant.py qc --mode final_publication --fail-on major")

    for f in made:
        print(f"  + {f}")
    for f in skipped:
        print(f"  = (existuje, preskočené) {f}")
    print("\nĎalej:\n" + nxt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
