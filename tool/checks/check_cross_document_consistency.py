#!/usr/bin/env python3
"""Cross-document consistency checker (NASTROJ-C4).

Evaluates the declarative `consistency` assertions from call-requirements against
a single context model assembled from project.yaml (the single source of truth)
plus values computed from the budget CSV. Two assertion forms:

    {id, left, right, op}   # op ∈ eq/ne/le/ge/lt/gt; left/right = dotted path or literal
    {id, expr}              # safe mini-expression (comparisons, and/or/not, + - * /,
                            #   and whitelisted funcs: set, disjoint, implies, len, abs)

No `eval` of arbitrary code — {expr} is parsed with `ast` and only a whitelist of
node types/functions is executed. An assertion that references data not present in
the model is SKIPPED with an info finding (never a false failure). Rules: SPEC §6.3.
"""
from __future__ import annotations

import argparse
import ast
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
_MISSING = object()


class MissingData(Exception):
    pass


def _to_float(cell: str) -> float | None:
    s = (cell or "").strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def build_context(project_root: Path, requirements: dict[str, Any]) -> dict[str, Any]:
    proj = {}
    p = resolve_project_path(project_root, "project.yaml")
    if p.is_file():
        proj = load_yaml(p)
    project = dict(proj.get("project") or {})
    project.setdefault("miesto", project.get("miesto_realizacie"))
    financovanie = dict(proj.get("financovanie") or {})
    msp = dict((proj.get("applicant") or {}).get("msp") or {})
    wp_ids = [w.get("id") for w in (proj.get("work_packages") or []) if isinstance(w, dict)]

    budget = {"total_cov": None, "sum_narokovane": None, "work_packages": None}
    bcfg = requirements.get("budget") or {}
    bpath = resolve_project_path(project_root, str(bcfg.get("file", "budget/rozpocet.csv")))
    if bpath.is_file():
        _, rows = read_rows(bpath)
        total = sum(_to_float(r.get("celkove_opravnene", "")) or 0.0 for r in rows)
        nar = sum(_to_float(r.get("narokovane", "")) or 0.0 for r in rows)
        wps = sorted({(r.get("wp") or "").strip() for r in rows if (r.get("wp") or "").strip()})
        budget = {"total_cov": round(total, 2), "sum_narokovane": round(nar, 2), "work_packages": wps}

    return {
        "project": {**project, "work_packages": wp_ids or project.get("work_packages")},
        "financovanie": financovanie,
        "opis": {"financovanie": financovanie, "work_packages": wp_ids},
        "budget": budget,
        "msp": msp,
        "aid_intensity": dict(requirements.get("aid_intensity") or {}),
    }


def _resolve_token(token: str, ctx: dict[str, Any]) -> Any:
    token = token.strip()
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    f = _to_float(token)
    if f is not None and any(c.isdigit() for c in token):
        return f
    cur: Any = ctx
    for part in token.split("."):
        if isinstance(cur, dict) and part in cur and cur[part] is not None:
            cur = cur[part]
        else:
            raise MissingData(token)
    return cur


def _cmp(left: Any, op: str, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if op == "eq":
            return abs(left - right) <= TOL
        if op == "ne":
            return abs(left - right) > TOL
    return {"eq": left == right, "ne": left != right, "le": left <= right,
            "ge": left >= right, "lt": left < right, "gt": left > right}[op]


# ---- safe {expr} evaluator ----
_FUNCS = {
    "set": lambda x: set(x),
    "len": lambda x: len(x),
    "abs": lambda x: abs(x),
    "disjoint": lambda a, b: len(set(a) & set(b)) == 0,
    "implies": lambda a, b: (not a) or b,
}
_CMP_OPS = {ast.Eq: "eq", ast.NotEq: "ne", ast.Lt: "lt", ast.LtE: "le", ast.Gt: "gt", ast.GtE: "ge"}


def _eval(node: ast.AST, ctx: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        raise MissingData(node.id)
    if isinstance(node, ast.Attribute):
        base = _eval(node.value, ctx)
        if isinstance(base, dict) and node.attr in base and base[node.attr] is not None:
            return base[node.attr]
        raise MissingData(node.attr)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_eval(e, ctx) for e in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval(node.operand, ctx)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, ctx) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        a, b = _eval(node.left, ctx), _eval(node.right, ctx)
        return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b,
                ast.Div: (a / b if b else float("nan"))}[type(node.op)]
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, ctx)
            if type(op) not in _CMP_OPS:
                raise ValueError(f"operator {type(op).__name__} not allowed")
            if not _cmp(left, _CMP_OPS[type(op)], right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_eval(a, ctx) for a in node.args])
    raise ValueError(f"expression node {type(node).__name__} not allowed")


def check_cross_document_consistency(requirements: dict[str, Any], project_root: Path) -> list[Finding]:
    asserts = requirements.get("consistency") or []
    if not asserts:
        return []
    ctx = build_context(project_root, requirements)
    findings: list[Finding] = []

    for item in asserts:
        aid = str(item.get("id", "assertion"))
        sev = str(item.get("severity", "major"))
        try:
            if "expr" in item and item.get("expr"):
                ok = bool(_eval(ast.parse(str(item["expr"]), mode="eval"), ctx))
                detail = str(item["expr"])
            else:
                left = _resolve_token(str(item.get("left", "")), ctx)
                right = _resolve_token(str(item.get("right", "")), ctx)
                op = str(item.get("op", "eq"))
                ok = _cmp(left, op, right)
                detail = f"{item.get('left')} {op} {item.get('right')} ({left} vs {right})"
        except MissingData as m:
            findings.append(Finding("info", "consistency", "consistency_skipped_missing_data",
                                    "project.yaml", f"Assertion `{aid}` skipped: `{m}` not in model.",
                                    [aid], "Fill the referenced value in project.yaml/budget."))
            continue
        except (ValueError, SyntaxError, TypeError) as e:
            findings.append(Finding("minor", "consistency", "consistency_bad_expression",
                                    "call-requirements.yaml", f"Assertion `{aid}` could not be evaluated: {e}",
                                    [aid], "Fix the assertion syntax."))
            continue
        if not ok:
            findings.append(Finding(sev, "consistency", f"consistency_failed:{aid}",
                                    "project.yaml", f"Consistency assertion `{aid}` failed: {detail}.",
                                    [aid], "Reconcile the values against project.yaml (single source of truth)."))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Cross-document consistency checker.")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--requirements", default="call-requirements.yaml")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    root = args.project_root.resolve()
    reqs = load_yaml(resolve_project_path(root, args.requirements))
    findings = check_cross_document_consistency(reqs, root)
    bad = [f for f in findings if f.severity in ("major", "blocker")]
    if args.format == "json":
        print(json.dumps({"decision": "REVISE" if bad else "PASS",
                          "findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False))
    else:
        print(f"Consistency check: {'REVISE' if bad else 'PASS'}")
        for f in findings:
            print(f"- {f.severity} {f.check_id}: {f.message}")
        if not findings:
            print("- no findings")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
