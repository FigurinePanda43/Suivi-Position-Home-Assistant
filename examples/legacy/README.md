# Anciennes versions (sauvegarde)

Copies conformes des fichiers livrés avec la version 0.1.1, conservées pour permettre
un retour arrière simple :

- `lovelace-dashboard-0.1.yaml` : l'ancien tableau de bord d'exemple ;
- `suivi-presence-card-0.1.js` : l'ancienne carte Lovelace.

Pour revenir à l'ancienne carte : copiez `suivi-presence-card-0.1.js` dans
`config/www/` et déclarez-la comme ressource `/local/suivi-presence-card-0.1.js`
(type *Module JavaScript*). Elle reste compatible avec les capteurs créés par la
version 1.0.0 mais ses téléchargements souffrent des bugs corrigés en 1.0.0.
