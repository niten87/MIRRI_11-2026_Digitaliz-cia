#!/usr/bin/env python3
"""Anonymization leak-scan (NASTROJ-C5).

Scans text artifacts for real PII / company identifiers that should have been
replaced by placeholders before anything is committed or packaged. Pattern-based
(dependency-free) + an optional literal denylist. Placeholder tokens (e.g.
`[ZIADATEL]`, `[OSOBA_1]`) are recognised and never flagged. A real match is a
blocker (`unanonymized_pii` / `company_identifier_leak`). Rules: SPEC §7.

This is a final-gate / pre-package check (mode `final_publication`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys as _sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in _sys.path:
    _sys.path.append(str(_TOOL))
from grantlib.findings import Finding  # noqa: E402
from grantlib.paths import resolve_project_path  # noqa: E402

PLACEHOLDER_RE = re.compile(r"\[[A-ZÁČĎÉÍĽĹŇÓŔŠŤÚÝŽ_]+(?:_\d+)?\]")

PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "iban_sk": re.compile(r"\bSK\d{2}(?:\s?\d){20}\b"),
    "dic": re.compile(r"\bSK\d{10}\b"),
    "phone_sk": re.compile(r"(?:\+421|00421)\s?\d(?:[\d\s]{7,}\d)"),
}

DEFAULT_SCAN = ["manuscript", "project.yaml", "call-requirements.yaml", "budget", "indicators"]


def _iter_text_files(project_root: Path, targets: list[str]):
    for rel in targets:
        p = resolve_project_path(project_root, rel)
        if p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file() and sub.suffix.lower() in {".md", ".yaml", ".yml", ".csv", ".txt"}:
                    yield sub
        elif p.is_file():
            yield p


def _mask_placeholders(text: str) -> str:
    return PLACEHOLDER_RE.sub("", text)


def check_anonymization_leaks(project_root: Path, *, targets: list[str] | None = None,
                              denylist: list[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    denylist = [d for d in (denylist or []) if d.strip()]
    for path in _iter_text_files(project_root, targets or DEFAULT_SCAN):
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else str(path)
        masked = _mask_placeholders(raw)
        for kind, rx in PII_PATTERNS.items():
            for m in rx.finditer(masked):
                findings.append(Finding("blocker", "anonymization", "unanonymized_pii", rel,
                                        f"Possible real {kind} in `{rel}`: {m.group(0)!r} (use a placeholder).",
                                        [kind], "Replace with a placeholder; keep real values only in *_.local.md."))
        for literal in denylist:
            if literal in raw:
                findings.append(Finding("blocker", "anonymization", "company_identifier_leak", rel,
                                        f"Forbidden identifier `{literal}` present in `{rel}`.",
                                        [literal], "Replace with the corresponding placeholder."))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Anonymization leak-scan.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--denylist", default=None, help="path to a newline-separated file of forbidden literals")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    denylist = []
    if args.denylist and Path(args.denylist).is_file():
        denylist = Path(args.denylist).read_text(encoding="utf-8").splitlines()
    findings = check_anonymization_leaks(root, denylist=denylist)
    blockers = [f for f in findings if f.severity == "blocker"]
    if args.format == "json":
        print(json.dumps({"decision": "BLOCK" if blockers else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Anonymization leak-scan: {'BLOCK' if blockers else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no leaks (no real PII / forbidden identifiers found)")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
