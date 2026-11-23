// content-review.workflow.js — agentická QC nad OBSAHOM žiadosti (nie čísla/štruktúra).
// Prísny hodnotiteľ: prejde generovaný Opis + prílohy a posúdi relevanciu, vecnosť a kvalitu
// obsahu voči hodnotiacim kritériám výzvy (excelentnosť/dopad/implementácia) + compliance obsah.
// Vracia nálezy zoradené podľa dopadu na body. Dopĺňa deterministickú bránu (tá rieši čísla/štruktúru).
//
//   Workflow({ scriptPath: ".../workflows/content-review.workflow.js",
//              args: { projectRoot: "applications/<call>-<applicant>", call: "17I04-04-V05-RIS3" } })

export const meta = {
  name: 'content-review',
  description: 'Agentická QC nad obsahom žiadosti: prísny hodnotiteľ posúdi relevanciu/kvalitu/compliance generovaných dokumentov voči hodnotiacim kritériám výzvy',
  whenToUse: 'Pred podaním, alebo ako fáza grant-prep — na odhalenie generického/tenkého/nesúladného obsahu, ktorý deterministické checkery nevidia.',
  phases: [{ title: 'Review', detail: 'reviewer agent per hodnotiace kritérium + compliance' }],
}

// Cesty sú RELATÍVNE ku koreňu repa (agenti bežia s cwd = repo root) — funguje aj vo forku.
const projectRoot = (args && args.projectRoot) || 'applications/17I04-04-V05-RIS3-predictai'
const call = (args && args.call) || '17I04-04-V05-RIS3'
const OPIS = `${projectRoot}/publication/opis.md`
const ANN = `${projectRoot}/publication/annexes`
const VYZVA = `calls/${call}/source-md/oficialne/` // hlavný text výzvy (01-*vyzva*.md) nájdi v tomto adresári
const GOLD = `calls/${call}/source-md/ziadatel/`   // vyplnený vzor Opisu (ak existuje) — kalibrácia úrovne

const SCHEMA = { type: 'object', additionalProperties: false, required: ['rating', 'findings'], properties: {
  rating: { type: 'integer', description: 'orientačná kvalita 1 (slabé) – 5 (excelentné) pre toto kritérium' },
  findings: { type: 'array', items: { type: 'object', additionalProperties: false,
    required: ['issue', 'severity', 'where', 'impact', 'fix'], properties: {
      issue: { type: 'string', description: 'čo je generické/tenké/nerelevantné/nesúladné' },
      severity: { type: 'string', enum: ['critical', 'major', 'minor'] },
      where: { type: 'string', description: 'sekcia/dokument' },
      impact: { type: 'string', description: 'dopad na body v tomto kritériu' },
      fix: { type: 'string', description: 'konkrétne čo doplniť/prepísať' } } } } } }

const LENSES = [
  { key: 'excelentnost',
    p: `Hodnotíš kritérium EXCELENTNOSŤ. Subkritériá: kvalita a jasnosť východiskovej situácie a problému; ` +
       `relevancia a ambicióznosť cieľov; vedecká/technická metodika a jej primeranosť; TRL trajektória (6→8) a jej ` +
       `dôveryhodnosť; interdisciplinárnosť; komparatívna výhoda a inovatívnosť; kvalita SWOT.` },
  { key: 'dopad',
    p: `Hodnotíš kritérium DOPAD. Subkritériá: konkrétnosť a merateľnosť očakávaných výsledkov (KPI); ekonomický a ` +
       `spoločenský dopad; udržateľnosť a plán komercializácie; prínos k digitálnemu ekosystému SR; synergie/škálovanie; ` +
       `kvalita komunikačného a diseminačného plánu (cieľové skupiny, kanály, harmonogram).` },
  { key: 'implementacia',
    p: `Hodnotíš kritérium IMPLEMENTÁCIA. Subkritériá: realistickosť harmonogramu a míľnikov v 9 mesiacoch; ` +
       `primeranosť a odôvodnenosť rozpočtu (vecný popis položiek, personálne kapacity vs aktivity); manažment rizík ` +
       `(úplnosť, mitigácie); štruktúra riadenia a QA; personálne/materiálne kapacity.` },
  { key: 'compliance-obsah',
    p: `Hodnotíš COMPLIANCE OBSAH (nie čísla). Over či je v texte OBSAHOVO a presvedčivo spracované: DNSH posúdenie ` +
       `(6 environmentálnych cieľov), neprekrývanie s Komponentom 9, zákaz dvojitého financovania, súlad s RIS3 doménami, ` +
       `ochrana IP vs povinnosť šírenia. Hľadaj vágne/formálne/protirečivé formulácie.` },
]

phase('Review')
const results = await parallel(LENSES.map(l => () =>
  agent(`Si PRÍSNY nezávislý hodnotiteľ grantovej žiadosti (výzva ${call}). ${l.p}\n\n` +
    `Prečítaj generovaný Opis: ${OPIS} a relevantné prílohy v ${ANN}. Hodnotiace pravidlá a kritériá čerpaj z hlavného textu výzvy (súbor *vyzva*.md v ${VYZVA}). ` +
    `Pre kalibráciu ÚROVNE si pozri reálny vyplnený vzor Opisu v ${GOLD} (súbor *opis-projektu*.md, ak existuje) — porovnaj hĺbku a konkrétnosť.\n\n` +
    `Buď adversariálny: hľadaj GENERICKÝ, tenký, nekonkrétny alebo nerelevantný obsah, chýbajúce prepojenie na hodnotiace ` +
    `subkritériá, a všetko, čo by znížilo body. NEhodnoť čísla/formátovanie (to rieši deterministická brána) — hodnoť OBSAH. ` +
    `Vráti orientačný rating 1–5 a konkrétne nálezy s návrhom, čo doplniť/prepísať.`,
    { label: `review:${l.key}`, phase: 'Review', schema: SCHEMA })
    .then(r => ({ kriterium: l.key, rating: (r && r.rating) || 0, findings: (r && r.findings) || [] }))))

return { review: results.filter(Boolean) }
