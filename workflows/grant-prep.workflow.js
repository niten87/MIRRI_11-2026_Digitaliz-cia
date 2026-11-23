// grant-prep.workflow.js — znovupoužiteľný orchestračný workflow pre prípravu jednej
// grantovej žiadosti (per-žiadosť fázy F5–F9 zo SPEC). Spusti cez Workflow tool:
//   Workflow({ scriptPath: ".../workflows/grant-prep.workflow.js",
//              args: { call: "17I04-04-V05-RIS3", applicant: "elara",
//                      projectRoot: "applications/17I04-04-V05-RIS3-elara" } })
//
// Princíp (SPEC §8): LLM navrhuje prózu/hodnoty; deterministická brána (tool/grant.py qc)
// je záväzný arbiter. Slučka write/compute → qc → (REVISE) → oprava → qc, kým PASS.
// Fázy, ktoré závisia od checkerov z BACKLOGu (check_budget/intensity/indicators/cross-doc),
// sa spustia až keď tie skripty v tool/checks/ existujú; dovtedy sa preskočia s log().

export const meta = {
  name: 'grant-prep',
  description: 'Priprav jednu grantovú žiadosť: napíš sekcie Opisu, dopočítaj rozpočet a intenzity, vyber indikátory, prežeň QC bránou a iteruj REVISE loop, kým nie je PASS',
  whenToUse: 'Keď máš hotovú knowledge base výzvy (calls/<call>/) a project.yaml žiadosti a chceš vygenerovať a zvalidovať kompletný Opis + rozpočet + prílohy.',
  phases: [
    { title: 'Priprava', detail: 'over knowledge base, project.yaml, call-requirements' },
    { title: 'Pisanie',  detail: 'sekcie Opisu (paralelne per sekcia)' },
    { title: 'Vypocty',  detail: 'rozpočet, intenzity, indikátory' },
    { title: 'QC-loop',  detail: 'agregovaná brána + REVISE iterácie' },
    { title: 'Finalize', detail: 'de-anonymizácia + build + submission package' },
  ],
}

const call        = (args && args.call)        || '17I04-04-V05-RIS3'
const applicant   = (args && args.applicant)   || 'demo'
const projectRoot = (args && args.projectRoot) || `applications/${call}-${applicant}`
const FW = `python3 tool/grant.py --project-root ${projectRoot}`

// Sekcie Opisu, ktoré vie LLM napísať z project.yaml + knowledge base (próza).
// Čísla (rozpočet/intenzity/indikátory) NEpíše LLM — tie dopočíta checker.
const OPIS_SECTIONS = [
  { id: 'abstrakt',        file: 'manuscript/10_abstrakt.md',                 hint: 'Zhrnutie projektu 150–250 slov: problém, riešenie, cieľ, dopad.' },
  { id: 'ciel',            file: 'manuscript/20_ciel.md',                     hint: 'Cieľ projektu a prioritná oblasť domény RIS3 (3-1..3-4).' },
  { id: 'excelentnost',    file: 'manuscript/40_excelentnost_vychodisko.md',  hint: 'Východisková situácia, relevantnosť cieľov, stav poznania, SWOT.' },
  { id: 'technicke',       file: 'manuscript/50_technicke_riesenie.md',       hint: 'Technické riešenie, TRL trajektória (začiatok→koniec 6–8), udržateľnosť.' },
  { id: 'dopad',           file: 'manuscript/60_dopad.md',                    hint: 'Očakávané výsledky, dopady, komunikácia a šírenie výsledkov.' },
  { id: 'aktivity',        file: 'manuscript/70_aktivity_harmonogram.md',     hint: 'Aktivity, časový harmonogram, priame výstupy, míľniky (z project.yaml).' },
  { id: 'rizika',          file: 'manuscript/80_rizika.md',                   hint: 'Implementačné riziká a ich manažment (z project.yaml risks).' },
  { id: 'manazment',       file: 'manuscript/90_projektovy_manazment.md',     hint: 'Projektový manažment, personálne + materiálne/finančné kapacity.' },
]

const QC_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['decision', 'blockers', 'majors', 'summary'],
  properties: {
    decision: { type: 'string', enum: ['BLOCK', 'REVISE', 'PASS_WITH_NOTES', 'PASS', 'UNKNOWN'] },
    blockers: { type: 'array', items: { type: 'string' } },
    majors:   { type: 'array', items: { type: 'string' } },
    summary:  { type: 'string' },
  },
}

// ---- F0: príprava ----
phase('Priprava')
const prep = await agent(
  `Over pripravenosť žiadosti v ${projectRoot}. Skontroluj že existuje project.yaml, call-requirements.yaml a knowledge base calls/${call}/. ` +
  `Prečítaj project.yaml a calls/${call}/SEMANTIC-MAP.md a zhrň: režim (A/B), miesto realizácie (BA kraj?), veľkosť MSP, prioritné domény/work-packages, deadline podania a realizačný termín. ` +
  `Ak niečo chýba, jasne to vymenuj. Vráť stručné zhrnutie.`,
  { label: 'prep:context', phase: 'Priprava' })
