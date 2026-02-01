# Suivi de Présence pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/votre-repo/suivi-presence)

Une intégration Home Assistant pour suivre les mouvements des personnes entre les zones et exporter les données en CSV.

## Fonctionnalités

- **Suivi automatique** : Enregistre chaque changement de zone pour toutes les personnes
- **Export CSV** : Téléchargez l'historique complet des mouvements
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
  # Intervalle de vérification en secondes (défaut: 30)
  scan_interval: 30

  # Chemin du fichier CSV (défaut: dans le dossier config)
  csv_path: "/config/suivi_presence.csv"
```

## Utilisation

### Tableau de bord

Accédez au tableau de bord via le menu latéral "Suivi Présence" pour :
- Voir l'état actuel de toutes les personnes
- Consulter l'historique des mouvements
- Télécharger le fichier CSV

### Services disponibles

#### `suivi_presence.export_csv`
Exporte l'historique en CSV.

```yaml
service: suivi_presence.export_csv
data:
  filename: "mon_export.csv"  # Optionnel
```

#### `suivi_presence.clear_history`
Efface l'historique enregistré.

```yaml
service: suivi_presence.clear_history
```

### Entités créées

| Entité | Description |
|--------|-------------|
| `sensor.suivi_presence_total` | Nombre total de personnes suivies |
| `sensor.suivi_presence_[person]` | État de chaque personne |

## Format du CSV

Le fichier CSV contient les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| `timestamp` | Date et heure du changement |
| `person` | Nom de la personne |
| `previous_zone` | Zone précédente |
| `new_zone` | Nouvelle zone |
| `duration_in_previous` | Durée dans la zone précédente |

## Exemple de données CSV

```csv
timestamp,person,previous_zone,new_zone,duration_in_previous
2024-01-15 08:30:00,Jean,home,work,12:30:00
2024-01-15 12:00:00,Marie,work,restaurant,03:30:00
2024-01-15 18:00:00,Jean,work,home,09:30:00
```

## Zones supportées

L'intégration détecte automatiquement toutes les zones configurées dans Home Assistant :
- Zones personnalisées
- Zone "home" (domicile)
- État "not_home" (absent)

## Dépannage

### L'intégration ne détecte pas mes personnes

Vérifiez que :
1. Vous avez configuré des entités `person` dans Home Assistant
2. Ces personnes ont un device_tracker associé
3. Redémarrez Home Assistant après la configuration

### Le CSV ne se télécharge pas

1. Vérifiez les permissions du dossier `/config`
2. Consultez les logs dans **Paramètres** > **Système** > **Logs**

## Contribution

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les détails.

## Changelog

### 0.0.1 (Version initiale - En développement)
- Structure de base de l'intégration
- Suivi des changements de zone
- Export CSV basique
- Tableau de bord initial

## Licence

MIT License - Voir [LICENSE](LICENSE) pour plus de détails.

## Support

- [Issues GitHub](https://github.com/votre-repo/suivi-presence/issues)
- [Discussions](https://github.com/votre-repo/suivi-presence/discussions)
