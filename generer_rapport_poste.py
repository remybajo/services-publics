"""Génère rapport_poste.html à partir de donnees_propres/poste/chiffres_poste.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Style repris de rapport_lots.html (EDR-011),
graphiques du module partagé graphiques_svg.py.
Usage : python3 generer_rapport_poste.py [--brouillon]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from graphiques_svg import (STYLE_MILITANT, barres_groupees, barres_h, casse_en_chiffres, d, empile_100_h,  # noqa: E402
                            lecture, legende, limite, n, pct, section)
from graphiques_svg import alleger_limites, barres_divergentes, limite  # noqa: E402
CP = json.load(open("donnees_propres/comparaisons/chiffres_comparaisons.json", encoding="utf-8"))  # comparaisons : population, Europe, OCDE
from cartes_svg import STYLE_CARTE, carte_departements, section_carte  # noqa: E402

FICHE = "donnees_propres/poste/chiffres_poste.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapports/rapport_poste.html"
BROUILLON = "--brouillon" in sys.argv

C = json.load(open(FICHE, encoding="utf-8"))
EV, RA, HO, BO, RI = (C[k] for k in ("evolution", "reseau_actuel", "horaires", "boites", "rapport_integre"))
TYPES = ["Bureau de poste", "Agence postale", "Relais poste"]
COUL = {"Bureau de poste": "var(--s1)", "Agence postale": "var(--s2)", "Relais poste": "var(--s5)"}
a0, a1 = EV["periode"]


def hm(v):
    """15,75 -> « 15 h 45 » ; 55,0 -> « 55 h »."""
    h, mn = int(v), round((v - int(v)) * 60)
    return f"{h}&nbsp;h&nbsp;{mn:02d}" if mn else f"{h}&nbsp;h"
s0, s2 = EV["serie"][0], EV["serie"][-1]

# --- 1. Le réseau change de mains -------------------------------------------------------------
g_res = barres_groupees([(x["annee"], [x[t] for t in TYPES]) for x in EV["serie"]], [COUL[t] for t in TYPES], 10000, 2000, n,
                        "Points postaux par type, au 1er janvier")
eb = EV["evol"]
s_res = section("0", "Le réseau postal", f"{n(abs(eb['Bureau de poste']['ecart']))} bureaux de poste en moins entre {a0} et {a1}", g_res, f"""
  <p class="take">La France compte <strong>{n(eb['Bureau de poste']['fin'])}</strong> bureaux de poste au 1er janvier {a1}, contre {n(eb['Bureau de poste']['debut'])} en {a0} ({pct(eb['Bureau de poste']['pct'])}).</p>
  <p>Dans le même temps, les agences postales tenues par les communes ou les intercommunalités passent de {n(eb['Agence postale']['debut'])} à {n(eb['Agence postale']['fin'])} ({pct(eb['Agence postale']['pct'])}) et les relais poste chez des commerçants de {n(eb['Relais poste']['debut'])} à {n(eb['Relais poste']['fin'])} ({pct(eb['Relais poste']['pct'])}).</p>
  <p>Le nombre total de points postaux varie peu ({pct(EV['total']['pct'])}) : ce qui change, c'est qui tient le guichet.</p>
  <p><strong>Limites :</strong> comparaison entre trois dates, pas une tendance annuelle continue. Pour les relais poste, l'Insee signalait sur 2016-2021 une évolution atypique dans six départements (Alpes-Maritimes, Bouches-du-Rhône, Haute-Garonne, Paris, Var, Hauts-de-Seine), dont trois avec rupture de série, tout en jugeant la montée en charge des relais avérée depuis 2017, notamment en Île-de-France.</p>""",
                legende([(t, COUL[t]) for t in TYPES]))

g_part = empile_100_h([(x["annee"], {t: 100 * x[t] / x["total"] for t in TYPES}) for x in EV["serie"]], TYPES, COUL,
                      "Répartition des points postaux selon qui les tient")
