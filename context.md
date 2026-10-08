# Context - Intégration Suivi de Présence pour Home Assistant

## Version actuelle : 1.0.2

---

## 1. Description du Projet

Cette intégration Home Assistant permet de suivre les changements de zone de toutes les personnes configurées dans Home Assistant. Elle enregistre chaque mouvement dans un fichier CSV et offre un tableau de bord pour visualiser et télécharger ces données.

### Fonctionnalités principales
- Suivi automatique des changements de zone pour chaque personne
- **CSV permanent** : Stockage illimité (Home Assistant ne garde que 10 jours)
- Tableau de bord de visualisation avec filtres
- **Export CSV** avec filtrage par dates et personnes
- **Export Excel** avancé avec :
  - Une feuille par personne
  - Données brutes en tableau formaté
  - Statistiques par zone (temps total, moyennes jour/semaine/mois, fréquence)
- Compatible avec toutes les installations Home Assistant et HACS

---

## 2. Stratégie de Versionnement

### Format : X.Y.Z

| Niveau | Chiffre | Type de modification | Exemple |
|--------|---------|---------------------|---------|
| Majeur | X | Refonte complète, changements cassants | 1.0.0 → 2.0.0 |
| Mineur | Y | Nouvelles fonctionnalités moyennes | 0.1.0 → 0.2.0 |
| Patch  | Z | Corrections, petites améliorations | 0.0.1 → 0.0.2 |

### Règles de versionnement
- **Version 0.x.x** : Phase de développement (non fonctionnelle en production)
- **Version 1.0.0+** : Première version fonctionnelle stable
- Les versions fonctionnelles commencent à partir de **1.0.1**

---

## 3. Stratégie de Développement

### Principes
1. **Développement incrémental** : Chaque fonctionnalité est développée et testée indépendamment
2. **Backward compatibility** : Les nouvelles fonctionnalités ne doivent pas casser les existantes
3. **Configuration isolée** : Chaque composant a sa propre configuration
4. **Tests avant commit** : Toujours valider le fonctionnement avant de commit

### Workflow de développement
1. Créer une branche pour la fonctionnalité
2. Implémenter la fonctionnalité
3. Tester localement
4. Mettre à jour la documentation
5. Incrémenter la version
6. Commit avec message descriptif
7. Merge vers la branche principale

---

## 4. Structure du Projet

```
suivi-presence/
├── custom_components/
│   └── suivi_presence/
│       ├── __init__.py          # Setup domaine (vues, websocket, ressource frontend, services) + entrée
│       ├── tracker.py           # PresenceTracker : écoute des person.*, CSV, réconciliation au démarrage
│       ├── stats.py             # Statistiques par intervalles (temps par zone sur une période)
│       ├── export.py            # Export CSV / Excel
│       ├── xlsx_writer.py       # Écriture .xlsx minimale (bibliothèque standard, sans openpyxl)
│       ├── http.py              # Vues HTTP (téléchargements, JSON)
│       ├── websocket.py         # Commandes websocket utilisées par la carte
│       ├── util.py              # Dates, fuseaux, durées
│       ├── sensor.py            # 4 capteurs (push)
│       ├── config_flow.py       # Config flow + options flow
│       ├── const.py             # Constantes
│       ├── manifest.json        # Métadonnées (version unique de référence)
│       ├── services.yaml        # Définition des services
│       ├── strings.json         # Traductions (source)
│       ├── translations/        # fr.json, en.json
│       └── www/
│           └── suivi-presence-card.js  # Carte Lovelace (JS natif, auto-chargée)
├── tests/                       # pytest sur un Home Assistant réel + tests/card (jsdom)
├── docs/                        # Audit V1.0.0, refonte du tableau de bord
├── examples/
│   ├── lovelace-dashboard.yaml  # Tableau de bord 1.0.0 (3 vues)
│   └── legacy/                  # Anciens fichiers 0.1.x (retour arrière)
├── .github/workflows/ci.yml     # pytest, ruff, hassfest, HACS, syntaxe JS
├── hacs.json, pyproject.toml, requirements_test.txt
├── README.md, CHANGELOG.md, LICENSE, context.md
```

