# BACKLOG — Agentický framework pre grantové žiadosti (`agentic-grantapp-framework`)

**Verzia backlogu:** 1.0 · **Zdroj:** SPEC 1.0 + analýzy · **Dátum:** 2026-07-08
**Referenčná výzva:** `17I04-04-V05-RIS3`
**Legenda vrstiev:** `vrstva: nástroj` = lokálny balík `tool/` v tomto repe (výzvovo-neutrálny checker/builder, oddelený od obsahu) · `vrstva: obsah` = tento repozitár (`agentic-grantapp-framework`).
**Legenda priorít:** `P0` = nevyhnutné pre prvý end-to-end beh QC brány · `P1` = potrebné pre „hotovú" žiadosť podľa §9 · `P2` = kvalita/robustnosť/pohodlie.

> **Pravidlo hranice (P1 zo SPEC):** do nástroja sa NIKDY nezadrôtováva žiadny výzvový fakt. Grant-špecifická logika = iba dátami riadené pravidlá v `call-requirements.yaml`/`legislation.yaml` + generické check-loopy v nástroji.

---

## IMPLEMENTAČNÝ STAV (k 2026-07-09) — jadro HOTOVÉ

Framework je funkčný, otestovaný (**78 testov**) a na `main`. Overený **dvoma nezávislými auditmi**
(45 → 0 blockerov) a **agentickou content-QC**. Hotové:

- **Nástroj `tool/`** (lokálny, bez submodulu): schéma `call-requirements` v2, jednotné CLI (`grant.py`).
- **Deterministické checkery:** call-requirements, budget, aid-intensity, indicators, cross-document
  consistency, MSP + **VaV eligibility (computed)**, timeline (časová oprávnenosť), legislation freshness,
  **document completeness** (štruktúra vs oficiálna šablóna), anonymization leak-scan.
- **Generovanie celého balíka:** `build --target all` → Opis 2b (DOCX, plná štruktúra z tokenizovanej
  oficiálnej šablóny), rozpočet 2c (XLSX, blokový layout po WP s TRL a medzisúčtami + paušál per WP),
  **7 príloh** (čestné vyhlásenie, MSP, výpis RT, Príloha 5, ISPO, životopisy, doklad o VaV).
- **Dvoj-bránový QC model:** (1) deterministická brána (`qc`) — čísla/štruktúra/compliance; (2) **agentická
  content-QC** (`content-review` skill + workflow) — relevancia/kvalita/compliance obsahu voči kritériám výzvy.
- **Obsah:** register žiadateľov (`applicants/`), retrieval legislatívy + freshness, anonymizácia + reverzný kľúč,
  dve referenčné žiadosti (`applications/…-elara`, `…-predictai`) — obe štruktúrne kompletné a súladné.
- **Princíp P7 (SPEC):** finálne dokumenty MUSIA presne spĺňať prílohy/výzvu/zákon; generuje sa z oficiálnych
  šablôn + completeness gate. Skills/inštrukcie sú compliance-first.

**Zostáva (per-žiadosť, na strane žiadateľa):** reálne dáta do `[DOPLNIŤ]` značiek (metodika, CV, pilot,
trhové čísla) na zvýšenie obsahového ratingu; reálne firemné údaje z `applicants/` pre finalizáciu.

---

## Prehľad EPIC-ov

| Epic | Názov | Vrstva | Ťažisko |
|------|-------|--------|---------|
| **NASTROJ-A** | Lokálny balík `tool/` (NASTROJ-0) + rozšírená schéma `call-requirements` v2 | nástroj | založenie `tool/` a odpojenie submodulu; schema.py bloky budget/aid_intensity/indicators/consistency |
| **NASTROJ-B** | XLSX I/O (`xlsxio.py`) | nástroj | bezzávislý čítač/zapisovač rozpočtu |
| **NASTROJ-C** | Deterministické checkery (budget/aid-intensity/indicators/cross-doc/leaks) | nástroj | výpočtový modul §4, krížové kontroly §6.3 |
| **NASTROJ-D** | Agregácia QC + CLI + build/package | nástroj | run_framework_qc, grant.py subkomandy, build/leak-scan |
| **OBSAH-E** | Šablóny (call-req v2, project, legislation, manifest, Opis) | obsah | templates/ + path-kľúče manifestu |
| **OBSAH-F** | Agentické skills + `/workflows` orchestrácia | obsah | 9 skillov, 9-fázová pipeline |
| **OBSAH-G** | Call-ingestion pipeline + knowledge base | obsah | ingest, SEMANTIC-MAP, locked-source handling |
| **OBSAH-H** | Register externých zdrojov + retrieval playbook | obsah | legislation-retrieval, pinning, freshness |
| **OBSAH-I** | Anonymizácia (helper, schéma, gitignore) | obsah | ANONYMIZATION.md, kľúč, integrácia s leak-scanom |
| **OBSAH-J** | Klonovateľný skeleton žiadosti + demo | obsah | examples/, applications/ |

---

# NASTROJ-A — Rozšírená schéma `call-requirements` v2 (vrstva: nástroj)

Rozširuje `CALL_REQUIREMENTS_SCHEMA` v `tool/checks/check_call_requirements.py` o nové top-level bloky pri zachovaní `allow_unknown: False`. Existujúce bloky ostávajú spätne kompatibilné.

> **Status (2026-07-08) — schéma v2 HOTOVÁ (A1–A6, schema-level):** `check_call_requirements.py`
> prijíma bloky `budget`/`aid_intensity`/`indicators`/`consistency`, rozšírené `call`
> (number/realization_deadline/allocation_eur/regime), `annexes` (format/required_if),
> `eligibility` (evidence/computed) — všetko cez `allow_unknown:False` (typo = blocker).
> Pridané: guard na podmienené prílohy (`conditional_annex_deferred`) a kontrola formátu
> (`annex_wrong_format`). Testy `tool/tests/test_call_requirements.py` (6/6) overujú v1↔v2
> kompatibilitu, typo-blocker, podmienenú prílohu a formát.
> **Ostáva (runtime, NASTROJ-C):** hodnotové/cross-field kontroly (napr. `call_cap ≤ scheme_cap`,
> intenzity, sumy) a bezpečný evaluátor `consistency` blokov — tie robia checkery C1–C4, nie schéma.