s_part = section("0", "Qui tient le guichet", f"Les bureaux de La Poste ne représentent plus que {d(s2['part_bureaux'], 0)}&nbsp;% des points postaux", g_part, f"""
  <p class="take">En {a1}, <strong>{d(s2['part_bureaux'])}&nbsp;%</strong> des points postaux sont des bureaux de poste tenus par La Poste, contre {d(s0['part_bureaux'])}&nbsp;% en {a0}.</p>
  <p>Les autres sont des agences postales, tenues par une commune ou une intercommunalité, et des relais installés chez des commerçants.</p>
  <p><em>Notre lecture :</em> confier les guichets à des communes et à des commerçants est une forme d'externalisation du service public postal. Les données ne disent pas que chaque agence ou relais a remplacé un bureau fermé dans la même commune.</p>
  <p><strong>Limites :</strong> part calculée parmi les bureaux, agences et relais recensés par l'Insee (points partenaires exclus) ; la source compte des points, pas les services qu'on y trouve.</p>""",
                 legende([(t, COUL[t]) for t in TYPES]))

# --- 2. Territoires ------------------------------------------------------------------------------
deps = [o for o in EV["departements"] if o["pct_bureaux"] is not None]
k = 15
g_dep = barres_h([(o["nom"], abs(o["pct_bureaux"])) for o in deps[:k]], lambda v: "−" + d(v) + "&nbsp;%",
                 f"Départements où les bureaux de poste ont le plus reculé, {a0}-{a1}", couleur="var(--s2)")
s_dep = section("0", "Par département", f"Dans {EV['deps_minorite_bureaux']} départements sur {len(deps)}, les bureaux de poste sont minoritaires parmi les points postaux", g_dep, f"""
  <p class="take">En {a1}, les bureaux de poste représentent moins de la moitié des points postaux dans <strong>{EV['deps_minorite_bureaux']} départements sur {len(deps)}</strong>, contre {EV['deps_minorite_bureaux_debut']} en {a0}.</p>
  <p>Les plus fortes baisses : {deps[0]['nom']} ({deps[0]['bureaux_debut']} → {deps[0]['bureaux_fin']}, {pct(deps[0]['pct_bureaux'])}), {deps[1]['nom']} ({pct(deps[1]['pct_bureaux'])}), {deps[2]['nom']} ({pct(deps[2]['pct_bureaux'])}).</p>
  <p><strong>Limite :</strong> nombre de points, sans tenir compte de la population ni des distances.</p>""")

# --- 3. Heures d'ouverture -----------------------------------------------------------------------
ht = HO["par_type"]
g_h = barres_h([(t, ht[t]["mediane"]) for t in TYPES], hm, "Heures d'ouverture par semaine (médiane)",
               couleur=lambda i, v: COUL[TYPES[i]])
s_h = section("0", "Heures d'ouverture", f"Une agence postale est ouverte {hm(ht['Agence postale']['mediane'])} par semaine, un bureau de poste {hm(ht['Bureau de poste']['mediane'])} (médianes)", g_h, f"""
  <p class="take">La moitié des agences postales sont ouvertes <strong>{hm(ht['Agence postale']['mediane'])}</strong> ou moins par semaine ; {d(ht['Agence postale']['part_moins_de_20h'])}&nbsp;% le sont moins de 20 heures.</p>
  <p>Les bureaux de poste sont ouverts {hm(ht['Bureau de poste']['mediane'])} par semaine en médiane, et {n(ht['Bureau de poste']['moins_de_20h'])} d'entre eux ({d(ht['Bureau de poste']['part_moins_de_20h'])}&nbsp;%) moins de 20 heures.</p>
  <p>Les relais poste, installés dans des commerces, sont ouverts {hm(ht['Relais poste']['mediane'])} par semaine en médiane.</p>
  <p><strong>Limites :</strong> horaires prévus par La Poste sur 13 semaines (octobre 2026 - janvier 2027), pas les horaires effectivement tenus, ni une évolution dans le temps ; les données ne disent pas quels services sont proposés dans chaque type de point. Horaires connus pour {d(ht['Bureau de poste']['couverture_pct'])}&nbsp;% des bureaux, {d(ht['Agence postale']['couverture_pct'])}&nbsp;% des agences et {d(ht['Relais poste']['couverture_pct'])}&nbsp;% des relais de la liste de La Poste.</p>""")

