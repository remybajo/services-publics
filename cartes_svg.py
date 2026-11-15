"""Cartes interactives par département, autonomes (SVG + JavaScript intégrés), partagées par les générateurs de rapports.

Fond de carte : contours des départements (Etalab, contours administratifs 2024, Licence Ouverte), donnees_brutes/cartes/.
Aucune dépendance : carte_departements() renvoie un bloc HTML ; les valeurs affichées viennent des fiches de chiffres (EDR-005).
"""
import json
import math
import os

FOND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees_brutes", "cartes", "departements-1000m.geojson")
LARG, HAUT_CARTE = 660, 520
# Départements d'outre-mer : encadrés à gauche de la carte (code -> libellé)
DROM = {"971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion", "976": "Mayotte"}
PETITE_COURONNE = ("75", "92", "93", "94")  # agrandie dans un encadré : départements trop petits à l'échelle nationale
NB_CLASSES = 5

STYLE_CARTE = """<style>
/* Cartes par département : 5 classes du plus clair au plus foncé, gris = pas de donnée */
:root { --c0: #fde3e0; --c1: #f8b4ab; --c2: #ee7e73; --c3: #d9453f; --c4: #9c1420; --c-vide: #d9dce1; --c-trait: #ffffff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --c0: #4a2326; --c1: #7a2f33; --c2: #ad3f42; --c3: #e0605e; --c4: #ffaaa0; --c-vide: #3a3f47; --c-trait: #14171c; } }
:root[data-theme="dark"] { --c0: #4a2326; --c1: #7a2f33; --c2: #ad3f42; --c3: #e0605e; --c4: #ffaaa0; --c-vide: #3a3f47; --c-trait: #14171c; }
.carte { display: grid; gap: 10px; }
.carte .choix { display: flex; flex-wrap: wrap; gap: 6px; }
.carte .choix button { font: inherit; font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 99px; border: 1px solid var(--ring); background: var(--surface); color: var(--ink-2); cursor: pointer; }
.carte .choix button[aria-pressed="true"] { background: var(--alerte); border-color: var(--alerte); color: #fff; }
.carte .cadre { position: relative; }
.carte svg { width: 100%; height: auto; display: block; }
.carte path { stroke: var(--c-trait); stroke-width: .6; cursor: pointer; }
.carte path:hover { stroke: var(--ink); stroke-width: 1.6; }
.carte .k0 { fill: var(--c0); } .carte .k1 { fill: var(--c1); } .carte .k2 { fill: var(--c2); } .carte .k3 { fill: var(--c3); } .carte .k4 { fill: var(--c4); } .carte .kv { fill: var(--c-vide); }
.carte .bulle { position: absolute; pointer-events: none; background: var(--ink); color: var(--surface); font-size: 13px; line-height: 1.35; padding: 6px 10px; border-radius: 6px; max-width: 220px; display: none; z-index: 2; }
.carte .legende-carte { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--ink-2); }
.carte .legende-carte i { display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.carte .legende-carte .k0 { background: var(--c0); } .carte .legende-carte .k1 { background: var(--c1); } .carte .legende-carte .k2 { background: var(--c2); } .carte .legende-carte .k3 { background: var(--c3); } .carte .legende-carte .k4 { background: var(--c4); } .carte .legende-carte .kv { background: var(--c-vide); }
.carte .titre-carte { font-size: 14px; font-weight: 600; flex-basis: 100%; color: var(--ink); }
</style>"""

_cache = {}