log(`Kontext: ${String(prep).slice(0, 280)}`)

// ---- F5: písanie sekcií Opisu (paralelne) ----
phase('Pisanie')
await parallel(OPIS_SECTIONS.map(s => () => agent(
  `Napíš sekciu Opisu projektu "${s.id}" do súboru ${projectRoot}/${s.file} (vytvor adresár ak treba). ` +
  `${s.hint} Čerpaj FAKTY iba z ${projectRoot}/project.yaml a z knowledge base calls/${call}/source-md/ (šablóna 2b, FAQ, schéma). ` +
  `Používaj anonymizačné placeholdre ([ZIADATEL], [OSOBA_1]…), NIE reálne mená. Dodrž slovný limit sekcie z call-requirements.yaml. ` +
  `Čísla rozpočtu/intenzít/indikátorov NEVYMÝŠĽAJ — tie dopočíta výpočtový modul. Napíš vecnú, hodnotiteľnú prózu v slovenčine.`,
  { label: `write:${s.id}`, phase: 'Pisanie' })))
log(`Napísaných ${OPIS_SECTIONS.length} sekcií Opisu.`)

// ---- F6/F7: výpočty (rozpočet, intenzity, indikátory) ----
phase('Vypocty')
await agent(
  `Priprav rozpočet žiadosti v ${projectRoot}. Z project.yaml (work_packages, personnel, financovanie) a z bloku budget/aid_intensity v call-requirements.yaml ` +
  `vytvor ${projectRoot}/budget/rozpocet.csv podľa štruktúry Prílohy 3 (2c): riadky výdavkov s kategóriou, počtom, jednotkovou cenou, celkové oprávnené výdavky, intenzitou, nárokované. ` +
  `Dodrž: celkove = pocet * cena; paušál podľa režimu (A:920=20%, B:940=40%); envelope 300k–2,2M €; effective intenzita = min(base+size_uplift+region_uplift, call_cap). ` +
  `Dopočítané sumy zapíš aj do project.yaml (financovanie.celkove_opravnene/ziadana_ppm/spolufinancovanie). Vysvetli výpočet.`,
  { label: 'compute:budget', phase: 'Vypocty' })
await agent(
  `Vyber merateľné ukazovatele do ${projectRoot}/indicators/indicators.csv z katalógu ` +
  `calls/${call}/source-md/oficialne/4-*priklady-meratelnych-ukazovatelov.md: 1–3 hlavné + 1–3 vedľajšie (max 6), aspoň 1 vedľajší diseminačný. ` +
  `Polia: nazov, definicia, merna_jednotka, vychodiskova_hodnota, planovana_hodnota, typ (hlavny/vedlajsi). Plánované hodnoty dosiahnuteľné do realizačného termínu.`,
  { label: 'compute:indicators', phase: 'Vypocty' })

// ---- F8: QC brána + REVISE loop ----
phase('QC-loop')
const MAX_ITERS = 4
let decision = 'UNKNOWN'
for (let i = 1; i <= MAX_ITERS; i++) {
  const qc = await agent(
    `Postav CELÝ balík a prežeň FINÁLNOU bránou (completeness + compliance), lebo finálne dokumenty ` +
    `MUSIA presne spĺňať prílohy/výzvu/zákon (P7). Spusti z koreňa repa a prečítaj výstup:\n` +
    `  ${FW} build --target all\n` +          // Opis 2b + rozpočet 2c + všetky prílohy z oficiálnych šablôn
    `  ${FW} qc --mode final_publication --fail-on major --format json\n` +
    `Final gate zahŕňa: call-requirements, budget, aid-intensity, indicators, cross-doc, MSP eligibility, ` +
    `timeline (časová oprávnenosť), legislation freshness, DOCUMENT COMPLETENESS (štruktúra vs oficiálna šablóna) ` +
    `a anonymizačný leak-scan. Zhrň VŠETKY nálezy: rozhodnutie a zoznam blocker-ov/major-ov s konkrétnym ` +
    `súborom/sekciou (najmä required_section_missing = chýbajúca povinná časť dokumentu).`,
    { label: `qc:iter${i}`, phase: 'QC-loop', schema: QC_SCHEMA })
  decision = qc.decision
  log(`QC #${i}: ${decision} · blockers=${qc.blockers.length} majors=${qc.majors.length}`)
  if (decision === 'PASS_WITH_NOTES' || decision === 'PASS') break
  if (i === MAX_ITERS) { log(`Dosiahnutý strop ${MAX_ITERS} iterácií, rozhodnutie stále ${decision}.`); break }

  // REVISE: oprav konkrétne nálezy a znova over
  await agent(
    `Oprav tieto QC nálezy v ${projectRoot} (neopravuj nič iné):\n` +
    `BLOCKERS:\n- ${qc.blockers.join('\n- ') || '(žiadne)'}\n` +
    `MAJORS:\n- ${qc.majors.join('\n- ') || '(žiadne)'}\n` +
    `Sekcie mimo limitu skráť; chýbajúce doplň z project.yaml/knowledge base; nesúlad čísel oprav v rozpočte/indikátoroch/project.yaml (single source of truth). ` +
    `Nezavádzaj reálne PII. Po oprave nič nespúšťaj — QC prebehne v ďalšej iterácii.`,
    { label: `revise:iter${i}`, phase: 'QC-loop' })
}

