# tool/ — lokálny grantový nástroj (vrstva NÁSTROJ)

Deterministický, výzvovo-neutrálny nástroj pre grantové žiadosti. Žije **lokálne v tomto
repe** — grantová logika sa zámerne nemieša s výskumným frameworkom (viď `docs/SPEC-grantapp.md`,
architektonické rozhodnutie v `HANDOVER.md`).

```
tool/
  grant.py            # CLI: check | qc | package | build(stub)
  grantlib/           # dependency-free plumbing: findings, schema, yamllite, csvio, paths
  checks/
    check_call_requirements.py   # grantový completeness gate (rámec výzvy)
    run_grant_qc.py              # slim grantový QC agregátor (BLOCK/REVISE/PASS)
    build_submission_package.py  # balenie (visibility gate + path-traversal ochrana)
```

## Použitie
```bash
python3 tool/grant.py --project-root <app> check                 # rámec výzvy
python3 tool/grant.py --project-root <app> qc --mode pre_word     # agregovaná brána
python3 tool/grant.py --project-root <app> package --manifest submission-manifest.csv
```

## Pôvod / atribúcia
`grantlib/` a `check_call_requirements.py` / `build_submission_package.py` boli pôvodne
súčasťou [`agentic-research-framework`](https://github.com/pbielik/agentic-research-framework)
(moduly `frameworklib`, `scripts/`). Sú to malé bezzávislé moduly (iba štandardná knižnica),
preto sú tu skopírované a udržiavané lokálne; balík `frameworklib` bol premenovaný na `grantlib`.
Research submodule bol odpojený (NASTROJ-0).

## Roadmapa (BACKLOG NASTROJ-A..D)
- schéma `call-requirements` v2 (budget/aid_intensity/indicators/consistency)
- `grantlib/xlsxio.py` + checkery `check_budget`, `check_aid_intensity`, `check_indicators`,
  `check_cross_document_consistency`, `check_anonymization_leaks`, `check_eligibility`
- `build` (render DOCX/XLSX z modelu) — dnes stub
