#!/usr/bin/env python3
"""Time-eligibility checker (NASTROJ-C8).

Verifies temporal eligibility of the project timeline against the call: activities
and expenses are eligible only from the day the application is submitted
(call.deadline) until the end of realization (call.realization_deadline). Flags any
activity starting before submission or ending after the realization deadline —
these produce ineligible costs. Emits Findings (area="timeline").
"""
from __future__ import annotations

import argparse
import datetime
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


def _d(v: Any) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(str(v))
    except (ValueError, TypeError):
        return None


def _f(sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="timeline", check_id=cid, file="project.yaml",
                   message=msg, evidence_refs=ev or [], suggested_fix="Adjust the activity dates into the eligible window.")


def check_timeline(requirements: dict[str, Any], project_root: Path) -> list[Finding]:
    call = requirements.get("call") or {}
    start = _d(call.get("deadline"))            # výdavky/aktivity až odo dňa podania
    end = _d(call.get("realization_deadline"))  # koniec vecnej realizácie
    proj_path = resolve_project_path(project_root, "project.yaml")
    if not proj_path.is_file() or (start is None and end is None):
        return []
    proj = load_yaml(proj_path)
    findings: list[Finding] = []

    for wp in proj.get("work_packages") or []:
        for a in wp.get("aktivity") or []:
            az, ak = _d(a.get("zaciatok")), _d(a.get("koniec"))
            label = f"WP {wp.get('id')} / A{a.get('por')} „{a.get('nazov','')}“"
            if start and az and az < start:
                findings.append(_f("major", "activity_before_submission",
                                   f"{label} začína {az.isoformat()} pred dňom podania ({start.isoformat()}) — výdavky by boli neoprávnené.",
                                   [az.isoformat()]))
            if end and ak and ak > end:
                findings.append(_f("major", "activity_after_realization",
                                   f"{label} končí {ak.isoformat()} po termíne realizácie ({end.isoformat()}).",
                                   [ak.isoformat()]))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Time-eligibility checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    reqs = load_yaml(resolve_project_path(root, "call-requirements.yaml"))
    findings = check_timeline(reqs, root)
    bad = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if bad else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Timeline eligibility: {'REVISE' if bad else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings (all activities within the eligible window)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
