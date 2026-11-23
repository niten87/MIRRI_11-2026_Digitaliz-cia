#!/usr/bin/env python3
"""Measurable-indicators checker for grant applications (NASTROJ-C3).

Verifies the indicators CSV against the `indicators` block of call-requirements:
counts of main/secondary indicators, total cap, at least one dissemination
secondary, and that required fields are filled. Rules follow docs/SPEC-grantapp.md
§3 (F7) / §6.2. Emits typed Findings (area="indicators").

Indicators CSV columns (default): nazov, definicia, merna_jednotka,
vychodiskova_hodnota, planovana_hodnota, typ   (typ ∈ {hlavny, vedlajsi}).
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
from grantlib.csvio import read_csv_rows  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402

DISSEMINATION_KEYWORDS = ("publik", "disemin", "šíren", "siren", "konferenc", "seminár", "seminar", "transfer")
DEFAULT_FIELDS = ["nazov", "definicia", "merna_jednotka", "vychodiskova_hodnota", "planovana_hodnota", "typ"]


def _f(sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="indicators", check_id=cid, file="indicators", message=msg,
                   evidence_refs=ev or [], suggested_fix="")


def _is_dissemination(row: dict[str, str]) -> bool:
    text = f"{row.get('nazov', '')} {row.get('definicia', '')}".lower()
    return any(k in text for k in DISSEMINATION_KEYWORDS)


def check_indicators(cfg: dict[str, Any], project_root: Path) -> list[Finding]:
    if not cfg:
        return []
    rel = str(cfg.get("file", "indicators/indicators.csv"))
    path = resolve_project_path(project_root, rel)
    if not path.is_file():
        return [_f("major", "indicators_file_missing", f"Indicators file `{rel}` not found.")]

    findings: list[Finding] = []
    _, rows = read_csv_rows(path)
    fields = cfg.get("fields") or DEFAULT_FIELDS

    main = [r for r in rows if (r.get("typ", "").strip().lower() == "hlavny")]
    secondary = [r for r in rows if (r.get("typ", "").strip().lower() == "vedlajsi")]

    def count_check(items, lo_key, hi_key, label):
        lo, hi = cfg.get(lo_key), cfg.get(hi_key)
        n = len(items)
        if lo is not None and n < int(lo):
            findings.append(_f("major", f"missing_{label}",
                               f"Only {n} {label} indicator(s); minimum {lo}.", [f"{n}<{lo}"]))
        if hi is not None and n > int(hi):
            findings.append(_f("major", "indicators_count_out_of_range",
                               f"{n} {label} indicator(s); maximum {hi}.", [f"{n}>{hi}"]))

    count_check(main, "min_main", "max_main", "main")
    count_check(secondary, "min_secondary", "max_secondary", "secondary")

    max_total = cfg.get("max_total")
    if max_total is not None and len(rows) > int(max_total):
        findings.append(_f("major", "indicators_count_out_of_range",
                           f"{len(rows)} indicators total; maximum {max_total}.", [f"{len(rows)}>{max_total}"]))

    if cfg.get("require_dissemination_secondary") and not any(_is_dissemination(r) for r in secondary):
        findings.append(_f("major", "missing_dissemination_secondary",
                           "No dissemination-related secondary indicator (publikácia/diseminácia/…)."))

    for i, row in enumerate(rows, start=2):
        for field in fields:
            if not (row.get(field, "") or "").strip():
                findings.append(_f("minor", "indicator_field_missing",
                                   f"Row {i}: field `{field}` is empty.", [field]))

    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Grant indicators checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--requirements", default="call-requirements.yaml")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    reqs = load_yaml(resolve_project_path(root, args.requirements))
    findings = check_indicators(reqs.get("indicators") or {}, root)
    majors = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if majors else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Indicators check: {'REVISE' if majors else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings (counts, dissemination and fields OK)")
    return 1 if majors else 0


if __name__ == "__main__":
    raise SystemExit(main())