// ---- F8b: agentická QC nad OBSAHOM (relevancia/kvalita/compliance vs hodnotiace kritériá) ----
// Deterministická brána rieši čísla/štruktúru; toto rieši či je obsah vecný a bodovo silný.
phase('Content-review')
if (decision === 'PASS_WITH_NOTES' || decision === 'PASS') {
  const REVIEW_SCHEMA = { type: 'object', additionalProperties: false, required: ['rating', 'findings'],
    properties: { rating: { type: 'integer' }, findings: { type: 'array', items: { type: 'object',
      additionalProperties: false, required: ['issue', 'severity', 'fix'], properties: {
        issue: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'major', 'minor'] },
        fix: { type: 'string' } } } } } }
  const LENS = ['EXCELENTNOSŤ (východisko, ciele, metodika, TRL, inovatívnosť)',
                'DOPAD (merateľné výsledky, udržateľnosť, šírenie, ekosystém)',
                'IMPLEMENTÁCIA (harmonogram, rozpočet-primeranosť, riziká, kapacity)',
                'COMPLIANCE OBSAH (DNSH, neprekrývanie Komp.9, dvojité financovanie, RIS3, IP)']
  const reviews = await parallel(LENS.map(k => () => agent(
    `Si PRÍSNY hodnotiteľ. Prečítaj ${projectRoot}/publication/opis.md a prílohy v ${projectRoot}/publication/annexes/. ` +
    `Hodnoť IBA kritérium: ${k}. Kalibruj podľa reálneho vzoru calls/${call}/source-md/ziadatel/…opis-projektu-ziadatel-fin.md. ` +
    `Hľadaj GENERICKÝ/tenký/nerelevantný obsah a slabé prepojenie na hodnotiace subkritériá (nie čísla). ` +
    `Vráti rating 1–5 a konkrétne nálezy s návrhom, čo doplniť/prepísať.`,
    { label: `content:${k.split(' ')[0]}`, phase: 'Content-review', schema: REVIEW_SCHEMA })))
  const bad = reviews.filter(Boolean).flatMap(r => r.findings).filter(f => f.severity !== 'minor')
  log(`Content-review: ratingy ${reviews.filter(Boolean).map(r => r.rating).join('/')} · ${bad.length} kritických/major nálezov`)
  if (bad.length) {
    await agent(`Zlepši OBSAH ${projectRoot} podľa týchto nálezov hodnotiteľa (prepíš/dopln prózu v manuscript/*.md, ` +
      `nezavádzaj reálne PII, nemeň čísla):\n- ${bad.map(f => `[${f.severity}] ${f.issue} → ${f.fix}`).join('\n- ')}\n` +
      `Po úprave znova build a QC.`, { label: 'content:revise', phase: 'Content-review' })
  }
}

// ---- F9: finalizácia (len ak brána prešla) ----
phase('Finalize')
if (decision === 'PASS_WITH_NOTES' || decision === 'PASS') {
  const fin = await agent(
    `Žiadosť ${projectRoot} prešla QC (${decision}). Priprav finalizáciu:\n` +
    `1) Over že _anonymization-key.local.md existuje a leak-scan (check_anonymization_leaks.py ak existuje) je čistý.\n` +
    `2) Spusti \`${FW} build --target docx\` (Opis 2b) a ak build vie XLSX, aj rozpočet 2c a Prílohu 5.\n` +
    `3) Ak existuje build_submission_package.py, zabaľ iba include=true AND visibility=public a over package_manifest.csv.\n` +
    `De-anonymizovaný build sa NIKDY necommituje (je gitignored). Vráť zoznam vygenerovaných artefaktov a čo ešte treba doplniť ručne (portálové kroky: ITMS/e-doručenka, výpis z RT).`,
    { label: 'finalize:build', phase: 'Finalize' })
  log(`Finalizácia: ${String(fin).slice(0, 280)}`)
  return { decision, finalize: fin }
}

log(`Žiadosť NEprešla bránou (${decision}) — finalizácia preskočená. Doriešte blocker-y a spustite workflow znova.`)
return { decision }
