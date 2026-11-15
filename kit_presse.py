"""Pages et fichiers d'accompagnement du site : presse, méthode, corrections, identification, partage, exports.

Utilisé par assembler_site.py. Les chiffres de la page presse sont lus dans les fiches donnees_propres/*/chiffres_*.json,
jamais saisis à la main.
"""
import csv
import html
import io
import json
import re

URL = "https://services-publics.bajolet-remy.workers.dev"
AUTEUR = "Rémy Bajolet"
CONTACT = "À_CONFIRMER"
AFFILIATION = "À_CONFIRMER"
LICENCE = "CC BY 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/deed.fr"
DATE_PUBLICATION = "15 novembre 2026"
DATE_MISE_A_JOUR = "15 novembre 2026"

# Jeux de données : (thème, producteur, titre, lien direct, licence, date de téléchargement)
SOURCES = [
    ("Santé", "DREES", "Évolution du nombre de lits et de places au 31 décembre depuis 2013",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/graphique-1-evolution-du-nombre-de-lits-et-de-places-au-31-decembre-depuis-fin-2013/", "non renseignée par le producteur", "20 octobre 2026"),
    ("Santé", "DREES", "Base ARES, agrégats régionaux sur les établissements de santé",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/bases-ares/", "Licence Ouverte 2.0", "20 octobre 2026"),
    ("Santé", "DREES", "Liste des maternités de France depuis 2000",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/fichier_maternites_112021/", "Licence Ouverte 2.0", "20 octobre 2026"),
    ("Santé", "DREES", "Accessibilité potentielle localisée (APL) aux médecins généralistes",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/530_l-accessibilite-potentielle-localisee-apl/", "Licence Ouverte 2.0", "20 octobre 2026"),
    ("Santé", "DREES", "La démographie des professionnels de santé depuis 2012",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/la-demographie-des-professionnels-de-sante-depuis-2012/", "Licence Ouverte 2.0", "20 octobre 2026"),
    ("Santé", "DREES", "Lits de soins critiques des établissements de santé",
     "https://data.drees.solidarites-sante.gouv.fr/explore/dataset/lits-de-reanimation-de-soins-intensifs-et-de-surveillance-continue-en-france0/", "non renseignée par le producteur", "20 octobre 2026"),
    ("Transports", "Autorité de régulation des transports", "Données du transport ferroviaire (réseau, offre et fréquentation des TER, fiabilité, gares)",
     "https://www.autorite-transports.fr/observatoire-et-numerique/jeux-de-donnees-en-open-data/", "Licence Ouverte", "21 octobre 2026"),
    ("Transports", "SNCF", "Points de vente SNCF", "https://ressources.data.sncf.com/explore/dataset/points-vente/", "ODbL", "21 octobre 2026"),
    ("Transports", "SNCF Réseau", "Lignes par statut", "https://ressources.data.sncf.com/explore/dataset/lignes-par-statut/", "ODbL", "21 octobre 2026"),
    ("Transports", "SNCF Gares & Connexions", "Fréquentation en gares", "https://ressources.data.sncf.com/explore/dataset/frequentation-gares/", "ODbL", "21 octobre 2026"),
    ("Transports", "SNCF", "Régularité mensuelle TER, Intercités et TGV", "https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-ter/", "ODbL", "21 octobre 2026"),
    ("Transports", "SNCF", "Répartition par âge de l'effectif", "https://ressources.data.sncf.com/explore/dataset/repartition-age-effectif/", "ODbL", "21 octobre 2026"),
    ("La Poste", "Insee", "Base permanente des équipements, évolution 2015-2020-2025", "https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_BPE_EVOLUTION", "Licence Ouverte", "21 octobre 2026"),
    ("La Poste", "La Poste", "Liste des bureaux de poste, agences postales et relais poste", "https://data.laposte.fr/explore/dataset/laposte-poincont2/", "Licence Ouverte", "21 octobre 2026"),
    ("La Poste", "La Poste", "Calendrier d'ouverture des points de contact", "https://data.laposte.fr/datasets/laposte-ouvertur", "ODbL", "21 octobre 2026"),
    ("La Poste", "La Poste", "Liste des boîtes aux lettres de rue", "https://data.laposte.fr/explore/dataset/laposte-boiterue/", "ODbL", "21 octobre 2026"),
    ("Logement", "SDES", "Répertoire des logements locatifs des bailleurs sociaux (RPLS), 2024 et 2025",
     "https://www.statistiques.developpement-durable.gouv.fr/54-millions-de-logements-locatifs-sociaux-en-france-au-1er-janvier-2025", "Licence Ouverte", "25 octobre 2026"),
    ("Logement", "SDES", "Compte du logement 2025, séries longues des aides",
     "https://www.statistiques.developpement-durable.gouv.fr/rapport-du-compte-du-logement-2025", "Licence Ouverte", "25 octobre 2026"),
    ("Logement", "Ministère chargé du logement", "Communes et inventaire SRU", "https://www.data.gouv.fr/datasets/communes-et-inventaire-sru", "Licence Ouverte 2.0", "25 octobre 2026"),
    ("Logement", "Cnaf", "Aides au logement par département et type de parc", "https://data.caf.fr/explore/dataset/al_s_type_parc_dep/", "Licence Ouverte 2.0", "25 octobre 2026"),
    ("Éducation", "DEPP", "Effectifs d'élèves et nombre de classes par école", "https://data.education.gouv.fr/explore/dataset/fr-en-ecoles-effectifs-nb_classes/", "Licence Ouverte 2.0", "27 octobre 2026"),
    ("Éducation", "DEPP", "Indicateur de ségrégation sociale des collèges", "https://data.education.gouv.fr/explore/dataset/fr-en-indicateur_segregation_sociale_colleges/", "Licence Ouverte 2.0", "27 octobre 2026"),
    ("Éducation", "DEPP", "Indice de position sociale des collèges (depuis 2023)", "https://data.education.gouv.fr/explore/dataset/fr-en-ips-colleges-ap2023/", "Licence Ouverte 2.0", "27 octobre 2026"),
    ("Éducation", "SIES", "Effectifs d'étudiants inscrits (version agrégeable)",
     "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables/", "Licence Ouverte 2.0", "27 octobre 2026"),
    ("Comparaisons", "Insee", "Estimations localisées de population par département et âge", "https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ESTIMATION_POPULATION", "Licence Ouverte", "15 novembre 2026"),
    ("Comparaisons", "OCDE", "Évolution des salaires statutaires des enseignants depuis 2000", "https://data-explorer.oecd.org/", "CC BY 4.0", "15 novembre 2026"),
    ("Comparaisons", "Eurostat", "Élèves par enseignant (educ_uoe_perp04)", "https://ec.europa.eu/eurostat/databrowser/view/educ_uoe_perp04/default/table", "CC BY 4.0", "15 novembre 2026"),
    ("Cartes", "Etalab", "Contours administratifs 2024 des départements", "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2024/", "Licence Ouverte", "14 novembre 2026"),
]

CORRECTIONS = [
    ("15 novembre 2026", "Éducation", "Écoles publiques pour 10 000 enfants de moins de 10 ans, 2009-2025 : −3,8 % remplacé par −2,6 %. Mayotte était comptée pour les écoles mais pas pour les enfants en 2009 ; le calcul est refait hors Mayotte aux deux dates."),
    ("15 novembre 2026", "Santé", "Médecins généralistes pour 1 000 habitants selon l'OCDE (−14,8 % depuis 2000) : chiffre retiré. La baisse venait surtout de ruptures de série de l'OCDE en 2009 et 2011."),
    ("À la prochaine mise en ligne", "Santé", "Lits d'hôpital pour 100 000 habitants selon Eurostat (−33,0 % depuis 2000) : chiffre retiré. Rupture de série en 2013 et définition non comparable à la statistique française."),
    ("À la prochaine mise en ligne", "La Poste", "Paris : nombre d'agences postales (0) et part des bureaux parmi les points postaux (77,1 % en 2025) remplacés par « non disponible ». L'Insee ne publie pas de valeur pour les agences parisiennes."),
]

CITER = f"{AUTEUR}, « Services publics : ce que disent les chiffres publics », {URL}, version du {DATE_MISE_A_JOUR}, licence {LICENCE}."

STYLE_PIED = """<style>
.pied-site { margin-top: 32px; padding-top: 18px; border-top: 1px solid var(--ring); font-size: 13px; color: var(--ink-2); display: grid; gap: 6px; }
.pied-site a { color: var(--ink-2); }
.dates-donnees { font-size: 13px; color: var(--ink-2); }
.citer { font-family: ui-monospace, monospace; font-size: 12px; background: var(--accent-wash); padding: 8px 10px; border-radius: 6px; }
.telecharger { font-size: 14px; font-weight: 600; }
@media print { .menu-site, .sommaire, #filtre, .carte .choix { display: none; } body { background: #fff; } }
</style>"""


def pied():
    """Identification, dates, licence et citation, en bas de chaque page."""
    return f"""
<footer class="pied-site">
  <p>Site réalisé par {AUTEUR} (responsable de publication : {AUTEUR}, À_CONFIRMER), à partir de données publiques ouvertes. Affiliation : {AFFILIATION}. Contact : {CONTACT}.</p>
  <p>Publié le {DATE_PUBLICATION}, mis à jour le {DATE_MISE_A_JOUR}. <a href="methode.html">Méthode et sources</a> · <a href="corrections.html">Corrections</a> · <a href="presse.html">Presse</a></p>
  <p>Textes et graphiques sous licence <a href="{LICENCE_URL}">{LICENCE}</a> ; les données gardent la licence de leur producteur (Licence Ouverte, ODbL pour les données SNCF et une partie des données de La Poste).</p>
  <p>Comment citer : <span class="citer">{html.escape(CITER)}</span></p>
</footer>"""


def meta_partage(nom, titre, description):
    url = f"{URL}/" if nom == "index.html" else f"{URL}/{nom[:-5]}"
    t, d = html.escape(titre), html.escape(description)
    return f"""<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{URL}/partage.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{URL}/partage.png">"""


def tableau_csv(page_html):
    """Tableau départemental de la page (id « tdep ») en CSV, valeurs telles qu'affichées (attributs data-v)."""
    m = re.search(r'<table id="tdep">(.*?)</table>', page_html, re.S)
    if not m:
        return None
    entetes = [html.unescape(re.sub(r"<[^>]+>", "", h)).replace("\xa0", " ").strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", m.group(1), re.S)]
    sortie = io.StringIO()
    w = csv.writer(sortie)
    w.writerow(entetes)
    for ligne in re.findall(r"<tr>(.*?)</tr>", m.group(1).split("<tbody>", 1)[-1], re.S):
        w.writerow([html.unescape(v) for v in re.findall(r'data-v="([^"]*)"', ligne)])
    return "﻿" + sortie.getvalue()


def fiche(theme):
    return json.load(open(f"donnees_propres/{theme}/chiffres_{theme}.json", encoding="utf-8"))


def nf(v, k=0):
    return f"{v:,.{k}f}".replace(",", " ").replace(".", ",")


def signe(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + nf(abs(v), 1) + " %"


def chiffres_presse():
    """Dix chiffres lus dans les fiches : (chiffre, période, source, lien, limite, page) ; et la liste « à manier avec précaution »."""
    S, P, G, E, T, CP = (fiche(t) for t in ("sante", "poste", "logement", "education", "transports", "comparaisons"))
    L, MA, A = S["lits"], S["maternites"], S["apl"]
    eb, (a0, a1) = P["evolution"]["evol"]["Bureau de poste"], P["evolution"]["periode"]
    pic, der = G["parc"]["mises_en_service_pic"], G["parc"]["mises_en_service_derniere"]
    ai = G["aides"]["montant_2017_2025"]
    rv, fo = T["reseau_evolution"], T["frequentation_offre"]
    ho = E["superieur"]["homogene"]
    bp = CP["poste"]["bureaux_pour_100000"]

    def lien(motif):
        return next(x[3] for x in SOURCES if motif in x[3])

    out = [
        (f"{nf(L['lits']['debut'])} lits d'hospitalisation complète en {L['periode'][0]}, {nf(L['lits']['fin'])} en {L['periode'][1]}", f"{L['periode'][0]}-{L['periode'][1]}", "DREES", lien("graphique-1"),
         f"Tous établissements, publics et privés ; les places d'hospitalisation partielle augmentent de {nf(L['places']['ecart'])} sur la même période.", "sante.html"),
        (f"{nf(MA['total']['debut'])} maternités en {MA['periode'][0]}, {nf(MA['total']['fin'])} en {MA['periode'][1]}", f"{MA['periode'][0]}-{MA['periode'][1]}", "DREES", lien("maternites"),
         "Solde net : une maternité qui disparaît de la liste peut avoir fermé ou fusionné.", "sante.html"),
        (f"{nf(A['serie'][-1]['population_sous_dense'] / 1e6, 1)} millions d'habitants en commune sous-dotée en médecins généralistes en {A['serie'][-1]['annee']}, contre {nf(A['serie'][0]['population_sous_dense'] / 1e6, 1)} millions en {A['serie'][0]['annee']}",
         f"{A['serie'][0]['annee']}-{A['serie'][-1]['annee']}", "DREES", lien("apl"),
         "Commune sous-dotée : 2,5 consultations par an et par habitant ou moins ; la hausse reflète en partie l'évolution de la population.", "sante.html"),
        (f"{nf(eb['debut'])} bureaux de poste en {a0}, {nf(eb['fin'])} en {a1}", f"{a0}-{a1}", "Insee", lien("DS_BPE_EVOLUTION"),
         "Les agences postales tenues par les communes et les relais chez des commerçants augmentent sur la même période.", "poste.html"),
        (f"{nf(bp['debut'], 1)} bureaux de poste pour 100 000 habitants en {a0}, {nf(bp['fin'], 1)} en {a1}", f"{a0}-{a1}", "Insee", lien("DS_ESTIMATION_POPULATION"),
         f"Population {a1} provisoire.", "poste.html"),
        (f"{nf(der['valeur'])} logements sociaux mis en service en {der['annee_mise_en_service']}, contre {nf(pic['valeur'])} en {pic['annee_mise_en_service']}", f"{pic['annee_mise_en_service']}-{der['annee_mise_en_service']}", "SDES", lien("54-millions"),
         "France métropolitaine ; une mise en service n'est pas une construction (achats sur plan et acquisitions compris).", "logement.html"),
        (f"{nf(ai['debut'], 2)} Md€ d'aides personnelles au logement en 2017, {nf(ai['fin'], 2)} Md€ en 2025", "2017-2025", "SDES", lien("compte-du-logement"),
         "Euros courants, sans correction de l'inflation.", "logement.html"),
        (f"{nf(rv['classique']['debut'])} km de lignes classiques gérées par SNCF Réseau en {rv['periode'][0]}, {nf(rv['classique']['fin'])} km en {rv['periode'][1]}", f"{rv['periode'][0]}-{rv['periode'][1]}", "ART", lien("autorite-transports"),
         "Sorties du réseau toutes causes confondues, y compris les transferts de gestion aux régions.", "transports.html"),
        (f"Fréquentation des TER {signe(fo['pkt'])}, places offertes {signe(fo['sieges_km'])}", f"{fo['periode'][0]}-{fo['periode'][1]}", "ART", lien("autorite-transports"),
         "Passagers-km et sièges-km ; Intercités transférés aux régions comptés en TER.", "transports.html"),
        (f"Étudiants des établissements privés {signe(ho['prive']['pct'])}, du public {signe(ho['public']['pct'])}", f"{ho['debut']} à {ho['fin']}", "SIES", lien("enseignementsup"),
         "La source ne distingue pas le privé lucratif du privé non lucratif.", "education.html"),
    ]
    precaution = [
        ("Écoles publiques en moins depuis 2009", f"Solde de numéros d'établissement : fusions et changements de numéro compris. Rapporté aux enfants de moins de 10 ans, la baisse est de {signe(CP['education']['ecoles_pour_10000_enfants']['pct'])[1:]}.", "education.html"),
        ("Départements les plus mal placés (page Territoires)", "Comptage relatif construit pour ce site : un cinquième des départements est classé défavorable par construction ; mélange de niveaux et d'évolutions.", "territoires.html"),
        ("Gares sans guichet", "Photographie : données traitées en février 2024 ; « sans guichet » ne veut pas dire « sans automate ».", "transports.html"),
        ("Élèves par enseignant en primaire (Eurostat)", "Eurostat signale une définition différente pour la France ; un ratio n'est pas une taille de classe.", "education.html"),
        ("Salaires des enseignants (OCDE)", "Indice de salaire statutaire hors primes, corrigé de l'inflation par l'OCDE.", "education.html"),
        ("Habitants sans bureau de poste dans leur commune", "Mesure l'absence de bureau dans la commune, pas la distance ; population 2022 et liste de La Poste d'octobre 2026.", "poste.html"),
    ]
    return out, precaution


def page(tete, menu, titre_h1, chapo, corps):
    return (tete + "\n</head>\n<body>\n<div class=\"wrap\">" + menu + f"""
<header>
  <div class="eyebrow">Services publics · données publiques</div>
  <h1>{titre_h1}</h1>
  <p class="lead">{chapo}</p>
</header>""" + corps + pied() + "\n</div>\n</body>\n</html>\n")


def page_presse(tete, menu):
    out, prec = chiffres_presse()
    lignes = "".join(f'<tr id="chiffre-{i}"><td><strong>{c}</strong></td><td>{p}</td><td><a href="{u}">{src}</a></td><td>{lim}</td><td><a href="{pg}">Rapport</a></td></tr>'
                     for i, (c, p, src, u, lim, pg) in enumerate(out, 1))
    prec_l = "".join(f'<li><strong>{a}</strong> : {b} <a href="{c}">Voir le rapport</a>.</li>' for a, b, c in prec)
    corps = f"""
<section id="chiffres">
  <h2>Dix chiffres</h2>
  <div class="tbl"><table>
    <thead><tr><th>Chiffre</th><th>Période</th><th>Source</th><th>Limite</th><th>Détail</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
</section>
<section id="precaution">
  <h2>À manier avec précaution</h2>
  <ul>{prec_l}</ul>
</section>
<section id="contact">
  <h2>Contact et réutilisation</h2>
  <p>Contact : {CONTACT}. Textes et graphiques réutilisables sous licence {LICENCE}, avec la mention suivante :</p>
  <p class="citer">{html.escape(CITER)}</p>
  <p>Les tableaux départementaux de chaque rapport se téléchargent en CSV depuis la page du rapport.</p>
</section>"""
    return page(tete, menu, "Dossier de presse", "Les chiffres principaux du site, avec leur période, leur source et leur limite principale. Chaque chiffre renvoie au rapport où il est détaillé.", corps)


def page_methode(tete, menu):
    lignes = "".join(f'<tr><td>{t}</td><td>{p}</td><td><a href="{u}">{ti}</a></td><td>{li}</td><td>{dt}</td></tr>' for t, p, ti, u, li, dt in SOURCES)
    corps = f"""
<section id="chaine">
  <h2>Comment les chiffres sont produits</h2>
  <p>Chaque rapport repose sur des données publiques téléchargées telles quelles chez leur producteur. Un script nettoie ces fichiers sans correction à la main : les valeurs manquantes ou suspectes sont signalées, pas supprimées. Un second script calcule chaque chiffre à partir des fichiers nettoyés et l'enregistre avec sa définition. Un troisième produit la page à partir de ces calculs : aucun chiffre n'est saisi à la main dans les textes.</p>
  <p>Les limites de chaque donnée figurent à côté du chiffre concerné et dans la section « Fiabilité » de chaque rapport. Les encadrés « Notre lecture » signalent les interprétations.</p>
</section>
<section id="reproduire">
  <h2>Reproduire les calculs</h2>
  <p>Le code est public. Avec Python 3 et sans autre dépendance, après avoir placé les fichiers sources dans <code>donnees_brutes/</code> :</p>
  <p class="citer">python3 nettoyer_sante.py &amp;&amp; python3 calculer_chiffres_sante.py &amp;&amp; python3 generer_rapport_sante.py</p>
  <p>Même enchaînement pour <code>transports</code>, <code>poste</code>, <code>logement</code> et <code>education</code>, puis <code>calculer_chiffres_comparaisons.py</code>, <code>calculer_chiffres_territoires.py</code>, <code>generer_rapport_territoires.py</code> et <code>assembler_site.py</code>.</p>
</section>
<section id="sources">
  <h2>Sources</h2>
  <div class="tbl"><table>
    <thead><tr><th>Thème</th><th>Producteur</th><th>Jeu de données</th><th>Licence</th><th>Téléchargé le</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
</section>"""
    return page(tete, menu, "Méthode et sources", "D'où viennent les chiffres, comment ils sont calculés et comment les refaire.", corps)


def page_corrections(tete, menu):
    lignes = "".join(f"<tr><td>{d}</td><td>{p}</td><td>{t}</td></tr>" for d, p, t in CORRECTIONS)
    corps = f"""
<section id="journal">
  <h2>Journal des corrections</h2>
  <div class="tbl"><table>
    <thead><tr><th>Date</th><th>Page</th><th>Correction</th></tr></thead>
    <tbody>{lignes}</tbody>
  </table></div>
  <p>Signaler une erreur : {CONTACT}.</p>
</section>"""
    return page(tete, menu, "Corrections", "Toute correction d'un chiffre publié est indiquée ici, avec l'ancienne valeur, la nouvelle et la raison.", corps)


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#c8102e"/><path d="M7 22h4V14H7zm7 0h4V9h-4zm7 0h4V17h-4z" fill="#fff"/></svg>"""


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {URL}/sitemap.xml\n"


def sitemap(pages):
    urls = "".join(f"<url><loc>{URL}/{'' if p == 'index.html' else p[:-5]}</loc></url>" for p in pages)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