def _anneaux(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [a for p in polys for a in p]


def _projeter(anneaux_par_code, x0, y0, larg, haut):
    """Projection plane simple (longitude corrigée par le cosinus de la latitude moyenne), ajustée dans un rectangle."""
    pts = [pt for an in anneaux_par_code.values() for a in an for pt in a]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    e = min(larg / ((lon1 - lon0) * k), haut / (lat1 - lat0))
    dx = x0 + (larg - (lon1 - lon0) * k * e) / 2
    dy = y0 + (haut - (lat1 - lat0) * e) / 2
    return {code: "".join("M" + "L".join(f"{dx + (lon - lon0) * k * e:.1f} {dy + (lat1 - lat) * e:.1f}" for lon, lat in a) + "Z"
                          for a in an) for code, an in anneaux_par_code.items()}


def _fond():
    """Tracés SVG des 101 départements : métropole, encadrés des DROM et de la petite couronne. Calculé une seule fois."""
    if "fond" not in _cache:
        geo = {f["properties"]["code"]: (f["properties"]["nom"], _anneaux(f["geometry"]))
               for f in json.load(open(FOND, encoding="utf-8"))["features"]}
        metro = {c: an for c, (_, an) in geo.items() if len(c) == 2}
        traces = [(c, d, "") for c, d in _projeter(metro, 100, 8, 500, 504).items()]
        cadres = []
        for i, (c, lib) in enumerate(DROM.items()):
            y = 8 + i * 100
            traces += [(c, d, "") for c, d in _projeter({c: geo[c][1]}, 8, y + 4, 70, 66).items()]
            cadres.append((4, y, 78, 88, lib))
        traces += [(c, d, " zoom") for c, d in _projeter({c: metro[c] for c in PETITE_COURONNE}, 586, 12, 66, 56).items()]
        cadres.append((582, 8, 74, 78, "Petite couronne"))
        _cache["fond"] = (traces, cadres, {c: nom for c, (nom, _) in geo.items()})
    return _cache["fond"]


def _seuils(valeurs):
    """Seuils de classes par quantiles (au plus NB_CLASSES classes ; seuils en double supprimés)."""
    v = sorted(valeurs)
    seuils = []
    for i in range(1, NB_CLASSES):
        s = v[min(len(v) - 1, round(i * len(v) / NB_CLASSES))]
        if s not in seuils and s > v[0]:
            seuils.append(s)
    return seuils


def carte_departements(ident, indicateurs, titre):
    """Carte choroplèthe interactive.

    indicateurs : liste de dicts {"libelle": bouton, "legende": phrase, "valeurs": {code_departement: nombre ou None},
    "fmt": fonction de formatage, "inverse": True si les valeurs basses sont les plus préoccupantes ; en option,
    "seuils": bornes de classes imposées (sinon quantiles) et "etiquettes": libellés de légende correspondants}.
    Les départements absents ou à None sont en gris (« pas de donnée »).
    """
    traces, cadres, noms = _fond()
    donnees, legendes = [], []
    for ind in indicateurs:
        vals = {c: v for c, v in ind["valeurs"].items() if v is not None and c in noms}
        seuils = ind.get("seuils") or _seuils(vals.values())  # seuils imposés (ex. comptages entiers) ou quantiles
        nb = len(seuils) + 1
        fmt, inv = ind["fmt"], ind.get("inverse", False)

        def teinte(k, nb=nb, inv=inv):  # classe de valeur k (0 = plus basse) -> teinte 0 (claire) à 4 (foncée)
            pos = (nb - 1 - k) if inv else k
            return round(pos * (NB_CLASSES - 1) / (nb - 1)) if nb > 1 else 2

        donnees.append({c: [teinte(sum(1 for s in seuils if v >= s)), fmt(v)] for c, v in vals.items()})
        bornes = []
        for k in range(nb):
            if nb == 1:
                txt = "toutes valeurs"
            elif k == 0:
                txt = f"moins de {fmt(seuils[0])}"
            elif k == nb - 1:
                txt = f"{fmt(seuils[-1])} ou plus"
            else:
                txt = f"de {fmt(seuils[k - 1])} à moins de {fmt(seuils[k])}"
            if ind.get("etiquettes"):
                txt = ind["etiquettes"][k]
            bornes.append(f'<span><i class="k{teinte(k)}"></i>{txt}</span>')
        legendes.append(f'<span class="titre-carte">{ind["legende"]}</span>' + "".join(bornes)
                        + '<span><i class="kv"></i>pas de donnée</span>')
    chemins = "".join(f'<path class="kv{z}" data-c="{c}" d="{d}"/>' for c, d, z in traces)
    boites = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="none" style="stroke:var(--ring)"/>'
                     f'<text x="{x + w / 2}" y="{y + h - 5}" text-anchor="middle" font-size="9" style="fill:var(--muted)">{lib}</text>'
                     for x, y, w, h, lib in cadres)
    boutons = "".join(f'<button type="button" aria-pressed="{"true" if i == 0 else "false"}" data-i="{i}">{ind["libelle"]}</button>'
                      for i, ind in enumerate(indicateurs)) if len(indicateurs) > 1 else ""
    js = json.dumps({"d": donnees, "l": legendes, "n": {c: noms[c] for c, _, _ in traces}}, ensure_ascii=False, separators=(",", ":"))
    return f"""
<div class="carte" id="{ident}">
  <div class="choix" role="group" aria-label="Indicateur affiché">{boutons}</div>
  <div class="legende-carte"></div>
  <div class="cadre">
    <svg viewBox="0 0 {LARG} {HAUT_CARTE}" role="img" aria-label="{titre}">{boites}{chemins}</svg>
    <div class="bulle" role="status"></div>
  </div>
</div>
<script>
(function () {{
  var C = {js}, racine = document.getElementById('{ident}'), bulle = racine.querySelector('.bulle'),
      cadre = racine.querySelector('.cadre'), leg = racine.querySelector('.legende-carte'), i = 0;
  var chemins = racine.querySelectorAll('path'), boutons = racine.querySelectorAll('.choix button');
  function peindre() {{
    leg.innerHTML = C.l[i];
    Array.prototype.forEach.call(chemins, function (p) {{
      var v = C.d[i][p.dataset.c];
      p.setAttribute('class', v ? 'k' + v[0] : 'kv');
    }});
  }}
  function montrer(p, e) {{
    var v = C.d[i][p.dataset.c], r = cadre.getBoundingClientRect();
    bulle.innerHTML = '<strong>' + C.n[p.dataset.c] + '</strong><br>' + (v ? v[1] : 'pas de donnée');
    bulle.style.display = 'block';
    bulle.style.left = Math.max(0, Math.min(e.clientX - r.left + 12, r.width - bulle.offsetWidth - 4)) + 'px';
    bulle.style.top = Math.max(0, Math.min(e.clientY - r.top + 12, r.height - bulle.offsetHeight - 4)) + 'px';
  }}
  Array.prototype.forEach.call(chemins, function (p) {{
    p.addEventListener('pointermove', function (e) {{ montrer(p, e); }});
    p.addEventListener('click', function (e) {{ montrer(p, e); }});
    p.addEventListener('pointerleave', function () {{ bulle.style.display = 'none'; }});
  }});
  Array.prototype.forEach.call(boutons, function (b) {{
    b.addEventListener('click', function () {{
      i = +b.dataset.i;
      Array.prototype.forEach.call(boutons, function (x) {{ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); }});
      peindre();
    }});
  }});
  peindre();
}})();
</script>"""


def section_carte(surtitre, titre, carte, note, ident="carte"):
    """Section avec carte à gauche et texte à droite (même mise en page que les sections à graphique)."""
    return f"""
<section id="{ident}">
  <h3>0 · {surtitre}</h3>
  <h2>{titre}</h2>
  <div class="row">
    <div class="chart">{carte}</div>
    <div class="note">{note}</div>
  </div>
</section>"""