---

## 5. Manière de Travailler

### Avant de coder
- [ ] Lire le context.md
- [ ] Identifier les fichiers impactés
- [ ] Planifier les modifications
- [ ] Vérifier les dépendances

### Pendant le développement
- [ ] Un changement = un commit logique
- [ ] Commenter le code complexe
- [ ] Respecter les conventions Home Assistant
- [ ] Ne pas modifier les fichiers non concernés

### Après le développement
- [ ] Mettre à jour context.md si nécessaire
- [ ] Mettre à jour la version dans manifest.json
- [ ] Mettre à jour le CHANGELOG
- [ ] Tester l'intégration

---

## 6. Problèmes Rencontrés et Solutions

### Journal des problèmes

| Date | Version | Problème | Solution | Statut |
|------|---------|----------|----------|--------|
| 2026-09-13 | 0.1.1 | `openpyxl` obligatoire bloquait le démarrage | Dépendance optionnelle | Corrigé |
| 2026-10-08 | 1.0.0 | Export Excel grisé sur l'instance réelle (`openpyxl` absent de l'hôte) | `.xlsx` écrit en bibliothèque standard | Corrigé |
| 2026-10-08 | 1.0.0 | Tous les téléchargements CSV en 500 (`charset` dans `content_type`) | `charset=` séparé | Corrigé |
| 2026-10-08 | 1.0.0 | Exports filtrés en 500 (dates naïves vs UTC) | `util.parse_user_datetime`, tout en aware | Corrigé |
| 2026-10-08 | 1.0.0 | Options flow : `TypeError` | `OptionsFlow` sans argument, `self.config_entry` injecté | Corrigé |
| 2026-10-08 | 1.0.0 | Vues HTTP figées après rechargement | Tracker résolu à la requête | Corrigé |
| 2026-10-08 | 1.0.0 | Téléchargement `blob:` KO sur appli mobile | Chemins signés `auth/sign_path` | Corrigé |
| 2026-10-08 | 1.0.0 | Durées fausses après redémarrage, transitions manquées | Réconciliation CSV ↔ états au démarrage | Corrigé |

---

## 7. Stratégie de Maintenance

### Maintenance préventive
- Revue de code régulière
- Mise à jour des dépendances
- Tests de régression

### Maintenance corrective
1. Identifier le problème
2. Documenter dans ce fichier
3. Créer une branche fix/
4. Corriger et tester
5. Incrémenter le patch version

---

## 8. Règles pour Développer sans Casser l'Existant

### Golden Rules
1. **Ne jamais modifier directement** les fichiers en production
2. **Toujours brancher** depuis la version stable
3. **Tests unitaires** pour les fonctions critiques
4. **Feature flags** pour les fonctionnalités expérimentales
5. **Rollback plan** : toujours pouvoir revenir en arrière

### Checklist avant modification
- [ ] J'ai lu et compris le code existant
- [ ] Ma modification est isolée
- [ ] J'ai un plan de test
- [ ] Je peux revenir en arrière facilement

---

## 8bis. PROTECTION DES DONNÉES - RÈGLES CRITIQUES

> **IMPORTANT** : Le fichier CSV est la source de données permanente de l'utilisateur.
> Toute perte de données est INACCEPTABLE.

### Règles absolues

1. **NE JAMAIS supprimer** le fichier CSV existant lors d'une mise à jour
2. **NE JAMAIS modifier** la structure des colonnes existantes (ajout OK, suppression/renommage INTERDIT)
3. **TOUJOURS** charger les données existantes au démarrage
4. **TOUJOURS** préserver la rétrocompatibilité du format CSV

### Migration de données

Si une nouvelle version nécessite des changements de structure :

