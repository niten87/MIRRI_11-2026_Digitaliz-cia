#!/usr/bin/env python3
"""Aid-intensity checker for grant applications (NASTROJ-C2).

Computes the correct effective aid intensity from project data (MSP size,
place of realization, regime) and the `aid_intensity` block, then verifies each
budget row's `narokovane` and the total against the call cap. Rules follow
docs/SPEC-grantapp.md §4.2 (I1–I7). Emits typed Findings (area="aid_intensity").

    effective_A = min(base_rate + size_uplift[size] + region_uplift?, call_cap)   (never > scheme_cap)
    effective_B = regime_B_fixed                                                   (výskumná organizácia)
    per-row:  narokovane == celkove_opravnene * effective
    total:    Σ narokovane <= call_cap * Σ celkove   (regime B: == regime_B_fixed * Σ celkove)
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
from grantlib.csvio import read_csv_rows, read_rows  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402

TOL = 0.01


def to_float(cell: str) -> float | None:
    s = (cell or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _f(sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="aid_intensity", check_id=cid,
                   file="call-requirements.yaml", message=msg, evidence_refs=ev or [], suggested_fix="")


def is_bratislava(miesto: str) -> bool:
    m = (miesto or "").lower()
    # Handle explicit negation, e.g. "mimo Bratislavského kraja" → NOT Bratislava.
    if "mimo" in m:
        return False
    return "bratislav" in m or "ba kraj" in m


def check_aid_intensity(requirements: dict[str, Any], project_root: Path) -> list[Finding]:
    cfg = requirements.get("aid_intensity") or {}
    if not cfg:
        return []
    findings: list[Finding] = []

    proj = {}
    proj_path = resolve_project_path(project_root, "project.yaml")
    if proj_path.is_file():
        proj = load_yaml(proj_path)
    regime = str((proj.get("project") or {}).get("regime")
                 or (requirements.get("call") or {}).get("regime", "A"))
    miesto = str((proj.get("project") or {}).get("miesto_realizacie", ""))
    size = str(((proj.get("applicant") or {}).get("msp") or {}).get("size_category", ""))

    call_cap = float(cfg.get("call_cap", 1.0))
    scheme_cap = float(cfg.get("scheme_cap", 1.0))
    region_uplift = float(cfg.get("region_uplift", 0.0))
    region_applied = not is_bratislava(miesto)

    # --- I1/I2/I5 — effective intensity ---
    if regime == "B":
        effective = float(cfg.get("regime_B_fixed", call_cap))
    else:
        uplift_map = cfg.get("size_uplift") or {}
        if size not in uplift_map:
            findings.append(_f("blocker", "size_unknown",
                               f"MSP size_category `{size}` not in size_uplift keys {sorted(uplift_map)} (set project.applicant.msp.size_category).",
                               [size]))
            return findings
        raw = float(cfg.get("base_rate", 0.0)) + float(uplift_map[size]) + (region_uplift if region_applied else 0.0)
        effective = min(raw, call_cap)
        if effective > scheme_cap + TOL:  # I: never above the scheme's absolute cap
            findings.append(_f("blocker", "intensity_over_scheme_cap",
                               f"Effective intensity {effective:.2%} exceeds scheme cap {scheme_cap:.0%}.",
                               [f"{effective:.4f}>{scheme_cap}"]))

    findings.append(_f("info", "effective_intensity",
                       f"Effective intensity = {effective:.2%} (regime {regime}, size `{size or 'n/a'}`, region uplift {'applied' if region_applied and regime != 'B' else 'not applied'}).",
                       [f"{effective:.4f}"]))

    # --- read budget rows for per-row and total checks ---
    budget_cfg = requirements.get("budget") or {}
    bpath = resolve_project_path(project_root, str(budget_cfg.get("file", "budget/rozpocet.csv")))
    if not bpath.is_file():
        return findings
    _, rows = read_rows(bpath)

    total_cov = 0.0
    total_nar = 0.0
    for i, row in enumerate(rows, start=2):
        cov = to_float(row.get("celkove_opravnene", ""))
        nar = to_float(row.get("narokovane", ""))
        if cov is not None:
            total_cov += cov
        if nar is not None:
            total_nar += nar
        # I3 — per-row narokovane == celkove * effective
        if cov is not None and nar is not None:
            expected = round(cov * effective, 2)
            if abs(nar - expected) > TOL:
                findings.append(_f("major", "narokovane_mismatch",
                                   f"Row {i}: narokovane {nar} != celkove {cov} * {effective:.2%} = {expected:.2f}.",
                                   [f"{nar}!={expected:.2f}"]))

    # --- I4/I5 — total vs cap ---
    if regime == "B":
        expected_total = round(effective * total_cov, 2)
        if abs(total_nar - expected_total) > TOL:
            findings.append(_f("blocker", "regimeB_not_fixed_60",
                               f"Regime B: Σ narokovane {total_nar:.2f} must equal {effective:.0%} of COV {total_cov:.2f} = {expected_total:.2f}.",
                               [f"{total_nar:.2f}!={expected_total:.2f}"]))
    else:
        cap_amount = call_cap * total_cov
        if total_nar > cap_amount + TOL:
            findings.append(_f("blocker", "intensity_over_cap",
                               f"Σ narokovane {total_nar:.2f} exceeds call cap {call_cap:.0%} of COV {total_cov:.2f} = {cap_amount:.2f}.",
                               [f"{total_nar:.2f}>{cap_amount:.2f}"]))

    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Grant aid-intensity checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--requirements", default="call-requirements.yaml")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    reqs = load_yaml(resolve_project_path(root, args.requirements))
    findings = check_aid_intensity(reqs, root)
    blockers = [f for f in findings if f.severity == "blocker"]
    if args.format == "json":
        print(json.dumps({"decision": "BLOCK" if blockers else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Aid-intensity check: {'BLOCK' if blockers else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
