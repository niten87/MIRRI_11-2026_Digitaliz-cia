# skills/ — agentické skilly (vrstva OBSAH)

9 skillov mapuje 9-fázovú pipeline zo `docs/SPEC-grantapp.md §3, §8`. Deľba: **LLM navrhuje
prózu/hodnoty, deterministická brána (`tool/grant.py qc`) rozhoduje** — skill nikdy neschvaľuje
vlastný výstup.

> **Compliance-first (P7):** finálne dokumenty MUSIA presne spĺňať prílohy, výzvu a zákon.
> Generuj z **oficiálnych tokenizovaných šablôn** (nie ad-hoc prózou) a over **completeness**
> (`check_document_completeness` vs `required-structure.yaml`) + **compliance** (eligibility/
> timeline/intenzity/lehoty). „Hotovo" = `qc --mode final_publication` PASS. Viď `grant-prep/SKILL.md`.

| Skill | Fáza | Robí | Volá | Stav |
|-------|------|------|------|------|
| `ingest-call` | F1 | PDF/DOCX/XLSX → 1:1 markdown do `calls/<call>/source-md/`; označí locked/empty ako blocker | `tool/grant.py ingest` | 🔲 OBSAH-G1 |
| `semantic-map` | F2 | inventár faktov → `SEMANTIC-MAP.md` (každý fakt s odkazom na zdroj) | — | 🔲 OBSAH-G2 |
| `call-model` | F3 | `SEMANTIC-MAP.md` → `call-requirements.yaml` v2 | `tool/grant.py check` | 🔲 OBSAH-G3 |
| `legislation-retrieval` | F4 | WebFetch + pinning → `legislation.yaml` (+ freshness gate) | WebFetch, `tool/checks/check_legislation.py` | ✅ OBSAH-H1/H3 |
| `write-opis` | F5 | próza sekcií Opisu | — | 🔲 OBSAH-F3 |
| `compute-budget` | F6 | naplní `project.yaml` → rozpočet + intenzity | `tool/grant.py budget` | 🔲 OBSAH-F3 |
| `indicators` | F7 | výber ukazovateľov + cieľové hodnoty | `tool/checks/check_indicators.py` | 🔲 OBSAH-F3 |
| `qc-gate` | F8 | agregovaný QC beh + rozhodnutie | `tool/grant.py qc --mode …` | 🔲 OBSAH-F4 |
| `finalize` | F9 | de-anonymizácia + build + submission package | `tool/checks/build_publication.py`, `tool/checks/build_submission_package.py` | 🔲 OBSAH-F4 |

**Pridanie novej výzvy (fork):** `onboard-call/` (viď `onboard-call/SKILL.md`) — opakovateľný postup
scaffold → tokenizuj oficiálne šablóny → zakóduj podmienky → over. Kostra: `grant.py new-call` /
`new-application`; slovník tokenov: `docs/TOKENS.md`; startery: `templates/_starters/`.

**Dve QC brány:**
- **Deterministická** (`tool/grant.py qc`) — čísla, štruktúra (completeness vs oficiálna šablóna), compliance-pravidlá. Automaticky.
- **Agentická nad obsahom** (`content-review/` + `workflows/content-review.workflow.js`) — prísny hodnotiteľ posúdi
  relevanciu/vecnosť/kvalitu obsahu voči kritériám výzvy (excelentnosť/dopad/implementácia + compliance obsah).
  Beží ako fáza `grant-prep` aj samostatne pred podaním. Žiadosť je hotová, keď sú **obidve** brány čisté.

**Zastrešujúci vstup:** `grant-prep/` (viď `grant-prep/SKILL.md`) — riadi celý per-žiadosť
beh cez orchestračný workflow `workflows/grant-prep.workflow.js` so slučkou REVISE + content-review fázou.

**Per-výzva (F1–F4) vs. per-žiadosť (F5–F9):** F1–F4 sa robia raz na výzvu (naplnia
`calls/<call>/`); F5–F9 sa opakujú pre každú žiadosť v `applications/<call>-<applicant>/`.
