# SPEC — Agentický framework pre grantové žiadosti (`agentic-grantapp-framework`)

**Verzia:** 1.0 · **Autor:** vedúci architekt · **Dátum:** 2026-07-08
**Referenčná výzva:** `17I04-04-V05-RIS3` (Komponent 17, MIRRI SR, Plán obnovy)
**Cieľová platforma:** deterministický lokálny balík `tool/` + obsahová vrstva, oba v tomto repozitári (bez závislosti na research frameworku).

> **Stav (2026-07-09): jadro implementované a overené** (78 testov, 2 audity, agentická content-QC).
> Prehľad hotového viď `docs/BACKLOG-grantapp.md` → „IMPLEMENTAČNÝ STAV". Kľúčové: `build --target all`
> generuje Opis 2b + rozpočet 2c + 7 príloh z oficiálnych šablôn; dvoj-bránová QC (deterministická + agentická).

---

## 1) Cieľ a princípy (nástroj vs. obsah)

### 1.1 Cieľ
Vybudovať **agentický systém, ktorý dokáže zreplikovať úspešnú RIS3 žiadosť pre ľubovoľnú novú výzvu**: vygenerovať Opis projektu (Príloha 2b), rozpočet s intenzitami pomoci (Príloha 3 / 2c), povinné prílohy, merateľné ukazovatele (Príloha 4) a porovnávaciu tabuľku neprekrývania s Komponentom 9 (Príloha 5) — pričom AI robí **výpočty (rozpočet, intenzity, paušál, spolufinancovanie), formátovanie, syntax, sémantiku** a **automaticky dohľadáva relevantnú SK/EU legislatívu**. Výstup musí prejsť jednou deterministickou QC bránou s rozhodnutím `BLOCK / REVISE / PASS_WITH_NOTES`.

### 1.2 Základné princípy

| # | Princíp | Dôsledok |
|---|---------|----------|
| P1 | **Nástroj ≠ obsah.** `tool/` je generický, výzvovo-neutrálny checker/builder — lokálny balík v tomto repo, oddelený od obsahu. Obsah (fakty výzvy, projektové dáta, legislatíva) žije v tomto repo. | Do balíka `tool/` nikdy nekopírujeme výzvové fakty. Grant-špecifická logika = **iba dátami riadené pravidlá** v `call-requirements.yaml` + generické check-loopy. |
| P2 | **Jeden zdroj pravdy (single source of truth).** Projektový model (`project.yaml`) je autoritatívny; Opis, rozpočet, indikátory aj Príloha 5 sa z neho generujú alebo proti nemu validujú. | Krížové kontroly nemajú porovnávať dokument s dokumentom „naslepo", ale každý dokument s modelom. |
| P3 | **Determinizmus na bráne, kreativita na písaní.** Výpočty a kontroly sú bezzávislé (dependency-free) a reprodukovateľné; LLM píše prózu a navrhuje hodnoty, ale nikdy neschvaľuje sám seba. | QC gate je „hard gate": pri `blocker` sa build zastaví. |
| P4 | **Manifestom riadené cesty.** Projekt vypĺňa iba tie časti `study_manifest.yaml`, ktoré používa; `grant.py` odovzdáva len flagy, ktorých súbory existujú. | Rozšírenia sa pridávajú ako nové kľúče manifestu + nové checkery, nie ako nové CLI vetvy. |
| P5 | **Leak-safety je hranica pri balení.** De-anonymizácia sa deje až vo finalizácii; do gitu nikdy nejde reverzný kľúč (`*_.local.md`, `*.local.md` sú gitignored). | Anonymizačný sken je blokujúci krok pred `build_submission_package.py`. |
| P6 | **Legislatíva je verzia-pinnutá a citovateľná.** Intenzity/kategórie/lehoty derivujú z konkrétnej konsolidovanej verzie predpisu (GBER 651/2014, RRF 2021/241, schéma D1, SK RIS3 2021+). | Každé strojovo-kontrolovateľné pravidlo má `source` + `retrieved_at` + `version`. |
| **P7** | **Ground truth = oficiálne dokumenty; finálne dokumenty MUSIA presne spĺňať prílohy, výzvu a zákon.** Každý generovaný dokument (Opis 2b, rozpočet 2c, prílohy) sa odvodzuje z **tokenizovanej oficiálnej šablóny** a porovnáva sa s ňou na **štruktúrnu úplnosť** (`check_document_completeness` + `required-structure.yaml`) aj **compliance** (eligibility/timeline/intenzity/lehoty). | „Zelené výpočtové testy" ≠ úplný/vyhovujúci dokument. Žiadosť je hotová IBA keď `qc --mode final_publication` prejde completeness + compliance bránou. Nikdy negeneruj dokument ad-hoc (prózou); vždy z oficiálnej šablóny. |

### 1.3 Rozdelenie vrstiev

