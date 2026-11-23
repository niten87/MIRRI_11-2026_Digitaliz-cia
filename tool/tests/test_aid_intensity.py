#!/usr/bin/env python3
"""Tests for the aid-intensity checker (NASTROJ-C2). Dependency-free."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1]
if str(_TOOL) not in sys.path:
    sys.path.insert(0, str(_TOOL))
from grantlib.csvio import write_csv  # noqa: E402

_spec = importlib.util.spec_from_file_location("ci", _TOOL / "checks" / "check_aid_intensity.py")
ci = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(ci)

COLS = ["wp", "nazov_vydavku", "kategoria", "merna_jednotka", "pocet_jednotiek",
        "jednotkova_cena", "celkove_opravnene", "intenzita", "narokovane", "vecny_popis"]

AID = {
    "base_rate": 0.25,
    "size_uplift": {"mikro": 0.20, "maly": 0.20, "stredny": 0.10, "velky": 0.0},
    "region_uplift": 0.15, "call_cap": 0.60, "scheme_cap": 0.80, "regime_B_fixed": 0.60,
}


def brow(cov, nar):
    return {"wp": "3-1", "nazov_vydavku": "x", "kategoria": "521", "merna_jednotka": "os",
            "pocet_jednotiek": "1", "jednotkova_cena": str(cov), "celkove_opravnene": str(cov),
            "intenzita": "", "narokovane": str(nar), "vecny_popis": ""}


def _run(rows, regime="A", miesto="Košice", size="maly", aid=None):
    reqs = {"version": 2, "call": {"regime": regime},
            "budget": {"file": "budget/rozpocet.csv"}, "aid_intensity": aid or AID}
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write_csv(root / "budget" / "rozpocet.csv", COLS, rows)
        (root / "project.yaml").write_text(
            f"project:\n  regime: \"{regime}\"\n  miesto_realizacie: \"{miesto}\"\n"
            f"applicant:\n  msp:\n    size_category: \"{size}\"\n", encoding="utf-8")
        return ci.check_aid_intensity(reqs, root)


def ids(f):
    return {x.check_id for x in f}


# maly + Košice → 0.25+0.20+0.15 = 0.60 (== call_cap)
def test_valid_intensity_no_blocker_or_major():
    f = _run([brow(400000, 240000), brow(100000, 60000), brow(100000, 60000)])
    assert not any(x.severity in ("blocker", "major") for x in f)
    assert "effective_intensity" in ids(f)


def test_narokovane_mismatch_is_major():
    f = _run([brow(400000, 250000), brow(100000, 60000), brow(100000, 60000)])
    assert any(x.check_id == "narokovane_mismatch" and x.severity == "major" for x in f)


def test_over_cap_is_blocker():
    # narokovane at 0.70 while effective 0.60 → over the call cap
    f = _run([brow(400000, 280000), brow(100000, 70000), brow(100000, 70000)])
    assert any(x.check_id == "intensity_over_cap" and x.severity == "blocker" for x in f)


def test_bratislava_drops_region_uplift():
    # BA → 0.25+0.20 = 0.45; rows at 0.45 are valid, rows at 0.60 mismatch
    ok = _run([brow(400000, 180000)], miesto="Bratislava")
    assert not any(x.severity in ("blocker", "major") for x in ok)
    bad = _run([brow(400000, 240000)], miesto="Bratislava")
    assert any(x.check_id == "narokovane_mismatch" for x in bad)


def test_mimo_bratislavy_keeps_region_uplift():
    # "mimo Bratislavského kraja" contains the substring "bratislav" but is OUTSIDE BA
    f = _run([brow(400000, 240000)], miesto="[MIESTO] – mimo Bratislavského kraja")
    assert not any(x.severity in ("blocker", "major") for x in f)  # 0.60 applied → row matches


def test_regime_B_fixed_60():
    ok = _run([brow(500000, 300000)], regime="B", size="")
    assert not any(x.severity == "blocker" for x in ok)
    bad = _run([brow(500000, 250000)], regime="B", size="")
    assert any(x.check_id == "regimeB_not_fixed_60" and x.severity == "blocker" for x in bad)


def test_unknown_size_is_blocker():
    f = _run([brow(400000, 240000)], size="obrovsky")
    assert any(x.check_id == "size_unknown" and x.severity == "blocker" for x in f)


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