### NASTROJ-0 — Založ lokálny balík `tool/` a odpoj research submodule `P0` — ✅ HOTOVO (2026-07-08)
**Popis:** Vytvor `tool/` v tomto repe: `tool/grantlib/` (skopíruj dependency-free moduly findings.py, schema.py, yamllite.py, csvio.py, paths.py z research frameworku, premenuj balík `frameworklib`→`grantlib`, zachovaj atribúciu), presuň grantovo-relevantné checkery (`check_call_requirements.py`, `build_submission_package.py`) do `tool/checks/`, napíš **slim grantový** agregátor `tool/checks/run_grant_qc.py` (NIE výskumný `run_framework_qc.py` — ten ťahá citation/figure/output-manifest checky, ktoré s grantom nesúvisia) a CLI `tool/grant.py` (check|qc|package|build). `build` je zatiaľ stub (NASTROJ-D4). Odstráň závislosť na `vendor/framework` (vyčisti `.gitmodules`, aktualizuj README/HANDOVER).
**Akceptačné kritériá:**
- [x] `python3 tool/grant.py --project-root examples/modelova-vyzva-2026 check` vráti PASS BEZ prítomnosti `vendor/framework` (overené po fyzickom odpojení submodulu).
- [x] `tool/grantlib/` obsahuje skopírované moduly bez externých závislostí; atribúcia v `tool/README.md`.
- [x] `check_call_requirements.py` beží z `tool/checks/` (v2 schéma pribudne v NASTROJ-A1..A6).
- [x] `.gitmodules` odstránený (prázdny); README/HANDOVER/example aktualizované na lokálny `tool/`.
- [x] Unit testy checkerov v `tool/tests/test_call_requirements.py` (6/6 PASS); ďalšie pribudnú s C1–C4.

### NASTROJ-A1 — Povýšenie hlavičky schémy na v2 (`call`, `sections`, `annexes`) `P0`
**Popis:** Rozšíriť blok `call` o `number`, `realization_deadline`, `allocation_eur`, `regime`; blok `sections` už podporuje limity (netreba meniť); blok `annexes` o `format`, `required_if`. Zachovať spätnú kompatibilitu s `version: 1`.
**Akceptačné kritériá:**
- [ ] `call` prijíma nové polia `number`, `realization_deadline`, `allocation_eur`, `regime` (validované typy: str/str/int/str).
- [ ] `annexes[]` prijíma `format` (str) a `required_if` (str výraz).
- [ ] `version: 1` súbor (existujúca šablóna) stále prejde bez `blocker`.
- [ ] Neznáme pole → `blocker` (`allow_unknown:False` platí aj pre nové bloky).
- [ ] Existujúce testy `check_call_requirements` prechádzajú bez zmeny.

### NASTROJ-A2 — Blok `budget` do schémy `P0`
**Popis:** Pridať validáciu bloku `budget` (file, currency, vat_included, min_cov, max_cov, work_packages[], require_trl_per_wp, categories{regime:[str]}, pausal{regime:{code,rate,base_codes}}, totals{...}).
**Akceptačné kritériá:**
- [ ] Blok `budget` je validovaný s `allow_unknown:False`; chýbajúci povinný podkľúč hlási zrozumiteľný nález.
- [ ] `categories` a `pausal` prijímajú kľúčovanie podľa režimu (`A`/`B`).
- [ ] `min_cov`/`max_cov` validované ako int; `vat_included` ako bool.
- [ ] Unit test s referenčným rozpočtovým blokom z výzvy prejde.

### NASTROJ-A3 — Blok `aid_intensity` do schémy `P0`
**Popis:** Validovať `scheme_ref`, `category`, `call_cap`, `scheme_cap`, `base_rate`, `size_uplift{mikro/maly/stredny/velky}`, `region_uplift`, `region_uplift_condition`, `regime_B_fixed`, `per_row_check`, `effective_le_cap`.
**Akceptačné kritériá:**
- [ ] Sadzby validované ako float v rozsahu 0.0–1.0; mimo rozsahu → `major`/`blocker`.
- [ ] `size_uplift` je mapa štyroch veľkostných kategórií.
- [ ] `call_cap ≤ scheme_cap` je validované už na úrovni schémy (inak `blocker`).

### NASTROJ-A4 — Blok `indicators` do schémy `P1`
**Popis:** Validovať `file`, `min_main`, `max_main`, `min_secondary`, `max_secondary`, `max_total`, `require_dissemination_secondary`, `fields[]`, `plan_by`, `catalogue_ref`.
**Akceptačné kritériá:**
- [ ] Počty validované ako int; `require_dissemination_secondary` ako bool.
- [ ] `fields[]` je zoznam reťazcov.

### NASTROJ-A5 — Blok `consistency` (deklaratívne asercie) do schémy `P1`
**Popis:** Validovať zoznam asercií s tvarmi `{id, left, right, op}` a `{id, expr}`. Definovať povolenú množinu operátorov (`eq`, `le`, `ge`, ...) a whitelist funkcií pre `expr` (`set`, `disjoint`, `implies`).
**Akceptačné kritériá:**
- [ ] Obidva tvary asercie sú validné; miešanie `left/right/op` s `expr` v jednej položke → `blocker`.
- [ ] Neznámy operátor → `blocker` už pri validácii schémy.
- [ ] Dokumentovaná gramatika `expr` (bezpečný evaluátor, žiadny `eval` nad ľubovoľným kódom).

### NASTROJ-A6 — Rozšírenie bloku `eligibility` (evidence/computed) `P1`
**Popis:** K existujúcemu `{id, description, met}` pridať voliteľné `evidence` (str cesta) a `computed` (str referencia na checker, napr. `check_eligibility.py::msp`).
**Akceptačné kritériá:**
- [ ] `met` a `computed` sú vzájomne voliteľné; položka bez oboch → `major` (nevyhodnotiteľná eligibilita).
- [ ] `evidence` cesta sa (ak vyplnená) kontroluje na existenciu súboru.

---

# NASTROJ-B — XLSX I/O (vrstva: nástroj)