- **Vrstva NÁSTROJ (`tool/`, lokálny balík v tomto repe, výzvovo-neutrálny, oddelený od obsahu):** `grant.py`, `grantlib/` (`yamllite.py`, `schema.py`, `findings.py`, `csvio.py`, `paths.py` + nová `xlsxio.py`), `checks/check_call_requirements.py`, `checks/run_framework_qc.py`, `checks/build_publication.py`, `checks/build_submission_package.py`, `checks/validate_output_manifest.py` + **nové generické checkery** (`check_budget.py`, `check_aid_intensity.py`, `check_indicators.py`, `check_cross_document_consistency.py`, `check_anonymization_leaks.py`). Research submodul sa odpája; malé dependency-free moduly (`findings`, `schema`, `yamllite`, `csvio`, `paths`) sa jednorazovo skopírujú do `tool/grantlib/` so zachovaním atribúcie.
- **Vrstva OBSAH (tento repo):** `calls/<call>/` (knowledge base, SEMANTIC-MAP, `call-requirements.yaml`, `project.yaml`, `legislation.yaml`), `templates/`, agentické `skills/` a `workflows/`, lokálne anonymizačné kľúče (gitignored).

---

## 2) Architektúra a dátový model

### 2.1 Rozloženie repozitára (cieľový stav)

```
agentic-grantapp-framework/
├─ tool/                                  # NÁSTROJ (lokálny, v tomto repe) — nekopírovať sem obsah
│  ├─ grant.py                            # jednotný CLI: qc | pipeline | build | check | budget | ingest | anonymize
│  ├─ grantlib/
│  │  ├─ yamllite.py schema.py findings.py csvio.py paths.py
│  │  └─ xlsxio.py                        # NOVÉ: bezzávislý XLSX čítač/zapisovač (numeric-tolerant)
│  ├─ checks/
│  │  ├─ check_call_requirements.py       # rozšírená schéma v2 + nové check-loopy
│  │  ├─ check_budget.py                  # NOVÉ
│  │  ├─ check_aid_intensity.py           # NOVÉ
│  │  ├─ check_indicators.py              # NOVÉ
│  │  ├─ check_cross_document_consistency.py  # NOVÉ
│  │  ├─ check_anonymization_leaks.py     # NOVÉ
│  │  ├─ check_eligibility.py             # NOVÉ
│  │  ├─ run_framework_qc.py              # agreguje všetky nálezy → BLOCK/REVISE/PASS
│  │  ├─ build_publication.py             # + DOCX/XLSX render z modelu
│  │  ├─ build_submission_package.py      # visibility gate + leak-scan hook
│  │  └─ validate_output_manifest.py
│  └─ templates/study-manifest.yaml       # + nové path-kľúče
│
├─ templates/                             # OBSAH — šablóny na klonovanie
│  ├─ call-requirements-template.yaml     # v2 (budget/aid_intensity/indicators/consistency)
│  ├─ project-template.yaml               # NOVÉ: typový projektový model
│  └─ legislation-template.yaml           # NOVÉ: register externých zdrojov + pinning
│
├─ calls/
│  └─ 17I04-04-V05-RIS3/                  # KNOWLEDGE BASE výzvy
│     ├─ SEMANTIC-MAP.md                  # inventár faktov + kandidáti na requirements
│     ├─ ANONYMIZATION.md                 # schéma placeholderov
│     ├─ _anonymization-key.local.md      # gitignored reverzný kľúč
│     └─ source-md/
│        ├─ oficialne/  (01-vyzva…, 2b-…opis-projektu, 2c-…rozpocet, 4-…priklady-meratelnych-ukazovatelov,
│        │               5-…porovnavacia-tabulka, schema-vav-d1-final.md, casto-kladene-otazky-k-vyzve-2.md, …)
│        └─ ziadatel/    (vzor-modelove-vyhlasenie-…-msp…, elara-veduce-osoby.md, …)
│
├─ applications/                          # KONKRÉTNE ŽIADOSTI (klon examples/)
│  └─ <call>-<applicant>/
│     ├─ study_manifest.yaml
│     ├─ call-requirements.yaml           # v2, vyplnené pre danú výzvu
│     ├─ project.yaml                      # single source of truth
│     ├─ legislation.yaml                  # pinnutá legislatíva
│     ├─ manuscript/                       # sekcie Opisu (markdown)
│     ├─ budget/rozpocet.csv|.xlsx         # rozpočet
│     ├─ indicators/indicators.csv
│     ├─ references/source-registry.yaml   # track-record (VaV projekty, referencie)
│     ├─ annexes/                          # PDF/DOCX prílohy
│     └─ analysis/qc_reports/              # gitignored výstupy QC
│
└─ examples/modelova-vyzva-2026/           # demo skeleton na klonovanie
```

### 2.2 `call-requirements.yaml` v2 — rozšírená schéma

Rozširuje `CALL_REQUIREMENTS_SCHEMA` v `check_call_requirements.py` (dnes riadky 44–106) o nové top-level bloky, pri zachovaní `allow_unknown: False` (preklep = blocker). Existujúce bloky (`call`, `sections`, `annexes`, `eligibility`) ostávajú spätne kompatibilné.

