#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {"package_path", "source_path", "include", "required", "visibility", "artifact_type", "notes"}
SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "blocker": 3}
TRUE_VALUES = {"true", "yes", "y", "1", "include", "required"}
FALSE_VALUES = {"false", "no", "n", "0", "skip", "optional", ""}
PUBLIC_VISIBILITY = "public"


import sys as _sys
from pathlib import Path as _BootPath
_root = _BootPath(__file__).resolve()
while not (_root / "grantlib" / "__init__.py").exists() and _root != _root.parent:
    _root = _root.parent
if str(_root) not in _sys.path:
    _sys.path.append(str(_root))
from grantlib.findings import Finding  # noqa: E402


@dataclass
class PackageItem:
    package_path: str
    source_path: str
    visibility: str
    artifact_type: str
    notes: str


@dataclass
class SubmissionPackageResult:
    dry_run: bool
    project_root: str
    manifest: str
    output_dir: str
    included_count: int
    skipped_count: int
    package_items: list[dict[str, str]]


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [{key: value or "" for key, value in row.items()} for row in reader]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_bool(raw: str) -> bool | None:
    lowered = raw.strip().lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    return None


def resolve_project_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def is_safe_package_path(raw_path: str) -> bool:
    path = Path(raw_path)
    if not raw_path.strip() or path.is_absolute():
        return False
    return ".." not in path.parts


def validate_submission_manifest(
    manifest_path: Path,
    *,
    project_root: Path,
) -> tuple[list[Finding], list[PackageItem], int]:
    findings: list[Finding] = []
    package_items: list[PackageItem] = []
    skipped_count = 0

    if not manifest_path.exists():
        return [
            Finding(
                severity="blocker",
                area="submission",
                check_id="missing_submission_manifest",
                file=str(manifest_path),
                message="Submission manifest does not exist.",
                evidence_refs=[str(manifest_path)],
                suggested_fix="Create publication/submission_manifest.csv or pass a different manifest path.",
            )
        ], [], 0

    columns, rows = read_csv_rows(manifest_path)
    missing_columns = sorted(REQUIRED_COLUMNS - set(columns))
    if missing_columns:
        return [
            Finding(
                severity="blocker",
                area="submission",
                check_id="submission_manifest_missing_columns",
                file=str(manifest_path),
                message=f"Submission manifest is missing columns: {', '.join(missing_columns)}.",
                evidence_refs=[str(manifest_path)],
                suggested_fix="Use the framework submission manifest columns.",
            )
        ], [], 0

    seen_package_paths: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        include = parse_bool(row.get("include", ""))
        required = parse_bool(row.get("required", ""))
        visibility = row.get("visibility", "").strip().lower()
        package_path = row.get("package_path", "").strip()
        raw_source_path = row.get("source_path", "").strip()

        if include is None:
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_invalid_include",
                    file=str(manifest_path),
                    message=f"Row {row_number} has invalid include flag `{row.get('include', '')}`.",
                    evidence_refs=[f"{manifest_path}:{row_number}"],
                    suggested_fix="Use true/false for include.",
                )
            )
            include = False
        if required is None:
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_invalid_required",
                    file=str(manifest_path),
                    message=f"Row {row_number} has invalid required flag `{row.get('required', '')}`.",
                    evidence_refs=[f"{manifest_path}:{row_number}"],
                    suggested_fix="Use true/false for required.",
                )
            )
            required = False

        if not include:
            skipped_count += 1
            continue

        if visibility != PUBLIC_VISIBILITY:
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_restricted_included",
                    file=str(manifest_path),
                    message=f"Included artifact `{raw_source_path}` is marked visibility `{visibility or 'missing'}`.",
                    evidence_refs=[f"{manifest_path}:{row_number}"],
                    suggested_fix="Mark the artifact public only if it is safe to publish, otherwise set include=false.",
                )
            )

        if not is_safe_package_path(package_path):
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_unsafe_package_path",
                    file=str(manifest_path),
                    message=f"Package path `{package_path}` is empty, absolute, or escapes the package root.",
                    evidence_refs=[f"{manifest_path}:{row_number}"],
                    suggested_fix="Use a relative package path without `..`.",
                )
            )
            continue

        if package_path in seen_package_paths:
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_duplicate_package_path",
                    file=str(manifest_path),
                    message=f"Package path `{package_path}` appears more than once.",
                    evidence_refs=[f"{manifest_path}:{seen_package_paths[package_path]}", f"{manifest_path}:{row_number}"],
                    suggested_fix="Use one row per package path.",
                )
            )
        seen_package_paths[package_path] = row_number

        source_path = resolve_project_path(project_root, raw_source_path)
        if not is_inside(source_path, project_root):
            findings.append(
                Finding(
                    severity="blocker",
                    area="submission",
                    check_id="submission_source_outside_project",
                    file=str(manifest_path),
                    message=f"Source path `{raw_source_path}` is outside the project root.",
                    evidence_refs=[f"{manifest_path}:{row_number}", str(source_path)],
                    suggested_fix="Use a source artifact inside the project repository.",
                )
            )
            continue
        if not source_path.is_file():
            severity = "blocker" if required else "major"
            findings.append(
                Finding(
                    severity=severity,
                    area="submission",
                    check_id="submission_source_missing",
                    file=str(manifest_path),
                    message=f"Submission source `{raw_source_path}` does not exist.",
                    evidence_refs=[f"{manifest_path}:{row_number}", str(source_path)],
                    suggested_fix="Generate the artifact or set include=false if it is not part of this package.",
                )
            )
            continue

        package_items.append(
            PackageItem(
                package_path=package_path,
                source_path=str(source_path),
                visibility=visibility,
                artifact_type=row.get("artifact_type", "").strip(),
                notes=row.get("notes", "").strip(),
            )
        )
    return findings, package_items, skipped_count


