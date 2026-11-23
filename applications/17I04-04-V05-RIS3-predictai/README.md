# PredictAI — žiadosť (výzva 17I04-04-V05-RIS3)

Prediktívna platforma pre digitálnu transformáciu priemyselnej výroby (ERP + IoT → AI → dashboard).
Zostavené frameworkom z detailov projektu; firemné údaje sú **placeholdre** (doplniť z registra firiem).

## Spustenie
```bash
python3 tool/grant.py --project-root applications/17I04-04-V05-RIS3-predictai qc --mode final_publication
python3 tool/grant.py --project-root applications/17I04-04-V05-RIS3-predictai build --target all   # Opis 2b + rozpočet 2c + VŠETKY prílohy
```
`--target all` vygeneruje do `publication/`: `opis.docx` (Opis 2b), `rozpocet.xlsx` (rozpočet 2c) a
`annexes/` — Čestné vyhlásenie (Príloha 1), Údaje na výpis z RT (Príloha 3), Porovnávaciu tabuľku
(Príloha 5), MSP vyhlásenie a ISPO žiadosť o PPM. Identita ostáva placeholdrom do finalizácie.

## Kľúčové čísla (overené bránou)
- **COV 2 086 000 €** (v rozsahu 300 k–2,2 M), paušál 20 % zo Σ(521+518+551) = 347 666,67 €.
- **Intenzita 60 %** (režim A, malý podnik, mimo BA); nárokované **1 251 600 €**, spolufinancovanie **834 400 €**.
- Domény RIS3: **3-1, 3-2, 3-3**. TRL 6 → 7–8. 6 aktivít / 6 míľnikov (M1–M6).
- Indikátory: 2 hlavné + 3 vedľajšie (1 diseminačný). MSP: vypočítané `malý` = deklarované.

## ⚠️ Predpoklady na potvrdenie
- **Žiadateľ (firma):** placeholdre `[ZIADATEL]`/`[ICO]`/… — doplň z `applicants/companies.local.yaml`.
- **MSP čísla** (zamestnanci/obrat/súvaha) a **miesto realizácie (mimo BA)** sú predpoklady odvodené
  z cieľovej intenzity 60 % — potvrď reálne hodnoty.
- **Termín:** výzva 17I04-04-V05 bola CLOSED (3. 10. 2025) → `deadline_passed` blocker. Ak je nový
  termín/kolo, uprav `call.deadline`. Pred termínom (`--today 2025-09-15`) žiadosť prechádza.

## Rozpočet — významné položky
Personál/vývoj (521): 1 404 300 € · Externé testovanie a validácia (518): 212 289 € ·
Odpisy IoT/HW (551): 121 744,33 € · Paušál (920): 347 666,67 €.