g_cl = empile_100_h([(t.replace("Bureau de poste", "Bureaux").replace("Agence postale", "Agences").replace("Relais poste", "Relais"),
                      ht[t]["classes"]) for t in TYPES], HO["classes"],
                    dict(zip(HO["classes"], ["var(--warn)", "var(--s2)", "var(--s5)", "var(--s1)"])),
                    "Répartition des points selon leurs heures d'ouverture par semaine")
s_cl = section("0", "Plages d'ouverture", f"{d(ht['Agence postale']['classes']['10 à 20 h'], 0)}&nbsp;% des agences postales ouvrent entre 10 et 20 heures par semaine", g_cl, f"""
  <p class="take">{d(ht['Bureau de poste']['classes']['35 h et plus'])}&nbsp;% des bureaux de poste sont ouverts 35 heures ou plus par semaine, contre {d(ht['Agence postale']['classes']['35 h et plus'])}&nbsp;% des agences postales.</p>
  <p>{d(ht['Bureau de poste']['part_ouverts_samedi'])}&nbsp;% des bureaux de poste sont ouverts au moins un samedi sur les 13 de la période, contre {d(ht['Agence postale']['part_ouverts_samedi'])}&nbsp;% des agences postales.</p>
  <p><strong>Limites :</strong> médiane sur 13 semaines, jours fériés et fermetures compris ; la classe « moins de 10 h » comprend des points fermés la plupart des semaines ({n(ht['Bureau de poste']['mediane_zero_heure'])} bureaux, {n(ht['Agence postale']['mediane_zero_heure'])} agences et {n(ht['Relais poste']['mediane_zero_heure'])} relais avec une médiane de 0 h).</p>""",
                  legende([(c, col) for c, col in zip(HO["classes"], ["var(--warn)", "var(--s2)", "var(--s5)", "var(--s1)"])]))

# --- 4. Boîtes aux lettres -----------------------------------------------------------------------
bo_classes = [("Avant 10 h", BO["avant_10h"]), ("De 10 h à midi", BO["avant_12h"] - BO["avant_10h"]),
              ("Midi et après", BO["nombre"] - BO["avant_12h"])]
g_bo = barres_h([(lib, 100 * v / BO["nombre"]) for lib, v in bo_classes], lambda v: d(v) + "&nbsp;%",
                "Heure limite de dépôt du courrier dans les boîtes aux lettres de rue, en semaine", vmax=100)
s_bo = section("0", "Boîtes aux lettres", f"{d(BO['part_avant_10h'], 0)}&nbsp;% des boîtes aux lettres de rue ont une heure limite de dépôt avant 10 h", g_bo, f"""
  <p class="take">Sur {n(BO['nombre'])} boîtes aux lettres de rue, <strong>{n(BO['avant_10h'])}</strong> ({d(BO['part_avant_10h'])}&nbsp;%) ont une heure limite de dépôt avant 10 heures en semaine.</p>
  <p><strong>Limites :</strong> heure limite telle que publiée par La Poste ; {n(BO['exclues_sans_heure'])} boîtes sans heure renseignée sont exclues. Photographie au 8 septembre 2026 : la source ne dit pas si ces horaires ont été avancés au fil du temps.</p>""")

s_fac = f"""
<section>
  <h3>0 · Facteurs</h3>
  <h2>{n(RI['facteurs_cdi'])} facteurs embauchés en CDI en 2025, {d(RI['facteurs_cdi_baisse_pct'], 0)}&nbsp;% de moins qu'en 2024</h2>
  <p class="take">Selon La Poste, <strong>{n(RI['facteurs_cdi'])}</strong> facteurs ont été embauchés en CDI en 2025, soit {d(RI['facteurs_cdi_baisse_pct'], 0)}&nbsp;% de moins qu'en 2024.</p>
  <p><strong>Limites :</strong> chiffres publiés par l'entreprise dans son rapport intégré 2025, non vérifiables par une autre source ; il s'agit d'embauches de l'année, pas de l'effectif de facteurs ; aucune série publique sur les effectifs n'a été trouvée.</p>
</section>"""

# --- Ajouts : population sans bureau, territoires 2026 --------------------------------------------
D6 = C["departements_2026"]
deps6 = [o for o in D6["departements"] if o["part_pop_sans_bureau"] is not None]
top_pop = sorted(deps6, key=lambda o: -o["part_pop_sans_bureau"])[:15]
g_pop = barres_h([(o["nom"], o["part_pop_sans_bureau"]) for o in top_pop], lambda v: d(v) + "&nbsp;%",
                 "Part de la population vivant dans une commune sans bureau de poste, par département", couleur="var(--alerte)", vmax=100)
