"""Calcule les chiffres du rapport logement à partir de donnees_propres/logement/ (EDR-005 : tout chiffre est rejouable).

Produit donnees_propres/logement/chiffres_logement.json : séries des graphiques + chiffres clés, chacun avec sa définition.
Usage : python3 calculer_chiffres_logement.py
"""
import csv
import json
import os
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

DIR = "donnees_propres/logement"
MOIS_CAF = "03"  # mois comparé d'une année à l'autre (dernier mois disponible : mars 2026)
HORS_DEPARTEMENTS_CAF = {"99", "XX"}  # codes Caf sans département (comptés dans le total national)
SEUIL_MES = 100  # mises en service annuelles minimales en 2013-2015 pour figurer dans le classement des baisses


def lire(nom):
    with open(os.path.join(DIR, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def f(v):
    return float(v) if v not in ("", None) else 0.0


def arrondi(x, k=1):
    """Arrondi commercial (0,05 -> 0,1), et non l'arrondi bancaire de round()."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))


def evol(a, b):
    return {"debut": a, "fin": b, "ecart": b - a, "pct": arrondi(100 * (b - a) / a)}


def parc():
    r = lire("logement_parc_social_propre.csv")
    parc, mes = defaultdict(float), defaultdict(float)
    for x in r:
        parc[x["annee"]] += f(x["logements_sociaux"])
        mes[x["annee"]] += f(x["mises_en_service"])
    annees = sorted(parc)
    pic = max(annees, key=lambda a: mes[a])
    return {
        "serie": [{"annee": a, "annee_mise_en_service": str(int(a) - 1), "logements_sociaux": round(parc[a]),
                   "mises_en_service": round(mes[a])} for a in annees],
        "parc": evol(round(parc[annees[0]]), round(parc[annees[-1]])),
        "mises_en_service_pic": {"annee": pic, "annee_mise_en_service": str(int(pic) - 1), "valeur": round(mes[pic])},
        "mises_en_service_derniere": {"annee": annees[-1], "annee_mise_en_service": str(int(annees[-1]) - 1), "valeur": round(mes[annees[-1]])},
        "hausse_parc_derniere_annee": round(parc[annees[-1]] - parc[annees[-2]]),
        "mises_en_service_vs_pic": evol(round(mes[pic]), round(mes[annees[-1]])),
        "nb_departements": len({x["departement"] for x in r}),
        "definition": "SDES, répertoire des logements locatifs des bailleurs sociaux (RPLS), résultats 2025, onglet DEPARTEMENT : logements du parc locatif social au 1er janvier de chaque année (champ « décret » : hors logements non conventionnés des SEM), 96 départements de France métropolitaine (Corse comprise, DROM non présents dans l'onglet). Le champ France entière (DROM compris) n'existe que dans l'onglet REGION. Mises en service « au 1er janvier N » = logements mis en service entre le 2 janvier N-1 et le 1er janvier N (onglet INFORMATIONS du RPLS 2024), d'où le champ annee_mise_en_service ; série disponible pour les mises en service 2012 à 2024 (« pic de la période »). Une mise en service n'est pas une construction : elle comprend les logements construits par l'organisme, acquis en VEFA ou acquis avec ou sans travaux. Rupture de série en 2023 (méthode d'imputation revue par le SDES) : effet mesuré dans le RPLS 2024, −2 012 logements en 2023 (−0,04 %) ; années 2013-2022 non rétropolées (valeurs de l'ancienne méthode) ; l'évolution 2013-2025 reste publiable avec cette mention.",
    }


def sorties():
    r = lire("logement_sorties_propre.csv")
    p = defaultdict(float)
    for x in lire("logement_parc_social_propre.csv"):
        p[x["annee"]] += f(x["mises_en_service"])
    out = {}
    for m in sorted({x["millesime"] for x in r}):
        s = [x for x in r if x["millesime"] == m]
        tot = {k: round(sum(f(x[k]) for x in s)) for k in ("ventes_occupant", "autres_ventes", "ventes_autre_bailleur",
                                                         "demolitions", "autres_motifs", "changements_usage", "fusions_scissions")}
        ventes_hors_hlm = tot["ventes_occupant"] + tot["autres_ventes"]
        out[m] = {"annee_des_sorties": str(int(m) - 1), **tot, "ventes_occupant_et_autres": ventes_hors_hlm,
                  "demolitions_et_ventes_occupant_et_autres": ventes_hors_hlm + tot["demolitions"],
                  "mises_en_service_meme_annee": round(p[m]),
                  "pour_100_mises_en_service": arrondi(100 * (ventes_hors_hlm + tot["demolitions"]) / p[m])}
    return {
        "par_millesime": out,
        "definition": "SDES, RPLS, résultats 2024 et 2025, onglet DEPARTEMENT : logements sortis du parc social au cours de l'année précédant le millésime, par motif (libellés de la source). « Ventes à l'occupant et autres ventes » = ventes à l'occupant + « autre vente », hors ventes à un autre bailleur social, présentées à part ; la source ne définit pas « autre vente » (ne pas écrire « ventes au privé »). Les sorties « changement d'usage » et « fusion scission » sont peut-être des sous-catégories d'« autre motif » : aucun total de toutes les sorties n'est calculé. Rapport « pour 100 mises en service » = (ventes à l'occupant et autres ventes + démolitions) / mises en service de la même année ; ce n'est pas un solde (le parc augmente de hausse_parc_derniere_annee logements entre 2024 et 2025, bloc parc). France métropolitaine. Deux années seulement : ne permet pas de dégager une tendance.",
    }


def sru():
    r = lire("logement_sru_propre.csv")
    out = []
    for m in sorted({x["millesime"] for x in r}):
        s_ = [x for x in r if x["millesime"] == m and x["commune_sru"] in ("", "1.0")]
        # « déficitaire » hors exemptées : définition des millésimes 2023, 2024 et 2026, appliquée aussi à 2025 (qui marque des exemptées)
        defic = [x for x in s_ if f(x["deficitaire"]) == 1 and f(x["exemptee"]) != 1]
        out.append({"millesime": m, "annee_inventaire": s_[0]["annee_inventaire"], "communes_sru": len(s_),
                    "deficitaires_marquees": sum(1 for x in s_ if f(x["deficitaire"]) == 1),
                    "deficitaires_hors_exemptees": len(defic),
                    "carencees": sum(1 for x in s_ if f(x["carencee"]) == 1),
                    "prelevement_net_m": arrondi(sum(f(x["prelevement_net"]) for x in s_) / 1e6) if s_[0]["prelevement_net"] != "" else None,
                    "communes_avec_prelevement": sum(1 for x in s_ if f(x["prelevement_net"]) > 0) if s_[0]["prelevement_net"] != "" else None})
    der = out[-1]
    s_ = [x for x in r if x["millesime"] == der["millesime"] and x["commune_sru"] in ("", "1.0")]
    sans_marqueur = sorted(x["commune"] for x in s_ if x["deficitaire"] == "")
    par_dep = defaultdict(lambda: {"communes_sru": 0, "deficitaires": 0, "carencees": 0})
    for x in s_:
        o = par_dep[x["code_departement"]]
        o["communes_sru"] += 1
        o["deficitaires"] += f(x["deficitaire"]) == 1
        o["carencees"] += f(x["carencee"]) == 1
    drom = [x for x in s_ if x["code_departement"].startswith("97")]
    return {
        "serie": out,
        "dernier": der,
        "part_deficitaires": arrondi(100 * der["deficitaires_marquees"] / der["communes_sru"]),
        "communes_sans_marqueur_deficitaire": sans_marqueur,
        "drom": {"communes_sru": len(drom), "deficitaires": sum(1 for x in drom if f(x["deficitaire"]) == 1)},
        "par_departement": {k: {kk: int(vv) for kk, vv in v.items()} for k, v in sorted(par_dep.items())},
        "definition": "Ministère chargé du logement, inventaire SRU (millésimes 2023 à 2026, Licence Ouverte), France entière (DROM compris) : communes soumises à l'article 55 de la loi SRU (taux cible de 20 ou 25 % de logements sociaux) ; logements sociaux et taux au 1er janvier de l'année précédant le millésime. « Déficitaire » = marqueur de l'inventaire : sous le taux cible et non exemptée dans les millésimes 2023, 2024 et 2026 ; le millésime 2025 marque aussi 139 communes exemptées (et quelques communes au-dessus de leur taux), d'où la série « deficitaires_hors_exemptees », seule comparable d'un millésime à l'autre (le périmètre des communes change toutefois chaque année). Seul le chiffre 2026 « déficitaires selon l'inventaire » est publié comme niveau ; 5 communes SRU n'ont pas de marqueur (communes_sans_marqueur_deficitaire, dont Neuilly-sur-Seine, carencée sans inventaire). Carencée = arrêté de carence de la période triennale 2023-2025 (278 communes dans le millésime 2023, liste très différente ; 336 en 2024, 335 en 2025 et 2026). Prélèvement : « montant du prélèvement net (dont majoration) inscrit à l'inventaire », absent du millésime 2023 ; « - € » lu comme 0 ; quelques communes ont un prélèvement sans être marquées déficitaires. Millésime 2026 : les 3 communes sortantes au 1er janvier 2026 sont exclues.",
    }


def aides_compte():
    r = lire("logement_compte_aides_propre.csv")
    v = {(x["tableau"], x["ligne"], x["annee"]): f(x["valeur"]) for x in r if x["valeur"] != ""}
    annees = [str(a) for a in range(2010, 2026)]
    serie = []
    for a in annees:
        montant = sum(v[("T311", k, a)] for k in ("APL (1)", "ALS (1)", "ALF (1)"))
        benef = v[("T341", "ENSEMBLE APL + AL", a)]
        serie.append({"annee": a, "montant_md": arrondi(montant / 1000, 2), "beneficiaires_m": arrondi(benef / 1000, 2),
                      "moyenne_mensuelle_apl": arrondi(v[("T343", "Ensemble des allocataires", a)], 0),
                      "moyenne_mensuelle_al": arrondi(v[("T343", "Ensemble des allocataires A.L.", a)], 0),
                      "ensemble_aides_md": arrondi(v[("T311", "ENSEMBLE DES AIDES AU LOGEMENT", a)] / 1000, 1)})
    brut = {a: sum(v[("T311", k, a)] for k in ("APL (1)", "ALS (1)", "ALF (1)")) for a in annees}
    pic = max(annees, key=lambda a: brut[a])
    b17, b25 = v[("T341", "ENSEMBLE APL + AL", "2017")], v[("T341", "ENSEMBLE APL + AL", "2025")]
    return {
        "serie": serie,
        "montant_2017_2025": {"debut": arrondi(brut["2017"] / 1000, 2), "fin": arrondi(brut["2025"] / 1000, 2),
                              "ecart": arrondi((brut["2025"] - brut["2017"]) / 1000, 2), "pct": arrondi(100 * (brut["2025"] - brut["2017"]) / brut["2017"])},
        "beneficiaires_2017_2025": {"debut": arrondi(b17 / 1000, 2), "fin": arrondi(b25 / 1000, 2),
                                    "ecart_milliers": round(b25 - b17), "pct": arrondi(100 * (b25 - b17) / b17)},
        "pic_montant": {"annee": pic, "md": arrondi(brut[pic] / 1000, 2)},
        "definition": "SDES, compte du logement 2025, séries longues (licence ouverte selon les mentions légales du site du SDES, https://www.statistiques.developpement-durable.gouv.fr/mentions-legales) : tableau T311 (montant des aides personnelles au logement APL + ALS + ALF, millions d'euros courants) et tableau T341 (nombre de bénéficiaires APL + AL, milliers, ligne « ENSEMBLE APL + AL »). Champ : France entière (compte du logement 2025, fichier des figures, onglet « Figure 5.8 », cellule A14). Montants mensuels moyens : tableau officiel T343 (APL, ligne « Ensemble des allocataires » ; AL, ligne « Ensemble des allocataires A.L. »). Aides versées, en euros courants, non corrigées de l'inflation (aucune évolution en euros constants n'est calculée). Les causes des évolutions (réformes) ne figurent pas dans la source.",
    }


def caf():
    r = lire("logement_aides_caf_propre.csv")
    mois = sorted({x["mois"] for x in r})
    dernier = mois[-1]
    comp = [m for m in mois if m.endswith("-" + MOIS_CAF)]
    nat = []
    for m in comp:
        s = [x for x in r if x["mois"] == m]
        foy = sum(f(x["foyers_ndural"]) for x in s)
        mt = sum(f(x["montant_ndural"]) for x in s)
        pub = sum(f(x["foyers_ndural"]) for x in s if x["type_parc"] == "Parc public")
        nat.append({"mois": m, "foyers": round(foy), "montant_mensuel_m": arrondi(mt / 1e6), "moyenne": arrondi(mt / foy, 0),
                    "part_parc_public": arrondi(100 * pub / foy)})
    brut = {}
    for m in (comp[0], comp[-1]):
        s = [x for x in r if x["mois"] == m]
        brut[m] = sum(f(x["montant_ndural"]) for x in s) / sum(f(x["foyers_ndural"]) for x in s)
    moy_pct = arrondi(100 * (brut[comp[-1]] - brut[comp[0]]) / brut[comp[0]])  # sur les moyennes non arrondies
    m0 = comp[0]
    deps = defaultdict(dict)
    for x in r:
        if x["mois"] in (m0, dernier) and x["departement"] not in HORS_DEPARTEMENTS_CAF:
            o = deps[x["departement"]].setdefault(x["mois"], {"foyers": 0.0, "montant": 0.0})
            o["foyers"] += f(x["foyers_ndural"])
            o["montant"] += f(x["montant_ndural"])
            deps[x["departement"]]["nom"] = x["nom"]
    par_dep = {}
    for k, o in sorted(deps.items()):
        if m0 in o and dernier in o:
            a, b = o[m0], o[dernier]
            par_dep[k] = {"nom": o["nom"], "foyers_debut": round(a["foyers"]), "foyers_fin": round(b["foyers"]),
                          "pct_foyers": arrondi(100 * (b["foyers"] - a["foyers"]) / a["foyers"]),
                          "moyenne_fin": arrondi(b["montant"] / b["foyers"], 0)}
    return {
        "serie_mars": nat,
        "foyers": evol(nat[0]["foyers"], nat[-1]["foyers"]),
        "moyenne": {"debut": nat[0]["moyenne"], "fin": nat[-1]["moyenne"], "pct": moy_pct},
        "par_departement": par_dep,
        "territoires_en_baisse": sum(1 for o in par_dep.values() if o["pct_foyers"] < 0),
        "nb_territoires": len(par_dep),
        "periode": [m0, dernier],
        "definition": f"Cnaf (data.caf.fr, Licence Ouverte), aides au logement par département et type de parc : foyers allocataires des Caf bénéficiaires d'au moins une aide au logement dans le mois (colonne NDURAL) et montant total de prestation versée au titre du mois de droit. Comparaison des mois de mars (premier mois de mars disponible : {m0} ; dernier : {dernier}). Département de résidence (métadonnées data.caf.fr) ; territoires = départements, DROM et Saint-Martin (978). Euros courants ; pourcentage du montant moyen calculé sur les valeurs non arrondies. Les codes « 99 » et « XX » sont comptés dans le total national, pas dans le tableau. Dans 40 lignes sur 24 629, NDURAL est inférieur de 1 à 3 à la somme APL + ALS + ALF (foyers cumulant deux aides dans le mois). Ne jamais comparer des mois de décembre (Mayotte, Saint-Martin et code 99 absents de décembre 2020 à 2024).",
    }


def departements():
    p = defaultdict(dict)
    for x in lire("logement_parc_social_propre.csv"):
        p[x["departement"]][x["annee"]] = x
    so = {x["departement"]: x for x in lire("logement_sorties_propre.csv") if x["millesime"] == "2025"}
    out = []
    for dep, ans in sorted(p.items()):
        a0, a1 = ans["2013"], ans["2025"]
        mes_debut = sum(f(ans[str(a)]["mises_en_service"]) for a in (2014, 2015, 2016)) / 3
        mes_fin = sum(f(ans[str(a)]["mises_en_service"]) for a in (2023, 2024, 2025)) / 3
        s = so.get(dep, {})
        out.append({"departement": dep, "nom": a1["nom"], "parc_2013": round(f(a0["logements_sociaux"])),
                    "parc_2025": round(f(a1["logements_sociaux"])),
                    "pct_parc": arrondi(100 * (f(a1["logements_sociaux"]) - f(a0["logements_sociaux"])) / f(a0["logements_sociaux"])),
                    "mises_en_service_2013_2015": arrondi(mes_debut, 0), "mises_en_service_2022_2024": arrondi(mes_fin, 0),
                    "pct_mises_en_service": arrondi(100 * (mes_fin - mes_debut) / mes_debut) if mes_debut else None,
                    "ventes_occupant_et_autres_2024": round(f(s.get("ventes_occupant")) + f(s.get("autres_ventes"))) if s else None,
                    "demolitions_2024": round(f(s.get("demolitions"))) if s else None,
                    "taux_vacance_2025": f(a1["taux_vacance"]) if a1["taux_vacance"] != "" else None})
    baisse = [o for o in out if o["pct_mises_en_service"] is not None and o["pct_mises_en_service"] < 0]
    return {
        "departements": out,
        "deps_mises_en_service_en_baisse": len(baisse),
        "classement_baisse_mises_en_service": sorted([o for o in baisse if o["mises_en_service_2013_2015"] >= SEUIL_MES],
                                                     key=lambda o: o["pct_mises_en_service"])[:15],
        "seuil_classement": SEUIL_MES,
        "definition": "Par département (France métropolitaine) : parc social au 1er janvier 2013 et 2025 (RPLS 2025) ; mises en service annuelles moyennes, années de mise en service 2013-2015 (colonnes « au 1er janvier » 2014 à 2016) contre 2022-2024 (colonnes 2023 à 2025) ; classement limité aux départements ayant au moins 100 mises en service par an en 2013-2015 (pourcentages fragiles sur les petites bases : toujours afficher les valeurs absolues) ; ventes à l'occupant et autres ventes et démolitions de l'année 2024 (RPLS 2025) ; taux de vacance au 1er janvier 2025. Moyennes sur trois ans pour lisser les variations annuelles. Rupture de série RPLS en 2023.",
    }


def main():
    chiffres = {"parc": parc(), "sorties": sorties(), "sru": sru(), "aides": aides_compte(), "caf": caf(),
                "departements": departements()}
    with open(os.path.join(DIR, "chiffres_logement.json"), "w", encoding="utf-8") as fichier:
        json.dump(chiffres, fichier, ensure_ascii=False, indent=1)
    print(f"{len(chiffres)} blocs -> {DIR}/chiffres_logement.json")


if __name__ == "__main__":
    main()
