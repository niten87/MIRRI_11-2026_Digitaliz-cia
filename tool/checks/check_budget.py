#!/usr/bin/env python3
"""Deterministic budget checker for grant applications (NASTROJ-C1).

Consumes a normalized budget CSV (one row per výdavok) and the `budget` block of
call-requirements.yaml, and verifies row arithmetic, allowed categories per
regime, the lump-sum (paušál) rate, the total and the funding envelope.
Emits typed Findings (area="budget"). Rules follow docs/SPEC-grantapp.md §4.1.

Normalized budget CSV columns:
    wp, nazov_vydavku, kategoria, merna_jednotka, pocet_jednotiek,
    jednotkova_cena, celkove_opravnene, intenzita, narokovane, vecny_popis

The messy official layout (Príloha 3 / 2c, with per-work-package subtotal blocks)
is a render target for the build step (NASTROJ-D4), not the checker's input.
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

TOL = 0.01  # eur cent tolerance


def to_float(cell: str) -> float | None:
    s = (cell or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _f(name: str, sev: str, cid: str, msg: str, ev: list[str] | None = None) -> Finding:
    return Finding(severity=sev, area="budget", check_id=cid, file=name, message=msg,
                   evidence_refs=ev or [], suggested_fix="")


def check_budget(budget_cfg: dict[str, Any], project_root: Path, *, regime: str) -> list[Finding]:
    findings: list[Finding] = []
    rel = str(budget_cfg.get("file") or "budget/rozpocet.csv")
    path = resolve_project_path(project_root, rel)
    if not path.is_file():
        return [_f(rel, "blocker", "budget_file_missing", f"Budget file `{rel}` not found.")]

    _, rows = read_rows(path)
    allowed = set((budget_cfg.get("categories") or {}).get(regime, []))
    pausal = (budget_cfg.get("pausal") or {}).get(regime) or {}
    pausal_code = str(pausal.get("code", "")) if pausal else ""
    base_codes = set(pausal.get("base_codes", []) or [])

    total_cov = 0.0
    base_sum = 0.0
    pausal_rows: list[dict[str, str]] = []

    for i, row in enumerate(rows, start=2):  # +1 header, +1 to 1-index
        kat = (row.get("kategoria") or "").strip()
        cov = to_float(row.get("celkove_opravnene", ""))
        pocet = to_float(row.get("pocet_jednotiek", ""))
        cena = to_float(row.get("jednotkova_cena", ""))
        name = row.get("nazov_vydavku") or f"riadok {i}"

        # R2 — category allowed for this regime
        if kat and allowed and kat not in allowed:
            findings.append(_f(rel, "blocker", "category_not_allowed",
                               f"Row {i} ({name}): category `{kat}` not allowed for regime {regime} (allowed: {sorted(allowed)}).",
                               [kat]))

        is_pausal = pausal_code and kat == pausal_code
        # R1 — row arithmetic (skip pausal rows: they are computed, not pocet*cena)
        if not is_pausal and cov is not None and pocet is not None and cena is not None:
            if abs(cov - pocet * cena) > TOL:
                findings.append(_f(rel, "major", "budget_row_mismatch",
                                   f"Row {i} ({name}): celkove_opravnene {cov} != pocet {pocet} * cena {cena} = {pocet * cena:.2f}.",
                                   [f"{cov}!={pocet * cena:.2f}"]))

        if cov is not None:
            total_cov += cov
            if kat in base_codes:
                base_sum += cov
        if is_pausal:
            pausal_rows.append(row)

    # R6 — paušál correctness
    if pausal_code and pausal.get("rate") is not None:
        rate = float(pausal["rate"])
        expected = round(rate * base_sum, 2)
        got = sum(to_float(r.get("celkove_opravnene", "")) or 0.0 for r in pausal_rows)
        if pausal_rows and abs(got - expected) > TOL:
            findings.append(_f(rel, "major", "pausal_wrong",
                               f"Paušál ({pausal_code}) is {got:.2f}, expected {rate:.0%} of base {base_sum:.2f} = {expected:.2f}.",
                               [f"{got:.2f}!={expected:.2f}"]))

    # R7 — funding envelope
    min_cov = budget_cfg.get("min_cov")
    max_cov = budget_cfg.get("max_cov")
    if min_cov is not None and total_cov < float(min_cov) - TOL:
        findings.append(_f(rel, "blocker", "budget_out_of_envelope",
                           f"Total COV {total_cov:.2f} < minimum {min_cov} (bez DPH).", [f"{total_cov:.2f}<{min_cov}"]))
    if max_cov is not None and total_cov > float(max_cov) + TOL:
        findings.append(_f(rel, "blocker", "budget_out_of_envelope",
                           f"Total COV {total_cov:.2f} > maximum {max_cov} (bez DPH).", [f"{total_cov:.2f}>{max_cov}"]))

    return findings


def resolve_regime(project_root: Path, requirements: dict[str, Any]) -> str:
    proj = resolve_project_path(project_root, "project.yaml")
    if proj.is_file():
        data = load_yaml(proj)
        r = ((data.get("project") or {}).get("regime"))
        if r:
            return str(r)
    return str((requirements.get("call") or {}).get("regime", "A"))


def main() -> int:
    p = argparse.ArgumentParser(description="Grant budget checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--requirements", default="call-requirements.yaml")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    reqs = load_yaml(resolve_project_path(root, args.requirements))
    budget_cfg = reqs.get("budget") or {}
    if not budget_cfg:
        print("No `budget` block in call-requirements.yaml — nothing to check.")
        return 0
    findings = check_budget(budget_cfg, root, regime=resolve_regime(root, reqs))
    blockers = [f for f in findings if f.severity == "blocker"]
    if args.format == "json":
        print(json.dumps({"decision": "BLOCK" if blockers else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Budget check: {'BLOCK' if blockers else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings (rows, categories, paušál and envelope OK)")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
