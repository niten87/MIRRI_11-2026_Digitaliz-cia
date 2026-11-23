#!/usr/bin/env python3
"""Document structural-completeness gate (NASTROJ-C7).

The systemic fix for the class of bug the audit found: the framework validated
numbers and declared sections, but never checked that the GENERATED documents are
structurally complete vs the official template. This checker compares the built
Opis (publication/opis.md) and annexes against a per-call `required-structure.yaml`
(the mandatory sections/tables each document must contain) and flags anything
missing — so incompleteness is caught automatically, not by a manual audit.

Runs post-build (mode final_publication). Emits Findings (area="completeness").
"""
from __future__ import annotations

import argparse
import json
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
from grantlib.yamllite import load_yaml  # noqa: E402


def _f(sev: str, cid: str, file: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="completeness", check_id=cid, file=file,
                   message=msg, evidence_refs=ev or [], suggested_fix="Build the document and ensure this section/table is generated.")


def check_document_completeness(project_root: Path, repo_root: Path | None = None) -> list[Finding]:
    repo_root = repo_root or _TOOL.parent
    reqs = load_yaml(resolve_project_path(project_root, "call-requirements.yaml"))
    number = str((reqs.get("call") or {}).get("number", "")).strip()
    spec_path = repo_root / "templates" / "opis" / number / "required-structure.yaml"
    if not spec_path.is_file():
        return []
    spec = load_yaml(spec_path) or {}
    findings: list[Finding] = []

    for doc in spec.get("documents") or []:
        rel = str(doc.get("built", ""))
        required = doc.get("required_markers") or []
        sev = str(doc.get("severity", "major"))
        path = resolve_project_path(project_root, rel)
        if not path.is_file():
            findings.append(_f("info", "document_not_built", rel,
                               f"`{rel}` not built yet — run `grant.py build --target all` before the final gate."))
            continue
        text = path.read_text(encoding="utf-8")
        missing = [m for m in required if str(m) not in text]
        for m in missing:
            findings.append(_f(sev, "required_section_missing", rel,
                               f"Povinná časť „{m}“ chýba v generovanom `{rel}` (oproti oficiálnej šablóne)."))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Document structural-completeness gate.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    findings = check_document_completeness(root)
    bad = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if bad else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Document completeness: {'REVISE' if bad else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings (all required sections present, or nothing built yet)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
