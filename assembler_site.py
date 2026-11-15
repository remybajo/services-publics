"""Assemble le site site_services_publics/ à partir des rapports validés (rapport_*.html).

Ajoute à chaque rapport un menu commun et crée une page d'accueil qui reprend le surtitre et le titre de chaque rapport.
Aucun chiffre n'est ajouté ni modifié : seuls la navigation et la page d'accueil sont produites (EDR-005).
Usage : python3 assembler_site.py
"""
import os
import re

SORTIE = "site_services_publics"
# Ordre du menu : (fichier publié, rapport source, libellé du menu)
PAGES = [
    ("sante.html", "rapport_sante.html", "Santé"),
    ("transports.html", "rapport_transports.html", "Transports"),
    ("poste.html", "rapport_poste.html", "La Poste"),
    ("logement.html", "rapport_logement.html", "Logement"),
    ("education.html", "rapport_education.html", "Éducation"),
    ("territoires.html", "rapport_territoires.html", "Territoires"),
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
    liens = [lien("index.html", "Services publics", ' class="marque"')] + [lien(f, lib) for f, _, lib in PAGES]
    return '<nav class="menu-site" aria-label="Thèmes">' + "".join(liens) + "</nav>"


def ajouter_menu(html, fichier):
    html = html.replace("</head>", STYLE_MENU + "\n</head>", 1)
    return html.replace('<div class="wrap">', '<div class="wrap">' + menu(fichier), 1)


def texte(motif, html):
    m = re.search(motif, html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def main():
    os.makedirs(SORTIE, exist_ok=True)
    cartes = []
    for fichier, source, libelle in PAGES:
        html = open(source, encoding="utf-8").read()
        with open(os.path.join(SORTIE, fichier), "w", encoding="utf-8") as f:
            f.write(ajouter_menu(html, fichier))
        cartes.append(f'<a class="carte" href="{fichier}"><span class="eyebrow">{libelle}</span>'
                      f'<strong>{texte(r"<h1>(.*?)</h1>", html)}</strong>'
                      f'<span>{texte(r"<header>\s*<div class=.eyebrow.>(.*?)</div>", html)}</span></a>')
        print(f"{fichier} <- {source}")
    # Page d'accueil : en-tête et styles du premier rapport, titre et contenu propres
    modele = open(PAGES[0][1], encoding="utf-8").read()
    tete = modele[:modele.index("</head>")]
    tete = re.sub(r"<title>.*?</title>", "<title>Services publics</title>", tete)
    accueil = (tete + STYLE_MENU + "\n</head>\n<body>\n<div class=\"wrap\">" + menu("index.html") + """
<header>
  <div class="eyebrow">Services publics · données publiques</div>
  <h1>Ce que les chiffres publics disent de l'état des services publics</h1>
  <p class="lead">Santé, transports, La Poste, logement, éducation, et leur croisement par département : six rapports construits uniquement à partir de données publiques. Chaque chiffre peut être recalculé ou vérifié à la source, et chaque graphique est accompagné de ses limites.</p>
</header>
<section>
  <div class="cartes">""" + "".join(cartes) + """</div>
</section>
<section>
  <h3>Méthode</h3>
  <p>Chaque rapport suit la même chaîne : téléchargement des données publiques, nettoyage par script sans correction à la main, calcul des chiffres, puis vérification indépendante de chaque chiffre avant publication. Les encadrés « Notre lecture » signalent les interprétations ; les limites des données figurent à côté des chiffres et dans la section « Fiabilité » de chaque rapport.</p>
</section>
</div>
</body>
</html>
""")
    with open(os.path.join(SORTIE, "index.html"), "w", encoding="utf-8") as f:
        f.write(accueil)
    print("index.html <- page d'accueil")


if __name__ == "__main__":
    main()
