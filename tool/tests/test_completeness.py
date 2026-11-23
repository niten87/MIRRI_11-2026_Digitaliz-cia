#!/usr/bin/env python3
"""Tests for the document structural-completeness gate (NASTROJ-C7)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))

_spec = importlib.util.spec_from_file_location("cc", _TOOL / "checks" / "check_document_completeness.py")
cc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cc)

CALL = "17I04-04-V05"


def _setup(tmp: Path, opis_text: str | None):
    repo = tmp / "repo"
    proj = tmp / "proj"
    (repo / "templates" / "opis" / CALL).mkdir(parents=True)
    (repo / "templates" / "opis" / CALL / "required-structure.yaml").write_text(
        "documents:\n  - name: \"Opis\"\n    built: \"publication/opis.md\"\n    severity: \"major\"\n"
        "    required_markers:\n      - \"Identifikácia žiadateľa\"\n      - \"Intenzita pomoci\"\n      - \"DNSH\"\n",
        encoding="utf-8")
    proj.mkdir()
    (proj / "call-requirements.yaml").write_text(f"version: 2\ncall:\n  number: \"{CALL}\"\n", encoding="utf-8")
    if opis_text is not None:
        (proj / "publication").mkdir()
        (proj / "publication" / "opis.md").write_text(opis_text, encoding="utf-8")
    return repo, proj


def test_complete_document_passes():
    with tempfile.TemporaryDirectory() as d:
        repo, proj = _setup(Path(d), "Identifikácia žiadateľa ... Intenzita pomoci ... DNSH ...")
        f = cc.check_document_completeness(proj, repo_root=repo)
    assert not any(x.severity in ("major", "blocker") for x in f)


def test_missing_section_flagged():
    with tempfile.TemporaryDirectory() as d:
        repo, proj = _setup(Path(d), "Identifikácia žiadateľa ... Intenzita pomoci ...")  # DNSH missing
        f = cc.check_document_completeness(proj, repo_root=repo)
    assert any(x.check_id == "required_section_missing" and "DNSH" in x.message for x in f)


def test_unbuilt_document_is_info_not_failure():
    with tempfile.TemporaryDirectory() as d:
        repo, proj = _setup(Path(d), None)  # nothing built
        f = cc.check_document_completeness(proj, repo_root=repo)
    assert any(x.check_id == "document_not_built" for x in f)
    assert not any(x.severity in ("major", "blocker") for x in f)


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
