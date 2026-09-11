# sectorbot

Pas un outil en soi — un dossier de configuration partagé qui donne à [`assurbot/`](../assurbot) (et à sa copie dans [`agentisys-suite/tools/assurbot/`](../agentisys-suite/tools/assurbot)) sa capacité multi-secteur.

- `sectors.config.json` — pour chacun des 7 secteurs : le nom affiché de l'outil, une icône, un prompt système, le fichier de connaissances associé, et le libellé des champs de saisie.
- `knowledge/*.txt` — une base de connaissances par secteur, au format `Q: ... / R: ...`.

Le nom neutre (« sectorbot ») est volontaire : ce dossier héberge les 7 identités sectorielles, pas seulement l'assurance.

**Contenu illustratif pour 6 secteurs sur 7** (télécom, fintech, e-commerce, automobile, edtech, assurance) — à remplacer par des données réelles pour une démonstration client. **OrthoBot (dispositifs médicaux) est basé sur une expérience réelle** (SOCA International / Groupe Sober), avec ses deux parcours effectifs : ordonnance venant d'un hôpital vs. venant d'un chirurgien.
