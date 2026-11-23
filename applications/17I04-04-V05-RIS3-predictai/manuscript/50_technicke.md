### Technické riešenie projektu, jeho udržateľnosť a potenciál využitia

#### 1. Architektúra a spôsob implementácie
Platforma PredictAI je navrhnutá ako modulárne riešenie s otvorenými rozhraniami, pozostávajúce
zo štyroch hlavných komponentov:

- **A1 – Dátová integrácia (ERP + IoT):** API konektory pre podnikové ERP systémy a IoT senzory,
  jednotná dátová pipeline (zber, normalizácia, čistenie, verziovanie), edge/cloud spracovanie a
  dátový model výrobných procesov.
- **A2 – Prediktívne AI/ML modely:** modely na predikciu porúch a prestojov (anomaly detection,
  time-series forecasting, remaining useful life), optimalizáciu procesov a energetickú optimalizáciu;
  tréning na doménových dátach s priebežnou validáciou.
- **A3 – Real-time dashboard a orchestrácia:** vizualizácia stavu výroby, prediktívnych výstupov a
  odporúčaní; alerting, prehľady KPI, rozhrania pre operátorov a manažment; audit a telemetria.
- **A4 – Projektový manažment a QA:** riadenie rizík, dokumentácia, monitorovacie správy, reporting.

Implementácia prebieha fázovo: analýza ERP a návrh architektúry → vývoj konektorov a pipeline →
tréning modelov → integrácia a dashboard → pilotná validácia v prevádzke, s priebežnými
integračnými míľnikmi, aby sme rýchlo iterovali a udržali realistický TRL postup.

#### 2. Vedecké prístupy a metodika riešenia
- **Dáta a príprava:** kurácia dát z ERP a IoT senzorov, čistenie a normalizácia, riešenie
  chýbajúcich/nekonzistentných hodnôt, syntetické dopĺňanie a verziovanie datasetov; privacy-by-design
  a súlad s GDPR/AI Act.
- **Prediktívne modely:** kombinácia štatistických a ML metód (detekcia anomálií, forecasting,
  klasifikácia porúch, odhad zostávajúcej životnosti zariadení); výber modelov podľa charakteru
  signálu a validácia na reálnych/pilotných dátach.
- **Optimalizácia a energetika:** modely pre optimalizáciu výrobných parametrov a znižovanie
  energetickej náročnosti; vyhodnocovanie kompromisu medzi priepustnosťou, kvalitou a spotrebou.
- **Integrácia a nasadenie:** štandardizované API, orchestrácia dátových tokov, real-time inferencia,
  monitoring modelov (drift), spätná väzba operátorov (human-in-the-loop).

#### 3. Relevancia metodiky k cieľu a očakávaným výsledkom — TRL trajektória
Postupným experimentálnym overovaním zvyšujeme úroveň pripravenosti technológie z TRL 6 na TRL 7
s jasne definovanými dôkazmi na každom stupni:

- **TRL 6 (východisko):** overený model/komponenty v relevantnom prostredí — existujúce PoC
  prediktívnej analytiky a dátovej integrácie (validované na historických dátach).
- **prechod TRL 6 → 7:** integrácia komponentov do platformy a **pilotné nasadenie v jednej reálnej
  prevádzke** s auditovanými metrikami (M5: prestoje ≥ 20 %, energia ≥ 10 %; M3: presnosť ≥ 85 %).
- **TRL 7 (cieľ):** prototyp platformy **overený v relevantnom prevádzkovom prostredí** — audit TRL 7
  na konci projektu (M6) so záverečnou technickou správou.
- **ambícia TRL 8 (stretch):** kvalifikovaný systém v plnom prevádzkovom prostredí pre vybrané
  scenáre — reálne dosiahnuteľné len pri [DOPLNIŤ: podmienky/rozsah pilotu], preto sa nezaväzuje ako cieľ.

Otvorené API a modulárna architektúra zabezpečujú prenositeľnosť riešenia do ďalších podnikov a ERP prostredí.

#### 4. Interdisciplinárnosť a medzisektorová spolupráca
Projekt prepája strojové učenie, dátové inžinierstvo, IoT a senzoriku, elektrotechniku, energetiku
a podnikové (ERP) systémy. Ráta s externým tímom pre testovanie a validáciu; architektúra ostáva
otvorená (štandardné API), aby bola rozšíriteľná aj do ďalších sektorov.

#### 5. Kľúčové faktory úspechu implementácie
1. Kvalitné a konzistentné dáta (validácia, čistenie, redundancia senzorov).
2. Robustná dátová pipeline a spoľahlivé API konektory (ERP + IoT).
3. Presné a stabilné prediktívne modely s monitoringom driftu.
4. Bezpečnosť a súlad (GDPR, AI Act, privacy-by-design).
5. Modularita a otvorené rozhrania (prenositeľnosť, minimalizácia vendor lock-in).
6. Disciplinované projektové riadenie a priebežné integračné testy.

#### 6. Udržateľnosť riešenia
Udržateľnosť stojí na technickej báze (modulárna architektúra, otvorené API, verziovanie modelov a
dát, dokumentácia a runbooky), prevádzkovej báze (on-prem/cloud/hybrid, monitoring a proaktívna
údržba, školenia používateľov) a ekonomickej báze (licencovanie platformy, integračné projekty,
SLA na prevádzku a údržbu, správa dát ako služba). Roadmapa počíta s rozšírením na TRL 8–9,
viac výrobných liniek a hlbšie integrácie do ERP/MES/PLM, čo umožňuje škálovanie a komerčné
nasadenie mimo rámec projektu.
