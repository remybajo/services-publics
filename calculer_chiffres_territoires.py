"""Croise les fiches de chiffres des cinq thèmes pour mesurer les disparités entre départements (EDR-005 : tout est rejouable).

Lit donnees_propres/<thème>/chiffres_<thème>.json (déjà vérifiées) et produit donnees_propres/territoires/chiffres_territoires.json :
pour sept indicateurs, les écarts entre départements et, pour chaque département, le nombre d'indicateurs où il figure
dans le cinquième le plus défavorable. Aucun nouveau chiffre de base : seulement des classements et des comptages.
Usage : python3 calculer_chiffres_territoires.py
"""
import json
import math
import os
from collections import defaultdict

OUT = "donnees_propres/territoires"
MIN_INDICATEURS = 5  # nombre minimal d'indicateurs disponibles pour figurer au classement des cumuls


def fiche(theme):
    return json.load(open(f"donnees_propres/{theme}/chiffres_{theme}.json", encoding="utf-8"))


def par_dep(liste, cle, filtre=lambda o: True):
    return {o["departement"]: o[cle] for o in liste if o.get(cle) is not None and filtre(o)}


def indicateurs():
    """Sept indicateurs repris tels quels des fiches ; sens = « haut » si une valeur élevée est défavorable, « bas » sinon."""
    S, T, P, G, E = (fiche(t) for t in ("sante", "transports", "poste", "logement", "education"))
    return [
        {"cle": "sous_dotee", "theme": "Santé", "libelle": "Habitants en commune sous-dotée en généralistes", "unite": "%", "sens": "haut",
         "source": "sante/departements/part_sous_dotee", "valeurs": par_dep(S["departements"], "part_sous_dotee")},
        {"cle": "generalistes", "theme": "Santé", "libelle": "Évolution des généralistes pour 100 000 habitants", "unite": "% (évolution)", "sens": "bas",
         "source": "sante/departements/generalistes_pct", "valeurs": par_dep(S["departements"], "generalistes_pct")},
        {"cle": "bureaux_poste", "theme": "La Poste", "libelle": "Évolution du nombre de bureaux de poste", "unite": "% (évolution)", "sens": "bas",
         "source": "poste/evolution/departements/pct_bureaux", "valeurs": par_dep(P["evolution"]["departements"], "pct_bureaux")},
        {"cle": "sans_bureau", "theme": "La Poste", "libelle": "Habitants d'une commune sans bureau de poste", "unite": "%", "sens": "haut",
         "source": "poste/departements_2026/departements/part_pop_sans_bureau",
         "valeurs": par_dep(P["departements_2026"]["departements"], "part_pop_sans_bureau")},
        {"cle": "ecoles", "theme": "Éducation", "libelle": "Évolution du nombre d'écoles publiques", "unite": "% (évolution)", "sens": "bas",
         "source": "education/departements/departements/pct_ecoles_public",
         "valeurs": par_dep(E["departements"]["departements"], "pct_ecoles_public")},
        {"cle": "logements", "theme": "Logement", "libelle": "Évolution des mises en service de logements sociaux", "unite": "% (évolution)", "sens": "bas",
         "source": "logement/departements/departements/pct_mises_en_service",
         "valeurs": par_dep(G["departements"]["departements"], "pct_mises_en_service")},
        {"cle": "guichets", "theme": "Transports", "libelle": "Gares sans guichet", "unite": "%", "sens": "haut",
         "source": "transports/gares_departements/departements/part_sans_guichet (hors Île-de-France, départements d'au moins 10 gares)",
         "valeurs": par_dep(T["gares_departements"]["departements"], "part_sans_guichet", lambda o: not o["ile_de_france"] and o["gares"] >= 10)},
    ], {o["departement"]: o["nom"] for o in P["evolution"]["departements"]}


def mediane(v):
    v = sorted(v)
    m = len(v) // 2
    return v[m] if len(v) % 2 else round((v[m - 1] + v[m]) / 2, 2)


