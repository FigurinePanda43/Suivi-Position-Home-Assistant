# Suivi de Présence pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/votre-repo/suivi-presence)

Une intégration Home Assistant pour suivre les mouvements des personnes entre les zones, avec stockage permanent et exports avancés (CSV/Excel).

## Pourquoi cette intégration ?

**Home Assistant ne conserve que 10 jours d'historique.** Cette intégration résout ce problème en :
- Stockant **toutes les données** dans un fichier CSV permanent
- Permettant des exports filtrés par dates et personnes
- Générant des rapports Excel avec statistiques détaillées

## Fonctionnalités

- **Suivi automatique** : Enregistre chaque changement de zone pour toutes les personnes
- **Stockage permanent** : CSV qui conserve l'historique complet (sans limite de 10 jours)
- **Export CSV** : Téléchargez l'historique avec filtres (dates, personnes)
- **Export Excel** : Rapport avancé avec une feuille par personne et statistiques :
  - Temps total par zone
  - Moyennes journalière, hebdomadaire, mensuelle
  - Fréquence des visites
- **Tableau de bord** : Visualisez les présences en temps réel
- **Compatible HACS** : Installation facile via HACS

## Installation

### Via HACS (recommandé)

1. Ouvrez HACS dans Home Assistant
2. Cliquez sur "Intégrations"
3. Cliquez sur les 3 points en haut à droite
4. Sélectionnez "Dépôts personnalisés"
5. Ajoutez l'URL de ce dépôt avec la catégorie "Intégration"
6. Recherchez "Suivi de Présence"
7. Cliquez sur "Télécharger"
8. Redémarrez Home Assistant

### Installation manuelle

1. Téléchargez le dossier `custom_components/suivi_presence`
2. Copiez-le dans votre dossier `config/custom_components/`
3. Redémarrez Home Assistant

## Configuration

### Via l'interface (recommandé)

1. Allez dans **Paramètres** > **Appareils et services**
2. Cliquez sur **Ajouter une intégration**
3. Recherchez **Suivi de Présence**
4. Suivez les instructions de configuration

### Configuration YAML (optionnel)

```yaml
suivi_presence:
  # Chemin du fichier CSV permanent (défaut: dans le dossier config)
  csv_path: "/config/suivi_presence_data.csv"
```

## Utilisation

### Carte Lovelace

Ajoutez la carte personnalisée à votre tableau de bord :

```yaml
type: custom:suivi-presence-card
title: Suivi de Présence
```

La carte offre :
- Vue en temps réel des présences
- Panel de filtres (dates, personnes)
- Boutons d'export CSV et Excel
- Historique récent des mouvements

### Services disponibles

#### `suivi_presence.export_csv`
Exporte l'historique en CSV avec filtres optionnels.

```yaml
service: suivi_presence.export_csv
data:
  filename: "mon_export.csv"      # Optionnel
  start_date: "2024-01-01"        # Optionnel - Format ISO
  end_date: "2024-12-31"          # Optionnel - Format ISO
  persons:                        # Optionnel - Liste des personnes
    - "Jean"
    - "Marie"
```

#### `suivi_presence.export_excel`
Exporte l'historique en Excel avec statistiques.

```yaml
service: suivi_presence.export_excel
data:
  filename: "rapport_presence"    # Optionnel (.xlsx ajouté auto)
  start_date: "2024-01-01"        # Optionnel
  end_date: "2024-12-31"          # Optionnel
  persons:                        # Optionnel
    - "Jean"
    - "Marie"
```

**Le fichier Excel contient pour chaque personne :**
- Une feuille dédiée avec son nom
- Tableau de statistiques par zone :
  - Temps total passé
  - Moyenne journalière
  - Moyenne hebdomadaire
  - Moyenne mensuelle
  - Fréquence (nombre de visites)
  - Première et dernière visite
- Tableau des données brutes

#### `suivi_presence.clear_history`
Efface l'historique enregistré. **Attention : irréversible !**

```yaml
service: suivi_presence.clear_history
```

### Endpoints HTTP

