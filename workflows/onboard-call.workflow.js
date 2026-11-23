// onboard-call.workflow.js — automatizované pridanie NOVEJ výzvy do frameworku.
// Agentický náprotivok runbooku skills/onboard-call/SKILL.md. Cesty sú relatívne ku
// koreňu repa (funguje aj vo forku).
//
// PREREKVIZITA: oficiálne dokumenty výzvy sú už ingestované ako 1:1 markdown v
// calls/<call>/source-md/oficialne/ (konverzia z PDF/DOCX je manuálny krok — pdftotext a pod.).
//
//   Workflow({ scriptPath: "workflows/onboard-call.workflow.js",
//              args: { call: "18I05-XX-V01" } })
//
// Fázy: Scaffold → Semantic-map → Tokenize (paralelne: Opis 2b, prílohy, required-structure)
//       → Call-requirements draft → Verify (test žiadosť + build + completeness) → oprava.

export const meta = {
  name: 'onboard-call',
  description: 'Z ingestovaných oficiálnych dokumentov novej výzvy vygeneruj tokenizované šablóny (Opis 2b + prílohy), required-structure, sémantickú mapu a draft call-requirements; over build-om',
  whenToUse: 'Po forknutí repa / pri pridávaní novej výzvy, keď sú oficiálne dokumenty už skonvertované do calls/<call>/source-md/oficialne/.',
  phases: [
    { title: 'Scaffold', detail: 'kostra + kontrola prerekvizít (ingestované dokumenty)' },
    { title: 'Semantic-map', detail: 'inventár faktov výzvy' },
    { title: 'Tokenize', detail: 'Opis 2b + prílohy + required-structure (paralelne)' },
    { title: 'Requirements', detail: 'draft call-requirements v2' },
    { title: 'Verify', detail: 'test žiadosť + build --target all + completeness' },
  ],
}

const call = (args && args.call)
if (!call) { log('CHÝBA args.call (číslo výzvy) — končím.'); return { error: 'missing args.call' } }
const KB = `calls/${call}/source-md/oficialne`
const TPL_OPIS = `templates/opis/${call}`
const TPL_ANN = `templates/annexes/${call}`

// ---- Fáza 0: scaffold + prerekvizity ----
phase('Scaffold')
const prep = await agent(
  `Priprav onboarding výzvy ${call}. Kroky:\n` +
  `1) Spusti: python3 tool/grant.py new-call ${call} (existujúce súbory preskočí).\n` +
  `2) Over, že ${KB}/ obsahuje ingestované oficiálne dokumenty (aspoň hlavný text výzvy a šablónu Opisu).\n` +
  `Vráť zoznam súborov v ${KB}/ a krátke zhodnotenie, či sa dá pokračovať (ak sú tam len README, NEdá sa).`,
  { label: 'scaffold+check', phase: 'Scaffold' })
if (String(prep).toLowerCase().includes('nedá sa') || String(prep).toLowerCase().includes('neda sa')) {
  log(`Prerekvizita nesplnená — ingestuj oficiálne dokumenty do ${KB}/ a spusti workflow znova.`)
  return { status: 'blocked_missing_documents', detail: prep }
}

// ---- Fáza 1: sémantická mapa ----
phase('Semantic-map')
await agent(
  `Napíš calls/${call}/SEMANTIC-MAP.md (prepíš starter). Prečítaj VŠETKY dokumenty v ${KB}/ a zostav:\n` +
  `1) tabuľku kľúčových faktov výzvy (kód, poskytovateľ, alokácia, min/max výdavky, termín podania,\n` +
  `   termín realizácie, oprávnený žiadateľ, počet žiadostí, kategórie výdavkov, intenzity, tvrdé podmienky),\n` +
  `2) inventár dokumentov (súbor → čo to je → rola pri žiadosti),\n` +
  `3) zoznam VYPLNITEĽNÝCH príloh (tie, ktoré žiadateľ vypĺňa) — tie sa budú tokenizovať,\n` +
  `4) kandidátov na call-requirements (sekcie/limity, prílohy, eligibility, budget, intenzity, indikátory).\n` +
  `KAŽDÝ fakt musí mať odkaz na zdrojový súbor. Vzor: calls/17I04-04-V05-RIS3/SEMANTIC-MAP.md.`,
  { label: 'semantic-map', phase: 'Semantic-map' })

// ---- Fáza 2: tokenizácia (paralelne) ----
phase('Tokenize')
const ANNEX_SCHEMA = { type: 'object', additionalProperties: false, required: ['annex_ids'],
  properties: { annex_ids: { type: 'array', items: { type: 'string' } } } }

