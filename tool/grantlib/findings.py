"""Shared QC finding type and severity ordering.

Field order matches the framework's check convention
(``severity, area, check_id, file, message, evidence_refs, suggested_fix``) so
existing positional construction sites migrate without changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "blocker": 3}


@dataclass
class Finding:
    severity: str
    area: str
    check_id: str
    file: str
    message: str
    evidence_refs: list[str] = field(default_factory=list)
    suggested_fix: str = ""
