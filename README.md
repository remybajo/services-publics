# Services publics : ce que disent les chiffres publics

Rapports chiffrés sur l'état des services publics en France, construits uniquement à partir de données publiques ouvertes : santé, transports, La Poste, logement, éducation, et leur croisement par département.

Le site (`site_services_publics/`) réunit les six rapports, avec des cartes interactives par département. Chaque chiffre peut être recalculé à partir des scripts de ce dépôt ; chaque graphique est accompagné de ses limites.

## Organisation

| Étape | Fichiers | Rôle |
|---|---|---|
| 1. Nettoyage | `nettoyer_<thème>.py` | Lit les fichiers bruts de `donnees_brutes/<thème>/` et produit des CSV propres dans `donnees_propres/<thème>/` (anomalies signalées, jamais supprimées) |
| 2. Calcul | `calculer_chiffres_<thème>.py` | Calcule tous les chiffres d'un rapport dans `chiffres_<thème>.json`, chacun avec sa définition |
| 3. Rédaction | `generer_rapport_<thème>.py` | Produit `rapports/rapport_<thème>.html` à partir du JSON, sans aucun chiffre saisi à la main |
| 4. Site | `assembler_site.py` | Assemble `site_services_publics/` (menu commun et page d'accueil) |

Modules partagés : `graphiques_svg.py` (graphiques et formats français), `cartes_svg.py` (cartes par département), `lecture_xlsx.py` (lecture des fichiers Excel sans dépendance).

Python 3, bibliothèque standard uniquement. Pour tout rejouer :

```bash
python3 nettoyer_sante.py && python3 calculer_chiffres_sante.py && python3 generer_rapport_sante.py
python3 assembler_site.py
```

(même enchaînement pour `transports`, `poste`, `logement`, `education` ; `calculer_chiffres_comparaisons.py` rapporte ensuite les services à la population et les compare à l'Europe et à l'OCDE, avant la génération des rapports ; `calculer_chiffres_territoires.py` et `generer_rapport_territoires.py` croisent les cinq thèmes.)

## Données et méthode

Les données ne sont pas versionnées dans ce dépôt (plusieurs centaines de Mo) : elles se retéléchargent depuis leurs producteurs et se placent dans `donnees_brutes/<thème>/`. La liste complète des jeux de données, avec lien direct, licence et date de téléchargement, figure sur la page « Méthode et sources » du site (`site_services_publics/methode.html`, générée à partir de `kit_presse.py`).

Producteurs : DREES (santé) ; Autorité de régulation des transports et SNCF (transports) ; Insee et La Poste (réseau postal) ; SDES, ministère chargé du logement et Cnaf (logement) ; DEPP et SIES (éducation) ; Insee, OCDE et Eurostat (comparaisons) ; Etalab (fond de carte, inclus dans `donnees_brutes/cartes/`). Licences : Licence Ouverte pour la plupart ; ODbL pour les données SNCF et une partie des données de La Poste ; CC BY 4.0 pour l'OCDE et Eurostat.

Textes et graphiques du site : licence CC BY 4.0. Auteur : Rémy Bajolet.

## Règles du projet

Les principales :

- tout chiffre publié est recalculable à partir des données sources : aucune estimation ni extrapolation ;
- les limites des données sont signalées à côté des chiffres ;
- les interprétations sont signalées comme telles (encadrés « Notre lecture ») ;
- chaque chiffre est vérifié de façon indépendante avant publication.

## État

Les six rapports (santé, transports, La Poste, logement, éducation, territoires) ont été vérifiés chiffre par chiffre de façon indépendante, cartes et comparaisons comprises (version du 15 novembre 2026). Ils ne retiennent que les analyses qui montrent un recul des services publics ; le contexte nécessaire à la lecture de chaque chiffre est conservé à côté de lui.
