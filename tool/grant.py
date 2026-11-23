#!/usr/bin/env python3
"""Grant tool CLI (local, grant-scoped). Replaces the research submodule's
framework.py for grant applications. Manifest-aware, delegates to tool/checks/.

    python3 tool/grant.py --project-root <app> check [--format json]
    python3 tool/grant.py --project-root <app> qc --mode pre_word [--fail-on major]
    python3 tool/grant.py --project-root <app> package --manifest <csv>
    python3 tool/grant.py --project-root <app> build --target docx   # (stub, NASTROJ-D4)

Grant-domain only — no research pipeline (stats/citations). See docs/SPEC-grantapp.md.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
CHECKS = _ROOT / "checks"


def run(script: str, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(CHECKS / script), *args]).returncode


def cmd_check(root: Path, a: argparse.Namespace) -> int:
    return run("check_call_requirements.py", ["--project-root", str(root), "--format", a.format])


def cmd_qc(root: Path, a: argparse.Namespace) -> int:
    args = ["--project-root", str(root), "--mode", a.mode, "--format", a.format]
    if a.fail_on:
        args += ["--fail-on", a.fail_on]
    return run("run_grant_qc.py", args)


def cmd_budget(root: Path, a: argparse.Namespace) -> int:
    rc = run("check_budget.py", ["--project-root", str(root), "--format", a.format])
    rc |= run("check_aid_intensity.py", ["--project-root", str(root), "--format", a.format])
    return rc


def cmd_package(root: Path, a: argparse.Namespace) -> int:
    if not a.manifest:
        print("package: --manifest <csv> je povinný (submission manifest).", file=sys.stderr)
        return 2
    return run("build_submission_package.py", ["--project-root", str(root), "--manifest", a.manifest])


def cmd_applicant(root: Path, a: argparse.Namespace) -> int:
    args = [a.action, "--project-root", str(root)]
    if a.company:
        args += ["--company", a.company]
    return run("applicant_profile.py", args)


def cmd_new_call(root: Path, a: argparse.Namespace) -> int:
    return run("scaffold.py", ["new-call", a.number])


def cmd_new_application(root: Path, a: argparse.Namespace) -> int:
    return run("scaffold.py", ["new-application", a.call, a.applicant])


def cmd_tokens(root: Path, a: argparse.Namespace) -> int:
    return run("scaffold.py", ["tokens", "--project-root", str(root)])


def cmd_build(root: Path, a: argparse.Namespace) -> int:
    if a.target == "pdf":
        print("BUILD (pdf): PDF render nie je podporovaný (dependency-free). Použi docx/xlsx/markdown.")
        return 0
    if a.target == "docx":  # full Opis projektu (2b) from tokenized template
        return run("build_annexes.py", ["--project-root", str(root), "--opis"])
    if a.target == "annexes":
        return run("build_annexes.py", ["--project-root", str(root)])
    if a.target == "all":
        rc = run("build_annexes.py", ["--project-root", str(root), "--opis"])
        rc |= run("build_dossier.py", ["--project-root", str(root), "--target", "xlsx"])
        rc |= run("build_annexes.py", ["--project-root", str(root)])
        return rc
    return run("build_dossier.py", ["--project-root", str(root), "--target", a.target])


def main() -> int:
    p = argparse.ArgumentParser(description="Grant tool CLI (grant-scoped, local).")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("check", help="call-requirements completeness gate")
    sc.add_argument("--format", choices=("text", "json"), default="text")
    sc.set_defaults(fn=cmd_check)

    sq = sub.add_parser("qc", help="aggregated grant QC gate")
    sq.add_argument("--mode", choices=("smoke", "pre_word", "final_publication"), default="pre_word")
    sq.add_argument("--fail-on", choices=("info", "minor", "major", "blocker"), default=None)
    sq.add_argument("--format", choices=("text", "json"), default="text")
    sq.set_defaults(fn=cmd_qc)

    snc = sub.add_parser("new-call", help="scaffold a new call (calls/ + templates/)")
    snc.add_argument("number")
    snc.set_defaults(fn=cmd_new_call)

    sna = sub.add_parser("new-application", help="scaffold a new application skeleton")
    sna.add_argument("call")
    sna.add_argument("applicant")
    sna.set_defaults(fn=cmd_new_application)

    stok = sub.add_parser("tokens", help="print the available {{token}} vocabulary")
    stok.set_defaults(fn=cmd_tokens)

    sapp = sub.add_parser("applicant", help="applicant/company profile registry (list | key)")
    sapp.add_argument("action", choices=("list", "key"))
    sapp.add_argument("--company", default=None)
    sapp.set_defaults(fn=cmd_applicant)

    sbud = sub.add_parser("budget", help="budget checker (rows/categories/paušál/envelope)")
    sbud.add_argument("--format", choices=("text", "json"), default="text")
    sbud.set_defaults(fn=cmd_budget)

    sp = sub.add_parser("package", help="build submission package from a CSV manifest")
    sp.add_argument("--manifest", default=None)
    sp.set_defaults(fn=cmd_package)

    sb = sub.add_parser("build", help="render Opis/rozpočet/prílohy (markdown|docx|xlsx|annexes|all)")
    sb.add_argument("--target", choices=("markdown", "docx", "pdf", "xlsx", "annexes", "all"), default="docx")
    sb.set_defaults(fn=cmd_build)

    args = p.parse_args()
    return args.fn(args.project_root.resolve(), args)


if __name__ == "__main__":
    raise SystemExit(main())
