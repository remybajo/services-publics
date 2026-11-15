# Rapport de vérification (préparation presse)

Fichier de travail, hors du dossier servi (`site_services_publics/`). Chaque écart de chiffre est consigné ici avec l'ancienne valeur, la nouvelle et la cause.

## Rejeu complet de la chaîne (15 novembre 2026)

Toute la chaîne a été relancée à partir des fichiers bruts de `donnees_brutes/` : nettoyage, calcul, génération, assemblage.

- Les 7 fiches de chiffres (`chiffres_*.json`) sont identiques, octet pour octet, à celles de la version publiée.
- Les 7 pages régénérées sont identiques aux pages servies en ligne (services-publics.bajolet-remy.workers.dev), comparées octet pour octet.

## Écarts de chiffres

| Page | Chiffre | Ancienne valeur | Nouvelle valeur | Cause |
|---|---|---|---|---|
| La Poste | Agences postales à Paris, 2025 | 0 | non disponible | L'Insee ne publie pas d'observation pour Paris ; la valeur absente était comptée comme zéro. |
| La Poste | Part des bureaux parmi les points postaux à Paris, 2015 et 2025 | 99,5 % et 77,1 % | non disponible | Conséquence de la ligne précédente : le total des points postaux de Paris est incomplet. Les totaux nationaux ne changent pas. |
| Santé | Lits d'hôpital pour 100 000 habitants selon Eurostat, 2000-2024 | 797 → 534 (−33,0 %) | retiré | Rupture de série en 2013 et définition non comparable à la statistique française. |
| Éducation | Écoles publiques pour 10 000 enfants de moins de 10 ans, 2009-2025 | −3,8 % | −2,6 % | Mayotte comptée pour les écoles mais pas pour les enfants en 2009 ; calcul refait hors Mayotte aux deux dates. Corrigé avant la mise en ligne du 15 novembre. |
| Santé | Médecins généralistes pour 1 000 habitants selon l'OCDE | 1,62 → 1,38 (−14,8 %) | retiré | Ruptures de série de l'OCDE en 2009 et 2011 ; sur la série homogène 2011-2024, la baisse n'est que de 2,8 %. Corrigé avant la mise en ligne du 15 novembre. |

## Contrôles à la source sans changement de chiffre

- **La Poste, boîtes aux lettres des Hauts-de-Seine (2,5 % avant 10 h).** Valeur confirmée dans le fichier brut de La Poste : 983 des 1 093 boîtes du département ont une heure limite à 13 h, 27 à 9 h. La valeur est isolée mais exacte.
- **La Poste, heures limites.** Le fichier brut écrit les heures sous la forme `T13:00:00+00:00`. Le suffixe `+00:00` est repris tel quel ; l'heure est lue comme une heure locale, ce que la documentation de La Poste ne précise pas.
- **La Poste, horaires.** Horaires prévus par La Poste, médiane sur 13 semaines du 19 octobre 2026 au 18 janvier 2027 ; ce ne sont pas les horaires effectivement tenus.
- **Transports, dates des données** (métadonnées du portail SNCF) : statut des lignes, données traitées le 26 février 2026 ; points de vente, jeu mis en ligne le 7 janvier 2026, données traitées le 2 février 2024. Aucun jeu plus récent n'existe pour les points de vente sur le portail SNCF à la date du contrôle.
- **Territoires, robustesse.** Avec le quart le plus défavorable au lieu du cinquième, les 19 départements du groupe de référence restent tous dans le groupe (27 départements au total). Avec le rang moyen, 14 des 19 restent parmi les 19 premiers.
