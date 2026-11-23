# Token slovník — čo môžeš použiť v tokenizovaných šablónach

Šablóny (`templates/opis/<call>/opis-2b.md`, `templates/annexes/<call>/*.md`) sa vyplnia
deterministicky z modelu (`project.yaml` + `call-requirements.yaml` + rozpočet). Syntax: `{{token}}`.
Použi **iba tokeny z tohto zoznamu** (poskytuje ich `tool/checks/build_annexes.py::build_context`).
Neznámy token ostane nevyplnený (`{{token}}`) a `build` ho ohlási ako `⚠ nevyplnené tokeny`.

> Aktuálny zoznam vygeneruješ kedykoľvek: `python3 tool/grant.py --project-root <app> tokens`.

## Skalárne tokeny (jedna hodnota)

**Výzva** (`call:` blok v `call-requirements.yaml`):
`{{call.name}}` `{{call.number}}` `{{call.deadline}}` `{{call.realization_deadline}}`
`{{call.komponent}}` `{{call.investicia}}`

**Žiadateľ** (`applicant:` v `project.yaml`; identita = placeholdre do finalizácie):
`{{applicant.nazov}}` `{{applicant.ico}}` `{{applicant.dic}}` `{{applicant.ic_dph}}`
`{{applicant.pravna_forma}}` `{{applicant.platitel_dph}}` `{{applicant.statutar}}`
`{{applicant.adresa}}` `{{applicant.koresp_adresa}}` `{{applicant.iban}}` `{{applicant.banka}}`
`{{applicant.telefon}}` `{{applicant.email}}`

**Kontaktná osoba** (`kontakt:` v `project.yaml`):
`{{kontakt.meno}}` `{{kontakt.telefon}}` `{{kontakt.email}}`

**MSP** (`applicant.msp:`): `{{msp.zamestnanci}}` `{{msp.obrat_eur}}` `{{msp.suvaha_eur}}` `{{msp.size_category}}`

**Projekt** (`project:`): `{{project.nazov}}` `{{project.skratka}}` `{{project.miesto_realizacie}}`
`{{project.trl_start}}` `{{project.trl_end}}` `{{project.domeny}}` `{{project.obdobie}}` `{{project.dlzka_realizacie}}`

**Financie** (`financovanie:`): `{{financovanie.celkove_opravnene}}` `{{financovanie.ziadana_ppm}}`
`{{financovanie.spolufinancovanie}}`

**Intenzita:** `{{aid.effective}}` (vypočítaná efektívna intenzita, napr. „60 %")

## Obsah sekcií (próza z `manuscript/*.md`)

Pre každú sekciu v `call-requirements.yaml → sections[].id`:
`{{section.<id>}}` — vloží obsah `manuscript/*.md` (bez hlavného `###` nadpisu, podnadpisy `####` ostávajú).
Napr.: `{{section.abstrakt}}` `{{section.excelentnost}}` `{{section.dopad}}` `{{section.manazment}}` …

## Tabuľky a bloky (vlož ako celý markdown blok)

**Hlavičkové tabuľky Opisu 2b:** `{{tables.vykonavatel}}` `{{tables.programova_struktura}}`
`{{tables.identifikacia_ziadatel}}` `{{tables.financovanie_platba}}` `{{tables.kontaktne_osoby}}`
`{{tables.financny_prehlad}}` `{{tables.identifikacia_projekt}}` `{{tables.domeny_checklist}}` (☒/☐)
`{{tables.intenzita}}` (základ + veľkosť + región = spolu)

**Štruktúrované tabuľky:** `{{tables.aktivity}}` `{{tables.milniky}}` (s akceptačnými kritériami)
`{{tables.rizika}}` `{{tables.personnel}}` `{{tables.indikatory}}` `{{tables.vav}}` (referencie)

**Rozpočet:** `{{tables.rozpocet}}` (sumár po kategóriách) · `{{tables.rozpocet_ispo}}` (PPM vs vlastné zdroje)

**Plain-text zoznamy** (do buniek tabuliek, kde vnorená tabuľka rozbije layout):
`{{tables.aktivity_list}}` `{{tables.personnel_list}}`

> Ak potrebuješ nový token (napr. pre špecifickú prílohu inej výzvy), pridaj ho do `build_context`
> a doplň sem. Vždy over cez `build --target all` (žiadne `⚠ nevyplnené tokeny`).