> **Status (2026-07-08) — ✅ HOTOVO (B1 čítač + B2 zapisovač):** `tool/grantlib/xlsxio.py`
> (write_xlsx s inlineStr/číselnými bunkami + read_xlsx/read_xlsx_rows, csvio-kompatibilné) a navyše
> `tool/grantlib/docxio.py` (write_docx: nadpisy/odseky/tabuľky). `grantlib/csvio.read_rows` dispatchuje
> CSV↔XLSX podľa prípony, takže rozpočet môže byť `.csv` aj `.xlsx` (checkery C1/C2/C4 + build). Build
> `grant.py build --target docx|xlsx` generuje validný OOXML (Opis 2b DOCX, rozpočet+indikátory XLSX).
> Testy `tool/tests/test_ooxml.py` (6/6: round-trip, well-formed XML, multi-sheet, csvio-shape, xlsx-vstup do check_budget).
> **Ostáva:** parsovanie *reálneho* 2c layoutu so subtotalmi (dnes normalizovaný CSV/XLSX), styles.xml pre šírky stĺpcov.

### NASTROJ-B1 — `grantlib/xlsxio.py` — bezzávislý čítač `P0`
**Popis:** Vytvoriť numeric-tolerantný XLSX reader (rozbalenie ZIP + parse `xl/worksheets/*.xml` + `sharedStrings.xml`) bez externých závislostí, konzistentný s API `grantlib/csvio.py` (rovnaký tvar riadkov/hlavičiek).
**Akceptačné kritériá:**
- [ ] Prečíta hárky do zoznamu dictov (hlavička = prvý riadok) rovnako ako `csvio`.
- [ ] Toleruje číselné bunky, prázdne bunky, zlúčené hlavičky; nespadne pri chýbajúcom `sharedStrings`.
- [ ] Žiadny import mimo štandardnej knižnice (`zipfile`, `xml.etree`).
- [ ] Unit testy: čítanie reálneho `2c-rozpocet` exportu do XLSX aj triviálneho fixture.

### NASTROJ-B2 — `xlsxio.py` — zapisovač (render z modelu) `P1`
**Popis:** Zapisovač XLSX pre výstupné 2c/5 (viacero hárkov, číselné formáty, subtotal riadky). Používa ho `build_publication.py`.
**Akceptačné kritériá:**
- [ ] Zapíše validný `.xlsx` otvoriteľný v Exceli/LibreOffice (round-trip cez B1 čítač vráti rovnaké dáta).
- [ ] Podpora viacerých hárkov (2c rozpočet, Príloha 5).
- [ ] Číselné bunky sú číselné (nie textové), aby prešli súčtami.

---

# NASTROJ-C — Deterministické checkery (vrstva: nástroj)

Bezzávislé, numeric-tolerant, emitujú typované `Finding` (`grantlib/findings.py`) so správnym `area`. Žiadny výzvový fakt nie je zadrôtovaný — všetko z `call-requirements.yaml` + `project.yaml` + `legislation.yaml`.

### NASTROJ-C1 — `check_budget.py` (riadkové/subtotal/total/paušál/envelope/TRL) `P0` — 🟡 ČIASTOČNE HOTOVO (2026-07-08)
> Implementované: R1 (riadková aritmetika `budget_row_mismatch`), R2 (kategórie `category_not_allowed`),
> total COV + R7 envelope (`budget_out_of_envelope`), R6 paušál (`pausal_wrong`), `budget_file_missing`.
> Číta **normalizovaný** rozpočtový CSV cez `csvio` (jeden riadok = výdavok; oficiálny 2c layout so
> subtotalmi je render-target pre `build`). Wired do `run_grant_qc` + CLI `grant.py budget`.
> Testy `tool/tests/test_budget.py` (6/6). Demo: `examples/budget-demo/`.
> **Ostáva:** R3/R4 explicitné subtotal-riadky (v normalizovanom CSV odpadá — total sa počíta priamo),
> R8 TRL-per-WP (čaká na `project.yaml` WP TRL), a XLSX vstup (NASTROJ-B).
**Popis:** Implementovať pravidlá R1–R8 zo SPEC §4.1. Číta rozpočet cez `xlsxio`/`csvio`, blok `budget`, `project.regime`.
**Akceptačné kritériá:**
- [ ] R1 `celkove = pocet * jednotkova_cena` (nesúlad → `major`).
- [ ] R2 kategória riadku ∈ `budget.categories[regime]` (inak `blocker`).
- [ ] R3 `SPOLU(wp) = Σ riadkov WP` (`major`); R4 `Σ SPOLU(3-1..3-4) = total_cov` (`blocker`); R5 `total_cov = Σ všetkých COV bez DPH` (`blocker`).
- [ ] R6a/R6b paušál podľa režimu (A: 920=20 % zo Σ(521+551+518); B: 940=40 % zo Σ521) s toleranciou ±0,01 € (`major`); R6c dvojitý paušál → `blocker`.
- [ ] R7 `300000 ≤ total_cov ≤ 2200000` bez DPH (`blocker`).
- [ ] R8 každý použitý WP má TRL na začiatku (`major`).
- [ ] `area="budget"`, stabilné `check_id` reťazce podľa §6.2 (`budget_row_mismatch`, `budget_subtotal_mismatch`, `budget_out_of_envelope`, `pausal_wrong`, `category_not_allowed`, `wp_trl_missing`).
- [ ] Numeric tolerancia konfigurovateľná; unit testy pre každý nález (pozitívny aj negatívny prípad).

