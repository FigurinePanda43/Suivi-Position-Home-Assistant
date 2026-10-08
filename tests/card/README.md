# Test de la carte Lovelace (jsdom)

```bash
npm install jsdom          # une fois, à la racine du dépôt (ou NODE_PATH vers un dossier qui le contient)
node tests/card/test_card.mjs
```

Le script instancie la carte dans un DOM simulé avec un faux objet `hass` dont `callWS`
répond comme l'API websocket de l'intégration, puis vérifie le rendu (personnes, alertes,
résumé, historique, exports) et les interactions (périodes, filtres, « Afficher plus »,
téléchargements via `auth/sign_path`). Il ne remplace pas un essai dans un vrai navigateur.
