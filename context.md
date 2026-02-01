# Context - Intégration Suivi de Présence pour Home Assistant

## Version actuelle : 0.0.1

---

## 1. Description du Projet

Cette intégration Home Assistant permet de suivre les changements de zone de toutes les personnes configurées dans Home Assistant. Elle enregistre chaque mouvement dans un fichier CSV et offre un tableau de bord pour visualiser et télécharger ces données.

### Fonctionnalités principales
- Suivi automatique des changements de zone pour chaque personne
- Enregistrement horodaté dans un fichier CSV
- Tableau de bord de visualisation
- Téléchargement du fichier CSV
- Compatible avec toutes les installations Home Assistant

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
│       ├── __init__.py          # Point d'entrée de l'intégration
│       ├── manifest.json        # Métadonnées de l'intégration
│       ├── const.py             # Constantes
│       ├── config_flow.py       # Configuration UI
│       ├── sensor.py            # Entités sensor
│       ├── services.yaml        # Définition des services
│       ├── strings.json         # Traductions
│       ├── translations/
│       │   ├── fr.json          # Traductions françaises
│       │   └── en.json          # Traductions anglaises
│       └── www/
│           └── suivi-presence-card.js  # Carte Lovelace personnalisée
├── examples/
│   └── lovelace-dashboard.yaml  # Exemple de configuration
├── hacs.json                    # Configuration HACS
├── README.md                    # Documentation principale
├── LICENSE                      # Licence MIT
├── CHANGELOG.md                 # Journal des modifications
└── context.md                   # Ce fichier
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
| - | - | - | - | - |

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

## 9. Roadmap

### Version 0.0.1 (actuelle) ✅
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

### Version 0.1.0 (prévue)
- [ ] Filtrage par personne (choix des personnes à suivre)
- [ ] Export personnalisé (plage de dates)
- [ ] Statistiques avancées
- [ ] Notifications de changement de zone

### Version 0.2.0 (prévue)
- [ ] Panel sidebar dédié
- [ ] Graphiques d'historique dans le dashboard
- [ ] Zones favorites / zones ignorées

### Version 1.0.0 (cible)
- [ ] Version stable et testée en production
- [ ] Tests unitaires complets
- [ ] Documentation complète
- [ ] Publication sur HACS default repository

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

---

## 11. Contacts et Ressources

### Documentation Home Assistant
- [Développement d'intégrations](https://developers.home-assistant.io/docs/creating_integration_index)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Zone](https://www.home-assistant.io/integrations/zone/)
- [Person](https://www.home-assistant.io/integrations/person/)

---

*Dernière mise à jour : Version 0.0.1*
