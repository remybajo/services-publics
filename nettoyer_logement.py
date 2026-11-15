"""Nettoyage des données sur le logement social et les aides au logement (EDR-023).

Sources : donnees_brutes/logement/ (SDES : répertoire RPLS et compte du logement, licence ouverte ; ministère du Logement :
inventaire SRU, Licence Ouverte ; Cnaf : aides au logement par département, Licence Ouverte).
Produit dans donnees_propres/logement/ :
- logement_parc_social_propre.csv   : 1 ligne = 1 département x 1 année (parc au 1er janvier, mises en service, vacance, loyer)
- logement_sorties_propre.csv       : 1 ligne = 1 département x 1 millésime RPLS (ventes, démolitions, autres sorties de l'année)
- logement_construits_propre.csv    : 1 ligne = 1 champ x 1 année de construction (logements sociaux construits, 1998-2024)
- logement_sru_propre.csv           : 1 ligne = 1 commune soumise à la loi SRU x 1 millésime de l'inventaire (2023-2026)
- logement_aides_caf_propre.csv     : 1 ligne = 1 mois x 1 département x 1 type de parc (foyers et montants par aide)
- logement_compte_aides_propre.csv  : 1 ligne = 1 tableau x 1 ligne x 1 année (compte du logement, aides 1984-2025)
Usage : python3 nettoyer_logement.py [dossier_source]
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from lecture_xlsx import lignes_xlsx  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "donnees_brutes/logement"
OUT = "donnees_propres/logement"

RPLS_2025 = "rpls_2025/statistiques_sdes_resultats_rpls_2025_secret_donnees.xlsx"
RPLS_PAR_MILLESIME = {"2024": "rpls_2024.xlsx", "2025": RPLS_2025}  # millésime = parc au 1er janvier
SORTIES = {"nb_ls_vendu_occupant": "ventes_occupant", "nb_ls_vendu_autre_bailleur": "ventes_autre_bailleur",
           "nb_ls_autre_vente": "autres_ventes", "nb_ls_demolition": "demolitions", "nb_ls_sortie_autre_motif": "autres_motifs",
           "nb_ls_chgt_usage": "changements_usage", "nb_ls_fusion_scission": "fusions_scissions"}
# Colonnes de l'inventaire SRU : le nom change à chaque millésime (année, accents, majuscules) ; correspondance explicite
COLONNES_SRU = {
    "code_departement": ("Code_Departement", "Code_Département"),
    "code_insee": ("Code_INSEE_commune",),
    "commune": ("Nom_commune",),
    "population": ("Population_municipale_01_01_{m}",),
    "logements_sociaux": ("Nombre_lls_ Inventaire_au_01_01_{p}", "Nombre_lls_ Inventaire_au_01_01_{m}"),
    "taux_sru": ("Taux_SRU_au_01_01_{p}",),
    "taux_cible": ("Taux_cible_commune_2023_2025", "Taux_cible_commune"),
    "deficitaire": ("Commune_deficitaire_{m}", "Commune_déficitaire_{m}", "commune_deficitaire", "commune_deficitaire_au_01-01-{p}"),
    "carencee": ("Commune_carencee_2023_2025", "Commune_carencée_2023_2025", "Commune_carencée"),
    "exemptee": ("Commune_exemptee_2023_2025", "Commune_exemptée_2023_2025", "Commune_exemptee_2026_2028"),
    "prelevement_net": ("Prélèvement_net_{m}_dont_majoration", "Prelevement_net_{m}_dont_majoration"),
    "commune_sru": ("Commune_sru_au_01_01_{m}",),  # absent en 2023 et 2024 : toutes les lignes sont des communes SRU
}
TABLEAUX_COMPTE = {"T311": "Montant des aides au logement (M€ courants)",
                   "T341": "Aides personnelles : nombre de bénéficiaires (milliers)",
                   "T342": "Aides personnelles : montants (M€ courants)",
                   "T343": "Aides personnelles : montants mensuels moyens (€ courants)"}


def ecrire(nom, lignes):
    with open(os.path.join(OUT, nom), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes):>7} lignes -> {nom}")


def nombre(v):
    """Nombre au format anglais ou français (« 26,10% », « 1 234,5 ») ; None si vide, « - » ou non numérique."""
    v = (v or "").replace("\xa0", "").replace(" ", "").replace("%", "").replace("€", "").replace(",", ".").strip()
    try:
        return float(v)
    except ValueError:
        return None


def vide_si_none(x):
    return x if x is not None else ""


def feuille_departements(nom):
    """Onglet DEPARTEMENT du RPLS : codes de colonnes en ligne 5, une ligne par département ensuite."""
    lignes_f = list(lignes_xlsx(os.path.join(SRC, nom), "DEPARTEMENT"))
    entete = lignes_f[4]
    return entete, [l for l in lignes_f[5:] if l and re.fullmatch(r"\d\d|2[AB]", l[0] or "")]


def parc_social():
    entete, lignes_dep = feuille_departements(RPLS_2025)
    out = []
    for l in lignes_dep:
        v = dict(zip(entete, l))
        for a in range(2013, 2026):
            suf = "" if a == 2025 else f"_{a}"
            parc = nombre(v.get("nb_ls" if a == 2025 else f"nb_ls{a}"))
            anomalies = ["parc_manquant"] if parc is None else []
            if a >= 2023:
                anomalies.append("rupture_serie_2023")  # méthode d'imputation revue par le SDES en 2023 (onglet INFORMATIONS)
            out.append({"annee": a, "departement": l[0], "nom": v.get("LIBDEP", ""),
                        "logements_sociaux": vide_si_none(parc),
                        "mises_en_service": vide_si_none(nombre(v.get("nv_mes" + suf))),
                        "taux_vacance": vide_si_none(nombre(v.get("tx_vac" + suf))),
                        "taux_mobilite": vide_si_none(nombre(v.get("tx_mob" + suf))),
                        "loyer_moyen_m2": vide_si_none(nombre(v.get("loymoy" + suf))),
                        "anomalies": ";".join(anomalies)})
    ecrire("logement_parc_social_propre.csv", out)


def sorties():
    out = []
    for millesime, nom in RPLS_PAR_MILLESIME.items():
        entete, lignes_dep = feuille_departements(nom)
        for l in lignes_dep:
            v = dict(zip(entete, l))
            ligne = {"millesime": millesime, "annee_des_sorties": int(millesime) - 1, "departement": l[0]}
            anomalies = []
            for code, col in SORTIES.items():
                ligne[col] = vide_si_none(nombre(v.get(code)))
                if code not in entete:
                    anomalies.append(f"{col}_absent_du_millesime")
            ligne["anomalies"] = ";".join(anomalies)
            out.append(ligne)
    ecrire("logement_sorties_propre.csv", out)


def construits():
    lignes_f = list(lignes_xlsx(os.path.join(SRC, "rpls_construits_1998_2025.xlsx"), "Nombre de logements sociaux"))
    annees = next(l for l in lignes_f if l and "1998" in l)
    out = []
    for l in lignes_f:
        if l and l[0] in ("France métropolitaine", "France entière"):
            for j, a in enumerate(annees):
                if re.fullmatch(r"\d{4}", a or "") and j < len(l):
                    x = nombre(l[j])
                    out.append({"champ": l[0], "annee_construction": a, "logements_construits": vide_si_none(x),
                                "anomalies": "" if x is not None else "non_disponible"})
    ecrire("logement_construits_propre.csv", out)


def lire_sru(chemin):
    brut = open(chemin, "rb").read()
    try:
        texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = brut.decode("cp1252")  # millésimes 2025 et 2026 publiés en Windows-1252
    lignes_f = [l for l in texte.splitlines() if l.strip(",; ")]
    sep = ";" if lignes_f[0].count(";") > lignes_f[0].count(",") else ","
    lignes_f = list(csv.reader(lignes_f, delimiter=sep))
    entete = [c.strip() for c in lignes_f[0]]
    return [dict(zip(entete, l)) for l in lignes_f[1:]]


def sru():
    out = []
    for m in ("2023", "2024", "2025", "2026"):
        p = str(int(m) - 1)
        for v in lire_sru(os.path.join(SRC, f"sru_{m}.csv")):
            ligne = {"millesime": m, "annee_inventaire": p}  # logements sociaux et taux SRU au 1er janvier de l'année précédente
            anomalies = []
            for col, noms in COLONNES_SRU.items():
                cle = next((n.format(m=m, p=p) for n in noms if n.format(m=m, p=p) in v), None)
                brut = v[cle].strip() if cle else ""
                if cle is None:
                    anomalies.append(f"{col}_absent_du_millesime")
                if col == "prelevement_net" and brut.replace("€", "").strip() == "-":
                    brut = "0"  # format comptable du fichier : « - € » signifie un prélèvement nul
                ligne[col] = brut if col in ("code_departement", "code_insee", "commune") else vide_si_none(nombre(brut))
            ligne["anomalies"] = ";".join(anomalies)
            out.append(ligne)
    ecrire("logement_sru_propre.csv", out)


def aides_caf():
    out = []
    with open(os.path.join(SRC, "caf_al_type_parc_dep.csv"), encoding="utf-8-sig", newline="") as f:
        for v in csv.DictReader(f, delimiter=";"):
            ligne = {"mois": v["Date référence"], "departement": v["Numéro département"], "nom": v["Nom département"],
                     "type_parc": v["Type parc"]}
            anomalies = []
            for aide in ("APL", "ALS", "ALF", "NDURAL"):
                for k, col in (("Nombre foyers", "foyers"), ("Montant total", "montant")):
                    x = nombre(v.get(f"{k} {aide}"))
                    ligne[f"{col}_{aide.lower()}"] = vide_si_none(x)
                    if x is None:
                        anomalies.append(f"{col}_{aide.lower()}_manquant")
            ligne["anomalies"] = ";".join(anomalies)
            out.append(ligne)
    out.sort(key=lambda o: (o["mois"], o["departement"], o["type_parc"]))
    ecrire("logement_aides_caf_propre.csv", out)


def compte_aides():
    out = []
    for tab, titre in TABLEAUX_COMPTE.items():
        lignes_f = list(lignes_xlsx(os.path.join(SRC, "compte_logement_aides_1984_2025.xlsx"), tab))
        i_annees = next(i for i, l in enumerate(lignes_f) if l and "1984" in l)
        annees = lignes_f[i_annees]
        rubrique = ""
        for rang, l in enumerate(lignes_f[i_annees + 1:], start=1):
            if not l or not (l[0] or "").strip():
                continue
            libelle = re.sub(r"\s+", " ", l[0]).strip()
            valeurs = [(a, l[j] if j < len(l) else "") for j, a in enumerate(annees) if re.fullmatch(r"\d{4}", a or "")]
            if not any((x or "").strip() for _, x in valeurs):
                rubrique = libelle  # ligne de titre (ex. « AIDE PERSONNALISÉE AU LOGEMENT ») ou note de bas de tableau
                continue
            for a, x in valeurs:
                n = nombre(x)
                out.append({"tableau": tab, "titre_tableau": titre, "rang_ligne": rang, "rubrique": rubrique, "ligne": libelle,
                            "annee": a, "valeur": vide_si_none(n), "anomalies": "" if n is not None else "non_disponible"})
    ecrire("logement_compte_aides_propre.csv", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    parc_social()
    sorties()
    construits()
    sru()
    aides_caf()
    compte_aides()


if __name__ == "__main__":
    main()
