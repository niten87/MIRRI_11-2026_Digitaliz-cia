#!/usr/bin/env python3
"""Tests for the applicant profile registry helper. Dependency-free (dummy data)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("ap", _TOOL / "checks" / "applicant_profile.py")
ap = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(ap)

REGISTRY = """companies:
  acme:
    nazov_display: "ACME s. r. o."
    placeholders:
      ZIADATEL: "ACME s. r. o."
      ICO: "12345678"
      STATUTAR: "Jan Test"
    msp:
      zamestnanci: 8
      obrat_eur: 900000
      size_category: "mikro"
  beta:
    nazov_display: "Beta a. s."
    placeholders:
      ZIADATEL: "Beta a. s."
      ICO: "87654321"
"""


def _repo_with_registry(d: Path) -> Path:
    (d / "applicants").mkdir()
    (d / "applicants" / "companies.local.yaml").write_text(REGISTRY, encoding="utf-8")
    return d


def test_list_companies():
    with tempfile.TemporaryDirectory() as d:
        repo = _repo_with_registry(Path(d))
        companies = dict(ap.list_companies(repo))
    assert companies == {"acme": "ACME s. r. o.", "beta": "Beta a. s."}


def test_missing_registry_is_empty():
    with tempfile.TemporaryDirectory() as d:
        assert ap.load_registry(Path(d)) == {}
        assert ap.list_companies(Path(d)) == []


def test_write_reverse_key_contains_placeholders_and_msp():
    with tempfile.TemporaryDirectory() as d:
        repo = _repo_with_registry(Path(d))
        app = Path(d) / "app"
        out = ap.write_reverse_key("acme", app, repo)
        text = out.read_text(encoding="utf-8")
    assert out.name == "_anonymization-key.local.md"
    assert "`[ZIADATEL]` | ACME s. r. o." in text
    assert "`[ICO]` | 12345678" in text
    assert "zamestnanci: 8" in text
    assert "NECOMMITOVAŤ" in text


def test_unknown_company_raises():
    with tempfile.TemporaryDirectory() as d:
        repo = _repo_with_registry(Path(d))
        try:
            ap.write_reverse_key("nope", Path(d) / "app", repo)
        except KeyError:
            return
        raise AssertionError("expected KeyError for unknown company")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