def main():
    inds, noms = indicateurs()
    deps = {c: {"departement": c, "nom": noms[c], "valeurs": {}, "defavorables": []} for c in sorted(noms)}
    resume = []
    for ind in inds:
        vals = ind["valeurs"]
        # Du plus défavorable au plus favorable ; à valeur égale, ordre des codes (sans effet sur le seuil)
        ordre = sorted(vals, key=lambda c: (-vals[c] if ind["sens"] == "haut" else vals[c], c))
        seuil = vals[ordre[math.ceil(len(ordre) / 5) - 1]]
        defav = [c for c in ordre if (vals[c] >= seuil if ind["sens"] == "haut" else vals[c] <= seuil)]
        for c, v in vals.items():
            deps[c]["valeurs"][ind["cle"]] = v
        for c in defav:
            deps[c]["defavorables"].append(ind["cle"])
        resume.append({"cle": ind["cle"], "theme": ind["theme"], "libelle": ind["libelle"], "unite": ind["unite"], "sens": ind["sens"],
                       "source": ind["source"], "nb_departements": len(vals), "seuil_cinquieme_defavorable": seuil,
                       "nb_defavorables": len(defav), "mediane": mediane(vals.values()),
                       "plus_defavorable": {"departement": ordre[0], "nom": noms[ordre[0]], "valeur": vals[ordre[0]]},
                       "plus_favorable": {"departement": ordre[-1], "nom": noms[ordre[-1]], "valeur": vals[ordre[-1]]}})
    liste = []
    for o in deps.values():
        o["nb_disponibles"] = len(o["valeurs"])
        o["nb_defavorables"] = len(o["defavorables"])
        liste.append(o)
    classes = [o for o in liste if o["nb_disponibles"] >= MIN_INDICATEURS]
    classement = sorted(classes, key=lambda o: (-o["nb_defavorables"], o["departement"]))
    chiffres = {
        "indicateurs": resume,
        "departements": liste,
        "classement_cumul": [{"departement": o["departement"], "nom": o["nom"], "nb_defavorables": o["nb_defavorables"],
                              "nb_disponibles": o["nb_disponibles"]} for o in classement if o["nb_defavorables"] >= 3],
        "repartition_cumul": {str(k): sum(1 for o in classes if o["nb_defavorables"] == k) for k in range(len(inds) + 1)},
        "nb_departements_classes": len(classes),
        "nb_au_moins_3": sum(1 for o in classes if o["nb_defavorables"] >= 3),
        "nb_au_moins_4": sum(1 for o in classes if o["nb_defavorables"] >= 4),
        "nb_aucun": sum(1 for o in classes if o["nb_defavorables"] == 0),
        "departements_non_classes": [o["nom"] for o in liste if o["nb_disponibles"] < MIN_INDICATEURS],
        "min_indicateurs": MIN_INDICATEURS,
        "definition": f"Croisement des fiches de chiffres vérifiées des cinq thèmes (santé, La Poste, éducation, logement, transports) : sept indicateurs départementaux repris sans recalcul (champ « source » = fiche/chemin). Pour chaque indicateur, les départements sont rangés du plus défavorable au plus favorable (sens « haut » : une valeur élevée est défavorable ; « bas » : une valeur basse) ; le « cinquième le plus défavorable » réunit les départements dont la valeur est au moins aussi défavorable que celle du département de rang ⌈N/5⌉ (N = départements disposant de l'indicateur ; ex æquo au seuil inclus). nb_defavorables = nombre d'indicateurs pour lesquels le département est dans ce cinquième. Classement des cumuls limité aux départements disposant d'au moins {MIN_INDICATEURS} indicateurs sur {len(inds)}. Comptage construit pour ce projet, non pondéré : il mesure des écarts entre départements (par construction, un cinquième des départements est « défavorable » pour chaque indicateur), pas un niveau absolu de service ; les indicateurs portent sur des périodes et des champs différents (voir chaque rapport) ; logement : France métropolitaine ; gares : hors Île-de-France, Corse et outre-mer, départements d'au moins 10 gares (même champ que le classement du rapport transports).",
    }
    # Tests de robustesse : quart le plus défavorable au lieu du cinquième, et rang moyen (0 = le plus défavorable, 1 = le plus favorable)
    rangs = defaultdict(list)
    quart = defaultdict(int)
    for ind in inds:
        vals = ind["valeurs"]
        ordre = sorted(vals, key=lambda c: (-vals[c] if ind["sens"] == "haut" else vals[c], c))
        seuil_q = vals[ordre[math.ceil(len(ordre) / 4) - 1]]
        for i, c in enumerate(ordre):
            # rang relatif ; ex æquo : même rang que le premier de leur groupe
            premier = next(j for j, x in enumerate(ordre) if vals[x] == vals[c])
            rangs[c].append(premier / (len(ordre) - 1))
            if vals[c] >= seuil_q if ind["sens"] == "haut" else vals[c] <= seuil_q:
                quart[c] += 1
    groupe = {o["departement"] for o in classes if o["nb_defavorables"] >= 3}
    q3 = {c for c in (o["departement"] for o in classes) if quart[c] >= 3}
    moyen = sorted(((sum(rangs[o["departement"]]) / len(rangs[o["departement"]]), o["departement"]) for o in classes))
    top_moyen = {c for _, c in moyen[:len(groupe)]}
    chiffres["robustesse"] = {
        "groupe_quintile": sorted(groupe),
        "quart_au_moins_3": sorted(q3), "quart_communs": len(groupe & q3),
        "rang_moyen_premiers": [{"departement": c, "nom": deps[c]["nom"], "rang_moyen": round(r, 3)} for r, c in moyen[:len(groupe)]],
        "rang_moyen_communs": len(groupe & top_moyen),
        "hors_groupe_rang_moyen": sorted(deps[c]["nom"] for c in top_moyen - groupe),
        "groupe_absents_rang_moyen": sorted(deps[c]["nom"] for c in groupe - top_moyen),
        "definition": "Test 1 : même comptage avec le quart (25 %) le plus défavorable au lieu du cinquième ; départements à au moins 3 indicateurs sur 7. Test 2 : rang moyen de chaque département sur les indicateurs disponibles (0 = le plus défavorable, 1 = le plus favorable ; ex æquo au même rang), et comparaison des N premiers avec le groupe de référence (N = taille du groupe).",
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "chiffres_territoires.json"), "w", encoding="utf-8") as f:
        json.dump(chiffres, f, ensure_ascii=False, indent=1)
    print(f"{len(liste)} départements, {len(inds)} indicateurs -> {OUT}/chiffres_territoires.json")


if __name__ == "__main__":
    main()
