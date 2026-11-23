---
name: legislation-retrieval
description: >-
  Dohľadá a pinne relevantnú SK/EÚ legislatívu pre grantovú žiadosť (GBER 651/2014,
  RRF 2021/241, schéma pomoci, SK RIS3, MIRRI výzvy) cez WebFetch do legislation.yaml
  s consolidated_version + retrieved_at. Použi keď treba overiť/aktualizovať právny
  rámec výzvy alebo keď freshness gate hlási zastaraný/nepinnutý zdroj.
---

# legislation-retrieval — dohľadanie a pinning legislatívy (F4)

## Kedy
Na začiatku práce s novou výzvou (naplniť `legislation.yaml`) a kedykoľvek QC hlási
`legislation_stale` / `legislation_unpinned` / `manual_doc_expired`.

## Princíp
Agent (WebFetch) navrhuje a pinne hodnoty; deterministický **freshness gate**
(`tool/checks/check_legislation.py`) je záväzný arbiter aktuálnosti. Každé strojovo
kontrolovateľné pravidlo (intenzity, MSP, lehoty) musí mať v `legislation.yaml`
`source` + `retrieved_at` + `consolidated_version`.

## Postup
1. Vyjdi z `templates/legislation-template.yaml` (kostra so SK/EÚ zdrojmi a `used_for`).
2. Pre každý verejný zdroj urob **WebFetch** na kanonickú URL a over/zapíš:
   - EÚ (EUR-Lex ELI): GBER `2014/651`, RRF `2021/241`, Digital Europe `2021/694` —
     zapíš `consolidated_version` (napr. GBER = **2023-07-01**, overené).
   - SK: MIRRI `plan-obnovy/vyzvy/` (stav výzvy + Usmernenia), VAIA RIS3 + metodické usmernenie.
   - Nastav `retrieved_at` na dnešný dátum.
3. Portálové/autentifikované kroky (ITMS2014+, slovensko.sk QES, výpis z RT) NEautomatizuj —
   nechaj ako `manual_portals` s `validity` (napr. výpis z RT „3 mesiace“).
4. Intenzitné tabuľky a definíciu MSP ulož **ako dáta** do `call-requirements.yaml`
   (`aid_intensity`/`budget`), aby ich checkery čítali bez siete.
5. Spusti gate: `python3 tool/grant.py --project-root <app> qc` → nesmie hlásiť
   `legislation_stale`/`manual_doc_expired`.

## Poznámky
- WebFetch je US-only; EUR-Lex aj `mirri.gov.sk` sú dostupné (overené).
- Novšie `Usmernenie` výzvy než pinnuté je **blocker**, ktorý posúdi agent (porovná
  MIRRI stránku so stavom v `legislation.yaml`) — deterministický gate rieši len vek pinu.