### NASTROJ-C2 — `check_aid_intensity.py` (intenzity/cap/uplift/režim B) `P0` — ✅ HOTOVO (2026-07-08)
> Implementované I1–I6: efektívna intenzita = `min(base + size_uplift[size] + region_uplift?, call_cap)`,
> strop schémy (`intensity_over_scheme_cap`), per-row `narokovane = COV × effective` (`narokovane_mismatch`),
> Σ nárokované ≤ cap (`intensity_over_cap`), režim B fix 60 % (`regimeB_not_fixed_60`), Bratislavský kraj
> ruší region uplift, neznáma veľkosť (`size_unknown`). Číta `project.yaml` (regime/miesto/MSP size) + rozpočet.
> Wired do `run_grant_qc` + `grant.py budget` (spúšťa budget aj intensity). Testy `tool/tests/test_aid_intensity.py`
> (6/6). Demo `examples/budget-demo/`: efektívna intenzita **60 %** (režim A, malý, Košice) → PASS.
> **Ostáva:** I7 size==MSP-vyhlásenie a spolufinancovanie S1–S4 sa dorieši s C4 (cross-doc) a C6 (MSP eligibility);
> intenzitné tabuľky sa neskôr plnia z `legislation.yaml` (dnes z `call-requirements` bloku).
**Popis:** Implementovať pravidlá I1–I7 zo SPEC §4.2 + spolufinancovanie S1–S4 (§4.3). Ruleset kľúčovaný `kategória × veľkosť` plnený z `legislation.yaml` (bez sieťového volania).
**Akceptačné kritériá:**
- [ ] I1 `intensity = base + size_uplift[size] + (region_uplift ak miesto != 'BA kraj')`.
- [ ] I2 `effective = min(intensity, call_cap)`; I3 per-row `narokovane = celkove * effective` (`major`).
- [ ] I4 `Σ narokovane ≤ call_cap * total_cov` (`blocker`).
- [ ] I5 režim B `ziadana_ppm = 0.60 * total_cov` fix (`blocker`, nie 100 %).
- [ ] I6 región uplift uplatnený ⇒ `miesto != 'BA kraj'` (`blocker`).
- [ ] I7 veľkosť v intenzite == veľkosť z MSP vyhlásenia (`blocker`).
- [ ] Referenčný beh (režim A, exp. vývoj, mimo BA): mikro/malý = 60 %, stredný = 50 %, veľký = 40 %.
- [ ] S1–S3 spolufinancovanie invariant; `check_id` podľa §6.2 (`intensity_over_cap`, `narokovane_mismatch`, `region_uplift_invalid`, `size_mismatch`, `regimeB_not_fixed_60`).

### NASTROJ-C3 — `check_indicators.py` (počty/typy/diseminácia/polia) `P1` — ✅ HOTOVO (2026-07-08)
> Počty main/secondary v rozsahu + `max_total` (`indicators_count_out_of_range`, `missing_main/secondary`),
> aspoň 1 diseminačný vedľajší (`missing_dissemination_secondary`, keyword heuristika), povinné polia
> (`indicator_field_missing` minor), chýbajúci súbor (`indicators_file_missing`). Wired do `run_grant_qc`.
> Testy `tool/tests/test_indicators.py` (6/6). Demo rozšírené o `indicators/indicators.csv`.
> **Ostáva:** striktná kontrola `plan_by` termínu a párovanie s katalógom Prílohy 4 (`catalogue_ref`).
**Popis:** Implementovať kontroly zo SPEC §3 (F7) a §6.2.
**Akceptačné kritériá:**
- [ ] 1–3 hlavné, 1–3 vedľajšie, `max_total ≤ 6`; ≥1 hlavný, ≥1 vedľajší (`major`).
- [ ] ≥1 vedľajší diseminačný, ak `require_dissemination_secondary` (`major`).
- [ ] všetky `fields[]` vyplnené (`indicator_field_missing` → `minor`).
- [ ] `planovana_hodnota` má termín ≤ `plan_by` (30.6.2026).

### NASTROJ-C4 — `check_cross_document_consistency.py` (asercie proti `project.yaml`) `P1` — ✅ HOTOVO (2026-07-08)
> Bezpečný evaluátor (ast whitelist — odmietne `__import__`/volania mimo `set/disjoint/implies/len/abs`)
> pre obidva tvary asercií `{left,right,op}` aj `{expr}`. Kontext = `project.yaml` (single source of truth)
> + dopočítaný rozpočet (`budget.total_cov`, `sum_narokovane`, `work_packages`) + namespaces
> `financovanie/opis/msp/aid_intensity`. Chýbajúce dáta → `consistency_skipped_missing_data` (info, nie
> falošný fail); zlá syntax → `consistency_bad_expression` (minor); per-asercia `severity`. Wired do
> `run_grant_qc`. Testy `tool/tests/test_cross_document.py` (6/6). Demo overuje COV=rozpočet, PPM,
> spolufinancovanie, TRL 6–8.
> **Ostáva:** namespaces `priloha5`/`komp9` (personál, neprekrývanie) po doplnení Prílohy 5 do modelu.
**Popis:** Bezpečný evaluátor deklaratívneho bloku `consistency` (§2.2, §6.3) proti `project.yaml` ako single source of truth (P2). Nie „dokument vs. dokument", ale „dokument vs. model".
**Akceptačné kritériá:**
- [ ] Vyhodnotí `{left,right,op}` aj `{expr}` s whitelist funkciami `set`/`disjoint`/`implies` (žiadny `eval` nad ľubovoľným kódom).
- [ ] Kľúčové kontroly: COV(Opis)=SPOLU(2c); PPM(Opis)=Σnárokované(2c); spolufinancovanie=COV−PPM; TRL koniec 6–8 a > začiatok; {WP} Opis=rozpočet=Príloha 5; personál Komp.9 ∩ personál projektu = ∅; veľkosť=MSP; región uplift len mimo BA.
- [ ] `check_id` podľa §6.2 (`cov_mismatch_opis_budget`, `ppm_mismatch`, `wp_set_mismatch`, `komp9_personal_overlap`, `trl_inconsistent`); severity blocker/major podľa SPEC.
- [ ] Chýbajúca hodnota v modeli → zrozumiteľný `major`, nie tichý pass.

### NASTROJ-C5 — `check_anonymization_leaks.py` (PII/firemné identifikátory) `P1` — ✅ HOTOVO (2026-07-08)
> Regexový scan (email, IBAN SK, DIČ, tel. +421) + voliteľný literal denylist; placeholdre
> (`[ZIADATEL]`, `[OSOBA_1]`…) maskované, nehlásené. `unanonymized_pii`/`company_identifier_leak`
> (blocker). Gejtované na mód `final_publication` v `run_grant_qc` (pred balením). Testy
> `tool/tests/test_anonymization.py` (6/6).
> **Ostáva:** naplniť denylist z gitignored `_anonymization-key.local.md` (reálne hodnoty) + hook
> pred `build_submission_package` (NASTROJ-D5).
**Popis:** Skenuje artefakty regexom proti placeholder schéme z `ANONYMIZATION.md`. Nájdený reálny (neplaceholdrovaný) identifikátor = `blocker`.
**Akceptačné kritériá:**
- [ ] Deteguje `unanonymized_pii` a `company_identifier_leak` (`blocker`).
- [ ] Placeholder tvary (`[ZIADATEL]`, `[ICO]`, `[OSOBA_n]`) sa NEhlásia ako leak.
- [ ] Vstupom je zoznam skenovaných ciest + schéma placeholderov (cesta z manifestu), nie zadrôtované firemné mená.
- [ ] Konfigurovateľné regex vzory (IČO, e-mail, telefón, názvy) v dátach, nie v kóde nástroja.

