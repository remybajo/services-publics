"""Lecture des sources tabulaires partagée par les scripts de nettoyage (bibliothèque standard uniquement)."""
import re
import zipfile

NS_XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def chemin_feuille(z, n):
    """n = numéro de fichier (sheetN.xml) ou nom d'onglet tel qu'affiché dans Excel."""
    if isinstance(n, int):
        return f"xl/worksheets/sheet{n}.xml"
    classeur = z.read("xl/workbook.xml").decode("utf-8")
    rid = re.search(r'<sheet [^>]*name="' + re.escape(n) + r'"[^>]*r:id="([^"]+)"', classeur).group(1)
    liens = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    cible = re.search(r'<Relationship [^>]*Id="' + rid + r'"[^>]*/>', liens).group(0)
    return "xl/" + re.search(r'Target="([^"]+)"', cible).group(1).lstrip("/").replace("xl/", "", 1)


def lignes_xlsx(chemin, n):
    """Lit une feuille xlsx en flux (fichiers de plusieurs centaines de Mo) -> listes de valeurs, colonnes vides comprises."""
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(chemin)
    feuille = chemin_feuille(z, n)
    partages = []
    if "xl/sharedStrings.xml" in z.namelist():
        for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
            if el.tag == NS_XLSX + "si":
                partages.append("".join(t.text or "" for t in el.iter(NS_XLSX + "t")))
                el.clear()
    for _, el in ET.iterparse(z.open(feuille)):
        if el.tag != NS_XLSX + "row":
            continue
        valeurs = {}
        for c in el.findall(NS_XLSX + "c"):
            lettres = re.match(r"[A-Z]+", c.get("r")).group(0)
            i = 0
            for ch in lettres:
                i = i * 26 + ord(ch) - 64
            v = c.find(NS_XLSX + "v")
            x = v.text if v is not None else "".join(t.text or "" for t in c.iter(NS_XLSX + "t"))
            if c.get("t") == "s" and x:
                x = partages[int(x)]
            valeurs[i - 1] = (x or "").strip()
        el.clear()
        yield [valeurs.get(i, "") for i in range(max(valeurs) + 1)] if valeurs else []


def nombre_fr(v):
    v = v.replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    return float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else None
