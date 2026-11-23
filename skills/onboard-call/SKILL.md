---
name: onboard-call
description: >-
  Pridaj NOVÚ grantovú výzvu do frameworku tak, aby z nej vedel generovať kompletné,
  štruktúrne verné a súladu-spĺňajúce dokumenty (Opis + rozpočet + všetky prílohy).
  Použi po forknutí repa alebo keď operátor povie "nová výzva", "pridaj výzvu", "/onboard-call".
---

# onboard-call — pridanie novej výzvy (fork → funkčná výzva)

Toto je **opakovateľný postup**, ktorý sa robí RAZ na výzvu. Cieľom je, aby potom `new-application`
+ `build --target all` + `qc` vygenerovali kompletný, vyhovujúci balík pre ľubovoľného žiadateľa.

> **Automatizovane:** celý postup (od kroku 2 nižšie) vykoná multi-agentný workflow —
> `Workflow({ scriptPath: "workflows/onboard-call.workflow.js", args: { call: "<ČÍSLO>" } })`.
> Prerekvizita: ingestované oficiálne dokumenty (krok 1). Výstup workflowu VŽDY skontroluj
> (najmä required-structure a tvrdé podmienky v call-requirements) pred commitom.
> Fork checklist: `docs/FORKING.md`.

> Princíp P7: **ground truth = oficiálne dokumenty výzvy.** Generuj z tokenizovaných oficiálnych
> šablôn, nie ad-hoc. Slovník tokenov: `docs/TOKENS.md` (alebo `grant.py --project-root <app> tokens`).

## Kroky

**0. Kostra:**
```
python3 tool/grant.py new-call <ČÍSLO-VÝZVY>
```
Vytvorí `calls/<č>/`, `templates/opis/<č>/{opis-2b.md, required-structure.yaml}`, `templates/annexes/<č>/annexes.yaml`.

**1. Ingest oficiálnych dokumentov** → `calls/<č>/source-md/oficialne/` ako **1:1 markdown**
(text výzvy, 2b Opis, 2c rozpočet, prílohy 1/3/5, formulár žiadosti, schéma pomoci, FAQ).
Anonymizuj dokumenty žiadateľa (`ziadatel/`) placeholdrami (viď `ANONYMIZATION.md`).

**2. Sémantická mapa** → `calls/<č>/SEMANTIC-MAP.md`: inventár dokumentov + kľúčové fakty
(alokácia, limity min/max, lehoty podania a realizácie, oprávnený žiadateľ, kategórie výdavkov,
intenzity, merateľné ukazovatele, povinné prílohy, tvrdé podmienky). Každý fakt s odkazom na zdroj.

**3. Tokenizuj Opis 2b** → `templates/opis/<č>/opis-2b.md`: zober **oficiálnu 2b šablónu**, zachovaj jej
štruktúru (hlavičkové tabuľky, sekcie, tabuľky aktivít/míľnikov/rizík/indikátorov) a hodnoty nahraď
tokenmi z `docs/TOKENS.md`. Reálne firemné/osobné údaje NIKDY nevkladaj — len identita tokeny.

**4. Tokenizuj prílohy** → `templates/annexes/<č>/<id>.md` pre KAŽDÚ vyplniteľnú prílohu (čestné
vyhlásenie, MSP, výpis RT, porovnávacia tabuľka, formulár žiadosti, CV, doklad o VaV…), zaregistruj
ich v `annexes.yaml`. Kalibruj podľa vyplnených vzorov v `ziadatel/` (ak sú).

**5. Povinná štruktúra** → `templates/opis/<č>/required-structure.yaml`: zoznam povinných častí Opisu
(a príloh), ktoré MUSIA byť v generovanom dokumente. Toto je automatická poistka úplnosti
(`check_document_completeness`). Odvoď markery z oficiálnej 2b.

**6. Zakóduj podmienky výzvy** (per žiadosť) → `call-requirements.yaml` v2: sekcie+limity, prílohy
(`required`), `budget` (kategórie, paušál, envelope), `aid_intensity` (base+size+region+cap),
`indicators`, `consistency`, `eligibility` (VŠETKY tvrdé podmienky: MSP, VaV, DNSH, neprekrývanie,
dvojité financovanie, bezúhonnosť, lehoty), `scoring`. Ak niečo v checkeroch chýba, pridaj generický
checker do `tool/checks/` (žiadny výzvový fakt v kóde!).

**7. Over end-to-end:**
```
python3 tool/grant.py new-application <č> <testfirma>
# vyplň project.yaml + rozpočet + sekcie (placeholdrami / [DOPLNIŤ])
python3 tool/grant.py --project-root applications/<č>-<testfirma> build --target all
python3 tool/grant.py --project-root applications/<č>-<testfirma> qc --mode final_publication --fail-on major
```
Cieľ: **žiadne `⚠ nevyplnené tokeny`**, completeness PASS, compliance PASS.

**8. Adversariálny audit (odporúčané):** spusti audit workflow — porovná generované dokumenty s
oficiálnymi šablónami a nájde chýbajúce/nesprávne veci (vzor: `workflows/…audit…`). Potvrdené oprav.

## Hotovo, keď
Nová výzva má: tokenizovaný Opis 2b + prílohy, `required-structure.yaml`, kompletný `call-requirements`,
a testovacia žiadosť prejde **oboma bránami** (deterministickou + `content-review`). Potom je výzva
pripravená na reálne žiadosti.
