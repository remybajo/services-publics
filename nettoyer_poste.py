"""Nettoyage des données sur le service public postal (EDR-022).

Sources : donnees_brutes/poste/ (Insee, Base permanente des équipements, Licence Ouverte ; La Poste : points de contact
sous Licence Ouverte, calendrier d'ouverture et boîtes aux lettres de rue sous ODbL, rapport intégré 2025).
Produit dans donnees_propres/poste/ :
- poste_reseau_evolution_propre.csv : 1 ligne = 1 territoire x 1 année x 1 type de point (Insee, 2015-2020-2025)
- poste_points_contact_propre.csv   : 1 ligne = 1 point de contact actuel (bureau, agence, relais, partenaire)
- poste_horaires_propre.csv         : 1 ligne = 1 point de contact (heures d'ouverture par semaine, médiane sur 13 semaines)
- poste_boites_propre.csv           : 1 ligne = 1 boîte aux lettres de rue (heures limites de dépôt)
- poste_rapport_integre_propre.csv  : 1 ligne = 1 indicateur du rapport intégré 2025 de La Poste
"""
import csv
import datetime
import glob
import json
import os
import re
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from lecture_xlsx import lignes_xlsx  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "donnees_brutes/poste"
OUT = "donnees_propres/poste"

TYPES_INSEE = {"A206": "Bureau de poste", "A207": "Relais poste", "A208": "Agence postale"}
# Caractéristiques La Poste regroupées (le libellé d'origine est conservé dans type_source)
TYPES_LA_POSTE = {
    "Bureau de Poste": "Bureau de poste",
    "Agence postale communale": "Agence postale",
    "Agence postale intercommunale": "Agence postale",
    "Agence postale": "Agence postale",
    "Relais poste": "Relais poste",
    "Point partenaire": "Point partenaire",
    "Agence postale ou Relais poste": "Agence postale ou relais poste",
}
COLLECTIVITES_HORS_DEPARTEMENTS = {"975", "977", "978"}  # Saint-Pierre-et-Miquelon, Saint-Barthélemy, Saint-Martin
# Codes commune de La Poste corrigés (code de la commune où se trouve réellement le point, d'après le géocodage de La Poste)
CORRECTIONS_CODE_INSEE = {"49069": "49126"}  # Orée d'Anjou : ancien code de commune déléguée
PREMIER_LUNDI = datetime.date(2026, 10, 19)  # début du calendrier téléchargé
NB_SEMAINES = 13


def ecrire(nom, lignes):
    with open(os.path.join(OUT, nom), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes):>7} lignes -> {nom}")


def departement(code_insee):
    return code_insee[:3] if code_insee.startswith("97") else code_insee[:2]


def reseau_evolution():
    out = []
    for chemin in sorted(glob.glob(os.path.join(SRC, "insee_bpe_evolution_*.json"))):
        for o in json.load(open(chemin, encoding="utf-8"))["observations"]:
            dim = o["dimensions"]
            geo = dim["GEO"].split("-", 1)[1]  # « 2026-DEP-09 » -> « DEP-09 » (géographie au 1er janvier 2026)
            niveau, _, code = geo.partition("-")
            v = o["measures"]["OBS_VALUE_NIVEAU"]["value"]
            out.append({"niveau": niveau, "code_geo": code, "annee": dim["TIME_PERIOD"],
                        "type_point": TYPES_INSEE[dim["FACILITY_TYPE"]], "code_type": dim["FACILITY_TYPE"],
                        "nombre": v if v is not None else "", "statut_observation": o["attributes"].get("OBS_STATUS", ""),
                        "anomalies": "" if v is not None else "valeur_manquante"})
    # Combinaisons territoire x année x type absentes de l'Insee : conservées avec une valeur vide (EDR-007)
    presentes = {(o["niveau"], o["code_geo"], o["annee"], o["code_type"]) for o in out}
    territoires = {(o["niveau"], o["code_geo"]) for o in out}
    annees = {o["annee"] for o in out}
    for niveau, code in territoires:
        for a in annees:
            for t, lib in TYPES_INSEE.items():
                if (niveau, code, a, t) not in presentes:
                    out.append({"niveau": niveau, "code_geo": code, "annee": a, "type_point": lib, "code_type": t,
                                "nombre": "", "statut_observation": "", "anomalies": "observation_absente"})
    out.sort(key=lambda x: (x["niveau"], x["code_geo"], x["annee"], x["code_type"]))
    ecrire("poste_reseau_evolution_propre.csv", out)


