"""Formats français et graphiques SVG autonomes partagés par les générateurs de rapports (rapport_*.html).

Aucune dépendance : chaque fonction renvoie une chaîne SVG ou HTML. Couleurs en variables CSS (thème clair/sombre).
"""

# Couleurs par statut d'établissement (public / privé)
COUL = {"Public": "var(--s1)", "Privé non lucratif": "var(--dim)", "Privé lucratif": "var(--s2)"}


# --- Formats français -------------------------------------------------------
def n(v):
    """Entier avec espace fine insécable comme séparateur de milliers."""
    return f"{round(v):,}".replace(",", " ")


def d(v, k=1):
    return f"{v:.{k}f}".replace(".", ",")


def pct(v, signe=True):
    s = d(abs(v)) + " %"
    if not signe:
        return s
    return ("+" if v > 0 else "−") + s


def m(v, k=1):
    return d(v / 1e6, k) + " M"


def ecart(v):
    return ("+" if v > 0 else "−") + n(abs(v))


# --- Graphiques SVG ---------------------------------------------------------
W, H = 640, 300
G, D, HAUT, BAS = 56, 16, 24, 34  # marges


def echelle(vmin, vmax):
    return lambda v: HAUT + (H - HAUT - BAS) * (1 - (v - vmin) / (vmax - vmin))


def axe_y(vmin, vmax, pas, fmt):
    y = echelle(vmin, vmax)
    out = []
    v = vmin
    while v <= vmax + 1e-9:
        out.append(f'<line x1="{G}" x2="{W - D}" y1="{y(v):.1f}" y2="{y(v):.1f}" style="stroke:var(--grid)"/>'
                   f'<text x="{G - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="12" style="fill:var(--muted)">{fmt(v)}</text>')
        v += pas
    return "".join(out)


def svg(contenu, titre):
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{titre}">{contenu}</svg>'


def courbes(series, annees, vmin, vmax, pas, fmt, titre, etiquette_dessous=False, mention=""):
    """series : liste de (libellé, couleur, valeurs)."""
    y = echelle(vmin, vmax)
    pas_x = (W - G - D - 20) / (len(annees) - 1)
    x = lambda i: G + 10 + i * pas_x
    out = [axe_y(vmin, vmax, pas, fmt)]
    if mention:
        out.append(f'<text x="{G}" y="{HAUT - 4}" font-size="12" font-style="italic" style="fill:var(--muted)">{mention}</text>')
    for i, a in enumerate(annees):
        if len(annees) <= 12 or i % 3 == 0 or i == len(annees) - 1:
            out.append(f'<text x="{x(i):.1f}" y="{H - 12}" text-anchor="middle" font-size="12" style="fill:var(--muted)">{a}</text>')
    etiquettes_y = []  # évite les étiquettes de fin qui se chevauchent
    for _, coul, vals in sorted(series, key=lambda s_: -s_[2][-1]):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)  # None = année non disponible
        out.append(f'<polyline points="{pts}" fill="none" style="stroke:{coul}" stroke-width="2.5" stroke-linejoin="round"/>')
        for i in (next(i for i, v in enumerate(vals) if v is not None), len(vals) - 1):
            out.append(f'<circle cx="{x(i):.1f}" cy="{y(vals[i]):.1f}" r="3.5" style="fill:{coul}"/>')
        ye = y(vals[-1]) + 20 if etiquette_dessous else y(vals[-1]) - 9
        if any(abs(ye - e) < 13 for e in etiquettes_y):
            continue
        etiquettes_y.append(ye)
        out.append(f'<text x="{x(len(vals) - 1) - 4:.1f}" y="{ye:.1f}" text-anchor="end" font-size="12" font-weight="600" style="fill:{coul}">{fmt(vals[-1])}</text>')
    return svg("".join(out), titre)


def barres_empilees(lignes, cles, vmax, pas, fmt, titre, coupures=(), couleurs=None):
    """lignes : liste de (année, {clé: valeur}). coupures : années précédées d'un trou dans la série."""
    y = echelle(0, vmax)
    larg = (W - G - D) / len(lignes)
    out = [axe_y(0, vmax, pas, fmt)]
    for i, (a, vals) in enumerate(lignes):
        x0 = G + i * larg + larg * 0.18
        bas = 0
        for k in cles:
            v = vals[k]
            out.append(f'<rect x="{x0:.1f}" y="{y(bas + v):.1f}" width="{larg * 0.64:.1f}" height="{y(bas) - y(bas + v):.1f}" style="fill:{(couleurs or COUL)[k]}"/>')
            bas += v
        out.append(f'<text x="{x0 + larg * 0.32:.1f}" y="{y(bas) - 6:.1f}" text-anchor="middle" font-size="11" style="fill:var(--ink-2)">{fmt(bas)}</text>')
        out.append(f'<text x="{x0 + larg * 0.32:.1f}" y="{H - 12}" text-anchor="middle" font-size="12" style="fill:var(--muted)">{a}</text>')
        if a in coupures:
            xc = G + i * larg
            out.append(f'<line x1="{xc:.1f}" x2="{xc:.1f}" y1="{HAUT}" y2="{H - BAS}" stroke-dasharray="4 4" style="stroke:var(--warn)"/>')
    return svg("".join(out), titre)