const [/*opis*/, /*reqstruct*/, annexResult] = await parallel([
  () => agent(
    `Tokenizuj Opis projektu pre výzvu ${call}: prepíš ${TPL_OPIS}/opis-2b.md tak, aby VERNE kopíroval\n` +
    `štruktúru oficiálnej šablóny Opisu z ${KB}/ (hlavičkové tabuľky, sekcie, tabuľky aktivít/míľnikov/rizík/\n` +
    `indikátorov), s hodnotami nahradenými tokenmi. Používaj VÝHRADNE tokeny z docs/TOKENS.md.\n` +
    `Reálne údaje žiadateľa NIKDY — len identita tokeny. Vzor: templates/opis/17I04-04-V05/opis-2b.md.`,
    { label: 'tokenize:opis-2b', phase: 'Tokenize' }),
  () => agent(
    `Vytvor ${TPL_OPIS}/required-structure.yaml pre výzvu ${call}: zoznam povinných častí/markerov,\n` +
    `ktoré MUSÍ obsahovať vygenerovaný Opis (podľa oficiálnej šablóny v ${KB}/). Markery = krátke\n` +
    `unikátne reťazce z nadpisov/tabuliek (ako templates/opis/17I04-04-V05/required-structure.yaml).\n` +
    `Toto je automatická poistka úplnosti (check_document_completeness).`,
    { label: 'tokenize:required-structure', phase: 'Tokenize' }),
  () => agent(
    `Z ${KB}/ (a SEMANTIC-MAP) urč VYPLNITEĽNÉ prílohy výzvy ${call} (čestné vyhlásenie, MSP vyhlásenie,\n` +
    `výpis RT, porovnávacie tabuľky, formulár žiadosti, CV, doklady…). Pre KAŽDÚ vytvor tokenizovanú\n` +
    `šablónu ${TPL_ANN}/<id>.md (autentická štruktúra oficiálneho dokumentu + tokeny z docs/TOKENS.md)\n` +
    `a zaregistruj ich všetky v ${TPL_ANN}/annexes.yaml. Vzor: templates/annexes/17I04-04-V05/.\n` +
    `Vráť zoznam annex_ids, ktoré si vytvoril.`,
    { label: 'tokenize:annexes', phase: 'Tokenize', schema: ANNEX_SCHEMA }),
])
log(`Tokenizované prílohy: ${(annexResult && annexResult.annex_ids || []).join(', ') || '(žiadne?)'}`)

// ---- Fáza 3: draft call-requirements ----
phase('Requirements')
await agent(
  `Vytvor calls/${call}/call-requirements.reference.yaml — REFERENČNÝ draft call-requirements v2 pre\n` +
  `výzvu ${call} (nová žiadosť si ho skopíruje ako call-requirements.yaml). Zo SEMANTIC-MAP a ${KB}/\n` +
  `zakóduj VŠETKY tvrdé podmienky: call blok (deadline podania + realizácie, alokácia, režim,\n` +
  `komponent/investícia ak relevantné), sections+limity, annexes (generované cesty publication/…,\n` +
  `required podľa výzvy), budget (kategórie, paušál, min/max envelope), aid_intensity (base+uplift+cap),\n` +
  `indicators, consistency, scoring, eligibility (MSP/VaV computed ak platí, DNSH, dvojité financovanie,\n` +
  `bezúhonnosť, max žiadostí…). Vzor: applications/17I04-04-V05-RIS3-predictai/call-requirements.yaml.\n` +
  `POZOR: yamllite nepodporuje inline {} mapy — používaj block-style.`,
  { label: 'call-requirements', phase: 'Requirements' })

// ---- Fáza 4: verifikácia end-to-end ----
phase('Verify')
const VERIFY_SCHEMA = { type: 'object', additionalProperties: false, required: ['ok', 'problems'],
  properties: { ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } } } }
let verdict = { ok: false, problems: [] }
for (let i = 1; i <= 2; i++) {
  verdict = await agent(
    `Over onboarding výzvy ${call} end-to-end:\n` +
    `1) python3 tool/grant.py new-application ${call} testfirma (ak už existuje, pokračuj)\n` +
    `2) skopíruj calls/${call}/call-requirements.reference.yaml → applications/${call}-testfirma/call-requirements.yaml\n` +
    `3) python3 tool/grant.py --project-root applications/${call}-testfirma check --format json (schéma musí prejsť)\n` +
    `4) python3 tool/grant.py --project-root applications/${call}-testfirma build --target all\n` +
    `5) python3 tool/checks/check_document_completeness.py --project-root applications/${call}-testfirma\n` +
    `Kritériá: schéma validná, build bez '⚠ nevyplnené tokeny' (okrem section.* pri prázdnych sekciách),\n` +
    `completeness bez major. Vráť ok=true/false + zoznam konkrétnych problémov.`,
    { label: `verify:${i}`, phase: 'Verify', schema: VERIFY_SCHEMA })
  if (verdict.ok) break
  log(`Verify #${i}: ${verdict.problems.length} problémov — opravujem.`)
  await agent(
    `Oprav tieto problémy onboardingu výzvy ${call} (šablóny/required-structure/call-requirements.reference):\n` +
    `- ${verdict.problems.join('\n- ')}\n` +
    `Neopravuj nič iné. Tokeny len z docs/TOKENS.md; yamllite = block-style YAML.`,
    { label: `fix:${i}`, phase: 'Verify' })
}
log(verdict.ok
  ? `Výzva ${call} onboardnutá ✓ — testfirma prešla build+completeness. Skontroluj a commitni.`
  : `Výzva ${call} onboardnutá ČIASTOČNE — zvyšné problémy: ${verdict.problems.join('; ')}`)
return { call, ok: verdict.ok, problems: verdict.problems,
         annexes: (annexResult && annexResult.annex_ids) || [] }
