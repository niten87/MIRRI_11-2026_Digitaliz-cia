### EXCELENTNOSŤ — východisková situácia a relevantnosť plánovaných cieľov

**Východisková situácia.** Priemyselné podniky generujú veľké objemy dát z ERP systémov (výrobné
príkazy, plánovanie, stavy zásob) a z IoT senzorov (teplota, vibrácie, prúd, spotreba, prevádzkové
stavy strojov). Tieto dáta sú však typicky uložené v izolovaných systémoch, nie sú prepojené a
nevyužívajú sa na prediktívne rozhodovanie. Dôsledkom je reaktívna údržba (zásah až po poruche),
neplánované prestoje s vysokými nákladmi, neefektívne plánovanie a vysoká energetická náročnosť
výroby. Chýba integrovaná vrstva, ktorá by v reálnom čase spájala ERP a senzorické dáta, aplikovala
prediktívne modely a dodávala operátorom a manažmentu zrozumiteľné odporúčania.

**Riešenie a komparatívna výhoda.** PredictAI reaguje integrovaným reťazcom „ERP + IoT →
dátová pipeline → prediktívne AI modely → real-time dashboard". Komparatívna výhoda pre SR spočíva
v jedinečnom premostení podnikových (ERP) a prevádzkových (IoT) dát do jednotnej prediktívnej
platformy s dôrazom na univerzálnosť a prenositeľnosť — riešenie nie je viazané na jedného výrobcu
strojov ani na jeden ERP systém, ale funguje cez štandardizované API konektory. Východiskom je
TRL 6 (overený koncept prediktívnej analytiky a dátovej integrácie z predchádzajúcich VaV aktivít),
z ktorého projekt postupuje k TRL 7 pilotným nasadením v prevádzke.

**Dopyt po výsledkoch.** Prediktívna údržba znižuje neplánované prestoje a náklady na servis;
optimalizácia procesov zvyšuje priepustnosť a kvalitu; energetická optimalizácia znižuje
prevádzkové náklady a uhlíkovú stopu. Projekt je koncipovaný ako experimentálny vývoj (nie základný
výskum): výsledkom bude funkčný demonštrátor s dokumentovaným TRL 7 pre pilotné prípady.

**Prepojenie na strategické dokumenty a RIS3.** Projekt je plne zosúladený s RIS3 SK 2021–2027,
Doména 3: Digitálna transformácia Slovenska:
- **3-1 (hlavná):** integrácia IoT senzorov a prepojených výrobných zariadení, edge zber dát.
- **3-2:** zhodnotenie ERP a senzorových dát, dátová pipeline, prediktívna analytika.
- **3-3:** inteligentná optimalizácia energetickej náročnosti výroby.
V národnom rámci zapadá do Komponentu 17 – Digitálne Slovensko, Investícia 4 (vývoj a aplikácia
špičkových digitálnych technológií). V európskom kontexte nadväzuje na agendu digitálnych dvojčiat,
dátových priestorov vo výrobe a Industry 4.0/5.0, s dôrazom na súlad s GDPR a AI Act.

**Prieskum konkurenčného prostredia a odlíšenie.** Prediktívna údržba a integrácia ERP+IoT sú známe
kategórie Industry 4.0; existujúce prístupy majú však konkrétne limity, voči ktorým sa PredictAI
vymedzuje:
- **Riešenia veľkých ERP/MES vendorov** — silná integrácia v rámci vlastného ekosystému, ale vendor
  lock-in a slabá prenositeľnosť na heterogénnu senzoriku. *PredictAI: jednotný dátový model a otvorené
  API naprieč rôznymi ERP/senzormi.*
- **Špecializované nástroje prediktívnej údržby** — často zamerané len na jeden typ zariadenia/signálu.
  *PredictAI: kombinácia porúch/prestojov + energetickej optimalizácie v jednej platforme.*
- **Interné ad-hoc skripty podnikov** — bez robustnej pipeline, monitoringu driftu a reálno-časovej vrstvy.
  *PredictAI: produkčná pipeline s monitoringom a dashboardom.*

Za rámec existujúcich riešení projekt ide v [DOPLNIŤ: konkrétny algoritmický/architektonický prínos,
napr. jednotný model naprieč heterogénnou senzorikou; energetická optimalizačná slučka]. [DOPLNIŤ:
odhad veľkosti/rastu trhu prediktívnej údržby ako podpora dopytu.]

**Kapacity žiadateľa.** [ZIADATEL] disponuje interdisciplinárnym tímom (AI/ML, dátové inžinierstvo,
IoT, elektro, ERP) a doménovými dátami z priemyselnej praxe. Za posledné dva roky realizoval VaV
projekty v doménach RIS3 (viď sekcia Referencie), na ktoré projekt nadväzuje — každý s obsahom,
výsledkom, RIS3 doménou a dokladom.

**SWOT analýza projektu**

*Silné stránky (Strengths):*
- Interdisciplinárny tím pokrývajúci celý reťazec (AI/ML, dátové inžinierstvo, IoT, elektro, ERP).
- Prístup k reálnym výrobným a senzorovým dátam a doménovej expertíze.
- Existujúce PoC prototypy (TRL 6) prediktívnej analytiky a dátovej integrácie.
- Univerzálna, modulárna architektúra s otvorenými API — minimalizuje vendor lock-in.
- Preukázaný VaV track-record v doménach RIS3.

*Slabé stránky (Weaknesses):*
- Závislosť od kvality a konzistencie senzorových dát.
- Integračná komplexita naprieč rôznymi ERP systémami a heterogénnou senzorikou.
- Krátky čas realizácie (9 mesiacov) — TRL 7 na vybraných pilotných scenároch.
- Vysoká záťaž na špecializované roly (AI/ML, dátové inžinierstvo).

*Príležitosti (Opportunities):*
- Silný trhový dopyt po prediktívnej údržbe a energetickej efektívnosti v priemysle.
- Prenositeľnosť riešenia do ďalších podnikov a sektorov (škálovanie, licencovanie).
- Nadväznosť na európske iniciatívy (digitálne dvojčatá, dátové priestory, Industry 4.0/5.0).
- Budovanie vlastných dátových aktív a doménového know-how ako konkurenčnej výhody.

*Hrozby (Threats):*
- Zmeny legislatívy (GDPR, AI Act) a súvisiace požiadavky na dáta a modely.
- Makroekonomické vplyvy (inflácia, ceny energií a vstupov).
- Rýchly vývoj konkurenčných platforiem veľkých vendorov.
- Technologické riziká pri pilotnom nasadení v reálnej prevádzke.
