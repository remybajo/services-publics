"""Nettoyage de export_lots.csv (lots de marchés publics Pôle Emploi / France Travail).

Produit deux fichiers :
- lots_attributaires_propre.csv : 1 ligne = 1 lot x 1 prestataire (même grain que la source)
- lots_uniques.csv              : 1 ligne = 1 lot (id_contrat), à utiliser pour sommer les montants
"""
import csv
import os
import re
import sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/export_lots.csv")
OUT_DETAIL = "lots_attributaires_propre.csv"
OUT_LOTS = "lots_uniques.csv"

CATEGORIES = {"inseertion": "insertion"}

TYPES_MARCHE = {
    "procédure ouverte": "Procédure ouverte",
    "procédure ouverte, accord_cadre": "Procédure ouverte",
    "procédure nc": "Procédure non communiquée",
    "procédure adaptée": "Procédure adaptée",
    "procédure conjointe": "Procédure conjointe",
    "accord-cadre": "Accord-cadre",
    "accord cadre": "Accord-cadre",
    "accord-cadre à bon de commande": "Accord-cadre à bons de commande",
    "accord cadre à bons de commande": "Accord-cadre à bons de commande",
    "accord-cadre à bons de commande et à marchés subséquents": "Accord-cadre à bons de commande et marchés subséquents",
    "marché public": "Marché public",
    # valeurs qui ne sont pas des types de marché -> vidées
    "2 lots": "",
    "services": "",
}


def clean_text(v):
    """Retire retours à la ligne, espaces multiples et espaces en bord."""
    return re.sub(r"\s+", " ", v).strip()


def to_float(v):
    return float(v) if v.strip() else None


def main():
    with open(SRC, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    out = []
    for r in rows:
        r = {k: clean_text(v) for k, v in r.items()}
        anomalies = []

        url = re.search(r'href="([^"]+)"', r["marche"])

        date = r["date_attribution"]
        if date.startswith("1001"):
            anomalies.append("date_invalide")
            date = ""
        elif not date:
            anomalies.append("date_manquante")
        date = date.replace("/", "-")

        type_marche = r["type_marche"]
        type_marche = TYPES_MARCHE.get(type_marche.lower(), type_marche)

        # "25-14246, lot 25-14246, lot 9.2" -> "25-14246, lot 9.2"
        reference = re.sub(r"^(.+?), lot \1, lot ", r"\1, lot ", r["reference"])

        m_marche = to_float(r["montant_marche"])
        m_lot = to_float(r["montant_lot"])
        if m_lot is not None and m_marche is not None and m_lot > m_marche:
            anomalies.append("montant_lot_superieur_au_marche")
        if m_lot is None:
            anomalies.append("montant_lot_manquant")

        if not r["categorie"]:
            anomalies.append("categorie_manquante")
        if not r["acheteur"]:
            anomalies.append("acheteur_manquant")

        out.append({
            "id_lot_attributaire": r["numero"],
            "id_contrat": r["id_contrat"],
            "id_marche": r["id_marche"],
            "num_boamp": r["num_boamp"],
            "url_boamp": url.group(1) if url else "",
            "num_lot": r["num_lot"],  # 0 = marché non alloti
            "intitule": r["intitule"],
            "reference": reference,
            "date_attribution": date,
            "annee": date[:4],
            "categorie": CATEGORIES.get(r["categorie"], r["categorie"]),
            "prestation": r["prestation"],
            "type_marche": type_marche,
            "id_acheteur": r["id_acheteur"],
            "acheteur": r["acheteur"],
            "lieu_execution": r["lieu_execution"],
            "id_prestataire": r["id_prestataire"],
            "montant_marche": m_marche if m_marche is not None else "",
            "montant_lot": m_lot if m_lot is not None else "",
            "anomalies": ";".join(anomalies),
        })

    # Nombre d'attributaires par lot (accords-cadres multi-attributaires)
    prestataires = defaultdict(list)
    for o in out:
        prestataires[o["id_contrat"]].append(o["id_prestataire"])
    for o in out:
        o["nb_attributaires_lot"] = len(prestataires[o["id_contrat"]])

    out.sort(key=lambda o: (o["date_attribution"] or "9999", o["num_boamp"], int(o["num_lot"] or -1), int(o["id_prestataire"])))
    fields = list(out[0].keys())
    with open(OUT_DETAIL, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    # Une ligne par lot
    lots = {}
    for o in out:
        if o["id_contrat"] not in lots:
            lot = {k: v for k, v in o.items() if k not in ("id_lot_attributaire", "id_prestataire")}
            lot["ids_prestataires"] = ";".join(sorted(set(prestataires[o["id_contrat"]]), key=int))
            lots[o["id_contrat"]] = lot
    with open(OUT_LOTS, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(next(iter(lots.values())).keys()))
        w.writeheader()
        w.writerows(lots.values())

    print(f"{len(out)} lignes -> {OUT_DETAIL}")
    print(f"{len(lots)} lots   -> {OUT_LOTS}")


if __name__ == "__main__":
    main()
