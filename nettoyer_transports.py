"""Nettoyage des données sur les transports publics (EDR-020).

Sources : donnees_brutes/transports/ (SNCF Open Data sous licence ODbL, ART et Cerema sous Licence Ouverte).
Produit dans donnees_propres/transports/ :
- transports_ter_propre.csv           : 1 ligne = 1 région source x 1 mois (régularité et suppressions TER)
- transports_intercites_propre.csv    : 1 ligne = 1 liaison Intercités x 1 mois
- transports_tgv_propre.csv           : 1 ligne = 1 mois (régularité TGV nationale)
- transports_effectifs_sncf_propre.csv : 1 ligne = 1 année x contrat x collège x tranche d'âge
- transports_gares_propre.csv         : 1 ligne = 1 gare (voyageurs 2015-2024)
- transports_lignes_propre.csv        : 1 ligne = 1 portion de ligne du réseau ferré national (statut, longueur)
- transports_points_vente_propre.csv  : 1 ligne = 1 point de vente en gare (guichet ou automate)
- transports_reseau_rfn_propre.csv     : 1 ligne = 1 année x région x gestionnaire x catégorie de lignes (longueur du réseau, ART)
- transports_ter_art_propre.csv       : 1 ligne = 1 année x région x indicateur (offre, fréquentation, finances TER, ART)
- transports_autocars_propre.csv      : 1 ligne = 1 année x indicateur (autocars librement organisés, ART)
- transports_tcu_propre.csv           : 1 ligne = 1 réseau urbain x 1 année x variable (enquête TCU, Cerema)
- transports_fiabilite_art_propre.csv : 1 ligne = 1 année x service x indicateur (trains par jour : programmés, déprogrammés, annulés, ART)
- transports_dessertes_gares_propre.csv : 1 ligne = 1 gare x 1 année (fréquentation et dessertes, ART, 2019-2023)
"""
import csv
import io
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from lecture_xlsx import lignes_xlsx  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "donnees_brutes/transports"
OUT = "donnees_propres/transports"
csv.field_size_limit(10 ** 9)  # le fichier des lignes contient des géométries très longues

# Régions TER : anciennes régions et lots de lignes rattachés à la région administrative actuelle
REGIONS_TER = {
    "Alsace": "Grand Est", "Lorraine": "Grand Est", "Champagne Ardenne": "Grand Est", "Grand Est": "Grand Est",
    "Aquitaine": "Nouvelle-Aquitaine", "Limousin": "Nouvelle-Aquitaine", "Poitou Charentes": "Nouvelle-Aquitaine",
    "Nouvelle Aquitaine": "Nouvelle-Aquitaine",
    "Auvergne": "Auvergne-Rhône-Alpes", "Rhône Alpes": "Auvergne-Rhône-Alpes", "Auvergne-Rhône-Alpes": "Auvergne-Rhône-Alpes",
    "Bourgogne": "Bourgogne-Franche-Comté", "Franche Comté": "Bourgogne-Franche-Comté",
    "Bourgogne-Franche-Comté": "Bourgogne-Franche-Comté",
    "Basse Normandie": "Normandie", "Haute Normandie": "Normandie", "Normandie": "Normandie",
    "Nord Pas de Calais": "Hauts-de-France", "Picardie": "Hauts-de-France", "Hauts-de-France": "Hauts-de-France",
    "Etoile Amiens": "Hauts-de-France",
    "Midi Pyrénées": "Occitanie", "Languedoc Roussillon": "Occitanie", "Occitanie": "Occitanie",
    "Centre": "Centre-Val de Loire", "Centre Val-de-Loire": "Centre-Val de Loire",
    "Pays-de-la-Loire": "Pays de la Loire", "Loire Océan": "Pays de la Loire",
    "Provence Alpes Côte d'Azur": "Provence-Alpes-Côte d'Azur", "Sud Azur": "Provence-Alpes-Côte d'Azur",
    "Bretagne": "Bretagne",
}
# Lots de lignes publiés séparément à partir de 2025
LOTS_TER = {"Etoile Amiens", "Loire Océan", "Sud Azur"}
TYPE_EXPLOITANT_TCU = "2"  # 1 = autorité organisatrice, 2 = exploitant, 6 = sous-traitants et lots
VARIABLES_TCU = {"504": "voyages_milliers", "2201": "km_offerts"}


