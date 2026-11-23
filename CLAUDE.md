# agentic-grantapp-framework — inštrukcie pre AI agenta

Toto repo je **framework na prípravu grantových žiadostí** (SK/EÚ výzvy). Klonuje/forkuje sa
ako základ pre každú novú výzvu. Tvoja práca tu má jediný cieľ: **finálne dokumenty musia
PRESNE spĺňať požiadavky príloh, textu výzvy a zákonné/schémové požiadavky** (princíp P7).

## Železné pravidlá (nikdy neporuš)
1. **Ground truth = oficiálne dokumenty výzvy** (`calls/<call>/source-md/oficialne/`).
   Dokumenty generuj VŽDY z tokenizovaných oficiálnych šablôn (`templates/opis/<call>/`,
   `templates/annexes/<call>/`) — nikdy ad-hoc prózou. Slovník tokenov: `docs/TOKENS.md`.
2. **Deterministická brána je arbiter.** LLM navrhuje, `tool/grant.py qc` rozhoduje.
   Nikdy neschvaľuj vlastný výstup; čísla (rozpočet, intenzity) počítajú checkery.
3. **Reálne PII/firemné údaje NIKDY do commitov.** Používaj placeholdre (`[ZIADATEL]`,
   `[ICO]`, `[OSOBA_1]`…); reálne hodnoty len v gitignored `*.local.md` / `*.local.yaml`
   (`applicants/companies.local.yaml`, `_anonymization-key.local.md`). Leak-scan to vynúti.
4. **Do nástroja (`tool/`) sa nezadrôtováva žiadny výzvový fakt** — všetka výzvová logika
   je dátová (`call-requirements.yaml`, tokenizované šablóny, `required-structure.yaml`).
5. **„Hotovo" = obidve QC brány čisté:** deterministická (`qc --mode final_publication
   --fail-on major`) aj agentická content-QC (`workflows/content-review.workflow.js`).

## Kľúčové príkazy
```bash
python3 tool/grant.py new-call <ČÍSLO>                       # kostra novej výzvy
python3 tool/grant.py new-application <ČÍSLO> <firma>        # kostra žiadosti
python3 tool/grant.py --project-root <app> build --target all    # Opis 2b + rozpočet 2c + všetky prílohy
python3 tool/grant.py --project-root <app> qc --mode final_publication --fail-on major
python3 tool/grant.py --project-root <app> tokens            # dostupné {{tokeny}}
python3 tool/grant.py applicant list|key --company <id>      # register firiem (gitignored)
for t in tool/tests/test_*.py; do python3 "$t"; done          # testy (všetky musia prejsť)
```

## Kedy čo robiť (rozcestník)
- **Nová výzva (po forku):** postupuj podľa `skills/onboard-call/SKILL.md`
  (scaffold → ingest → sémantická mapa → tokenizuj → podmienky → over);
  automatizovane cez `workflows/onboard-call.workflow.js`.
- **Nová/úprava žiadosti:** `skills/grant-prep/SKILL.md` (compliance-first postup)
  + `workflows/grant-prep.workflow.js` (celý beh s REVISE slučkou).
- **Kontrola kvality obsahu pred podaním:** `skills/content-review/SKILL.md`.
- **Architektúra a stav:** `docs/SPEC-grantapp.md`, `docs/BACKLOG-grantapp.md`, `HANDOVER.md`.

## Štruktúra
`tool/` nástroj (CLI+checkery, generický) · `calls/<call>/` znalostná báza výzvy ·
`templates/opis|annexes/<call>/` tokenizované oficiálne šablóny + `required-structure.yaml` ·
`applications/<call>-<firma>/` žiadosti (model `project.yaml` = single source of truth) ·
`applicants/` register firiem (reálne dáta gitignored) · `skills/`+`workflows/` agentika.

> Referenčná výzva `17I04-04-V05-RIS3` (+ žiadosti ELARA, PredictAI) slúži ako **vzor** —
> pri forku pre inú výzvu ju môžeš ponechať ako referenciu alebo odstrániť (viď `docs/FORKING.md`).

## Poučenie, ktoré stálo audit (neopakuj)
Negeneruj „pekné" dokumenty bez porovnania s oficiálnou šablónou — zelené výpočtové testy
≠ úplný dokument. `check_document_completeness` + `required-structure.yaml` sú poistka;
pri novej výzve ich VŽDY vytvor. Po zmenách vždy `build --target all` → `qc` → (ideálne)
content-review.