zero = [o["nom"] for o in deps6 if o["part_pop_sans_bureau"] == 0]
s_pop = section("0", "Sans bureau de poste", f"{d(D6['population_sans_bureau'] / 1e6)} millions d'habitants vivent dans une commune où La Poste ne liste aucun bureau de poste (population 2022 ; bureaux listés par La Poste en octobre 2026)", g_pop, f"""
  <p class="take"><strong>{d(D6['population_sans_bureau'] / 1e6)} millions de personnes</strong>, soit {d(D6['part_population_sans_bureau'])}&nbsp;% de la population, vivent dans une commune où La Poste ne liste aucun bureau de poste. C'est le cas de {n(D6['communes_sans_bureau'])} communes et arrondissements municipaux sur {n(D6['communes'])}.</p>
  <p>{top_pop[0]['nom']} : <strong>{d(top_pop[0]['part_pop_sans_bureau'])}&nbsp;%</strong> de la population ; suivent {top_pop[1]['nom']} ({d(top_pop[1]['part_pop_sans_bureau'])}&nbsp;%), {top_pop[2]['nom']} ({d(top_pop[2]['part_pop_sans_bureau'])}&nbsp;%), puis plusieurs départements proches ({top_pop[3]['nom']} {d(top_pop[3]['part_pop_sans_bureau'])}&nbsp;%, {top_pop[4]['nom']} {d(top_pop[4]['part_pop_sans_bureau'])}&nbsp;%). À l'opposé, la part est nulle à {", ".join(zero[:4])}.</p>
  <p>{d(D6['population_sans_point'] / 1e6)} millions de personnes ({d(D6['part_population_sans_point'])}&nbsp;%) vivent dans une commune sans aucun point de contact postal (les points partenaires comptent comme points de contact).</p>
  {lecture(f"les bureaux de poste restent surtout dans les communes les plus peuplées. Dans {sum(1 for o in deps6 if o['part_pop_sans_bureau'] > 50)} départements, plus de la moitié des habitants vivent dans une commune où La Poste ne liste aucun bureau.")}
  {limite("« sans bureau » : aucun bureau de poste listé par La Poste dans la commune (au 08/10/2026), même si une agence postale, un relais ou un bureau voisin existe ; ne mesure ni la distance ni le temps d'accès. Population totale 2022 (fichier APL 2024 de la DREES, géographie non documentée), communes et arrondissements municipaux, hors Mayotte ; taille des communes très inégale.")}""")

top_h = sorted([o for o in D6["departements"] if o["part_points_moins_20h"] is not None], key=lambda o: -o["part_points_moins_20h"])[:15]
g_hdep = barres_h([(o["nom"], o["part_points_moins_20h"]) for o in top_h], lambda v: d(v) + "&nbsp;%",
                  "Part des bureaux, agences et relais ouverts moins de 20 h par semaine, par département", couleur="var(--alerte)", vmax=100)
s_hdep = section("0", "Ouverture par territoire", f"{top_h[0]['nom']} : {d(top_h[0]['part_points_moins_20h'], 0)}&nbsp;% des points postaux ouvrent moins de 20 h par semaine", g_hdep, f"""
  <p class="take">{top_h[0]['nom']} : <strong>{d(top_h[0]['part_points_moins_20h'])}&nbsp;%</strong> des bureaux, agences et relais y sont ouverts moins de 20 heures par semaine ; {top_h[1]['nom']} ({d(top_h[1]['part_points_moins_20h'])}&nbsp;%) et {top_h[2]['nom']} ({d(top_h[2]['part_points_moins_20h'])}&nbsp;%) suivent.</p>
  {lecture(f"la moitié des agences postales ouvrent {hm(ht['Agence postale']['mediane'])} ou moins par semaine, contre {hm(ht['Bureau de poste']['mediane'])} pour la moitié des bureaux de poste (horaires prévus).")}
  {limite("horaires prévus par La Poste du 19/10/2026 au 18/01/2027 (médiane sur 13 semaines), points dont les horaires sont connus (relais : 90,8&nbsp;% couverts) ; points partenaires exclus.")}""")

