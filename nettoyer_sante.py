"""Nettoyage des données DREES sur les moyens de l'hôpital et l'accès aux soins (EDR-019).

Source : donnees_brutes/sante/ (exports data.drees, voir date_telechargement.txt).
Produit dans donnees_propres/sante/ :
- sante_lits_propre.csv            : 1 ligne = 1 année (lits et places, France entière)
- sante_effectifs_propre.csv       : 1 ligne = 1 secteur x 1 profession x 1 année
- sante_soins_critiques_propre.csv : 1 ligne = 1 territoire x 1 statut x 1 unité x 1 année
- sante_maternites_propre.csv      : 1 ligne = 1 maternité x 1 année
- sante_urgences_propre.csv        : 1 ligne = 1 département x 1 année (somme des passages journaliers)
- sante_urgences_mensuel_propre.csv : 1 ligne = 1 département x 1 mois (somme des passages journaliers)
- sante_apl_propre.csv             : 1 ligne = 1 commune x 1 année (APL médecins généralistes)
- sante_medecins_effectifs_propre.csv : 1 ligne = 1 territoire x spécialité x exercice x tranche d'âge (effectifs RPPS 2012-2026)
- sante_medecins_densites_propre.csv  : idem, tous âges, densité pour 100 000 habitants calculée par la DREES
- sante_medecins_specialites_detaillees_propre.csv : 1 ligne = 1 spécialité détaillée (France entière, effectifs 2012-2026)
- sante_ares_propre.csv            : 1 ligne = 1 indicateur x région x année x catégorie (base ARES 2013-2021)
- sante_comptes_financement_propre.csv : 1 ligne = 1 année x poste x financeur (comptes de la santé, euros courants)
- sante_comptes_volume_prix_propre.csv : 1 ligne = 1 année x poste x type (valeur, indices de prix et de volume)
"""
import csv
import html
import os
import re
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from lecture_xlsx import lignes_xlsx, nombre_fr  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "donnees_brutes/sante"
OUT = "donnees_propres/sante"

STATUTS_CRITIQUES = {
    "1_Public": "Public",
    "2_Prive_BL": "Privé lucratif",
    "3_Prive_BNL": "Privé non lucratif",
}
STATUTS_MATERNITES = {
    "PUBLIC": "Public",
    "PRIVE LUCRATIF": "Privé lucratif",
    "PRIVE NON LUCRATIF": "Privé non lucratif",
}
# Codes non documentés dans les métadonnées : libellés reconstitués d'après la nomenclature SAE
UNITES_CRITIQUES = {
    "REAADU": "Réanimation adulte",
    "REAENF": "Réanimation pédiatrique",
    "USIC": "Soins intensifs de cardiologie",
    "SIUNV": "Soins intensifs neuro-vasculaires",
    "AUTSI": "Autres soins intensifs",
    "SURVADU": "Surveillance continue adulte",
    "SURVENF": "Surveillance continue pédiatrique",
}
FEUILLES_APL = {"2022": 2, "2023": 3, "2024": 4}  # n° de feuille dans le classeur
# Le fichier des maternités code les communes d'outre-mer "9A1xx" (Guadeloupe) au lieu de "971xx" (code Insee)
PREFIXES_OUTRE_MER = {"9A": "97", "9B": "97", "9C": "97", "9D": "97", "9F": "97"}


def departement(code_commune):
    """Code département à partir d'un code commune Insee (3 caractères en outre-mer)."""
    return code_commune[:3] if code_commune.startswith("97") else code_commune[:2]


def lire(nom):
    with open(os.path.join(SRC, nom), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ecrire(nom, lignes):
    with open(os.path.join(OUT, nom), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes):>6} lignes -> {nom}")


def to_float(v):
    v = v.strip()
    return float(v) if v else None


def lits():
    out = []
    for r in lire("graphique-1-evolution-du-nombre-de-lits-et-de-places-au-31-decembre-depuis-fin-2013.csv"):
        out.append({
            "annee": r["annee"],
            "lits_hospitalisation_complete": int(r["nombre_de_lits_d_hospitalisation_complete_echelle_de_gauche"]),
            "places_hospitalisation_partielle": int(r["nombre_de_places_d_hospitalisation_partielle_echelle_de_droite"]),
        })
    out.sort(key=lambda o: o["annee"])
    ecrire("sante_lits_propre.csv", out)


