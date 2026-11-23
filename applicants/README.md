# applicants/ — centrálny register profilov žiadateľov (firiem)

Jedno miesto, kde sú **reálne firemné údaje pre viacero firiem** uložené bezpečne
(gitignored) a odkiaľ sa pri novej žiadosti rýchlo vygeneruje anonymizačný reverzný kľúč.

## Súbory
| Súbor | V git? | Obsah |
|---|---|---|
| `company-profile.template.yaml` | ✅ committed | schéma profilu — **len placeholdre** |
| `README.md` | ✅ committed | tento návod |
| `companies.local.yaml` | ❌ **gitignored** (`*.local.yaml`) | **reálne údaje** všetkých firiem |

## Bezpečnostný princíp
- Reálne identifikátory (názov firmy, IČO, DIČ, IBAN, kontakty) žijú **výhradne** v
  `companies.local.yaml`, ktorý sa **nikdy necommituje**.
- Do commitnutých súborov žiadosti (`project.yaml`, `manuscript/`, prílohy) idú **placeholdre**
  (`[ZIADATEL]`, `[ICO]`, …). Pri finalizácii sa nahradia z reverzného kľúča.
- `tool/checks/check_anonymization_leaks.py` overí, že sa reálne dáta nedostali do commitu.

## Založenie / pridanie firmy
1. Skopíruj `company-profile.template.yaml` → `companies.local.yaml` (ak ešte nie je).
2. Vyplň reálne hodnoty pre každú firmu pod jej `company-id`.

## Použitie pri novej žiadosti
```bash
# zoznam firiem v registri
python3 tool/grant.py applicant list

# vygeneruj reverzný kľúč pre konkrétnu žiadosť z profilu firmy
python3 tool/grant.py --project-root applications/<call>-<firma> applicant key --company <company-id>
#   → zapíše applications/<call>-<firma>/_anonymization-key.local.md  (gitignored)
```
Do `project.yaml` žiadosti vyplň `applicant` blok placeholdrami a `applicant.msp` číslami
(zamestnanci/obrat/súvaha) — tie sú v profile firmy; `check_eligibility` z nich vypočíta veľkosť.

> Pozn.: reálne MSP financie (obrat/súvaha) sú citlivé. Ak nechceš mať ich reálne hodnoty v
> commitnutom `project.yaml`, drž ich len v profile a v `project.yaml` ponechaj `size_category`
> (deklarované); výpočtovú kontrolu spusti lokálne.