```yaml
version: 2

call:
  name: "Výzva 17I04-04-V05-RIS3 (Digitálne Slovensko 2)"
  number: "17I04-04-V05"
  deadline: "2025-10-03"        # posunuté Usmernením č.1 z 19.9.2025 (pôvodne 30.9.2025)
  realization_deadline: "2026-06-30"   # koniec vecnej realizácie (NIE podanie)
  allocation_eur: 45000000
  regime: "A"                   # A = štátna pomoc | B = výskumná organizácia
  language: "sk"
  warn_days: 14

sections:                       # ako v1 + limity; RIS3 excelentnosť má max_words: null (bez limitu, FAQ ot.2)
  - id: "excelentnost_vychodiskova_situacia"
    title: "EXCELENTNOSŤ – Východisková situácia a relevantnosť cieľov"
    manuscript: "manuscript/40_excelentnost_vychodisko.md"
    required: true
  - id: "zhrnutie_abstrakt"
    title: "Zhrnutie (abstrakt)"
    manuscript: "manuscript/10_abstrakt.md"
    required: true
    min_words: 150
    max_words: 250

annexes:                        # required/optional + PDF page-limit; mapuje na source_doc-y knowledge base
  - id: "opis-projektu"
    title: "Opis projektu (Príloha č. 2 Zmluvy)"
    artifact: "annexes/2b-opis-projektu.docx"
    required: true
    format: "docx"              # NOVÉ: vynúti formát predloženia
  - id: "priloha-5-porovnavacia-tabulka"
    title: "Porovnávacia tabuľka (neprekrývanie s Komponentom 9)"
    artifact: "annexes/priloha-5.xlsx"
    required_if: "komponent9_history == true"   # NOVÉ: podmienená povinnosť

# ---- NOVÝ BLOK: rozpočet ----
budget:
  file: "budget/rozpocet.csv"
  currency: "EUR"
  vat_included: false           # DPH nie je oprávnený výdavok
  min_cov: 300000
  max_cov: 2200000
  work_packages: ["3-1", "3-2", "3-3", "3-4"]   # domény RIS3
  require_trl_per_wp: true      # každý použitý balík má TRL na začiatku
  categories:
    A: ["521", "551", "518", "920"]   # personál / odpisy / zmluvný výskum / paušál
    B: ["521", "940"]
  pausal:
    A: { code: "920", rate: 0.20, base_codes: ["521", "551", "518"] }
    B: { code: "940", rate: 0.40, base_codes: ["521"] }
  totals:
    sum_wp_equals_total: true   # SPOLU(3-1..3-4) == SPOLU oprávnené výdavky
    row_check: "celkove = pocet * jednotkova_cena"

# ---- NOVÝ BLOK: intenzita pomoci ----
aid_intensity:
  scheme_ref: "legislation.yaml#schema-vav-d1"
  category: "experimentalny_vyvoj"
  call_cap: 0.60                # strop VÝZVY (podmienka č.5)
  scheme_cap: 0.80             # absolútny strop schémy (čl. J)
  base_rate: 0.25
  size_uplift: { mikro: 0.20, maly: 0.20, stredny: 0.10, velky: 0.0 }
  region_uplift: 0.15          # čl. 107(3)(a), len mimo Bratislavského kraja
  region_uplift_condition: "miesto_realizacie != 'BA kraj'"
  regime_B_fixed: 0.60         # výskumná organizácia = 60% fix (nie 100%, FAQ ot.7)
  per_row_check: "narokovane = celkove * intenzita"
  effective_le_cap: true

# ---- NOVÝ BLOK: merateľné ukazovatele ----
indicators:
  file: "indicators/indicators.csv"
  min_main: 1
  max_main: 3
  min_secondary: 1
  max_secondary: 3
  max_total: 6
  require_dissemination_secondary: true   # aspoň 1 vedľajší o diseminácii
  fields: ["nazov","definicia","merna_jednotka","vychodiskova_hodnota","planovana_hodnota","typ"]
  plan_by: "2026-06-30"        # čas plnenia = koniec realizácie
  catalogue_ref: "calls/17I04-04-V05-RIS3/source-md/oficialne/4-…priklady-meratelnych-ukazovatelov.md"

# ---- NOVÝ BLOK: krížové kontroly (deklaratívne asercie proti project.yaml) ----
consistency:
  - id: "cov_opis_eq_rozpocet"
    left: "opis.financovanie.celkove_opravnene"
    right: "budget.total_cov"
    op: "eq"
  - id: "ppm_eq_sum_narokovane"
    left: "opis.financovanie.ziadana_ppm"
    right: "budget.sum_narokovane"
    op: "eq"
  - id: "spolufinancovanie"
    expr: "opis.financovanie.spolufinancovanie == budget.total_cov - budget.sum_narokovane"
  - id: "trl_koniec_6_8"
    expr: "6 <= project.trl_end <= 8"
  - id: "wp_opis_eq_budget"
    expr: "set(opis.work_packages) == set(budget.work_packages) == set(priloha5.work_packages)"
  - id: "personal_komp9_disjoint"
    expr: "disjoint(priloha5.komp9_personal, project.personnel)"   # personál Komp.9 ≠ personál Komp.17
  - id: "size_matches_msp"
    expr: "aid_intensity.size == msp.size_category"
  - id: "region_uplift_only_outside_ba"
    expr: "aid_intensity.region_uplift_applied implies project.miesto != 'BA kraj'"

# ---- ako v1: booleovská + rozšírená eligibilita ----
eligibility:
  - id: "vav_projekty_2r"
    description: "≥1 VaV projekt (režim A) / ≥2 (režim B) za 2 roky v doménach 3-1..3-4"
    met: true
    evidence: "references/source-registry.yaml"   # NOVÉ: odkaz na dôkaz
  - id: "msp_kvalifikacia"
    description: "Kvalifikácia MSP podľa vzor-modelove-vyhlasenie"
    computed: "check_eligibility.py::msp"          # NOVÉ: počítaná, nie ručne set
  - id: "neprekryvanie_komp9"
    description: "Aktivity/výstupy sa neprekrývajú s Komponentom 9 (Príloha 5)"
    met: true
```

