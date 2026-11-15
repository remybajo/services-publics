"""Nettoyage des données sur l'éducation (EDR-024).

Sources : donnees_brutes/education/ (DEPP et SIES, Licence Ouverte v2.0).
Produit dans donnees_propres/education/ :
- education_ecoles_propre.csv      : 1 ligne = 1 école x 1 rentrée (secteur, éducation prioritaire, classes, élèves), 2009-2025
- education_segregation_propre.csv : 1 ligne = 1 territoire x 1 année (indicateur de ségrégation sociale des collèges)
- education_ips_colleges_propre.csv : 1 ligne = 1 collège x 1 rentrée (indice de position sociale), depuis 2023-2024
- education_superieur_propre.csv   : 1 ligne = 1 commune x 1 année x 1 regroupement x 1 secteur x 1 sexe (étudiants inscrits)
Usage : python3 nettoyer_education.py [dossier_source]
"""
import csv
import os
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "donnees_brutes/education"
OUT = "donnees_propres/education"

# Secteurs des écoles harmonisés ; le libellé d'origine est conservé dans secteur_source
SECTEURS_ECOLES = {"PUBLIC": "public", "PRIVE SOUS CONTRAT": "prive_sous_contrat", "PRIVE": "prive_sous_contrat"}
# Collectivités d'outre-mer présentes à partir de 2019 seulement : hors des 101 départements (série comparable)
HORS_DEPARTEMENTS = {"975", "986", "987", "988"}  # Saint-Pierre-et-Miquelon, Wallis-et-Futuna, Polynésie, Nouvelle-Calédonie
SECTEURS_SUP = {"PU": "public", "PR": "prive"}


def ecrire(nom, lignes):
    with open(os.path.join(OUT, nom), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes):>7} lignes -> {nom}")


def lire(nom):
    with open(os.path.join(SRC, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def nombre(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def vide_si_none(x):
    return x if x is not None else ""


def ecoles():
    out = []
    # La colonne « code_commune_insee » de la source contient le code postal (métadonnées DEPP) : publiée sous le nom code_postal
    for x in lire("fr-en-ecoles-effectifs-nb_classes.csv"):
        anomalies = []
        if x["secteur"] == "PRIVE":
            anomalies.append("secteur_prive_sans_precision")  # 98 écoles en 2022, « privé sous contrat » les autres années
        classes, eleves = nombre(x["nombre_total_classes"]), nombre(x["nombre_total_eleves"])
        if not eleves:
            anomalies.append("aucun_eleve")
        out.append({"rentree": x["rentree_scolaire"], "departement": x["code_departement"], "nom_departement": x["departement"],
                    "code_postal": x["code_commune_insee"], "commune": x["commune"], "uai": x["numero_ecole"],
                    "secteur": SECTEURS_ECOLES[x["secteur"]], "secteur_source": x["secteur"],
                    "rep": x["rep"], "rep_plus": x["rep_plus"],
                    "classes": vide_si_none(classes), "eleves": vide_si_none(eleves),
                    "eleves_preelementaire": vide_si_none(nombre(x["nombre_eleves_preelementaire_hors_ulis"])),
                    "eleves_elementaire": vide_si_none(nombre(x["nombre_eleves_elementaire_hors_ulis"])),
                    "dans_101_departements": int(x["code_departement"] not in HORS_DEPARTEMENTS),
                    "anomalies": ";".join(anomalies)})
    out.sort(key=lambda o: (o["rentree"], o["uai"]))
    ecrire("education_ecoles_propre.csv", out)


def segregation():
    out = []
    for x in lire("fr-en-indicateur_segregation_sociale_colleges.csv"):
        niveau = "departement" if x["dep"] else "academie" if x["acad"] else "france"
        ligne = {"annee": x["annee"], "niveau": niveau, "academie": x["nom_academie"], "departement": x["dep"],
                 "nom_departement": x["nom_departement"]}
        for k in ("nb_coll_calcul", "nb_coll_pu_calcul", "nb_coll_pr_calcul", "poids_prive_calcul",
                  "p_tfav", "p_defav", "p_tfav_pu", "p_tfav_pr", "p_defav_pu", "p_defav_pr", "i_entropie_tot", "contrib_interpupr"):
            ligne[k] = vide_si_none(nombre(x[k]))
        ligne["anomalies"] = ";".join(f"{k}_manquant" for k, v in ligne.items()
                                      if v == "" and k not in ("academie", "departement", "nom_departement"))
        out.append(ligne)
    out.sort(key=lambda o: (o["annee"], o["niveau"], o["academie"], o["departement"]))
    ecrire("education_segregation_propre.csv", out)


def ips_colleges():
    out = []
    for x in lire("fr-en-ips-colleges-ap2023.csv"):
        ips = nombre(x["ips"])
        out.append({"rentree": x["rentree_scolaire"], "departement": x["code_du_departement"], "nom_departement": x["departement"],
                    "uai": x["uai"], "secteur": x["secteur"].lower(), "ips": vide_si_none(ips),
                    "ips_departemental_public": vide_si_none(nombre(x["ips_departemental_public"])),
                    "ips_departemental_prive": vide_si_none(nombre(x["ips_departemental_prive"])),
                    "ips_national_public": vide_si_none(nombre(x["ips_national_public"])),
                    "ips_national_prive": vide_si_none(nombre(x["ips_national_prive"])),
                    "anomalies": "" if ips is not None else "ips_manquant"})
    out.sort(key=lambda o: (o["rentree"], o["uai"]))
    ecrire("education_ips_colleges_propre.csv", out)


def superieur():
    out = []
    for x in lire("fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables.csv"):
        eff, atlas = nombre(x["effectif"]), nombre(x["effectif_atlas"])
        out.append({"annee": x["annee_universitaire"], "rentree": x["rentree"], "departement": x["dep_id"].removeprefix("D"),
                    "nom_departement": x["dep_nom"], "code_commune": x["com_id"], "regroupement": x["regroupement"],
                    "libelle_regroupement": x["rgp_formations_ou_etablissements"], "secteur": SECTEURS_SUP[x["secteur"]],
                    "sexe": x["sexe_de_l_etudiant"], "effectif": vide_si_none(eff), "effectif_hors_doubles_cpge": vide_si_none(atlas),
                    "apprentis_sts": vide_si_none(nombre(x["effectif_apprentis_en_sts"])),  # comptés à partir de 2015-16 seulement
                    "anomalies": "" if eff is not None else "effectif_manquant"})
    out.sort(key=lambda o: (o["annee"], o["code_commune"], o["regroupement"], o["secteur"], o["sexe"]))
    ecrire("education_superieur_propre.csv", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    ecoles()
    segregation()
    ips_colleges()
    superieur()


if __name__ == "__main__":
    main()