### NASTROJ-C6 — `check_eligibility.py` (počítaná eligibilita: MSP, VaV track-record) `P1` — ✅ HOTOVO (MSP; 2026-07-08)
> `compute_msp_size` z EU definície (zamestnanci AND (obrat≤X OR súvaha≤Y)): mikro/malý/stredný/veľký;
> cross-check voči deklarovanej `size_category` (`msp_size_mismatch` major), `velky` → `eligibility_not_met`,
> chýbajúci headcount → `msp_incomputable`. `check_call_requirements` teraz preskakuje `computed:` položky
> (rieši ich C6). Wired do `run_grant_qc`. Testy `tool/tests/test_eligibility.py` (8/8). Demo: computed `maly` == deklarované.
> **Ostáva:** VaV track-record (≥1/≥2 projekty za 2 roky v doménach 3-1..3-4 zo `source-registry.yaml`) — po
> ustálení formátu registra; prepojené partnerské/prepojené podniky (agregácia údajov) podľa schémy.
**Popis:** Nová počítaná eligibilita volaná cez `computed:` referenciu (napr. `check_eligibility.py::msp`). Vypočíta veľkostnú kategóriu MSP z `project.applicant.msp` a overí ≥1/≥2 VaV projekty za 2 roky v doménach 3-1..3-4 zo `source-registry.yaml`.
**Akceptačné kritériá:**
- [ ] `msp`: <10 zam. & ≤2 M€ → mikro; <50 & ≤10 M€ → malý; inak stredný/veľký; výsledok použiteľný v C2 (I7).
- [ ] VaV track-record: počíta projekty v okne 2 rokov v cieľových doménach z evidencie; nedostatok → `eligibility_not_met` (`major`).
- [ ] Nič nie je „ručne `met:true`" — hodnota sa deriváciou počíta.

---

# NASTROJ-D — Agregácia QC, CLI, build, package (vrstva: nástroj)

### NASTROJ-D1 — Napojenie nových checkerov do `run_framework_qc.py` `P0`
**Popis:** Rovnakým vzorom `load_module` + `findings.extend` (dnes ~185–249) zaradiť C1–C6. Rozhodnutie `BLOCK / REVISE / PASS_WITH_NOTES`. Módy `smoke` (len blocker), `pre_word` (blocker+major), `final_publication` (plný set + leak-scan). Prah cez `--fail-on`.
**Akceptačné kritériá:**
- [ ] Checkery bežia iba ak existujú ich vstupné súbory (manifest-driven, vzor `add_if_exists`).
- [ ] Agregát emituje JSON + MD report do `analysis/qc_reports/`.
- [ ] `final_publication` zahŕňa leak-scan (C5) ako povinný krok.
- [ ] `--fail-on major` v `final_publication` vracia nenulový kód pri akomkoľvek major/blocker.
- [ ] Rozhodnutie zodpovedá: akýkoľvek `blocker` → `BLOCK`; major bez blocker → `REVISE`; inak `PASS_WITH_NOTES`.

### NASTROJ-D2 — Nové subkomandy `budget`, `ingest`, `anonymize` v `grant.py` `P0`
**Popis:** Rozšíriť dispatcher (`cmd_*` funkcie) o nové subkomandy; odvodzovať cesty z manifestu, odovzdávať iba flagy existujúcich súborov.
**Akceptačné kritériá:**
- [ ] `grant.py budget --project-root <app>` spustí `check_budget.py` + `check_aid_intensity.py` s manifest-derived cestami.
- [ ] `grant.py ingest` a `grant.py anonymize` sú registrované a dispatchujú na príslušné skripty.
- [ ] `grant.py check` už validuje v2 (žiadna nová CLI vetva pre bloky — čisto data-driven).
- [ ] Chýbajúci súbor → flag sa neodovzdá (nie chyba).

### NASTROJ-D3 — Nové path-kľúče v `tool/templates/study-manifest.yaml` `P0`
**Popis:** Doplniť `budget_file`, `aid_intensity_scheme`, `indicators_file`, `project_model`, `legislation_file`, `anonymization_key` podľa vzoru `add_if_exists`.
**Akceptačné kritériá:**
- [ ] Nové kľúče sú v šablóne manifestu (`tool/templates/study-manifest.yaml`) a dokumentované.
- [ ] `grant.py` číta a validuje ich existenciu pred odovzdaním checkerom.