def summarize(findings: list[Finding]) -> dict[str, int]:
    summary = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        summary[finding.severity] = summary.get(finding.severity, 0) + 1
    return summary


def has_failure(findings: list[Finding], fail_on: str) -> bool:
    threshold = SEVERITY_ORDER[fail_on]
    return any(SEVERITY_ORDER.get(finding.severity, 0) >= threshold for finding in findings)


def build_submission_package(
    *,
    project_root: Path,
    manifest_path: Path,
    output_dir: Path,
    dry_run: bool = False,
    fail_on: str = "blocker",
) -> tuple[SubmissionPackageResult, list[Finding]]:
    findings, package_items, skipped_count = validate_submission_manifest(manifest_path, project_root=project_root)
    if has_failure(findings, fail_on):
        return (
            SubmissionPackageResult(
                dry_run=dry_run,
                project_root=str(project_root),
                manifest=str(manifest_path),
                output_dir=str(output_dir),
                included_count=0,
                skipped_count=skipped_count,
                package_items=[],
            ),
            findings,
        )

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for item in package_items:
            destination = output_dir / item.package_path
            if not is_inside(destination, output_dir):
                findings.append(
                    Finding(
                        severity="blocker",
                        area="submission",
                        check_id="submission_destination_outside_package",
                        file=str(manifest_path),
                        message=f"Destination `{destination}` escapes output dir.",
                        evidence_refs=[str(destination)],
                        suggested_fix="Use a safe relative package path.",
                    )
                )
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source_path, destination)
        if not has_failure(findings, fail_on):
            write_csv(
                output_dir / "package_manifest.csv",
                ["package_path", "visibility", "artifact_type", "notes"],
                [
                    {
                        "package_path": item.package_path,
                        "visibility": item.visibility,
                        "artifact_type": item.artifact_type,
                        "notes": item.notes,
                    }
                    for item in package_items
                ],
            )

    return (
        SubmissionPackageResult(
            dry_run=dry_run,
            project_root=str(project_root),
            manifest=str(manifest_path),
            output_dir=str(output_dir),
            included_count=len(package_items),
            skipped_count=skipped_count,
            package_items=[asdict(item) for item in package_items],
        ),
        findings,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a public submission package from an explicit package manifest.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path("publication/submission_manifest.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("publication/submission_package"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-on", choices=sorted(SEVERITY_ORDER, key=SEVERITY_ORDER.get), default="blocker")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    result, findings = build_submission_package(
        project_root=project_root,
        manifest_path=resolve_project_path(project_root, args.manifest),
        output_dir=resolve_project_path(project_root, args.output_dir),
        dry_run=args.dry_run,
        fail_on=args.fail_on,
    )
    payload: dict[str, Any] = {
        "ok": not has_failure(findings, args.fail_on),
        "summary": summarize(findings),
        "result": asdict(result),
        "findings": [asdict(finding) for finding in findings],
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        status = "planned" if args.dry_run else "built"
        print(f"Submission package {status}: {result.output_dir}")
        print(f"Included artifacts: {result.included_count}; skipped rows: {result.skipped_count}")
        for finding in findings:
            print(f"{finding.severity.upper()} {finding.check_id}: {finding.message}")
            print(f"  evidence: {', '.join(finding.evidence_refs)}")
    return 1 if has_failure(findings, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
