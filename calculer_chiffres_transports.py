"""Calcule les chiffres du rapport transports à partir de donnees_propres/transports/ (EDR-005 : tout chiffre est rejouable).

Produit donnees_propres/transports/chiffres_transports.json : séries des graphiques + chiffres clés, chacun avec sa définition.
Usage : python3 calculer_chiffres_transports.py
"""
import csv
import json
import os
from collections import defaultdict

DIR = "donnees_propres/transports"
csv.field_size_limit(10 ** 9)
ANNEES_TER = [str(a) for a in range(2017, 2026)]  # périmètre complet (Grand Est complet à partir de 2017), années entières


def lire(nom):
    with open(os.path.join(DIR, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def evol(a, b):
    return {"debut": a, "fin": b, "ecart": b - a, "pct": round(100 * (b - a) / a, 1)}


def f(v):
    return float(v) if v not in ("", None) else 0.0


def ter():
    r = [x for x in lire("transports_ter_propre.csv") if x["trains_programmes"]]
    t = defaultdict(lambda: defaultdict(float))
    reg = defaultdict(lambda: defaultdict(float))
    for x in r:
        a = x["annee"]
        for k in ("trains_programmes", "trains_circules", "trains_supprimes", "trains_en_retard"):
            t[a][k] += f(x[k])
            reg[(x["region"], a)][k] += f(x[k])
    serie = []
    for a in ANNEES_TER:
        s = t[a]
        serie.append({"annee": a, "programmes": round(s["trains_programmes"]), "supprimes": round(s["trains_supprimes"]),
                      "taux_suppression": round(100 * s["trains_supprimes"] / s["trains_programmes"], 2),
                      "regularite": round(100 * (1 - s["trains_en_retard"] / s["trains_circules"]), 1)})
    regions = []
    for region in sorted({x["region"] for x in r}):
        d, fin = reg[(region, ANNEES_TER[0])], reg[(region, ANNEES_TER[-1])]
        regions.append({"region": region, "programmes_debut": round(d["trains_programmes"]), "programmes_fin": round(fin["trains_programmes"]),
                        "pct_offre": round(100 * (fin["trains_programmes"] - d["trains_programmes"]) / d["trains_programmes"], 1),
                        "taux_suppression_fin": round(100 * fin["trains_supprimes"] / fin["trains_programmes"], 2),
                        "regularite_fin": round(100 * (1 - fin["trains_en_retard"] / fin["trains_circules"]), 1)})
    regions.sort(key=lambda o: -o["taux_suppression_fin"])
    return {
        "serie": serie,
        "programmes": evol(serie[0]["programmes"], serie[-1]["programmes"]),
        "supprimes": evol(serie[0]["supprimes"], serie[-1]["supprimes"]),
        "regions": regions,
        "periode": [ANNEES_TER[0], ANNEES_TER[-1]],
        "definition": "Trains TER programmés, supprimés et en retard (plus de 5 minutes au terminus), 11 régions (hors Île-de-France et Corse), données SNCF agrégées par région actuelle ; périmètre complet à partir de 2017. Un train supprimé avant 16 h la veille n'est compté ni comme programmé ni comme supprimé. Régularité = 1 − trains en retard / trains ayant circulé. Certaines années (voir ecart_programmes_circules_supprimes), la somme des trains ayant circulé et supprimés dépasse les trains programmés (suppressions partielles probablement comptées deux fois). Les Intercités transférés aux régions sont comptés en TER après leur transfert.",
        "ecart_programmes_circules_supprimes": {a: round(t[a]["trains_circules"] + t[a]["trains_supprimes"] - t[a]["trains_programmes"]) for a in ANNEES_TER},
    }


def ter_finances():
    r = [x for x in lire("transports_ter_art_propre.csv") if x["niveau"] == "total" and x["valeur"] != ""]
    v = {(x["annee"], x["indicateur"]): float(x["valeur"]) for x in r}
    annees = sorted({a for a, i in v if (a, "Contributions publiques versées aux EF") in v and (a, "Total") in v})
    serie = []
    for a in annees:
        contrib, recettes, charges = v[(a, "Contributions publiques versées aux EF")], v[(a, "Recettes directes issues du trafic")], v[(a, "Total")]
        serie.append({"annee": a, "contributions_md": round(contrib / 1e9, 2), "recettes_md": round(recettes / 1e9, 2),
                      "charges_md": round(charges / 1e9, 2), "pkt_md": round(v[(a, "Passagers.km transportés (PKT)")] / 1e9, 1),
                      "trains_km_m": round(v[(a, "Trains.km commerciaux (TKM)")] / 1e6, 1),
                      "part_contributions": round(100 * contrib / charges, 1), "part_recettes": round(100 * recettes / charges, 1)})
    a0, a1 = annees[0], annees[-1]

    def evol_brute(ind, div, k):
        e = evol(v[(a0, ind)], v[(a1, ind)])
        return {"debut": round(e["debut"] / div, k), "fin": round(e["fin"] / div, k), "ecart": round(e["ecart"] / div, k), "pct": e["pct"]}

    return {
        "serie": serie,
        "contributions": evol_brute("Contributions publiques versées aux EF", 1e9, 2),
        "recettes": evol_brute("Recettes directes issues du trafic", 1e9, 2),
        "pkt": evol_brute("Passagers.km transportés (PKT)", 1e9, 1),
        "trains_km": evol_brute("Trains.km commerciaux (TKM)", 1e6, 1),
        "periode": [annees[0], annees[-1]],
        "definition": "ART, données du transport ferroviaire, onglet « 9.1 - Offre, Freq, REF TER », ligne « Total TER » : contributions publiques versées aux entreprises ferroviaires, recettes directes du trafic, charges d'exploitation totales (euros courants), passagers.km et trains.km. Parts = contributions (ou recettes) rapportées aux charges d'exploitation ; elles ne s'additionnent pas à 100 %. Évolutions calculées sur les valeurs non arrondies. 2025 exclue (données incomplètes dans la source).",
    }


def grandes_lignes():
    ic = defaultdict(float)
    liaisons = defaultdict(set)
    for x in lire("transports_intercites_propre.csv"):
        if x["trains_programmes"]:
            ic[x["annee"]] += f(x["trains_programmes"])
            liaisons[x["annee"]].add((x["depart"], x["arrivee"]))
    annees_ic = [a for a in sorted(ic) if len({x for x in lire_mois_ic() if x[0] == a}) == 12]
    panel = set.intersection(*(liaisons[a] for a in annees_ic))
    ic_panel = defaultdict(float)
    for x in lire("transports_intercites_propre.csv"):
        if x["trains_programmes"] and (x["depart"], x["arrivee"]) in panel:
            ic_panel[x["annee"]] += f(x["trains_programmes"])
    tgv = defaultdict(list)
    for x in lire("transports_tgv_propre.csv"):
        if x["regularite_composite"]:
            tgv[x["annee"]].append(float(x["regularite_composite"]))
    annees_tgv = [a for a in sorted(tgv) if len(tgv[a]) == 12]
    return {
        "intercites": [{"annee": a, "programmes": round(ic[a]), "programmes_relations_constantes": round(ic_panel[a])} for a in annees_ic],
        "intercites_evol": evol(round(ic[annees_ic[0]]), round(ic[annees_ic[-1]])),
        "intercites_relations_constantes": {"nombre": len(panel), "evol": evol(round(ic_panel[annees_ic[0]]), round(ic_panel[annees_ic[-1]]))},
        "tgv_regularite": [{"annee": a, "regularite": round(sum(tgv[a]) / 12, 1)} for a in annees_tgv],
        "definition": "Intercités : trains programmés par an sur la sélection de relations suivie par l'AQST (années complètes), et sur les relations (orientées) présentes chaque année ; une partie des lignes Intercités a été transférée aux régions, ce qui réduit mécaniquement le total. TGV : moyenne annuelle de la régularité composite mensuelle publiée par SNCF (années complètes).",
    }


_MOIS_IC = None


def lire_mois_ic():
    global _MOIS_IC
    if _MOIS_IC is None:
        _MOIS_IC = {(x["annee"], x["date"]) for x in lire("transports_intercites_propre.csv") if x["trains_programmes"]}
    return _MOIS_IC


def effectifs():
    t = defaultdict(float)
    for x in lire("transports_effectifs_sncf_propre.csv"):
        if x["effectif"]:
            t[(x["annee"], x["contrat"])] += float(x["effectif"])
    annees = sorted({a for a, _ in t})
    serie = [{"annee": a, "statut": round(t[(a, "Agents au statut")]), "contractuels": round(t[(a, "Agents contractuels")]),
              "part_contractuels": round(100 * t[(a, "Agents contractuels")] / (t[(a, "Agents au statut")] + t[(a, "Agents contractuels")]), 1)}
             for a in annees]
    base = [s_ for s_ in serie if s_["annee"] >= "2022"]
    return {
        "serie": base,
        "statut": evol(base[0]["statut"], base[-1]["statut"]),
        "contractuels": evol(base[0]["contractuels"], base[-1]["contractuels"]),
        "annees_avec_anomalies": sorted({x["annee"] for x in lire("transports_effectifs_sncf_propre.csv") if x["anomalies"]}),
        "periode": [base[0]["annee"], base[-1]["annee"]],
        "definition": "Effectifs de la SNCF au 31 décembre (bilan social, hors contrats aidés), agents au statut (cadre permanent) et contractuels de droit commun. Comparaison limitée à 2022-2024 : de 2015 à 2021, la source présente des tranches d'âge manquantes, des tranches en double et une valeur atypique ; à partir de 2019, effectifs totaux et non plus « réels ».",
    }


def gares():
    r = lire("transports_gares_propre.csv")
    annees = [str(a) for a in range(2015, 2025)]
    seg = defaultdict(lambda: defaultdict(float))
    nb = defaultdict(int)
    for x in r:
        s = x["segment"] or "non renseigné"
        nb[s] += 1
        for a in annees:
            seg[s][a] += f(x[f"voyageurs_{a}"])
    segments = {s: [round(seg[s][a]) for a in annees] for s in ("A", "B", "C")}
    total = [round(sum(seg[s][a] for s in seg)) for a in annees]
    c24 = sorted(f(x["voyageurs_2024"]) for x in r if x["segment"] == "C")
    b_hors_idf = [x for x in r if x["segment"] == "B" and x["type_gare"] != "IDF"]
    b19, b24 = sum(f(x["voyageurs_2019"]) for x in b_hors_idf), sum(f(x["voyageurs_2024"]) for x in b_hors_idf)
    return {
        "annees": annees,
        "voyageurs_par_segment": segments,
        "voyageurs_total": total,
        "nb_gares": dict(nb),
        "evol_2019_2024": {s: evol(segments[s][annees.index("2019")], segments[s][-1]) for s in segments},
        "part_c_gares": round(100 * nb["C"] / len(r), 1),
        "part_c_voyageurs_2024": round(100 * segments["C"][-1] / total[-1], 1),
        "gares_c_moins_de_100_par_jour": sum(1 for v in c24 if v < 36500),
        "evol_b_hors_idf_2019_2024": evol(round(b19), round(b24)),
        "part_idf_voyageurs_b_2024": round(100 * (segments["B"][-1] - b24) / segments["B"][-1], 1),
        "definition": "Voyageurs annuels par gare (SNCF Gares & Connexions), hors non-voyageurs. Segments SNCF : A = gares nationales, B = régionales, C = locales (le segment ne recoupe pas exactement le type « halte »). « Moins de 100 voyageurs par jour » = moins de 36 500 voyageurs en 2024 (moyenne annuelle). Billetterie hors ventes par des tiers ; trafic Île-de-France extrapolé à partir de comptages (l'essentiel des voyageurs du segment B). Méthode révisée chaque année par SNCF (historique repris).",
    }


def reseau():
    groupes = {
        "Exploitée": "Exploitées", "S9A3 - Ligne en travaux": "Exploitées",
        "Neutralisée": "Neutralisées", "Neutralisée et conservée pour les besoins de la Défense": "Neutralisées",
        "Transférée en voie de service": "Transférées en voies de service",
    }
    km = defaultdict(float)
    for x in lire("transports_lignes_propre.csv"):
        if x["longueur_km"] == "":
            continue
        g = groupes.get(x["statut"], "Fermées, retranchées ou déclassées" if x["statut"] != "Projet" else "Projet")
        km[g] += float(x["longueur_km"])
    total = sum(km.values())
    return {
        "km": {g: round(v) for g, v in sorted(km.items(), key=lambda kv: -kv[1])},
        "total_km": round(total),
        "part_non_exploitee": round(100 * (total - km["Exploitées"]) / total, 1),
        "km_non_exploites": round(total - km["Exploitées"]),
        "definition": "Longueur des lignes recensées par SNCF Réseau selon leur statut (« Lignes par statut », traitement du 26/02/2026), calculée à partir des points kilométriques de début et de fin (approximation). Lignes en travaux comptées comme exploitées ; deux tronçons aux points kilométriques illisibles exclus ; « neutralisée » n'est pas « fermée ». Photographie à une date : ne dit pas quand les lignes ont été fermées.",
    }


def guichets():
    pv = defaultdict(set)
    for x in lire("transports_points_vente_propre.csv"):
        pv[x["code_uic"]].add(x["type_point_vente"])
    idf = ("75", "77", "78", "91", "92", "93", "94", "95")
    hors_idf = [x for x in lire("transports_gares_propre.csv") if x["type_gare"] != "IDF" and x["departement"] not in idf]
    avec_guichet = sum(1 for x in hors_idf if "Poste de vente guichet" in pv.get(x["code_uic"], set()))
    automates = sum(1 for x in hors_idf if pv.get(x["code_uic"]) and "Poste de vente guichet" not in pv[x["code_uic"]])
    aucun = len(hors_idf) - avec_guichet - automates
    par_type = defaultdict(lambda: [0, 0])
    for x in hors_idf:
        t = x["type_gare"] or "non renseigné"
        par_type[t][1] += 1
        par_type[t][0] += "Poste de vente guichet" in pv.get(x["code_uic"], set())
    return {
        "gares_hors_idf": len(hors_idf),
        "avec_guichet": avec_guichet, "automates_seuls": automates, "aucun_point_vente": aucun,
        "part_avec_guichet": round(100 * avec_guichet / len(hors_idf), 1),
        "part_sans_guichet": round(100 - 100 * avec_guichet / len(hors_idf), 1),
        "par_type": {t: {"gares": v[1], "avec_guichet": v[0], "part": round(100 * v[0] / v[1], 1)} for t, v in par_type.items()},
        "definition": "Gares voyageurs situées hors Île-de-France (type et code postal) de la liste de fréquentation SNCF, rapprochées par code UIC des points de vente SNCF (guichets et automates, hors Transilien ; jeu mis en ligne en janvier 2026, données traitées en février 2024). Sans point de vente répertorié sous ce code UIC ; quelques appariements peuvent échouer. Photographie à une date.",
    }


def autocars():
    v = defaultdict(dict)
    for x in lire("transports_autocars_propre.csv"):
        if x["valeur"] != "" and "annee_partielle" not in x["anomalies"]:
            v[x["annee"]][x["indicateur"]] = float(x["valeur"])
    annees = sorted(v)
    cle_freq = next(k for k in v[annees[-1]] if k.startswith("Fréquentation totale"))
    serie = [{"annee": a, "passagers_m": round(v[a][cle_freq] / 1e6, 1), "liaisons": round(v[a]["Liaisons commercialisées"]),
              "villes": round(v[a]["Nombre d'unités urbaines desservies"])} for a in annees]
    return {
        "serie": serie,
        "passagers": evol(serie[1]["passagers_m"], serie[-1]["passagers_m"]),
        "periode": [annees[0], annees[-1]],
        "definition": "Autocars librement organisés (« cars Macron »), ART : fréquentation totale (liaisons domestiques et internationales), liaisons commercialisées, unités urbaines desservies. 2015 = année d'ouverture (août), comparaison à partir de 2016. 2026 exclue (mi-année).",
    }


def urbain():
    v = defaultdict(dict)
    for x in lire("transports_tcu_propre.csv"):
        if x["valeur"] != "":
            v[(x["reseau_id"], x["variable"])][x["annee"]] = float(x["valeur"])
    annees = [str(a) for a in range(2005, 2017)]
    panel = sorted({r for (r, var) in v if all(a in v.get((r, "voyages_milliers"), {}) and a in v.get((r, "km_offerts"), {}) for a in annees)})
    voy = [sum(v[(r, "voyages_milliers")][a] for r in panel) / 1000 for a in annees]
    km = [sum(v[(r, "km_offerts")][a] for r in panel) / 1e6 for a in annees]
    return {
        "annees": annees,
        "nb_reseaux": len(panel),
        "voyages_m": [round(x, 1) for x in voy],
        "km_m": [round(x, 1) for x in km],
        "voyages": evol(round(voy[0], 1), round(voy[-1], 1)),
        "km": evol(round(km[0], 1), round(km[-1], 1)),
        "definition": "Enquête nationale sur les transports collectifs urbains (Cerema, hors Île-de-France), panel constant des réseaux ayant déclaré voyages et kilomètres offerts chaque année de 2005 à 2016 ; déclarations des exploitants uniquement (plusieurs exploitants d'un réseau additionnés ; déclarations de sous-traitants ignorées). Données publiées jusqu'en 2016 (quelques valeurs 2017 seulement).",
    }


def fiabilite():
    v = defaultdict(dict)
    for x in lire("transports_fiabilite_art_propre.csv"):
        if x["valeur"] != "":
            v[(x["service"], x["annee"])][x["indicateur"]] = float(x["valeur"])
    res = {}
    for service in ("TER", "Transilien", "Intercités"):
        annees = sorted(a for (sv, a) in v if sv == service and "Trains programmés" in v[(sv, a)]
                        and 'Annulations "de dernière minute"' in v[(sv, a)])
        serie = []
        for a in annees:
            x = v[(service, a)]
            prog, deprog, annul = x["Trains programmés"], x["Déprogrammations"], x['Annulations "de dernière minute"']
            totales = x['dont annulations totales "de dernière minute"']
            serie.append({"annee": a, "programmes_jour": round(prog, 1), "deprogrammes_jour": round(deprog, 1),
                          "annules_derniere_minute_jour": round(annul, 1), "annules_totaux_jour": round(totales, 1),
                          "part_non_circules": round(100 * (deprog + totales) / prog, 2),
                          "part_annules_derniere_minute": round(100 * annul / prog, 2)})
        x0, x1 = v[(service, annees[0])], v[(service, annees[-1])]
        e = evol(x0['Annulations "de dernière minute"'], x1['Annulations "de dernière minute"'])
        res[service] = {"serie": serie,
                        "annules_derniere_minute": {"debut": round(e["debut"], 1), "fin": round(e["fin"], 1),
                                                    "ecart": round(e["ecart"], 1), "pct": e["pct"]},
                        "programmes": {k: (round(w, 1) if k != "pct" else w) for k, w in evol(x0["Trains programmés"], x1["Trains programmés"]).items()},
                        "taux_annules_derniere_minute": {"debut": serie[0]["part_annules_derniere_minute"],
                                                         "fin": serie[-1]["part_annules_derniere_minute"]},
                        "periode": [serie[0]["annee"], serie[-1]["annee"]]}
    return {
        "par_service": res,
        "definition": "ART, données du transport ferroviaire, onglet « 8.1 - Fiabilité » : moyennes de trains par jour. Déprogrammations = trains retirés du plan de transport avant la veille 16 h (non comptés par la statistique de régularité SNCF) ; annulations de dernière minute = trains prévus la veille à 16 h puis supprimés, totalement ou partiellement. Part non circulés = (déprogrammations + annulations totales) / trains programmés ; part annulée au dernier moment = annulations de dernière minute / trains programmés (même dénominateur que l'ART). Évolutions calculées sur les valeurs non arrondies. Les déprogrammations comprennent aussi des retraits prévus (travaux). Années atypiques : 2017 (valeur TER anormalement basse), 2018, 2019 et 2023 (grèves), 2020 et 2021 (crise sanitaire). Intercités : offre fortement réduite par les transferts aux régions, comparer les taux plutôt que les volumes.",
    }


def dessertes():
    r = lire("transports_dessertes_gares_propre.csv")
    par = defaultdict(dict)
    for x in r:
        if x["dessertes"] != "":
            par[x["code_ci"]][x["annee"]] = (float(x["dessertes"]), x["segment"], float(x["dessertes_ter_intercites"] or 0))
    annees = sorted({x["annee"] for x in r})
    a0, a1 = annees[0], annees[-1]
    deux = {g: d for g, d in par.items() if a0 in d and a1 in d}
    total = {a: round(sum(d[a][0] for d in deux.values() if a in d)) for a in annees}
    seg = defaultdict(lambda: [0.0, 0.0])
    baisse = defaultdict(int)
    nb_seg = defaultdict(int)
    plus10 = sum(1 for d in deux.values() if d[a0][0] and d[a1][0] < 0.9 * d[a0][0])
    plus20 = sum(1 for d in deux.values() if d[a0][0] and d[a1][0] < 0.8 * d[a0][0])
    hausse = sum(1 for d in deux.values() if d[a1][0] > d[a0][0])
    sorties = sum(1 for d in par.values() if a0 in d and a1 not in d)
    for g, d in deux.items():
        s_ = d[a1][1] or "non renseigné"
        seg[s_][0] += d[a0][2]
        seg[s_][1] += d[a1][2]
        nb_seg[s_] += 1
        if d[a1][0] < d[a0][0]:
            baisse[s_] += 1
    return {
        "annees": annees,
        "gares_suivies": len(deux),
        "dessertes_total": total,
        "gares_en_baisse": sum(baisse.values()),
        "part_gares_en_baisse": round(100 * sum(baisse.values()) / len(deux), 1),
        "gares_en_baisse_plus_10pct": plus10, "gares_en_baisse_plus_20pct": plus20, "gares_en_hausse": hausse,
        "gares_absentes_fin": sorties,
        "dessertes_total_evol": evol(total[a0], total[a1]),
        "par_segment": {s_: {"gares": nb_seg[s_], "en_baisse": baisse[s_],
                              "dessertes_ter_ic": evol(round(seg[s_][0]), round(seg[s_][1]))} for s_ in sorted(seg)},
        "definition": "ART, onglet « 6.1 - Gares » : nombre de dessertes (arrêts de trains) par gare et par an, gares présentes en 2019 et en 2023 ; dessertes TER et Intercités par segment (A nationales, B régionales, C locales ; « B IDF » et « TGA » : libellés de l'ART non définis dans son glossaire, présentés tels quels ; segment de 2023). Les gares présentes en 2019 mais absentes en 2023 sont hors du calcul (voir gares_absentes_fin). Le total des dessertes augmente : la baisse dans une partie des gares traduit une concentration de l'offre, pas une baisse globale. 2020-2021 marquées par la crise sanitaire.",
    }


def gares_departements():
    pv = defaultdict(set)
    for x in lire("transports_points_vente_propre.csv"):
        pv[x["code_uic"]].add(x["type_point_vente"])
    idf = ("75", "77", "78", "91", "92", "93", "94", "95")
    d = defaultdict(lambda: {"gares": 0, "avec_guichet": 0, "v2019": 0.0, "v2024": 0.0, "gares_c": 0})
    for x in lire("transports_gares_propre.csv"):
        dep = x["departement"]
        o = d[dep]
        o["gares"] += 1
        o["avec_guichet"] += "Poste de vente guichet" in pv.get(x["code_uic"], set())
        o["v2019"] += f(x["voyageurs_2019"])
        o["v2024"] += f(x["voyageurs_2024"])
        o["gares_c"] += x["segment"] == "C"
    out = []
    for dep, o in sorted(d.items()):
        if dep == "98":  # Monaco (code postal 98000) : hors France
            continue
        out.append({"departement": dep, "gares": o["gares"], "avec_guichet": o["avec_guichet"],
                    "part_sans_guichet": round(100 - 100 * o["avec_guichet"] / o["gares"], 1),
                    "ile_de_france": dep in idf,
                    "voyageurs_2019": round(o["v2019"]), "voyageurs_2024": round(o["v2024"]),
                    "pct_voyageurs": round(100 * (o["v2024"] - o["v2019"]) / o["v2019"], 1) if o["v2019"] else None})
    hors = [o for o in out if not o["ile_de_france"] and o["gares"] >= 10]
    return {
        "departements": out,
        "classement_sans_guichet": sorted(hors, key=lambda o: -o["part_sans_guichet"]),
        "deps_majorite_sans_guichet": sum(1 for o in hors if o["part_sans_guichet"] > 50),
        "nb_deps_classes": len(hors),
        "definition": "Gares voyageurs SNCF par département (code postal de la gare) rapprochées des points de vente SNCF par code UIC (guichets hors Transilien) ; classement limité aux départements hors Île-de-France comptant au moins 10 gares ; gare de Monaco exclue. Photographie (points de vente traités en février 2024) : ne dit pas combien de guichets ont fermé ; « sans guichet » ne veut pas dire sans automate. Voyageurs comptés par SNCF (billetterie, trafic francilien extrapolé).",
    }


PETITES_LIGNES = {"7 à 9 AV": "avec voyageurs", "7 à 9 SV": "sans voyageurs"}


def reseau_evolution():
    """Longueur du réseau ferré national (km de lignes) par année : total, réseau classique SNCF Réseau, petites lignes, régions."""
    total, classique, petites, regions = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for x in lire("transports_reseau_rfn_propre.csv"):
        if x["km_ligne"] == "":
            continue
        a, km = x["annee"], float(x["km_ligne"])
        total[a] += km
        if x["gestionnaire"] == "SNCF Réseau" and x["categorie_ligne"] != "LGV":
            classique[a] += km
            regions[(x["region"], a)] += km
        if x["categorie_ligne"] in PETITES_LIGNES:
            petites[(PETITES_LIGNES[x["categorie_ligne"]], a)] += km
    annees = sorted(total)
    a0, a1 = annees[0], annees[-1]

    def ev(d, k0, k1):
        e = evol(d[k0], d[k1])
        return {"debut": round(e["debut"]), "fin": round(e["fin"]), "ecart": round(e["ecart"]), "pct": e["pct"]}

    par_region = sorted(({"region": r, **ev(regions, (r, a0), (r, a1))} for r in sorted({r for r, _ in regions})
                         if (r, a0) in regions and (r, a1) in regions), key=lambda o: o["ecart"])
    return {
        "serie": [{"annee": a, "total_km": round(total[a]), "classique_km": round(classique[a]),
                   "petites_av_km": round(petites[("avec voyageurs", a)]), "petites_sv_km": round(petites[("sans voyageurs", a)])} for a in annees],
        "total": ev(total, a0, a1),
        "classique": ev(classique, a0, a1),
        "petites_lignes_sans_voyageurs": ev(petites, ("sans voyageurs", a0), ("sans voyageurs", a1)),
        "part_sans_voyageurs_dans_baisse_classique": round(100 * (petites[("sans voyageurs", a1)] - petites[("sans voyageurs", a0)])
                                                           / (classique[a1] - classique[a0]), 1),
        "petites_lignes_avec_voyageurs_non_comparable": ev(petites, ("avec voyageurs", a0), ("avec voyageurs", a1)),  # reclassements : ne pas interpréter
        "par_region": par_region,
        "periode": [a0, a1],
        "definition": "ART, données du transport ferroviaire, onglet « 1.1 - RFN » : longueur du réseau ferré national en km de lignes au 31 décembre de chaque année, par « gestionnaire de la maintenance » (SNCF Réseau et trois concessionnaires de LGV) ; une ligne dont la gestion est transférée à une région peut sortir de ce périmètre sans être fermée. Selon l'ART, les indicateurs ne couvrent pas l'ensemble du réseau en 2018. Périmètre et méthode différents du jeu « lignes par statut » de SNCF Réseau (longueurs approchées par points kilométriques), d'où des longueurs non comparables entre les deux sources. Total = tous gestionnaires (dont les lignes à grande vitesse concédées LISEA, OCVIA et ERE, présentes à partir de 2017) ; réseau classique = lignes gérées par SNCF Réseau hors LGV ; petites lignes = catégories UIC 7 à 9 ; la longueur des petites lignes avec voyageurs n'est pas comparable dans le temps (lignes reclassées depuis ou vers les catégories 5-6), celle des lignes sans voyageurs l'est davantage. La catégorie dépend du trafic supporté : une ligne peut changer de catégorie d'une année à l'autre (reclassement important en 2022 entre catégories 2-4 et 5-6), seules la longueur totale et celle du réseau classique sont comparables dans le temps. La source ne dit ni quelles lignes sont sorties du réseau ni pourquoi : fermeture, déclassement ou transfert hors du réseau ferré national (la loi d'orientation des mobilités de 2019 permet le transfert de petites lignes aux régions) ; « sortie du réseau ferré national » n'est donc pas synonyme de « fermée ». Régions : découpage actuel (anciennes régions additionnées).",
    }


def frequentation_offre():
    """TER : fréquentation (passagers.km) rapportée à l'offre (trains.km, sièges.km) et taux d'occupation, ART 9.1, ligne « Total TER »."""
    v = {(x["annee"], x["indicateur"]): float(x["valeur"]) for x in lire("transports_ter_art_propre.csv")
         if x["niveau"] == "total" and x["valeur"] != ""}
    pkt, tkm, sko = "Passagers.km transportés (PKT)", "Trains.km commerciaux (TKM)", "Sièges.km offerts (SKO)"
    annees = sorted(a for a in {a for a, _ in v} if all((a, i) in v for i in (pkt, tkm, sko)))
    a0, a1 = annees[0], annees[-1]
    return {
        "serie": [{"annee": a, "indice_pkt": round(100 * v[(a, pkt)] / v[(a0, pkt)], 1), "indice_trains_km": round(100 * v[(a, tkm)] / v[(a0, tkm)], 1),
                   "indice_sieges_km": round(100 * v[(a, sko)] / v[(a0, sko)], 1), "taux_occupation": round(100 * v[(a, pkt)] / v[(a, sko)], 1)}
                  for a in annees],
        "pkt": evol(v[(a0, pkt)], v[(a1, pkt)])["pct"],
        "trains_km": evol(v[(a0, tkm)], v[(a1, tkm)])["pct"],
        "sieges_km": evol(v[(a0, sko)], v[(a1, sko)])["pct"],
        "taux_occupation": {"debut": round(100 * v[(a0, pkt)] / v[(a0, sko)], 1), "fin": round(100 * v[(a1, pkt)] / v[(a1, sko)], 1)},
        "periode": [a0, a1],
        "definition": "ART, onglet « 9.1 - Offre, Freq, REF TER », ligne « Total TER » (hors Transilien) : passagers.km transportés, trains.km commerciaux, sièges.km offerts ; taux d'occupation = passagers.km / sièges.km (définition ART) ; indices base 100 en première année. 2025 exclue (fréquentation non disponible). Nombre de voyages non retenu : distance moyenne quasi constante de 2015 à 2020 (passagers vraisemblablement estimés à partir des passagers-km), rupture en 2021. Limites : Intercités transférés aux régions entre 2017 et 2020 comptés en TER, ce qui gonfle à la fois l'offre et la fréquentation ; 2020-2021 marquées par la crise sanitaire ; taux d'occupation moyen sur toute la journée et tout le réseau, il ne mesure pas la saturation aux heures de pointe.",
    }


def main():
    chiffres = {"ter": ter(), "ter_finances": ter_finances(), "grandes_lignes": grandes_lignes(), "effectifs": effectifs(),
                "gares": gares(), "reseau": reseau(), "guichets": guichets(), "autocars": autocars(), "urbain": urbain(),
                "fiabilite": fiabilite(), "dessertes": dessertes(), "gares_departements": gares_departements(),
                "reseau_evolution": reseau_evolution(), "frequentation_offre": frequentation_offre()}
    with open(os.path.join(DIR, "chiffres_transports.json"), "w", encoding="utf-8") as fichier:
        json.dump(chiffres, fichier, ensure_ascii=False, indent=1)
    print(f"{len(chiffres)} blocs -> {DIR}/chiffres_transports.json")


if __name__ == "__main__":
    main()
