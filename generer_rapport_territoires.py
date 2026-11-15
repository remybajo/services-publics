"""Génère rapport_territoires.html à partir de donnees_propres/territoires/chiffres_territoires.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Style repris de rapport_lots.html (EDR-011),
ton « offensif mais inattaquable » (EDR-012), carte interactive (cartes_svg.py).
Usage : python3 generer_rapport_territoires.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from graphiques_svg import STYLE_MILITANT, alleger_limites, barres_h, casse_en_chiffres, d, lecture, limite, n  # noqa: E402
from cartes_svg import STYLE_CARTE, carte_departements, section_carte  # noqa: E402

FICHE = "donnees_propres/territoires/chiffres_territoires.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapports/rapport_territoires.html"

C = json.load(open(FICHE, encoding="utf-8"))
IND, DEPS = C["indicateurs"], C["departements"]
NB = len(IND)
# Libellés courts des boutons de la carte et des colonnes du tableau
COURTS = {"sous_dotee": "Déserts médicaux", "generalistes": "Généralistes", "bureaux_poste": "Bureaux de poste",
          "sans_bureau": "Habitants sans bureau de poste", "ecoles": "Écoles publiques", "logements": "Logements sociaux",
          "guichets": "Gares sans guichet"}
RAPPORTS = {"Santé": "sante.html", "La Poste": "poste.html", "Éducation": "education.html", "Logement": "logement.html",
            "Transports": "transports.html"}


def fmt(ind):
    """Formatage selon l'unité de l'indicateur : part en % ou évolution signée."""
    if "évolution" in ind["unite"]:
        return lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%"
    return lambda v: d(v) + "&nbsp;%"


def cumul(v):
    return f"{n(v)} indicateur{'s' if v > 1 else ''} sur {NB}"


# --- 1. La carte ------------------------------------------------------------------------------
classes = [o for o in DEPS if o["nb_disponibles"] >= C["min_indicateurs"]]
cartes = [{"libelle": "Cumul", "legende": f"Nombre d'indicateurs (sur {NB}) où le département est dans le cinquième le plus défavorable",
           "valeurs": {o["departement"]: o["nb_defavorables"] for o in classes}, "fmt": cumul,
           "seuils": [1, 2, 3, 4], "etiquettes": ["aucun", "1", "2", "3", "4 ou plus"]}]
cartes += [{"libelle": COURTS[i["cle"]], "legende": i["libelle"], "valeurs": {o["departement"]: o["valeurs"].get(i["cle"]) for o in DEPS},
            "fmt": fmt(i), "inverse": i["sens"] == "bas"} for i in IND]
top = C["classement_cumul"]
maxi = top[0]["nb_defavorables"]
tetes = [o["nom"] for o in top if o["nb_defavorables"] == maxi]
s_carte = section_carte("La carte", f"{C['nb_au_moins_3']} départements cumulent au moins trois reculs sur {NB}", carte_departements("carte-territoires", cartes, "Carte du cumul des indicateurs défavorables par département"), f"""
  <p class="take">Sur {C['nb_departements_classes']} départements, <strong>{C['nb_au_moins_3']}</strong> figurent dans le cinquième le plus défavorable pour au moins trois des {NB} indicateurs retenus, et {C['nb_au_moins_4']} pour au moins quatre. À l'inverse, {C['nb_aucun']} n'y figurent pour aucun.</p>
  <p>En tête : {' et '.join(tetes)} ({maxi} indicateurs sur {NB}).</p>
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons affichent chaque indicateur séparément. Plus la teinte est foncée, plus la situation est défavorable.</p>
  {lecture("le recul des services publics ne se répartit pas au hasard : les mêmes départements perdent à la fois leurs médecins, leurs bureaux de poste, leurs écoles ou leurs guichets de gare.")}
  {limite(f"comptage construit pour ce rapport, non pondéré : par construction, un cinquième des départements est « défavorable » pour chaque indicateur ; le cumul mesure donc des écarts entre départements, pas un niveau absolu de service. Les indicateurs portent sur des périodes et des champs différents. Départements disposant d'au moins {C['min_indicateurs']} indicateurs ({', '.join(C['departements_non_classes'])} non classé).")}""")

# --- 2. Le classement ---------------------------------------------------------------------------
g_cl = barres_h([(o["nom"], o["nb_defavorables"]) for o in top], lambda v: n(v),
                f"Nombre d'indicateurs (sur {NB}) où le département est dans le cinquième le plus défavorable", couleur="var(--alerte)", vmax=NB)
rep = C["repartition_cumul"]
s_cl = f"""
<section>
  <h3>0 · Les cumuls</h3>
  <h2>Les {len(top)} départements qui cumulent le plus de reculs</h2>
  <div class="row">
    <div class="chart">{g_cl}</div>
    <div class="note">
  <p class="take">Répartition des {C['nb_departements_classes']} départements : {rep['0']} ne sont dans le cinquième le plus défavorable pour aucun indicateur, {rep['1']} pour un seul, {rep['2']} pour deux, <strong>{C['nb_au_moins_3']} pour trois ou plus</strong>.</p>
  {limite("à nombre égal d'indicateurs, les départements sont rangés par numéro : l'ordre à l'intérieur d'un même groupe n'a pas de sens.")}
    </div>
  </div>
