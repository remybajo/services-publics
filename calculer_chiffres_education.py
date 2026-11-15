"""Calcule les chiffres du rapport éducation à partir de donnees_propres/education/ (EDR-005 : tout chiffre est rejouable).

Produit donnees_propres/education/chiffres_education.json : séries des graphiques + chiffres clés, chacun avec sa définition.
Usage : python3 calculer_chiffres_education.py
"""
import csv
import json
import os
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

DIR = "donnees_propres/education"
PETITE_ECOLE = 2  # école publique « à une ou deux classes »


def lire(nom):
    with open(os.path.join(DIR, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def f(v):
    return float(v) if v not in ("", None) else 0.0


def arrondi(x, k=1):
    """Arrondi commercial (0,05 -> 0,1), et non l'arrondi bancaire de round()."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))


def code_dep(c):
    """Harmonise les codes départements des différentes sources : « 001 » -> « 01 », « 02A » -> « 2A », DROM inchangés."""
    return c[1:] if len(c) == 3 and c.startswith("0") else c


def evol(a, b):
    return {"debut": a, "fin": b, "ecart": b - a, "pct": arrondi(100 * (b - a) / a)}


def ecoles():
    r = [x for x in lire("education_ecoles_propre.csv") if x["dans_101_departements"] == "1"]
    nb, el, cl, pet = defaultdict(int), defaultdict(float), defaultdict(float), defaultdict(int)
    uai_pu = defaultdict(set)
    for x in r:
        k = (x["rentree"], x["secteur"])
        nb[k] += 1
        el[k] += f(x["eleves"])
        cl[k] += f(x["classes"])
        if x["secteur"] == "public":
            uai_pu[x["rentree"]].add(x["uai"])
        if x["secteur"] == "public" and 0 < f(x["classes"]) <= PETITE_ECOLE:
            pet[x["rentree"]] += 1
    annees = sorted({x["rentree"] for x in r})
    a0, a1 = annees[0], annees[-1]
    serie = [{"rentree": a, "ecoles_public": nb[(a, "public")], "ecoles_prive": nb[(a, "prive_sous_contrat")],
              "eleves_public": round(el[(a, "public")]), "eleves_prive": round(el[(a, "prive_sous_contrat")]),
              "classes_public": round(cl[(a, "public")]),
              "eleves_par_classe_public": arrondi(el[(a, "public")] / cl[(a, "public")]),
              "eleves_par_classe_prive": arrondi(el[(a, "prive_sous_contrat")] / cl[(a, "prive_sous_contrat")]),
              "part_eleves_prive": arrondi(100 * el[(a, "prive_sous_contrat")] / (el[(a, "public")] + el[(a, "prive_sous_contrat")])),
              "petites_ecoles_public": pet[a]} for a in annees]
    return {
        "serie": serie,
        "ecoles_public": evol(nb[(a0, "public")], nb[(a1, "public")]),
        "ecoles_prive": evol(nb[(a0, "prive_sous_contrat")], nb[(a1, "prive_sous_contrat")]),
        "eleves_public": evol(round(el[(a0, "public")]), round(el[(a1, "public")])),
        "eleves_prive": evol(round(el[(a0, "prive_sous_contrat")]), round(el[(a1, "prive_sous_contrat")])),
        "classes_public": evol(round(cl[(a0, "public")]), round(cl[(a1, "public")])),
        "petites_ecoles_public": evol(pet[a0], pet[a1]),
        "uai_public_sorties": len(uai_pu[a0] - uai_pu[a1]),
        "uai_public_entrees": len(uai_pu[a1] - uai_pu[a0]),
        "ecart_part_prive_points": arrondi(100 * el[(a1, "prive_sous_contrat")] / (el[(a1, "public")] + el[(a1, "prive_sous_contrat")])
                                           - 100 * el[(a0, "prive_sous_contrat")] / (el[(a0, "public")] + el[(a0, "prive_sous_contrat")])),
        "eleves_masques": sum(1 for x in r if x["eleves"] == ""),
        "periode": [a0, a1],
        "definition": f"DEPP, effectifs d'élèves et nombre de classes par école (Licence Ouverte), écoles maternelles et élémentaires publiques et privées sous contrat, rentrées {a0} à {a1}, 101 départements (collectivités d'outre-mer présentes seulement à partir de 2019 exclues). Une école = un numéro UAI présent à la rentrée ; une école qui disparaît du fichier peut avoir fermé, fusionné avec une autre ou changé de numéro : on parle d'écoles « en moins », pas de fermetures. Élèves par classe = élèves / classes (ULIS comprises). Petites écoles = écoles publiques à une ou deux classes. 98 écoles libellées « PRIVE » en 2022, toutes dans des collectivités d'outre-mer hors périmètre (sans effet sur les chiffres). Entre la première et la dernière rentrée, uai_public_sorties numéros d'écoles publiques disparaissent et uai_public_entrees apparaissent : l'ampleur de ce renouvellement indique que des fusions (maternelle et élémentaire regroupées en école primaire, regroupements) peuvent expliquer une partie importante de la baisse, sans que les données permettent de la mesurer ; à dire à côté du chiffre. Contexte obligatoire : élèves du public en baisse, classes du public en hausse, élèves par classe en baisse dans le public. Quelques nombres d'élèves sont masqués par le secret statistique (eleves_masques lignes, petites écoles) : effet négligeable. La source ne contient pas le code commune Insee (la colonne ainsi nommée contient le code postal) : pas d'analyse par commune.",
    }


def segregation():
    r = lire("education_segregation_propre.csv")
    fr = sorted([x for x in r if x["niveau"] == "france"], key=lambda x: x["annee"])
    serie = [{"annee": x["annee"], **{k: f(x[k]) for k in ("poids_prive_calcul", "p_tfav", "p_tfav_pu", "p_tfav_pr", "p_defav", "p_defav_pu", "p_defav_pr",
                                                          "contrib_interpupr", "i_entropie_tot")}} for x in fr]
    a1 = fr[-1]["annee"]
    deps = sorted([x for x in r if x["niveau"] == "departement" and x["annee"] == a1 and x["contrib_interpupr"] != ""],
                  key=lambda x: -f(x["contrib_interpupr"]))
    return {
        "serie": serie,
        "par_departement": {code_dep(x["departement"]): {"nom": x["nom_departement"], "contrib_interpupr": f(x["contrib_interpupr"]),
                                               "poids_prive": f(x["poids_prive_calcul"]), "p_tfav_pu": f(x["p_tfav_pu"]),
                                               "p_tfav_pr": f(x["p_tfav_pr"])} for x in deps},
        "deps_sans_valeur": sorted(code_dep(x["departement"]) for x in r if x["niveau"] == "departement" and x["annee"] == a1 and x["contrib_interpupr"] == ""),
        "definition": "DEPP, indicateur de ségrégation sociale entre collèges publics et privés sous contrat (Licence Ouverte), 2014 à 2025. p_tfav / p_defav = part des collégiens d'origine sociale très favorisée / défavorisée parmi les collégiens de l'ensemble, du public (_pu) ou du privé (_pr), en % (ex. p_tfav_pr = part des collégiens du privé d'origine très favorisée, et non part des très favorisés scolarisés dans le privé) ; poids_prive = part des collégiens scolarisés dans le privé, en % ; i_entropie_tot = indice de ségrégation sociale (entropie) entre collèges ; contrib_interpupr = contribution des écarts entre secteurs public et privé à l'indice (part de la ségrégation entre collèges qui tient à l'écart de composition sociale entre public et privé), en %. Champ : France métropolitaine et DROM, PCS non renseignées exclues. Prudence pour 2023 : la remontée de la deuxième PCS dans le privé change fortement cette année-là (métadonnées de l'IPS), ce qui peut créer une rupture dans le privé. Valeurs reprises telles que publiées par la DEPP. Départements sans collège privé : pas de valeur.",
    }


HORS_DEPARTEMENTS_IPS = {"975", "981", "982", "983", "986", "987"}  # collectivités d'outre-mer et provinces de Nouvelle-Calédonie


def ips():
    r = lire("education_ips_colleges_propre.csv")
    a1 = max(x["rentree"] for x in r)
    s = [x for x in r if x["rentree"] == a1]
    nat = next(x for x in s if x["ips_national_public"] != "")
    par_dep = {}
    for x in s:
        if x["ips_departemental_public"] != "":
            par_dep[code_dep(x["departement"])] = {"nom": x["nom_departement"], "ips_public": f(x["ips_departemental_public"]),
                                         "ips_prive": f(x["ips_departemental_prive"]) if x["ips_departemental_prive"] != "" else None}
    deps_101 = {k: o for k, o in par_dep.items() if k not in HORS_DEPARTEMENTS_IPS}
    avec_prive = [o for o in deps_101.values() if o["ips_prive"] is not None]
    return {
        "rentree": a1,
        "national_public": f(nat["ips_national_public"]), "national_prive": f(nat["ips_national_prive"]),
        "colleges_101_departements": {"public": sum(1 for x in s if x["secteur"] == "public" and code_dep(x["departement"]) not in HORS_DEPARTEMENTS_IPS),
                                      "prive": sum(1 for x in s if x["secteur"] != "public" and code_dep(x["departement"]) not in HORS_DEPARTEMENTS_IPS)},
        "par_departement": dict(sorted(par_dep.items())),
        "deps_prive_plus_favorise": sum(1 for o in avec_prive if o["ips_prive"] > o["ips_public"]),
        "deps_avec_prive": len(avec_prive),
        "nb_departements": len(deps_101),
        "deps_sans_prive": sorted(o["nom"] for o in deps_101.values() if o["ips_prive"] is None),
        "ecart_min_departemental": arrondi(min(o["ips_prive"] - o["ips_public"] for o in avec_prive)),
        "classement_ecart_departemental": [{"departement": k, "nom": o["nom"], "ecart": arrondi(o["ips_prive"] - o["ips_public"])}
                                           for k, o in sorted(((k, o) for k, o in deps_101.items() if o["ips_prive"] is not None),
                                                              key=lambda kv: -(kv[1]["ips_prive"] - kv[1]["ips_public"]))][:15],
        "definition": f"DEPP, indice de position sociale (IPS) des collèges (Licence Ouverte), rentrée {a1} : IPS nationaux et départementaux du public et du privé sous contrat tels que publiés par la DEPP (un IPS élevé = élèves de milieux plus favorisés). Série commencée en 2023-2024 : rupture avec l'IPS publié jusqu'en 2021-2022, aucune comparaison avec les années antérieures. Comptages départementaux limités aux 101 départements (Saint-Pierre-et-Miquelon, provinces de Nouvelle-Calédonie, Wallis-et-Futuna et Polynésie exclus) ; IPS nationaux hors collectivités d'outre-mer ; la DEPP déconseille d'interpréter des écarts de 3 points ou moins. Classement des écarts départementaux (IPS privé − IPS public) : 101 départements, DROM compris.",
    }


ANNEE_HOMOGENE = "2015-16"  # première année sans doubles inscriptions CPGE et avec les apprentis de STS : périmètre stable
HORS_TERRITOIRES_SUP = {"999"}  # « Étranger » : pas un département
COM_SUP = {"975", "977", "978", "986", "987", "988"}  # collectivités d'outre-mer, hors des 101 départements


def superieur():
    r = lire("education_superieur_propre.csv")
    tot, app, reg, dep = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    noms = {}
    for x in r:
        e = f(x["effectif_hors_doubles_cpge"])
        tot[(x["annee"], x["secteur"])] += e
        app[(x["annee"], x["secteur"])] += f(x["apprentis_sts"])
        reg[(x["annee"], x["regroupement"], x["libelle_regroupement"], x["secteur"])] += e
        dep[(x["annee"], code_dep(x["departement"]), x["secteur"])] += e
        noms[code_dep(x["departement"])] = x["nom_departement"]
    annees = sorted({x["annee"] for x in r})
    a0, a1, ah = annees[0], annees[-1], ANNEE_HOMOGENE

    def part(a, hors_app=False):
        pr = tot[(a, "prive")] - (app[(a, "prive")] if hors_app else 0)
        pu = tot[(a, "public")] - (app[(a, "public")] if hors_app else 0)
        return arrondi(100 * pr / (pr + pu))

    serie = [{"annee": a, "public": round(tot[(a, "public")]), "prive": round(tot[(a, "prive")]),
              "apprentis_sts_prive": round(app[(a, "prive")]), "apprentis_sts_public": round(app[(a, "public")]),
              "part_prive": part(a), "part_prive_hors_apprentis_sts": part(a, True)} for a in annees]
    pic = max(serie, key=lambda o: o["part_prive"])
    sts_lib = next(lib for (_, code, lib, _) in reg if code == "STS")  # les apprentis de la source sont tous en STS
    croissance = []
    for (a, code, lib, sct), v in reg.items():
        if a == a1 and sct == "prive":
            v0 = reg.get((ah, code, lib, "prive"), 0.0)
            croissance.append({"regroupement": lib, "debut": round(v0), "fin": round(v), "ecart": round(v - v0),
                               "reclassement_probable": v0 < 0.05 * v})  # quasi absent en 2015-16 : changement de nomenclature probable
    croissance.sort(key=lambda o: -o["ecart"])
    par_dep = {}
    for code in sorted({c for (a, c, _) in dep if a == a1}):
        if code in HORS_TERRITOIRES_SUP:
            continue
        pr, pu = dep.get((a1, code, "prive"), 0.0), dep.get((a1, code, "public"), 0.0)
        par_dep[code] = {"nom": noms[code], "prive": round(pr), "public": round(pu),
                         "part_prive": arrondi(100 * pr / (pr + pu)) if pr + pu else None, "collectivite_outre_mer": code in COM_SUP}
    return {
        "serie": serie,
        "homogene": {"debut": ah, "fin": a1, "prive": evol(round(tot[(ah, "prive")]), round(tot[(a1, "prive")])),
                     "public": evol(round(tot[(ah, "public")]), round(tot[(a1, "public")])),
                     "part_prive_debut": part(ah), "part_prive_fin": part(a1)},
        "longue_hors_apprentis": {"debut": a0, "fin": a1,
                                  "prive": evol(round(tot[(a0, "prive")] - app[(a0, "prive")]), round(tot[(a1, "prive")] - app[(a1, "prive")])),
                                  "part_prive_debut": part(a0, True), "part_prive_fin": part(a1, True)},
        "pic_part_prive": {"annee": pic["annee"], "part": pic["part_prive"]},
        "sts_prive": {"apprentis": evol(round(app[(ah, "prive")]), round(app[(a1, "prive")])),
                      "hors_apprentis": evol(round(reg[(ah, "STS", sts_lib, "prive")] - app[(ah, "prive")]),
                                             round(reg[(a1, "STS", sts_lib, "prive")] - app[(a1, "prive")]))},
        "croissance_prive_par_regroupement": croissance,
        "par_departement": par_dep,
        "periode": [a0, a1],
        "definition": f"SIES, effectifs d'étudiants inscrits dans l'enseignement supérieur, version agrégeable (Licence Ouverte), {a0} à {a1}, France entière (inscrits à l'étranger compris dans les totaux, exclus du tableau départemental) : colonne effectif_atlas. Deux ruptures en {ah} : les doubles inscriptions CPGE/université (public) cessent d'être comptées deux fois, et les apprentis de STS (environ 41 000 dans le privé en {ah}, 134 000 en {a1}) entrent dans la série. Comparaison principale sur le périmètre homogène {ah} -> {a1} ; la série longue {a0} -> {a1} n'est présentée que hors apprentis de STS (le public y reste majoré par les doubles comptes CPGE avant {ah}, ce qui sous-estime sa hausse et la part du privé en {a0}). Secteur de l'établissement d'inscription : public ou privé, sans distinction lucratif/non lucratif. Croissance par regroupement calculée sur {ah} -> {a1} ; regroupements quasi absents en {ah} (moins de 5 % de leur effectif final : universités, grands établissements privés) = reclassements de nomenclature probables, pas une croissance. Écoles paramédicales et sociales provisoires pour {a1}. Département = département de la commune d'inscription ; départements sans inscrit dans le privé à 0 %.",
    }


def departements(E):
    r = [x for x in lire("education_ecoles_propre.csv") if x["dans_101_departements"] == "1"]
    a0, a1 = E["periode"]
    agg = defaultdict(lambda: defaultdict(float))
    noms = {}
    for x in r:
        if x["rentree"] in (a0, a1):
            o = agg[x["departement"]]
            s = "pu" if x["secteur"] == "public" else "pr"
            o[f"ecoles_{s}_{x['rentree']}"] += 1
            o[f"eleves_{s}_{x['rentree']}"] += f(x["eleves"])
            o[f"classes_{s}_{x['rentree']}"] += f(x["classes"])
            noms[x["departement"]] = x["nom_departement"]
    out = []
    for dep, o in sorted(agg.items()):
        e0, e1 = o[f"ecoles_pu_{a0}"], o[f"ecoles_pu_{a1}"]
        el1 = o[f"eleves_pu_{a1}"] + o[f"eleves_pr_{a1}"]
        out.append({"departement": dep, "nom": noms[dep], "ecoles_public_debut": int(e0), "ecoles_public_fin": int(e1),
                    "pct_ecoles_public": arrondi(100 * (e1 - e0) / e0) if e0 else None,
                    "pct_eleves_public": arrondi(100 * (o[f"eleves_pu_{a1}"] - o[f"eleves_pu_{a0}"]) / o[f"eleves_pu_{a0}"]) if o[f"eleves_pu_{a0}"] else None,
                    "part_eleves_prive_fin": arrondi(100 * o[f"eleves_pr_{a1}"] / el1) if el1 else None,
                    "eleves_par_classe_public_fin": arrondi(o[f"eleves_pu_{a1}"] / o[f"classes_pu_{a1}"]) if o[f"classes_pu_{a1}"] else None})
    baisse = [o for o in out if o["pct_ecoles_public"] is not None and o["pct_ecoles_public"] < 0]
    plus_vite = [o for o in baisse if o["pct_eleves_public"] is not None and o["pct_ecoles_public"] < o["pct_eleves_public"]]
    eleves_hausse = [o for o in baisse if o["pct_eleves_public"] is not None and o["pct_eleves_public"] > 0]
    return {
        "departements": out,
        "deps_ecoles_public_en_baisse": len(baisse),
        "deps_ecoles_reculent_plus_que_eleves": len(plus_vite),
        "deps_ecoles_reculent_eleves_augmentent": len(eleves_hausse),
        "deps_ecoles_public_en_hausse": [o["nom"] for o in out if o["pct_ecoles_public"] is not None and o["pct_ecoles_public"] > 0],
        "classement_baisse_ecoles_public": sorted(baisse, key=lambda o: o["pct_ecoles_public"])[:15],
        "definition": f"Par département (101 départements), écoles et élèves du premier degré public et privé sous contrat aux rentrées {a0} et {a1} (DEPP) ; mêmes réserves que le bloc ecoles (écoles en moins et non fermetures).",
    }


def main():
    E = ecoles()
    chiffres = {"ecoles": E, "segregation": segregation(), "ips": ips(), "superieur": superieur(), "departements": departements(E)}
    with open(os.path.join(DIR, "chiffres_education.json"), "w", encoding="utf-8") as fichier:
        json.dump(chiffres, fichier, ensure_ascii=False, indent=1)
    print(f"{len(chiffres)} blocs -> {DIR}/chiffres_education.json")


if __name__ == "__main__":
    main()
