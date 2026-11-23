# ELARA-AI — referenčná žiadosť (výzva 17I04-04-V05-RIS3)

End-to-end dôkaz, že framework replikuje vzorový RIS3 grant. Zostavené z faktov v
`calls/17I04-04-V05-RIS3/SEMANTIC-MAP.md`; všetky firemné/osobné údaje sú **placeholdre**
(reálne hodnoty len v gitignored `_anonymization-key.local.md`).

## Spustenie
```bash
python3 tool/grant.py --project-root applications/17I04-04-V05-RIS3-elara qc --mode final_publication
python3 tool/grant.py --project-root applications/17I04-04-V05-RIS3-elara build --target docx   # Opis 2b
python3 tool/grant.py --project-root applications/17I04-04-V05-RIS3-elara build --target xlsx   # rozpočet 2c
```

## Čo brána overuje (a s akým výsledkom)
- **Rozpočet:** COV 1 056 000 € (v rozsahu 300 k–2,2 M), paušál 20 % zo Σ(521+551+518), riadková aritmetika → PASS.
- **Intenzita:** režim A, malý podnik, Košice (mimo BA) → efektívna **60 %**; nárokované 633 600 € = 60 % COV → PASS.
- **Indikátory:** 2 hlavné + 1 diseminačný vedľajší → PASS.
- **Krížové kontroly:** COV/PPM/spolufinancovanie (Opis↔rozpočet), TRL 7 ∈ [6,8], WP {3-1,3-2} zhodné → PASS.
- **MSP:** vypočítané `maly` = deklarované → PASS. **Legislatíva:** GBER/RRF/schéma/MIRRI pinnuté, fresh → PASS.
- **Termín:** `deadline_passed` **BLOCKER** — výzva je od 3. 10. 2025 **CLOSED** (overené na MIRRI). Pred termínom
  (`--today 2025-09-15`) žiadosť prechádza. Toto je korektné správanie brány, nie chyba obsahu.

## Prílohy
Externé prílohy (CV, čestné vyhlásenie, výpis z RT) sa dodávajú pri podaní — v tomto drafte
`required: false`. Príloha 5 (neprekrývanie s Komp. 9) je podmienená (`required_if`).