1. **Ajouter** de nouvelles colonnes (ne pas supprimer les anciennes)
2. **Créer** une fonction de migration qui :
   - Détecte l'ancienne structure
   - Ajoute les nouvelles colonnes avec valeurs par défaut
   - Préserve toutes les données existantes
3. **Documenter** la migration dans le CHANGELOG

### Structure CSV actuelle (v1.0.0)

```
timestamp,person,previous_zone,new_zone,duration_in_previous,duration_seconds,person_entity_id
```

Valeurs écrites en 1.0.0 : `timestamp` en heure locale avec décalage et sans microsecondes,
`duration_in_previous` en `H:MM:SS`, `duration_seconds` entier. Les anciennes valeurs (UTC,
`str(timedelta)`, flottants) restent lues (`util.parse_timestamp`, `util.parse_duration_seconds`).

### Historique des structures

| Version | Colonnes | Notes |
|---------|----------|-------|
| 0.0.1 | timestamp, person, previous_zone, new_zone, duration_in_previous | Structure initiale |
| 0.1.0 | + duration_seconds | Ajout colonne pour calculs |
| 1.0.0 | + person_entity_id | Identifiant stable de la personne ; migration automatique de l'en-tête avec sauvegarde `.bak-migration-<date>` |

### Code de chargement sécurisé

Le code doit :
- Accepter les CSV avec ou sans les nouvelles colonnes
- Remplir les colonnes manquantes avec des valeurs par défaut
- Ne jamais écraser un fichier existant sans backup

### Tests obligatoires avant release

- [ ] Charger un CSV de la version précédente
- [ ] Vérifier que toutes les données sont préservées
- [ ] Vérifier que les nouvelles fonctionnalités fonctionnent
- [ ] Vérifier que l'export contient toutes les données

---

## 9. Roadmap

### Version 0.0.1 ✅
- [x] Structure de base
- [x] Manifest et configuration
- [x] Config Flow (configuration via UI)
- [x] Suivi des changements de zone
- [x] Enregistrement CSV automatique
- [x] Endpoint HTTP pour téléchargement CSV
- [x] Services (export_csv, clear_history)
- [x] Entités sensor (4 sensors)
- [x] Carte Lovelace personnalisée
- [x] Support HACS
- [x] Traductions FR/EN

### Version 0.1.0 (actuelle) ✅
- [x] CSV permanent comme source de données (contourne la limite 10 jours HA)
- [x] Export CSV avec filtrage par plage de dates
- [x] Export CSV avec filtrage par personnes
- [x] Export Excel avancé avec :
  - [x] Une feuille par personne sélectionnée
  - [x] Données brutes formatées en tableau
  - [x] Statistiques par zone :
    - [x] Temps total passé
    - [x] Moyenne journalière
    - [x] Moyenne hebdomadaire
    - [x] Moyenne mensuelle
    - [x] Fréquence (nombre de visites)
    - [x] Première et dernière visite
- [x] Nouveaux endpoints HTTP avec filtres
- [x] Carte Lovelace améliorée avec panel de filtres
- [x] Service export_excel

### Idées pour après la 1.0.0
- [ ] Zones ignorées (ex. ne pas enregistrer les passages < 2 min)
- [ ] Notifications de changement de zone (blueprint)
- [ ] Colonnes GPS optionnelles dans le CSV (à discuter : vie privée)

### Version 1.0.0 (cette branche)
- [x] Audit complet (`docs/AUDIT-V1.0.0.md`) et correction de tous les points bloquants / importants
- [x] Tests automatisés sur un Home Assistant réel (74) + test jsdom de la carte
- [x] Documentation réécrite, CHANGELOG, notes de migration
- [x] Carte Lovelace auto-chargée, tableau de bord à trois niveaux
- [ ] Validation manuelle sur une instance réelle (navigateur + appli compagnon) avant le tag
- [ ] Publication sur le dépôt HACS par défaut (après la 1.0.0)

---

## 10. Notes de Développement

*Section pour les notes temporaires pendant le développement*