</section>"""

# --- 3. Les écarts, indicateur par indicateur ---------------------------------------------------------
lignes_ind = "".join(
    f'<tr><td><a href="{RAPPORTS[i["theme"]]}">{i["theme"]}</a></td><td>{i["libelle"]}</td>'
    f'<td class="num">{i["plus_defavorable"]["nom"]} : <strong>{fmt(i)(i["plus_defavorable"]["valeur"])}</strong></td>'
    f'<td class="num">{fmt(i)(i["mediane"])}</td>'
    f'<td class="num">{i["plus_favorable"]["nom"]} : {fmt(i)(i["plus_favorable"]["valeur"])}</td>'
    f'<td class="num">{i["nb_departements"]}</td></tr>' for i in IND)
s_ecarts = f"""
<section id="ecarts">
  <h3>0 · Les écarts</h3>
  <h2>D'un département à l'autre, des situations sans commune mesure</h2>
  <div class="tbl"><table>
    <thead><tr><th>Thème</th><th>Indicateur</th><th class="num">Département le plus défavorable</th><th class="num">Département médian</th><th class="num">Département le plus favorable</th><th class="num">Départements couverts</th></tr></thead>
    <tbody>{lignes_ind}</tbody>
  </table></div>
  {limite("valeurs reprises des cinq rapports thématiques, où figurent leurs sources, leurs dates et leurs limites (lien dans la première colonne). Médiane : la moitié des départements est au-dessus, l'autre moitié en dessous.")}
</section>"""

# --- 4. Tableau par département ------------------------------------------------------------------


def cellule(o, i):
    v = o["valeurs"].get(i["cle"])
    if v is None:
        return '<td class="num" data-v="">–</td>'
    marque = ' class="num defav"' if i["cle"] in o["defavorables"] else ' class="num"'
    return f'<td{marque} data-v="{v}">{fmt(i)(v)}</td>'


lignes = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td><td data-v="{o["nom"]}">{o["nom"]}</td>'
    + (f'<td class="num" data-v="{o["nb_defavorables"]}"><strong>{o["nb_defavorables"]}</strong> sur {o["nb_disponibles"]}</td>')
    + "".join(cellule(o, i) for i in IND) + "</tr>" for o in DEPS)
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Les sept indicateurs, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un nom ou un numéro pour filtrer. Les cases en rouge signalent les indicateurs pour lesquels le département est dans le cinquième le plus défavorable.</p>
  <input id="filtre" type="search" placeholder="Rechercher un département…" aria-label="Rechercher un département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>N°</th><th>Département</th><th class="num">Indicateurs défavorables</th>{"".join(f'<th class="num">{i["libelle"]}</th>' for i in IND)}</tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
  <p><strong>Sources :</strong> rapports santé, La Poste, éducation, logement et transports de ce site. « – » : indicateur non disponible pour ce département (logement : France métropolitaine ; gares : hors Île-de-France, Corse et outre-mer, départements d'au moins 10 gares).</p>
</section>
<script>
(function () {{
  var t = document.getElementById('tdep'), corps = t.tBodies[0], sens = {{}};
  Array.prototype.forEach.call(t.tHead.rows[0].cells, function (th, i) {{
    th.style.cursor = 'pointer';
    th.addEventListener('click', function () {{
      sens[i] = !sens[i];
      var l = Array.prototype.slice.call(corps.rows);
      l.sort(function (a, b) {{
        var x = a.cells[i].dataset.v, y = b.cells[i].dataset.v;
        if (x === '') return 1; if (y === '') return -1;
        var nx = parseFloat(x), ny = parseFloat(y);
        var r = (!isNaN(nx) && !isNaN(ny) && i > 1) ? nx - ny : x.localeCompare(y, 'fr');
        return sens[i] ? r : -r;
      }});
      l.forEach(function (r) {{ corps.appendChild(r); }});
    }});
  }});
  document.getElementById('filtre').addEventListener('input', function () {{
    var q = this.value.toLowerCase();
    Array.prototype.forEach.call(corps.rows, function (r) {{
      r.style.display = (r.cells[0].textContent + ' ' + r.cells[1].textContent).toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    }});
  }});
}})();
</script>"""

