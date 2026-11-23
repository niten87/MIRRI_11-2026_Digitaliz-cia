# FORKING — klonovanie frameworku pre novú výzvu / nový repozitár

Tento repo je **základ (template)**. Pre každú novú výzvu (alebo klienta) sa forkne/naklonuje
a rozšíri o dáta výzvy. Nástroj (`tool/`) sa NEupravuje výzvovo — všetko výzvové je dátové.

## 1) Fork / klon
```bash
git clone <tento-repo> grantapp-<nazov>   # alebo GitHub fork / "Use this template"
cd grantapp-<nazov>
for t in tool/tests/test_*.py; do python3 "$t"; done   # sanity: všetky testy musia prejsť
```

## 2) Čo s referenčným obsahom (17I04-04-V05-RIS3)
Fork zdedí referenčnú výzvu a 2 žiadosti (ELARA, PredictAI). Odporúčanie:
- **Ponechať** `calls/17I04-04-V05-RIS3/` + `templates/{opis,annexes}/17I04-04-V05/` — slúžia ako
  **vzor pre agentov** (onboard-call workflow sa na ne odvoláva ako na príklady).
- `applications/17I04-04-V05-RIS3-*` môžeš odstrániť, ak zavadzajú (sú to demá s placeholdrami);
  testy na ne NEviažu build okrem `test_annexes`/`test_ooxml` — ak ich mažeš, uprav aj tie testy.
- `examples/` a `applicants/company-profile.template.yaml` ponechaj.

## 3) Lokálne (gitignored) súbory — po forku treba znovu vytvoriť
Reálne dáta sa NEklonujú (sú gitignored). V novom prostredí vytvor:
- `applicants/companies.local.yaml` — register firiem (z `company-profile.template.yaml`)
- `applications/<app>/_anonymization-key.local.md` — generuje `grant.py applicant key --company <id>`

## 4) Onboarding novej výzvy
1. **Ingest (manuálne):** skonvertuj oficiálne dokumenty výzvy do 1:1 markdownu
   (`pdftotext -layout`, DOCX→md) do `calls/<č>/source-md/oficialne/`. Dokumenty žiadateľa
   anonymizuj placeholdrami do `ziadatel/`.
2. **Automatizovane:** spusti `workflows/onboard-call.workflow.js` s `args: { call: "<č>" }`
   — vygeneruje SEMANTIC-MAP, tokenizované šablóny (Opis 2b + prílohy), `required-structure.yaml`,
   draft `call-requirements.reference.yaml` a overí build-om.
   (Manuálny postup: `skills/onboard-call/SKILL.md`.)
3. **Skontroluj a commitni** — najmä required-structure (poistka úplnosti) a tvrdé podmienky
   v call-requirements (porovnaj s textom výzvy!).

## 5) Žiadosti
```bash
python3 tool/grant.py new-application <č> <firma>
cp calls/<č>/call-requirements.reference.yaml applications/<č>-<firma>/call-requirements.yaml
# ďalej: skills/grant-prep/SKILL.md (build --target all, qc, content-review)
```

## 6) Zásady, ktoré fork NESMIE porušiť
- Reálne PII/firemné údaje nikdy do commitov (leak-scan + gitignore `*.local.*`, `**/publication/`).
- Dokumenty len z tokenizovaných oficiálnych šablón (P7); completeness gate pri každej výzve.
- Výzvové fakty len v dátach — `tool/` ostáva generický (uľahčuje merge vylepšení z upstream repa).

## 7) Ako dostať vylepšenia frameworku do forkov
`tool/`, `skills/`, `workflows/`, `templates/_starters/`, `docs/` sú zdieľané jadro — vo forku ich
neupravuj výzvovo, aby sa dal robiť `git merge upstream/main` bez konfliktov s tvojimi dátami výzvy.
