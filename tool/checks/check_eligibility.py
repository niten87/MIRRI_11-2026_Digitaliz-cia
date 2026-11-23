#!/usr/bin/env python3
"""Computed eligibility checker (NASTROJ-C6).

Derives the MSP (SME) size category from headcount + turnover / balance sheet
(EU definition, GBER Annex I / schéma) and cross-checks it against the declared
`applicant.msp.size_category`. Also evaluates `computed:` eligibility items from
call-requirements (e.g. `check_eligibility.py::msp`). Emits Findings
(area="eligibility"). Nothing is "manually met=true" — the size is computed.

SME thresholds (headcount is a hard AND with turnover-OR-balance):
    mikro  : < 10  and (obrat ≤ 2M  or súvaha ≤ 2M)
    maly   : < 50  and (obrat ≤ 10M or súvaha ≤ 10M)
    stredny: < 250 and (obrat ≤ 50M or súvaha ≤ 43M)
    velky  : otherwise (nie je MSP)
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

_TIERS = [
    ("mikro", 10, 2_000_000, 2_000_000),
    ("maly", 50, 10_000_000, 10_000_000),
    ("stredny", 250, 50_000_000, 43_000_000),
]


def compute_msp_size(msp: dict[str, Any]) -> tuple[str | None, str]:
    staff = msp.get("zamestnanci")
    turnover = msp.get("obrat_eur")
    balance = msp.get("suvaha_eur")
    if not isinstance(staff, (int, float)):
        return None, "chýba `zamestnanci`"
    for name, staff_lim, t_lim, b_lim in _TIERS:
        fin_ok = (isinstance(turnover, (int, float)) and turnover <= t_lim) or \
                 (isinstance(balance, (int, float)) and balance <= b_lim)
        if staff < staff_lim and fin_ok:
            return name, f"{staff} zam., obrat {turnover}, súvaha {balance}"
    return "velky", f"{staff} zam., obrat {turnover}, súvaha {balance}"


def _f(sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="eligibility", check_id=cid, file="project.yaml",
                   message=msg, evidence_refs=ev or [], suggested_fix="")


def check_eligibility(requirements: dict[str, Any], project_root: Path) -> list[Finding]:
    proj_path = resolve_project_path(project_root, "project.yaml")
    if not proj_path.is_file():
        return []
    proj = load_yaml(proj_path)
    msp = dict((proj.get("applicant") or {}).get("msp") or {})

    # Only run MSP logic if there is an MSP block or a computed::msp eligibility item.
    wants_msp = bool(msp) or any(str(c.get("computed", "")).endswith("::msp")
                                 for c in (requirements.get("eligibility") or []))
    if not wants_msp:
        return []

    findings: list[Finding] = []
    size, reason = compute_msp_size(msp)
    if size is None:
        return [_f("major", "msp_incomputable", f"MSP size cannot be computed: {reason}.")]

    findings.append(_f("info", "msp_size_computed", f"Computed MSP size: `{size}` ({reason})."))

    declared = str(msp.get("size_category", "")).strip()
    if declared and declared != size:
        findings.append(_f("major", "msp_size_mismatch",
                           f"Declared size `{declared}` != computed `{size}` (from headcount/turnover/balance).",
                           [f"{declared}!={size}"]))

    if size == "velky":
        findings.append(_f("major", "eligibility_not_met",
                           "Applicant is `velky` (not an SME) — likely ineligible for an MSP-only call.", ["msp"]))

    # --- computed VaV track-record (podmienka č. 1) ---
    if any(str(c.get("computed", "")).endswith("::vav") for c in (requirements.get("eligibility") or [])):
        findings.extend(_check_vav(requirements, project_root))
    return findings


_RIS3 = {"3-1", "3-2", "3-3", "3-4"}


def _check_vav(requirements: dict[str, Any], project_root: Path) -> list[Finding]:
    regime = str((requirements.get("call") or {}).get("regime", "A"))
    need = 2 if regime == "B" else 1
    reg = resolve_project_path(project_root, "references/source-registry.yaml")
    if not reg.is_file():
        return [_f("major", "vav_evidence_missing", "references/source-registry.yaml chýba — nedá sa overiť VaV track-record.")]
    data = load_yaml(reg) or {}
    qualifying = [s for s in (data.get("sources") or []) if str(s.get("domain", "")) in _RIS3]
    n = len(qualifying)
    if n < need:
        return [_f("major", "vav_projekty_insufficient",
                   f"Len {n} VaV projekt(ov) v doménach RIS3 (potrebných ≥{need} pre režim {regime}).", [f"{n}<{need}"])]
    return [_f("info", "vav_projekty_ok", f"VaV track-record: {n} projekt(ov) v doménach RIS3 (≥{need} pre režim {regime}).")]


def main() -> int:
    p = argparse.ArgumentParser(description="Computed eligibility (MSP) checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--requirements", default="call-requirements.yaml")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    rp = resolve_project_path(root, args.requirements)
    reqs = load_yaml(rp) if rp.is_file() else {}
    findings = check_eligibility(reqs, root)
    bad = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if bad else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Eligibility (MSP) check: {'REVISE' if bad else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