# --- Synthèse, méthode, assemblage ----------------------------------------------------------------
par_cle = {i["cle"]: i for i in IND}


def extreme(cle):
    i = par_cle[cle]
    return (f"{i['plus_defavorable']['nom']} : {fmt(i)(i['plus_defavorable']['valeur'])} ; "
            f"{i['plus_favorable']['nom']} : {fmt(i)(i['plus_favorable']['valeur'])}")


casse = casse_en_chiffres("Les fractures en chiffres", [
    f"<strong>{C['nb_au_moins_3']} départements</strong> sur {C['nb_departements_classes']} sont parmi les plus mal placés pour au moins trois indicateurs sur {NB} ; {C['nb_aucun']} ne le sont pour aucun.",
    f"Déserts médicaux, part des habitants en commune sous-dotée en généralistes : <strong>{extreme('sous_dotee')}</strong>.",
    f"Bureaux de poste, évolution en dix ans : <strong>{extreme('bureaux_poste')}</strong>.",
    f"Écoles publiques, évolution depuis 2009 : <strong>{extreme('ecoles')}</strong>.",
    f"Gares sans guichet : <strong>{extreme('guichets')}</strong>.",
], note="« Fractures » : notre lecture de ces écarts. Chaque indicateur est détaillé, sourcé et assorti de ses limites dans le rapport thématique correspondant ; le cumul est un comptage construit pour ce rapport, dont la méthode est décrite plus bas.")

