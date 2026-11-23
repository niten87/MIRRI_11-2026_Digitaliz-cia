#!/usr/bin/env python3
"""Legislation freshness gate (NASTROJ-H3 / SPEC §5).

Reads `legislation.yaml` (pinned SK/EU sources + manual portals) and flags
staleness deterministically:
  - a pinned source with no `retrieved_at`      -> minor `legislation_unpinned`
  - `today - retrieved_at > freshness_window`   -> minor `legislation_stale`
  - a manual doc past its `validity`            -> major `manual_doc_expired`
(The "newer Usmernenie than pinned" blocker needs live data and is handled by the
agentic `legislation-retrieval` skill, not this deterministic gate.)
"""
from __future__ import annotations

import argparse
import datetime
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
from grantlib.yamllite import load_yaml  # noqa: E402

DEFAULT_WINDOW = 30


def _f(sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="legislation", check_id=cid, file="legislation.yaml",
                   message=msg, evidence_refs=ev or [], suggested_fix="")


def _parse_date(value: Any) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _validity_days(text: str) -> int | None:
    m = re.search(r"(\d+)", text or "")
    if not m:
        return None
    n = int(m.group(1))
    t = text.lower()
    if "mesiac" in t:
        return n * 30
    if "rok" in t:
        return n * 365
    if "dn" in t or "day" in t:
        return n
    return None


def check_legislation(project_root: Path, *, today: datetime.date | None = None) -> list[Finding]:
    path = resolve_project_path(project_root, "legislation.yaml")
    if not path.is_file():
        return []
    today = today or datetime.date.today()
    data = load_yaml(path)
    window = int(data.get("freshness_window_days", DEFAULT_WINDOW))
    findings: list[Finding] = []

    for src in data.get("sources") or []:
        sid = str(src.get("id", "source"))
        ra = _parse_date(src.get("retrieved_at"))
        if ra is None:
            findings.append(_f("minor", "legislation_unpinned",
                               f"Source `{sid}` has no valid `retrieved_at` — pin it after retrieval.", [sid]))
            continue
        age = (today - ra).days
        if age > window:
            findings.append(_f("minor", "legislation_stale",
                               f"Source `{sid}` retrieved {ra.isoformat()} ({age} d ago > {window} d) — re-verify.", [sid]))

    for m in data.get("manual_portals") or []:
        mid = str(m.get("id", "portal"))
        validity = m.get("validity")
        ra = _parse_date(m.get("retrieved_at"))
        days = _validity_days(str(validity)) if validity else None
        if days is not None and ra is not None and (today - ra).days > days:
            findings.append(_f("major", "manual_doc_expired",
                               f"Manual doc `{mid}` older than its validity ({validity}) — obtain a fresh one.", [mid]))

    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Legislation freshness gate.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--today", default=None, help="reference date YYYY-MM-DD (default: today)")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    today = _parse_date(args.today) if args.today else None
    findings = check_legislation(root, today=today)
    bad = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if bad else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Legislation freshness: {'REVISE' if bad else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings (legislation.yaml absent or all sources fresh)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
