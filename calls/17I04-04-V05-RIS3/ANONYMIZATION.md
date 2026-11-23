# Anonymizácia — schéma placeholderov

Zdrojové dokumenty žiadateľa boli pri konverzii do markdownu **anonymizované**:
citlivé firemné a osobné identifikátory sú nahradené konzistentnými placeholdermi,
aby bola znalostná báza zdieľateľná a bezpečná pre prácu s AI agentom.

## Použité placeholdre

| Placeholder | Význam |
|---|---|
| `[ŽIADATEĽ]` | obchodný názov žiadateľa (firma) |
| `[IČO]` | IČO žiadateľa |
| `[DIČ]` | DIČ žiadateľa |
| `[ŠTATUTÁR]` | štatutárny orgán (meno) |
| `[OSOBA_1]`, `[OSOBA_2]` | mená kľúčových / vedúcich osôb projektu |
| `[PRIEZVISKO]` | zvyškové priezvisko bez kontextu |

## Čo NEbolo anonymizované (zámerne)
- **Názov projektu** ELARA-AI a jeho technický obsah (to sa bude editovať).
- **Oficiálne dokumenty výzvy** (verejné) — bez zmien.
- Verejné profesijné fakty v CV (názvy modelov/produktov, minulí zamestnávatelia).

## Reverzný kľúč
Mapovanie placeholder → **skutočná hodnota** je v súbore
`_anonymization-key.local.md`, ktorý je **v `.gitignore`** a do repa sa
**necommituje**. Slúži na spätné doplnenie reálnych údajov pri finalizácii žiadosti.

## Poznámka
- `source-md/ziadatel/…opis-projektu-ziadatel-fin.md` — pôvodne prázdny (PDF bolo chránené
  heslom); **odheslované 2026-07-08**, skonvertované (pdftotext) a **anonymizované** (placeholdre
  `[ZIADATEL]`, `[ICO]`, `[DIC]`, `[IC_DPH]`, `[STATUTAR]`, `[IBAN]`, `[TELEFON]`, `[EMAIL]`,
  `[ADRESA]`, `[BANKA]`). Reálne hodnoty sú len v gitignored `_anonymization-key.local.md`.
- Overené naším `check_anonymization_leaks` — bez PII leakov.