fiab = f"""
<section id="fiabilite">
  <h3>0 · Méthode</h3>
  <h2>Comment le cumul est calculé</h2>
  <div class="tbl"><table>
    <tr><th>Étape</th><th>Règle</th><th>Conséquence</th></tr>
    <tr><td>Indicateurs</td><td>{NB} indicateurs départementaux repris sans recalcul des cinq rapports vérifiés</td><td>Mêmes sources et mêmes limites que ces rapports</td></tr>
    <tr><td>Cinquième le plus défavorable</td><td>Pour chaque indicateur, les départements au moins aussi mal placés que celui du rang correspondant à un cinquième de l'effectif (ex æquo inclus)</td><td>Par construction, environ un département sur cinq pour chaque indicateur : le cumul mesure des écarts, pas un niveau absolu</td></tr>
    <tr><td>Cumul</td><td>Nombre d'indicateurs pour lesquels le département est dans ce cinquième ; aucun poids</td><td>Un indicateur de santé compte autant qu'un indicateur de transport</td></tr>
    <tr><td>Couverture</td><td>Logement : France métropolitaine ; gares : hors Île-de-France, Corse et outre-mer, départements d'au moins 10 gares ; classement limité aux départements disposant d'au moins {C['min_indicateurs']} indicateurs</td><td>{', '.join(C['departements_non_classes'])} non classé ; l'outre-mer et l'Île-de-France sont classés sur moins d'indicateurs</td></tr>
    <tr><td>Périodes</td><td>Les indicateurs ne portent pas sur les mêmes années (2009 à 2026 selon les sources)</td><td>Le cumul n'est pas une évolution datée</td></tr>
  </table></div>
</section>"""
sources = """
<section>
  <h3>Sources</h3>
  <p>Fiches de chiffres vérifiées des rapports santé (DREES), La Poste (Insee, La Poste), éducation (DEPP), logement (SDES) et transports (SNCF), détaillées dans chacun de ces rapports. Fond de carte : contours administratifs 2024 (Etalab, Licence Ouverte).</p>
  <p>Calculs rejouables : <code>calculer_chiffres_territoires.py</code> puis <code>generer_rapport_territoires.py</code>.</p>
</section>"""
tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">{C['nb_au_moins_3']}</div><div class="l">départements parmi les plus mal placés pour au moins 3 indicateurs sur {NB}</div></div>
    <div class="tile"><div class="v">{C['nb_aucun']}</div><div class="l">départements qui ne le sont pour aucun</div></div>
    <div class="tile"><div class="v">{fmt(par_cle['sous_dotee'])(par_cle['sous_dotee']['plus_defavorable']['valeur'])}</div><div class="l">d'habitants en commune sous-dotée en généralistes ({par_cle['sous_dotee']['plus_defavorable']['nom']}, département le plus touché)</div></div>
    <div class="tile"><div class="v">{fmt(par_cle['bureaux_poste'])(par_cle['bureaux_poste']['plus_defavorable']['valeur'])}</div><div class="l">de bureaux de poste en dix ans ({par_cle['bureaux_poste']['plus_defavorable']['nom']}, plus forte baisse)</div></div>
  </div>"""
entete = f"""
<header>
  <div class="eyebrow">Territoires · croisement des cinq rapports</div>
  <h1>Médecins, bureaux de poste, écoles, guichets : {C['nb_au_moins_3']} départements cumulent les reculs</h1>
  <p class="lead">Les cinq rapports de ce site mesurent chacun un service public. Croisés département par département, ils montrent que les reculs se concentrent sur les mêmes territoires. Chaque chiffre vient des rapports thématiques et peut y être vérifié.</p>
  {tuiles}
</header>""" + casse

sommaire = ('<nav class="sommaire" aria-label="Sommaire"><a href="#carte">La carte</a><a href="#ecarts">Les écarts</a>'
            '<a href="#departements">Votre département</a><a href="#fiabilite">Méthode</a></nav>')
corps = s_cl + s_ecarts + tableau + fiab
compteur = iter(range(1, 100))
corps = re.sub(r"<h3>\d+ · ", lambda _: f"<h3>{next(compteur)} · ", corps)
corps = alleger_limites(corps)  # version presse : limites repliables, jamais supprimées
carte_haut = alleger_limites(re.sub(r"<h3>0 · ", "<h3>", s_carte))  # carte en tête de page, juste après l'en-tête
entete = entete.replace("</header>", "</header>" + carte_haut, 1)

STYLE_SUPPL = """<style>
.sommaire { display: flex; flex-wrap: wrap; gap: 8px; }
.sommaire a { font-size: 14px; font-weight: 600; color: var(--ink); text-decoration: none; padding: 6px 12px; border-radius: 99px; background: var(--accent-wash); }
#filtre { font: inherit; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--ring); background: var(--surface); color: var(--ink); width: 100%; max-width: 360px; }
td.defav { background: var(--alerte-fond); color: var(--alerte); font-weight: 600; }
@media (max-width: 720px) { .row { grid-template-columns: minmax(0, 1fr); } .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
a { color: var(--s1); }
</style>"""
modele = open(MODELE_STYLE, encoding="utf-8").read()
tete = re.search(r"(?s)^.*?</style>", modele).group(0)
tete = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', "", tete)  # pas de police externe : rapport autonome
tete = re.sub(r"<title>.*?</title>", "<title>Services publics : les fractures territoriales</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">"
        + entete + sommaire + corps + sources + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques)")
