"""Génère rapport_logement.html à partir de donnees_propres/logement/chiffres_logement.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Style repris de rapport_lots.html (EDR-011),
graphiques du module partagé graphiques_svg.py, ton « offensif mais inattaquable » (EDR-012).
Usage : python3 generer_rapport_logement.py [--brouillon]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
from graphiques_svg import (STYLE_MILITANT, barres_groupees, barres_h, casse_en_chiffres, courbes, d, lecture,  # noqa: E402
                            limite, n, pct, section)
from graphiques_svg import alleger_limites  # noqa: E402
from cartes_svg import STYLE_CARTE, carte_departements, section_carte  # noqa: E402

FICHE = "donnees_propres/logement/chiffres_logement.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapport_logement.html"
BROUILLON = "--brouillon" in sys.argv

C = json.load(open(FICHE, encoding="utf-8"))
PA, SO, SR, AI, CA, DE = (C[k] for k in ("parc", "sorties", "sru", "aides", "caf", "departements"))
# Noms des territoires d'outre-mer (absents de l'onglet départemental du RPLS, présents dans les données SRU et Caf)
NOMS_DROM = {"971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion", "976": "Mayotte", "978": "Saint-Martin"}
NOMS = {o["departement"]: o["nom"] for o in DE["departements"]} | NOMS_DROM


def md(v):
    """Montant en milliards d'euros, deux décimales : 16,43 -> « 16,43 Md€ »."""
    return d(v, 2) + "&nbsp;Md€"


# --- 1. Construire : les mises en service --------------------------------------------------------
se = PA["serie"]
pic, der = PA["mises_en_service_pic"], PA["mises_en_service_derniere"]
bas = min(se, key=lambda x: x["mises_en_service"])
g_mes = barres_groupees([(x["annee_mise_en_service"][2:], [x["mises_en_service"] / 1000]) for x in se], ["var(--alerte)"], 100, 20,
                        lambda v: d(v, 0), "Logements sociaux mis en service chaque année, en milliers (France métropolitaine)")
s_mes = section("0", "Production", f"{pct(PA['mises_en_service_vs_pic']['pct'], False)} de logements sociaux mis en service en moins qu'en {pic['annee_mise_en_service']}", g_mes, f"""
  <p class="take">En {der['annee_mise_en_service']}, <strong>{n(der['valeur'])}</strong> logements sociaux ont été mis en service en France métropolitaine, contre {n(pic['valeur'])} en {pic['annee_mise_en_service']}, le niveau le plus élevé de la période {se[0]['annee_mise_en_service']}-{der['annee_mise_en_service']} : <strong>{n(-PA['mises_en_service_vs_pic']['ecart'])} de moins</strong> ({pct(PA['mises_en_service_vs_pic']['pct'])}).</p>
  <p>Le point bas de la période est atteint en {bas['annee_mise_en_service']} ({n(bas['mises_en_service'])}). Depuis, la production ne retrouve pas son niveau du milieu des années 2010.</p>
  {lecture("l'offre nouvelle de logements sociaux reste nettement inférieure à celle du milieu des années 2010.")}
  {limite("une mise en service n'est pas une construction : elle comprend les logements construits par les bailleurs, achetés sur plan à des promoteurs (VEFA) ou acquis dans l'ancien. Année de mise en service = année précédant le 1er janvier de la colonne du RPLS (12 = 2012). Départements d'outre-mer non compris.")}""")

g_parc = courbes([("Parc social", "var(--s1)", [x["logements_sociaux"] / 1e6 for x in se])], [x["annee"] for x in se], 4.4, 5.4, 0.2,
                 lambda v: d(v, 1), "Logements du parc social au 1er janvier, en millions (France métropolitaine)",
                 mention="Millions de logements (axe tronqué)")