def points_contact():
    out = []
    with open(os.path.join(SRC, "laposte-poincont2.csv"), encoding="utf-8", newline="") as f:
        for x in csv.DictReader(f, delimiter=";"):
            insee_source = (x["code_insee"] or "").strip().zfill(5)
            insee = CORRECTIONS_CODE_INSEE.get(insee_source, insee_source)
            anomalies = ["code_insee_corrige"] if insee != insee_source else []
            if x["caracteristique_du_site"] not in TYPES_LA_POSTE:
                anomalies.append("type_inconnu")
            if x["caracteristique_du_site"] == "Agence postale ou Relais poste":
                anomalies.append("type_ambigu")
            if not x["code_insee"]:
                anomalies.append("code_insee_manquant")
            hors_departements = (x["pays"] != "FRANCE" or insee.startswith("99")
                                 or departement(insee) in COLLECTIVITES_HORS_DEPARTEMENTS
                                 or (x["code_postal"] or "").startswith("980"))  # Monaco, parfois codé avec une commune française
            if hors_departements:
                anomalies.append("hors_101_departements")
            out.append({"identifiant": x["identifiant_a"], "libelle": x["libelle_du_site"], "pays": x["pays"],
                        "dans_101_departements": "non" if hors_departements else "oui",
                        "type_point": TYPES_LA_POSTE.get(x["caracteristique_du_site"], x["caracteristique_du_site"]),
                        "type_source": x["caracteristique_du_site"], "bureau_rattachement": x["site_acores_de_rattachement"],
                        "code_insee": insee, "code_insee_source": insee_source, "code_postal": x["code_postal"], "commune": x["localite"], "departement": departement(insee),
                        "nom_departement": x["_reverse_geoloc-departement.nom_dep"],
                        "region": x["_reverse_geoloc-region.nom_reg"], "anomalies": ";".join(anomalies)})
    out.sort(key=lambda x: x["identifiant"])
    ecrire("poste_points_contact_propre.csv", out)


def duree_plage(plage):
    """'09:00-12:00' -> 3,0 heures ; 'FERME' -> 0 ; None si illisible."""
    if plage.strip().upper() == "FERME":
        return 0.0
    m = re.fullmatch(r"(\d\d):(\d\d)-(\d\d):(\d\d)", plage.strip())
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    return max(0.0, (h2 * 60 + m2 - h1 * 60 - m1) / 60)