def barres_groupees(lignes, couleurs, vmax, pas, fmt, titre):
    """lignes : liste de (année, [v1, v2, ...]) ; couleurs : une par série."""
    y = echelle(0, vmax)
    larg = (W - G - D) / len(lignes)
    lb = larg * 0.7 / len(couleurs)
    out = [axe_y(0, vmax, pas, fmt)]
    for i, (a, vals) in enumerate(lignes):
        x0 = G + i * larg + larg * 0.15
        for j, (coul, v) in enumerate(zip(couleurs, vals)):
            xj = x0 + j * lb
            out.append(f'<rect x="{xj + 2:.1f}" y="{y(v):.1f}" width="{lb - 4:.1f}" height="{y(0) - y(v):.1f}" style="fill:{coul}"/>'
                       f'<text x="{xj + lb / 2:.1f}" y="{y(v) - 6:.1f}" text-anchor="middle" font-size="12" font-weight="600" style="fill:var(--ink)">{fmt(v)}</text>')
        out.append(f'<text x="{x0 + larg * 0.35:.1f}" y="{H - 12}" text-anchor="middle" font-size="12" style="fill:var(--muted)">{a}</text>')
    return svg("".join(out), titre)


def barres_h(items, fmt, titre, couleur="var(--s1)", coupure=None, vmax=None):
    """Classement horizontal : items = [(libellé, valeur)] ; coupure = index avant lequel tracer « … »."""
    lg, hl = 170, 22
    h = HAUT + hl * len(items) + (hl if coupure else 0) + 10
    vmax = vmax or max(v for _, v in items)
    larg = W - lg - 70
    out, yy = [], HAUT
    for i, (lib, v) in enumerate(items):
        if coupure is not None and i == coupure:
            out.append(f'<text x="{lg - 10}" y="{yy + 15}" text-anchor="end" font-size="13" style="fill:var(--muted)">…</text>')
            yy += hl
        w = larg * v / vmax
        out.append(f'<text x="{lg - 10}" y="{yy + 15}" text-anchor="end" font-size="12" style="fill:var(--ink-2)">{lib}</text>'
                   f'<rect x="{lg}" y="{yy + 4}" width="{max(w, 1):.1f}" height="{hl - 8}" rx="2" style="fill:{couleur(i, v) if callable(couleur) else couleur}"/>'
                   f'<text x="{lg + w + 6:.1f}" y="{yy + 15}" font-size="12" font-weight="600" style="fill:var(--ink)">{fmt(v)}</text>')
        yy += hl
    return f'<svg viewBox="0 0 {W} {h}" role="img" aria-label="{titre}">{"".join(out)}</svg>'


def barres_divergentes(items, fmt, titre, coupure=None):
    """Valeurs positives et négatives autour de zéro : items = [(libellé, valeur)]."""
    lg, hl = 170, 22
    h = HAUT + hl * len(items) + (hl if coupure else 0) + 10
    neg = max([-v for _, v in items if v < 0] or [0])
    pos = max([v for _, v in items if v > 0] or [0])
    span = W - lg - 110  # 50 px de marge à gauche et 60 à droite pour les valeurs
    x0 = lg + 50 + span * neg / (neg + pos)
    out, yy = [f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="{HAUT}" y2="{h - 10}" style="stroke:var(--axis)"/>'], HAUT
    for i, (lib, v) in enumerate(items):
        if coupure is not None and i == coupure:
            out.append(f'<text x="{lg - 10}" y="{yy + 15}" text-anchor="end" font-size="13" style="fill:var(--muted)">…</text>')
            yy += hl
        w = span * abs(v) / (neg + pos)
        xr = x0 if v >= 0 else x0 - w
        coul = "var(--s1)" if v >= 0 else "var(--s2)"
        xt, ancre = (x0 + w + 6, "start") if v >= 0 else (x0 - w - 6, "end")
        out.append(f'<text x="{lg - 10}" y="{yy + 15}" text-anchor="end" font-size="12" style="fill:var(--ink-2)">{lib}</text>'
                   f'<rect x="{xr:.1f}" y="{yy + 4}" width="{max(w, 1):.1f}" height="{hl - 8}" rx="2" style="fill:{coul}"/>'
                   f'<text x="{xt:.1f}" y="{yy + 15}" text-anchor="{ancre}" font-size="12" font-weight="600" style="fill:var(--ink)">{fmt(v)}</text>')
        yy += hl
    return f'<svg viewBox="0 0 {W} {h}" role="img" aria-label="{titre}">{"".join(out)}</svg>'


def empile_100_h(lignes, classes, couleurs, titre):
    """Barres horizontales à 100 % : lignes = [(libellé, {classe: part})]."""
    lg, hl = 60, 44
    h = HAUT + hl * len(lignes) + 10
    larg = W - lg - D
    out, yy = [], HAUT
    for lib, parts in lignes:
        x = lg
        out.append(f'<text x="{lg - 10}" y="{yy + 26}" text-anchor="end" font-size="12" style="fill:var(--ink-2)">{lib}</text>')
        for k in classes:
            w = larg * parts[k] / 100
            out.append(f'<rect x="{x:.1f}" y="{yy + 6}" width="{w:.1f}" height="{hl - 12}" style="fill:{couleurs[k]}"/>'
                       f'<text x="{x + w / 2:.1f}" y="{yy + 26}" text-anchor="middle" font-size="12" font-weight="600" style="fill:#fff">{d(parts[k])}&nbsp;%</text>')
            x += w
        yy += hl
    return f'<svg viewBox="0 0 {W} {h}" role="img" aria-label="{titre}">{"".join(out)}</svg>'


def legende(items):
    return '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{l}</span>' for l, c in items) + "</div>"