s_parc = section("0", "Le parc", f"Le parc social continue de grandir : {n(PA['parc']['fin'])} logements au 1er janvier {se[-1]['annee']}", g_parc, f"""
  <p class="take">Le parc locatif social compte <strong>{n(PA['parc']['fin'])}</strong> logements au 1er janvier {se[-1]['annee']} en France métropolitaine, contre {n(PA['parc']['debut'])} en {se[0]['annee']} ({pct(PA['parc']['pct'])}).</p>
  <p>Entre le 1er janvier {se[-2]['annee']} et le 1er janvier {se[-1]['annee']}, il gagne {n(PA['hausse_parc_derniere_annee'])} logements, après les ventes et les démolitions de l'année.</p>
  {limite("rupture de série en 2023 (méthode du SDES revue) : effet mesuré de −2 012 logements en 2023, années 2013 à 2022 non recalculées. Champ « décret » : hors logements non conventionnés des sociétés d'économie mixte.")}""")

cl = DE["classement_baisse_mises_en_service"]
g_dep = barres_h([(o["nom"], -o["pct_mises_en_service"]) for o in cl], lambda v: "−" + d(v) + "&nbsp;%",
                 "Baisse des mises en service annuelles moyennes, 2013-2015 contre 2022-2024", couleur="var(--alerte)", vmax=100)
s_dep = section("0", "Par département", f"Les mises en service reculent dans {DE['deps_mises_en_service_en_baisse']} départements sur {len(DE['departements'])}", g_dep, f"""
  <p class="take">En moyenne annuelle, les mises en service de logements sociaux de 2022-2024 sont inférieures à celles de 2013-2015 dans <strong>{DE['deps_mises_en_service_en_baisse']} départements sur {len(DE['departements'])}</strong>.</p>
  <p>Parmi les départements qui en mettaient au moins {DE['seuil_classement']} en service par an, les baisses les plus fortes : {cl[0]['nom']} ({n(cl[0]['mises_en_service_2013_2015'])} par an, puis {n(cl[0]['mises_en_service_2022_2024'])}), {cl[1]['nom']} ({n(cl[1]['mises_en_service_2013_2015'])} puis {n(cl[1]['mises_en_service_2022_2024'])}), {cl[2]['nom']} ({n(cl[2]['mises_en_service_2013_2015'])} puis {n(cl[2]['mises_en_service_2022_2024'])}).</p>
  {limite(f"moyennes annuelles sur trois ans ; classement limité aux départements ayant au moins {DE['seuil_classement']} mises en service par an en 2013-2015, les pourcentages étant fragiles sur de petits nombres ; valeurs absolues dans le tableau « Votre département ».")}""")

# --- 2. Sortir du parc : ventes et démolitions ---------------------------------------------------
s25, s24 = SO["par_millesime"]["2025"], SO["par_millesime"]["2024"]
g_sort = barres_h([("Démolitions", s25["demolitions"]), ("Ventes à l'occupant et autres", s25["ventes_occupant_et_autres"]),
                   ("Ventes à un autre bailleur social", s25["ventes_autre_bailleur"]), ("Autres motifs", s25["autres_motifs"])],
                  n, f"Logements sortis du parc social en {s25['annee_des_sorties']}, par motif",
                  couleur=lambda i, v: "var(--alerte)" if i < 2 else "var(--dim)")