def horaires():
    heures = defaultdict(lambda: [0.0] * NB_SEMAINES)
    jours_ouverts = defaultdict(lambda: [0] * NB_SEMAINES)
    samedis = defaultdict(int)
    infos, illisibles = {}, defaultdict(int)
    vus, doubles = set(), defaultdict(int)
    with open(os.path.join(SRC, "laposte-calendrier-ouverture.csv"), encoding="latin-1", newline="") as f:
        for x in csv.DictReader(f, delimiter=";"):
            jour = datetime.datetime.strptime(x["Date_calendrier"], "%d/%m/%Y").date()
            semaine = (jour - PREMIER_LUNDI).days // 7
            ident = x["#Identifiant"]
            infos[ident] = (x["Libellé_du_site"], x["Caractéristique"])
            if (ident, jour) in vus:  # ligne en double à l'identique : comptée une seule fois
                doubles[ident] += 1
                continue
            vus.add((ident, jour))
            if not 0 <= semaine < NB_SEMAINES:
                continue
            total = 0.0
            for k in range(1, 8):
                plage = x[f"Plage_horaire_{k}"]
                if plage:
                    d = duree_plage(plage)
                    if d is None:
                        illisibles[ident] += 1
                    else:
                        total += d
            heures[ident][semaine] += total
            if total > 0:
                jours_ouverts[ident][semaine] += 1
                if jour.weekday() == 5:
                    samedis[ident] += 1
    out = []
    for ident, (libelle, carac) in sorted(infos.items()):
        anomalies = ["plages_illisibles"] if illisibles[ident] else []
        if doubles[ident]:
            anomalies.append("jours_en_double")
        if carac not in TYPES_LA_POSTE:
            anomalies.append("type_hors_correspondance")
        if ident not in heures:
            anomalies.append("aucune_semaine_complete")
        out.append({"identifiant": ident, "libelle": libelle,
                    "type_point": TYPES_LA_POSTE.get(carac, carac), "type_source": carac,
                    "heures_par_semaine": round(statistics.median(heures[ident]), 4) if ident in heures else "",
                    "jours_ouverts_par_semaine": statistics.median(jours_ouverts[ident]) if ident in heures else "",
                    "samedis_ouverts": samedis[ident], "semaines": NB_SEMAINES,
                    "anomalies": ";".join(anomalies)})
    ecrire("poste_horaires_propre.csv", out)


def heure(v):
    """'T09:00:00+00:00' -> '09:00' ; '' si absente."""
    m = re.search(r"T?(\d\d):(\d\d)", v or "")
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def boites():
    out = []
    with open(os.path.join(SRC, "laposte-boiterue.csv"), encoding="utf-8-sig", newline="") as f:
        for x in csv.DictReader(f, delimiter=";"):
            insee = (x["CO_INSEE_COM"] or "").strip().zfill(5)
            semaine, samedi = heure(x["HDL_SEMAINE_EXTRA"]), heure(x["HDL_SAMEDI_EXTRA"])
            anomalies = []
            if not semaine:
                anomalies.append("heure_semaine_manquante")
            if not x["CO_INSEE_COM"]:
                anomalies.append("code_insee_manquant")
            out.append({"identifiant": x["CO_MUP"], "code_insee": insee, "commune": x["LB_COM"],
                        "departement": departement(insee), "heure_limite_semaine": semaine,
                        "heure_limite_samedi": samedi, "anomalies": ";".join(anomalies)})
    out.sort(key=lambda x: x["identifiant"])
    ecrire("poste_boites_propre.csv", out)


def nombre_ou_vide(v):
    try:
        return float(v)
    except ValueError:
        return ""


def rapport_integre():
    lignes = list(lignes_xlsx(os.path.join(SRC, "laposte-rapport-integre-2025.xlsx"), 1))
    entete = lignes[0]
    out = []
    for l in lignes[1:]:
        if not l or not any(l):
            continue
        r = dict(zip(entete, l + [""] * (len(entete) - len(l))))
        nombre, pourcentage = r.get("Valeur en nombre", ""), r.get("Valeur en pourcentage", "")
        nb, pc = nombre_ou_vide(nombre), nombre_ou_vide(pourcentage)
        anomalies = [] if (nombre or pourcentage) else ["valeur_manquante"]
        if (nombre and nb == "") or (pourcentage and pc == ""):
            anomalies.append("valeur_non_numerique")
        out.append({"theme": r["Thème"], "indicateur": r["Indicateur"].strip(), "valeur_nombre": nb, "valeur_pourcentage": pc,
                    "valeur_texte": nombre or pourcentage, "anomalies": ";".join(anomalies)})
    ecrire("poste_rapport_integre_propre.csv", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    reseau_evolution()
    points_contact()
    horaires()
    boites()
    rapport_integre()


if __name__ == "__main__":
    main()
