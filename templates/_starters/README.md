# templates/_starters/ — východiskové šablóny pre NOVÚ výzvu

`grant.py new-call <číslo>` z nich vygeneruje kostru novej výzvy. Potom ich agent prispôsobí
podľa oficiálnych dokumentov konkrétnej výzvy. Slovník tokenov: `docs/TOKENS.md`.

| Starter | Kam sa skopíruje | Čo urobiť |
|---|---|---|
| `opis-2b.starter.md` | `templates/opis/<call>/opis-2b.md` | prispôsobiť nadpisy/tabuľky oficiálnej 2b výzvy |
| `required-structure.starter.yaml` | `templates/opis/<call>/required-structure.yaml` | zoznam povinných častí (ground truth) |
| `annexes.starter.yaml` | `templates/annexes/<call>/annexes.yaml` | zaregistrovať prílohy výzvy |
| `../call-requirements-v2-template.yaml` | `applications/<call>-<applicant>/call-requirements.yaml` | zakódovať podmienky/limity/lehoty |
| `../project-template.yaml` | `applications/<call>-<applicant>/project.yaml` | fakty projektu (single source of truth) |
| `../legislation-template.yaml` | `applications/<call>-<applicant>/legislation.yaml` | pinnutá legislatíva |

Postup pre celú výzvu: `skills/onboard-call/SKILL.md`.