s_sort = section("0", "Ventes et démolitions", f"Pour 100 logements sociaux mis en service en {s25['annee_des_sorties']}, {d(s25['pour_100_mises_en_service'], 0)} ont été démolis ou vendus à leur occupant ou à d'autres acquéreurs", g_sort, f"""
  <p class="take">En {s25['annee_des_sorties']}, <strong>{n(s25['demolitions'])}</strong> logements sociaux ont été démolis et <strong>{n(s25['ventes_occupant_et_autres'])}</strong> vendus à leur occupant ou à d'autres acquéreurs (« autres ventes »), hors ventes entre bailleurs sociaux.</p>
  <p>Rapporté aux {n(s25['mises_en_service_meme_annee'])} mises en service de la même année, cela fait <strong>{d(s25['pour_100_mises_en_service'])} logements</strong> sortis pour 100 mis en service ({d(s24['pour_100_mises_en_service'])} en {s24['annee_des_sorties']}). S'y ajoutent {n(s25['ventes_autre_bailleur'])} logements vendus à un autre bailleur social.</p>
  {lecture("une partie de l'effort de production est absorbée par les démolitions et par les ventes : le parc progresse bien moins vite que ce que les mises en service laissent croire.")}
  {limite(f"deux années seulement ({s24['annee_des_sorties']} et {s25['annee_des_sorties']}) : pas de tendance. Le rapport « pour 100 » n'est pas un solde. La source ne précise pas qui achète lors d'une « autre vente ». Une démolition peut s'inscrire dans une opération de rénovation urbaine avec reconstruction. France métropolitaine.")}""")

# --- 3. La loi SRU ----------------------------------------------------------------------------
sd = SR["dernier"]
top_sru = sorted(SR["par_departement"].items(), key=lambda kv: (-kv[1]["deficitaires"], kv[0]))[:15]
g_sru = barres_h([(NOMS.get(k, k), v["deficitaires"]) for k, v in top_sru], n,
                 f"Communes déficitaires au regard de la loi SRU, inventaire {sd['millesime']}, par département", couleur="var(--alerte)")
sans = SR["communes_sans_marqueur_deficitaire"]
s_sru = section("0", "Loi SRU", f"{n(sd['deficitaires_marquees'])} communes sur {n(sd['communes_sru'])} sont déficitaires au regard de la loi SRU", g_sru, f"""
  <p class="take">D'après l'inventaire {sd['millesime']}, <strong>{n(sd['deficitaires_marquees'])} communes</strong> soumises à la loi SRU sur {n(sd['communes_sru'])} ({d(SR['part_deficitaires'])}&nbsp;%) sont déficitaires : elles comptent moins de logements sociaux que leur objectif de 20 ou 25&nbsp;% et ne sont pas exemptées.</p>
  <p><strong>{n(sd['carencees'])} communes</strong> sont carencées pour la période 2023-2025 : un arrêté préfectoral de carence a été pris. Le prélèvement net (dont majoration) inscrit à l'inventaire {sd['millesime']} s'élève à {d(sd['prelevement_net_m'])}&nbsp;M€, pour {n(sd['communes_avec_prelevement'])} communes.</p>
  {lecture("plus d'une commune concernée sur deux n'a pas atteint son obligation, et des centaines paient un prélèvement faute de l'atteindre.")}
  {limite(f"France entière (dont {SR['drom']['communes_sru']} communes d'outre-mer). Logements sociaux au 1er janvier {sd['annee_inventaire']}. {len(sans)} communes sans indication dans l'inventaire ({', '.join(c.title() for c in sans)}). La définition de « déficitaire » varie selon les millésimes : aucune évolution du nombre de communes déficitaires n'est présentée. Nombres absolus : un département compte d'autant plus de communes déficitaires qu'il a de communes soumises à la loi (voir le tableau, colonne « Communes SRU »).")}""")

# --- 4. Les aides au logement ------------------------------------------------------------------
sa = AI["serie"]
a17 = next(x for x in sa if x["annee"] == "2017")
g_aides = barres_groupees([(x["annee"][2:], [x["montant_md"]]) for x in sa if int(x["annee"]) >= 2012], ["var(--s1)"], 20, 5,
                          lambda v: d(v, 1), "Aides personnelles au logement (APL, ALS, ALF), en milliards d'euros courants")
