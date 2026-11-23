#!/usr/bin/env python3
"""Check a grant/proposal draft against a call's requirements framework.

Deterministic, dependency-free "what is still missing" gate for grant
applications (or any structured submission). It reads a `call-requirements.yaml`
that encodes the call's framework — required sections with word limits, required
annexes, and eligibility flags — and checks the draft against it:

- `missing_required_section` (blocker): a required section file is absent or empty.
- `section_over_limit` / `section_over_char_limit` (major): a section exceeds its word/char limit.
- `section_under_min` / `section_under_char_min` (minor): a section is below a declared minimum.
- `missing_required_annex` (blocker): a required annex artifact does not exist.
- `annex_over_page_limit` (major): a PDF annex exceeds its page limit.
- `eligibility_not_met` (major): a declared eligibility criterion is not met.
- `deadline_passed` (blocker) / `deadline_near` (minor): submission deadline vs. today.

This lets the same framework QC gate surface the structure a call demands and
what the draft still lacks, instead of a manual checklist.
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

_root = Path(__file__).resolve()
while not (_root / "grantlib" / "__init__.py").exists() and _root != _root.parent:
    _root = _root.parent
if str(_root) not in _sys.path:
    _sys.path.append(str(_root))
from grantlib.findings import Finding  # noqa: E402
from grantlib.paths import resolve_project_path  # noqa: E402
from grantlib.yamllite import load_yaml  # noqa: E402
from grantlib import schema as _schema  # noqa: E402


BRACKET_CITATION_RE = re.compile(r"\[[^\]\n]*@[A-Za-z0-9][A-Za-z0-9:_-]*[^\]\n]*\]")

# Regime-keyed and size-keyed maps use fixed, enumerable keys, so they are
# expressed with explicit fields (the validator has no dynamic-key support).
_REGIME_LIST = {"type": "map", "allow_unknown": False,
                "fields": {"A": {"type": "list", "item": {"type": "str"}},
                           "B": {"type": "list", "item": {"type": "str"}}}}
_PAUSAL_ENTRY = {"type": "map", "allow_unknown": False,
                 "fields": {"code": {"type": "str"}, "rate": {"type": "float"},
                            "base_codes": {"type": "list", "item": {"type": "str"}}}}

CALL_REQUIREMENTS_SCHEMA = {
    "type": "map",
    "allow_unknown": False,
    "fields": {
        "version": {"type": "int"},
        "call": {
            "type": "map",
            "allow_unknown": False,
            "fields": {
                "name": {"type": "str"},
                "number": {"type": "str"},
                "deadline": {"type": "str"},
                "realization_deadline": {"type": "str"},
                "allocation_eur": {"type": "int"},
                "regime": {"type": "str", "enum": ["A", "B"]},
                "komponent": {"type": "str"},
                "investicia": {"type": "str"},
                "language": {"type": "str"},
                "warn_days": {"type": "int"},
            },
        },
        "sections": {
            "type": "list",
            "item": {
                "type": "map",
                "required": ["id"],
                "allow_unknown": False,
                "fields": {
                    "id": {"type": "str"},
                    "title": {"type": "str"},
                    "manuscript": {"type": "str"},
                    "required": {"type": "bool"},
                    "max_words": {"type": "int"},
                    "min_words": {"type": "int"},
                    "max_chars": {"type": "int"},
                    "min_chars": {"type": "int"},
                },
            },
        },
        "annexes": {
            "type": "list",
            "item": {
                "type": "map",
                "required": ["id"],
                "allow_unknown": False,
                "fields": {
                    "id": {"type": "str"},
                    "title": {"type": "str"},
                    "artifact": {"type": "str"},
                    "required": {"type": "bool"},
                    "required_if": {"type": "str"},
                    "format": {"type": "str"},
                    "max_pages": {"type": "int"},
                },
            },
        },
        # ---- v2: rozpočet ----
        "budget": {
            "type": "map",
            "allow_unknown": False,
            "fields": {
                "file": {"type": "str"},
                "currency": {"type": "str"},
                "vat_included": {"type": "bool"},
                "min_cov": {"type": "int"},
                "max_cov": {"type": "int"},
                "work_packages": {"type": "list", "item": {"type": "str"}},
                "require_trl_per_wp": {"type": "bool"},
                "categories": _REGIME_LIST,
                "pausal": {"type": "map", "allow_unknown": False,
                           "fields": {"A": _PAUSAL_ENTRY, "B": _PAUSAL_ENTRY}},
                "totals": {"type": "map", "allow_unknown": False,
                           "fields": {"sum_wp_equals_total": {"type": "bool"},
                                      "row_check": {"type": "str"}}},
            },
        },
        # ---- v2: intenzita pomoci ----
        "aid_intensity": {
            "type": "map",
            "allow_unknown": False,
            "fields": {
                "scheme_ref": {"type": "str"},
                "category": {"type": "str"},
                "base_rate": {"type": "float"},
                "size_uplift": {"type": "map", "allow_unknown": False,
                                "fields": {"mikro": {"type": "float"}, "maly": {"type": "float"},
                                           "stredny": {"type": "float"}, "velky": {"type": "float"}}},
                "region_uplift": {"type": "float"},
                "region_uplift_condition": {"type": "str"},
                "call_cap": {"type": "float"},
                "scheme_cap": {"type": "float"},
                "regime_B_fixed": {"type": "float"},
                "per_row_check": {"type": "str"},
                "effective_le_cap": {"type": "bool"},
            },
        },
        # ---- v2: informatívne kritériá odborného hodnotenia ----
        "scoring": {
            "type": "map",
            "allow_unknown": False,
            "fields": {
                "min_total": {"type": "int"},
                "max_total": {"type": "int"},
                "min_per_criterion": {"type": "int"},
                "criteria": {"type": "list", "item": {"type": "str"}},
                "evaluators": {"type": "int"},
            },
        },
        # ---- v2: merateľné ukazovatele ----
        "indicators": {
            "type": "map",
            "allow_unknown": False,
            "fields": {
                "file": {"type": "str"},
                "min_main": {"type": "int"}, "max_main": {"type": "int"},
                "min_secondary": {"type": "int"}, "max_secondary": {"type": "int"},
                "max_total": {"type": "int"},
                "require_dissemination_secondary": {"type": "bool"},
                "fields": {"type": "list", "item": {"type": "str"}},
                "plan_by": {"type": "str"},
                "catalogue_ref": {"type": "str"},
            },
        },
        # ---- v2: krížové kontroly (deklaratívne asercie) ----
        "consistency": {
            "type": "list",
            "item": {
                "type": "map",
                "required": ["id"],
                "allow_unknown": False,
                "fields": {
                    "id": {"type": "str"},
                    "left": {"type": "str"},
                    "right": {"type": "str"},
                    "op": {"type": "str", "enum": ["eq", "ne", "le", "ge", "lt", "gt"]},
                    "expr": {"type": "str"},
                    "severity": {"type": "str", "enum": ["info", "minor", "major", "blocker"]},
                },
            },
        },
        "eligibility": {
            "type": "list",
            "item": {
                "type": "map",
                "required": ["id"],
                "allow_unknown": False,
                "fields": {
                    "id": {"type": "str"},
                    "description": {"type": "str"},
                    "met": {"type": "bool"},
                    "evidence": {"type": "str"},
                    "computed": {"type": "str"},
                },
            },
        },
    },
}


def load_requirements(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def _content(text: str) -> str:
    return BRACKET_CITATION_RE.sub("", text)


def word_count(text: str) -> int:
    return len(_content(text).split())


def char_count(text: str) -> int:
    return len(_content(text).strip())


def count_pdf_pages(path: Path) -> int | None:
    """Best-effort dependency-free PDF page count; None if it cannot be determined."""
    if path.suffix.lower() != ".pdf":
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    counts = [int(match) for match in re.findall(rb"/Count\s+(\d+)", data)]
    if counts:
        return max(counts)
    pages = re.findall(rb"/Type\s*/Page(?![s])", data)
    return len(pages) or None


def _rel(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def check_call_requirements(
    requirements: dict[str, Any], project_root: Path, *, today: datetime.date | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    today = today or datetime.date.today()

    schema_errors = _schema.validate(requirements, CALL_REQUIREMENTS_SCHEMA)
    if schema_errors:
        return [
            Finding(
                severity="blocker",
                area="call",
                check_id="invalid_requirements_schema",
                file="call-requirements.yaml",
                message=message,
                evidence_refs=[],
                suggested_fix="Fix the call-requirements.yaml key/type; likely a typo.",
            )
            for message in schema_errors
        ]

    call = requirements.get("call") or {}
    deadline_raw = call.get("deadline")
    if deadline_raw:
        try:
            deadline = datetime.date.fromisoformat(str(deadline_raw))
        except ValueError:
            deadline = None
        if deadline is not None:
            warn_days = int(call.get("warn_days", 14))
            if deadline < today:
                findings.append(
                    Finding(
                        severity="blocker",
                        area="call",
                        check_id="deadline_passed",
                        file="call-requirements.yaml",
                        message=f"Submission deadline {deadline.isoformat()} has passed (today {today.isoformat()}).",
                        evidence_refs=[deadline.isoformat()],
                        suggested_fix="This call is closed; target the next round.",
                    )
                )
            elif (deadline - today).days <= warn_days:
                findings.append(
                    Finding(
                        severity="minor",
                        area="call",
                        check_id="deadline_near",
                        file="call-requirements.yaml",
                        message=f"Deadline {deadline.isoformat()} is in {(deadline - today).days} day(s).",
                        evidence_refs=[deadline.isoformat()],
                        suggested_fix="Finalize and submit soon.",
                    )
                )

    for section in requirements.get("sections") or []:
        section_id = str(section.get("id", "section"))
        required = bool(section.get("required", True))
        manuscript = section.get("manuscript")
        path = resolve_project_path(project_root, manuscript) if manuscript else None
        exists = bool(path and path.is_file())
        text = path.read_text(encoding="utf-8") if exists else ""
        words = word_count(text)

        if required and (not exists or words == 0):
            findings.append(
                Finding(
                    severity="blocker",
                    area="call",
                    check_id="missing_required_section",
                    file=_rel(path, project_root) if path else section_id,
                    message=f"Required section `{section_id}` is missing or empty.",
                    evidence_refs=[section_id],
                    suggested_fix="Write the section file declared in call-requirements.yaml.",
                )
            )
            continue
        if not exists:
            continue

        max_words = section.get("max_words")
        if max_words and words > int(max_words):
            findings.append(
                Finding(
                    severity="major",
                    area="call",
                    check_id="section_over_limit",
                    file=_rel(path, project_root),
                    message=f"Section `{section_id}` has {words} words (limit {max_words}).",
                    evidence_refs=[f"{words}/{max_words} words"],
                    suggested_fix="Trim the section to the call word limit.",
                )
            )
        min_words = section.get("min_words")
        if min_words and words < int(min_words):
            findings.append(
                Finding(
                    severity="minor",
                    area="call",
                    check_id="section_under_min",
                    file=_rel(path, project_root),
                    message=f"Section `{section_id}` has {words} words (minimum {min_words}).",
                    evidence_refs=[f"{words}/{min_words} words"],
                    suggested_fix="Expand the section to the expected minimum.",
                )
            )

        chars = char_count(text)
        max_chars = section.get("max_chars")
        if max_chars and chars > int(max_chars):
            findings.append(
                Finding(
                    severity="major",
                    area="call",
                    check_id="section_over_char_limit",
                    file=_rel(path, project_root),
                    message=f"Section `{section_id}` has {chars} chars (limit {max_chars}).",
                    evidence_refs=[f"{chars}/{max_chars} chars"],
                    suggested_fix="Trim the section to the call character limit.",
                )
            )
        min_chars = section.get("min_chars")
        if min_chars and chars < int(min_chars):
            findings.append(
                Finding(
                    severity="minor",
                    area="call",
                    check_id="section_under_char_min",
                    file=_rel(path, project_root),
                    message=f"Section `{section_id}` has {chars} chars (minimum {min_chars}).",
                    evidence_refs=[f"{chars}/{min_chars} chars"],
                    suggested_fix="Expand the section to the expected minimum length.",
                )
            )

    for annex in requirements.get("annexes") or []:
        annex_id = str(annex.get("id", "annex"))
        # v2: a conditional annex (required_if) with no explicit `required` is not
        # unconditionally required — the condition is evaluated by a later checker
        # (NASTROJ-C). Default such annexes to not-hard-required to avoid a false blocker.
        conditional = "required_if" in annex and "required" not in annex
        required = False if conditional else bool(annex.get("required", True))
        artifact = annex.get("artifact")
        path = resolve_project_path(project_root, artifact) if artifact else None
        exists = bool(path and path.exists())
        if conditional and not exists:
            findings.append(
                Finding(
                    severity="info",
                    area="call",
                    check_id="conditional_annex_deferred",
                    file=(_rel(path, project_root) if path else annex_id),
                    message=f"Conditional annex `{annex_id}` (required_if: {annex.get('required_if')}) not present; condition evaluated downstream.",
                    evidence_refs=[annex_id],
                    suggested_fix="Provide it if the condition holds for this application.",
                )
            )
        if required and not exists:
            findings.append(
                Finding(
                    severity="blocker",
                    area="call",
                    check_id="missing_required_annex",
                    file=(_rel(path, project_root) if path else annex_id),
                    message=f"Required annex `{annex_id}` is missing.",
                    evidence_refs=[annex_id],
                    suggested_fix="Add the required annex artifact or fix its path.",
                )
            )
        elif not required and not exists:
            findings.append(
                Finding(
                    severity="info",
                    area="call",
                    check_id="optional_annex_absent",
                    file=(_rel(path, project_root) if path else annex_id),
                    message=f"Optional annex `{annex_id}` is not present.",
                    evidence_refs=[annex_id],
                    suggested_fix="Add it if the call rewards it.",
                )
            )

        want_format = annex.get("format")
        if exists and want_format and path is not None:
            actual = path.suffix.lower().lstrip(".")
            if actual != str(want_format).lower():
                findings.append(
                    Finding(
                        severity="major",
                        area="call",
                        check_id="annex_wrong_format",
                        file=_rel(path, project_root),
                        message=f"Annex `{annex_id}` is `.{actual}` but the call requires `{want_format}`.",
                        evidence_refs=[f"{actual}!={want_format}"],
                        suggested_fix=f"Provide the annex as {want_format}.",
                    )
                )

        max_pages = annex.get("max_pages")
        if exists and max_pages and path is not None:
            pages = count_pdf_pages(path)
            if pages is None:
                findings.append(
                    Finding(
                        severity="info",
                        area="call",
                        check_id="annex_page_count_unknown",
                        file=_rel(path, project_root),
                        message=f"Could not determine page count of annex `{annex_id}` (limit {max_pages}).",
                        evidence_refs=[annex_id],
                        suggested_fix="Provide the annex as a readable PDF to enforce the page limit.",
                    )
                )
            elif pages > int(max_pages):
                findings.append(
                    Finding(
                        severity="major",
                        area="call",
                        check_id="annex_over_page_limit",
                        file=_rel(path, project_root),
                        message=f"Annex `{annex_id}` has {pages} pages (limit {max_pages}).",
                        evidence_refs=[f"{pages}/{max_pages} pages"],
                        suggested_fix="Shorten the annex to the call page limit.",
                    )
                )

    for criterion in requirements.get("eligibility") or []:
        criterion_id = str(criterion.get("id", "criterion"))
        # `computed` criteria are evaluated by check_eligibility.py (C6), not here.
        if criterion.get("computed"):
            continue
        met = bool(criterion.get("met", False))
        if not met:
            findings.append(
                Finding(
                    severity="major",
                    area="call",
                    check_id="eligibility_not_met",
                    file="call-requirements.yaml",
                    message=f"Eligibility criterion `{criterion_id}` is not met: {criterion.get('description', '')}.",
                    evidence_refs=[criterion_id],
                    suggested_fix="Resolve the eligibility gap before submission.",
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a proposal draft against a call's requirements framework.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--requirements", type=Path, default=Path("call-requirements.yaml"))
    parser.add_argument("--today", default=None, help="Reference date YYYY-MM-DD for the deadline check (default: today).")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    requirements_path = resolve_project_path(project_root, args.requirements)
    if not requirements_path.exists():
        print(f"Requirements file not found: {requirements_path}", file=_sys.stderr)
        return 1

    try:
        today = datetime.date.fromisoformat(args.today) if args.today else None
    except ValueError:
        print(f"Invalid --today date: {args.today}", file=_sys.stderr)
        return 1

    requirements = load_requirements(requirements_path)
    findings = check_call_requirements(requirements, project_root, today=today)
    blockers = [finding for finding in findings if finding.severity == "blocker"]

    if args.format == "json":
        print(
            json.dumps(
                {
                    "decision": "BLOCK" if blockers else "PASS",
                    "findings": [asdict(finding) for finding in findings],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Call requirements check: {'BLOCK' if blockers else 'PASS'}")
        for finding in findings:
            print(f"- {finding.severity} {finding.check_id}: {finding.message}")
        if not findings:
            print("- no findings (all required sections, annexes and eligibility satisfied)")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