### NASTROJ-D4 — build render z modelu `P1` — ✅ HOTOVO (Markdown + binárny DOCX/XLSX; 2026-07-08)
> `tool/checks/build_dossier.py` + `grant.py build --target markdown` → `publication/dossier.md` (gitignored):
> zostaví Opis (manuscript/*.md) + rozpočtovú tabuľku s dopočítanými súčtami (COV/PPM/spolufinancovanie)
> + tabuľku indikátorov + hlavičku výzvy. Placeholdre zachované (de-anonymizácia až vo finalizácii).
> Testy `tool/tests/test_build.py` (2/2). Demo: `examples/budget-demo/publication/dossier.md`.
> Binárny DOCX (2b) + XLSX (2c/indikátory) render cez `docxio`/`xlsxio` je HOTOVÝ (`grant.py build --target docx|xlsx`).
> **Ostáva:** presný oficiálny 2c layout (subtotaly/míľniky), Príloha 5, content-hash snapshot/build log, strip `[@key]`.
**Popis:** Rozšíriť builder o render 2b (DOCX), 2c a 5 (XLSX cez `xlsxio` B2) z validovaného modelu. Žiadny surový `[@key]` neprežije vo výstupe. Content-hashed snapshot + build log.
**Akceptačné kritériá:**
- [ ] Vyprodukuje DOCX (2b) a XLSX (2c, 5) z `project.yaml`/rozpočtu.
- [ ] Žiadny `[@key]` citačný token v build výstupe.
- [ ] Zapíše content-hash snapshot a build log.

### NASTROJ-D5 — `build_submission_package.py`: leak-scan hook + visibility gate `P1`
**Popis:** Pred kopírovaním pridať leak-scan (C5) ako blokujúci krok. Zachovať kopírovanie iba riadkov `include=true AND visibility=public`, blokovanie restricted/path-traversal/duplicít/chýbajúcich zdrojov.
**Akceptačné kritériá:**
- [ ] Leak-scan beží pred kopírovaním; `blocker` zastaví balenie.
- [ ] Do balíka idú iba `include=true AND visibility=public`; `package_manifest.csv` sa vytvorí.
- [ ] Path-traversal (`..`/absolútne/mimo-root), duplicity a chýbajúce povinné zdroje sú blokované (existujúce správanie zachované).

---

# OBSAH-E — Šablóny (vrstva: obsah)

### OBSAH-E1 — `templates/call-requirements-template.yaml` → v2 `P0`
**Popis:** Povýšiť existujúcu v1 šablónu na v2 s komentovanými blokmi budget/aid_intensity/indicators/consistency (pozri SPEC §2.2). Zachovať v1 sekcie ako podmnožinu.
**Akceptačné kritériá:**
- [ ] Šablóna prejde `grant.py check` proti schéme v2 (`allow_unknown:False`, žiadny blocker).
- [ ] Každý blok má komentár s významom polí a odkazom na relevantný checker.

### OBSAH-E2 — `templates/project-template.yaml` (single source of truth) `P0`
**Popis:** Nová typová šablóna projektového modelu podľa SPEC §2.3 (project, applicant.msp, work_packages, personnel, milestones) s placeholdermi.
**Akceptačné kritériá:**
- [ ] Obsahuje všetky polia, ktoré konzumujú C2/C4/C6 (regime, miesto, trl_start/end, msp, WP, personnel).
- [ ] Použité placeholdery (`[ZIADATEL]`, `[ICO]`, `[OSOBA_n]`) zodpovedajú ANONYMIZATION schéme.

### OBSAH-E3 — `templates/legislation-template.yaml` (register + pinning) `P1`
**Popis:** Nová šablóna registra zdrojov podľa §2.4 (GBER/RRF/schéma D1/SK RIS3) s `consolidated_version`, `retrieved_at`, `used_for`, `local_copy`/`url`, `manual`.
**Akceptačné kritériá:**
- [ ] Obsahuje 4 pinnuté zdroje zo SPEC + polia pre freshness gate.
- [ ] Intenzitné tabuľky sú reprezentovateľné ako dáta (konzumovateľné C2 bez siete).

### OBSAH-E4 — Šablóny sekcií Opisu (Príloha 2b) + Opis model `P1`
**Popis:** Šablóny markdown sekcií Opisu s limitmi zodpovedajúcimi `sections` (napr. abstrakt 150–250 slov, excelentnosť `max_words: null`) a placeholdrami z modelu.
**Akceptačné kritériá:**
- [ ] Sada `manuscript/*.md` skeletonov pokrýva povinné sekcie Opisu vrátane „Finančné prostriedky – celkový prehľad" (napojenie na S4).
- [ ] Limity sekcií zladené s `call-requirements` v2.

---

# OBSAH-F — Agentické skills + `/workflows` orchestrácia (vrstva: obsah)

### OBSAH-F1 — Skeleton adresárov `skills/` a `workflows/` `P0`
**Popis:** Založiť v tomto repe `skills/` (9 skillov zo SPEC §8) a `workflows/` s definíciou 9-fázovej pipeline (F1–F9) a REVISE-slučkou.
**Akceptačné kritériá:**
- [ ] Vytvorené `skills/{ingest-call,semantic-map,call-model,legislation-retrieval,write-opis,compute-budget,indicators,qc-gate,finalize}/`.
- [ ] `workflows/` popisuje poradie fáz, brány a per-výzva (F1–F4) vs. per-žiadosť (F5–F9) rozdelenie.

### OBSAH-F2 — `grant-prep` skill (jednotný vstupný workflow) `P0`
**Popis:** Zastrešujúci skill, ktorý riadi slučku `write/compute → qc → (REVISE) → oprava → qc`, kým nie je `PASS_WITH_NOTES` v `final_publication`. LLM navrhuje, checker schvaľuje.
**Akceptačné kritériá:**
- [ ] Skill nikdy neschvaľuje vlastný výstup — rozhodnutie robí `run_framework_qc.py`.
- [ ] Volá `grant.py <subcommand> --project-root <app>`; číta rozhodnutie z QC reportu a iteruje.
- [ ] Dokumentovaná deľba: LLM = próza/hodnoty, checker = čísla/asercie.

### OBSAH-F3 — Skills F5–F7 (`write-opis`, `compute-budget`, `indicators`) `P1`
**Popis:** Implementovať tri obsahové skilly píšuce/plniace model a spúšťajúce príslušné checkery.
**Akceptačné kritériá:**
- [ ] `write-opis` produkuje `manuscript/*.md` v rámci word/char limitov.
- [ ] `compute-budget` plní `project.yaml` → generuje rozpočet a volá `grant.py budget`.
- [ ] `indicators` vyberie 1–3+1–3 ukazovatele z katalógu Prílohy 4 a volá `check_indicators.py`.

### OBSAH-F4 — Skills F8–F9 (`qc-gate`, `finalize`) `P1`
**Popis:** `qc-gate` spúšťa agregovaný QC v danom móde; `finalize` reťazí de-anonymizáciu + build + package.
**Akceptačné kritériá:**
- [ ] `qc-gate` mapuje mód → `--mode/--fail-on` a vracia rozhodnutie.
- [ ] `finalize` beží iba pri `PASS_WITH_NOTES`; volá `build_publication.py` a `build_submission_package.py`.

---

# OBSAH-G — Call-ingestion pipeline + knowledge base (vrstva: obsah)

### OBSAH-G1 — `ingest-call` skill + `grant.py ingest` prepojenie (F1) `P0`
**Popis:** PDF/DOCX/XLSX → 1:1 markdown do `calls/<call>/source-md/**`; explicitne emituje `blocker` `locked_source`/`empty_required_section` (poučenie z prázdneho `…opis-projektu-ziadatel-fin.md`).
**Akceptačné kritériá:**
- [ ] Heslom chránený/prázdny povinný zdroj → `blocker`, NIE tiché vytvorenie prázdneho súboru.
- [ ] Emituje zoznam neextrahovateľných zdrojov; nález prežíva do F8.
- [ ] Výstup je deterministický markdown 1:1 k zdroju.

### OBSAH-G2 — `semantic-map` skill → `SEMANTIC-MAP.md` (F2) `P1`
**Popis:** Inventár faktov (alokácia, rozpočtový rozsah, lehoty, eligibilita) + kandidáti na requirements; každý fakt s odkazom na zdrojový súbor.
**Akceptačné kritériá:**
- [ ] Každý fakt má odkaz na konkrétny súbor v `source-md/`.
- [ ] Sekcia „kandidáti na requirements" priamo mapuje na bloky v2.

### OBSAH-G3 — `call-model` skill → `call-requirements.yaml` v2 (F3) `P1`
**Popis:** Zo `SEMANTIC-MAP.md` vygeneruje vyplnený `call-requirements.yaml` v2 pre referenčnú výzvu; validuje `grant.py check`.
**Akceptačné kritériá:**
- [ ] Výstup pre `17I04-04-V05-RIS3` prejde schémou v2 bez blocker.
- [ ] Hodnoty (deadline 2025-10-03 po Usmernení č.1, realizácia 2026-06-30, 300k–2,2M, cap 0,60) zodpovedajú knowledge base.

---

# OBSAH-H — Register externých zdrojov + retrieval playbook (vrstva: obsah)

### OBSAH-H1 — `legislation-retrieval` skill (WebFetch + pinning, F4) `P1` — ✅ HOTOVO (skill + live overené; 2026-07-08)
> `skills/legislation-retrieval/SKILL.md` — postup WebFetch → `legislation.yaml` s `retrieved_at`/`consolidated_version`;
> portály (ITMS/RT/QES) ako `manual_portals`. **Live overené:** GBER konsolidácia 2023-07-01 (EUR-Lex),
> MIRRI potvrdil 17I04-04-V05 = CLOSED. Demo `examples/budget-demo/legislation.yaml` s overenými pinmi.
> **Ostáva:** automatický agentický beh naprieč všetkými zdrojmi výzvy + porovnanie „novšie Usmernenie".
**Popis:** Napĺňa/udržiava `legislation.yaml`; `WebFetch` na verejné HTML/PDF; portálové kroky (ITMS2014+, slovensko.sk QES, výpis z RT) označí `manual: true` a NEautomatizuje.
**Akceptačné kritériá:**
- [ ] Každý zdroj má `consolidated_version` + `retrieved_at`.
- [ ] Intenzitné tabuľky a definícia MSP uložené ako dáta (nie iba odkaz).
- [ ] Manuálne kroky sú explicitne `manual: true`, bez pokusu o automatizáciu.

### OBSAH-H2 — Retrieval playbook (registrovaný zoznam SK/EU zdrojov) `P1`
**Popis:** Dokument v repe s registrom zdrojov a metódou (SK: MIRRI, VAIA, ORSR/RPVS, Register trestov, ÚPV, Finančná správa; EU: EUR-Lex ELI GBER/RRF/Digital Europe, JRC S3).
**Akceptačné kritériá:**
- [ ] Playbook uvádza pre každý zdroj URL/ELI, či je `manual`, a `used_for`.
- [ ] Zahŕňa non-overlap kontext (definícia Komponentu 9, doménová taxonómia 3-1..3-4) pre krížovú kontrolu Prílohy 5.

### OBSAH-H3 — Freshness gate integrácia `P2` — ✅ HOTOVO (2026-07-08)
> `tool/checks/check_legislation.py` (pozn.: vrstva nástroj) — `>window (30d) → minor legislation_stale`,
> chýbajúci pin → `legislation_unpinned`, manuálny doklad po platnosti (`validity` „3 mesiace“ atď.) →
> `manual_doc_expired` major. Wired do `run_grant_qc` (ak `legislation.yaml` existuje). Testy
> `tool/tests/test_legislation.py` (7/7). „Novšie Usmernenie → blocker“ ostáva agentické (skill).
**Popis:** Pravidlá freshness zo SPEC §5 (>30 dní → minor; novšie Usmernenie než pinnuté → blocker; manuálny doklad po platnosti, napr. výpis z RT > 3 mesiace → major) vyhodnocované v QC.
**Akceptačné kritériá:**
- [ ] `today - retrieved_at > 30 dní` → `minor`.
- [ ] Vyššie číslované Usmernenie výzvy než pinnuté → `blocker`.
- [ ] Manuálny doklad po požadovanej platnosti → `major`.

---

# OBSAH-I — Anonymizácia (vrstva: obsah)

### OBSAH-I1 — `ANONYMIZATION.md` + placeholder schéma + gitignore `P0`
**Popis:** Schéma placeholderov (`[ZIADATEL]`, `[ICO]`, `[OSOBA_n]`…) a gitignore vzory (`*.local.md`, `*_.local.md`, `**/publication/*`). Reverzný kľúč `_anonymization-key.local.md` je gitignored.
**Akceptačné kritériá:**
- [ ] `ANONYMIZATION.md` definuje kompletnú placeholder schému konzumovanú C5.
- [ ] `.gitignore` blokuje reverzný kľúč aj de-anonymizovaný build; overené `git check-ignore`.

### OBSAH-I2 — `anonymize` helper (substitúcia + restore vo F9) `P1`
**Popis:** Obsahový helper: pri písaní/konverzii nahrádza reálne hodnoty placeholdermi; vo F9 (finalizácia) restore z lokálneho kľúča (cesta `anonymization_key` z manifestu). De-anonymizovaný build sa NIKDY necommituje.
**Akceptačné kritériá:**
- [ ] Substitúcia aj restore sú reprodukovateľné a symetrické (round-trip).
- [ ] Restore beží iba vo F9 tesne pred generovaním 2b/2c/5.
- [ ] Leak-scan (C5) beží ako blokujúci krok pred balením.

---

# OBSAH-J — Klonovateľný skeleton žiadosti + demo (vrstva: obsah)

### OBSAH-J1 — Rozšírenie `examples/modelova-vyzva-2026/` na v2 skeleton `P1`
**Popis:** Doplniť do demo skeletonu `project.yaml`, `legislation.yaml`, `budget/`, `indicators/`, `references/source-registry.yaml`, `annexes/`, `call-requirements.yaml` v2 a committed `framework_qc_report` ukazujúci tvar brány.
**Akceptačné kritériá:**
- [ ] Klonovaním vznikne funkčná kostra pre `applications/<call>-<applicant>/`.
- [ ] Demo prejde `grant.py qc --mode smoke` a committed report ukazuje `PASS`/rozhodnutie.
- [ ] `study_manifest.yaml` obsahuje nové path-kľúče (NASTROJ-D3).

### OBSAH-J2 — Referenčná žiadosť `applications/17I04-04-V05-RIS3-elara/` `P2` — ✅ HOTOVO (2026-07-08)
> Kompletná anonymizovaná žiadosť ELARA-AI z faktov `SEMANTIC-MAP.md`: `call-requirements` v2, `project.yaml`,
> rozpočet (COV 1 056 000 €, paušál 20 %), intenzita 60 % (režim A/malý/Košice), 3 indikátory, 8 sekcií Opisu,
> pinnutá legislatíva, `source-registry`. **Brána:** všetky obsahové dimenzie PASS; jediný blocker
> `deadline_passed` (výzva CLOSED od 3. 10. 2025 — overené); pred termínom (`--today 2025-09-15`) PASS.
> **Build:** `opis.docx` (Opis 2b + rozpočtová tabuľka) a `rozpocet.xlsx` (SPOLU 1 056 000/633 600) vygenerované.
> Placeholdre zachované; build artefakty gitignored (doplnené `**/publication/*.xlsx`).
**Popis:** Prvá reálna klonovaná žiadosť pre referenčnú výzvu ako end-to-end dôkaz (per-žiadosť fázy F5–F9).
**Akceptačné kritériá:**
- [ ] `run_framework_qc.py --mode final_publication --fail-on major` → `PASS_WITH_NOTES`.
- [ ] Vygenerované 2b (DOCX), 2c/5 (XLSX); package s `package_manifest.csv`; reverzný kľúč necommitnutý.

---

# Sekvenovanie / míľniky

### Míľnik M0 — „Schéma v2 stojí" (základ pre všetko ostatné)
`NASTROJ-0` → `NASTROJ-A1`, `NASTROJ-A2`, `NASTROJ-A3` → `OBSAH-E1`, `OBSAH-E2`.
Cieľ: `grant.py check` prijme v2 pre referenčnú výzvu; existuje `project.yaml`.

### Míľnik M1 — „Prvá deterministická brána beží" (P0 jadro)
`NASTROJ-B1` → `NASTROJ-C1`, `NASTROJ-C2` → `NASTROJ-D1`, `NASTROJ-D2`, `NASTROJ-D3` → `OBSAH-F1`, `OBSAH-F2`, `OBSAH-G1`, `OBSAH-I1`.
Cieľ: rozpočet + intenzity + envelope + cap prechádzajú QC bránou; `grant.py budget` a `ingest` fungujú; leak schéma + gitignore stoja.

### Míľnik M2 — „Žiadosť je hotová podľa §9" (P1)
`NASTROJ-A4`, `NASTROJ-A5`, `NASTROJ-A6`, `NASTROJ-B2`, `NASTROJ-C3`, `NASTROJ-C4`, `NASTROJ-C5`, `NASTROJ-C6`, `NASTROJ-D4`, `NASTROJ-D5`; `OBSAH-E3`, `OBSAH-E4`, `OBSAH-F3`, `OBSAH-F4`, `OBSAH-G2`, `OBSAH-G3`, `OBSAH-H1`, `OBSAH-H2`, `OBSAH-I2`, `OBSAH-J1`.
Cieľ: indikátory, krížové kontroly, leak-scan, legislatíva pinnutá, DOCX/XLSX build, balenie — plný set §9 A–G.

### Míľnik M3 — „Top-class / robustnosť" (P2)
`OBSAH-H3` (freshness gate), `OBSAH-J2` (reálna referenčná žiadosť end-to-end), tvrdenie o jedinom ľudskom vstupe (`project.yaml` + lokálny kľúč).

**Kritická cesta:** M0 → `NASTROJ-B1` → `NASTROJ-C1/C2` → `NASTROJ-D1` je najkratšia trasa k prvej fungujúcej bráne; všetko ostatné vetví paralelne.

---

# Definition of Done (globálne, pre každú story)

**Nástroj (`tool/`):**
- [ ] Kód je bezzávislý (iba štandardná knižnica); žiadny výzvový fakt zadrôtovaný — všetko cez `call-requirements.yaml`/`project.yaml`/`legislation.yaml`.
- [ ] Nálezy sú typované `Finding` so správnym `severity`/`area`/`check_id`/`file`/`message` (podľa `grantlib/findings.py`).
- [ ] Unit testy: pozitívny aj negatívny prípad pre každý nový nález; `allow_unknown:False` zostáva vynútené.
- [ ] Checker beží iba pri existencii vstupu (manifest-driven, vzor `add_if_exists`); žiadna nová CLI vetva pre data-driven pravidlá.
- [ ] Zmena je commitnutá priamo v tool/ (jeden repozitár, žiadny submodule).

**Obsah (tento repo):**
- [ ] Žiadne reálne PII/firemné identifikátory mimo gitignored `*.local.md`; `check_anonymization_leaks.py` bez `blocker`.
- [ ] Artefakt prejde `grant.py check`/`qc` v relevantnom móde bez neplánovaného `blocker`.
- [ ] Skilly volajú `grant.py <subcommand> --project-root <app>` a nikdy neschvaľujú vlastný výstup — arbitrom je deterministická brána.
- [ ] Každý fakt/hodnota má stopu k zdroju (SEMANTIC-MAP odkaz alebo `legislation.yaml` pin s `retrieved_at`/`version`).

**Spoločné:**
- [ ] Aktualizovaná dokumentácia (README/šablónové komentáre) k novým blokom/kľúčom.
- [ ] Reprodukovateľnosť: dvojnásobný beh dáva identický JSON+MD report (deterministický výstup).

---

**Relevantné súbory pre implementáciu (absolútne cesty):**
- Schéma na rozšírenie: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/check_call_requirements.py` (riadky 44–106)
- QC agregátor: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/run_framework_qc.py`
- CLI dispatcher: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/grant.py`
- Finding typ: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/grantlib/findings.py`
- CSV I/O vzor pre nový `xlsxio.py`: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/grantlib/csvio.py`
- Builder/packager: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/build_publication.py`, `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/build_submission_package.py`
- Šablóna v1 → v2: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/templates/call-requirements-template.yaml`
- Demo skeleton: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/examples/modelova-vyzva-2026/`
- Knowledge base výzvy: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/calls/17I04-04-V05-RIS3/`