### 2.3 `project.yaml` — typový projektový model (single source of truth)

```yaml
project:
  nazov: "…"
  skratka: "ELARA-AI"
  regime: "A"
  miesto_realizacie: "Košice - mestská časť Juh"   # → NIE BA kraj → región uplift OK
  trl_start: 4
  trl_end: 7
  prioritne_domeny: ["3-1", "3-2"]
applicant:
  nazov: "[ZIADATEL]"          # placeholder; reálna hodnota v _anonymization-key.local.md
  ico: "[ICO]"
  msp:
    zamestnanci: 8
    obrat_eur: 610914
    suvaha_eur: 645134
    size_category: "maly"       # počítané: <50 zam. a ≤10M€ → malý (mikro ak <10 & ≤2M€)
work_packages:
  - id: "3-1"
    trl_start: 4
    aktivity: [ {por: 1, nazov: "…", vystup: "…", zaciatok: "2025-11-01", koniec: "2026-03-31"} ]
personnel:
  - {meno: "[OSOBA_1]", pozicia: "hlavný AI architekt", fte: 1.0, cv: "annexes/cv_osoba1.pdf"}
milestones:
  - {por: 1, nazov: "…", aktivity: [1,2], koniec: "2026-06-30"}
```

### 2.4 `legislation.yaml` — register externých zdrojov + pinning

```yaml
sources:
  - id: "gber-651-2014"
    title: "Nariadenie (EÚ) 651/2014 (GBER)"
    url: "https://eur-lex.europa.eu/eli/reg/2014/651/oj/eng"
    consolidated_version: "2023-07-01"
    retrieved_at: "2026-07-08"
    used_for: ["aid_intensity.base_rate", "aid_intensity.size_uplift", "msp.definicia"]
  - id: "rrf-2021-241"
    title: "Nariadenie (EÚ) 2021/241 (RRF)"
    url: "https://eur-lex.europa.eu/eli/reg/2021/241/oj/eng"
    used_for: ["DNSH", "zakaz_dvojiteho_financovania"]
  - id: "schema-vav-d1"
    title: "Schéma štátnej pomoci VaV D1 (SA.113533)"
    local_copy: "calls/17I04-04-V05-RIS3/source-md/oficialne/schema-vav-d1-final.md"
    used_for: ["aid_intensity.scheme_cap", "kategorie_vydavkov"]
  - id: "sk-ris3-2021"
    title: "SK RIS3 2021+ (VAIA)"
    url: "https://vaia.gov.sk/sk/strategia-inteligentnej-specializacie-ris3-2/"
    used_for: ["prioritne_domeny", "suladovy_argument"]
```

`study_manifest.yaml` dostane nové path-kľúče (podľa vzoru `add_if_exists` v `grant.py`): `budget_file`, `aid_intensity_scheme`, `indicators_file`, `project_model`, `legislation_file`, `anonymization_key`.

---

## 3) Pipeline v 9 fázach

Každá fáza = agentický skill (viď §8), s deterministickými kontrolami na výstupe. Fázy 1–4 sú per-výzva (raz), fázy 5–9 per-žiadosť.