### Session 1 - Création initiale (v0.0.1)
- **Date** : 2024
- **Objectif** : Création de la structure complète de l'intégration v0.0.1
- **Fichiers créés** :
  - `context.md` - Documentation de travail
  - `hacs.json` - Configuration HACS
  - `README.md` - Documentation utilisateur
  - `LICENSE` - Licence MIT
  - `CHANGELOG.md` - Journal des modifications
  - `custom_components/suivi_presence/__init__.py` - Point d'entrée
  - `custom_components/suivi_presence/manifest.json` - Métadonnées
  - `custom_components/suivi_presence/const.py` - Constantes
  - `custom_components/suivi_presence/config_flow.py` - Configuration UI
  - `custom_components/suivi_presence/sensor.py` - Entités sensor
  - `custom_components/suivi_presence/services.yaml` - Services
  - `custom_components/suivi_presence/strings.json` - Traductions
  - `custom_components/suivi_presence/translations/fr.json` - FR
  - `custom_components/suivi_presence/translations/en.json` - EN
  - `custom_components/suivi_presence/www/suivi-presence-card.js` - Carte Lovelace
  - `examples/lovelace-dashboard.yaml` - Exemple tableau de bord

- **Architecture décidée** :
  - Suivi basé sur `async_track_state_change_event` pour les entités `person`
  - CSV avec colonnes : timestamp, person, previous_zone, new_zone, duration
  - HTTP views pour téléchargement (authentifié)
  - 4 sensors : principal, personnes_home, personnes_away, total_changes

### Session 2 - Export avancé (v0.1.0)
- **Date** : 2024
- **Objectif** : Ajout des exports filtrables CSV/Excel avec statistiques
- **Fichiers créés** :
  - `custom_components/suivi_presence/export.py` - Module d'export

- **Fichiers modifiés** :
  - `__init__.py` - Nouveaux services et endpoints HTTP
  - `const.py` - Nouvelles constantes pour exports
  - `manifest.json` - Version 0.1.0, ajout openpyxl
  - `services.yaml` - Services export_csv et export_excel avec paramètres
  - `www/suivi-presence-card.js` - Panel de filtres, boutons CSV/Excel

- **Fonctionnalités ajoutées** :
  - CSV permanent (source de données illimitée)
  - Export CSV filtrable (dates, personnes)
  - Export Excel avec feuilles par personne
  - Statistiques automatiques par zone dans Excel
  - 3 endpoints HTTP : /download, /download/csv, /download/excel
  - Interface de filtrage dans la carte Lovelace

- **Dépendance ajoutée** : `openpyxl>=3.1.0`

---

### Session 3 - Audit et refonte 1.0.0
- **Date** : 2026-10-08
- **Objectif** : audit de maturité, correction des bugs bloquants, refonte du tableau de bord
- **Décisions d'architecture** :
  - Enregistrement « domaine » unique (`async_setup`) pour les vues HTTP, le websocket, le
    statique et la ressource frontend ; une entrée de configuration unique (`single_config_entry`).
  - Données volumineuses hors des attributs d'entités : websocket pour la carte.
  - Carte Lovelace en JS natif sans build, auto-chargée (`add_extra_js_url`), cartes natives
    (`map`, `history-graph`, `logbook`) pour le reste : aucune dépendance HACS.
  - Téléchargements via chemins signés.
  - Statistiques par intervalles découpés à la période (`stats.py`).
  - Export Excel écrit par l'intégration (`xlsx_writer.py`) : aucune dépendance à installer
    sur l'hôte, plus de bouton grisé.
- **Tests** : `pytest` (74, dont ouverture du classeur par LibreOffice), `ruff`, `node tests/card/test_card.mjs`, CI GitHub Actions.

## 11. Contacts et Ressources

### Documentation Home Assistant
- [Développement d'intégrations](https://developers.home-assistant.io/docs/creating_integration_index)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Zone](https://www.home-assistant.io/integrations/zone/)
- [Person](https://www.home-assistant.io/integrations/person/)

---

*Dernière mise à jour : Version 1.0.2*
