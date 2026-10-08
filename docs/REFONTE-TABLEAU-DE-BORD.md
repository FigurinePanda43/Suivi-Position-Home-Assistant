# Refonte du tableau de bord — proposition et réalisation (1.0.0)

> Complément de `docs/AUDIT-V1.0.0.md`. Ce document explique **ce qui a été retenu, supprimé, regroupé et ajouté**, et pourquoi.

---

## 1. Ce que l'utilisateur doit comprendre en cinq secondes

L'intégration suit des **zones**, pas des trajets GPS. La question quotidienne n'est donc pas « à quelle vitesse roule-t-il ? » mais :

1. **Qui est où ?** (maison / au travail / absent)
2. **Depuis quand ?**
3. **Puis-je faire confiance à l'information ?** (traqueur disponible, position GPS récente)
4. **Y a-t-il quelque chose à vérifier ?** (traqueur indisponible, position figée)

Tout le premier écran de la carte répond à ces quatre questions, personne par personne, en une ligne chacune.

---

## 2. Comparaison des architectures

| Critère | A — Intégration + YAML de cartes natives/HACS | B — Intégration + carte Lovelace dédiée | **Retenu : hybride** |
|---|---|---|---|
| Installation | Copier-coller YAML, installer 2 à 4 cartes HACS (Mushroom, ApexCharts…) | Rien à installer de plus si la ressource est chargée par l'intégration | Carte dédiée **auto-chargée** + cartes **natives** uniquement (`map`, `history-graph`, `logbook`) |
| Sélection de période, filtres, exports | Impossible proprement : des `input_datetime` + scripts + boutons, état global partagé entre utilisateurs | Natif dans la carte, état local à l'onglet | Carte dédiée |
| Carte géographique | `map` native, excellente (position, précision, trajet du recorder) | À réécrire (Leaflet…) : lourd, redondant | **`map` native** |
| Frise des zones par personne | `history-graph` native, parfaite pour ça | À réécrire | **`history-graph` native** |
| Maintenance | YAML fragile aux renommages d'entités, dépendances tierces à suivre | Un fichier JS à maintenir, sans build | Un fichier JS vanilla (pas de bundler), zéro dépendance HACS |
| Mobile | Dépend des cartes tierces | Maîtrisé | CSS responsive dans la carte + layout `sections` natif |

**Décision.** Une carte dédiée pour tout ce qui est *spécifique à l'intégration* (état par personne, période, résumé par zone, historique, exports), et des cartes **natives** pour ce que Home Assistant fait déjà très bien (carte géographique, frise temporelle, journal). Aucune dépendance HACS supplémentaire. La carte est servie et déclarée **automatiquement** par l'intégration : la seule étape manuelle restante est de coller le YAML du tableau de bord.

Ce qui a été écarté :
- une **interface JavaScript dédiée / panneau latéral** : plus de code à maintenir pour un gain faible face au layout `sections` natif ;
- **Mushroom / Button Card / ApexCharts** : le résumé par zone tient dans une barre segmentée de 10 px rendue par la carte elle-même ; ces dépendances n'apporteraient que de la décoration.

---

## 3. Les trois niveaux d'information

### Niveau 1 — vue immédiate (en haut de la carte, toujours visible)
- En-tête : état du suivi (**actif / inactif**) et nombre de personnes.
- Bloc **« À vérifier »** : n'apparaît que s'il y a quelque chose à dire (traqueur indisponible, position GPS plus ancienne que `stale_after_minutes`, fichier CSV illisible).
- **Une ligne par personne** : avatar, nom, **badge de zone** coloré (maison / zone / absent / indisponible), **« depuis 2 h 15 »**, et la fraîcheur de la position (« Position mise à jour il y a 5 min · ±25 m », ou « Pas de position GPS »). Un clic ouvre la fiche Home Assistant de la personne (carte, attributs, historique) : c'est l'action *plus d'infos* native, toujours fonctionnelle.
- À côté, la **carte `map` native** : positions réelles, cercles de précision, trajet des dernières heures.

### Niveau 2 — analyse (même carte, sous les personnes)
- **Sélecteur de période** : Aujourd'hui · 24 h · 7 jours · 30 jours · Tout · Personnalisé (deux dates). Il pilote *tout* ce qui suit : résumé, historique **et** exports.
- **Filtre par personne** (puces), visible seulement s'il y a plusieurs personnes.
- **Temps par zone** sur la période : barre segmentée + légende « Maison **8 h 12** · 2 passages », séjour en cours signalé. Calcul exact par intervalles, découpé à la période (voir `stats.py`).
- **Changements de zone** groupés par jour : « 08:32 · Jean · Maison → Travail · après 12 h 30 à Maison », pagination « Afficher plus ».
- **Exporter la période** : boutons **CSV** et **Excel**, avec le nombre de changements concernés. Excel grisé (et expliqué) si `openpyxl` manque.
- Vue « Historique » : la même carte réglée sur 7 jours, `history-graph` sur 7 jours, `logbook` natif.

### Niveau 3 — technique (replié)
- `<details>` « Détails techniques » dans la carte : chemin du CSV, nombre d'enregistrements, plage de données, versions, noms des services.
- Vue « Technique » du tableau de bord : les 4 capteurs, le chemin CSV, un histogramme des changements par jour.

---

## 4. Audit élément par élément (rappel des décisions)

