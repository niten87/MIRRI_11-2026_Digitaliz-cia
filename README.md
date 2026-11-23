# agentic-grantapp-framework

Agentický framework na prípravu **žiadostí o granty/dotácie** (SK/EÚ) — s dôrazom na
výpočty (rozpočet, intenzity pomoci, spolufinancovanie), formátovanie, sémantiku a
automatické dohľadanie relevantnej legislatívy zodpovedných inštitúcií.

Princíp: **nástroj vs. obsah.** Deterministický nástroj (grantový completeness check, QC
brána, balenie) žije lokálne v `tool/` a je výzvovo-neutrálny. Obsah (jednotlivé žiadosti,
znalostné bázy výziev) je oddelený. Grantová logika sa **zámerne nemieša** s výskumným
frameworkom — nástroj je sebestačný, bez submodulov.

> Návrh celého systému: **`docs/SPEC-grantapp.md`** · plán prác: **`docs/BACKLOG-grantapp.md`**.

## Štruktúra
```
tool/                              # NÁSTROJ (lokálny, sebestačný)
  grant.py                         # CLI: check | qc | package | build
  grantlib/  checks/               # plumbing + grantové checkery
templates/
  call-requirements-template.yaml      # rámec výzvy v1 (aktívny)
  call-requirements-v2-template.yaml    # cieľová schéma v2 (budget/intenzity/indikátory)
  project-template.yaml  legislation-template.yaml
calls/
  17I04-04-V05-RIS3/               # znalostná báza výzvy (source-md, SEMANTIC-MAP, …)
examples/
  modelova-vyzva-2026/             # vzorová žiadosť (jeden priečinok = jedna žiadosť)
applications/                      # konkrétne žiadosti (klon examples/)
applicants/                        # register profilov firiem (reálne dáta gitignored)
workflows/  skills/                # agentická orchestrácia (grant-prep)
```

## Prvé použitie
```bash
git clone https://github.com/pbielik/agentic-grantapp-framework.git
cd agentic-grantapp-framework
python3 tool/grant.py --project-root examples/modelova-vyzva-2026 check
```

## Fork pre novú výzvu (agent-friendly)
Repo je základ, ktorý sa **forkuje a rozširuje o ďalšie výzvy**. Každá výzva sa pridáva rovnakým
opakovateľným postupom (scaffold → tokenizuj oficiálne šablóny → zakóduj podmienky → over):
```bash
# 1) kostra novej výzvy (calls/ + templates/opis/ + templates/annexes/)
python3 tool/grant.py new-call <ČÍSLO-VÝZVY>

# 2) ingestuj oficiálne dokumenty, tokenizuj Opis 2b + prílohy (slovník: docs/TOKENS.md),
#    vyplň required-structure.yaml a call-requirements.yaml  — postup: skills/onboard-call/SKILL.md

# 3) kostra konkrétnej žiadosti
python3 tool/grant.py new-application <ČÍSLO-VÝZVY> <firma>
```
- **Postup pre novú výzvu:** `skills/onboard-call/SKILL.md`
- **Slovník tokenov** do šablôn: `docs/TOKENS.md` (alebo `grant.py --project-root <app> tokens`)
- **Východiskové šablóny:** `templates/_starters/`

## Príprava žiadosti
```bash
python3 tool/grant.py --project-root <app> build --target all   # Opis 2b + rozpočet 2c + všetky prílohy
python3 tool/grant.py --project-root <app> qc --mode final_publication --fail-on major
```
Celý per-žiadosť beh (vrátane agentickej content-QC) cez `workflows/grant-prep.workflow.js`
(skill `skills/grant-prep/`). „Hotovo" = **obidve brány** (deterministická + `content-review`) čisté.

## Zásady
- Súkromné dáta (reálne žiadosti, rozpočty) sem patria len **anonymizované**; reverzný kľúč
  (`*_.local.md`) je gitignored a nikdy sa necommituje.
- Nástroj (`tool/`) je výzvovo-neutrálny — **žiadny výzvový fakt sa nezadrôtováva** do kódu;
  všetko ide cez `call-requirements.yaml` / `project.yaml` / `legislation.yaml`.
