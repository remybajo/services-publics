"""Calcule les chiffres du rapport santé à partir de donnees_propres/sante/ (EDR-005 : tout chiffre est rejouable).

Produit donnees_propres/sante/chiffres_sante.json : séries des graphiques + chiffres clés, chacun avec sa définition.
Usage : python3 calculer_chiffres_sante.py
"""
import csv
import json
import os
import re
from collections import defaultdict

DIR = "donnees_propres/sante"
SEUIL_APL = 2.5  # commune sous-dotée si APL <= 2,5 consultations/an/habitant (Insee Flash Centre-Val de Loire n° 101, déc. 2025)


def lire(nom):
    with open(os.path.join(DIR, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def evol(a, b):
    return {"debut": a, "fin": b, "ecart": b - a, "pct": round(100 * (b - a) / a, 1)}


def lits():
    r = lire("sante_lits_propre.csv")
    serie = [{"annee": x["annee"], "lits": int(x["lits_hospitalisation_complete"]),
              "places": int(x["places_hospitalisation_partielle"])} for x in r]
    return {
        "serie": serie,
        "lits": evol(serie[0]["lits"], serie[-1]["lits"]),
        "places": evol(serie[0]["places"], serie[-1]["places"]),
        "periode": [serie[0]["annee"], serie[-1]["annee"]],
        "definition": "Lits d'hospitalisation complète et places d'hospitalisation partielle au 31 décembre (jeu data.drees « Graphique 1 – Évolution du nombre de lits et de places au 31 décembre, depuis fin 2013 », sans description ni licence renseignées). Pas de distinction public / privé.",
    }


def effectifs():
    t = defaultdict(float)
    prof = defaultdict(float)
    for x in lire("sante_effectifs_propre.csv"):
        if x["niveau"] != "agrege" or not x["effectifs"]:
            continue
        t[(x["annee"], x["secteur"])] += float(x["effectifs"])
        prof[(x["annee"], x["secteur"], x["profession"])] += float(x["effectifs"])
    annees = sorted({a for a, _ in t})
    serie = [{"annee": a, "public": round(t[(a, "Public")]), "prive": round(t[(a, "Privé")])} for a in annees]
    a0, a1 = annees[0], annees[-1]
    metiers = {}
    for p in ["1 - Médecins et assimilés", "4 - Infirmiers", "5 - Aides-soignants"]:
        metiers[p] = {s: evol(round(prof[(a0, s, p)]), round(prof[(a1, s, p)])) for s in ("Public", "Privé")}
    part_public = {a: round(100 * t[(a, "Public")] / (t[(a, "Public")] + t[(a, "Privé")]), 1) for a in (a0, a1)}
    return {
        "serie": serie,
        "public": evol(round(t[(a0, "Public")]), round(t[(a1, "Public")])),
        "prive": evol(round(t[(a0, "Privé")]), round(t[(a1, "Privé")])),
        "part_public": part_public,
        "metiers": metiers,
        "periode": [a0, a1],
        "definition": "Salariés en personnes physiques (pas en équivalents temps plein) rémunérés au 31 décembre par les établissements du secteur hospitalier (APE 8610Z), France métropolitaine et DROM y compris Mayotte, service de santé des armées et internes inclus ; somme des 7 catégories agrégées. Privé = lucratif + non lucratif (dont Espic). Séries par métier en partie rétropolées par la DREES.",
    }


def soins_critiques():
    t = defaultdict(int)
    for x in lire("sante_soins_critiques_propre.csv"):
        if x["code_geo"] != "00" or x["territoire"] != "FR":
            continue
        t[(x["annee"], x["statut"], x["code_unite"])] += int(x["nb_lits"])
    annees = sorted({k[0] for k in t})
    statuts = ["Public", "Privé non lucratif", "Privé lucratif"]
    rea = [{"annee": a, **{s: t[(a, s, "REAADU")] for s in statuts}} for a in annees]
    total = {a: sum(v for k, v in t.items() if k[0] == a) for a in annees}
    rea_tot = {a: sum(t[(a, s, "REAADU")] for s in statuts) for a in annees}
    part_public_rea = {a: round(100 * t[(a, "Public", "REAADU")] / rea_tot[a], 1) for a in annees}
    unites = {a: {u: sum(t[(a, s, u)] for s in statuts) for u in ("AUTSI", "SURVADU")} for a in ("2023", "2024")}
    return {
        "rea_serie": rea,
        "rea_total": {a: rea_tot[a] for a in annees},
        "rea_2019_2024": evol(rea_tot["2019"], rea_tot["2024"]),
        "rea_pic_2020": rea_tot["2020"],
        "part_public_rea": part_public_rea,
        "total_soins_critiques": total,
        "rupture_2024": unites,
        "annees": annees,
        "definition": "Lits de réanimation adulte au 31 décembre, France entière (code_geo 00, FR), par statut d'établissement. Années disponibles : 2013, puis 2019 à 2024 (aucune donnée 2014-2018). total_soins_critiques = 7 unités (réanimation, soins intensifs, surveillance continue, adulte et pédiatrique), non comparable entre 2023 et 2024 (reclassement observé : surveillance continue en baisse, autres soins intensifs en hausse). Libellés des unités reconstitués (non documentés dans la source). Licence non renseignée.",
    }


def maternites():
    n = defaultdict(int)
    lits_obs = defaultdict(int)
    for x in lire("sante_maternites_propre.csv"):
        n[(x["annee"], x["statut"])] += 1
        if x["lits_obstetrique"]:
            lits_obs[x["annee"]] += int(x["lits_obstetrique"])
    annees = sorted({a for a, _ in n})
    statuts = ["Public", "Privé non lucratif", "Privé lucratif"]
    serie = [{"annee": a, **{s: n[(a, s)] for s in statuts}, "total": sum(n[(a, s)] for s in statuts)} for a in annees]
    a0, a1 = annees[0], annees[-1]
    return {
        "serie": serie,
        "total": evol(serie[0]["total"], serie[-1]["total"]),
        "par_statut": {s: evol(n[(a0, s)], n[(a1, s)]) for s in statuts},
        "lits_obstetrique": evol(lits_obs[a0], lits_obs[a1]),
        "part_public": {a: round(100 * n[(a, "Public")] / sum(n[(a, s)] for s in statuts), 1) for a in (a0, a1)},
        "periode": [a0, a1],
        "definition": "Maternités ayant au moins un lit et un type au 31 décembre et au moins un accouchement dans l'année (une ligne sans type, CH de Dinan en 2021, est comptée telle que la source la fournit). Nombre de sites : ne mesure ni les distances ni les temps d'accès.",
    }


def apl():
    pop = defaultdict(float)
    sous = defaultdict(float)
    sous65 = defaultdict(float)
    communes_sous = defaultdict(int)
    somme_apl = defaultdict(float)
    somme_apl65 = defaultdict(float)
    pop_std = defaultdict(float)
    for x in lire("sante_apl_propre.csv"):
        if not x["apl"] or not x["population"]:
            continue
        a, p = x["annee"], float(x["population"])
        # APL moyen : pondéré par la population standardisée (note DREES du fichier)
        if x["population_standardisee"] and x["apl_medecins_65_ans_et_moins"]:
            ps = float(x["population_standardisee"])
            pop_std[a] += ps
            somme_apl[a] += float(x["apl"]) * ps
            somme_apl65[a] += float(x["apl_medecins_65_ans_et_moins"]) * ps
        pop[a] += p
        if float(x["apl"]) <= SEUIL_APL:
            sous[a] += p
            communes_sous[a] += 1
        if x["apl_medecins_65_ans_et_moins"] and float(x["apl_medecins_65_ans_et_moins"]) <= SEUIL_APL:
            sous65[a] += p
    annees = sorted(pop)
    serie = [{"annee": a, "population_sous_dense": round(sous[a]), "part": round(100 * sous[a] / pop[a], 1),
              "part_medecins_65_ans_et_moins": round(100 * sous65[a] / pop[a], 1),
              "communes_sous_denses": communes_sous[a],
              "apl_moyen": round(somme_apl[a] / pop_std[a], 2),
              "apl_moyen_medecins_65_ans_et_moins": round(somme_apl65[a] / pop_std[a], 2)} for a in annees]
    return {
        "serie": serie,
        "seuil": SEUIL_APL,
        "evolution_population": evol(round(sous[annees[0]]), round(sous[annees[-1]])),
        "definition": f"Population (non standardisée, comme le recommande la DREES) vivant dans une commune dont l'APL aux médecins généralistes est inférieur ou égal à {str(SEUIL_APL).replace('.', ',')} consultations par an et par habitant (définition de la commune sous-dotée : Insee Flash Centre-Val de Loire n° 101, décembre 2025). Soins de ville (libéraux et centres de santé), pas l'hôpital. France hors Mayotte. Populations Insee décalées de deux ans par rapport au millésime ; méthode non comparable avec les millésimes antérieurs à 2022.",
    }


def urgences():
    r = lire("sante_urgences_propre.csv")
    t = defaultdict(float)
    par_dep = defaultdict(dict)
    for x in r:
        if x["anomalies"]:  # périmètre constant : départements couverts sur toute la période
            continue
        t[x["annee"]] += float(x["passages"])
        par_dep[x["departement"]][x["annee"]] = float(x["passages"])
    t = {a: round(v) for a, v in t.items()}  # arrondi de la somme, pas de chaque département
    annees = sorted(t)
    a0, a1 = annees[0], annees[-1]
    hausse = sum(1 for d in par_dep.values() if d[a1] > d[a0])
    return {
        "serie": [{"annee": a, "passages": t[a]} for a in annees],
        "total": evol(t[a0], t[a1]),
        "depuis_2019": evol(t["2019"], t[a1]),
        "nb_departements": len(par_dep),
        "departements_en_hausse": hausse,
        "exclus": sorted({x["libelle_departement"] for x in r if x["anomalies"]}),
        "periode": [a0, a1],
        "definition": "Somme des passages journaliers aux urgences : séries DREES estimées (RPU calés sur les totaux SAE, complétés par le PMSI), pas des comptages de patients. Périmètre constant de 93 départements couverts de 2017 à 2023 : hors Martinique, Lozère et Mayotte (absentes de la source) et hors 5 départements à couverture partielle.",
    }


# --- Détails nationaux et territoriaux ------------------------------------------
UNITES = ["REAADU", "REAENF", "USIC", "SIUNV", "AUTSI", "SURVADU", "SURVENF"]
CLASSES_APL = [("≤ 2,5", None, 2.5), ("2,5 à 3,5", 2.5, 3.5), ("3,5 à 4,5", 3.5, 4.5), ("> 4,5", 4.5, None)]
CLASSES_ACC = [("< 500", 0, 500), ("500 à 999", 500, 1000), ("1 000 à 1 999", 1000, 2000),
               ("2 000 à 2 999", 2000, 3000), ("3 000 et plus", 3000, None)]


def dans(v, bas, haut):
    """bas exclu, haut inclus (classes APL) ; None = pas de borne."""
    return (bas is None or v > bas) and (haut is None or v <= haut)


def referentiel():
    """Libellés des départements (fichier soins critiques) et population totale Insee 2022 (fichier APL 2024)."""
    noms = {}
    for x in lire("sante_soins_critiques_propre.csv"):
        if x["code_geo"] != "00":
            noms[x["code_geo"]] = x["territoire"]
    pop = defaultdict(float)
    for x in lire("sante_apl_propre.csv"):
        if x["annee"] == "2024" and x["population"]:
            pop[x["departement"]] += float(x["population"])
    return noms, {d: round(v) for d, v in pop.items()}


NOMS, POP = None, None


def critiques_detail():
    t = defaultdict(int)
    dep = defaultdict(int)
    for x in lire("sante_soins_critiques_propre.csv"):
        if x["code_geo"] == "00" and x["territoire"] == "FR":
            t[(x["annee"], x["code_unite"])] += int(x["nb_lits"])
        elif x["code_geo"] != "00" and x["annee"] == "2024":
            dep[(x["code_geo"], x["code_unite"])] += int(x["nb_lits"])
    annees = sorted({a for a, _ in t})
    unites = [{"annee": a, **{u: t[(a, u)] for u in UNITES}} for a in annees]
    taux = []
    for d in NOMS:
        if d in POP:
            taux.append({"departement": d, "nom": NOMS[d], "lits": dep[(d, "REAADU")],
                         "pour_100k": round(100000 * dep[(d, "REAADU")] / POP[d], 1)})
    taux.sort(key=lambda o: o["pour_100k"])
    nat = round(100000 * t[("2024", "REAADU")] / sum(POP.values()), 1)
    sans_ped = sorted(NOMS[d] for d in NOMS if dep[(d, "REAENF")] == 0)
    return {
        "unites": unites,
        "rea_pour_100k_dep": taux,
        "rea_pour_100k_national": nat,
        "rea_pour_100k_ecart": [taux[0]["pour_100k"], taux[-1]["pour_100k"]],
        "deps_sans_rea_pediatrique": len(sans_ped),
        "nb_departements": len(NOMS),
        "definition": "Lits de soins critiques au 31 décembre par unité (France entière) ; taux de réanimation adulte 2024 pour 100 000 habitants par département, population totale Insee 2022 (fichier APL 2024), hors Mayotte (pas de population). Les patients sont souvent pris en charge hors de leur département : le taux mesure l'implantation des lits, pas l'accès réel.",
    }


def effectifs_detail():
    t = defaultdict(float)
    for x in lire("sante_effectifs_propre.csv"):
        if x["niveau"] == "agrege" and x["effectifs"]:
            t[(x["annee"], x["secteur"], x["profession"])] += float(x["effectifs"])
    annees = sorted({k[0] for k in t})
    metiers = sorted({k[2] for k in t})
    a0, a1 = annees[0], annees[-1]
    indice = {p: [round(100 * t[(a, "Public", p)] / t[(a0, "Public", p)], 1) for a in annees] for p in metiers}
    part_public = [{"profession": p, "public": round(t[(a1, "Public", p)]), "prive": round(t[(a1, "Privé", p)]),
                    "part_public": round(100 * t[(a1, "Public", p)] / (t[(a1, "Public", p)] + t[(a1, "Privé", p)]), 1)}
                   for p in metiers]
    return {
        "annees": annees,
        "indice_public": indice,
        "evol_public": {p: evol(round(t[(a0, "Public", p)]), round(t[(a1, "Public", p)])) for p in metiers},
        "part_public": sorted(part_public, key=lambda o: -o["part_public"]),
        "definition": "Salariés en personnes physiques au 31 décembre, par catégorie agrégée (internes en catégorie 2, distincts des médecins) ; indice base 100 en 2003 pour le public.",
    }


def maternites_detail():
    r = lire("sante_maternites_propre.csv")
    annees = sorted({x["annee"] for x in r})
    a0, a1 = annees[0], annees[-1]
    types = [{"annee": a, **{ty: sum(1 for x in r if x["annee"] == a and x["type"] == ty) for ty in ("1", "2a", "2b", "3")}}
             for a in annees]
    taille = {}
    for a in (a0, a1):
        acc = [int(x["accouchements"]) for x in r if x["annee"] == a and x["accouchements"]]
        taille[a] = {lib: sum(1 for v in acc if v >= b and (h is None or v < h)) for lib, b, h in CLASSES_ACC}
    par_dep = {a: defaultdict(int) for a in (a0, a1)}
    for x in r:
        if x["annee"] in par_dep:
            par_dep[x["annee"]][x["departement"]] += 1
    deps = sorted(set(par_dep[a0]) | set(par_dep[a1]) | set(NOMS))
    pertes = sorted(({"departement": d, "nom": NOMS.get(d, d), "debut": par_dep[a0][d], "fin": par_dep[a1][d],
                      "ecart": par_dep[a1][d] - par_dep[a0][d]} for d in deps), key=lambda o: (o["ecart"], o["nom"]))
    return {
        "types": types,
        "types_evol": {ty: evol(types[0][ty], types[-1][ty]) for ty in ("1", "2a", "2b", "3")},
        "taille": taille,
        "par_departement": pertes,
        "deps_en_baisse": sum(1 for o in pertes if o["ecart"] < 0),
        "deps_une_seule": {a: sorted(NOMS.get(d, d) for d in deps if par_dep[a][d] == 1) for a in (a0, a1)},
        "deps_aucune": {a: sorted(NOMS.get(d, d) for d in NOMS if par_dep[a][d] == 0) for a in (a0, a1)},
        "periode": [a0, a1],
        "definition": "Type 1 : obstétrique seule ; 2a : + néonatologie ; 2b : + soins intensifs néonatals ; 3 : + réanimation néonatale (définitions DREES). Taille : accouchements de l'année des maternités présentes au 31 décembre (le fichier ne permet pas de compter le total des accouchements).",
    }


def apl_detail():
    pop = defaultdict(float)
    classes = defaultdict(float)
    dep_pop = defaultdict(float)
    dep_sous = defaultdict(float)
    for x in lire("sante_apl_propre.csv"):
        if not x["apl"] or not x["population"]:
            continue
        a, p, v = x["annee"], float(x["population"]), float(x["apl"])
        pop[a] += p
        for lib, b, h in CLASSES_APL:
            if dans(v, b, h):
                classes[(a, lib)] += p
        dep_pop[(a, x["departement"])] += p
        if v <= SEUIL_APL:
            dep_sous[(a, x["departement"])] += p
    annees = sorted(pop)
    a0, a1 = annees[0], annees[-1]
    repartition = [{"annee": a, **{lib: round(100 * classes[(a, lib)] / pop[a], 1) for lib, _, _ in CLASSES_APL}} for a in annees]
    deps = []
    for d in sorted({k[1] for k in dep_pop}):
        p0, p1 = 100 * dep_sous[(a0, d)] / dep_pop[(a0, d)], 100 * dep_sous[(a1, d)] / dep_pop[(a1, d)]
        deps.append({"departement": d, "nom": NOMS.get(d, d), "part_debut": round(p0, 1), "part_fin": round(p1, 1),
                     "ecart_points": round(p1 - p0, 1), "en_hausse": p1 > p0})  # comparaison avant arrondi
    return {
        "repartition": repartition,
        "classes": [lib for lib, _, _ in CLASSES_APL],
        "departements": deps,
        "deps_majorite_sous_dotee": [o["nom"] for o in deps if o["part_fin"] > 50],
        "deps_en_hausse": sum(1 for o in deps if o["en_hausse"]),
        "periode": [a0, a1],
        "definition": "Répartition de la population (non standardisée) selon l'APL aux médecins généralistes de sa commune ; classes au-dessus de 2,5 choisies pour la lecture (non officielles). Part sous-dotée par département : APL inférieur ou égal à 2,5.",
    }


def urgences_detail():
    mois = defaultdict(float)
    jours = defaultdict(int)
    for x in lire("sante_urgences_mensuel_propre.csv"):
        if x["anomalies"]:
            continue
        mois[x["mois"]] += float(x["passages"])
        jours[x["mois"]] = max(jours[x["mois"]], int(x["nb_jours"]))
    saison = {a: [round(mois[f"{a}-{m:02d}"] / jours[f"{a}-{m:02d}"]) for m in range(1, 13)] for a in ("2019", "2023")}
    an = defaultdict(dict)
    noms = {}
    for x in lire("sante_urgences_propre.csv"):
        if "annee_incomplete" not in x["anomalies"]:
            an[x["departement"]][x["annee"]] = float(x["passages"])
            noms[x["departement"]] = x["libelle_departement"]
    deps = []
    for d, v in an.items():
        if "2019" in v and "2023" in v:
            o = {"departement": d, "nom": noms[d], "pct_2019_2023": round(100 * (v["2023"] - v["2019"]) / v["2019"], 1)}
            if d in POP:
                o["pour_1000_hab_2023"] = round(1000 * v["2023"] / POP[d])
            deps.append(o)
    deps.sort(key=lambda o: o["pct_2019_2023"])
    taux = sorted((o for o in deps if "pour_1000_hab_2023" in o), key=lambda o: o["pour_1000_hab_2023"])
    return {
        "saison_moyenne_journaliere": saison,
        "departements": deps,
        "nb_departements": len(deps),
        "deps_en_baisse_depuis_2019": sum(1 for o in deps if o["pct_2019_2023"] < 0),
        "pour_1000_ecart": [taux[0]["pour_1000_hab_2023"], taux[-1]["pour_1000_hab_2023"]],
        "definition": "Saisonnalité : moyenne des passages par jour, chaque mois, sur les 93 départements couverts toute la période. Par département : évolution 2019-2023 (départements couverts ces deux années) et passages 2023 pour 1 000 habitants (population Insee 2022) ; un passage peut concerner un non-résident.",
    }



# --- Sources ajoutées : base ARES (2013-2021), démographie des médecins (RPPS), comptes de la santé ---
def ares_serie(lignes, indicateur, categorie, region="France entière"):
    return {x["annee"]: float(x["valeur"]) for x in lignes
            if x["indicateur"] == indicateur and x["categorie"] == categorie and x["region"] == region and x["valeur"]}


def ares_bloc():
    r = lire("sante_ares_propre.csv")
    annees = sorted({x["annee"] for x in r})
    a0, a1 = annees[0], annees[-1]

    def bloc(ind, cats):
        series = {c: ares_serie(r, ind, c) for c in cats}
        return {"serie": [{"annee": a, **{c: round(series[c][a]) for c in cats}} for a in annees],
                "evol": {c: evol(round(series[c][a0]), round(series[c][a1])) for c in cats}}

    return {
        "etablissements": bloc("etablissements_par_statut", ["Public", "Privé non lucratif", "Privé lucratif", "Total"]),
        "urgences_autorisees": bloc("etablissements_avec_urgences", ["Établissements avec urgences autorisées", "dont urgences pédiatriques autorisées"]),
        "lits_mco": bloc("lits_mco", ["Médecine", "Chirurgie", "Obstétrique", "Total MCO"]),
        "psychiatrie": {"lits_temps_plein": bloc("lits_psychiatrie_temps_plein", ["Total"]),
                        "places_jour": bloc("places_psychiatrie_jour", ["Total"])},
        "had": bloc("places_had", ["Total"]),
        "usld": bloc("lits_usld", ["Total"]),
        "ssr": bloc("lits_ssr", ["Adulte", "Enfant", "Total"]),
        "passages_urgences": bloc("passages_urgences", ["Urgences générales", "Urgences pédiatrique", "Total"]),
        "periode": [a0, a1],
        "definition": "Base ARES (DREES), agrégats régionaux issus de la SAE 2013-2021, ligne « France entière » (y compris Saint-Martin et Saint-Barthélemy). Établissement = entité géographique. Lits d'hospitalisation complète au 31 décembre ; places de psychiatrie de jour et d'hospitalisation à domicile (HAD : patients pouvant être pris en charge simultanément).",
    }


def medecins_bloc():
    eff = lire("sante_medecins_effectifs_propre.csv")
    den = lire("sante_medecins_densites_propre.csv")
    an = [str(a) for a in range(2012, 2027)]
    a0, a1 = an[0], an[-1]

    def ligne(rows, pref, **f):
        cand = [x for x in rows if all(x[k] == v for k, v in f.items())]
        assert len(cand) == 1, (f, len(cand))
        return [float(cand[0][pref + a]) for a in an]

    fr = dict(territoire="France entière", exercice="Ensemble")
    gen = ligne(eff, "effectif_", specialites_agregees="Médecine générale", specialite="Médecine générale", tranche_age="Ensemble", **fr)
    autres = ligne(eff, "effectif_", specialites_agregees="Autres spécialités", specialite="Ensemble", tranche_age="Ensemble", **fr)
    dens_gen = ligne(den, "densite_", specialites_agregees="Médecine générale", specialite="Médecine générale", tranche_age="Ensemble", **fr)
    # Âge des généralistes : 60 ans et plus
    ages = defaultdict(lambda: [0.0] * len(an))
    for x in eff:
        if (x["territoire"] == "France entière" and x["exercice"] == "Ensemble" and x["specialite"] == "Médecine générale"
                and x["specialites_agregees"] == "Médecine générale" and x["tranche_age"] != "Ensemble"):
            for i, a in enumerate(an):
                ages[x["tranche_age"]][i] += float(x["effectif_" + a] or 0)
    tranches_60 = {"entre 60 et 64 ans", "entre 65 et 69 ans", "entre 70 et 74 ans", "75 ans et plus"}
    assert tranches_60 <= set(ages), sorted(ages)
    plus60 = [sum(ages[t][i] for t in tranches_60) for i in range(len(an))]
    part60 = [round(100 * plus60[i] / gen[i], 1) for i in range(len(an))]
    # Généralistes par mode d'exercice
    exercices = ["Libéral", "Mixte", "Salarié hospitalier", "Autre Salarié"]
    par_ex = {e: ligne(eff, "effectif_", territoire="France entière", exercice=e, specialites_agregees="Médecine générale",
                       specialite="Médecine générale", tranche_age="Ensemble") for e in exercices}
    # Spécialités : évolution 2012 -> 2026
    spe = []
    for x in eff:
        if (x["territoire"] == "France entière" and x["exercice"] == "Ensemble" and x["tranche_age"] == "Ensemble"
                and x["specialite"] not in ("Ensemble",) and x["specialites_agregees"] != "Ensemble"
                and not (x["specialites_agregees"] == "Autres spécialités" and x["specialite"] == "Ensemble")):
            spe.append({"specialite": x["specialite"], "debut": float(x["effectif_" + a0]), "fin": float(x["effectif_" + a1]),
                        "pct": round(100 * (float(x["effectif_" + a1]) - float(x["effectif_" + a0])) / float(x["effectif_" + a0]), 1)})
    spe.sort(key=lambda o: o["pct"])
    # Spécialités détaillées absentes en 2012 (aucun effectif) et présentes en 2026
    nouvelles = [x for x in lire("sante_medecins_specialites_detaillees_propre.csv")
                 if x["specialite_detaillee"] != "Ensemble" and not float(x["effectif_" + a0] or 0) and float(x["effectif_" + a1] or 0)]
    nouvelles.sort(key=lambda x: -float(x["effectif_" + a1]))
    # Densité de généralistes par département
    deps = []
    for x in den:
        if (x["departement"] and x["departement"] != "999" and x["exercice"] == "Ensemble" and x["tranche_age"] == "Ensemble"
                and x["specialite"] == "Médecine générale" and x["specialites_agregees"] == "Médecine générale"
                and x["densite_" + a0] != "" and x["densite_" + a1] != ""):
            d0, d1 = float(x["densite_" + a0]), float(x["densite_" + a1])
            # Mayotte : densité non calculée par la DREES en 2012-2013 (valeur 0) -> pas d'évolution calculée
            deps.append({"departement": x["departement"], "nom": NOMS.get(x["departement"], x["libelle_departement"]), "debut": round(d0, 1),
                         "fin": round(d1, 1), "pct": round(100 * (d1 - d0) / d0, 1) if d0 else None})
    deps.sort(key=lambda o: o["fin"])
    return {
        "annees": an,
        "generalistes": [round(v) for v in gen],
        "autres_specialites": [round(v) for v in autres],
        "evol_generalistes": evol(round(gen[0]), round(gen[-1])),
        "evol_autres": evol(round(autres[0]), round(autres[-1])),
        "densite_generalistes": [round(v, 1) for v in dens_gen],
        "part_60_ans_et_plus": part60,
        "part_60_max": {"annee": an[part60.index(max(part60))], "valeur": max(part60)},
        "nouvelles_specialites": {"nombre": len(nouvelles), "effectif_fin": round(sum(float(x["effectif_" + a1]) for x in nouvelles)),
                                  "effectif_fin_autre_specialite": round(sum(float(x["effectif_" + a1]) for x in nouvelles if x["specialite"] == "Autre spécialité")),
                                  "exemples": [{"specialite": re.sub(r"^SM\d+\s*", "", x["specialite_detaillee"]),
                                                "effectif_fin": round(float(x["effectif_" + a1]))} for x in nouvelles[:3]]},
        "par_exercice": {e: [round(v) for v in par_ex[e]] for e in exercices},
        "evol_par_exercice": {e: evol(round(par_ex[e][0]), round(par_ex[e][-1])) for e in exercices},
        "specialites": spe,
        "densite_dep": deps,
        "deps_densite_en_baisse": sum(1 for o in deps if o["pct"] is not None and o["fin"] < o["debut"]),
        "deps_sans_evolution": [o["nom"] for o in deps if o["pct"] is None],
        "definition": "Médecins inscrits à l'Ordre et actifs au 1er janvier (RPPS, DREES), France entière. Densité pour 100 000 habitants calculée par la DREES. Médecine générale = spécialité exercée « Médecine générale » ; « 60 ans et plus » = somme des tranches d'âge à partir de 60 ans.",
    }


def comptes_bloc():
    r = lire("sante_comptes_financement_propre.csv")
    v = {(x["annee"], x["poste"], x["financeur"]): float(x["montant_euros"]) for x in r if x["montant_euros"]}
    annees = sorted({x["annee"] for x in r})
    fin = {"f110": "Sécurité sociale", "f120": "État et collectivités", "f210": "Organismes complémentaires", "f220": "Ménages"}
    parts = [{"annee": a, **{lib: round(100 * v[(a, "p00000", f)] / v[(a, "p00000", "f000")], 1) for f, lib in fin.items()},
              "csbm_md": round(v[(a, "p00000", "f000")] / 1e9, 1)} for a in annees]
    hop = [{"annee": a, "public_md": round(v[(a, "p11000", "f000")] / 1e9, 1), "prive_md": round(v[(a, "p12000", "f000")] / 1e9, 1),
            "part_public": round(100 * v[(a, "p11000", "f000")] / v[(a, "p10000", "f000")], 1)} for a in annees]
    return {
        "financement_csbm": parts,
        "hopital": hop,
        "periode": [annees[0], annees[-1]],
        "definition": "Comptes de la santé (DREES, édition 2026), euros courants non corrigés de l'inflation, séries révisées à chaque édition. CSBM = consommation de soins et de biens médicaux ; parts de chaque financeur. Soins hospitaliers publics et privés au sens des comptes de la santé : le secteur public regroupe les hôpitaux publics, les hôpitaux militaires et les établissements privés à but non lucratif anciennement financés par dotation globale ; les autres établissements non lucratifs sont classés dans le privé ; le secteur privé comprend aussi les cliniques et les honoraires des médecins libéraux qui y exercent.",
    }


def tableau_departements(crit, mat, apld, urg, med):
    rea = {o["departement"]: o["pour_100k"] for o in crit["rea_pour_100k_dep"]}
    mats = {o["departement"]: o for o in mat["par_departement"]}
    apls = {o["departement"]: o for o in apld["departements"]}
    urgs = {o["departement"]: o for o in urg["departements"]}
    dens = {o["departement"]: o for o in med["densite_dep"]}
    lignes = []
    for d, nom in sorted(NOMS.items()):
        lignes.append({
            "departement": d, "nom": nom, "population": POP.get(d),
            "maternites_debut": mats[d]["debut"] if d in mats else 0, "maternites_fin": mats[d]["fin"] if d in mats else 0,
            "rea_pour_100k": rea.get(d), "part_sous_dotee": apls[d]["part_fin"] if d in apls else None,
            "urgences_pct_2019_2023": urgs[d]["pct_2019_2023"] if d in urgs else None,
            "urgences_pour_1000": urgs[d].get("pour_1000_hab_2023") if d in urgs else None,
            "generalistes_pour_100k": dens[d]["fin"] if d in dens else None,
            "generalistes_pct": dens[d]["pct"] if d in dens else None,
        })
    return lignes


def main():
    chiffres = {
        "lits": lits(),
        "effectifs": effectifs(),
        "soins_critiques": soins_critiques(),
        "maternites": maternites(),
        "apl": apl(),
        "urgences": urgences(),
    }
    global NOMS, POP
    NOMS, POP = referentiel()
    chiffres["critiques_detail"] = critiques_detail()
    chiffres["effectifs_detail"] = effectifs_detail()
    chiffres["maternites_detail"] = maternites_detail()
    chiffres["apl_detail"] = apl_detail()
    chiffres["urgences_detail"] = urgences_detail()
    chiffres["ares"] = ares_bloc()
    chiffres["medecins"] = medecins_bloc()
    chiffres["comptes"] = comptes_bloc()
    chiffres["departements"] = tableau_departements(chiffres["critiques_detail"], chiffres["maternites_detail"],
                                                    chiffres["apl_detail"], chiffres["urgences_detail"], chiffres["medecins"])
    with open(os.path.join(DIR, "chiffres_sante.json"), "w", encoding="utf-8") as f:
        json.dump(chiffres, f, ensure_ascii=False, indent=1)
    print(f"{len(chiffres)} blocs -> {DIR}/chiffres_sante.json")


if __name__ == "__main__":
    main()
