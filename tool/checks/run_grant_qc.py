#!/usr/bin/env python3
"""Slim grant QC aggregator (grant-only; NOT the research QC pipeline).

Runs the grant-domain checkers that exist and aggregates their typed Findings
into a single decision: BLOCK / REVISE / PASS_WITH_NOTES / PASS. Deliberately
does NOT pull in research checks (citations, figure refs, output manifests) —
this tool lives locally and stays grant-scoped (see docs/SPEC-grantapp.md).

Wired today: check_call_requirements. Add future checkers (check_budget,
check_aid_intensity, check_indicators, check_cross_document_consistency,
check_anonymization_leaks) to CHECKERS below as they land (BACKLOG NASTROJ-C).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys as _sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TOOL = _HERE.parent
if str(_TOOL) not in _sys.path:
    _sys.path.append(str(_TOOL))
from grantlib.findings import Finding, SEVERITY_ORDER  # noqa: E402
from grantlib.paths import resolve_project_path  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402

MODE_THRESHOLD = {"smoke": "blocker", "pre_word": "major", "final_publication": "major"}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run_checks(project_root: Path, mode: str = "pre_word") -> list[Finding]:
    findings: list[Finding] = []

    req_path = resolve_project_path(project_root, "call-requirements.yaml")
    requirements = load_yaml(req_path) if req_path.exists() else {}

    # --- call-requirements (grant completeness gate) ---
    if requirements:
        ccr = load_module("grant_check_call_requirements", _HERE / "check_call_requirements.py")
        findings.extend(ccr.check_call_requirements(requirements, project_root=project_root))

    # --- budget (rows / categories / paušál / envelope) — run if configured ---
    budget_cfg = requirements.get("budget") or {}
    if budget_cfg and resolve_project_path(project_root, str(budget_cfg.get("file", "budget/rozpocet.csv"))).is_file():
        cb = load_module("grant_check_budget", _HERE / "check_budget.py")
        findings.extend(cb.check_budget(budget_cfg, project_root, regime=cb.resolve_regime(project_root, requirements)))

    # --- aid intensity (effective rate / nárokované / cap / regime B) ---
    if requirements.get("aid_intensity"):
        ci = load_module("grant_check_aid_intensity", _HERE / "check_aid_intensity.py")
        findings.extend(ci.check_aid_intensity(requirements, project_root))

    # --- indicators (counts / dissemination / fields) ---
    if requirements.get("indicators"):
        cin = load_module("grant_check_indicators", _HERE / "check_indicators.py")
        findings.extend(cin.check_indicators(requirements["indicators"], project_root))

    # --- cross-document consistency (assertions vs project.yaml single source of truth) ---
    if requirements.get("consistency"):
        cx = load_module("grant_check_cross_doc", _HERE / "check_cross_document_consistency.py")
        findings.extend(cx.check_cross_document_consistency(requirements, project_root))

    # --- document structural completeness vs official template (post-build) ---
    if mode == "final_publication":
        cc = load_module("grant_check_doc_completeness", _HERE / "check_document_completeness.py")
        findings.extend(cc.check_document_completeness(project_root))

    # --- anonymization leak-scan (final gate only, before packaging) ---
    if mode == "final_publication":
        cl = load_module("grant_check_anon_leaks", _HERE / "check_anonymization_leaks.py")
        findings.extend(cl.check_anonymization_leaks(project_root))

    # --- computed eligibility (MSP size from headcount/turnover/balance) ---
    ce = load_module("grant_check_eligibility", _HERE / "check_eligibility.py")
    findings.extend(ce.check_eligibility(requirements, project_root))

    # --- time-eligibility (activities within submission → realization window) ---
    ct = load_module("grant_check_timeline", _HERE / "check_timeline.py")
    findings.extend(ct.check_timeline(requirements, project_root))

    # --- legislation freshness gate (if legislation.yaml present) ---
    if resolve_project_path(project_root, "legislation.yaml").is_file():
        cg = load_module("grant_check_legislation", _HERE / "check_legislation.py")
        findings.extend(cg.check_legislation(project_root))

    return findings


def decide(findings: list[Finding]) -> str:
    sev = {f.severity for f in findings}
    if "blocker" in sev:
        return "BLOCK"
    if "major" in sev:
        return "REVISE"
    return "PASS_WITH_NOTES" if findings else "PASS"


def render_md(decision: str, findings: list[Finding]) -> str:
    lines = [f"# Grant QC report", "", f"**Rozhodnutie:** `{decision}`", ""]
    if not findings:
        lines.append("- žiadne nálezy (call-requirements splnené)")
    for f in sorted(findings, key=lambda x: -SEVERITY_ORDER.get(x.severity, 0)):
        lines.append(f"- `{f.severity}` `{f.check_id}` ({f.file}): {f.message}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Slim grant QC aggregator.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=tuple(MODE_THRESHOLD), default="pre_word")
    parser.add_argument("--fail-on", choices=tuple(SEVERITY_ORDER), default=None)
    parser.add_argument("--output-dir", default="analysis/qc_reports")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    findings = run_checks(project_root, mode=args.mode)
    decision = decide(findings)

    out_dir = resolve_project_path(project_root, args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "grant_qc_report.json").write_text(
        json.dumps({"decision": decision, "mode": args.mode,
                    "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (out_dir / "grant_qc_report.md").write_text(render_md(decision, findings), encoding="utf-8")

    if args.format == "json":
        print(json.dumps({"decision": decision, "findings": [asdict(f) for f in findings]},
                         indent=2, ensure_ascii=False))
    else:
        print(f"Grant QC ({args.mode}): {decision}")
        for f in sorted(findings, key=lambda x: -SEVERITY_ORDER.get(x.severity, 0)):
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings")

    threshold = args.fail_on or MODE_THRESHOLD[args.mode]
    cutoff = SEVERITY_ORDER[threshold]
    return 1 if any(SEVERITY_ORDER.get(f.severity, 0) >= cutoff for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
