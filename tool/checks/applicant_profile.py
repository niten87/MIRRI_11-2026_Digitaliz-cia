#!/usr/bin/env python3
"""Applicant (company) profile registry helper.

Reads the gitignored central registry `applicants/companies.local.yaml` (real data
for multiple companies) and, for a chosen company, generates a per-application
reverse anonymization key `<app>/_anonymization-key.local.md` (also gitignored).
Lets you reuse one company's identifiers across many calls without ever committing
real data. See applicants/README.md.
"""
from __future__ import annotations

import argparse
import sys as _sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
_REPO = _TOOL.parent
if str(_TOOL) not in _sys.path:
    _sys.path.append(str(_TOOL))
from grantlib.yamllite import load_yaml  # noqa: E402

REGISTRY_REL = "applicants/companies.local.yaml"


def registry_path(repo_root: Path | None = None) -> Path:
    return (repo_root or _REPO) / REGISTRY_REL


def load_registry(repo_root: Path | None = None) -> dict[str, Any]:
    path = registry_path(repo_root)
    if not path.is_file():
        return {}
    return (load_yaml(path) or {}).get("companies") or {}


def list_companies(repo_root: Path | None = None) -> list[tuple[str, str]]:
    reg = load_registry(repo_root)
    return [(cid, str((c or {}).get("nazov_display", ""))) for cid, c in reg.items()]


def render_reverse_key(company_id: str, company: dict[str, Any]) -> str:
    lines = ["# LOKÁLNY reverzný kľúč — NECOMMITOVAŤ (gitignored)", "",
             f"Firma: {company.get('nazov_display', company_id)} (id: `{company_id}`)", "",
             "Placeholder → skutočná hodnota (na finalizáciu / de-anonymizáciu):", "",
             "| Placeholder | Skutočná hodnota |", "|---|---|"]
    for key, val in (company.get("placeholders") or {}).items():
        lines.append(f"| `[{key}]` | {val} |")
    msp = company.get("msp") or {}
    if msp:
        lines += ["", "## MSP (pre check_eligibility)"]
        for k, v in msp.items():
            lines.append(f"- {k}: {v}")
    if company.get("poznamky"):
        lines += ["", f"> Poznámky: {company['poznamky']}"]
    return "\n".join(lines) + "\n"


def write_reverse_key(company_id: str, app_root: Path, repo_root: Path | None = None) -> Path:
    reg = load_registry(repo_root)
    if company_id not in reg:
        raise KeyError(f"company `{company_id}` not in registry ({registry_path(repo_root)})")
    out = app_root / "_anonymization-key.local.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_reverse_key(company_id, reg[company_id] or {}), encoding="utf-8")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Applicant profile registry helper.")
    p.add_argument("action", choices=("list", "key"))
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--company", default=None)
    p.add_argument("--repo-root", type=Path, default=None)
    args = p.parse_args()
    repo = args.repo_root.resolve() if args.repo_root else _REPO

    if args.action == "list":
        companies = list_companies(repo)
        if not companies:
            print(f"No registry or no companies ({registry_path(repo)}). See applicants/README.md.")
            return 0
        print("Companies in registry:")
        for cid, name in companies:
            print(f"  - {cid}: {name}")
        return 0

    if not args.company:
        print("key: --company <id> is required.", file=_sys.stderr)
        return 2
    try:
        out = write_reverse_key(args.company, args.project_root.resolve(), repo)
    except KeyError as e:
        print(str(e), file=_sys.stderr)
        return 1
    rel = out.relative_to(repo) if out.is_relative_to(repo) else out
    print(f"Reverse key written (gitignored): {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