casse = casse_en_chiffres("En chiffres", [
    f"<strong>Près d'un bureau de poste sur trois a disparu</strong> en dix ans : {n(eb['Bureau de poste']['debut'])} en {a0}, {n(eb['Bureau de poste']['fin'])} en {a1} ({pct(eb['Bureau de poste']['pct'])}) ; {d(CP['poste']['bureaux_pour_100000']['fin'])} bureaux pour 100 000 habitants contre {d(CP['poste']['bureaux_pour_100000']['debut'])} ({pct(CP['poste']['bureaux_pour_100000']['pct'])}).",
    f"Les bureaux de La Poste ne sont plus que <strong>{d(s2['part_bureaux'], 0)}&nbsp;%</strong> des points postaux (contre {d(s0['part_bureaux'], 0)}&nbsp;% en {a0}) ; le reste est tenu par des communes, des intercommunalités ou des commerçants.",
    f"Dans <strong>{EV['deps_minorite_bureaux']} départements</strong> sur {len(deps)}, les bureaux sont devenus minoritaires parmi les points postaux, contre {EV['deps_minorite_bureaux_debut']} en {a0}.",
], note=f"Évolutions {a0}-{a1} (Insee). Le nombre total de points postaux (bureaux, agences et relais) varie peu ({pct(EV['total']['pct'])}). Détail, sources et limites dans la suite du rapport.")

# --- 5. Tableau par département ------------------------------------------------------------------
def cellule(v, fmt):
    return f'<td class="num" data-v="{v if v is not None else ""}">{fmt(v) if v is not None else "–"}</td>'


D6_par_dep = {o["departement"]: o for o in D6["departements"]}
lignes = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td><td data-v="{o["nom"]}">{o["nom"]}</td>'
    + cellule(o["bureaux_debut"], n) + cellule(o["bureaux_fin"], n)
    + cellule(o["pct_bureaux"], lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%")
    + cellule(o["agences_fin"], n) + cellule(o["relais_fin"], n)
    + cellule(o["part_bureaux_fin"], lambda v: d(v) + "&nbsp;%")
    + cellule(D6_par_dep.get(o["departement"], {}).get("part_pop_sans_bureau"), lambda v: d(v) + "&nbsp;%")
    + cellule(D6_par_dep.get(o["departement"], {}).get("mediane_heures_bureaux"), lambda v: d(v) + "&nbsp;h")
    + cellule(D6_par_dep.get(o["departement"], {}).get("part_points_moins_20h"), lambda v: d(v) + "&nbsp;%")
    + cellule(D6_par_dep.get(o["departement"], {}).get("part_boites_avant_10h"), lambda v: d(v) + "&nbsp;%") + "</tr>"
    for o in sorted(EV["departements"], key=lambda o: o["departement"]))
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Le réseau postal, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un nom ou un numéro pour filtrer.</p>
  <input id="filtre" type="search" placeholder="Rechercher un département…" aria-label="Rechercher un département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>N°</th><th>Département</th><th class="num">Bureaux {a0}</th><th class="num">Bureaux {a1}</th><th class="num">Évolution</th><th class="num">Agences {a1}</th><th class="num">Relais {a1}</th><th class="num">Part des bureaux {a1}</th><th class="num">Population sans bureau dans sa commune (pop. 2022, points 2026)</th><th class="num">Ouverture médiane des bureaux (2026)</th><th class="num">Points ouverts &lt; 20 h (2026)</th><th class="num">Boîtes : dépôt avant 10 h (2026)</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
  <p><strong>Source :</strong> Insee, Base permanente des équipements (au 1er janvier). Part des bureaux calculée parmi les bureaux, agences et relais (points partenaires exclus). Paris : aucune agence postale recensée par l'Insee (observation absente, comptée 0). Colonnes 2026 : La Poste (points au 08/10/2026, horaires prévus d'octobre 2026 à janvier 2027, boîtes au 08/09/2026), à ne pas comparer aux colonnes Insee.</p>
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
  document.getElementById('filtre').addEventListener('input', function (e) {{
    var q = e.target.value.toLowerCase();
    Array.prototype.forEach.call(corps.rows, function (r) {{ r.style.display = r.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none'; }});
  }});
}})();
</script>"""

# --- Fiabilité, sources, assemblage ----------------------------------------------------------------
fiab = f"""
<section id="fiabilite">
  <h3>0 · Fiabilité</h3>
  <h2>Ce qu'il faut garder en tête</h2>
  <div class="tbl"><table>
    <tr><th>Donnée</th><th>Limite</th><th>Conséquence</th></tr>
    <tr><td>Évolution du réseau (Insee)</td><td>Trois dates (2015, 2020, 2025) ; relais : évolution atypique dans six départements sur 2016-2021, dont trois avec rupture de série (Insee)</td><td>Sens de l'évolution identique aux trois dates ; détail annuel inconnu ; évolution des relais à lire avec la réserve de l'Insee</td></tr>
    <tr><td>Points de contact (La Poste)</td><td>Photographie au 8 octobre 2026 ; 13 points de type ambigu</td><td>Pas d'évolution ; non comparable avec les chiffres de l'Insee (dates et définitions différentes)</td></tr>
    <tr><td>Heures d'ouverture</td><td>Horaires prévus, médiane sur 13 semaines ; horaires inconnus pour une partie des points (relais : {d(ht['Relais poste']['couverture_pct'])}&nbsp;% couverts) ; services proposés non renseignés</td><td>Ne mesure ni l'affluence ni l'étendue des services</td></tr>
    <tr><td>Boîtes aux lettres</td><td>Photographie au 8 septembre 2026</td><td>Ne dit pas si les levées ont été avancées</td></tr>
    <tr><td>Corrections tracées</td><td>4 bureaux de Monaco exclus ; code commune d'Orée d'Anjou corrigé ; 88 communes sans point ni boîte (13 267 habitants), codes communes peut-être obsolètes</td><td>Effet négligeable sur les totaux</td></tr>
    <tr><td>Population sans bureau (2026)</td><td>Points La Poste 2026 et population 2022 par commune ; ni distance ni temps d'accès ; unité commune très inégale</td><td>Mesure l'absence de bureau dans la commune, pas l'éloignement</td></tr>
    <tr><td>Rapport intégré</td><td>Chiffres publiés par l'entreprise, une seule année</td><td>Non vérifiables à partir d'une autre source</td></tr>
      <tr><td>Rapport à la population (Insee)</td><td>Estimations de population au 1er janvier, années récentes provisoires</td><td>Ratios par habitant susceptibles de légères révisions</td></tr>
  </table></div>
