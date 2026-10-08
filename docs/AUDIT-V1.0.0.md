# Audit technique — passage de la bêta à la V1.0.0

> Intégration **Suivi de Présence** (`suivi_presence`) — dépôt `FigurinePanda43/Suivi-Position-Home-Assistant`
> État audité : branche `main`, commit `5a44276` (version déclarée 0.1.1).
> Audit réalisé le 2026-10-08. Les corrections apportées suite à cet audit sont listées dans `CHANGELOG.md`.

---

## 0. Remarque préliminaire : ce que l'intégration fait réellement

Le dépôt s'appelle « Suivi-Position » mais l'intégration est un **suivi de présence par zones** :
elle écoute les entités `person.*`, enregistre chaque **changement de zone** (`home → travail`,
`travail → not_home`, …) dans un CSV permanent, et calcule des durées de séjour par zone.

Elle **ne stocke ni coordonnées GPS, ni vitesse, ni trajets**. Les coordonnées courantes des personnes
existent dans Home Assistant (attributs `latitude` / `longitude` / `gps_accuracy` de `person.*`) et
peuvent être affichées par la carte `map` native, mais l'intégration elle-même ne les exploite pas.

Conséquence pour la refonte du tableau de bord : les notions de « vitesse », « distance parcourue »,
« trajet » du cahier des charges **ne sont pas disponibles et ne doivent pas être inventées**. Le
tableau de bord est reconstruit autour de ce que les données permettent réellement : *où est chaque
personne, depuis quand, la donnée est-elle fraîche, quels ont été ses déplacements entre zones,
combien de temps par zone, et comment exporter tout cela.*

---

## 1. Synthèse

Les trois plantages signalés comme bloquants ont été **reproduits par des tests automatisés** exécutés sur Home Assistant 2026.2.3 contre le code non modifié (voir `tests/`).

| Verdict | **NO GO en l'état** pour la 0.1.1. **GO conditionnel** après les corrections de cette branche (voir §6). |
|---|---|
| Points forts | Idée simple et utile (historique illimité des présences), stockage append-only robuste, auth sur les endpoints HTTP, dépendance Excel rendue optionnelle. |
| Points bloquants | Aucun téléchargement CSV n'aboutit (erreur aiohttp sur le type MIME) ; l'export filtré (CSV **et** Excel) plante en plus sur les fuseaux horaires ; options de l'intégration inutilisables ; endpoints HTTP figés sur un ancien tracker après rechargement ; aucun test ; ressource Lovelace à enregistrer à la main ; fichiers `.pyc` versionnés ; métadonnées HACS incohérentes. |

---

## 2. Architecture et fonctionnement — constats détaillés

### 2.1 Stockage et modèle de données
- **Bien** : CSV append-only, chargé au démarrage, verrou `asyncio.Lock` pour l'écriture. Règle « ne jamais supprimer de colonne » documentée dans `context.md`.
- **Problème (bloquant)** — `custom_components/suivi_presence/export.py:124` : `filter_history()` compare des horodatages **aware UTC** (issus de `state.last_changed.isoformat()`) avec des dates **naïves** envoyées par la carte (`2025-09-01T00:00:00`) → `TypeError: can't compare offset-naive and offset-aware datetimes`. Reproduit : tout export CSV ou Excel avec un filtre de date renvoie **HTTP 500**. C'est la cause première des « téléchargements qui ne fonctionnent pas ».
- **Problème (important)** — fuseau horaire : les dates stockées sont en UTC ; l'Excel les affiche telles quelles (`strftime` sans conversion) → décalage de 1 h / 2 h pour un utilisateur en France. Les filtres de dates saisis « en local » sont interprétés en UTC.
- **Problème (important)** — la colonne `duration_in_previous` contient `str(timedelta)` (`1 day, 2:03:04.567890`) : anglais, microsecondes, format non documenté (le README annonce `12:30:00`). `duration_seconds` est un float avec microsecondes.
- **Problème (amélioration)** — une durée de 0 s est stockée comme chaîne vide (`duration_seconds if duration_seconds else ""`).

