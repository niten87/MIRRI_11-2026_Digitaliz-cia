---
name: content-review
description: >-
  Agentická QC nad OBSAHOM žiadosti (nie čísla/štruktúra — tie rieši deterministická brána).
  Prísny hodnotiteľ posúdi relevanciu, vecnosť a kvalitu generovaných dokumentov voči
  hodnotiacim kritériám výzvy (excelentnosť/dopad/implementácia) + compliance obsah.
  Použi pred podaním alebo keď operátor povie "skontroluj obsah", "review", "/content-review".
---

# content-review — agentická QC nad obsahom

## Prečo (a čím sa líši od `qc`)
`tool/grant.py qc` (deterministická brána) overuje **čísla, štruktúru a compliance-pravidlá**,
ale NEvie posúdiť, či je **obsah relevantný, vecný a bodovo silný**. To vie len hodnotiteľ-agent.
Táto vrstva odhalí generický/tenký/nesúladný obsah, ktorý by znížil body — skôr než ho uvidí komisia.

## Kedy
Pred podaním každej žiadosti; automaticky beží aj ako fáza `grant-prep` workflow (po QC bráne).

## Ako spustiť
```
Workflow({ scriptPath: "workflows/content-review.workflow.js",
           args: { projectRoot: "applications/<call>-<applicant>", call: "17I04-04-V05-RIS3" } })
```
Workflow paralelne spustí prísnych hodnotiteľov pre každé kritérium:
- **EXCELENTNOSŤ** — východisková situácia, relevancia cieľov, metodika, TRL trajektória, inovatívnosť, SWOT.
- **DOPAD** — merateľné výsledky (KPI), udržateľnosť, komercializácia, ekosystém, komunikačný/diseminačný plán.
- **IMPLEMENTÁCIA** — realistickosť harmonogramu/míľnikov, primeranosť rozpočtu (vecný popis), riziká, kapacity.
- **COMPLIANCE OBSAH** — DNSH, neprekrývanie s Komp. 9, dvojité financovanie, súlad s RIS3, ochrana IP.

Každý agent: kalibruje voči reálnemu vyplnenému vzoru, vráti **rating 1–5** a **konkrétne nálezy**
(generický/tenký/nerelevantný obsah + čo doplniť/prepísať), zoradené podľa dopadu na body.

## Ako to zapadá do „hotovo"
1. `build --target all` → `qc --mode final_publication` (deterministická brána: čísla/štruktúra/compliance).
2. **content-review** (agentická brána: relevancia/kvalita obsahu).
3. Oprav nálezy (prepíš prózu v `manuscript/*.md`, nemeň čísla, nezavádzaj PII) → build → qc → review.
4. Žiadosť je pripravená na podanie, keď **obidve brány** sú čisté a ratingy sú silné.

> Deľba: LLM navrhuje a hodnotí obsah; **deterministická brána zostáva arbitrom čísel/štruktúry**.
> Content-review NEmení čísla — len upozorňuje na slabý obsah a navrhuje jeho zlepšenie.