def lire_csv(chemin, sep=";", encodage="utf-8-sig"):
    with open(os.path.join(SRC, chemin), encoding=encodage, newline="") as f:
        return list(csv.DictReader(f, delimiter=sep))


def ecrire(nom, lignes):
    with open(os.path.join(OUT, nom), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes):>6} lignes -> {nom}")


def nombre(v):
    v = (v or "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def ter():
    r = lire_csv("sncf/regularite-mensuelle-ter.csv")
    # Grand Est : la Lorraine ne transmet pas ses données avant 2017 (sauf 2015-2016 partiel)
    lorraine = {x["date"] for x in r if x["region"] == "Lorraine" and x["nombre_de_trains_programmes"]}
    out = []
    for x in r:
        reg = x["region"]
        anomalies = []
        if not x["nombre_de_trains_programmes"]:
            anomalies.append("valeurs_manquantes")
        if REGIONS_TER[reg] == "Grand Est" and x["date"] < "2017-01" and x["date"] not in lorraine:
            anomalies.append("perimetre_grand_est_incomplet")
        # Le rattachement à la région actuelle est tracé par les colonnes region_source / region (pas une anomalie)
        out.append({
            "date": x["date"], "annee": x["date"][:4], "mois": x["date"][5:7],
            "region_source": reg, "region": REGIONS_TER[reg], "lot": "oui" if reg in LOTS_TER else "non",
            "trains_programmes": nombre(x["nombre_de_trains_programmes"]) if x["nombre_de_trains_programmes"] else "",
            "trains_circules": nombre(x["nombre_de_trains_ayant_circule"]) if x["nombre_de_trains_ayant_circule"] else "",
            "trains_supprimes": nombre(x["nombre_de_trains_annules"]) if x["nombre_de_trains_annules"] else "",
            "trains_en_retard": nombre(x["nombre_de_trains_en_retard_a_l_arrivee"]) if x["nombre_de_trains_en_retard_a_l_arrivee"] else "",
            "taux_regularite": nombre(x["taux_de_regularite"]) if x["taux_de_regularite"] else "",
            "commentaires": re.sub(r"\s+", " ", x["commentaires"] or "").strip(),
            "anomalies": ";".join(anomalies),
        })
    out.sort(key=lambda o: (o["date"], o["region"], o["region_source"]))
    ecrire("transports_ter_propre.csv", out)


def intercites_tgv():
    out = []
    for x in lire_csv("sncf/regularite-mensuelle-intercites.csv"):
        manque = not x["nombre_de_trains_programmes"]
        out.append({
            "date": x["date"], "annee": x["date"][:4], "depart": x["depart"], "arrivee": x["arrivee"],
            "trains_programmes": nombre(x["nombre_de_trains_programmes"]) if not manque else "",
            "trains_circules": nombre(x["nombre_de_trains_ayant_circule"]) if not manque else "",
            "trains_supprimes": nombre(x["nombre_de_trains_annules"]) if not manque else "",
            "trains_en_retard": nombre(x["nombre_de_trains_en_retard_a_l_arrivee"]) if not manque else "",
            "taux_regularite": nombre(x["taux_de_regularite"]) if x["taux_de_regularite"] else "",
            "anomalies": "valeurs_manquantes" if manque else "",
        })
    out.sort(key=lambda o: (o["date"], o["depart"], o["arrivee"]))
    ecrire("transports_intercites_propre.csv", out)
    out = [{"date": x["date"], "annee": x["date"][:4],
            "regularite_composite": nombre(x["regularite_composite"]) if x["regularite_composite"] else "",
            "ponctualite_origine": nombre(x["ponctualite_origine"]) if x["ponctualite_origine"] else "",
            "anomalies": "" if x["regularite_composite"] else "valeurs_manquantes"}
           for x in lire_csv("sncf/reglarite-mensuelle-tgv-nationale.csv")]
    out.sort(key=lambda o: o["date"])
    ecrire("transports_tgv_propre.csv", out)


def effectifs_sncf():
    r = lire_csv("sncf/repartition-age-effectif.csv")
    # Libellés harmonisés (l'original est conservé dans college_source / tranche_source)
    college = lambda c: {"Exécution sédentaire": "Exécution sédentaires"}.get(c.strip(), c.strip())
    tranche = lambda t: t[:1].upper() + t[1:]
    groupes = defaultdict(list)
    for x in r:
        groupes[(x["date"], x["contrat_travail"], college(x["college"]))].append(tranche(x["tranche_age"]))
    valeurs = {(x["date"], x["contrat_travail"], college(x["college"]), tranche(x["tranche_age"])): nombre(x["effectif"])
               for x in r}
    out = []
    for x in r:
        a, contrat, col, tr = x["date"], x["contrat_travail"], college(x["college"]), tranche(x["tranche_age"])
        anomalies = [] if x["effectif"] else ["effectif_manquant"]
        if not any("et plus" in t for t in groupes[(a, contrat, col)]):
            anomalies.append("tranche_age_haute_manquante")
        if groupes[(a, contrat, col)].count(tr) > 1:
            anomalies.append("tranche_age_en_double")
        v = nombre(x["effectif"])
        voisins = [valeurs.get((str(int(a) + k), contrat, col, tr)) for k in (-1, 1)]
        if v is not None and all(w is not None and w > 1000 for w in voisins) and v < 0.2 * min(voisins):
            anomalies.append("valeur_atypique")
        out.append({"annee": a, "contrat": contrat, "college": col, "college_source": x["college"].strip(),
                    "tranche_age": tr, "tranche_source": x["tranche_age"],
                    "effectif": v if v is not None else "", "anomalies": ";".join(anomalies)})
    out.sort(key=lambda o: (o["annee"], o["contrat"], o["college"], o["tranche_age"]))
    ecrire("transports_effectifs_sncf_propre.csv", out)


def gares():
    out = []
    for x in lire_csv("sncf/frequentation-gares.csv"):
        cp = (x["code_postal"] or "").strip().zfill(5)
        ligne = {"gare": x["nom_gare"], "code_uic": x["code_uic_complet"], "code_postal": cp,
                 "departement": cp[:3] if cp.startswith("97") else cp[:2],
                 "segment": x["segmentation_drg"], "type_gare": x["segmentation_marketing"]}
        manquantes = 0
        for a in range(2015, 2025):
            cle = "totalvoyageurs2017" if a == 2017 else f"total_voyageurs_{a}"
            v = nombre(x.get(cle, ""))
            ligne[f"voyageurs_{a}"] = v if v is not None else ""
            manquantes += v is None
        anomalies = []
        if manquantes:
            anomalies.append("annees_manquantes")
        if not x["segmentation_drg"]:
            anomalies.append("segment_manquant")
        ligne["anomalies"] = ";".join(anomalies)
        out.append(ligne)
    out.sort(key=lambda o: o["code_uic"])
    ecrire("transports_gares_propre.csv", out)


def point_kilometrique(pk):
    """'049+056' -> 49,056 km ; '000-377' -> -0,377 km."""
    m = re.fullmatch(r"(\d+)([+-])(\d+)", (pk or "").strip())
    if not m:
        return None
    if m.group(2) == "+":
        return int(m.group(1)) + int(m.group(3)) / 1000
    return int(m.group(1)) - int(m.group(3)) / 1000


def lignes():
    out = []
    for x in lire_csv("sncf/lignes-par-statut.csv"):
        d, f = point_kilometrique(x["pkd"]), point_kilometrique(x["pkf"])
        longueur = round(abs(f - d), 3) if d is not None and f is not None else ""
        out.append({"code_ligne": x["code_ligne"], "libelle_ligne": x["lib_ligne"], "statut": x["statut"],
                    "rang_troncon": x["rg_troncon"], "pk_debut": x["pkd"], "pk_fin": x["pkf"], "longueur_km": longueur,
                    "anomalies": "" if longueur != "" else "point_kilometrique_illisible"})
    out.sort(key=lambda o: (o["code_ligne"], o["rang_troncon"]))
    ecrire("transports_lignes_propre.csv", out)


def points_vente():
    out = [{"gare": x["gare"], "code_uic": x["gare_code_uic"], "ville": x["ville"], "region": x["region"].strip(),
            "type_point_vente": x["type_de_point_de_vente"], "anomalies": "" if x["gare_code_uic"] else "code_gare_manquant"}
           for x in lire_csv("sncf/points-vente.csv")]
    out.sort(key=lambda o: (o["code_uic"], o["type_point_vente"]))
    ecrire("transports_points_vente_propre.csv", out)


def ter_art():
    """Onglet « 9.1 - Offre, Freq, REF TER » : en-têtes sur deux lignes (indicateur, unité), année en colonne A."""
    chemin = os.path.join(SRC, "art", "ART_donnees_transport_ferroviaire.xlsx")
    lignes_f = list(lignes_xlsx(chemin, "9.1 - Offre, Freq, REF TER"))
    indicateurs, unites = lignes_f[1], lignes_f[2]
    out, annee = [], ""
    for l in lignes_f[3:]:
        if not l or len(l) < 2 or not l[1]:
            continue
        annee = l[0] if re.fullmatch(r"20\d\d", l[0] or "") else annee
        region = l[1].strip()
        niveau = "total" if region.lower().startswith("total") else ("detail" if region.startswith("Dont") else "region")
        for j in range(2, len(indicateurs)):
            if not indicateurs[j]:
                continue
            brut = l[j] if j < len(l) else ""
            v = nombre(brut)
            out.append({"annee": annee, "region": region, "niveau": niveau, "indicateur": indicateurs[j],
                        "unite": unites[j] if j < len(unites) else "", "valeur": v if v is not None else "",
                        "anomalies": "" if v is not None else ("non_disponible" if brut in ("N/D", "") else "valeur_non_numerique")})
    ecrire("transports_ter_art_propre.csv", out)


def autocars():
    chemin = os.path.join(SRC, "art", "Donnees_trimestrielles_SLO_interurbains_autocar.xlsx")
    lignes_f = list(lignes_xlsx(chemin, "Tab1-Données globales"))
    i = next(k for k, l in enumerate(lignes_f) if l and l[0] == "Année")
    entete = lignes_f[i]
    out = []
    for l in lignes_f[i + 1:]:
        if not l or not re.match(r"20\d\d", l[0] or ""):
            continue
        partielle = not re.fullmatch(r"20\d\d", l[0])
        for j in range(1, len(entete)):
            v = nombre(l[j]) if j < len(l) else None
            anomalies = []
            if v is None:
                anomalies.append("valeur_manquante")
            if partielle:
                anomalies.append("annee_partielle")
            out.append({"annee": l[0][:4], "periode": l[0], "indicateur": entete[j], "valeur": v if v is not None else "",
                        "anomalies": ";".join(anomalies)})
    ecrire("transports_autocars_propre.csv", out)


def lire_tcu(nom):
    with open(os.path.join(SRC, "tcu", nom), encoding="latin-1", errors="replace") as f:
        texte = f.read()
    return list(csv.DictReader(io.StringIO(texte), dialect=csv.Sniffer().sniff(texte[:5000], delimiters=";,\t")))


def tcu():
    """Voyages et kilomètres offerts par réseau, déclarés par l'exploitant (type 2). Les déclarations des autres types
    (sous-traitants, lots : type 6) sont ignorées et signalées ; plusieurs exploitants d'un même réseau la même année
    sont additionnés et signalés."""
    annees = {}
    for x in lire_tcu("tcu-enquete.csv"):
        m = re.search(r"(\d{4})", x["enq_nom"])
        if m:
            annees[x["enq_id"]] = m.group(1)
    declarants = {x["pm_id"]: (x["res_id"], x["perstype_id"]) for x in lire_tcu("tcu-persmorale.csv")}
    reseaux = {x["res_id"]: x["res_nom"] for x in lire_tcu("tcu-reseau.csv")}
    valeurs = defaultdict(list)
    ignorees = defaultdict(int)
    with open(os.path.join(SRC, "tcu", "open-data-tcu-dataenq.csv"), encoding="latin-1", newline="") as f:
        for x in csv.DictReader(f, delimiter=";"):
            if x["var_id"] not in VARIABLES_TCU or x["enq_id"] not in annees or x["pm_id"] not in declarants:
                continue
            v = nombre(x["dat_valeur"].replace(",", "."))
            if v is None:
                continue
            res, typ = declarants[x["pm_id"]]
            cle = (res, annees[x["enq_id"]], VARIABLES_TCU[x["var_id"]])
            if typ == TYPE_EXPLOITANT_TCU:
                valeurs[cle].append(v)
            else:
                ignorees[cle] += 1
    out = []
    # Couples sans déclaration d'exploitant : conservés avec une valeur vide (EDR-007)
    for cle in ignorees:
        valeurs.setdefault(cle, [])
    for cle, vals in sorted(valeurs.items()):
        res, annee, variable = cle
        anomalies = [] if vals else ["aucune_declaration_exploitant"]
        if len(vals) > 1:
            anomalies.append("plusieurs_exploitants_valeurs_additionnees")
        if ignorees.get(cle):
            anomalies.append("declarations_autres_types_ignorees")
        out.append({"reseau_id": res, "reseau": reseaux.get(res, ""), "annee": annee, "variable": variable,
                    "valeur": sum(vals) if vals else "", "nb_exploitants": len(vals), "nb_declarations_ignorees": ignorees.get(cle, 0),
                    "anomalies": ";".join(anomalies)})
    ecrire("transports_tcu_propre.csv", out)


SERVICES_FIABILITE = {"TER", "Transilien", "Intercités"}


def fiabilite_art():
    """Onglet « 8.1 - Fiabilité » : moyennes de trains par jour, par année et par service."""
    lignes_f = list(lignes_xlsx(os.path.join(SRC, "art", "ART_donnees_transport_ferroviaire.xlsx"), "8.1 - Fiabilité"))
    indicateurs, unites = lignes_f[1], lignes_f[2]
    out, annee = [], ""
    for l in lignes_f[3:]:
        if not l or len(l) < 3:
            continue
        annee = l[0] if re.fullmatch(r"20\d\d", l[0] or "") else annee
        if l[1] not in SERVICES_FIABILITE:
            continue
        for j in range(2, min(len(indicateurs), len(l))):
            if not indicateurs[j] or (unites[j] if j < len(unites) else "") == "%" or indicateurs[j].strip().startswith("Taux"):
                continue  # les taux (y compris ceux sans unité dans la source) sont recalculés à partir des volumes
            v = nombre(l[j])
            out.append({"annee": annee, "service": l[1], "indicateur": re.sub(r"\s+", " ", indicateurs[j]).strip(),
                        "unite": unites[j] if j < len(unites) else "", "valeur": v if v is not None else "",
                        "anomalies": "" if v is not None else "non_disponible"})
    ecrire("transports_fiabilite_art_propre.csv", out)


def dessertes_gares():
    """Onglet « 6.1 - Gares » : fréquentation et nombre de dessertes par gare, 2019-2023."""
    lignes_f = list(lignes_xlsx(os.path.join(SRC, "art", "ART_donnees_transport_ferroviaire.xlsx"), "6.1 - Gares"))
    out = []
    for l in lignes_f[2:]:
        if not l or not re.fullmatch(r"20\d\d", l[0] or ""):
            continue
        l = l + [""] * (9 - len(l))
        v = [nombre(x) for x in l[4:9]]
        out.append({"annee": l[0], "code_ci": l[1], "gare": l[2], "segment": l[3],
                    "frequentation": v[0] if v[0] is not None else "", "dessertes": v[1] if v[1] is not None else "",
                    "dessertes_slo": v[2] if v[2] is not None else "", "dessertes_ter_intercites": v[3] if v[3] is not None else "",
                    "dessertes_transilien": v[4] if v[4] is not None else "",
                    "anomalies": "" if v[1] is not None else "dessertes_manquantes"})
    ecrire("transports_dessertes_gares_propre.csv", out)


def reseau_rfn():
    """Onglet « 1.1 - RFN » : longueur du réseau ferré national par année, région, gestionnaire et catégorie de lignes."""
    lignes_f = list(lignes_xlsx(os.path.join(SRC, "art", "ART_donnees_transport_ferroviaire.xlsx"), "1.1 - RFN"))
    out = []
    for l in lignes_f[2:]:
        if not l or not re.fullmatch(r"20\d\d", l[0] or ""):
            continue
        l = l + [""] * (9 - len(l))
        km_voies, km_ligne, km_elec = nombre(l[5]), nombre(l[6]), nombre(l[8])
        anomalies = [] if km_ligne is not None else ["km_ligne_manquant"]
        if not l[4] or l[4] == "Non renseigné":
            anomalies.append("categorie_non_renseignee")
        out.append({"annee": l[0], "region": l[1], "ancienne_region": l[2], "gestionnaire": l[3], "categorie_ligne": l[4],
                    "km_voies": km_voies if km_voies is not None else "", "km_ligne": km_ligne if km_ligne is not None else "",
                    "km_ligne_electrifies": km_elec if km_elec is not None else "", "anomalies": ";".join(anomalies)})
    ecrire("transports_reseau_rfn_propre.csv", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    ter()
    intercites_tgv()
    effectifs_sncf()
    gares()
    lignes()
    points_vente()
    ter_art()
    autocars()
    tcu()
    fiabilite_art()
    dessertes_gares()
    reseau_rfn()


if __name__ == "__main__":
    main()
