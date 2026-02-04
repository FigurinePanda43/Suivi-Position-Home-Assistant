# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Non publié]

## [0.1.0] - 2024-XX-XX

### Ajouté
- **CSV permanent** : Le fichier CSV sert maintenant de source de données permanente
  - Contourne la limitation de 10 jours d'historique de Home Assistant
  - Chargement automatique des données existantes au démarrage
- **Export CSV filtrable** :
  - Filtrage par plage de dates (start_date, end_date)
  - Filtrage par personnes sélectionnées
  - Nouvel endpoint `/api/suivi_presence/download/csv`
- **Export Excel avancé** :
  - Une feuille par personne avec données et statistiques
  - Statistiques automatiques par zone :
    - Temps total passé dans chaque zone
    - Moyenne journalière
    - Moyenne hebdomadaire
    - Moyenne mensuelle
    - Fréquence (nombre de visites)
    - Première et dernière visite
  - Tableaux formatés avec styles
  - Endpoint `/api/suivi_presence/download/excel`
- **Service `suivi_presence.export_excel`** : Export Excel via automatisation
- **Carte Lovelace améliorée** :
  - Panel de filtres dépliable
  - Sélection de dates
  - Cases à cocher pour sélectionner les personnes
  - Boutons CSV et Excel
  - Affichage de la plage de données disponible
- Nouvelle colonne `duration_seconds` dans le CSV pour calculs facilités

### Modifié
- Service `export_csv` accepte maintenant les paramètres de filtrage
- Endpoints HTTP avec support des query parameters

### Technique
- Nouveau module `export.py` pour la logique d'export
- Dépendance `openpyxl>=3.1.0` pour l'export Excel
- Fonctions utilitaires pour le calcul des statistiques

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