| Endpoint | Description |
|----------|-------------|
| `/api/suivi_presence/download` | Télécharge le CSV complet |
| `/api/suivi_presence/download/csv?start_date=...&end_date=...&persons=...` | CSV filtré |
| `/api/suivi_presence/download/excel?start_date=...&end_date=...&persons=...` | Excel avec stats |
| `/api/suivi_presence/data` | Données JSON pour le dashboard |

### Entités créées

| Entité | Description |
|--------|-------------|
| `sensor.suivi_presence_suivi_presence_main` | Sensor principal avec attributs |
| `sensor.suivi_presence_personnes_a_domicile` | Compteur personnes à domicile |
| `sensor.suivi_presence_personnes_absentes` | Compteur personnes absentes |
| `sensor.suivi_presence_total_des_changements` | Total des changements enregistrés |

## Format du CSV

Le fichier CSV contient les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| `timestamp` | Date et heure du changement (ISO 8601) |
| `person` | Nom de la personne |
| `previous_zone` | Zone précédente |
| `new_zone` | Nouvelle zone |
| `duration_in_previous` | Durée dans la zone précédente (format lisible) |
| `duration_seconds` | Durée en secondes (pour calculs) |

## Exemple de données CSV

```csv
timestamp,person,previous_zone,new_zone,duration_in_previous,duration_seconds
2024-01-15T08:30:00,Jean,home,work,12:30:00,45000
2024-01-15T12:00:00,Marie,work,restaurant,03:30:00,12600
2024-01-15T18:00:00,Jean,work,home,09:30:00,34200
```

## Structure du fichier Excel

Chaque personne a sa propre feuille contenant :

### Section Statistiques
| Zone | Temps total | Moy. jour | Moy. semaine | Moy. mois | Fréquence | 1ère visite | Dernière visite |
|------|-------------|-----------|--------------|-----------|-----------|-------------|-----------------|
| home | 5j 12h 30m | 1h 15m | 8h 45m | 35h | 45 | 2024-01-01 | 2024-01-31 |
| work | 3j 8h 15m | 45m | 5h 15m | 21h | 22 | 2024-01-02 | 2024-01-30 |

### Section Données
| Date/Heure | Zone précédente | Nouvelle zone | Durée |
|------------|-----------------|---------------|-------|
| 2024-01-15 08:30 | home | work | 12:30:00 |

## Zones supportées

L'intégration détecte automatiquement toutes les zones configurées dans Home Assistant :
- Zones personnalisées (travail, école, gym, etc.)
- Zone "home" (domicile)
- État "not_home" (absent/inconnu)

## Dépannage

### L'intégration ne détecte pas mes personnes

Vérifiez que :
1. Vous avez configuré des entités `person` dans Home Assistant
2. Ces personnes ont un device_tracker associé
3. Redémarrez Home Assistant après la configuration

### Le CSV/Excel ne se télécharge pas

1. Vérifiez les permissions du dossier `/config`
2. Consultez les logs dans **Paramètres** > **Système** > **Logs**
3. Vérifiez que vous êtes authentifié (les endpoints requièrent l'auth)

### Les statistiques Excel sont incorrectes

Les statistiques sont calculées sur la plage de dates sélectionnée. Pour des moyennes précises, assurez-vous d'avoir suffisamment de données historiques.

## Changelog

### 0.1.0
- **CSV permanent** comme source de données (contourne limite 10j HA)
- **Export CSV filtrable** par dates et personnes
- **Export Excel avancé** avec feuille par personne et statistiques
- Nouveaux endpoints HTTP avec filtres
- Carte Lovelace améliorée avec panel de filtres

### 0.0.1
- Structure de base de l'intégration
- Suivi des changements de zone
- Export CSV basique
- Tableau de bord initial

## Licence

MIT License - Voir [LICENSE](LICENSE) pour plus de détails.

## Support

- [Issues GitHub](https://github.com/votre-repo/suivi-presence/issues)
- [Discussions](https://github.com/votre-repo/suivi-presence/discussions)
