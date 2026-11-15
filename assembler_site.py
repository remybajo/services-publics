"""Assemble le site site_services_publics/ à partir des rapports validés (rapport_*.html).

Ajoute à chaque rapport un menu commun et crée une page d'accueil qui reprend le surtitre et le titre de chaque rapport.
Aucun chiffre n'est ajouté ni modifié : seuls la navigation et la page d'accueil sont produites (EDR-005).
Usage : python3 assembler_site.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # modules du projet
import kit_presse as K  # noqa: E402

SORTIE = "site_services_publics"
# Ordre du menu : (fichier publié, rapport source, libellé du menu)
PAGES = [
    ("sante.html", "rapports/rapport_sante.html", "Santé"),
    ("transports.html", "rapports/rapport_transports.html", "Transports"),
    ("poste.html", "rapports/rapport_poste.html", "La Poste"),
    ("logement.html", "rapports/rapport_logement.html", "Logement"),
    ("education.html", "rapports/rapport_education.html", "Éducation"),
    ("territoires.html", "rapports/rapport_territoires.html", "Territoires"),
]
STYLE_MENU = """<style>
.menu-site { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; padding: 10px 0 14px; border-bottom: 1px solid var(--ring); margin-bottom: 8px; }
.menu-site a { font-size: 14px; font-weight: 600; color: var(--ink-2); text-decoration: none; }
.menu-site a[aria-current="page"] { color: var(--alerte, var(--ink)); text-decoration: underline; text-underline-offset: 4px; }
.menu-site .marque { color: var(--ink); margin-right: 8px; }
.cartes { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
.carte { display: grid; gap: 8px; align-content: start; padding: 18px; border-radius: 12px; background: var(--surface); border: 1px solid var(--ring); color: var(--ink); text-decoration: none; }
.carte:hover { border-color: var(--ink-2); }
.carte .eyebrow { font-size: 13px; }
.carte strong { font-size: 18px; line-height: 1.3; }
.carte span:last-child { font-size: 13px; color: var(--ink-2); }
</style>"""


def menu(courante):
    def lien(f, lib, classe=""):
        actif = ' aria-current="page"' if f == courante else ""
        return f'<a{classe} href="{f}"{actif}>{lib}</a>'
    liens = ([lien("index.html", "Services publics", ' class="marque"')] + [lien(f, lib) for f, _, lib in PAGES]
             + [lien("presse.html", "Presse"), lien("methode.html", "Méthode")])
    return '<nav class="menu-site" aria-label="Thèmes">' + "".join(liens) + "</nav>"


def ajouter_menu(html, fichier, titre="", description=""):
    """Menu commun, balises de partage, pied d'identification et lien de téléchargement du tableau départemental."""
    html = html.replace("</head>", K.meta_partage(fichier, titre, description) + "\n" + STYLE_MENU + "\n" + K.STYLE_PIED + "\n</head>", 1)
    html = html.replace('<div class="wrap">', '<div class="wrap">' + menu(fichier), 1)
    if K.tableau_csv(html):
        lien = f'<p class="telecharger"><a href="donnees/{fichier[:-5]}_departements.csv" download>Télécharger le tableau (CSV)</a></p>'
        html = html.replace('<div class="tbl"><table id="tdep">', lien + '<div class="tbl"><table id="tdep">', 1)
    i = html.rindex("</div>\n</body>")
    return html[:i] + K.pied() + "\n" + html[i:]


def texte(motif, html):
    m = re.search(motif, html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def main():
    os.makedirs(SORTIE, exist_ok=True)
    cartes = []
    os.makedirs(os.path.join(SORTIE, "donnees"), exist_ok=True)
    for fichier, source, libelle in PAGES:
        html = open(source, encoding="utf-8").read()
        titre = f"{libelle} : {texte(r'<h1>(.*?)</h1>', html)}"
        description = texte(r'<p class="lead">(.*?)</p>', html)[:200]
        with open(os.path.join(SORTIE, fichier), "w", encoding="utf-8") as f:
            f.write(ajouter_menu(html, fichier, titre, description))
        tab = K.tableau_csv(html)
        if tab:
            with open(os.path.join(SORTIE, "donnees", f"{fichier[:-5]}_departements.csv"), "w", encoding="utf-8", newline="") as f:
                f.write(tab)
        cartes.append(f'<a class="carte" href="{fichier}"><span class="eyebrow">{libelle}</span>'
                      f'<strong>{texte(r"<h1>(.*?)</h1>", html)}</strong>'
                      f'<span>{texte(r"<header>\s*<div class=.eyebrow.>(.*?)</div>", html)}</span></a>')
        print(f"{fichier} <- {source}")
    # Page d'accueil : en-tête et styles du premier rapport, titre et contenu propres
    modele = open(PAGES[0][1], encoding="utf-8").read()
    tete = modele[:modele.index("</head>")]
    tete = re.sub(r"<title>.*?</title>", "<title>Services publics</title>", tete)
    tete_site = tete + K.STYLE_PIED + "\n"
    accueil = (tete + K.meta_partage("index.html", "Services publics : ce que disent les chiffres publics", "Santé, transports, La Poste, logement, éducation : six rapports chiffrés à partir de données publiques, avec cartes par département.") + "\n" + STYLE_MENU + K.STYLE_PIED + "\n</head>\n<body>\n<div class=\"wrap\">" + menu("index.html") + """
<header>
  <div class="eyebrow">Services publics · données publiques</div>
  <h1>Services publics : ce que disent les chiffres publics</h1>
  <p class="lead">Santé, transports, La Poste, logement, éducation, et leur croisement par département : six rapports construits uniquement à partir de données publiques. Chaque chiffre peut être recalculé ou vérifié à la source, et chaque graphique est accompagné de ses limites.</p>
</header>
<section>
  <div class="cartes">""" + "".join(cartes) + """</div>
</section>
""" + K.pied() + """
</div>
</body>
</html>
""")
    with open(os.path.join(SORTIE, "index.html"), "w", encoding="utf-8") as f:
        f.write(accueil)
    print("index.html <- page d'accueil")
    # Pages d'accompagnement, fichiers de partage et de référencement
    autres = {"presse.html": K.page_presse, "methode.html": K.page_methode, "corrections.html": K.page_corrections}
    for nom, fonction in autres.items():
        t = re.sub(r"<title>.*?</title>", f"<title>{dict(zip(autres, ('Dossier de presse', 'Méthode et sources', 'Corrections')))[nom]} · Services publics</title>", tete_site)
        t += K.meta_partage(nom, "Services publics : " + dict(zip(autres, ("dossier de presse", "méthode et sources", "corrections")))[nom], "Chiffres sur les services publics en France, avec leur source, leur période et leurs limites.") + STYLE_MENU
        with open(os.path.join(SORTIE, nom), "w", encoding="utf-8") as f:
            f.write(fonction(t, menu(nom)))
    fichiers = {"robots.txt": K.robots(), "sitemap.xml": K.sitemap(["index.html"] + [p for p, _, _ in PAGES] + list(autres)), "favicon.svg": K.FAVICON}
    for nom, contenu in fichiers.items():
        with open(os.path.join(SORTIE, nom), "w", encoding="utf-8") as f:
            f.write(contenu)
    print("presse, méthode, corrections, robots.txt, sitemap.xml, favicon.svg")


if __name__ == "__main__":
    main()