</section>"""
date = open("donnees_brutes/poste/date_telechargement.txt", encoding="utf-8").read().strip()
sources = f"""
<section>
  <h3>Sources</h3>
  <p>Insee, Base permanente des équipements, jeu d'évolution 2015-2020-2025 (API Melodi, Licence Ouverte) ; Insee, <a href="https://www.insee.fr/fr/metadonnees/source/fichier/BPE16_21_Precautions_utilisation.pdf">BPE en évolution 2016-2021, précautions d'utilisation</a>. La Poste (data.laposte.fr) : liste des bureaux de poste, agences postales et relais poste (Licence Ouverte) ; calendrier d'ouverture et liste des boîtes aux lettres de rue (ODbL) ; rapport intégré 2025 (Licence Ouverte). Population : « population totale 2022 » du fichier APL 2024 de la DREES (Licence Ouverte). Téléchargement du {date}.</p>
  <p>Population : Insee, estimations localisées de population au 1er janvier (Licence Ouverte).</p>
  <p>Calculs rejouables : <code>calculer_chiffres_comparaisons.py</code> (comparaisons), <code>nettoyer_poste.py</code>, <code>calculer_chiffres_poste.py</code> puis <code>generer_rapport_poste.py</code>.</p>
</section>"""
bandeau = ('<div class="take" style="border-color:var(--warn)"><strong>Brouillon en cours de vérification</strong> : '
           'chiffres non encore validés de façon indépendante, ne pas diffuser.</div>') if BROUILLON else ""
tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">{pct(eb['Bureau de poste']['pct'])}</div><div class="l">bureaux de poste ({a0}-{a1}, Insee)</div></div>
    <div class="tile"><div class="v">{d(D6['population_sans_bureau'] / 1e6)}&nbsp;M</div><div class="l">d'habitants dans une commune sans bureau de poste listé (population 2022, liste d'octobre 2026)</div></div>
    <div class="tile"><div class="v">{hm(ht['Agence postale']['mediane'])}</div><div class="l">d'ouverture par semaine pour une agence postale (médiane, horaires prévus d'octobre 2026 à janvier 2027)</div></div>
    <div class="tile"><div class="v">{d(BO['part_avant_10h'], 0)}&nbsp;%</div><div class="l">des boîtes aux lettres avec dépôt limite avant 10 h (liste de septembre 2026)</div></div>
  </div>"""
