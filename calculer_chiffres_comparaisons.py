"""Rapporte les services publics à la population (Insee) et compare la France aux autres pays (Eurostat, OCDE).

Lit donnees_brutes/comparaisons/ (Insee : estimations de population par département et âge ; Eurostat : lits d'hôpital,
dépense publique par fonction, élèves par enseignant ; OCDE : ressources humaines en santé, salaires des enseignants)
et les fiches de chiffres des thèmes ; produit donnees_propres/comparaisons/chiffres_comparaisons.json (EDR-005).
Usage : python3 calculer_chiffres_comparaisons.py
"""
import csv
import glob
import json
import os
from decimal import ROUND_HALF_UP, Decimal

SRC = "donnees_brutes/comparaisons"
OUT = "donnees_propres/comparaisons"
AGES_75_PLUS = ("Y75T79", "Y80T84", "Y85T89", "Y90T94", "Y_GE95")
AGES_MOINS_10 = ("Y_LT5", "Y5T9")
PAYS_VOISINS = {"FR": "France", "DE": "Allemagne", "BE": "Belgique", "IT": "Italie", "ES": "Espagne", "NL": "Pays-Bas",
                "EU27_2020": "Union européenne (27)"}
UE27 = ("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU",
        "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")


def arrondi(x, k=1):
    """Arrondi commercial (0,05 -> 0,1), et non l'arrondi bancaire de round()."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))


def evol(a, b, k=1):
    return {"debut": arrondi(a, k), "fin": arrondi(b, k), "pct": arrondi(100 * (b - a) / a)}


def fiche(theme):
    return json.load(open(f"donnees_propres/{theme}/chiffres_{theme}.json", encoding="utf-8"))


# --- Population (Insee) -----------------------------------------------------------------------
def population():
    """{(département, année, âge): population au 1er janvier} ; âge « _T » = tous âges."""
    pop = {}
    for f in sorted(glob.glob(os.path.join(SRC, "insee_pop_dep_p*.json"))):
        for o in json.load(open(f, encoding="utf-8"))["observations"]:
            dim = o["dimensions"]
            pop[(dim["GEO"].split("-")[-1], dim["TIME_PERIOD"], dim["AGE"])] = o["measures"]["OBS_VALUE_NIVEAU"]["value"]
    return pop


def total(pop, annee, ages=("_T",), deps=None):
    return sum(v for (d, a, g), v in pop.items() if a == annee and g in ages and (deps is None or d in deps))


# --- Eurostat (JSON-stat) -----------------------------------------------------------------------
def eurostat(nom, filtres):
    """Série {(pays, année): valeur} pour une combinaison de modalités (les autres dimensions doivent être uniques)."""
    j = json.load(open(os.path.join(SRC, nom), encoding="utf-8"))
    ids, tailles, dims = j["id"], j["size"], j["dimension"]
    index = {k: dims[k]["category"]["index"] for k in ids}
    for k, n in zip(ids, tailles):
        if k not in ("geo", "time") and k not in filtres and n != 1:
            raise ValueError(f"{nom} : dimension {k} non filtrée ({n} modalités)")
    out = {}
    for g, ig in index["geo"].items():
        for t, it in index["time"].items():
            pos = 0
            for k, n in zip(ids, tailles):
                i = ig if k == "geo" else it if k == "time" else index[k][filtres[k]] if k in filtres else 0
                pos = pos * n + i
            v = j["value"].get(str(pos))
            if v is not None:
                out[(g, t)] = v
    return out


def comparaison_pays(s, annee_debut):
    """France, voisins et moyenne de l'UE ; rang de la France parmi les 27 (ordre croissant) à la dernière année de l'UE."""
    fin = max(a for (g, a) in s if g == "EU27_2020" and ("FR", a) in s)
    disponibles = sorted((s[(p, fin)], p) for p in UE27 if (p, fin) in s)
    return {
        "annee_debut": annee_debut, "annee_fin": fin,
        "pays": {lib: {"debut": s.get((p, annee_debut)), "fin": s.get((p, fin))} for p, lib in PAYS_VOISINS.items()},
        "rang_france_ue_croissant": 1 + [p for _, p in disponibles].index("FR"), "nb_pays_ue": len(disponibles),
        "serie_france": [{"annee": a, "valeur": v} for (g, a), v in sorted(s.items()) if g == "FR" and annee_debut <= a <= fin],
        "serie_ue": [{"annee": a, "valeur": v} for (g, a), v in sorted(s.items()) if g == "EU27_2020" and annee_debut <= a <= fin],
    }


# --- OCDE (CSV avec libellés) ---------------------------------------------------------------------
def ocde(nom, **filtres):
    r = csv.DictReader(open(os.path.join(SRC, nom), encoding="utf-8-sig"))
    return {(x["REF_AREA"], x["TIME_PERIOD"]): float(x["OBS_VALUE"]) for x in r
            if x["OBS_VALUE"] and all(x[k] == v for k, v in filtres.items())}


def main():
    pop = population()
    S, P, G, E = fiche("sante"), fiche("poste"), fiche("logement"), fiche("education")
    metro = {d for (d, _, _) in pop if not d.startswith("97")}
    C = {}

    C["population"] = {
        "france": {a: round(total(pop, a)) for a in ("2009", "2013", "2014", "2015", "2016", "2024", "2025", "2026")},
        "definition": "Insee, estimations localisées de population au 1er janvier, 101 départements (API Melodi, jeu DS_ESTIMATION_POPULATION, Licence Ouverte) ; années 2024 et suivantes provisoires. Moins de 10 ans = 0-4 + 5-9 ans ; 75 ans ou plus = 75-79 à 95 ans ou plus.",
    }

    # Santé : lits rapportés à la population et aux 75 ans ou plus (lits au 31 décembre N ~ population au 1er janvier N+1)
    L = S["lits"]
    a0, a1 = L["periode"]
    p0, p1 = total(pop, str(int(a0) + 1)), total(pop, str(int(a1) + 1))
    v0, v1 = total(pop, str(int(a0) + 1), AGES_75_PLUS), total(pop, str(int(a1) + 1), AGES_75_PLUS)
    lits_ue = eurostat("eurostat_hlth_rs_bds1.json", {"facility": "HBEDT", "hlthcare": "TOTAL"})
    gp = ocde("oecd_ressources_sante.csv", **{"Measure": "Health and social employment", "Unit of measure": "Per 1 000 inhabitants",
                                               "Health profession": "Generalist medical practitioners"})
    fr_gp = {a: v for (p, a), v in gp.items() if p == "FRA"}
    ag0, ag1 = "2011", max(fr_gp)  # ruptures de série signalées par l'OCDE en 2009 et 2011 : série homogène à partir de 2011
    C["sante"] = {
        "periode_lits": [a0, a1],
        "lits_pour_1000": evol(1000 * L["lits"]["debut"] / p0, 1000 * L["lits"]["fin"] / p1, 2),
        "population": evol(p0, p1, 0), "plus_75_ans": evol(v0, v1, 0),
        "lits_pour_1000_plus_75": evol(1000 * L["lits"]["debut"] / v0, 1000 * L["lits"]["fin"] / v1),
        "europe_lits": comparaison_pays(lits_ue, "2000"),
        "europe_lits_france_2013": lits_ue[("FR", "2013")],
        "europe_depense_hopital_pib": comparaison_pays(eurostat("eurostat_gov_10a_exp.json", {"cofog99": "GF0703"}), "1995"),
        "ocde_generalistes": {**evol(fr_gp[ag0], fr_gp[ag1], 2), "annees": [ag0, ag1],
                              "serie": [{"annee": a, "valeur": v} for a, v in sorted(fr_gp.items()) if a >= ag0]},
        "definition": f"Lits d'hospitalisation complète (fiche santé, au 31 décembre {a0} et {a1}) rapportés à la population au 1er janvier suivant (Insee). Eurostat hlth_rs_bds1 : lits d'hôpital disponibles (HP.1), tous soins, pour 100 000 habitants (rupture de série en 2013 signalée par Eurostat ; définition européenne, différente de la statistique française : ne pas comparer les deux sources). Eurostat gov_10a_exp : dépenses des administrations publiques pour les services hospitaliers (CFAP 07.3), en % du PIB. OCDE (DSD_HEALTH_EMP_REAC@DF_REAC) : médecins généralistes pour 1 000 habitants, France, depuis 2011 (ruptures de série en 2009 et 2011).",
    }

    # La Poste : bureaux de poste pour 100 000 habitants (bureaux et population au 1er janvier)
    EV = P["evolution"]
    b0, b1 = EV["periode"]
    eb = EV["evol"]["Bureau de poste"]
    par_dep = {}
    for o in EV["departements"]:
        q0, q1 = total(pop, b0, deps={o["departement"]}), total(pop, b1, deps={o["departement"]})
        if not (q0 and q1):
            continue
        r0, r1 = 1e5 * o["bureaux_debut"] / q0, 1e5 * o["bureaux_fin"] / q1
        par_dep[o["departement"]] = {"nom": o["nom"], "debut": arrondi(r0), "fin": arrondi(r1), "pct": arrondi(100 * (r1 - r0) / r0),
                                     "pct_population": arrondi(100 * (q1 - q0) / q0)}
    C["poste"] = {"periode": [b0, b1],
                  "bureaux_pour_100000": evol(1e5 * eb["debut"] / total(pop, b0), 1e5 * eb["fin"] / total(pop, b1)),
                  "population": evol(total(pop, b0), total(pop, b1), 0), "par_departement": par_dep,
                  "definition": f"Bureaux de poste au 1er janvier {b0} et {b1} (Insee, BPE, fiche poste) rapportés à la population au 1er janvier de la même année (Insee ; {b1} provisoire)."}

    # Éducation : écoles publiques rapportées aux enfants de moins de 10 ans ; comparaisons internationales
    EC = E["ecoles"]
    e0, e1 = EC["periode"]
    hors_976 = {d for (d, _, _) in pop if d != "976"}  # Mayotte : pas d'estimation par âge avant 2014, exclue aux deux dates
    k0, k1 = total(pop, e0, AGES_MOINS_10, hors_976), total(pop, e1, AGES_MOINS_10, hors_976)
    ec0 = sum(o["ecoles_public_debut"] for o in E["departements"]["departements"] if o["departement"] != "976")
    ec1 = sum(o["ecoles_public_fin"] for o in E["departements"]["departements"] if o["departement"] != "976")
    par_dep = {}
    for o in E["departements"]["departements"]:
        q0, q1 = total(pop, e0, AGES_MOINS_10, {o["departement"]}), total(pop, e1, AGES_MOINS_10, {o["departement"]})
        if not (q0 and q1):
            continue  # pas d'estimation par âge à l'une des deux dates (Mayotte avant 2014)
        r0, r1 = 1e4 * o["ecoles_public_debut"] / q0, 1e4 * o["ecoles_public_fin"] / q1
        par_dep[o["departement"]] = {"nom": o["nom"], "debut": arrondi(r0), "fin": arrondi(r1), "pct": arrondi(100 * (r1 - r0) / r0),
                                     "pct_enfants": arrondi(100 * (q1 - q0) / q0)}
    ee = eurostat("eurostat_educ_uoe_perp04.json", {"isced11": "ED1"})
    eleves = comparaison_pays(ee, "2013")
    sal = ocde("oecd_salaires_enseignants_tendance.csv", **{"Education level": "Primary education", "Experience level": "After 15 years of experience",
                                                            "Unit of measure": "Index", "Type of educational institution": "Public educational institutions"})
    C["education"] = {
        "periode": [e0, e1],
        "ecoles_pour_10000_enfants": evol(1e4 * ec0 / k0, 1e4 * ec1 / k1),
        "enfants_moins_10": evol(k0, k1, 0), "par_departement": par_dep,
        "deps_ratio_en_baisse": sum(1 for o in par_dep.values() if o["pct"] < 0),
        "ocde_salaires_hausse_2000_2025": sorted(p for (p, a), v in sal.items() if a == "2025" and (p, "2000") in sal and p not in ("OECD", "EU25") and v > sal[(p, "2000")]),
        "ocde_salaires_baisse_2000_2025": sorted(p for (p, a), v in sal.items() if a == "2025" and (p, "2000") in sal and p not in ("OECD", "EU25") and v < sal[(p, "2000")]),
        "ocde_salaires_primaire": {p: dict(sorted((a, v) for (q, a), v in sal.items() if q == p)) for p in ("FRA", "OECD", "DEU", "ITA", "ESP")},
        "europe_eleves_par_enseignant_primaire": eleves,
        "eleves_ex_aequo_france": [p for p in UE27 if p != "FR" and ee.get((p, eleves["annee_fin"])) == ee.get(("FR", eleves["annee_fin"]))],
        "eleves_pays_au_dessus": [p for p in UE27 if (ee.get((p, eleves["annee_fin"])) or 0) > ee[("FR", eleves["annee_fin"])]],
        "eleves_valeurs_ue_fin": {p: ee[(p, eleves["annee_fin"])] for p in UE27 if (p, eleves["annee_fin"]) in ee},
        "europe_depense_education_pib": comparaison_pays(eurostat("eurostat_gov_10a_exp.json", {"cofog99": "GF09"}), "1995"),
        "definition": f"Écoles publiques (fiche éducation, rentrées {e0} et {e1}) rapportées aux enfants de moins de 10 ans au 1er janvier de la même année (Insee ; tranche plus large que l'âge de l'école primaire, faute de tranche plus fine), hors Mayotte aux deux dates ; une école en moins peut être une fusion. OCDE, Regards sur l'éducation (DSD_EAG_SAL_TREND@DF_TCH_STA) : indice des salaires statutaires des enseignants du primaire public après 15 ans d'expérience, base 100 en 2015, tel que publié. Eurostat educ_uoe_perp04 : élèves par enseignant dans le primaire (CITE 1). Eurostat gov_10a_exp : dépenses des administrations publiques pour l'enseignement (CFAP 09), en % du PIB.",
    }

    # Logement : mises en service rapportées à la population de France métropolitaine
    PA = G["parc"]
    pic, der = PA["mises_en_service_pic"], PA["mises_en_service_derniere"]
    m0, m1 = total(pop, pic["annee_mise_en_service"], deps=metro), total(pop, der["annee_mise_en_service"], deps=metro)
    C["logement"] = {"annees": [pic["annee_mise_en_service"], der["annee_mise_en_service"]],
                     "mises_en_service_pour_10000": evol(1e4 * pic["valeur"] / m0, 1e4 * der["valeur"] / m1, 2),
                     "population_metropole": evol(m0, m1, 0),
                     "europe_depense_logement_pib": comparaison_pays(eurostat("eurostat_gov_10a_exp.json", {"cofog99": "GF06"}), "1995"),
                     "definition": "Logements sociaux mis en service (fiche logement, France métropolitaine) rapportés à la population de France métropolitaine au 1er janvier de l'année de mise en service (Insee). Eurostat gov_10a_exp : dépenses des administrations publiques pour le logement et les équipements collectifs (CFAP 06), en % du PIB."}

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "chiffres_comparaisons.json"), "w", encoding="utf-8") as f:
        json.dump(C, f, ensure_ascii=False, indent=1)
    print(f"{len(C)} blocs -> {OUT}/chiffres_comparaisons.json")


if __name__ == "__main__":
    main()
