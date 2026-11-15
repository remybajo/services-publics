"""Calcule les chiffres du rapport sur le service public postal à partir de donnees_propres/poste/ (EDR-005).

Produit donnees_propres/poste/chiffres_poste.json : séries des graphiques + chiffres clés, chacun avec sa définition.
Usage : python3 calculer_chiffres_poste.py
"""
import csv
import decimal
import json
import os
import statistics
from collections import defaultdict

DIR = "donnees_propres/poste"
TYPES = ["Bureau de poste", "Agence postale", "Relais poste"]
CLASSES_HEURES = [("Moins de 10 h", 0, 10), ("10 à 20 h", 10, 20), ("20 à 35 h", 20, 35), ("35 h et plus", 35, None)]


def arrondi(v, k):
    """Arrondi à la française (0,25 -> 0,3), et non au chiffre pair comme round()."""
    return float(decimal.Decimal(str(v)).quantize(decimal.Decimal(1).scaleb(-k), rounding=decimal.ROUND_HALF_UP))


def lire(nom):
    with open(os.path.join(DIR, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def evol(a, b):
    return {"debut": a, "fin": b, "ecart": b - a, "pct": round(100 * (b - a) / a, 1)}


def evolution():
    r = lire("poste_reseau_evolution_propre.csv")
    v = defaultdict(dict)
    for x in r:
        if x["nombre"] != "":
            v[(x["niveau"], x["code_geo"], x["type_point"])][x["annee"]] = float(x["nombre"])
    annees = sorted({x["annee"] for x in r})
    a0, a1 = annees[0], annees[-1]
    serie = [{"annee": a, **{t: round(v[("FRANCE", "F", t)][a]) for t in TYPES}} for a in annees]
    for s in serie:
        s["total"] = sum(s[t] for t in TYPES)
        s["part_bureaux"] = round(100 * s["Bureau de poste"] / s["total"], 1)
    noms = {x["departement"]: x["nom_departement"] for x in lire("poste_points_contact_propre.csv")}
    deps = []
    for code in sorted({c for (niv, c, t) in v if niv == "DEP"}):
        b = v.get(("DEP", code, "Bureau de poste"), {})
        ag = v.get(("DEP", code, "Agence postale"), {})
        re_ = v.get(("DEP", code, "Relais poste"), {})
        if a0 not in b or a1 not in b:
            continue
        # Part des bureaux non calculable si une composante manque à la source (agences à Paris) : « non disponible »
        complet0 = a0 in ag and a0 in re_
        complet1 = a1 in ag and a1 in re_
        tot1 = b[a1] + ag.get(a1, 0) + re_.get(a1, 0)
        tot0 = b[a0] + ag.get(a0, 0) + re_.get(a0, 0)
        deps.append({"departement": code, "nom": noms.get(code, code), "bureaux_debut": round(b[a0]), "bureaux_fin": round(b[a1]),
                     "pct_bureaux": round(100 * (b[a1] - b[a0]) / b[a0], 1) if b[a0] else None,
                     "agences_fin": round(ag[a1]) if a1 in ag else None, "relais_fin": round(re_[a1]) if a1 in re_ else None,
                     "part_bureaux_debut": round(100 * b[a0] / tot0, 1) if tot0 and complet0 else None,
                     "part_bureaux_fin": round(100 * b[a1] / tot1, 1) if tot1 and complet1 else None})
    deps.sort(key=lambda o: (o["pct_bureaux"] if o["pct_bureaux"] is not None else 0))
    return {
        "serie": serie,
        "evol": {t: evol(serie[0][t], serie[-1][t]) for t in TYPES},
        "total": evol(serie[0]["total"], serie[-1]["total"]),
        "departements": deps,
        "deps_minorite_bureaux": sum(1 for o in deps if o["part_bureaux_fin"] is not None and o["part_bureaux_fin"] < 50),
        "deps_minorite_bureaux_debut": sum(1 for o in deps if o["part_bureaux_debut"] is not None and o["part_bureaux_debut"] < 50),
        "periode": [a0, a1],
        "definition": "Insee, Base permanente des équipements, jeu d'évolution (2015, 2020, 2025, au 1er janvier, géographie au 1er janvier 2026) : bureaux de poste (A206), relais poste (A207), agences postales (A208). Agences postales communales et intercommunales confondues ; total = bureaux + agences + relais (points partenaires exclus). Observation absente (agences postales à Paris) : non disponible, et part des bureaux non calculée pour ce département. Pour 2016-2021, l'Insee signalait une évolution atypique des relais poste dans six départements, dont trois avec rupture de série (« Précautions d'utilisation », BPE 2016-2021) ; à Paris, les relais passent de 1 en 2015 à 53 en 2020.",
        "deps_ex_aequo_note": "Classement des baisses : départements à pourcentage égal ex æquo.",
    }


def reseau_actuel():
    r = lire("poste_points_contact_propre.csv")
    n, n101 = defaultdict(int), defaultdict(int)
    for x in r:
        n[x["type_point"]] += 1
        if x["dans_101_departements"] == "oui":
            n101[x["type_point"]] += 1
    return {
        "par_type": dict(sorted(n.items(), key=lambda kv: -kv[1])),
        "par_type_101_departements": dict(sorted(n101.items(), key=lambda kv: -kv[1])),
        "total": len(r),
        "hors_101_departements": sum(1 for x in r if x["dans_101_departements"] == "non"),
        "definition": "La Poste, liste des points de contact (mise à jour du 08/10/2026) : bureaux de poste, agences postales communales et intercommunales, relais poste, points partenaires. 13 points de type ambigu (« Agence postale ou Relais poste »). Le total inclut 24 points hors des 101 départements (Andorre, Monaco, Saint-Pierre-et-Miquelon, Saint-Barthélemy, Saint-Martin, codes 99) ; par_type_101_departements les exclut. Photographie non comparable en série avec l'Insee (dates et définitions différentes).",
    }


def horaires():
    r = [x for x in lire("poste_horaires_propre.csv") if x["heures_par_semaine"] != ""]
    liste = defaultdict(set)
    for x in lire("poste_points_contact_propre.csv"):
        liste[x["type_point"]].add(x["identifiant"])
    res = {}
    for t in TYPES:
        h = [float(x["heures_par_semaine"]) for x in r if x["type_point"] == t]
        samedi = [int(x["samedis_ouverts"]) for x in r if x["type_point"] == t]
        res[t] = {"nombre": len(h), "mediane": round(statistics.median(h), 2),
                  "moins_de_20h": sum(1 for v in h if v < 20), "part_moins_de_20h": round(100 * sum(1 for v in h if v < 20) / len(h), 1),
                  "classes": {lib: round(100 * sum(1 for v in h if v >= b and (f is None or v < f)) / len(h), 1) for lib, b, f in CLASSES_HEURES},
                  "part_ouverts_samedi": round(100 * sum(1 for s in samedi if s > 0) / len(samedi), 1),
                  "points_de_la_liste_couverts": sum(1 for x in r if x["type_point"] == t and x["identifiant"] in liste[t]),
                  "points_de_la_liste": len(liste[t]),
                  "mediane_zero_heure": sum(1 for v in h if v == 0)}
        res[t]["couverture_pct"] = round(100 * res[t]["points_de_la_liste_couverts"] / res[t]["points_de_la_liste"], 1)
    return {
        "par_type": res,
        "classes": [lib for lib, _, _ in CLASSES_HEURES],
        "definition": "La Poste, calendrier d'ouverture des points de contact (téléchargé le 21/10/2026, du 19/10/2026 au 18/01/2027) : heures d'ouverture au public par semaine, médiane sur 13 semaines complètes (jours fériés et fermetures compris, ce qui réduit l'effet des congés ponctuels). Plages postales uniquement (hors horaires de La Banque Postale). « Ouvert le samedi » = au moins un samedi ouvert sur les 13. Jours en double dans la source comptés une seule fois. La classe « moins de 10 h » comprend les points dont la médiane est de 0 h (fermés la plupart des semaines de la période). Horaires prévus, pas constatés.",
    }


def boites():
    tout = lire("poste_boites_propre.csv")
    r = [x for x in tout if x["heure_limite_semaine"]]
    n = len(r)
    avant_10 = sum(1 for x in r if x["heure_limite_semaine"] < "10:00")
    avant_12 = sum(1 for x in r if x["heure_limite_semaine"] < "12:00")
    return {
        "nombre": n,
        "exclues_sans_heure": len(tout) - n,
        "avant_10h": avant_10, "part_avant_10h": round(100 * avant_10 / n, 1),
        "avant_12h": avant_12, "part_avant_12h": round(100 * avant_12 / n, 1),
        "definition": "La Poste, liste des boîtes aux lettres de rue (France métropolitaine et outre-mer, mise à jour du 08/09/2026) : heure limite de dépôt en semaine, telle que publiée par La Poste (boîtes sans heure exclues). Photographie à une date : la source ne dit pas si ces horaires ont changé.",
    }


def rapport():
    r = lire("poste_rapport_integre_propre.csv")
    retenus = {}
    for x in r:
        if x["indicateur"].startswith("Nombre de facteurs embauchés en CDI"):
            retenus["facteurs_cdi"] = x["valeur_nombre"]
        if x["indicateur"].startswith("Diminution du nombre de facteurs embauchés en CDI"):
            retenus["facteurs_cdi_baisse_pct"] = x["valeur_pourcentage"] or x["valeur_nombre"]
    return {**{k: float(v) for k, v in retenus.items()},
            "definition": "La Poste, rapport intégré 2025 (données publiées par l'entreprise, non auditées par le projet) : nombre de facteurs embauchés en CDI en 2025 (embauches de l'année, pas l'effectif) et baisse par rapport à 2024 (taux arrondi par La Poste)."}


POPULATION = "donnees_propres/sante/sante_apl_propre.csv"  # population totale Insee 2022 par commune (fichier APL 2024, DREES)


def departements_2026():
    pop = {x["code_commune"]: float(x["population"]) for x in csv.DictReader(open(POPULATION, encoding="utf-8-sig"))
           if x["annee"] == "2024" and x["population"]}
    points = [x for x in lire("poste_points_contact_propre.csv") if x["dans_101_departements"] == "oui"]
    horaires = {x["identifiant"]: float(x["heures_par_semaine"]) for x in lire("poste_horaires_propre.csv") if x["heures_par_semaine"] != ""}
    boites = [x for x in lire("poste_boites_propre.csv") if x["heure_limite_semaine"]]
    noms = {x["departement"]: x["nom_departement"] for x in points}
    communes_bureau = {x["code_insee"] for x in points if x["type_point"] == "Bureau de poste"}
    communes_point = {x["code_insee"] for x in points}
    communes_point_hors_partenaires = {x["code_insee"] for x in points if x["type_point"] != "Point partenaire"}
    communes_boites = {x["code_insee"] for x in boites}
    d = defaultdict(lambda: defaultdict(float))
    h = defaultdict(lambda: defaultdict(list))
    for x in points:
        d[x["departement"]][x["type_point"]] += 1
        if x["identifiant"] in horaires:
            h[x["departement"]][x["type_point"]].append(horaires[x["identifiant"]])
    for x in boites:
        d[x["departement"]]["boites"] += 1
        d[x["departement"]]["boites_avant_10h"] += x["heure_limite_semaine"] < "10:00"
    for code, p_ in pop.items():
        dep = code[:3] if code.startswith("97") else code[:2]
        d[dep]["population"] += p_
        if code not in communes_bureau:
            d[dep]["pop_sans_bureau"] += p_
            d[dep]["communes_sans_bureau"] += 1
        if code not in communes_point:
            d[dep]["pop_sans_point"] += p_
        d[dep]["communes"] += 1
    out = []
    for dep in sorted(noms):
        o = d[dep]
        tous_h = [v for t in TYPES for v in h[dep][t]]
        out.append({
            "departement": dep, "nom": noms[dep],
            "bureaux": int(o["Bureau de poste"]), "agences": int(o["Agence postale"]), "relais": int(o["Relais poste"]),
            "mediane_heures_bureaux": arrondi(statistics.median(h[dep]["Bureau de poste"]), 1) if h[dep]["Bureau de poste"] else None,
            "part_points_moins_20h": round(100 * sum(1 for v in tous_h if v < 20) / len(tous_h), 1) if tous_h else None,
            "part_boites_avant_10h": round(100 * o["boites_avant_10h"] / o["boites"], 1) if o["boites"] else None,
            "population": round(o["population"]) if o["population"] else None,
            "part_pop_sans_bureau": round(100 * o["pop_sans_bureau"] / o["population"], 1) if o["population"] else None,
            "communes_sans_bureau": int(o["communes_sans_bureau"]) if o["population"] else None,
            "communes": int(o["communes"]) if o["population"] else None,
        })
    pop_tot = sum(pop.values())
    sans_bureau = sum(v for c, v in pop.items() if c not in communes_bureau)
    sans_point = sum(v for c, v in pop.items() if c not in communes_point)
    sans_point_hp = sum(v for c, v in pop.items() if c not in communes_point_hors_partenaires)
    inconnues = [c for c in pop if c not in communes_point and c not in communes_boites]
    return {
        "departements": out,
        "population_totale": round(pop_tot),
        "population_sans_bureau": round(sans_bureau), "part_population_sans_bureau": round(100 * sans_bureau / pop_tot, 1),
        "communes_sans_bureau": sum(1 for c in pop if c not in communes_bureau), "communes": len(pop),
        "population_sans_point": round(sans_point), "part_population_sans_point": round(100 * sans_point / pop_tot, 1),
        "population_sans_bureau_agence_relais": round(sans_point_hp), "part_population_sans_bureau_agence_relais": round(100 * sans_point_hp / pop_tot, 1),
        "communes_sans_point_ni_boite": len(inconnues), "population_communes_sans_point_ni_boite": round(sum(pop[c] for c in inconnues)),
        "communes_non_rapprochees": sorted(c for c in communes_point if c not in pop),
        "definition": "Points de contact La Poste (08/10/2026, 101 départements, Monaco exclu, code d'Orée d'Anjou corrigé) rapprochés des communes et arrondissements municipaux (34 890, hors Mayotte) et de leur « population totale 2022 » (fichier APL 2024 de la DREES, géographie de ce fichier non documentée). « Sans aucun point » compte les points partenaires comme des points ; variante sans eux : population_sans_bureau_agence_relais. Des communes n'ont ni point ni boîte La Poste (codes possiblement obsolètes après fusion) : voir communes_sans_point_ni_boite. L'unité « commune » est très hétérogène (de quelques dizaines d'habitants à des communes nouvelles de 20 000). « Sans bureau de poste » : aucun bureau dans la commune, même si une agence, un relais ou un bureau voisin existe ; ne mesure ni la distance ni le temps d'accès. Heures et boîtes : mêmes définitions que les blocs horaires et boites.",
    }


def main():
    chiffres = {"evolution": evolution(), "reseau_actuel": reseau_actuel(), "horaires": horaires(), "boites": boites(),
                "rapport_integre": rapport(), "departements_2026": departements_2026()}
    with open(os.path.join(DIR, "chiffres_poste.json"), "w", encoding="utf-8") as f:
        json.dump(chiffres, f, ensure_ascii=False, indent=1)
    print(f"{len(chiffres)} blocs -> {DIR}/chiffres_poste.json")


if __name__ == "__main__":
    main()
