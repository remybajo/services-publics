"""Génère rapport_education.html à partir de donnees_propres/education/chiffres_education.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Style repris de rapport_lots.html (EDR-011),
graphiques du module partagé graphiques_svg.py, ton « offensif mais inattaquable » (EDR-012).
Usage : python3 generer_rapport_education.py [--brouillon]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from graphiques_svg import (STYLE_MILITANT, barres_groupees, barres_h, casse_en_chiffres, courbes, d, lecture,  # noqa: E402
                            legende, limite, n, pct, section)
from graphiques_svg import alleger_limites  # noqa: E402
from cartes_svg import STYLE_CARTE, carte_departements, section_carte  # noqa: E402

FICHE = "donnees_propres/education/chiffres_education.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapport_education.html"
BROUILLON = "--brouillon" in sys.argv

C = json.load(open(FICHE, encoding="utf-8"))
EC, SG, IP, SU, DE = (C[k] for k in ("ecoles", "segregation", "ips", "superieur", "departements"))
# Noms des départements en minuscules accentuées (SIES) ; les noms DEPP sont en capitales
NOMS = {k: o["nom"] for k, o in SU["par_departement"].items()}


def nom(code, defaut):
    return NOMS.get(code, defaut.title())


def signe(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%"


# --- 1. L'école primaire -------------------------------------------------------------------
se = EC["serie"]
a0, a1 = EC["periode"]
g_ec = barres_groupees([(x["rentree"][2:], [x["ecoles_public"] / 1000]) for x in se], ["var(--alerte)"], 50, 10,
                       lambda v: d(v, 1), "Écoles maternelles et élémentaires publiques, en milliers (101 départements)")
s_ec = section("0", "Écoles publiques", f"{n(-EC['ecoles_public']['ecart'])} écoles publiques en moins depuis {a0}", g_ec, f"""
  <p class="take">À la rentrée {a1}, la France compte <strong>{n(EC['ecoles_public']['fin'])}</strong> écoles maternelles et élémentaires publiques, contre {n(EC['ecoles_public']['debut'])} en {a0} : <strong>{n(-EC['ecoles_public']['ecart'])} de moins</strong> ({pct(EC['ecoles_public']['pct'])}). Une partie de cette baisse peut venir de regroupements : entre ces deux rentrées, {n(EC['uai_public_sorties'])} numéros d'écoles publiques ont disparu et {n(EC['uai_public_entrees'])} sont apparus, ce qui arrive par exemple quand une maternelle et une élémentaire fusionnent en une école primaire. Les données ne permettent pas de distinguer fermetures et fusions.</p>
  <p>Dans le même temps, le public compte {pct(EC['eleves_public']['pct'], False)} d'élèves en moins ({n(EC['eleves_public']['debut'])} → {n(EC['eleves_public']['fin'])}), mais {pct(EC['classes_public']['pct'], False)} de classes en plus. Le nombre d'écoles publiques baisse donc plus vite que celui de leurs élèves.</p>
  <p>Les écoles privées sous contrat passent de {n(EC['ecoles_prive']['debut'])} à {n(EC['ecoles_prive']['fin'])} ({pct(EC['ecoles_prive']['pct'])}). La part des élèves du premier degré scolarisés dans le privé passe de {d(se[0]['part_eleves_prive'])}&nbsp;% à {d(se[-1]['part_eleves_prive'])}&nbsp;%.</p>
  {lecture("l'école publique se concentre dans des établissements moins nombreux ; là où ces baisses sont des fermetures, l'école s'éloigne des familles, même si les classes sont moins chargées (les distances ne sont pas mesurées ici).")}
  {limite("101 départements (collectivités d'outre-mer exclues, absentes avant 2019). Une école = un numéro d'établissement présent à la rentrée. Années en abscisse : 09 = 2009.")}""")

g_pet = barres_groupees([(x["rentree"][2:], [x["petites_ecoles_public"] / 1000]) for x in se], ["var(--alerte)"], 12, 2,
                        lambda v: d(v, 1), "Écoles publiques à une ou deux classes, en milliers")
s_pet = section("0", "Petites écoles", f"{pct(EC['petites_ecoles_public']['pct'], False)} d'écoles publiques à une ou deux classes en moins", g_pet, f"""
  <p class="take">Les écoles publiques à une ou deux classes passent de {n(EC['petites_ecoles_public']['debut'])} en {a0} à <strong>{n(EC['petites_ecoles_public']['fin'])}</strong> en {a1} ({pct(EC['petites_ecoles_public']['pct'])}).</p>
  {lecture(f"le recul touche d'abord les plus petites écoles publiques : {pct(EC['petites_ecoles_public']['pct'])} pour les écoles à une ou deux classes, contre {pct(EC['ecoles_public']['pct'])} pour l'ensemble des écoles publiques.")}
  {limite("la source ne permet pas d'identifier les communes (la colonne communale contient le code postal) : le caractère rural de ces écoles n'est pas mesuré. Une petite école peut aussi s'agrandir ou se regrouper avec une autre.")}""")

g_cl = courbes([("Public", "var(--s1)", [x["eleves_par_classe_public"] for x in se]),
                ("Privé sous contrat", "var(--s2)", [x["eleves_par_classe_prive"] for x in se])],
               [x["rentree"] for x in se], 18, 26, 2, lambda v: d(v, 1), "Élèves par classe dans le premier degré",
               mention="Élèves par classe (axe tronqué)")
s_cl = section("0", "Taille des classes", f"Dans le public, {d(se[-1]['eleves_par_classe_public'])} élèves par classe ; dans le privé, {d(se[-1]['eleves_par_classe_prive'])}", g_cl, f"""
  <p class="take">Le nombre d'élèves par classe baisse nettement dans le public, de {d(se[0]['eleves_par_classe_public'])} en {a0} à <strong>{d(se[-1]['eleves_par_classe_public'])}</strong> en {a1}, alors qu'il reste stable dans le privé sous contrat ({d(se[0]['eleves_par_classe_prive'])} → {d(se[-1]['eleves_par_classe_prive'])}).</p>
  {limite("élèves divisés par classes, classes spécialisées (ULIS) comprises ; moyenne nationale qui ne dit rien des écarts entre écoles. Les causes (baisse du nombre d'élèves, dédoublement de classes) ne sont pas mesurées ici.")}""",
               legende([("Public", "var(--s1)"), ("Privé sous contrat", "var(--s2)")]))

cl_dep = DE["classement_baisse_ecoles_public"]
g_dep = barres_h([(nom(o["departement"], o["nom"]), -o["pct_ecoles_public"]) for o in cl_dep], lambda v: "−" + d(v) + "&nbsp;%",
                 f"Baisse du nombre d'écoles publiques, {a0}-{a1}", couleur="var(--alerte)", vmax=50)
c0, c1, c2 = cl_dep[:3]
s_dep = section("0", "Par département", f"Moins d'écoles publiques dans {DE['deps_ecoles_public_en_baisse']} départements sur {len(DE['departements'])}", g_dep, f"""
  <p class="take">Le nombre d'écoles publiques baisse dans <strong>{DE['deps_ecoles_public_en_baisse']} départements sur {len(DE['departements'])}</strong> entre {a0} et {a1}. Dans {DE['deps_ecoles_reculent_plus_que_eleves']} d'entre eux, il baisse plus vite que le nombre d'élèves du public ; dans {DE['deps_ecoles_reculent_eleves_augmentent']}, il baisse alors que les élèves sont plus nombreux.</p>
  <p>Les plus fortes baisses : {nom(c0['departement'], c0['nom'])} ({n(c0['ecoles_public_debut'])} → {n(c0['ecoles_public_fin'])} écoles, pour {signe(c0['pct_eleves_public'])} d'élèves), {nom(c1['departement'], c1['nom'])} ({n(c1['ecoles_public_debut'])} → {n(c1['ecoles_public_fin'])}, élèves {signe(c1['pct_eleves_public'])}), {nom(c2['departement'], c2['nom'])} ({n(c2['ecoles_public_debut'])} → {n(c2['ecoles_public_fin'])}, élèves {signe(c2['pct_eleves_public'])}). Seuls la {', la '.join(x.title() for x in DE['deps_ecoles_public_en_hausse'][:-1])} et {DE['deps_ecoles_public_en_hausse'][-1].title()} comptent plus d'écoles publiques.</p>
  {limite("des baisses aussi fortes peuvent refléter des regroupements administratifs d'écoles autant que des fermetures ; valeurs absolues dans le tableau « Votre département ».")}""")

# --- 2. Le collège : public et privé ------------------------------------------------------------
ss = SG["serie"]
g_seg = courbes([("Collégiens du privé", "var(--alerte)", [x["p_tfav_pr"] for x in ss]),
                 ("Ensemble des collégiens", "var(--dim)", [x["p_tfav"] for x in ss]),
                 ("Collégiens du public", "var(--s1)", [x["p_tfav_pu"] for x in ss])],
                [x["annee"] for x in ss], 10, 50, 10, lambda v: d(v, 1) + "&nbsp;%",
                "Part des collégiens d'origine sociale très favorisée")
s_seg = section("0", "Mixité sociale", f"{d(ss[-1]['p_tfav_pr'])}&nbsp;% des collégiens du privé sont d'origine très favorisée, contre {d(ss[-1]['p_tfav_pu'])}&nbsp;% dans le public", g_seg, f"""
  <p class="take">En {ss[-1]['annee']}, <strong>{d(ss[-1]['p_tfav_pr'])}&nbsp;%</strong> des collégiens du privé sous contrat sont d'origine sociale très favorisée, contre {d(ss[-1]['p_tfav_pu'])}&nbsp;% des collégiens du public. En {ss[0]['annee']}, c'était {d(ss[0]['p_tfav_pr'])}&nbsp;% et {d(ss[0]['p_tfav_pu'])}&nbsp;%. Sur l'ensemble des collégiens, la part passe de {d(ss[0]['p_tfav'])}&nbsp;% à {d(ss[-1]['p_tfav'])}&nbsp;%.</p>
  <p>À l'inverse, {d(ss[-1]['p_defav_pu'])}&nbsp;% des collégiens du public sont d'origine défavorisée, contre {d(ss[-1]['p_defav_pr'])}&nbsp;% dans le privé. La contribution des écarts entre public et privé à la ségrégation sociale entre collèges passe de {d(ss[0]['contrib_interpupr'])}&nbsp;% à <strong>{d(ss[-1]['contrib_interpupr'])}&nbsp;%</strong>, alors que l'indice global de ségrégation reste stable ({d(ss[0]['i_entropie_tot'], 3)} → {d(ss[-1]['i_entropie_tot'], 3)}).</p>
  {lecture("le privé sous contrat accueille une population de plus en plus favorisée, et l'écart avec le public se creuse.")}
  {limite("indicateur publié par la DEPP, métropole et départements d'outre-mer, catégories sociales non renseignées exclues. Prudence pour 2023 : la façon de remonter la catégorie sociale des parents change cette année-là dans le privé. Le financement public du privé n'est pas chiffré dans ce rapport (pas de données ouvertes).")}""",
                legende([("Collégiens du privé", "var(--alerte)"), ("Ensemble", "var(--dim)"), ("Collégiens du public", "var(--s1)")]))

ip_dep = IP["classement_ecart_departemental"]
g_ips = barres_h([(nom(o["departement"], o["nom"]), o["ecart"]) for o in ip_dep], lambda v: "+" + d(v),
                 f"Écart d'indice de position sociale entre collèges privés et publics, {IP['rentree']}", couleur="var(--alerte)")
s_ips = section("0", "Origine sociale", f"Indice de position sociale : {d(IP['national_prive'])} dans les collèges privés, {d(IP['national_public'])} dans le public", g_ips, f"""
  <p class="take">À la rentrée {IP['rentree']}, l'indice de position sociale (IPS) des collèges privés sous contrat est de <strong>{d(IP['national_prive'])}</strong>, contre {d(IP['national_public'])} dans le public. Plus l'indice est élevé, plus les élèves viennent de milieux favorisés.</p>
  <p>Dans les <strong>{IP['deps_prive_plus_favorise']} départements</strong> qui ont des collèges privés sous contrat, l'IPS du privé dépasse celui du public ; l'écart le plus faible est de {d(IP['ecart_min_departemental'])} points. Les écarts les plus forts s'observent en {nom(ip_dep[0]['departement'], ip_dep[0]['nom'])} (+{d(ip_dep[0]['ecart'])} points) et à {nom(ip_dep[1]['departement'], ip_dep[1]['nom'])} (+{d(ip_dep[1]['ecart'])}), puis dans les {nom(ip_dep[2]['departement'], ip_dep[2]['nom'])} (+{d(ip_dep[2]['ecart'])}). {' et '.join(x.title() for x in IP['deps_sans_prive'])} n'ont pas de collège privé.</p>
  {limite(f"IPS publiés par la DEPP pour les collèges de 101 départements, départements d'outre-mer compris ({n(IP['colleges_101_departements']['public'])} publics, {n(IP['colleges_101_departements']['prive'])} privés sous contrat) ; série commencée en 2023-2024, non comparable avec l'IPS publié avant 2022. La DEPP déconseille d'interpréter des écarts de 3 points ou moins.")}""")

# --- 3. Le supérieur ---------------------------------------------------------------------------
su = SU["serie"]
ho, lo = SU["homogene"], SU["longue_hors_apprentis"]
i_h = [x["annee"] for x in su].index(ho["debut"])
g_sup = courbes([("Tous inscrits (depuis 2015-16)", "var(--alerte)", [x["part_prive"] if i >= i_h else None for i, x in enumerate(su)]),
                 ("Hors apprentis de STS", "var(--s1)", [x["part_prive_hors_apprentis_sts"] for x in su])],
                [x["annee"][:4] for x in su], 10, 30, 5, lambda v: d(v, 1) + "&nbsp;%",
                "Part des étudiants inscrits dans un établissement privé")
s_sup = section("0", "Enseignement supérieur", f"Depuis {ho['debut']}, le privé gagne {pct(ho['prive']['pct'], False)} d'étudiants, le public {pct(ho['public']['pct'], False)}", g_sup, f"""
  <p class="take">Entre {ho['debut']} et {ho['fin']}, les établissements privés passent de {n(ho['prive']['debut'])} à <strong>{n(ho['prive']['fin'])}</strong> étudiants ({pct(ho['prive']['pct'])}), le public de {n(ho['public']['debut'])} à {n(ho['public']['fin'])} ({pct(ho['public']['pct'])}). Le privé accueille désormais <strong>{d(ho['part_prive_fin'])}&nbsp;%</strong> des étudiants, contre {d(ho['part_prive_debut'])}&nbsp;% en {ho['debut']}.</p>
  <p>Sur une période plus longue, et sans les apprentis de STS (comptés seulement depuis {ho['debut']}), le privé passe de {n(lo['prive']['debut'])} étudiants en {lo['debut']} à {n(lo['prive']['fin'])} en {lo['fin']} ({pct(lo['prive']['pct'])}) ; sa part, de {d(lo['part_prive_debut'])}&nbsp;% à {d(lo['part_prive_fin'])}&nbsp;%. La part du privé a culminé à {d(SU['pic_part_prive']['part'])}&nbsp;% en {SU['pic_part_prive']['annee']} et recule légèrement depuis.</p>
  {lecture(f"depuis {ho['debut']}, la croissance de l'enseignement supérieur passe d'abord par le privé : {n(ho['prive']['ecart'])} étudiants de plus, contre {n(ho['public']['ecart'])} dans le public.")}
  {limite(f"SIES, France entière. Deux changements de comptage en {ho['debut']} : fin des doubles inscriptions classes préparatoires/université comptées deux fois (le public est surestimé avant) et entrée des apprentis de STS. La source ne distingue pas le privé lucratif du privé non lucratif. Écoles paramédicales et sociales : données provisoires pour {ho['fin']}.")}""",
                legende([("Tous inscrits", "var(--alerte)"), ("Hors apprentis de STS", "var(--s1)")]))

cr = [o for o in SU["croissance_prive_par_regroupement"] if not o["reclassement_probable"] and o["ecart"] > 0][:6]
sts = SU["sts_prive"]
g_reg = barres_h([(o["regroupement"].replace(" et assimilés", "").replace(", gestion et comptabilité", ""), o["ecart"]) for o in cr],
                 lambda v: "+" + n(v), f"Étudiants supplémentaires dans le privé, de {ho['debut']} à {ho['fin']}, par type de formation",
                 couleur="var(--alerte)")
s_reg = section("0", "Où croît le privé", f"Écoles de commerce privées : {n(cr[0]['debut'])} étudiants en {ho['debut']}, {n(cr[0]['fin'])} en {ho['fin']}", g_reg, f"""
  <p class="take">La croissance du privé se concentre dans les <strong>écoles de commerce, de gestion et de comptabilité</strong> : {n(cr[0]['ecart'])} étudiants de plus entre {ho['debut']} et {ho['fin']}.</p>
  <p>Dans les sections de techniciens supérieurs (STS) privées, la hausse vient entièrement de l'apprentissage : les apprentis passent de {n(sts['apprentis']['debut'])} à {n(sts['apprentis']['fin'])}, tandis que les autres étudiants baissent de {n(sts['hors_apprentis']['debut'])} à {n(sts['hors_apprentis']['fin'])}.</p>
  {limite("types de formation regroupés par le SIES ; les universités et grands établissements privés, quasi absents en 2015-2016, relèvent probablement de changements de classement et ne sont pas présentés.")}""")

# --- 4. Tableau par département ------------------------------------------------------------------
seg_dep, ips_dep, sup_dep = SG["par_departement"], IP["par_departement"], SU["par_departement"]


def cellule(v, fmt):
    return f'<td class="num" data-v="{v if v is not None else ""}">{fmt(v) if v is not None else "–"}</td>'


lignes = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td><td data-v="{nom(o["departement"], o["nom"])}">{nom(o["departement"], o["nom"])}</td>'
    + cellule(o["ecoles_public_debut"], n) + cellule(o["ecoles_public_fin"], n) + cellule(o["pct_ecoles_public"], signe)
    + cellule(o["pct_eleves_public"], signe) + cellule(o["eleves_par_classe_public_fin"], d)
    + cellule(o["part_eleves_prive_fin"], lambda v: d(v) + "&nbsp;%")
    + cellule(seg_dep.get(o["departement"], {}).get("poids_prive"), lambda v: d(v) + "&nbsp;%")
    + cellule(ips_dep.get(o["departement"], {}).get("ips_public"), d) + cellule(ips_dep.get(o["departement"], {}).get("ips_prive"), d)
    + cellule(sup_dep.get(o["departement"], {}).get("part_prive"), lambda v: d(v) + "&nbsp;%") + "</tr>"
    for o in DE["departements"])
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Écoles, collèges et supérieur, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un nom ou un numéro pour filtrer.</p>
  <input id="filtre" type="search" placeholder="Rechercher un département…" aria-label="Rechercher un département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>N°</th><th>Département</th><th class="num">Écoles publiques {a0}</th><th class="num">Écoles publiques {a1}</th><th class="num">Évolution</th><th class="num">Élèves du public, évolution</th><th class="num">Élèves par classe, public {a1}</th><th class="num">Élèves du premier degré dans le privé {a1}</th><th class="num">Collégiens dans le privé {ss[-1]['annee']}</th><th class="num">IPS collèges publics {IP['rentree']}</th><th class="num">IPS collèges privés {IP['rentree']}</th><th class="num">Étudiants dans le privé {ho['fin']}</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
  <p><strong>Sources :</strong> DEPP (écoles, ségrégation sociale des collèges, IPS) ; SIES (étudiants, département de la commune d'inscription). « – » : pas de collège privé ou donnée absente. Écoles : un numéro d'école disparu peut correspondre à une fusion.</p>
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

# --- Synthèse, fiabilité, sources, assemblage ----------------------------------------------------
casse = casse_en_chiffres("La casse en chiffres", [
    f"<strong>{n(-EC['ecoles_public']['ecart'])} écoles publiques en moins</strong> entre {a0} et {a1} ({pct(EC['ecoles_public']['pct'])}), fermetures, fusions et changements de numéro confondus ; moins d'écoles publiques dans {DE['deps_ecoles_public_en_baisse']} départements sur {len(DE['departements'])}.",
    f"<strong>{pct(EC['petites_ecoles_public']['pct'], False)} d'écoles publiques à une ou deux classes</strong> en moins ({n(EC['petites_ecoles_public']['debut'])} → {n(EC['petites_ecoles_public']['fin'])}).",
    f"Collégiens d'origine très favorisée : <strong>{d(ss[-1]['p_tfav_pr'])}&nbsp;%</strong> des collégiens du privé en {ss[-1]['annee']} ({d(ss[0]['p_tfav_pr'])}&nbsp;% en {ss[0]['annee']}), {d(ss[-1]['p_tfav_pu'])}&nbsp;% de ceux du public.",
    f"Indice de position sociale des collèges : <strong>{d(IP['national_prive'])}</strong> dans le privé, {d(IP['national_public'])} dans le public ({IP['rentree']}).",
    f"Supérieur : <strong>{pct(ho['prive']['pct'])}</strong> d'étudiants dans le privé entre {ho['debut']} et {ho['fin']}, contre {pct(ho['public']['pct'])} dans le public ; le privé accueille {d(ho['part_prive_fin'])}&nbsp;% des étudiants.",
], note=f"« Casse » : notre lecture de ces évolutions. Elles ne disent pas tout : le public compte {pct(EC['eleves_public']['pct'], False)} d'élèves en moins dans le premier degré, ses classes sont plus nombreuses ({pct(EC['classes_public']['pct'])}) et moins chargées ({d(se[0]['eleves_par_classe_public'])} → {d(se[-1]['eleves_par_classe_public'])} élèves), et la part du privé dans le supérieur recule légèrement depuis {SU['pic_part_prive']['annee']}. Chaque chiffre est détaillé, sourcé et assorti de ses limites dans la suite du rapport.")

fiab = f"""
<section id="fiabilite">
  <h3>0 · Fiabilité</h3>
  <h2>Ce qu'il faut garder en tête</h2>
  <div class="tbl"><table>
    <tr><th>Donnée</th><th>Limite</th><th>Conséquence</th></tr>
    <tr><td>Écoles (DEPP)</td><td>Un numéro d'école disparu peut être une fermeture, une fusion ou un changement de numéro ({n(EC['uai_public_sorties'])} sorties, {n(EC['uai_public_entrees'])} entrées) ; pas de code commune ; quelques effectifs masqués par le secret statistique</td><td>On parle d'écoles « en moins », pas de fermetures ; pas d'analyse par commune</td></tr>
    <tr><td>Périmètre des écoles</td><td>Collectivités d'outre-mer présentes seulement depuis 2019</td><td>101 départements</td></tr>
    <tr><td>Ségrégation sociale (DEPP)</td><td>Indicateur technique ; changement de recueil de la catégorie sociale dans le privé en 2023</td><td>Tendances plus solides que les écarts d'une année</td></tr>
    <tr><td>IPS des collèges</td><td>Nouvelle série depuis 2023-2024</td><td>Pas de comparaison avec l'IPS d'avant 2022</td></tr>
    <tr><td>Supérieur (SIES)</td><td>Deux changements de comptage en {ho['debut']} ; privé lucratif non isolable ; écoles paramédicales provisoires en {ho['fin']}</td><td>Comparaison principale de {ho['debut']} à {ho['fin']} ; série longue hors apprentis</td></tr>
    <tr><td>Absent des données ouvertes</td><td>Financement public du privé, dépense par élève, postes d'enseignants et contractuels, accompagnants d'élèves handicapés, médecine scolaire</td><td>Non traités dans ce rapport</td></tr>
  </table></div>
</section>"""
date = open("donnees_brutes/education/date_telechargement.txt", encoding="utf-8").read().strip()
sources = f"""
<section>
  <h3>Sources</h3>
  <p>Direction de l'évaluation, de la prospective et de la performance (DEPP, ministère chargé de l'éducation nationale, data.education.gouv.fr, Licence Ouverte v2.0) : effectifs d'élèves et nombre de classes par école (rentrées 2009 à 2025) ; indicateur de ségrégation sociale entre collèges publics et privés (2014 à 2025) ; indice de position sociale des collèges (depuis 2023-2024). Sous-direction des systèmes d'information et des études statistiques (SIES, ministère chargé de l'enseignement supérieur, data.enseignementsup-recherche.gouv.fr, Licence Ouverte v2.0) : effectifs d'étudiants inscrits, version agrégeable (2001-2002 à 2025-2026). Téléchargement du {date}.</p>
  <p>Calculs rejouables : <code>nettoyer_education.py</code>, <code>calculer_chiffres_education.py</code> puis <code>generer_rapport_education.py</code>.</p>
</section>"""
bandeau = ('<div class="take" style="border-color:var(--warn)"><strong>Brouillon en cours de vérification</strong> : '
           'chiffres non encore validés de façon indépendante, ne pas diffuser.</div>') if BROUILLON else ""
tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">−{n(-EC['ecoles_public']['ecart'])}</div><div class="l">écoles publiques ({a0}-{a1}, fermetures, fusions et changements de numéro confondus)</div></div>
    <div class="tile"><div class="v">{pct(EC['petites_ecoles_public']['pct'])}</div><div class="l">d'écoles publiques à une ou deux classes</div></div>
    <div class="tile"><div class="v">{d(ss[-1]['p_tfav_pr'], 0)}&nbsp;%</div><div class="l">des collégiens du privé d'origine très favorisée ({d(ss[-1]['p_tfav_pu'], 0)}&nbsp;% dans le public)</div></div>
    <div class="tile"><div class="v">{pct(ho['prive']['pct'])}</div><div class="l">d'étudiants dans le privé (de {ho['debut']} à {ho['fin']}), {pct(ho['public']['pct'])} dans le public</div></div>
  </div>"""
entete = f"""
<header>
  <div class="eyebrow">Éducation · données DEPP et SIES</div>
  <h1>{n(-EC['ecoles_public']['ecart'])} écoles publiques en moins, des collèges privés de plus en plus favorisés, un supérieur privé qui croît bien plus vite que le public depuis 2015</h1>
  <p class="lead">Ce que disent les données publiques sur l'école, le collège et l'enseignement supérieur. Chaque chiffre vient d'une source publique et peut être recalculé ou vérifié à la source ; chaque graphique est accompagné de ses limites.</p>
  {bandeau}
  {tuiles}
</header>""" + casse


# --- Carte par département (mêmes valeurs que le tableau « Votre département ») ----------------------------
def pc(v):
    return d(v) + "&nbsp;%"


DC = {o["departement"]: o for o in DE["departements"]}
s_carte = section_carte("La carte", "L'école, le collège et le supérieur, département par département", carte_departements("carte-education", [
    {"libelle": "Écoles publiques", "legende": f"Évolution du nombre d'écoles publiques, {a0}-{a1}",
     "valeurs": {k: o["pct_ecoles_public"] for k, o in DC.items()}, "fmt": signe, "inverse": True},
    {"libelle": "Privé à l'école", "legende": f"Part des élèves du premier degré scolarisés dans le privé sous contrat ({a1})",
     "valeurs": {k: o["part_eleves_prive_fin"] for k, o in DC.items()}, "fmt": pc},
    {"libelle": "Privé au collège", "legende": f"Part des collégiens scolarisés dans le privé sous contrat ({ss[-1]['annee']})",
     "valeurs": {k: o["poids_prive"] for k, o in seg_dep.items()}, "fmt": pc},
    {"libelle": "Écart social au collège", "legende": f"Écart d'indice de position sociale entre collèges privés et publics ({IP['rentree']})",
     "valeurs": {k: (round(o["ips_prive"] - o["ips_public"], 1) if o["ips_prive"] is not None else None) for k, o in ips_dep.items()},
     "fmt": lambda v: "+" + d(v) + " points"},
    {"libelle": "Privé dans le supérieur", "legende": f"Part des étudiants inscrits dans un établissement privé ({ho['fin']})",
     "valeurs": {k: o["part_prive"] for k, o in sup_dep.items()}, "fmt": pc},
], "Carte de l'éducation par département"), f"""
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons changent d'indicateur. Plus la teinte est foncée, plus la situation est défavorable. Les valeurs sont celles du tableau « Votre département » ci-dessous.</p>
  <p class="limite"><strong>Limites :</strong> classes de couleur = cinquièmes des départements ; écoles : une école en moins peut être une fermeture, une fusion ou un changement de numéro ; collège : pas de valeur pour les départements sans collège privé ; supérieur : département de la commune d'inscription, et non du domicile des étudiants.</p>""")


def partie(ident, titre, intro):
    return f'<div class="partie" id="{ident}"><div class="eyebrow">{titre}</div><p class="lead">{intro}</p></div>'


PARTIES = [
    ("ecole", "L'école primaire", "Écoles, élèves et classes, public et privé sous contrat.", [s_ec, s_pet, s_cl, s_dep]),
    ("college", "Le collège", "Qui va dans le public, qui va dans le privé.", [s_seg, s_ips]),
    ("superieur", "L'enseignement supérieur", "La place croissante des établissements privés.", [s_sup, s_reg]),
]
sommaire = ('<nav class="sommaire" aria-label="Sommaire">' + "".join(f'<a href="#{i}">{t}</a>' for i, t, _, _ in PARTIES)
            + '<a href="#carte">La carte</a><a href="#departements">Votre département</a><a href="#fiabilite">Fiabilité</a></nav>')
corps = "".join(partie(i, t, intro) + "".join(secs) for i, t, intro, secs in PARTIES) + s_carte + tableau + fiab
compteur = iter(range(1, 100))
corps = re.sub(r"<h3>\d+ · ", lambda _: f"<h3>{next(compteur)} · ", corps)
corps = alleger_limites(corps)  # version presse : limites repliables, jamais supprimées

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
tete = re.sub(r"<title>.*?</title>", "<title>Éducation publique</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">" + entete + sommaire + corps + sources
        + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques){' — BROUILLON' if BROUILLON else ''}")
