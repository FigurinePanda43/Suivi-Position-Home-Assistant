# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Non publié]

## [0.0.1] - 2024-XX-XX

### Ajouté
- Structure initiale de l'intégration Home Assistant
- Configuration via l'interface utilisateur (Config Flow)
- Suivi automatique des changements de zone pour les entités `person`
- Enregistrement des mouvements dans un fichier CSV
- Endpoint HTTP pour télécharger le fichier CSV (`/api/suivi_presence/download`)
- Endpoint HTTP pour les données du tableau de bord (`/api/suivi_presence/data`)
- Services Home Assistant :
  - `suivi_presence.export_csv` : Export manuel vers CSV
  - `suivi_presence.clear_history` : Effacement de l'historique
- Entités sensor :
  - `sensor.suivi_presence_suivi_presence` : Sensor principal
  - `sensor.suivi_presence_personnes_a_domicile` : Compteur personnes à domicile
  - `sensor.suivi_presence_personnes_absentes` : Compteur personnes absentes
  - `sensor.suivi_presence_total_des_changements` : Total des changements
- Carte Lovelace personnalisée (`suivi-presence-card`)
- Support des traductions (FR, EN)
- Compatible HACS
- Documentation complète (README, examples)

### Technique
- Utilisation de `async_track_state_change_event` pour le suivi en temps réel
- Écriture CSV asynchrone avec verrouillage
- Chargement des données CSV existantes au démarrage
- Gestion des états unavailable/unknown

### Connu
- Version de développement, non destinée à la production
- Le tableau de bord personnalisé nécessite un enregistrement manuel de la ressource

---

## Versionnement

- **X.0.0** : Changements majeurs, refonte complète
- **0.X.0** : Nouvelles fonctionnalités moyennes
- **0.0.X** : Corrections de bugs, petites améliorations

La version 1.0.0 sera la première version stable et fonctionnelle.