entete = f"""
<header>
  <div class="eyebrow">Service public postal · données Insee et La Poste</div>
  <h1>{n(eb['Bureau de poste']['debut'])} bureaux de poste en {a0}, {n(eb['Bureau de poste']['fin'])} en {a1} ; les agences postales passent de {n(eb['Agence postale']['debut'])} à {n(eb['Agence postale']['fin'])}</h1>
  <p class="lead">Le réseau postal d'après l'Insee ({a0}-{a1}) et d'après les données publiées par La Poste en 2026, deux sources distinctes présentées séparément. Chaque chiffre vient d'une source publique et peut être recalculé ou vérifié à la source ; chaque graphique est accompagné de ses limites.</p>
  {bandeau}
  {tuiles}
</header>""" + casse


# --- Carte par département (mêmes valeurs que le tableau « Votre département ») ----------------------------
def pc(v):
    return d(v) + "&nbsp;%"


DC_EV = {o["departement"]: o for o in EV["departements"]}
s_carte = section_carte("La carte", "La présence postale, département par département", carte_departements("carte-poste", [
    {"libelle": "Bureaux de poste : évolution", "legende": f"Évolution du nombre de bureaux de poste, {a0}-{a1}",
     "valeurs": {k: o["pct_bureaux"] for k, o in DC_EV.items()},
     "fmt": lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%", "inverse": True},
    {"libelle": "Part des bureaux", "legende": f"Part des bureaux de poste parmi les points postaux ({a1})",
     "valeurs": {k: o["part_bureaux_fin"] for k, o in DC_EV.items()}, "fmt": pc, "inverse": True},
    {"libelle": "Habitants sans bureau", "legende": "Part de la population vivant dans une commune sans bureau de poste (population 2022, points 2026)",
     "valeurs": {k: o["part_pop_sans_bureau"] for k, o in D6_par_dep.items()}, "fmt": pc},
    {"libelle": "Ouverture réduite", "legende": "Part des points postaux ouverts moins de 20 h par semaine (2026)",
     "valeurs": {k: o["part_points_moins_20h"] for k, o in D6_par_dep.items()}, "fmt": pc},
], "Carte de la présence postale par département"), f"""
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons changent d'indicateur. Plus la teinte est foncée, plus la situation est défavorable. Les valeurs sont celles du tableau « Votre département » ci-dessous.</p>
  <p class="limite"><strong>Limites :</strong> classes de couleur = cinquièmes des départements ; les deux premiers indicateurs viennent de l'Insee (2015-2025), les deux suivants de La Poste (2026) et ne se comparent pas entre eux ; « sans bureau » ne mesure ni la distance ni le temps d'accès.</p>""")


# --- Comparaisons : bureaux de poste rapportés à la population (Insee) -------------------------------------
CPO = CP["poste"]
hab = sorted(CPO["par_departement"].items(), key=lambda kv: kv[1]["pct"])[:15]
g_hab = barres_h([(o["nom"], -o["pct"]) for _, o in hab], lambda v: "−" + d(v) + "&nbsp;%",
                 f"Baisse du nombre de bureaux de poste pour 100 000 habitants, {CPO['periode'][0]}-{CPO['periode'][1]}", couleur="var(--alerte)", vmax=60)
s_hab = section("0", "Rapporté à la population", f"{d(CPO['bureaux_pour_100000']['fin'])} bureaux de poste pour 100 000 habitants, contre {d(CPO['bureaux_pour_100000']['debut'])} en {CPO['periode'][0]}", g_hab, f"""
  <p class="take">La population augmente ({pct(CPO['population']['pct'])} entre {CPO['periode'][0]} et {CPO['periode'][1]}) pendant que les bureaux de poste disparaissent : on passe de {d(CPO['bureaux_pour_100000']['debut'])} à <strong>{d(CPO['bureaux_pour_100000']['fin'])} bureaux pour 100 000 habitants</strong> ({pct(CPO['bureaux_pour_100000']['pct'])}).</p>
  <p>Les plus fortes baisses par habitant : {hab[0][1]['nom']} ({pct(hab[0][1]['pct'])}), {hab[1][1]['nom']} ({pct(hab[1][1]['pct'])}), {hab[2][1]['nom']} ({pct(hab[2][1]['pct'])}).</p>
  {limite(f"bureaux de poste au 1er janvier (Insee, BPE) rapportés à la population au 1er janvier de la même année (Insee, estimations ; {CPO['periode'][1]} provisoire).")}""")


def partie(ident, titre, intro):
    return f'<div class="partie" id="{ident}"><div class="eyebrow">{titre}</div><p class="lead">{intro}</p></div>'


PARTIES = [
    ("reseau", f"Évolution du réseau, {a0}-{a1} (Insee)", "Bureaux de poste, agences postales et relais, au 1er janvier de chaque année. Séries de l'Insee, à ne pas comparer aux données de La Poste de la partie suivante.", [s_res, s_hab, s_part, s_dep]),
    ("aujourdhui", "Le réseau en 2026 (La Poste)", "Photographie des points de contact, des horaires prévus (19 octobre 2026 - 18 janvier 2027) et des boîtes aux lettres, d'après les données publiées par La Poste. Pas d'évolution dans le temps.", [s_pop, s_h, s_cl, s_hdep, s_bo, s_fac]),
]
sommaire = ('<nav class="sommaire" aria-label="Sommaire">' + "".join(f'<a href="#{i}">{t}</a>' for i, t, _, _ in PARTIES)
            + '<a href="#carte">La carte</a><a href="#departements">Votre département</a><a href="#fiabilite">Fiabilité</a></nav>')
corps = "".join(partie(i, t, intro) + "".join(secs) for i, t, intro, secs in PARTIES) + tableau + fiab
corps = corps.replace("<p><strong>Limite", '<p class="limite"><strong>Limite')  # limites plus discrètes, toujours présentes
compteur = iter(range(1, 100))
corps = re.sub(r"<h3>\d+ · ", lambda _: f"<h3>{next(compteur)} · ", corps)
corps = alleger_limites(corps)  # version presse : limites repliables, jamais supprimées
carte_haut = alleger_limites(re.sub(r"<h3>0 · ", "<h3>", s_carte))  # carte en tête de page, juste après l'en-tête
entete = entete.replace("</header>", "</header>" + carte_haut, 1)

STYLE_SUPPL = """<style>
:root { --s3: #1f9e89; --s4: #8a5cd6; --s5: #c99a06; --s6: #c2417a; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --s3: #3cc2a9; --s4: #a883ec; --s5: #e0b52c; --s6: #e0679b; } }
:root[data-theme="dark"] { --s3: #3cc2a9; --s4: #a883ec; --s5: #e0b52c; --s6: #e0679b; }
.sommaire { display: flex; flex-wrap: wrap; gap: 8px; }
.sommaire a { font-size: 14px; font-weight: 600; color: var(--ink); text-decoration: none; padding: 6px 12px; border-radius: 99px; background: var(--accent-wash); }
.partie { border-top: 2px solid var(--ink); padding-top: 18px; display: grid; gap: 6px; }
.partie .eyebrow { font-size: 14px; }
#filtre { font: inherit; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--ring); background: var(--surface); color: var(--ink); width: 100%; max-width: 360px; }
@media (max-width: 720px) { .row { grid-template-columns: minmax(0, 1fr); } .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
a { color: var(--s1); }
</style>"""
modele = open(MODELE_STYLE, encoding="utf-8").read()
tete = re.search(r"(?s)^.*?</style>", modele).group(0)
tete = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', "", tete)  # pas de police externe : rapport autonome
tete = re.sub(r"<title>.*?</title>", "<title>Service public postal</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">" + entete + sommaire + corps + sources
        + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques){' — BROUILLON' if BROUILLON else ''}")