| Fáza | Názov | Vstup | Nástroj / skill | Výstup | Brána |
|------|-------|-------|-----------------|--------|-------|
| **F1** | **Ingest výzvy** | oficiálny balík (PDF/DOCX/XLSX) | `grant.py ingest` (obsah-skill) | `calls/<call>/source-md/**` (1:1 markdown), zoznam neextrahovateľných zdrojov | Password-protected/prázdny povinný zdroj → `blocker` (viď F1a) |
| **F2** | **Sémantická mapa** | source-md | skill `semantic-map` | `SEMANTIC-MAP.md` (alokácia, rozpočtový rozsah, lehoty, eligibilita, kandidáti na requirements) | manuálny review; každý fakt má odkaz na zdrojový súbor |
| **F3** | **Call-requirements** | SEMANTIC-MAP | skill `call-model` | `call-requirements.yaml` v2 | `grant.py check` → schéma validná (`allow_unknown:False`) |
| **F4** | **External retrieval + pinning** | `legislation.yaml` kostra | skill `legislation-retrieval` (WebFetch) | pinnutá legislatíva, intenzitné tabuľky ako dáta | freshness gate (viď §5) |
| **F5** | **Písanie sekcií Opisu** | `project.yaml`, knowledge base, legislatíva | skill `write-opis` (LLM) | `manuscript/*.md` | word/char limity per sekcia |
| **F6** | **Rozpočtové výpočty** | `project.yaml`, `aid_intensity`, `budget` bloky | `check_budget.py` + `check_aid_intensity.py` (výpočtový modul §4) | `budget/rozpocet.csv`, dopočítané `narokovane`, `spolufinancovanie` | riadkové/subtotal/total sumy, strop 300k–2,2M, cap 60% |
| **F7** | **Indikátory** | `project.yaml`, katalóg Prílohy 4 | `check_indicators.py` | `indicators/indicators.csv` | počty (1–3 hlavné, 1–3 vedľajšie, max 6), aspoň 1 diseminačný |
| **F8** | **QC brána (agregát)** | všetko vyššie | `run_framework_qc.py --mode {smoke,pre_word,final_publication}` | JSON+MD report v `analysis/qc_reports/`, rozhodnutie | `BLOCK` ak akýkoľvek `blocker` (podľa `--fail-on`) |
| **F9** | **Build + finalizácia + de-anonymizácia** | validovaný model | `build_publication.py` (DOCX/XLSX), leak-scan, `build_submission_package.py` | vyplnené 2b/2c/5, `package_manifest.csv` | leak-scan blocker + visibility gate |

**F1a — Handling neextrahovateľných zdrojov:** ingest musí explicitne emitovať `blocker` typu `locked_source` / `empty_required_section`, nie ticho vytvoriť prázdny súbor (poučenie z `vyzva-…-opis-projektu-ziadatel-fin.md`, ktorý ostal prázdny kvôli heslom chránenému PDF). Tento nález prežíva do F8.

---

## 4) Výpočtový modul (rozpočet, intenzity, paušál, spolufinancovanie, limity)

Bezzávislý, numeric-tolerant. Číta rozpočet cez novú `grantlib/xlsxio.py` (XLSX) alebo existujúcu `csvio.py` (CSV dump). Emituje typované `Finding` (severity podľa `grantlib/findings.py`) s `area="budget"` / `area="aid_intensity"`.

### 4.1 `check_budget.py`

Vstup: `budget.file`, blok `budget` z `call-requirements.yaml`, `project.regime`.

```
# Riadkové kontroly
R1  Celkove_opravnene_riadok  == Pocet_jednotiek * Jednotkova_cena          # major ak nesedí
R2  Kategória riadku ∈ budget.categories[regime]                            # blocker (A→521/551/518/920, B→521/940)
# Subtotal / total
R3  SPOLU(wp)  == Σ riadkov v danom WP                                      # major
R4  Σ SPOLU(3-1..3-4)  == SPOLU oprávnené výdavky                           # blocker
R5  total_cov == Σ všetkých 'Celkové oprávnené výdavky bez DPH'            # blocker
# Paušál
R6a A: riadok 920 == 0.20 * Σ(521+551+518)                                  # major (tolerancia ±0.01 €)
R6b B: riadok 940 == 0.40 * Σ(521)                                          # major
R6c Paušál nesmie byť súčasne 20% aj 40%                                    # blocker
# Envelope
R7  300000 <= total_cov <= 2200000  (bez DPH)                              # blocker
# TRL
R8  každý použitý WP má vyplnené TRL na začiatku                            # major
```

### 4.2 `check_aid_intensity.py`

Ruleset kľúčovaný `kategória × veľkosť podniku`, plnený z `legislation.yaml` (schéma D1 + GBER). Efektívna intenzita = `base + size_uplift[size] + (region_uplift ak mimo BA kraja)`, **capnutá `call_cap` (0,60)** a nikdy nad `scheme_cap` (0,80).

```
I1  intensity = base_rate + size_uplift[project.msp.size] + (region_uplift if miesto != 'BA kraj' else 0)
I2  effective = min(intensity, call_cap)                                    # výzva limituje exp. vývoj na 60%
I3  per-row: Narokovane_riadok == Celkove_riadok * effective (± tolerancia) # major
I4  Σ Narokovane <= call_cap * total_cov                                    # blocker ak prekročené
I5  regime B: ziadana_ppm == 0.60 * total_cov (fix)                         # blocker (nie 100%, FAQ ot.7)
I6  region_uplift uplatnený ⇒ project.miesto != 'BA kraj'                   # blocker (FAQ ot.8)
I7  size použitá v intenzite == size z modelového vyhlásenia MSP           # blocker
```