| Élément 0.1.1 | Décision | Remplacé par |
|---|---|---|
| Compteurs À domicile / Absents / Enregistrements | Supprimés du haut de carte | L'état par personne (plus informatif) ; « Enregistrements » en pied de carte |
| Trois listes de badges (domicile / absents / autres zones) | Supprimées | Une ligne par personne, triée par nom |
| Panneau « Filtres » (dates + cases) | Supprimé | Puces de période + puces de personnes, qui pilotent aussi l'affichage |
| Boutons CSV / Excel | Conservés, **réparés** | Chemins signés, fuseau horaire, Excel réel |
| « Données disponibles du … au … » | Conservé | Pied de carte « Détails techniques » |
| Tableau « Historique récent » (10 lignes fixes) | Remplacé | Liste par jour, filtrée par période, avec durées, pagination |
| Carte `entities` « Statut des Présences » | **Supprimée** | Doublon |
| `statistics-graph` « Évolution des changements » | Déplacée en vue Technique | Histogramme par jour (lisible) au lieu d'une courbe cumulative |
| `history-graph` sur les compteurs | Remplacée | `history-graph` sur les `person.*` (frise des zones) |
| Carte `markdown` « Instructions » | **Supprimée** | README |
| *(absent)* carte géographique | **Ajoutée** | `map` native |
| *(absent)* journal | **Ajouté** | `logbook` natif (vue Historique) |
| Éditeur visuel de la carte (`getConfigElement` cassé) | Supprimé | Options documentées en tête du fichier JS et dans le README |
| Options `show_history`, `history_count` ignorées | Remplacées | `show_summary`, `show_history`, `show_export`, `show_details`, `history_limit`, `default_period`, `persons`, `stale_after_minutes` — toutes **effectives** |

---

## 5. Audit des boutons et actions (après refonte)

| Action | Implémentation | Vérifié par |
|---|---|---|
| Clic sur une personne | événement `hass-more-info` → dialogue natif HA | revue de code (événement standard du frontend) ; à valider à l'écran |
| Puces de période / personnes | commande websocket `suivi_presence/history` avec `start`/`end`/`persons` | `tests/test_websocket.py`, test jsdom de la carte |
| Afficher plus | même commande avec `limit` augmenté | test jsdom |
| **CSV** | `auth/sign_path` → `/api/suivi_presence/download[/csv]?…` → `<a download>` | `tests/test_http.py::test_signed_path_download_without_token`, test jsdom (`sign_path` appelé avec le bon chemin) |
| **Excel** | idem vers `/download/excel` ; désactivé si `openpyxl` absent | `tests/test_http.py::test_excel_download_is_a_real_workbook` (classeur rechargé avec openpyxl), `test_excel_unavailable_returns_503_json` |
| Dates personnalisées | `change` sur `<input type=date>` ; inversion automatique si fin < début | test jsdom |

Il ne reste **aucun bouton** dont l'action n'est pas branchée.

---

## 6. Notes révisées après corrections

| Critère | Avant | Après | Ce qui a changé |
|---|---|---|---|
| Stabilité | 4 | 8 | Reconciliation au démarrage, personnes dynamiques, vues HTTP indépendantes du rechargement |
| Compatibilité HA | 5 | 8 | APIs actuelles (`ConfigFlowResult`, `OptionsFlow.config_entry`, `runtime_data`, `StaticPathConfig`, websocket), dépendances déclarées, `single_config_entry`, minimum HA 2024.12 annoncé |
| Configuration | 4 | 8 | Options fonctionnelles (personnes, chemin), rechargement automatique, ressource Lovelace automatique |
| Robustesse | 2 | 8 | Plus aucun 500 reproduit ; erreurs JSON explicites ; sauvegarde avant effacement |
| Performance | 5 | 8 | Capteurs en push, attributs volumineux retirés du recorder, carte qui ne re-rend que sur changement pertinent |
| Sécurité | 6 | 8 | Effacement réservé aux administrateurs, exports confinés au dossier de configuration, chemins signés à durée de vie courte |
| Maintenance | 5 | 8 | Modules séparés (tracker / stats / export / http / websocket), ruff, CI |
| Documentation | 6 | 8 | README réécrit sur le comportement réel, CHANGELOG daté, notes de migration |
| Fonctionnalités | 4 | 8 | Tout ce qui est annoncé est testé |
| Interface | 4 | 8 | Trois niveaux, carte géographique, aucun bouton mort — **rendu réel à valider à l'écran** |
| Tests | 0 | 8 | 74 tests Python sur un Home Assistant réel + test jsdom de la carte ; pas de test navigateur réel |
| Distribution HACS | 5 | 9 | `hacs.json` corrigé, `.pyc` retirés, CI hassfest + HACS |

**Moyenne : 8,1 / 10 — GO conditionnel** (validation visuelle et mobile par le mainteneur avant le tag, voir l'audit §6).

---

## 7. Limites assumées

- **Pas de vitesse, distance ni trajet long terme** : l'intégration ne stocke pas de coordonnées. Le trajet affiché par la carte `map` vient du recorder (quelques jours). Ajouter des colonnes GPS au CSV serait possible (format append-only) mais n'a pas été fait : hors périmètre d'un suivi de présence par zones, et impact vie privée à discuter.
- **Horodatage des changements manqués pendant un arrêt** : daté au redémarrage (meilleure estimation disponible), signalé dans les logs.
- **Statistiques** : « visites » = arrivées dans la zone pendant la période (+1 si la personne y était déjà au début) ; moyennes = total / nombre de jours de la période.
- **Export Excel** : nécessite `openpyxl` sur l'hôte (choix de la 0.1.1, conservé : un échec `pip` ne doit jamais empêcher le suivi de démarrer).
