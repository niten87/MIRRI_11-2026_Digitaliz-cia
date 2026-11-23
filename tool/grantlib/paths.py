"""Path helpers shared across framework scripts."""
from __future__ import annotations

from pathlib import Path


def resolve_project_path(project_root: Path, path: str | Path) -> Path:
    """Resolve `path` against `project_root` unless it is already absolute."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate


def find_framework_root(start: str | Path | None = None) -> Path:
    """Walk upward from `start` (or this file) to the framework root.

    The root is the directory that contains the `grantlib` package.
    """
    root = Path(start or __file__).resolve()
    while not (root / "grantlib" / "__init__.py").exists() and root != root.parent:
        root = root.parent
    return root