def effectifs():
    out = []
    for r in lire("effectifs-salaries-hospitaliers-series-longues.csv"):
        # Les sous-catégories 71/72 ont une colonne "professions" vide : ce sont des détails de la catégorie 7
        detail = not r["professions"]
        anomalies = [] if to_float(r["effectifs"]) is not None else ["effectifs_manquants"]
        out.append({
            "annee": r["annee"],
            "secteur": r["secteur"],
            "profession": r["professions_detaillees"] if detail else r["professions"],
            "niveau": "detail" if detail else "agrege",
            "effectifs": to_float(r["effectifs"]) if not anomalies else "",
            "anomalies": ";".join(anomalies),
        })
    out.sort(key=lambda o: (o["annee"], o["secteur"], o["niveau"], o["profession"]))
    ecrire("sante_effectifs_propre.csv", out)


def soins_critiques():
    out = []
    for r in lire("lits-de-reanimation-de-soins-intensifs-et-de-surveillance-continue-en-france0.csv"):
        code, _, libelle = r["id_geo"].partition("_")
        anomalies = []
        if r["statut_etab"] not in STATUTS_CRITIQUES:
            anomalies.append("statut_inconnu")
        if r["uni"] not in UNITES_CRITIQUES:
            anomalies.append("unite_inconnue")
        out.append({
            "annee": r["annee"],
            "code_geo": code,
            "territoire": libelle.replace("_", " "),
            "statut": STATUTS_CRITIQUES.get(r["statut_etab"], r["statut_etab"]),
            "code_unite": r["uni"],
            "unite": UNITES_CRITIQUES.get(r["uni"], r["uni"]),
            "nb_lits": int(float(r["nb_lit"])) if r["nb_lit"] else "",
            "anomalies": ";".join(anomalies),
        })
    out.sort(key=lambda o: (o["annee"], o["code_geo"], o["statut"], o["code_unite"]))
    ecrire("sante_soins_critiques_propre.csv", out)


def maternites():
    out = []
    for r in lire("fichier_maternites_112021.csv"):
        anomalies = []
        com = PREFIXES_OUTRE_MER.get(r["com"][:2], r["com"][:2]) + r["com"][2:]
        if not r["type"]:
            anomalies.append("type_manquant")
        if r["statut"] not in STATUTS_MATERNITES:
            anomalies.append("statut_inconnu")
        out.append({
            "annee": r["annee"],
            "id_finess_et": r["fi_et"],
            "id_finess_ej": r["fi_ej"],
            "nom": re.sub(r"\s+", " ", r["nom_mat"]).strip(),
            "statut": STATUTS_MATERNITES.get(r["statut"], r["statut"]),
            "type": r["type"],
            "code_commune": com,
            "commune": r["nomcom"],
            "departement": departement(com),
            "lits_obstetrique": int(r["lit_obs"]) if r["lit_obs"].strip() else "",
            "accouchements": int(float(r["acctot"])) if r["acctot"].strip() else "",
            "anomalies": ";".join(anomalies),
        })
    out.sort(key=lambda o: (o["annee"], o["id_finess_et"]))
    ecrire("sante_maternites_propre.csv", out)


def urgences():
    total = defaultdict(float)
    jours = defaultdict(int)
    mois = defaultdict(float)
    jours_mois = defaultdict(int)
    libelles = {}
    for r in lire("series_longues_passages_urgences_2017_2023.csv"):
        k = (r["date"][:4], r["dep"])
        total[k] += float(r["nb_passages"])
        jours[k] += 1
        mois[(r["date"][:7], r["dep"])] += float(r["nb_passages"])
        jours_mois[(r["date"][:7], r["dep"])] += 1
        libelles[r["dep"]] = r["libelle_dep"]
    annees_par_dep = defaultdict(set)
    for a, d in total:
        annees_par_dep[d].add(a)
    toutes = {a for a, _ in total}
    out = []
    for (a, d), v in sorted(total.items()):
        anomalies = []
        if jours[(a, d)] < (366 if int(a) % 4 == 0 else 365):
            anomalies.append("annee_incomplete")
        if annees_par_dep[d] != toutes:
            anomalies.append("departement_non_couvert_toute_la_periode")
        out.append({
            "annee": a,
            "departement": d,
            "libelle_departement": libelles[d],
            "passages": round(v, 1),  # arrondi à la somme finale, pas ici
            "nb_jours": jours[(a, d)],
            "anomalies": ";".join(anomalies),
        })
    ecrire("sante_urgences_propre.csv", out)
    ecrire("sante_urgences_mensuel_propre.csv", [{
        "mois": mo,
        "departement": d,
        "libelle_departement": libelles[d],
        "passages": round(v, 1),
        "nb_jours": jours_mois[(mo, d)],
        "anomalies": "" if annees_par_dep[d] == toutes else "departement_non_couvert_toute_la_periode",
    } for (mo, d), v in sorted(mois.items())])