s_aides = section("0", "Aides au logement", f"{md(-AI['montant_2017_2025']['ecart'])} d'aides personnelles au logement en moins qu'en 2017, en euros courants", g_aides, f"""
  <p class="take">Les aides personnelles au logement (APL et allocations logement) représentent <strong>{md(AI['montant_2017_2025']['fin'])}</strong> en {sa[-1]['annee']}, contre {md(AI['montant_2017_2025']['debut'])} en 2017 ({pct(AI['montant_2017_2025']['pct'])}), en euros courants, c'est-à-dire sans tenir compte de la hausse des prix.</p>
  <p>Le nombre de bénéficiaires passe de {d(AI['beneficiaires_2017_2025']['debut'], 2)} à <strong>{d(AI['beneficiaires_2017_2025']['fin'], 2)} millions</strong> ({n(-AI['beneficiaires_2017_2025']['ecart_milliers'])} milliers de moins). Le montant mensuel moyen de l'APL passe de {n(a17['moyenne_mensuelle_apl'])}&nbsp;€ à {n(sa[-1]['moyenne_mensuelle_apl'])}&nbsp;€ ; celui des allocations logement augmente, de {n(a17['moyenne_mensuelle_al'])}&nbsp;€ à {n(sa[-1]['moyenne_mensuelle_al'])}&nbsp;€.</p>
  <p>L'ensemble des aides au logement, qui comprend aussi les avantages fiscaux et les subventions, augmente sur la même période : {d(a17['ensemble_aides_md'])} → {d(sa[-1]['ensemble_aides_md'])}&nbsp;Md€.</p>
  {lecture("l'aide personnelle au logement, versée sous condition de ressources, recule pendant que l'ensemble des aides au logement, avantages fiscaux compris, progresse.")}
  {limite("compte du logement 2025 (SDES), France entière, euros courants ; aucune évolution en euros constants n'est calculée. Années en abscisse : 12 = 2012. Les causes de ces évolutions ne sont pas documentées par la source.")}""")

cs = CA["serie_mars"]
top_caf = sorted([(k, o) for k, o in CA["par_departement"].items() if k in NOMS], key=lambda kv: kv[1]["foyers_fin"] / kv[1]["foyers_debut"])[:15]  # tri sur les valeurs non arrondies
g_caf = barres_h([(NOMS[k], -o["pct_foyers"]) for k, o in top_caf], lambda v: "−" + d(v) + "&nbsp;%",
                 "Baisse du nombre de foyers aidés par les Caf, mars 2017 - mars 2026", couleur="var(--alerte)")
s_caf = section("0", "Foyers aidés par territoire", f"{n(-CA['foyers']['ecart'])} foyers aidés de moins par les Caf entre mars 2017 et mars 2026", g_caf, f"""
  <p class="take">En mars {CA['periode'][1][:4]}, <strong>{n(CA['foyers']['fin'])}</strong> foyers allocataires des Caf reçoivent une aide au logement, contre {n(CA['foyers']['debut'])} en mars {CA['periode'][0][:4]} ({pct(CA['foyers']['pct'])}).</p>
  <p>Le nombre de foyers aidés baisse dans <strong>{CA['territoires_en_baisse']} territoires sur {CA['nb_territoires']}</strong>. Le montant moyen versé par foyer passe de {n(CA['moyenne']['debut'])}&nbsp;€ à {n(CA['moyenne']['fin'])}&nbsp;€ par mois ({pct(CA['moyenne']['pct'])}, en euros courants). La part des foyers aidés logés dans le parc public passe de {d(cs[0]['part_parc_public'])}&nbsp;% à {d(cs[-1]['part_parc_public'])}&nbsp;%.</p>
  {limite("Cnaf, foyers bénéficiant d'au moins une aide au logement dans le mois, par département de résidence ; allocataires des Caf seulement. Comparaison des mois de mars. Une baisse du nombre de foyers aidés peut aussi refléter des changements de revenus ou de situation des ménages.")}""")

# --- 5. Tableau par département ------------------------------------------------------------------
sru_dep, caf_dep = SR["par_departement"], CA["par_departement"]


def cellule(v, fmt):
    return f'<td class="num" data-v="{v if v is not None else ""}">{fmt(v) if v is not None else "–"}</td>'


