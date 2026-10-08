# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) et ce projet
adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Non publié]

## [1.0.0] - 2026-10-08

Première version stable. Audit complet dans `docs/AUDIT-V1.0.0.md`, refonte du tableau de
bord dans `docs/REFONTE-TABLEAU-DE-BORD.md`.

### Corrigé
- **Téléchargement CSV : HTTP 500 systématique.** Les vues passaient `charset` dans
  `content_type`, ce qu'aiohttp refuse. Le téléchargement complet, le téléchargement filtré
  et l'endpoint JSON échouaient tous.
- **Exports filtrés par date : HTTP 500 / erreur de service.** Comparaison d'horodatages
  avec et sans fuseau (`TypeError`). Toutes les dates sont désormais interprétées dans le
  fuseau de Home Assistant (`2025-09-01` = toute la journée locale).
- **Options de l'intégration : plantage à l'ouverture** (`TypeError` sur le constructeur de
  l'options flow).
- **Endpoints HTTP figés après un rechargement** de l'intégration : ils résolvent le tracker
  à chaque requête.
- **Téléchargement depuis la carte** : remplacement du jeton brut + `blob:` (jeton expirant,
  incompatible avec l'application compagnon iOS) par les **chemins signés** de Home Assistant
  (`auth/sign_path`), comme pour les sauvegardes.
- **Redémarrage de Home Assistant** : la durée dans la zone précédente n'est plus réinitialisée
  au redémarrage (reconstruite depuis le CSV) et un changement de zone survenu pendant l'arrêt
  est enregistré (daté au redémarrage).
- **Personnes créées après le démarrage** : suivies immédiatement.
- **Capteurs** : mis à jour en push à chaque changement (plus de polling à 15–30 s) ; les
  attributs volumineux (`recent_history`) ne sont plus écrits dans le recorder.
- **Fuseau horaire dans l'Excel** : heures locales. **Cellules Excel typées** : dates réelles,
  durées au format `[h]:mm:ss` triables et sommables, nombres de secondes entiers.
- **Noms de feuilles Excel** : caractères interdits remplacés, doublons dédoublonnés, 31 caractères max.
- Carte : `getConfigElement` renvoyait un éditeur inexistant ; options `show_history` /
  `history_count` ignorées ; détection des entités par préfixe ; re-rendu complet à chaque
  événement Home Assistant ; noms non échappés ; erreurs par `alert()`.
- `hacs.json` : clés `domains` / `iot_class` non reconnues supprimées, version minimale de Home
  Assistant corrigée (2024.12.0 au lieu de 2023.1.0).
- `__pycache__` retiré du dépôt, `.gitignore` ajouté.
- Numéros de version alignés (manifest, carte, README).

### Ajouté
- **Carte Lovelace chargée automatiquement** par l'intégration (`frontend.add_extra_js_url`,
  URL versionnée pour invalider le cache). Plus aucune ressource à déclarer à la main.
- **Nouvelle carte** `custom:suivi-presence-card` : une ligne par personne (zone, « depuis »,
  fraîcheur et précision GPS, accès à la fiche), bloc « À vérifier », sélecteur de période
  (Aujourd'hui / 24 h / 7 j / 30 j / Tout / Personnalisé), filtre par personne, **temps par
  zone** sur la période, changements de zone groupés par jour, exports CSV / Excel de la
  période, détails techniques repliés, traductions FR / EN, responsive.
- **API websocket** `suivi_presence/overview` et `suivi_presence/history` (période, personnes,
  résumé par zone).
- **Statistiques par intervalles** (`stats.py`) : temps par zone exact pour n'importe quelle
  période, séjour en cours inclus.
- **Export Excel sans dépendance** : le classeur `.xlsx` est écrit par l'intégration elle-même
  (`xlsx_writer.py`, bibliothèque standard uniquement). Plus besoin d'installer `openpyxl` sur
  l'hôte, plus de bouton grisé. Feuille **Résumé** (toutes les personnes), puis une feuille par
  personne (statistiques + changements), filtres automatiques, volets figés.
- **Export CSV** : BOM UTF-8 (ouverture directe dans Excel), séparateur `;` optionnel
  (`delimiter`), filtre par nom **ou** par `person.*`.
- **Services** `export_csv` / `export_excel` : sélecteurs de date, réponse
  (`path`, `records`) utilisable dans les automatisations, fichiers confinés au dossier de
  configuration.
- **`clear_history`** : sauvegarde automatique du CSV (`.bak-avant-effacement-<date>`) avant
  effacement, réservé aux administrateurs, réponse avec le chemin de la sauvegarde.
- **Options** : personnes à suivre (sélecteur d'entités, vide = toutes) et chemin du CSV, avec
  validation d'écriture et rechargement automatique.
- Colonne CSV **`person_entity_id`** (ajout en fin de ligne, migration automatique avec
  sauvegarde `.bak-migration-<date>`).
- Nouveau tableau de bord d'exemple (`examples/lovelace-dashboard.yaml`) en trois vues
  (Présence / Historique / Technique) avec les cartes natives `map`, `history-graph`,
  `logbook`. Anciens fichiers conservés dans `examples/legacy/`.
- Tests automatisés (`tests/`, 74 tests sur un Home Assistant réel, dont une ouverture du classeur Excel par LibreOffice, + test jsdom de la carte),
  configuration `ruff`, CI GitHub Actions (pytest, ruff, hassfest, validation HACS, syntaxe JS).
- `manifest.json` : `single_config_entry`, `integration_type: service`, dépendances `http`,
  `frontend`, `websocket_api` déclarées.

### Modifié
- **Format de stockage** (rétrocompatible) : les horodatages sont écrits en **heure locale avec
  décalage** (`2025-09-01T10:30:00+02:00`, sans microsecondes) au lieu de l'UTC ; les durées en
  `H:MM:SS` (heures cumulées) et `duration_seconds` en entier. Les anciennes lignes restent
  lues telles quelles.
- Statique servi sous `/suivi_presence/` (l'ancien `/local/suivi_presence/` reste servi pour
  les ressources déclarées manuellement ; la déclaration manuelle peut être supprimée).
- Le capteur principal n'expose plus `recent_history` ni `csv_download_url` dans ses attributs.
- `scan_interval` supprimé de la configuration (le suivi est événementiel ; l'option n'avait
  jamais eu d'effet). La configuration YAML, documentée mais jamais implémentée, est retirée du
  README.
- Logs : moins verbeux au démarrage, plus de f-strings dans les appels de log.

### Migration depuis 0.1.x
1. Mettre à jour via HACS (ou copier `custom_components/suivi_presence`), redémarrer.
2. Le CSV existant est migré automatiquement (ajout d'une colonne) ; une sauvegarde
   `suivi_presence_data.csv.bak-migration-<date>` est créée à côté.
3. Supprimer la ressource Lovelace manuelle `/local/suivi_presence/suivi-presence-card.js`
   (Paramètres → Tableaux de bord → Ressources) : la carte est maintenant chargée par
   l'intégration.
4. Remplacer le tableau de bord par `examples/lovelace-dashboard.yaml` (ou garder l'ancien :
   les capteurs et leurs identifiants sont inchangés).
5. Les automatisations qui appelaient `export_csv` / `export_excel` continuent de fonctionner ;
   `clear_history` exige désormais un utilisateur administrateur (ou un appel sans utilisateur).

## [0.1.1] - 2026-09-13

### Corrigé
- L'intégration ne démarre plus si `openpyxl` est absent : `openpyxl` devient une dépendance
  **optionnelle**, importée uniquement au moment de l'export Excel ; avertissement dans les logs
  au démarrage, erreurs explicites (service, endpoint 503, carte).

## [0.1.0] - 2024

### Ajouté
- CSV permanent comme source de données (contourne la limite de 10 jours de Home Assistant).
- Export CSV filtrable par dates et personnes ; endpoint `/api/suivi_presence/download/csv`.
- Export Excel avec une feuille par personne et statistiques par zone ; service `export_excel` ;
  endpoint `/api/suivi_presence/download/excel`.
- Carte Lovelace avec panneau de filtres et boutons CSV / Excel.
- Colonne CSV `duration_seconds`.

## [0.0.1] - 2024

### Ajouté
- Structure initiale : config flow, suivi des changements de zone des `person.*`, CSV,
  endpoints HTTP, services `export_csv` / `clear_history`, quatre capteurs, carte Lovelace,
  traductions FR / EN, support HACS.
