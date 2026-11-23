---
name: grant-prep
description: >-
  Priprav grantovú žiadosť tak, aby FINÁLNE DOKUMENTY PRESNE SPĹŇALI požiadavky
  príloh, výzvy a zákonné/schémové požiadavky. Generuj z oficiálnych šablôn,
  prežeň completeness + compliance bránou a iteruj, kým final_publication nie je PASS.
  Použi keď operátor povie "priprav žiadosť", "vypracuj grant", "nová žiadosť" alebo "/grant-prep".
---

# grant-prep — príprava grantovej žiadosti (compliance-first)

## Základný princíp (o tomto je celý framework)
**Finálne dokumenty musia PRESNE spĺňať požiadavky príloh, textu výzvy a zákonných/
schémových požiadaviek.** Nie „približne", nie „prózou". Každý generovaný dokument
(Opis 2b, rozpočet 2c, všetky prílohy) sa porovnáva s **oficiálnou šablónou = ground truth**
a musí byť **štruktúrne úplný aj obsahovo v súlade**.

> ⚠️ Poučenie (2026-07-09): nikdy negeneruj dokument „ad-hoc" (len prózu + jedna tabuľka).
> VŽDY generuj z **tokenizovanej šablóny odvodenej z oficiálneho dokumentu** a over
> **completeness bránou**. Zelené výpočtové testy ≠ úplný/vyhovujúci dokument.

## Železné pravidlá
1. **Ground truth = oficiálne dokumenty výzvy** v `calls/<call>/source-md/oficialne/`
   (2b Opis, 2c rozpočet, prílohy 1/3/5, schéma pomoci) + text výzvy + FAQ. Z nich sa
   odvodzujú tokenizované šablóny (`templates/opis/<call>/`, `templates/annexes/<call>/`).
2. **Generuj z šablón, nie z hlavy.** Opis aj prílohy = tokenizovaná oficiálna štruktúra
   vyplnená z modelu (`project.yaml` + dopočítané financie). Žiadne chýbajúce hlavičkové
   tabuľky, žiadne rozpadnuté tabuľky.
3. **Completeness gate je povinný.** `check_document_completeness.py` overuje built
   dokumenty voči `templates/opis/<call>/required-structure.yaml` (povinné sekcie/tabuľky).
   Ak niečo chýba → oprav šablónu/model, nie manifest.
4. **Compliance gate je povinný.** Všetky zákonné/schémové podmienky sú v `eligibility`
   a checkeroch: MSP, ≥1/2 VaV projekty, neprekrývanie s Komp. 9, DNSH, zákaz dvojitého
   financovania, bezúhonnosť/EDES/podnik v ťažkostiach, TRL 6–8, intenzita ≤ 60 %,
   časová oprávnenosť (výdavky až odo dňa podania), lehoty.
5. **Deterministická brána je arbiter.** LLM navrhuje; `tool/grant.py qc` rozhoduje.
   Nikdy neschvaľuj vlastný výstup. Čísla overuje checker.
6. **Reálne PII sa nepíšu** — iba placeholdre; reálne hodnoty len v gitignored kľúči/profile.

## Postup
1. **Over vstupy:** `project.yaml` (vrátane identifikácie, kontaktu, MSP, work_packages,
   aktivít s dátumami, míľnikov, rizík), `call-requirements.yaml` v2, knowledge base výzvy.
   Firmu načítaj z `applicants/` (`grant.py applicant key --company <id>`).
2. **Generuj celý balík:**
   ```
   python3 tool/grant.py --project-root <app> build --target all
   ```
   (Opis 2b + rozpočet 2c + všetky prílohy z oficiálnych tokenizovaných šablôn.)
3. **Prežeň FINÁLNU bránu** (musí obsahovať completeness + compliance):
   ```
   python3 tool/grant.py --project-root <app> qc --mode final_publication --fail-on major
   ```
   Rieš KAŽDÝ blocker/major: chýbajúca sekcia (completeness), nesúlad čísel (budget/
   intensity/cross-doc), nesplnená podmienka (eligibility/timeline), leak (anonymizácia).
   Slučka `oprav → build → qc`, kým nie je `PASS_WITH_NOTES`.
4. **Adversariálny audit pred podaním (povinné pri „top kvalite"):** spusti audit workflow,
   ktorý porovná generované dokumenty s oficiálnymi šablónami + textom výzvy a hľadá
   chýbajúce/nesprávne veci (viď `workflows/`). Potvrdené nálezy oprav.
5. **Finalizácia:** de-anonymizuj z `_anonymization-key.local.md`, znovu build, zabaľ
   submission package. De-anonymizovaný build sa NIKDY necommituje.

## „Hotovo" = definícia
Žiadosť je hotová IBA keď:
- `qc --mode final_publication --fail-on major` → `PASS_WITH_NOTES` (žiadny blocker/major),
- **completeness PASS** (všetky povinné časti Opisu/príloh prítomné voči oficiálnej šablóne),
- **compliance PASS** (všetky eligibility podmienky + timeline + intenzity + lehoty),
- žiadny anonymizačný leak, a build vyprodukoval Opis 2b (DOCX) + rozpočet 2c (XLSX) + prílohy.

Ak čokoľvek z toho neplatí, žiadosť **nie je** pripravená na podanie — bez ohľadu na to,
ako „dobre vyzerá" próza.

## Keď pridávaš NOVÚ výzvu
1. Ingestuj oficiálne dokumenty do `calls/<call>/source-md/oficialne/` (1:1 markdown).
2. Odvoď tokenizované šablóny (Opis 2b, prílohy) z oficiálnych dokumentov.
3. Vytvor `templates/opis/<call>/required-structure.yaml` (povinné sekcie/tabuľky = ground truth).
4. Zakóduj VŠETKY tvrdé podmienky výzvy do `call-requirements.yaml` (eligibility/limity/lehoty).
5. Over, že `build --target all` + `qc final_publication` dá kompletný, vyhovujúci balík.