Referenčné hodnoty (režim A výzvy, exp. vývoj, mimo BA kraja): mikro/malý = 25+20+15 = **60 %** (=cap), stredný = 25+10+15 = **50 %**, veľký = 25+0+15 = **40 %**. Schéma (širší kontext, priemyselný výskum 70/60/50 + uplifty do 80 %) sa drží v ruleset dátach, ale výzva ho pre exp. vývoj limituje na 60 %.

### 4.3 Spolufinancovanie a top-line prehľad

```
S1  ziadana_ppm       = Σ Narokovane
S2  spolufinancovanie = total_cov - ziadana_ppm
S3  (ziadana_ppm + spolufinancovanie) == total_cov                         # invariant
S4  Tieto 3 sumy == 'Finančné prostriedky – celkový prehľad' v Opise (2b)  # → cross-check §6
```

---

## 5) Modul externých zdrojov (SK/EU retrieval + freshness)

Skill `legislation-retrieval` napĺňa a udržiava `legislation.yaml`. Zdroje a metóda podľa registra v analýze:

**SK:** MIRRI Plán obnovy – výzvy (`mirri.gov.sk/plan-obnovy/vyzvy/`) a harmonogram; SK RIS3 2021+ + VAIA metodické usmernenie k posudzovaniu súladu; ORSR/ŽR (identifikácia subjektu), RPVS (konečný užívateľ výhod), Register trestov (GP SR), ÚPV SR (IP indikátory), Finančná správa (status platiteľa DPH → oprávnenosť DPH).
**EU (EUR-Lex, ELI URL, konsolidovaná verzia):** GBER 651/2014, RRF 2021/241, Digital Europe 2021/694; JRC S3 Platform / Eye@RIS3.