def lire_feuille_xlsx(z, partages, n):
    """Lit une feuille xlsx (bibliothèque standard) -> liste de dict {colonne: valeur}."""
    xml = z.read(f"xl/worksheets/sheet{n}.xml").decode("utf-8")
    lignes = []
    for row in re.finditer(r"<row [^>]*>(.*?)</row>", xml, re.S):
        cellules = {}
        for c in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row.group(1), re.S):
            v = re.search(r"<v>(.*?)</v>", c.group(3) or "")
            v = v.group(1) if v else ""
            if 't="s"' in c.group(2) and v:
                v = partages[int(v)]
            cellules[c.group(1)] = html.unescape(v)
        lignes.append(cellules)
    return lignes


def apl():
    z = zipfile.ZipFile(os.path.join(SRC, "apl_medecins_generalistes.xlsx"))
    partages = [re.sub(r"<[^>]+>", "", m) for m in
                re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    out = []
    for annee, n in FEUILLES_APL.items():
        for c in lire_feuille_xlsx(z, partages, n):
            code = c.get("A", "")
            if not re.fullmatch(r"\d[\dAB]\d{3}", code):  # ignore titres, notes, en-têtes
                continue
            anomalies = [] if c.get("C") else ["apl_manquant"]
            out.append({
                "annee": annee,
                "code_commune": code,
                "departement": departement(code),
                "commune": html.unescape(c.get("B", "")),
                "apl": to_float(c.get("C", "")) if c.get("C") else "",
                "apl_medecins_65_ans_et_moins": to_float(c.get("D", "")) if c.get("D") else "",
                "population_standardisee": to_float(c.get("G", "")) if c.get("G") else "",
                "population": to_float(c.get("H", "")) if c.get("H") else "",
                "anomalies": ";".join(anomalies),
            })
    ecrire("sante_apl_propre.csv", out)


# --- Sources ajoutées : démographie des médecins (RPPS), ARES, comptes de la santé ---------
ANNEES_RPPS = [str(a) for a in range(2012, 2027)]


def sans_code(v):
    """'01-Médecine générale' -> 'Médecine générale' ; '972 - Martinique' -> 'Martinique'."""
    return re.sub(r"^\s*\w+\s*-\s*", "", v).strip()


def code(v):
    return re.match(r"^\s*(\w+)", v).group(1) if v.strip() else ""


def medecins():
    """Feuilles Effectifs (2) et Densités (4) du fichier RPPS, tous sexes confondus."""
    chemin = os.path.join(SRC, "demographie", "medecins_rpps_2012_2026.xlsx")
    for n, nom, prefixe in ((2, "sante_medecins_effectifs_propre.csv", "effectif_"),
                            (4, "sante_medecins_densites_propre.csv", "densite_")):
        out, entete = [], None
        for v in lignes_xlsx(chemin, n):
            if not v or not any(v):
                continue
            if entete is None:
                entete = v
                continue
            r = dict(zip(entete, v))
            if r.get("sexe") != "0-Ensemble":
                continue
            if n == 4 and r.get("tranche_age") != "00-Ensemble":
                continue
            dep = code(r["departement"])
            ligne = {
                "territoire": sans_code(r["territoire"]),
                "code_region": code(r["region"]),
                "departement": "" if dep == "000" else (dep[1:] if len(dep) == 3 and dep[0] == "0" else dep),
                "libelle_departement": sans_code(r["departement"]),
                "specialites_agregees": sans_code(r["specialites_agregees"]),
                "specialite": sans_code(r["specialites"]),
                "exercice": sans_code(r["exercice"]),
                "tranche_age": sans_code(r["tranche_age"]),
            }
            manquantes = 0
            for a in ANNEES_RPPS:
                x = r.get(prefixe + a, "")
                ligne[prefixe + a] = to_float(x) if x else ""
                manquantes += not x
            ligne["anomalies"] = "valeurs_manquantes" if manquantes else ""
            out.append(ligne)
        ecrire(nom, out)
    # Feuille 5 : effectifs par spécialité détaillée (France entière)
    out, entete = [], None
    for v in lignes_xlsx(chemin, 5):
        if not v or not any(v):
            continue
        if entete is None:
            entete = v
            continue
        r = dict(zip(entete, v))
        ligne = {"specialites_agregees": sans_code(r["specialites_agregees"]), "specialite": sans_code(r["specialites"]),
                 "specialite_detaillee": r["specialites_detaillees"]}
        for a in ANNEES_RPPS:
            x = r.get("effectif_" + a, "")
            ligne["effectif_" + a] = to_float(x) if x else ""
        ligne["anomalies"] = ""
        out.append(ligne)
    ecrire("sante_medecins_specialites_detaillees_propre.csv", out)


# Feuilles ARES utilisées : (fichier, n° de feuille, indicateur)
FEUILLES_ARES = [
    ("nombre_d_etablissements_de_sante_en_france_2013_2021.xlsx", 2, "etablissements_par_statut"),
    ("nombre_d_etablissements_de_sante_en_france_2013_2021.xlsx", 3, "etablissements_avec_urgences"),
    ("capacites_et_activite_en_mco_en_france_2013_2021.xlsx", 2, "lits_mco"),
    ("capacites_et_activite_en_mco_en_france_2013_2021.xlsx", 8, "passages_urgences"),
    ("capacites_activite_et_equipements_hors_mco_en_france_2013_2021.xlsx", 2, "lits_psychiatrie_temps_plein"),
    ("capacites_activite_et_equipements_hors_mco_en_france_2013_2021.xlsx", 4, "places_psychiatrie_jour"),
    ("capacites_activite_et_equipements_hors_mco_en_france_2013_2021.xlsx", 6, "places_had"),
    ("capacites_activite_et_equipements_hors_mco_en_france_2013_2021.xlsx", 7, "lits_usld"),
    ("capacites_activite_et_equipements_hors_mco_en_france_2013_2021.xlsx", 9, "lits_ssr"),
]


def ares():
    """Tableaux régionaux ARES (une ou deux lignes d'en-tête) -> format long."""
    out = []
    for fichier, n, indicateur in FEUILLES_ARES:
        lignes = list(lignes_xlsx(os.path.join(SRC, "ares", fichier), n))
        titre = lignes[0][0] if lignes and lignes[0] else ""
        i_ent = next(i for i, l in enumerate(lignes) if l and l[0] == "Region")
        entete = lignes[i_ent]
        annees_ligne = lignes[i_ent - 1] if i_ent > 0 else []
        deux_niveaux = any(re.fullmatch(r"20\d\d", x) for x in annees_ligne[1:])
        sous_type = entete[1] == "TYPE"
        region = ""
        for l in lignes[i_ent + 1:]:
            if not l or not any(l):
                continue
            region = l[0] or region  # ligne « dont … » : région de la ligne précédente
            if deux_niveaux:
                annee = ""
                for j in range(1, len(entete)):
                    annee = annees_ligne[j] if j < len(annees_ligne) and annees_ligne[j] else annee
                    val = nombre_fr(l[j]) if j < len(l) else None
                    out.append({"indicateur": indicateur, "titre_source": titre, "region": region, "annee": annee,
                                "categorie": entete[j], "valeur": val if val is not None else "",
                                "anomalies": "" if val is not None else "valeur_non_numerique"})
            else:
                debut = 2 if sous_type else 1
                for j in range(debut, len(entete)):
                    val = nombre_fr(l[j]) if j < len(l) else None
                    out.append({"indicateur": indicateur, "titre_source": titre, "region": region, "annee": entete[j],
                                "categorie": l[1] if sous_type else "Total", "valeur": val if val is not None else "",
                                "anomalies": "" if val is not None else "valeur_non_numerique"})
    ecrire("sante_ares_propre.csv", out)


def comptes():
    out = []
    with open(os.path.join(SRC, "comptes", "cns_financement.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out.append({"annee": r["annee"], "niveau_poste": r["poste_niv"], "poste": r["poste"], "libelle_poste": r["poste_lib"],
                        "niveau_financeur": r["financeur_niv"], "financeur": r["financeur"],
                        "libelle_financeur": r["financeur_lib"], "montant_euros": to_float(r["montant"]) if r["montant"] else "",
                        "anomalies": "" if r["montant"] else "montant_manquant"})
    out.sort(key=lambda o: (o["annee"], o["poste"], o["financeur"]))
    ecrire("sante_comptes_financement_propre.csv", out)
    out = []
    with open(os.path.join(SRC, "comptes", "comptes_de_la_sante_partage_volume_prix.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out.append({"annee": r["annee"], "niveau_poste": r["poste_niv"], "poste": r["poste"], "libelle_poste": r["poste_lib"],
                        "type": r["type"], "valeur": to_float(r["montant"]) if r["montant"] else "",
                        "anomalies": "" if r["montant"] else "valeur_manquante"})
    out.sort(key=lambda o: (o["annee"], o["poste"], o["type"]))
    ecrire("sante_comptes_volume_prix_propre.csv", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    lits()
    effectifs()
    soins_critiques()
    maternites()
    urgences()
    apl()
    medecins()
    ares()
    comptes()


if __name__ == "__main__":
    main()
