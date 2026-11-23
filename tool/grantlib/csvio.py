"""CSV read/write helpers shared across framework scripts."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def read_csv_rows(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV into (fieldnames, rows) with empty cells normalized to ``""``."""
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return (
            list(reader.fieldnames or []),
            [{key: (value or "") for key, value in row.items()} for row in reader],
        )


def read_rows(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a tabular file as (fieldnames, rows); dispatches CSV vs XLSX on suffix."""
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xlsm"}:
        from .xlsxio import read_xlsx_rows  # local import to avoid hard coupling
        return read_xlsx_rows(p)
    return read_csv_rows(p)


def write_csv(path: str | Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Write `rows` to `path` (creating parent dirs) with LF line endings."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