**Pravidlá modulu:**
- **Fetch metóda:** `WebFetch` na verejné HTML/PDF; portálové kroky (ITMS2014+, slovensko.sk QES, výpis z RT) sú **manuálne** — modul ich označí `manual: true` a NEautomatizuje.
- **Pinning:** každý zdroj má `consolidated_version` + `retrieved_at`. Intenzitné tabuľky a definícia MSP sa ukladajú **ako dáta** (nie iba odkaz), aby ich `check_aid_intensity.py` mohol konzumovať bez sieťového volania.
- **Freshness gate (v QC):** ak `today - retrieved_at > freshness_window` (default 30 dní) → `minor`; ak výzva má vyššie-číslované `Usmernenie` než pinnuté → `blocker` (výzvy sa menia „za behu"); ak dokument je `manual` a starší než požadovaná platnosť (napr. výpis z RT > 3 mesiace) → `major`.
- **Non-overlap kontext:** modul dohľadá a pinne definíciu Komponentu 9 a doménovú taxonómiu 3-1..3-4, ktoré konzumuje krížová kontrola Prílohy 5.

---

## 6) QC brány (rozšírenie `check_call_requirements` + agregácia)

### 6.1 Rozšírenie schémy a check-loopov
V `check_call_requirements.py` sa k existujúcim nálezom (`missing_required_section` blocker, `section_over_limit` major, `missing_required_annex` blocker, `annex_over_page_limit` major, `eligibility_not_met` major, `deadline_passed` blocker / `deadline_near` minor) pridajú nové typy z blokov v2. `word_count`/`char_count` naďalej stripujú `[@key]` citácie pred počítaním (limity merajú prózu, nie citačné tokeny). `count_pdf_pages` (bezzávislý `/Count` regex) ostáva na page-limity príloh.

### 6.2 Nové checkery napojené do agregátu
`run_framework_qc.py` (dnes `load_module` + `findings.extend`, riadky ~185–249) dostane rovnakým vzorom:

| Checker | Kľúčové nálezy | Severity |
|---------|----------------|----------|
| `check_budget.py` | `budget_row_mismatch`, `budget_subtotal_mismatch`, `budget_out_of_envelope`, `pausal_wrong`, `category_not_allowed`, `wp_trl_missing` | blocker/major |
| `check_aid_intensity.py` | `intensity_over_cap`, `narokovane_mismatch`, `region_uplift_invalid`, `size_mismatch`, `regimeB_not_fixed_60` | blocker/major |
| `check_indicators.py` | `indicators_count_out_of_range`, `missing_main`, `missing_secondary`, `missing_dissemination_secondary`, `indicator_field_missing` | major/minor |
| `check_cross_document_consistency.py` | `cov_mismatch_opis_budget`, `ppm_mismatch`, `wp_set_mismatch`, `komp9_personal_overlap`, `trl_inconsistent` | blocker/major |
| `check_anonymization_leaks.py` | `unanonymized_pii`, `company_identifier_leak` | blocker |
| `check_document_completeness.py` (P7) | `required_section_missing` — built dokument nie je štruktúrne úplný voči oficiálnej šablóne (`required-structure.yaml`) | major/blocker |
| `check_eligibility.py` | `msp_size_mismatch`, `eligibility_not_met` (MSP, VaV, DNSH, dvojité financovanie, bezúhonnosť/EDES/podnik v ťažkostiach, OR zápis, max 1 žiadosť) | major |
| `check_timeline.py` | `activity_before_submission`, `activity_after_realization` (časová oprávnenosť) | major |
| `check_legislation.py` | `legislation_stale`, `legislation_unpinned`, `manual_doc_expired` (freshness) | major/minor |

Výstup: jediné rozhodnutie `BLOCK / REVISE / PASS_WITH_NOTES` + JSON a MD report do `analysis/qc_reports/` (gitignored). Módy: `smoke` (len blocker), `pre_word` (blocker+major), `final_publication` (blocker+major, plný set vrátane leak-scanu). Prah cez `--fail-on`.

### 6.3 Krížové kontroly (`check_cross_document_consistency.py`)
Vyhodnocuje deklaratívne asercie z bloku `consistency` proti `project.yaml`. Kľúčové (z analýzy `cross_checks`): COV(Opis) == SPOLU(2c); žiadaná PPM(Opis) == Σ Narokované(2c); spolufinancovanie == COV − PPM; TRL koniec 6–8 a > TRL začiatok; množina WP {Opis} == {rozpočet} == {Príloha 5}; personál Komp.9 (Príloha 5) ∩ personál projektu = ∅; veľkostná kategória v intenzite == MSP vyhlásenie; región uplift len mimo BA kraja; prioritná doména zaškrtnutá v Opise zodpovedá WP v rozpočte.

---

## 7) Anonymizácia

Trojkroková, s hranicou pri balení (P5).

1. **Detekcia (`check_anonymization_leaks.py`, blocker):** pred `build_submission_package.py` skenuje všetky artefakty regexom/PII/firemnými identifikátormi proti placeholder schéme z `ANONYMIZATION.md` (`[ZIADATEL]`, `[ICO]`, `[OSOBA_1]`…). Nájdený reálny (neplaceholdrovaný) identifikátor = `blocker`.
2. **Substitúcia:** pri konverzii/písaní sa reálne hodnoty nahrádzajú placeholdermi; reverzný kľúč žije iba lokálne (`_anonymization-key.local.md`, gitignored vzorom `*.local.md` / `*_.local.md`).
3. **Restore (de-anonymizácia, iba F9 finalizácia):** tesne pred generovaním finálnych 2b/2c/5 sa placeholdre nahradia reálnymi hodnotami z lokálneho kľúča (cesta `anonymization_key` z manifestu). De-anonymizovaný build sa NIKDY necommituje — je gitignored (`**/publication/*`).

`build_submission_package.py` naďalej kopíruje **iba riadky `include=true` AND `visibility=public`** z explicitného CSV manifestu, blokuje restricted artefakty, path-traversal (`..`/absolútne/mimo-root), duplicity a chýbajúce povinné zdroje; leak-scan je pridaný ako krok **pred** kopírovaním.

---

## 8) Agentický operačný model (skills + workflow)

**Jednotný vstup:** `python3 tool/grant.py <subcommand> --project-root <app>` — odvodí cesty z `study_manifest.yaml`, odovzdá len flagy existujúcich súborov (vzor `add_if_exists`). Nové subkomandy: `budget`, `ingest`, `anonymize`.

**Skills (vrstva OBSAH, `skills/`):**

| Skill | Fáza | Robí | Volá |
|-------|------|------|------|
| `ingest-call` | F1 | PDF/DOCX/XLSX → 1:1 markdown; označí locked/empty | `grant.py ingest` |
| `semantic-map` | F2 | inventár faktov → `SEMANTIC-MAP.md` | — |
| `call-model` | F3 | `SEMANTIC-MAP.md` → `call-requirements.yaml` v2 | `grant.py check` |
| `legislation-retrieval` | F4 | WebFetch + pinning → `legislation.yaml` | WebFetch |
| `write-opis` | F5 | LLM próza sekcií (§ Opis model) | — |
| `compute-budget` | F6 | naplní `project.yaml` → rozpočet | `grant.py budget` |
| `indicators` | F7 | výber + cieľové hodnoty | `check_indicators.py` |
| `qc-gate` | F8 | agregovaný QC beh | `grant.py qc --mode …` |
| `finalize` | F9 | de-anonymizácia + build + package | `build_publication.py`, `build_submission_package.py` |

**Deľba práce agent vs. determinizmus:** LLM navrhuje hodnoty a píše prózu; **všetky čísla, sumy, intenzity, počty a krížové asercie overuje deterministický checker** — agent nikdy neschvaľuje vlastný výstup. Slučka: `write/compute → qc → (REVISE) → oprava → qc`, kým rozhodnutie nie je `PASS_WITH_NOTES` v móde `final_publication`.

**Klonovanie novej žiadosti:** z `examples/modelova-vyzva-2026` (obsahuje `study_manifest.yaml`, `call-requirements.yaml`, `manuscript/`, `references/source-registry.yaml`, `annexes/`, committed `framework_qc_report` ukazujúci tvar brány) do `applications/<call>-<applicant>/`.

---

## 9) Akceptačné kritériá „hotovo"

Žiadosť je „hotová", keď platí súčasne:

**A. Štruktúra a limity**
- [ ] `grant.py check` → `call-requirements.yaml` prejde schémou v2 (`allow_unknown:False`, žiadny `blocker`).
- [ ] Všetky `required: true` sekcie existujú a sú neprázdne; žiadny `section_over_limit`; abstrakt 150–250 slov.
- [ ] Všetky povinné prílohy existujú v požadovanom formáte (DOCX 2b, XLSX 2c/5); žiadny `annex_over_page_limit`.

**B. Rozpočet a intenzity (výpočtový modul)**
- [ ] `300000 ≤ total_cov ≤ 2200000 €` bez DPH; `Σ SPOLU(3-1..3-4) == total_cov`; každý riadok `celkove = pocet * cena`.
- [ ] Paušál korektný podľa režimu (A: 920 = 20 %; B: 940 = 40 %); kategórie ∈ povolenej množiny; každý WP má TRL.
- [ ] `Narokovane_riadok = Celkove * effective`; `Σ Narokovane ≤ 60 % * COV`; režim B fix 60 %; región uplift len mimo BA kraja; veľkosť == MSP vyhlásenie.

**C. Indikátory**
- [ ] 1–3 hlavné + 1–3 vedľajšie (≤6), ≥1 hlavný, ≥1 vedľajší, ≥1 vedľajší diseminačný; všetky polia vyplnené; `planovana_hodnota` dosiahnuteľná do 30.6.2026.

**D. Krížová konzistencia**
- [ ] COV/PPM/spolufinancovanie zhodné medzi Opisom (2b) a rozpočtom (2c); WP zhodné naprieč Opis/rozpočet/Príloha 5; TRL koniec 6–8 a > začiatok; personál Komp.9 disjunktný s personálom projektu.

**E. Legislatíva a eligibilita**
- [ ] `legislation.yaml` pinnuje GBER/RRF/schému D1/SK RIS3 s `consolidated_version` + `retrieved_at`; freshness gate bez `blocker`; žiadne novšie nezohľadnené `Usmernenie`.
- [ ] Eligibilita počítaná (MSP, ≥1/2 VaV projekty za 2 roky v doménach 3-1..3-4 s dôkazom v `source-registry.yaml`, neprekrývanie Komp.9), nie iba ručne `met:true`.
- [ ] Lehota: `deadline` neprešla (`deadline_passed` = blocker); vecná realizácia ≤ 30.6.2026.

**F. Anonymizácia a balenie**
- [ ] `check_anonymization_leaks.py` bez `unanonymized_pii`/`company_identifier_leak`.
- [ ] `build_submission_package.py` zabalí iba `include=true AND visibility=public`; `package_manifest.csv` vytvorený; žiadny path-traversal/duplicita/chýbajúci zdroj; reverzný kľúč necommitnutý.

**G. Finálna brána**
- [ ] `run_framework_qc.py --mode final_publication --fail-on major` → `PASS_WITH_NOTES` (nikdy `BLOCK`/`REVISE`); JSON+MD report v `analysis/qc_reports/`.
- [ ] `build_publication.py` vyprodukuje DOCX (2b), XLSX (2c, 5) z modelu; žiadny surový `[@key]` neprežije v build výstupe; content-hashed snapshot + build log zapísané.

**Definícia „top-class":** systém replikuje RIS3 výsledok pre novú výzvu tak, že jediný ľudský zásah je poskytnutie projektových faktov (`project.yaml`) a lokálneho anonymizačného kľúča; všetko ostatné — ingest, sémantická mapa, requirements, retrieval legislatívy, próza, výpočty, kontroly, build a balenie — beží agenticky s deterministickou bránou ako záväzným arbitrom.

---

Relevantné súbory (absolútne cesty):
- Nástroj/schéma na rozšírenie: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/check_call_requirements.py` (schéma riadky 44–106)
- Agregátor QC: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/run_framework_qc.py`
- CLI dispatcher: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/grant.py`
- Builder/packager: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/tool/checks/build_publication.py`, `.../build_submission_package.py`
- Šablóna v1 na povýšenie na v2: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/templates/call-requirements-template.yaml`
- Knowledge base výzvy: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/calls/17I04-04-V05-RIS3/` (`SEMANTIC-MAP.md`, `ANONYMIZATION.md`, `source-md/oficialne/`, `source-md/ziadatel/`)
- Demo skeleton na klonovanie: `/Users/pavol.bielik/dev/src/github.com/pbielik/agentic-grantapp-framework/examples/modelova-vyzva-2026/`