# budget-demo — ukážka rozpočtových výpočtov (NASTROJ-C1)

Minimálny v2 projekt (režim A), ktorý spúšťa deterministický rozpočtový checker.

```bash
python3 tool/grant.py --project-root examples/budget-demo qc --mode pre_word   # call-req + rozpočet
python3 tool/grant.py --project-root examples/budget-demo budget                # len rozpočet
```

Rozpočet (`budget/rozpocet.csv`): Personál 400 000 + Zmluvný výskum 100 000 +
Paušál 100 000 (= 20 % zo Σ 521+518) → **SPOLU 600 000 €** (v rozsahu 300 k–2,2 M).
Checker overuje: `celkove = počet × cena`, kategórie povolené pre režim, paušál
podľa sadzby, envelope. Skús zmeniť číslo v CSV → uvidíš `major`/`blocker` nález.
