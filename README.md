# Suivi de Présence pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/FigurinePanda43/Suivi-Position-Home-Assistant/blob/main/CHANGELOG.md)
[![CI](https://github.com/FigurinePanda43/Suivi-Position-Home-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/FigurinePanda43/Suivi-Position-Home-Assistant/actions/workflows/ci.yml)

Enregistre **chaque changement de zone** des personnes de votre Home Assistant (maison → travail,
travail → absent, …) dans un **fichier CSV permanent**, et fournit une **carte Lovelace** pour
voir qui est où, depuis quand, consulter l'historique par période et **exporter en CSV ou Excel**.

> Home Assistant ne conserve l'historique que quelques jours. Cette intégration garde tout, sans
> limite de durée, dans un fichier que vous contrôlez.

## Ce que fait (et ne fait pas) l'intégration

| Oui | Non |
|---|---|
| Qui est dans quelle **zone**, depuis quand | Vitesse, distance parcourue, itinéraires |
| Historique illimité des **changements de zone** | Stockage de coordonnées GPS dans le temps |
| Temps passé **par zone** sur une période | Géocodage d'adresses |
| Exports **CSV** et **Excel** d'une période, sans dépendance à installer | |
| Fraîcheur et précision de la **position GPS** courante (lue sur `person.*`) | |

Les positions courantes et le trajet des dernières heures sont affichés par la carte `map`
**native** de Home Assistant à partir des entités `person.*` (voir le tableau de bord d'exemple).

## Installation

### Via HACS (recommandé)

1. HACS → *Intégrations* → ⋮ → *Dépôts personnalisés*.
2. Ajoutez `https://github.com/FigurinePanda43/Suivi-Position-Home-Assistant`, catégorie *Intégration*.
3. Recherchez **Suivi de Présence**, téléchargez, **redémarrez Home Assistant**.

### Manuelle

Copiez `custom_components/suivi_presence` dans `config/custom_components/`, puis redémarrez.

### Prérequis

- Home Assistant **2024.12** ou plus récent.
- Des entités `person.*` associées à un traqueur d'appareil (application compagnon, routeur, …).
- Aucune bibliothèque supplémentaire : l'export Excel est généré par l'intégration elle-même.

## Configuration

*Paramètres → Appareils et services → Ajouter une intégration → **Suivi de Présence***.

| Option | Description |
|---|---|
| **Personnes à suivre** | Vide = toutes les personnes, y compris celles créées plus tard. |
| **Fichier CSV** | Par défaut `suivi_presence_data.csv` dans le dossier de configuration. Le dossier doit exister et être accessible en écriture. |

Les options sont modifiables ensuite via **Configurer** ; l'intégration se recharge toute seule.
Une seule instance est possible.

## Tableau de bord

La carte `custom:suivi-presence-card` est **chargée automatiquement** par l'intégration : il n'y a
**aucune ressource Lovelace à déclarer**. Si vous veniez d'une version 0.1.x, supprimez l'ancienne
ressource `/local/suivi_presence/suivi-presence-card.js` (*Paramètres → Tableaux de bord → ⋮ →
Ressources*).

### Tableau de bord complet (recommandé)

Créez un nouveau tableau de bord vide, ouvrez *⋮ → Éditeur brut* et collez
[`examples/lovelace-dashboard.yaml`](examples/lovelace-dashboard.yaml). Remplacez `person.jean` /
`person.marie` par vos entités dans les cartes natives `map`, `history-graph` et `logbook`.

Trois vues :

1. **Présence** — la carte (qui est où, depuis quand, alertes, période, temps par zone,
   changements, exports) + carte géographique native + frise des zones sur 24 h.
2. **Historique** — la carte réglée sur 7 jours, frise sur 7 jours, journal natif.
3. **Technique** — les capteurs, le chemin du CSV, changements par jour.

Aucune carte HACS supplémentaire n'est nécessaire.

### La carte seule

```yaml
type: custom:suivi-presence-card
title: Suivi de Présence        # false pour masquer l'en-tête
default_period: today          # today | 24h | 7d | 30d | all
persons:                       # optionnel : limiter l'affichage
  - person.jean
show_summary: true             # temps par zone sur la période
show_history: true             # changements de zone groupés par jour
show_export: true              # boutons CSV / Excel
show_details: true             # bloc « Détails techniques » replié
history_limit: 50              # lignes affichées avant « Afficher plus »
stale_after_minutes: 120       # position GPS considérée ancienne au-delà
```

Ce que montre la carte :

- **En haut** : état du suivi, bloc « À vérifier » (traqueur indisponible, position GPS ancienne,
  fichier illisible), puis **une ligne par personne** : zone, « depuis 2 h 15 », « Position mise à
  jour il y a 5 min · ±25 m ». Un clic ouvre la fiche Home Assistant de la personne.
- **Période** : Aujourd'hui · 24 h · 7 jours · 30 jours · Tout · Personnalisé, et un filtre par
  personne. La période pilote le résumé, l'historique **et** les exports ; le choix est mémorisé
  par le navigateur.
- **Temps par zone** : barre segmentée et légende par personne (séjour en cours inclus).
- **Changements de zone** : « 08:32 · Jean · Maison → Travail · après 12 h 30 à Maison ».
- **Exporter la période** : **CSV** et **Excel**. Les fichiers sont téléchargés par le navigateur
  ou l'application compagnon via un lien signé Home Assistant — rien à récupérer dans le dossier
  de configuration.

## Exports

### CSV

Mêmes colonnes que le fichier de stockage, encodage UTF-8 avec BOM (ouverture directe dans
Excel), séparateur `,` par défaut ou `;` (Excel en français).

| Colonne | Contenu |
|---|---|
| `timestamp` | Date et heure du changement, ISO 8601 en heure locale avec décalage (`2025-09-01T10:30:00+02:00`) |
| `person` | Nom de la personne |
| `previous_zone` | Zone quittée (`home`, `not_home` ou nom de zone) |
| `new_zone` | Zone rejointe |
| `duration_in_previous` | Temps passé dans la zone quittée, `H:MM:SS` (les heures peuvent dépasser 24) |
| `duration_seconds` | Même durée en secondes (entier) |
| `person_entity_id` | Identifiant `person.*` (ajouté en 1.0.0) |

Les lignes écrites par les versions 0.1.x (UTC, durées `1 day, 2:03:04.567890`) restent lues et
exportées telles quelles.

### Excel

Un vrai classeur `.xlsx`, généré par l'intégration **sans aucune dépendance** à installer :

- feuille **Résumé** : pour chaque personne et chaque zone, temps total, moyenne par jour, nombre
  de passages, **moyenne par visite** (durée moyenne d'un séjour), première et dernière arrivée,
  séjour en cours ;
- **une feuille par personne** : mêmes statistiques, puis la liste des changements de zone.

Les dates sont de vraies dates Excel, les durées sont au format `[h]:mm:ss` (triables, sommables),
les heures sont locales. Filtres automatiques et volets figés activés. Le fichier s'ouvre dans
Microsoft Excel, LibreOffice Calc, Numbers et Google Sheets.

## Services

Toutes les dates sont en **heure locale** ; `start_date` = début du jour, `end_date` = fin du jour.
`persons` accepte des noms **ou** des identifiants `person.*`.

### `suivi_presence.export_csv`

Écrit un CSV dans le dossier de configuration et renvoie `path` et `records`.

```yaml
action: suivi_presence.export_csv
data:
  filename: exports/presence_janvier.csv   # optionnel, horodaté si absent
  start_date: "2025-01-01"
  end_date: "2025-01-31"
  persons: ["Jean", "person.marie"]
  delimiter: ";"                           # "," par défaut
response_variable: export
```

### `suivi_presence.export_excel`

Idem pour un classeur `.xlsx`.

### `suivi_presence.clear_history`

Vide le fichier CSV **après l'avoir copié** en `suivi_presence_data.csv.bak-avant-effacement-<date>`.
Réservé aux administrateurs (un appel depuis une automatisation, sans utilisateur, est accepté).
Renvoie `backup`.

## Entités

Un appareil **Suivi de Présence** avec quatre capteurs (identifiants identiques aux versions 0.1.x) :

| Entité | État | Attributs utiles |
|---|---|---|
| `sensor.suivi_de_presence_suivi_presence` | Nombre de personnes suivies | `persons_home`, `persons_away`, `persons_in_zones`, `last_change`, `csv_path`, `tracking` |
| `sensor.suivi_de_presence_personnes_a_domicile` | Personnes à la maison | `persons` |
| `sensor.suivi_de_presence_personnes_absentes` | Personnes hors de toute zone | `persons` |
| `sensor.suivi_de_presence_total_des_changements` | Nombre de changements enregistrés | `last_change`, `last_person`, `last_from_zone`, `last_to_zone` |

Les capteurs sont mis à jour **immédiatement** à chaque changement (pas de polling).

## API (pour vos propres outils)

Toutes les routes exigent une authentification Home Assistant (jeton ou lien signé).

| Route | Description |
|---|---|
| `GET /api/suivi_presence/download[?delimiter=;]` | CSV complet |
| `GET /api/suivi_presence/download/csv?start_date=…&end_date=…&persons=a,b&delimiter=;` | CSV filtré |
| `GET /api/suivi_presence/download/excel?start_date=…&end_date=…&persons=…` | Excel |
| `GET /api/suivi_presence/data?start_date=…&end_date=…&persons=…&limit=200` | JSON : état des personnes, historique, résumé par zone |
| WebSocket `suivi_presence/overview` | État courant des personnes |
| WebSocket `suivi_presence/history` (`start`, `end`, `persons`, `limit`) | Changements et résumé par zone d'une période (`seconds`, `visits`, `average_visit_seconds`, `first`, `last`, `ongoing`) |

## Comportement à connaître

- **Redémarrage** : au démarrage, la zone courante de chaque personne est comparée au dernier
  enregistrement du CSV. Si elle a changé pendant l'arrêt, un changement est enregistré (daté au
  redémarrage, mentionné dans les logs). La durée « depuis » n'est pas réinitialisée.
- **Indisponible / inconnu** : ignorés ; la dernière zone connue est conservée et la personne est
  signalée dans « À vérifier ». Le retour dans une autre zone enregistre un seul changement.
- **Statistiques** : temps par zone calculé par intervalles découpés à la période choisie, séjour
  en cours inclus ; « passages » = nombre de séjours dans la zone recoupant la période (un séjour déjà en
  cours au début de la période compte pour un) ; moyenne = total / nombre de jours de la période.
- **Format du fichier** : les colonnes ne sont jamais renommées ni supprimées. En 1.0.0 une colonne
  est ajoutée ; le fichier est migré automatiquement avec une sauvegarde
  `.bak-migration-<date>`.

## Dépannage

**La carte affiche « Custom element doesn't exist »** — Redémarrez Home Assistant après
l'installation et rechargez la page (Ctrl+F5). Vérifiez qu'il ne reste pas une ancienne ressource
manuelle pointant vers `/local/suivi_presence/…` (elle est inutile et peut être supprimée).

**La carte affiche « Aucun changement de zone » / « 0 changement »** — La carte est filtrée sur la
période sélectionnée (« Aujourd'hui » par défaut, c'est-à-dire depuis minuit). Rien n'est perdu : le
nombre total d'enregistrements est visible dans « Détails techniques », et l'état vide rappelle le
dernier changement enregistré. Cliquez sur « 7 jours » ou « Tout » ; la période choisie est
mémorisée par le navigateur.

**Aucune personne suivie** — Créez des entités `person` et associez-leur un traqueur. Vérifiez
l'option *Personnes à suivre*.

**Le téléchargement ne démarre pas** — Le lien signé expire après deux minutes ; recliquez. Dans
l'application compagnon, autorisez les téléchargements si le système le demande. Les erreurs
détaillées apparaissent dans *Paramètres → Système → Journaux*.

**Les heures de l'Excel sont décalées** — Vérifiez le fuseau horaire de Home Assistant
(*Paramètres → Système → Général*) : les exports l'utilisent.

## Développement

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest                      # 74 tests sur un Home Assistant réel
ruff check custom_components tests
npm install jsdom && node tests/card/test_card.mjs   # test de la carte
```

La CI exécute pytest, ruff, [hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/)
et la validation HACS à chaque push.

## Documentation

- [`CHANGELOG.md`](CHANGELOG.md) — historique et notes de migration.
- [`docs/AUDIT-V1.0.0.md`](docs/AUDIT-V1.0.0.md) — audit technique de la version bêta.
- [`docs/REFONTE-TABLEAU-DE-BORD.md`](docs/REFONTE-TABLEAU-DE-BORD.md) — choix de conception du tableau de bord.
- [`examples/legacy/`](examples/legacy/) — anciens tableau de bord et carte (0.1.x).

## Licence

MIT — voir [LICENSE](LICENSE).