def signe(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%"


lignes = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td><td data-v="{o["nom"]}">{o["nom"]}</td>'
    + cellule(o["parc_2025"], n) + cellule(o["pct_parc"], signe)
    + cellule(o["mises_en_service_2013_2015"], n) + cellule(o["mises_en_service_2022_2024"], n)
    + cellule(o["pct_mises_en_service"], signe)
    + cellule(o["ventes_occupant_et_autres_2024"], n) + cellule(o["demolitions_2024"], n)
    + cellule(sru_dep.get(o["departement"], {}).get("deficitaires"), n)
    + cellule(sru_dep.get(o["departement"], {}).get("communes_sru"), n)
    + cellule(caf_dep.get(o["departement"], {}).get("foyers_fin"), n)
    + cellule(caf_dep.get(o["departement"], {}).get("pct_foyers"), signe) + "</tr>"
    for o in DE["departements"])
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Logement social et aides au logement, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un nom ou un numéro pour filtrer.</p>
  <input id="filtre" type="search" placeholder="Rechercher un département…" aria-label="Rechercher un département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>N°</th><th>Département</th><th class="num">Logements sociaux au 1er janvier 2025</th><th class="num">Évolution 2013-2025</th><th class="num">Mises en service par an 2013-2015</th><th class="num">Mises en service par an 2022-2024</th><th class="num">Évolution</th><th class="num">Ventes à l'occupant et autres ventes 2024</th><th class="num">Démolitions 2024</th><th class="num">Communes SRU déficitaires (inventaire {sd['millesime']})</th><th class="num">Communes SRU</th><th class="num">Foyers aidés par les Caf, mars 2026</th><th class="num">Évolution depuis mars 2017</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
  <p><strong>Sources :</strong> SDES, RPLS 2025 (parc au 1er janvier, mises en service, sorties de l'année 2024 ; rupture de série en 2023) ; inventaire SRU {sd['millesime']} ; Cnaf (département de résidence). France métropolitaine : les départements d'outre-mer ne figurent pas dans l'onglet départemental du RPLS.</p>
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
    f"<strong>{pct(PA['mises_en_service_vs_pic']['pct'])}</strong> de logements sociaux mis en service en {der['annee_mise_en_service']} par rapport à {pic['annee_mise_en_service']} ({n(pic['valeur'])} → {n(der['valeur'])}, France métropolitaine) ; en moyenne annuelle (2022-2024 contre 2013-2015), baisse dans {DE['deps_mises_en_service_en_baisse']} départements sur {len(DE['departements'])}.",
    f"En {s25['annee_des_sorties']}, en France métropolitaine, <strong>{n(s25['demolitions_et_ventes_occupant_et_autres'])} logements sociaux</strong> démolis ou vendus à leur occupant ou à d'autres acquéreurs, soit {d(s25['pour_100_mises_en_service'], 0)} pour 100 mis en service.",
    f"<strong>{md(-AI['montant_2017_2025']['ecart'])}</strong> d'aides personnelles au logement en moins entre 2017 et {sa[-1]['annee']} (France entière, euros courants), et {n(-AI['beneficiaires_2017_2025']['ecart_milliers'])} milliers de bénéficiaires en moins.",
    f"<strong>{n(-CA['foyers']['ecart'])} foyers</strong> aidés de moins par les Caf entre mars 2017 et mars 2026 (France entière) ; baisse dans {CA['territoires_en_baisse']} territoires sur {CA['nb_territoires']}.",
    f"<strong>{n(sd['deficitaires_marquees'])} communes</strong> sur {n(sd['communes_sru'])} déficitaires au sens de la loi SRU (inventaire {sd['millesime']}, France entière), dont {n(sd['carencees'])} carencées.",
], note=f"« Casse » : notre lecture de ces évolutions. Elles ne disent pas tout : le parc social continue de croître ({pct(PA['parc']['pct'])} depuis 2013, rupture de série en 2023), les mises en service progressent en {se[-2]['annee_mise_en_service']} et {der['annee_mise_en_service']} ({n(se[-3]['mises_en_service'])} → {n(der['valeur'])}) et dépassent leur point bas de {bas['annee_mise_en_service']} ({n(bas['mises_en_service'])}), le montant moyen des allocations logement augmente, et l'ensemble des aides au logement (avantages fiscaux compris) progresse. Chaque chiffre est détaillé, sourcé et assorti de ses limites dans la suite du rapport.")