### 2.2 Suivi des changements d'état
- **Bien** : écoute par `async_track_state_change_event`, ignore `unknown`/`unavailable`, ignore les non-changements.
- **Problème (important)** — redémarrage : au démarrage, `_person_states[...]["last_changed"]` prend la valeur de `state.last_changed` **au moment du redémarrage**. La durée dans la zone précédente est donc fausse après chaque redémarrage de Home Assistant. Par ailleurs, un changement de zone survenu **pendant** l'arrêt de HA est perdu (aucune comparaison entre la dernière zone connue du CSV et la zone courante).
- **Problème (important)** — la liste des personnes est figée au démarrage (`hass.states.async_all("person")`). Une personne créée ensuite n'est jamais suivie avant redémarrage.
- **Problème (important)** — les capteurs ne sont **jamais poussés** : aucun `async_write_ha_state()` après un enregistrement. Ils sont rafraîchis uniquement par le *polling* par défaut de la plateforme (toutes les 15 à 30 s), alors que `manifest.json` déclare `local_push`.

### 2.3 Capteurs
- Le capteur principal expose `recent_history` (50 enregistrements) et `data_range` (calculé en parcourant **tout** l'historique) dans ses **attributs**. Ces attributs sont écrits dans la base du *recorder* à chaque changement → gonflement de la base de données et dépassement probable de la limite de taille d'attributs. Anti-pattern reconnu par Home Assistant ; les données volumineuses doivent passer par une API (websocket) et non par les attributs d'état.
- `available` forcé à `True` : un capteur dont le tracker n'a pas démarré se déclare disponible avec des valeurs nulles.
- `async_update` vide sur le capteur principal, absent des autres : hérité du mode polling, inutile en mode push.

### 2.4 Configuration (config flow / options flow)
- **Problème (bloquant)** — `custom_components/suivi_presence/config_flow.py:96` : `SuiviPresenceOptionsFlowHandler(config_entry)` alors que la classe n'a pas de `__init__` acceptant un argument → `TypeError` dès que l'utilisateur clique sur **Configurer**. À vérifier version par version, mais sur les versions récentes de Home Assistant (≥ 2024.12) l'attribut `config_entry` est injecté par le framework et ne doit plus être passé au constructeur.
- **Problème (important)** — `scan_interval` est proposé à la configuration et dans les options mais **n'est jamais utilisé** (le suivi est événementiel). `tracked_persons` est traduit mais jamais proposé ni utilisé. Les options ne déclenchent **aucun rechargement** de l'entrée (pas d'`add_update_listener`).
- La validation du chemin CSV ne vérifie que l'existence du dossier parent, pas les droits d'écriture.
- `strings.json` ne couvre pas le service `export_excel` ; `services.yaml` utilise des sélecteurs `text` pour les dates (pas de `date`).

### 2.5 Endpoints HTTP et sécurité
- **Bien** : `requires_auth = True` sur les 4 vues ; la carte envoie bien le *bearer token*.
- **Problème (bloquant)** — `custom_components/suivi_presence/__init__.py:242,297,386` : les vues passent `content_type="text/csv; charset=utf-8"` (et `application/json; charset=utf-8`) à `aiohttp.web.Response`, qui lève `ValueError: charset must not be in content_type argument`. Reproduit sur Home Assistant 2026.2 : **le téléchargement CSV complet, le CSV filtré et l'endpoint JSON `/api/suivi_presence/data` renvoient tous HTTP 500**, quel que soit le filtre. Seul l'export Excel non filtré pouvait aboutir (si `openpyxl` est installé). C'est la première cause des « téléchargements qui ne fonctionnent pas » ; le bug des fuseaux horaires (§2.1) est la seconde.
- **Problème (important)** — les vues sont enregistrées **à chaque** `async_setup_entry` avec une référence directe au `PresenceTracker` courant. Après un rechargement de l'intégration (changement d'options, `Recharger`), les vues continuent de servir **l'ancien tracker arrêté** : les téléchargements renvoient des données figées. Les vues HTTP ne peuvent pas être désenregistrées dans Home Assistant ; elles doivent résoudre le tracker **au moment de la requête** et être enregistrées une seule fois.
- **Problème (important)** — la carte utilise `hass.auth.data.access_token` brut dans un `fetch`. Le jeton expire (par défaut 30 min) et n'est pas rafraîchi par ce chemin ; un onglet laissé ouvert produit des 401. De plus, le téléchargement via `blob:` + attribut `download` **ne fonctionne pas dans l'application compagnon iOS** et de manière aléatoire sur Android. Home Assistant fournit pour cela les **chemins signés** (`auth/sign_path`), utilisés par ses propres téléchargements (sauvegardes, médias).
- `clear_history` est destructif, irréversible, sans sauvegarde préalable et appelable par tout utilisateur non administrateur — en contradiction avec la règle « toute perte de données est INACCEPTABLE » de `context.md`.
- Pas d'exposition non authentifiée des données de localisation constatée. Les données servies sont des noms de zones, pas des coordonnées.

### 2.6 Chargement de la ressource frontend
- La ressource JS est servie sous `/local/suivi_presence/...` : `/local/` est le préfixe réservé au dossier `config/www` de l'utilisateur ; collision possible et convention non respectée.
- L'utilisateur doit **enregistrer la ressource à la main** dans *Paramètres → Tableaux de bord → Ressources*. Étape oubliée = carte « Custom element doesn't exist ». Home Assistant permet à une intégration d'injecter sa ressource automatiquement (`frontend.add_extra_js_url`).
- Aucun paramètre de *cache busting* : après une mise à jour, les navigateurs gardent l'ancienne carte.

### 2.7 Carte Lovelace (`www/suivi-presence-card.js`)
- `getConfigElement()` renvoie `suivi-presence-card-editor` **qui n'existe pas** → l'éditeur visuel de la carte affiche une erreur.
- Les options `show_history` et `history_count` sont acceptées puis **ignorées** (toujours 10 lignes, toujours affiché).
- Détection des entités par préfixe `sensor.suivi_de_presence*` : casse si l'utilisateur renomme l'appareil ou les entités, ou utilise HA en anglais. Le registre des entités (`hass.entities[...].platform`) permet une détection fiable.
- `_updateData()` reconstruit tout le DOM (`innerHTML`) **à chaque** mise à jour de `hass`, c'est-à-dire à chaque changement d'état dans toute l'installation (plusieurs fois par seconde) : gaspillage, scintillement, perte de focus sur les cases à cocher.
- Noms de personnes et de zones injectés sans échappement HTML.
- Erreurs signalées par `alert()`.
- Locale `fr-FR` codée en dur, pas de traduction.
- Les filtres de dates envoient des dates naïves (cf. 2.1) : **tous les exports filtrés échouent**.

### 2.8 Qualité logicielle
- **Aucun test automatisé**, aucune CI (ni `pytest`, ni `hassfest`, ni validation HACS).
- `__pycache__/*.pyc` versionnés, pas de `.gitignore`.
- Numéros de version incohérents : `manifest.json` 0.1.1, `const.py` 0.1.0, `README` 0.1.0, en-tête JS 0.1.0 / console 0.1.1, `examples/` 0.1.0, `CHANGELOG` « 2024-XX-XX ».
- `hacs.json` : clés `domains` et `iot_class` **non reconnues** par HACS ; `homeassistant: 2023.1.0` **faux** (`StaticPathConfig` n'existe que depuis 2024.6) ; `iot_class` `local_polling` contredit le manifest `local_push`.
- `manifest.json` : `http`/`frontend` utilisés mais absents de `dependencies`.
- Code mort : `CONF_SCAN_INTERVAL`, `CONF_TRACKED_PERSONS`, `SERVICE_DOWNLOAD_CSV`, constantes `PANEL_*`, `STATE_*` redéfinies alors qu'importées de `homeassistant.const`, `async_setup` qui ignore la configuration YAML pourtant documentée dans le README.
- Logging : f-strings dans les appels `_LOGGER` (interdit par les conventions HA), niveau `info` abusif au démarrage, `except Exception` large.
- Export Excel : feuilles nommées d'après la personne sans nettoyage des caractères interdits (`/ \ ? * [ ] :`), cellules de dates et de nombres écrites en **texte** (impossible de trier / filtrer / sommer dans Excel), largeur de colonnes fixe.
- La statistique « temps par zone » ne tient pas compte du séjour **en cours** (non terminé) ; la fréquence compte les arrivées ; les moyennes sont calculées sur l'étendue des données et non sur la période filtrée. À documenter.

---

## 3. Audit fonctionnel du tableau de bord fourni

| Élément | Objectif | Fonctionne ? | Verdict |
|---|---|---|---|
| `custom:suivi-presence-card` — compteurs À domicile / Absents / Enregistrements | Vue immédiate | Oui | **Conserver, réorganiser** : le compteur « Enregistrements » n'aide personne au quotidien → relégué en pied de carte. |
| Badges personnes par catégorie (domicile / absents / autres zones) | Qui est où | Oui | **Remplacer** par une ligne par personne : zone + *depuis* + fraîcheur GPS + accès à la fiche. Trois listes séparées obligent à chercher une personne. |
| Bouton **Filtres** (dates + cases personnes) | Préparer l'export | Partiellement | **Remplacer** par des raccourcis de période (Aujourd'hui / 24 h / 7 j / 30 j / Personnalisé) qui pilotent *aussi* l'historique affiché et le résumé, pas seulement l'export. |
| Bouton **CSV** | Télécharger | **Non** avec filtre (500), fragile sans filtre (jeton expiré, appli mobile) | **Corriger** (fuseau, chemin signé). |
| Bouton **Excel** | Télécharger | **Non** avec filtre ; sinon dépend d'openpyxl | **Corriger** + vrai format de cellules. |
| « Données disponibles : du … au … » | Contexte | Oui | **Conserver** discrètement en pied de carte. |
| Tableau « Historique récent » (10 lignes) | Comprendre les déplacements | Oui, mais figé à 10, sans période | **Remplacer** par une liste groupée par jour, filtrée par la période choisie, avec la durée de séjour. |
| Carte `entities` « Statut des Présences » | Compteurs | Oui | **Supprimer** : doublon exact de la carte principale. |
| `statistics-graph` « Évolution des changements » | Tendance | Oui, mais signification faible | **Supprimer** de la vue principale : « nombre de changements de zone cumulés » n'aide pas à une décision. |
| `history-graph` sur les compteurs domicile/absents | Historique | Oui | **Remplacer** par un `history-graph` sur les entités `person.*` elles-mêmes : la frise affiche **les zones** de chaque personne (natif, lisible, sans dépendance). |
| Carte `markdown` « Instructions » | Documentation | Oui | **Supprimer** : la documentation n'a pas sa place dans un tableau de bord d'usage quotidien ; déplacée dans le README. |
| *(absent)* Carte géographique | Où sont-ils ? | — | **Ajouter** la carte `map` native sur `person.*` avec `hours_to_show` : position courante, précision GPS, trajet des dernières heures (données du recorder). Aucune dépendance. |
| *(absent)* Journal natif (`logbook`) des personnes | Chronologie textuelle | — | **Ajouter** en vue secondaire : « Jean est passé de maison à travail » généré par HA. |

---

## 4. Évaluation par critère (état audité, avant corrections)

| Critère | Note /10 | Justification |
|---|---|---|
| Stabilité | 4 | Enregistrement fiable en régime nominal ; durées fausses après redémarrage ; changements de zone perdus pendant l'arrêt ; endpoints figés après rechargement. |
| Compatibilité HA | 5 | APIs récentes (`StaticPathConfig`) utilisées mais `hacs.json` annonce 2023.1 ; `FlowResult` déprécié ; options flow cassé ; dépendances `http`/`frontend` non déclarées. |
| Configuration | 4 | Config flow fonctionnel ; options inutilisables ; `scan_interval` factice ; ressource Lovelace manuelle ; YAML documenté mais non implémenté. |
| Robustesse | 2 | Tout téléchargement CSV → 500 ; export filtré → 500 ; aucune gestion d'erreur dans les vues HTTP ; `clear_history` sans sauvegarde. |
| Performance | 5 | Historique en mémoire acceptable ; attributs volumineux écrits dans le recorder ; carte qui re-rend tout le DOM à chaque événement HA. |
| Sécurité | 6 | Auth obligatoire sur les endpoints ; pas de fuite de coordonnées ; mais effacement irréversible ouvert à tous les utilisateurs, jeton brut dans les fetch. |
| Maintenance | 5 | Code lisible et commenté ; code mort, duplication des parseurs de dates, versions incohérentes, pas de `.gitignore`. |
| Documentation | 6 | README complet et clair ; mais décrit des fonctions inexistantes (YAML) et un format de durée faux ; CHANGELOG daté « 2024-XX-XX ». |
| Fonctionnalités | 4 | Suivi + CSV complet opérationnels ; exports filtrés, options, éditeur de carte : annoncés et non opérationnels. |
| Interface | 4 | Fonctionne mais lourde, redondante, pas de carte géographique, boutons défaillants. |
| Tests | 0 | Aucun test, aucune CI. |
| Distribution HACS | 5 | Structure correcte ; `hacs.json` avec clés invalides et version minimale fausse ; `.pyc` livrés. |

**Moyenne : 4,2 / 10.**

---

## 5. Classification des problèmes

### Bloquants (empêchent la V1.0.0)
1. Tous les téléchargements CSV et l'endpoint JSON → `ValueError` aiohttp (charset dans `content_type`) → HTTP 500 (`__init__.py:242,297,386`).
2. Export CSV/Excel filtré par date → `TypeError` → HTTP 500 (`export.py:124`).
3. Options de l'intégration : `TypeError` à l'ouverture (`config_flow.py:96`).
4. Vues HTTP liées à un tracker obsolète après rechargement (`__init__.py:214-219`).
5. Téléchargement non fiable (jeton brut, `blob:` incompatible appli mobile).
6. Aucun test automatisé ; aucune validation `hassfest` / HACS.
7. `hacs.json` invalide (clés inconnues, version minimale fausse).
8. `__pycache__` versionné.

### Importants (à corriger avant publication)
9. Fuseau horaire : stockage UTC non converti dans l'Excel et les filtres.
10. Durées : format `str(timedelta)` non documenté, microsecondes.
11. Redémarrage : durées fausses, transitions manquées.
12. Capteurs en polling au lieu de push ; attributs volumineux dans le recorder.
13. Personnes ajoutées après le démarrage non suivies.
14. `clear_history` sans sauvegarde ni restriction administrateur.
15. Ressource Lovelace manuelle, préfixe `/local/` détourné, pas de cache busting.
16. Carte : `getConfigElement` cassé, options ignorées, détection d'entités fragile, re-rendu permanent, pas d'échappement HTML.
17. Excel : cellules en texte, noms de feuilles non nettoyés.
18. Versions incohérentes ; `scan_interval` factice ; YAML documenté non implémenté.

### Améliorations (reportables)
19. Traductions complètes (services, options) et i18n de la carte.
20. Services d'export renvoyant une réponse (chemin, nombre de lignes) pour les automatisations.
21. Feuille « Résumé » dans l'Excel.
22. Comptabiliser le séjour en cours dans les statistiques.
23. CI GitHub Actions.

---

## 6. Conclusion GO / NO GO

**NO GO pour la 0.1.1 telle quelle.** Trois des fonctions mises en avant (téléchargement CSV, export filtré, configuration) sont cassées, le chemin de téléchargement est fragile, et rien n'est testé.

**GO conditionnel pour la 1.0.0 après les travaux de cette branche**, à condition que :
1. tous les points *bloquants* et *importants* ci-dessus soient corrigés (fait sur cette branche, voir `CHANGELOG.md`) ;
2. la suite de tests automatisés passe (fait : `pytest` sur un Home Assistant réel en environnement de test) ;
3. **une validation manuelle sur une instance Home Assistant réelle** soit effectuée par le mainteneur avant de poser le tag `v1.0.0` : chargement de la carte, téléchargements CSV et Excel depuis un navigateur **et** depuis l'application compagnon, rendu mobile. Cette validation ne peut pas être réalisée depuis l'environnement d'audit (pas d'instance HA avec frontend ni appareil mobile).

Les notes révisées après corrections sont données dans `docs/REFONTE-TABLEAU-DE-BORD.md` §6.
