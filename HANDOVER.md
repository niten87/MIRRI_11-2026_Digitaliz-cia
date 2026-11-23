# HANDOVER — pre ďalšiu session / coding AI agenta

Tento súbor hovorí novej session (alebo AI agentovi), **v akom stave repo je a čo robiť ďalej**.

## Kontext
- Repo `agentic-grantapp-framework` = **nástroj + obsah v jednom repe** (žiadny submodule).
  Nástroj (grantový completeness check, QC brána, balenie) žije lokálne v `tool/` a je
  výzvovo-neutrálny; obsah (žiadosti, znalostné bázy výziev) je oddelený.
- Research submodule `vendor/framework` bol **odpojený** (NASTROJ-0, 2026-07-08) —
  grantová logika sa nemieša s výskumným frameworkom.

## Návrh top-class frameworku (2026-07-08) — ZAČNI TU pri implementácii
- **`docs/SPEC-grantapp.md`** — plná špecifikácia agentického frameworku (dátový model
  `call-requirements` v2, 9-fázová pipeline, výpočtový modul rozpočtu/intenzít, modul
  externých SK/EU zdrojov, rozšírené QC brány, anonymizácia, akceptačné kritériá „hotovo").
- **`docs/BACKLOG-grantapp.md`** — epiky → user stories s akceptačnými kritériami, rozdelené
  na **NÁSTROJ** (lokálny balík `tool/` v tomto repe) a **OBSAH** (calls/applications/…),
  priority P0/P1/P2, míľniky M0–M3. Kritická cesta: NASTROJ-0 (založ `tool/`) → schéma v2 →
  `xlsxio` → `check_budget`/`check_aid_intensity` → agregácia QC.
- **Architektonické rozhodnutie (2026-07-08) — HOTOVO (NASTROJ-0):** deterministický grantový
  nástroj NEžije v research submodule — grantová logika sa nemieša s `agentic-research-framework`.
  Nástroj je teraz lokálny v `tool/` (`grantlib` + `checks` + `grant.py`); research submodule
  `vendor/framework` bol odpojený. `tool/grant.py … check|qc` funguje sebestačne (overené na
  `examples/modelova-vyzva-2026` = PASS bez `vendor/framework`).
- **Šablóny v2** (nové, neprepisujú funkčnú v1): `templates/call-requirements-v2-template.yaml`,
  `templates/project-template.yaml`, `templates/legislation-template.yaml`.
- **Orchestrácia:** `workflows/grant-prep.workflow.js` (per-žiadosť F5–F9 + REVISE loop) a
  `skills/grant-prep/SKILL.md` (+ `skills/README.md` — katalóg 9 skillov).
- Pozn.: v2 šablóna sa NEspúšťa cez `tool/grant.py check`, kým nedorazí NASTROJ-A (nová schéma);
  dovtedy platí v1 `templates/call-requirements-template.yaml` (beží cez `tool/grant.py check`).

## Čo už je hotové (2026-07-08)
- Spracovaná **výzva 17I04-04-V05 (RIS3, Komponent 17, Plán obnovy)** do znalostnej bázy:
  `calls/17I04-04-V05-RIS3/`.
  - `source-md/oficialne/` — 14 oficiálnych dokumentov výzvy (verejné) v markdowne (1:1).
  - `source-md/ziadatel/` — 6 dokumentov žiadateľa, **anonymizované** (placeholdre).
  - `SEMANTIC-MAP.md` — inventár dokumentov, kľúčové fakty výzvy, vzťahy, kandidáti na `call-requirements.yaml`. **Začni tu.**
  - `ANONYMIZATION.md` — schéma placeholderov; reálne hodnoty sú v `_anonymization-key.local.md` (gitignored).
- Vzorová (demo) žiadosť ostáva v `examples/modelova-vyzva-2026/` ako referencia štruktúry.

## Poučenie z auditu (2026-07-09) — compliance-first (P7)
- **Chyba, ktorej sa vyhni:** negeneruj dokumenty ad-hoc (len próza + jedna tabuľka). Opis 2b
  bol pôvodne neúplný (chýbali povinné hlavičkové tabuľky, intenzita, indikátory; tabuľky sa
  rozpadli na text). Zelené výpočtové testy ≠ úplný/vyhovujúci dokument.
- **Systémová poistka:** `check_document_completeness.py` porovnáva built dokumenty s oficiálnou
  šablónou (`templates/opis/<call>/required-structure.yaml`) — beží vo `final_publication` bráne.
  Pribudli aj `check_timeline.py` (časová oprávnenosť) a rozšírená `eligibility` (DNSH, dvojité
  financovanie, bezúhonnosť/EDES/podnik v ťažkostiach, OR zápis, max 1 žiadosť).
- **Disciplína:** generuj z oficiálnych tokenizovaných šablôn (`templates/opis/`, `templates/annexes/`),
  `build --target all` → `qc --mode final_publication --fail-on major` musí prejsť. Viď `skills/grant-prep/SKILL.md`
  a SPEC princíp P7. Pri novej výzve vytvor `required-structure.yaml` a zakóduj všetky tvrdé podmienky.

## Vyriešené obmedzenie (2026-07-08)
- `source-md/ziadatel/…opis-projektu-ziadatel-fin.md` bol pôvodne prázdny (PDF chránené heslom).
  PDF je **odheslované**, skonvertované a **anonymizované** → teraz obsahuje 23 s. reálne
  vyplnenej žiadosti (referenčný „gold" Opis). Reálne hodnoty len v gitignored kľúči.
- **Validácia frameworku:** reálna žiadosť potvrdzuje náš model (intenzita 25+20+15=60 %,
  kategórie 521/518/551/920, paušál 20 %, štruktúra indikátorov). Naše checkery by v nej
  našli aj reálne chyby: top-line nesúlad 0,18 € (`check_cross_document_consistency`),
  naratívny nesúlad paušálu (`check_budget`), preklep dátumu míľnika M9 (2025 vs 2026).

## Čo robiť ďalej (postup)
1. **Prečítaj** `calls/17I04-04-V05-RIS3/SEMANTIC-MAP.md` (celý obraz výzvy).
2. **Založ projekt žiadosti** (jeden priečinok = jedna žiadosť):
   ```bash
   cp -R examples/modelova-vyzva-2026 elara-ai-17I04-04-V05
   ```
3. **Zostav `call-requirements.yaml`** pre túto výzvu z faktov v SEMANTIC-MAP (sekcie
   Opisu projektu + limity 300 k–2,2 M € bez DPH + deadline 30.6.2026 + povinné prílohy
   + eligibility MSP/RIS3/neprekrývanie s Komp. 9). Šablóna: `templates/call-requirements-template.yaml`.
4. **Píš sekcie** `manuscript/` podľa štruktúry Opisu projektu (šablóna `2b`), čerpaj
   z `source-md/ziadatel/` (vedúce osoby, MSP, …). **Nechaj placeholdre** — reálne
   údaje sa doplnia až pri finalizácii z `_anonymization-key.local.md`.
5. **Priebežne kontroluj** cez lokálny nástroj:
   ```bash
   python3 tool/grant.py --project-root elara-ai-17I04-04-V05 check
   python3 tool/grant.py --project-root elara-ai-17I04-04-V05 qc --mode pre_word
   python3 tool/grant.py --project-root elara-ai-17I04-04-V05 build --target docx   # (build: stub, NASTROJ-D4)
   ```

## Zásady
- **Anonymizácia:** v repe zostávajú placeholdre; reálne firemné/osobné údaje nikdy
  necommituj (lokálny kľúč je gitignored). Nové citlivé údaje anonymizuj rovnakou schémou.
- **Zdroj pravdy** pre podmienky výzvy je `source-md/oficialne/01-…-vyzva.md` a `SEMANTIC-MAP.md`.
- Ako sa píše žiadosť (štýl/obsah) rieši ďalšia session — táto pripravila len znalostnú bázu.