def section(num, surtitre, titre, graphique, note, leg=""):
    return f"""
<section>
  <h3>{num} · {surtitre}</h3>
  <h2>{titre}</h2>
  <div class="row">
    <div class="chart">{leg}{graphique}</div>
    <div class="note">{note}</div>
  </div>
</section>"""


# --- Mise en forme « offensive mais inattaquable » (EDR-012) ---------------------------------
STYLE_MILITANT = """<style>
/* Ton militant : accent d'alerte, synthèse « La casse en chiffres », lectures signalées, limites discrètes */
:root { --alerte: #c8102e; --alerte-fond: #fdecee; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --alerte: #ff5c6f; --alerte-fond: #3a1419; } }
:root[data-theme="dark"] { --alerte: #ff5c6f; --alerte-fond: #3a1419; }
.eyebrow { color: var(--alerte); }
h1 { letter-spacing: -.025em; }
.casse { background: var(--alerte-fond); border-left: 6px solid var(--alerte); border-radius: 10px; padding: 18px 20px; display: grid; gap: 10px; }
.casse h2 { color: var(--alerte); font-size: 22px; }
.casse ol { margin: 0; padding-left: 22px; display: grid; gap: 8px; }
.casse li { font-size: 17px; line-height: 1.45; }
.casse li strong { color: var(--alerte); }
.lecture { border: 2px solid var(--alerte); border-radius: 10px; padding: 12px 16px; display: grid; gap: 6px; }
.lecture .titre-lecture { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--alerte); }
.take { border-left-color: var(--alerte); }
.note p.limite { font-size: 13px; color: var(--ink-2); }
details.limite { font-size: 13px; color: var(--ink-2); }
details.limite summary { cursor: pointer; }
details.limite p { margin-top: 6px; font-size: 13px; }
.tile .v { color: var(--alerte); }
</style>"""


def casse_en_chiffres(titre, items, note=""):
    """Bloc de synthèse en tête de rapport : items = phrases HTML (chiffres déjà formatés depuis la fiche)."""
    lignes = "".join(f"<li>{i}</li>" for i in items)
    pied = f'<p class="limite">{note}</p>' if note else ""
    return f'<section class="casse"><h2>{titre}</h2><ol>{lignes}</ol>{pied}</section>'


def lecture(texte, titre="Notre lecture"):
    """Encadré d'interprétation, toujours signalé comme une lecture (EDR-012)."""
    return f'<div class="lecture"><span class="titre-lecture">{titre}</span><p>{texte}</p></div>'


def limite(texte):
    """Paragraphe de limites, plus discret mais toujours présent à côté des chiffres (EDR-005, EDR-007)."""
    return f'<p class="limite"><strong>Limites :</strong> {texte}</p>'


def alleger_limites(html):
    """Version presse : chaque paragraphe de limites devient un bloc repliable.

    La première proposition reste visible à côté du graphique ; le texte complet s'ouvre d'un clic et à l'impression.
    Aucune limite n'est supprimée (EDR-005, EDR-007).
    """
    import re

    def bloc(m):
        etiquette, texte = m.group(1), m.group(2).strip()
        coupe = re.search(r"(?<![0-9&])(?: ;|\.|:) ", texte)  # fin de la première proposition
        if not coupe or coupe.start() > len(texte) - 20:
            return m.group(0)  # limite déjà courte : inchangée
        court = texte[:coupe.start()].rstrip()
        return (f'<details class="limite"><summary><strong>{etiquette}</strong> {court}… <u>en savoir plus</u></summary>'
                f"<p>{texte}</p></details>")

    html = re.sub(r'<p class="limite"><strong>(Limite[^<]*)</strong>(.*?)</p>', bloc, html, flags=re.S)
    return html + """
<script>
window.addEventListener('beforeprint', function () {
  Array.prototype.forEach.call(document.querySelectorAll('details.limite'), function (d) { d.open = true; });
});
</script>"""
