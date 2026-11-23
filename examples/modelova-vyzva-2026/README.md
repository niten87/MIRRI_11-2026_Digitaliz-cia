# Modelová výzva 2026 — vzorová žiadosť

Jedna grantová žiadosť ako priečinok. Nástroj (completeness check, QC, balenie) je
lokálny v `tool/`; tu je len obsah.

## Čo je čo
- `call-requirements.yaml` — rámec výzvy (povinné sekcie + limity, prílohy, deadline)
- `references/source-registry.yaml` — tvoje výstupy (track record), cituješ ich `[@key]`
- `manuscript/` — sekcie žiadosti
- `annexes/` — povinné prílohy (CV, vyhlásenie)
- `study_manifest.yaml` — cesty pre jednotný CLI

## Spustenie (z koreňa repa)
```bash
python3 tool/grant.py --project-root examples/modelova-vyzva-2026 check
python3 tool/grant.py --project-root examples/modelova-vyzva-2026 qc --mode pre_word
python3 tool/grant.py --project-root examples/modelova-vyzva-2026 build --target docx
```