fiab = f"""
<section id="fiabilite">
  <h3>0 · Fiabilité</h3>
  <h2>Ce qu'il faut garder en tête</h2>
  <div class="tbl"><table>
    <tr><th>Donnée</th><th>Limite</th><th>Conséquence</th></tr>
    <tr><td>Parc social (RPLS)</td><td>Rupture de série en 2023 (−2 012 logements) ; années antérieures non recalculées ; départements d'outre-mer absents de l'onglet départemental</td><td>Évolutions 2013-2025 à lire avec cette réserve ; chiffres de France métropolitaine</td></tr>
    <tr><td>Mises en service</td><td>Comprennent constructions, achats sur plan et acquisitions</td><td>Ne pas parler de « constructions »</td></tr>
    <tr><td>Ventes et démolitions</td><td>Deux années ; « autre vente » non définie par la source</td><td>Pas de tendance ; pas de « ventes au privé »</td></tr>
    <tr><td>Loi SRU</td><td>Définition de « déficitaire » variable selon les millésimes ; périmètre changeant ; {len(sans)} communes sans indication</td><td>Un seul millésime présenté ; pas d'évolution du nombre de communes déficitaires</td></tr>
    <tr><td>Aides personnelles (compte du logement)</td><td>Euros courants ; causes des évolutions non documentées</td><td>Pas de calcul en euros constants</td></tr>
    <tr><td>Aides au logement (Cnaf)</td><td>Allocataires des Caf ; département de résidence ; mois de décembre incomplets certaines années</td><td>Comparaison des seuls mois de mars</td></tr>
    <tr><td>Absent des données ouvertes</td><td>Demande de logement social et délais d'attente, droit au logement opposable, hébergement d'urgence (pas de données ouvertes nationales trouvées) ; expulsions non traitées</td><td>Non traités dans ce rapport</td></tr>
  </table></div>
</section>"""
date = open("donnees_brutes/logement/date_telechargement.txt", encoding="utf-8").read().strip()
sources = f"""
<section>
  <h3>Sources</h3>
  <p>Service des données et études statistiques (SDES, ministère de la Transition écologique ; licence ouverte selon les <a href="https://www.statistiques.developpement-durable.gouv.fr/mentions-legales">mentions légales du site du SDES</a>) : répertoire des logements locatifs des bailleurs sociaux (RPLS), résultats au 1er janvier 2024 et 2025 ; compte du logement 2025, séries longues des aides 1984-2025. Ministère chargé du logement : inventaire des communes soumises à la loi SRU, millésimes 2023 à 2026 (data.gouv.fr, Licence Ouverte). Caisse nationale des allocations familiales : aides au logement par département et type de parc (data.caf.fr, Licence Ouverte). Téléchargement du {date}.</p>
  <p>Calculs rejouables : <code>nettoyer_logement.py</code>, <code>calculer_chiffres_logement.py</code> puis <code>generer_rapport_logement.py</code>.</p>
</section>"""
bandeau = ('<div class="take" style="border-color:var(--warn)"><strong>Brouillon en cours de vérification</strong> : '
           'chiffres non encore validés de façon indépendante, ne pas diffuser.</div>') if BROUILLON else ""
tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">{pct(PA['mises_en_service_vs_pic']['pct'])}</div><div class="l">de logements sociaux mis en service ({pic['annee_mise_en_service']}-{der['annee_mise_en_service']}, métropole)</div></div>
    <div class="tile"><div class="v">{d(s25['pour_100_mises_en_service'], 0)}</div><div class="l">logements démolis ou vendus (hors ventes entre bailleurs) pour 100 mis en service ({s25['annee_des_sorties']}, métropole)</div></div>
    <div class="tile"><div class="v">−{md(-AI['montant_2017_2025']['ecart'])}</div><div class="l">d'aides personnelles au logement (2017-{sa[-1]['annee']}, France entière, euros courants)</div></div>
    <div class="tile"><div class="v">{n(sd['deficitaires_marquees'])}</div><div class="l">communes déficitaires au sens de la loi SRU (inventaire {sd['millesime']}, France entière)</div></div>
  </div>"""
entete = f"""
<header>
  <div class="eyebrow">Logement social et aides au logement · données SDES, ministère du Logement, Cnaf</div>
  <h1>Moins de logements sociaux mis en service qu'au milieu des années 2010, moins de ménages aidés : la production de logements sociaux marque le pas</h1>
  <p class="lead">Ce que disent les données publiques sur le logement social et les aides au logement. Chaque chiffre vient d'une source publique et peut être recalculé ou vérifié à la source ; chaque graphique est accompagné de ses limites.</p>
  {bandeau}
  {tuiles}
</header>""" + casse


# --- Carte par département (mêmes valeurs que le tableau « Votre département ») ----------------------------
DC = {o["departement"]: o for o in DE["departements"]}
s_carte = section_carte("La carte", "Le logement social, département par département", carte_departements("carte-logement", [
    {"libelle": "Mises en service", "legende": "Évolution des mises en service annuelles de logements sociaux, 2013-2015 à 2022-2024",
     "valeurs": {k: o["pct_mises_en_service"] for k, o in DC.items()}, "fmt": signe, "inverse": True},
    {"libelle": "Foyers aidés", "legende": "Évolution du nombre de foyers aidés par les Caf, mars 2017 à mars 2026",
     "valeurs": {k: o["pct_foyers"] for k, o in caf_dep.items()}, "fmt": signe, "inverse": True},
    {"libelle": "Communes SRU déficitaires", "legende": f"Nombre de communes déficitaires au sens de la loi SRU (inventaire {sd['millesime']})",
     "valeurs": {k: o["deficitaires"] for k, o in sru_dep.items()}, "fmt": n},
    {"libelle": "Parc social", "legende": "Évolution du nombre de logements sociaux, 2013-2025",
     "valeurs": {k: o["pct_parc"] for k, o in DC.items()}, "fmt": signe, "inverse": True},
], "Carte du logement social par département"), f"""
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons changent d'indicateur. Plus la teinte est foncée, plus la situation est défavorable. Les valeurs sont celles du tableau « Votre département » ci-dessous.</p>
  <p class="limite"><strong>Limites :</strong> classes de couleur = cinquièmes des départements ; mises en service et parc social : France métropolitaine seulement (RPLS), avec des pourcentages fragiles dans les départements qui mettent peu de logements en service ; communes SRU : nombres absolus, qui dépendent du nombre de communes soumises à la loi ; départements sans commune soumise à la loi SRU en gris.</p>""")


def partie(ident, titre, intro):
    return f'<div class="partie" id="{ident}"><div class="eyebrow">{titre}</div><p class="lead">{intro}</p></div>'


PARTIES = [
    ("construire", "Construire", "Combien de logements sociaux arrivent chaque année.", [s_mes, s_parc, s_dep]),
    ("sortir", "Vendre et démolir", "Les logements qui quittent le parc social.", [s_sort]),
    ("sru", "La loi SRU", "Les communes déficitaires au regard de la loi SRU.", [s_sru]),
    ("aides", "Aider les locataires", "Les aides personnelles au logement.", [s_aides, s_caf]),
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
tete = re.sub(r"<title>.*?</title>", "<title>Logement social</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">" + entete + sommaire + corps + sources
        + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques){' — BROUILLON' if BROUILLON else ''}")
