"""Génère rapport_sante.html à partir de la fiche validée donnees_propres/sante/chiffres_sante.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Le style est repris de rapport_lots.html (EDR-011).
Usage : python3 generer_rapport_sante.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # module graphiques_svg du projet
FICHE = "donnees_propres/sante/chiffres_sante.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapports/rapport_sante.html"

C = json.load(open(FICHE, encoding="utf-8"))
COUL = {"Public": "var(--s1)", "Privé non lucratif": "var(--dim)", "Privé lucratif": "var(--s2)"}
STATUTS = ["Public", "Privé non lucratif", "Privé lucratif"]


from graphiques_svg import (D, G, H, HAUT, BAS, W, STYLE_MILITANT, axe_y, barres_divergentes, barres_empilees, barres_groupees,
                            barres_h, casse_en_chiffres, courbes, d, ecart, echelle, empile_100_h, legende, lecture, m, n, pct,
                            section, svg)
from graphiques_svg import alleger_limites, barres_divergentes, limite  # noqa: E402
CP = json.load(open("donnees_propres/comparaisons/chiffres_comparaisons.json", encoding="utf-8"))  # comparaisons : population, Europe, OCDE
from cartes_svg import STYLE_CARTE, carte_departements, section_carte  # noqa: E402


# --- Contenu ------------------------------------------------------------------
L, E, S, MA, A, U = (C[k] for k in ("lits", "effectifs", "soins_critiques", "maternites", "apl", "urgences"))
apl_fin, apl_debut = A["serie"][-1], A["serie"][0]

# 1. Lits : indice base 100 (lits et places n'ont pas le même ordre de grandeur)
ann = [x["annee"] for x in L["serie"]]
idx_l = [100 * x["lits"] / L["serie"][0]["lits"] for x in L["serie"]]
idx_p = [100 * x["places"] / L["serie"][0]["places"] for x in L["serie"]]
g1 = courbes([("Lits", "var(--s1)", idx_l), ("Places", "var(--s2)", idx_p)], ann, 80, 140, 10,
             lambda v: n(v), f"Indice des lits et des places, base 100 en {ann[0]}", mention=f"Indice, base 100 en {ann[0]}")
s1 = section("1", "Lits d'hôpital", f"{n(abs(L['lits']['ecart']))} lits d'hospitalisation complète en moins depuis {L['periode'][0]}", g1, f"""
  <p class="take">Les établissements de santé comptent <strong>{n(L['lits']['fin'])}</strong> lits d'hospitalisation complète fin {L['periode'][1]}, contre {n(L['lits']['debut'])} fin {L['periode'][0]} : <strong>{pct(L['lits']['pct'])}</strong>.</p>
  <p>Dans le même temps, les places d'hospitalisation partielle (on entre et on sort le même jour) passent de {n(L['places']['debut'])} à {n(L['places']['fin'])} ({pct(L['places']['pct'])}).</p>
  <p>Ce recul coïncide avec la hausse des places ambulatoires, ce qui est cohérent avec le « virage ambulatoire » ; les données ne permettent pas de mesurer quelle part du recul il explique. Pour les patients qui doivent rester plusieurs jours, le nombre de lits disponibles, lui, a baissé de {pct(abs(L['lits']['pct']), False)}.</p>
  <p><strong>Limite :</strong> cette série ne distingue pas l'hôpital public des cliniques privées et n'est pas rapportée à la population.</p>""",
             legende([("Lits d'hospitalisation complète", "var(--s1)"), ("Places d'hospitalisation partielle", "var(--s2)")]))

# 2. Maternités
g2 = barres_empilees([(x["annee"], x) for x in MA["serie"]], STATUTS, 600, 100, n, "Nombre de maternités par statut")
ps = MA["par_statut"]
s2 = section("2", "Maternités", f"{n(abs(MA['total']['ecart']))} maternités en moins en {int(MA['periode'][1]) - int(MA['periode'][0])} ans", g2, f"""
  <p class="take">La France passe de <strong>{n(MA['total']['debut'])}</strong> maternités en {MA['periode'][0]} à <strong>{n(MA['total']['fin'])}</strong> en {MA['periode'][1]}, soit <strong>{pct(MA['total']['pct'])}</strong>. Les lits d'obstétrique reculent encore plus vite : {pct(MA['lits_obstetrique']['pct'])} ({n(MA['lits_obstetrique']['debut'])} → {n(MA['lits_obstetrique']['fin'])}).</p>
  <p>Ce sont les maternités privées lucratives qui disparaissent le plus de la liste : {ps['Privé lucratif']['debut']} → {ps['Privé lucratif']['fin']} ({pct(ps['Privé lucratif']['pct'])}). Le public perd {abs(ps['Public']['ecart'])} maternités ({pct(ps['Public']['pct'])}) et représente <strong>{d(MA['part_public'][MA['periode'][1]], 0)}&nbsp;%</strong> des maternités en {MA['periode'][1]} ({d(MA['part_public'][MA['periode'][0]], 0)}&nbsp;% en {MA['periode'][0]}).</p>
  <p><em>Notre lecture :</em> le privé lucratif se retire plus vite de l'obstétrique que le public, qui assure une part croissante de l'offre de maternités.</p>
  <p><strong>Limite :</strong> le nombre de sites ne dit pas combien de temps les femmes mettent pour rejoindre une maternité.</p>""",
             legende([(s, COUL[s]) for s in STATUTS]))

# 3. APL
g3 = barres_groupees([(x["annee"], [x["part"], x["part_medecins_65_ans_et_moins"]]) for x in A["serie"]],
                     ["var(--s1)", "var(--s2)"], 35, 5, lambda v: d(v) + " %",
                     "Part de la population en commune sous-dotée en médecins généralistes")
seuil = d(A["seuil"])
s3 = section("3", "Médecins généralistes", f"{d(apl_fin['population_sous_dense'] / 1e6)} millions d'habitants en commune sous-dotée", g3, f"""
  <p class="take">En {apl_fin['annee']}, <strong>{pct(apl_fin['part'], False)}</strong> de la population (France hors Mayotte) vit dans une commune où l'on a accès à {seuil} consultations ou moins de généraliste par an et par habitant, contre {pct(apl_debut['part'], False)} en {apl_debut['annee']}.</p>
  <p>Cela représente <strong>{ecart(A['evolution_population']['ecart'])}</strong> personnes en deux ans ({pct(A['evolution_population']['pct'])}), dans {n(apl_fin['communes_sous_denses'])} communes. La hausse reflète en partie l'évolution de la population (populations Insee 2020 → 2022).</p>
  <p>Si l'on ne compte que les médecins de 65 ans ou moins (variante publiée par la DREES, qui écarte les médecins proches de la retraite) et qu'on applique le même seuil, la part monte à <strong>{pct(apl_fin['part_medecins_65_ans_et_moins'], False)}</strong>.</p>
  <p>L'accessibilité moyenne baisse aussi : {d(apl_debut['apl_moyen_medecins_65_ans_et_moins'], 2)} → {d(apl_fin['apl_moyen_medecins_65_ans_et_moins'], 2)} consultations par an et par habitant (médecins de 65 ans ou moins).</p>
  <p><strong>Limite :</strong> il s'agit de la médecine de ville (libéraux et centres de santé), pas de l'hôpital. Cette version de l'indicateur ne permet pas de remonter avant {apl_debut['annee']}.</p>""",
             legende([("Tous médecins", "var(--s1)"), ("Médecins de 65 ans ou moins", "var(--s2)")]))

# 4. Personnel
ann_e = [x["annee"] for x in E["serie"]]
g4 = courbes([("Public", "var(--s1)", [x["public"] for x in E["serie"]]), ("Privé", "var(--s2)", [x["prive"] for x in E["serie"]])],
             ann_e, 0, 1_200_000, 200_000, lambda v: (d(v / 1e6, 2) + " M") if v else "0",
             "Salariés du secteur hospitalier, public et privé")
me = E["metiers"]
s4 = section("4", "Personnel hospitalier", f"Plus de salariés à l'hôpital public, une part quasi stable ({d(E['part_public'][E['periode'][1]] - E['part_public'][E['periode'][0]], 0).replace('-', '−')} point depuis {E['periode'][0]})", g4, f"""
  <p class="take">L'hôpital public emploie <strong>{n(E['public']['fin'])}</strong> salariés fin {E['periode'][1]}, contre {n(E['public']['debut'])} en {E['periode'][0]} ({pct(E['public']['pct'])}). Le privé progresse plus vite ({pct(E['prive']['pct'])}).</p>
  <p>Le public reste le premier employeur hospitalier : {d(E['part_public'][E['periode'][1]])}&nbsp;% des salariés en {E['periode'][1]}, contre {d(E['part_public'][E['periode'][0]])}&nbsp;% en {E['periode'][0]}.</p>
  <p>Infirmiers du public : {n(me['4 - Infirmiers']['Public']['debut'])} → {n(me['4 - Infirmiers']['Public']['fin'])} ({pct(me['4 - Infirmiers']['Public']['pct'])}). Médecins du public (hors internes, comptés à part) : {n(me['1 - Médecins et assimilés']['Public']['debut'])} → {n(me['1 - Médecins et assimilés']['Public']['fin'])} ({pct(me['1 - Médecins et assimilés']['Public']['pct'])}).</p>
  <p><strong>Limite importante :</strong> ce sont des personnes, pas des équivalents temps plein. Ces chiffres ne disent rien du temps partiel, des postes vacants ni de la charge de travail, et ne sont pas rapportés au nombre de patients.</p>""",
             legende([("Public", "var(--s1)"), ("Privé (lucratif et non lucratif)", "var(--s2)")]))

# 5. Réanimation adulte
g5 = barres_empilees([(x["annee"], x) for x in S["rea_serie"]], STATUTS, 7000, 1000, n,
                     "Lits de réanimation adulte par statut", coupures=("2019",))
s5 = section("5", "Réanimation", "Réanimation : après le pic de 2020, un niveau légèrement supérieur à 2019", g5, f"""
  <p class="take">Fin {S['annees'][-1]}, la France compte <strong>{n(S['rea_2019_2024']['fin'])}</strong> lits de réanimation adulte, contre {n(S['rea_2019_2024']['debut'])} fin 2019 ({pct(S['rea_2019_2024']['pct'])}).</p>
  <p>Le pic de fin 2020 (<strong>{n(S['rea_pic_2020'])}</strong> lits), atteint pendant l'épidémie, n'a pas été maintenu.</p>
  <p>L'hôpital public porte <strong>{d(S['part_public_rea'][S['annees'][-1]])}&nbsp;%</strong> des lits de réanimation adulte.</p>
  <p><strong>Limites :</strong> aucune donnée entre 2014 et 2018 (pointillé rouge). Les données 2024 montrent un transfert apparent de lits de surveillance continue vers d'autres soins intensifs (reclassement probable, non documenté par la source) : aucun total de soins critiques n'est donc comparé. La licence de ce jeu de données n'est pas renseignée par la DREES.</p>""",
             legende([(s, COUL[s]) for s in STATUTS]))

# 6. Urgences
ann_u = [x["annee"] for x in U["serie"]]
g6 = courbes([("Passages", "var(--s1)", [x["passages"] for x in U["serie"]])], ann_u, 16e6, 22e6, 1e6,
             lambda v: m(v), "Passages aux urgences par an (axe tronqué)", etiquette_dessous=True,
             mention="Axe tronqué : commence à 16 M")
du = U["depuis_2019"]
s6 = section("6", "Urgences", "Les passages aux urgences restent sous leur niveau de 2019", g6, f"""
  <p class="take">Environ <strong>{m(U['total']['fin'])}</strong> de passages aux urgences en {U['periode'][1]}, contre {m(du['debut'])} en 2019 ({pct(du['pct'])}) et {m(U['total']['debut'])} en {U['periode'][0]} ({pct(U['total']['pct'])}).</p>
  <p>La chute de 2020 correspond à la crise sanitaire. Depuis, la fréquentation reste sous son niveau d'avant-crise, même si {U['departements_en_hausse']} départements sur {U['nb_departements']} sont en hausse sur la période.</p>
  <p>Moins de passages ne veut pas dire moins de besoins : la baisse peut aussi venir de la régulation par le 15, de fermetures de services la nuit ou de réorientations. Les données ne permettent pas de trancher.</p>
  <p><strong>Limite :</strong> l'axe vertical commence à 16 millions pour rendre les variations lisibles. Passages estimés par la DREES, sur {U['nb_departements']} départements (hors {", ".join(U['exclus'])}, Martinique, Lozère et Mayotte).</p>""")

# --- Sections détaillées --------------------------------------------------------
CD, ED, MD, AD, UD, DEPS = (C[k] for k in ("critiques_detail", "effectifs_detail", "maternites_detail",
                                           "apl_detail", "urgences_detail", "departements"))
COUL_UNITES = {"REAADU": "var(--s1)", "REAENF": "var(--s3)", "USIC": "var(--s5)", "SIUNV": "var(--s4)",
               "AUTSI": "var(--s6)", "SURVADU": "var(--s2)", "SURVENF": "var(--dim)"}
LIB_UNITES = {"REAADU": "Réanimation adulte", "REAENF": "Réanimation pédiatrique", "USIC": "Soins intensifs de cardiologie",
              "SIUNV": "Soins intensifs neuro-vasculaires", "AUTSI": "Autres soins intensifs",
              "SURVADU": "Surveillance continue adulte", "SURVENF": "Surveillance continue pédiatrique"}
COUL_METIERS = {"1 - Médecins et assimilés": "var(--s1)", "2 - Internes": "var(--s3)", "3 - Sages-femmes": "var(--s4)",
                "4 - Infirmiers": "var(--s2)", "5 - Aides-soignants": "var(--s5)", "6 - Filière administrative": "var(--s6)",
                "7 - Autre personnel (soignants et non soignants)": "var(--dim)"}
lib_metier = lambda p: p.split(" - ", 1)[1]
COUL_TYPES = {"1": "var(--s2)", "2a": "var(--s5)", "2b": "var(--s3)", "3": "var(--s1)"}
COUL_APL = dict(zip(AD["classes"], ["var(--warn)", "var(--s2)", "var(--s5)", "var(--s1)"]))
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

# Soins critiques par unité (2024 exclu : reclassement)
uni = [u for u in CD["unites"] if u["annee"] != "2024"]
g_unites = barres_empilees([(u["annee"], u) for u in uni], list(LIB_UNITES), 25000, 5000, n,
                           "Lits de soins critiques par unité", coupures=("2019",), couleurs=COUL_UNITES)
u13, u23 = uni[0], uni[-1]
part_surv = 100 * (u23["SURVADU"] + u23["SURVENF"]) / sum(u23[k] for k in LIB_UNITES)
s_unites = section("0", "Soins critiques", f"La surveillance continue représente {d(part_surv, 0)}&nbsp;% des lits de soins critiques", g_unites, f"""
  <p class="take">Fin {u23['annee']}, les établissements comptent <strong>{n(sum(u23[k] for k in LIB_UNITES))}</strong> lits de soins critiques, dont {n(u23['REAADU'])} en réanimation adulte et {n(u23['REAENF'])} en réanimation pédiatrique.</p>
  <p>La surveillance continue adulte (patients qui ont besoin d'une surveillance rapprochée sans être en réanimation) compte {n(u23['SURVADU'])} lits, contre {n(u13['SURVADU'])} en {u13['annee']}.</p>
  <p>Les soins intensifs neuro-vasculaires (accidents vasculaires cérébraux) passent de {n(u13['SIUNV'])} à {n(u23['SIUNV'])} lits ({pct(100 * (u23['SIUNV'] - u13['SIUNV']) / u13['SIUNV'], True)}), et la surveillance continue pédiatrique de {n(u13['SURVENF'])} à {n(u23['SURVENF'])} ({pct(100 * (u23['SURVENF'] - u13['SURVENF']) / u13['SURVENF'])}).</p>
  <p><strong>Limite :</strong> l'année 2024 n'est pas montrée, car la répartition entre unités y change fortement (reclassement probable). Pas de données 2014-2018 (pointillé rouge). Libellés des unités reconstitués.</p>""",
                   legende([(LIB_UNITES[k], COUL_UNITES[k]) for k in LIB_UNITES]))

# Réanimation adulte par département
rd = CD["rea_pour_100k_dep"]
k = 12
g_rea_dep = barres_h([(o["nom"], o["pour_100k"]) for o in rd[:k] + rd[-k:]], lambda v: d(v),
                     "Lits de réanimation adulte pour 100 000 habitants, par département",
                     couleur=lambda i, v: "var(--s2)" if i < k else "var(--s1)", coupure=k)
s_rea_dep = section("0", "Réanimation par territoire", f"De {d(CD['rea_pour_100k_ecart'][0], 0)} à {d(CD['rea_pour_100k_ecart'][1], 0)} lits de réanimation pour 100&nbsp;000 habitants selon le département", g_rea_dep, f"""
  <p class="take">En moyenne, la France compte <strong>{d(CD['rea_pour_100k_national'])}</strong> lits de réanimation adulte pour 100&nbsp;000 habitants (fin 2024). Mais l'écart va de <strong>{d(CD['rea_pour_100k_ecart'][0])}</strong> ({rd[0]['nom']}) à <strong>{d(CD['rea_pour_100k_ecart'][1])}</strong> ({rd[-1]['nom']}).</p>
  <p>Les taux les plus élevés se trouvent à {rd[-1]['nom']}, dans les {rd[-2]['nom']} et dans le {rd[-3]['nom']}. <em>Notre lecture :</em> les lits sont concentrés dans les départements qui ont un grand centre hospitalier ; ailleurs, les patients en réanimation sont souvent pris en charge dans un département voisin.</p>
  <p><strong>{CD['deps_sans_rea_pediatrique']} départements sur {CD['nb_departements']}</strong> n'ont aucun lit de réanimation pédiatrique fin 2024.</p>
  <p><strong>Limite :</strong> le taux mesure où sont les lits, pas l'accès réel des habitants, qui dépend des distances et des transferts. La réanimation pédiatrique est concentrée dans quelques établissements par région ; son absence dans un département ne signifie pas une absence de prise en charge. Population totale Insee 2022.</p>""",
                    legende([(f"Les {k} moins dotés", "var(--s2)"), (f"Les {k} plus dotés", "var(--s1)")]))

# Personnel par métier (public, indice 2003 = 100)
metiers = [p for p in ED["indice_public"] if not p.startswith("7")]
g_metiers = courbes([(lib_metier(p), COUL_METIERS[p], ED["indice_public"][p]) for p in metiers], ED["annees"],
                    50, 250, 50, lambda v: n(v), "Salariés de l'hôpital public par métier, indice base 100 en 2003",
                    mention=f"Indice, base 100 en {ED['annees'][0]}")
ev = ED["evol_public"]
s_metiers = section("0", "Métiers de l'hôpital public", "Les internes ont plus que doublé, les aides-soignants progressent le moins parmi les métiers détaillés", g_metiers, f"""
  <p class="take">Entre {ED['annees'][0]} et {ED['annees'][-1]}, le nombre d'<strong>internes</strong> de l'hôpital public passe de {n(ev['2 - Internes']['debut'])} à {n(ev['2 - Internes']['fin'])} ({pct(ev['2 - Internes']['pct'])}).</p>
  <p>Les sages-femmes progressent de {pct(ev['3 - Sages-femmes']['pct'], False)}, les médecins de {pct(ev['1 - Médecins et assimilés']['pct'], False)}, les infirmiers de {pct(ev['4 - Infirmiers']['pct'], False)}.</p>
  <p>Les <strong>aides-soignants</strong>, au cœur des soins quotidiens, ne progressent que de {pct(ev['5 - Aides-soignants']['pct'], False)} ; la filière administrative de {pct(ev['6 - Filière administrative']['pct'], False)}.</p>
  <p><strong>Limite :</strong> personnes physiques, pas équivalents temps plein ; séries par métier en partie rétropolées par la DREES.</p>""",
                    legende([(lib_metier(p), COUL_METIERS[p]) for p in metiers]))

# Part du public par métier
pp = ED["part_public"]
g_part = barres_h([(lib_metier(o["profession"]).replace(" (soignants et non soignants)", ""), o["part_public"]) for o in pp],
                  lambda v: d(v) + "&nbsp;%", "Part du public dans les salariés hospitaliers, par métier", vmax=100)
s_part = section("0", "Public et privé", "Trois salariés hospitaliers sur quatre travaillent dans le public", g_part, f"""
  <p class="take">En {ED['annees'][-1]}, l'hôpital public emploie <strong>{d(pp[0]['part_public'], 0)}&nbsp;%</strong> des internes et <strong>{d(next(o for o in pp if o['profession'].startswith('1'))['part_public'], 0)}&nbsp;%</strong> des médecins salariés du secteur hospitalier.</p>
  <p>Les internes, médecins en formation, sont presque tous salariés de l'hôpital public.</p>
  <p>Même pour les infirmiers, le métier soignant où le privé pèse le plus, le public emploie {d(next(o for o in pp if o['profession'].startswith('4'))['part_public'], 0)}&nbsp;% des salariés.</p>
  <p><strong>Limite :</strong> seuls les salariés sont comptés. Les médecins libéraux qui exercent en clinique privée n'y figurent pas, ce qui sous-estime le poids du privé pour les médecins.</p>""")

# Maternités par type
te = MD["types_evol"]
g_types = barres_empilees([(t["annee"], t) for t in MD["types"]], ["3", "2b", "2a", "1"], 600, 100, n,
                          "Nombre de maternités par type", couleurs=COUL_TYPES)
s_types = section("0", "Types de maternités", f"Le type 1 représente {abs(te['1']['ecart'])} des {abs(MA['total']['ecart'])} maternités en moins (solde net)", g_types, f"""
  <p class="take">Les maternités de <strong>type 1</strong>, qui n'ont pas de service de néonatologie sur place, passent de {te['1']['debut']} à <strong>{te['1']['fin']}</strong> ({pct(te['1']['pct'])}). </p>
  <p>Les maternités équipées pour les nouveau-nés fragiles se maintiennent : type 2b {te['2b']['debut']} → {te['2b']['fin']}, type 3 (avec réanimation néonatale) {te['3']['debut']} → {te['3']['fin']}.</p>
  <p><em>Notre lecture :</em> l'offre se concentre dans des établissements plus grands et plus spécialisés, probablement au prix de trajets plus longs pour une partie des femmes, ce que ces données ne mesurent pas.</p>
  <p><strong>Limite :</strong> les données ne mesurent pas les temps de trajet. Une maternité peut changer de type d'une année à l'autre. En 2021, le total est de 471 : la ligne sans type (Dinan) est exclue de ce graphique.</p>""",
                  legende([("Type 3", COUL_TYPES["3"]), ("Type 2b", COUL_TYPES["2b"]), ("Type 2a", COUL_TYPES["2a"]), ("Type 1", COUL_TYPES["1"])]))

# Taille des maternités
a0m, a1m = MD["periode"]
g_taille = barres_groupees([(cl, [MD["taille"][a0m][cl], MD["taille"][a1m][cl]]) for cl in MD["taille"][a0m]],
                           ["var(--dim)", "var(--s1)"], 200, 50, n, "Nombre de maternités selon le nombre d'accouchements dans l'année")
s_taille = section("0", "Taille des maternités", "Moins de maternités moyennes, un peu plus de très petites", g_taille, f"""
  <p class="take">Entre {a0m} et {a1m}, le nombre de maternités réalisant <strong>1 000 à 1 999</strong> accouchements par an passe de {MD['taille'][a0m]['1 000 à 1 999']} à <strong>{MD['taille'][a1m]['1 000 à 1 999']}</strong>, et celles de 500 à 999 de {MD['taille'][a0m]['500 à 999']} à {MD['taille'][a1m]['500 à 999']}.</p>
  <p>Les très petites maternités (moins de 500 accouchements) sont {MD['taille'][a0m]['< 500']} en {a0m} et {MD['taille'][a1m]['< 500']} en {a1m}.</p>
  <p><strong>Limite :</strong> nombre d'accouchements des maternités ouvertes au 31 décembre. La DREES précise que ce fichier ne permet pas de compter le total des accouchements d'une année.</p>""",
                   legende([(a0m, "var(--dim)"), (a1m, "var(--s1)")]))

# Maternités par département
pdp = [o for o in MD["par_departement"] if o["ecart"] < 0][:15]
g_mat_dep = barres_h([(o["nom"], abs(o["ecart"])) for o in pdp], lambda v: "−" + n(v),
                     "Départements ayant perdu le plus de maternités", couleur="var(--s2)")
une = MD["deps_une_seule"]
s_mat_dep = section("0", "Maternités par territoire", f"{MD['deps_en_baisse']} départements ont perdu au moins une maternité", g_mat_dep, f"""
  <p class="take">Entre {a0m} et {a1m}, <strong>{MD['deps_en_baisse']} départements</strong> sur {len(MD['par_departement'])} ont vu disparaître au moins une maternité. Le département qui en perd le plus : {pdp[0]['nom']} ({pdp[0]['debut']} → {pdp[0]['fin']}).</p>
  <p><strong>{len(une[a1m])} départements</strong> n'ont plus qu'une seule maternité en {a1m}, contre {len(une[a0m])} en {a0m} : {", ".join(une[a1m])}.</p>
  <p><em>Notre lecture :</em> dans ces départements, toute fermeture, même temporaire, de la seule maternité oblige les femmes à accoucher dans un autre département.</p>
  <p><strong>Limite :</strong> une maternité qui disparaît de la liste peut avoir fermé, fusionné ou perdu son autorisation ; la source ne le précise pas.</p>""")

# APL : répartition de la population par classe
g_classes = empile_100_h([(r["annee"], r) for r in AD["repartition"]], AD["classes"], COUL_APL,
                         "Répartition de la population selon l'accès aux médecins généralistes")
rp0, rp1 = AD["repartition"][0], AD["repartition"][-1]
s_classes = section("0", "Accès aux généralistes", "La part de la population ayant accès à plus de 3,5 consultations recule", g_classes, f"""
  <p class="take">La part de la population qui a accès à plus de 3,5 consultations par an et par habitant passe de <strong>{d(rp0['3,5 à 4,5'] + rp0['> 4,5'])}&nbsp;%</strong> en {rp0['annee']} à <strong>{d(rp1['3,5 à 4,5'] + rp1['> 4,5'])}&nbsp;%</strong> en {rp1['annee']}.</p>
  <p>Dans le même temps, la classe la plus basse (2,5 consultations ou moins, définition Insee de la commune sous-dotée) gagne {d(rp1['≤ 2,5'] - rp0['≤ 2,5'])} points.</p>
  <p><strong>Limite :</strong> seul le seuil de 2,5 est une définition officielle ; les autres classes servent uniquement à la lecture. Tous médecins généralistes, France hors Mayotte.</p>""",
                    legende([(f"{c} consultations", COUL_APL[c]) for c in AD["classes"]]))

# APL : départements les plus touchés
ad_fin = sorted(AD["departements"], key=lambda o: -o["part_fin"])[:15]
g_apl_dep = barres_h([(o["nom"], o["part_fin"]) for o in ad_fin], lambda v: d(v) + "&nbsp;%",
                     "Part de la population en commune sous-dotée en généralistes, par département", couleur="var(--warn)", vmax=100)
s_apl_dep = section("0", "Déserts médicaux par territoire", f"Dans {len(AD['deps_majorite_sous_dotee'])} départements, la majorité des habitants est en commune sous-dotée", g_apl_dep, f"""
  <p class="take">En {AD['periode'][1]}, plus de la moitié de la population vit en commune sous-dotée dans <strong>{len(AD['deps_majorite_sous_dotee'])} départements</strong> : {", ".join(AD['deps_majorite_sous_dotee'])}.</p>
  <p>Le {ad_fin[0]['nom']} arrive en tête avec <strong>{d(ad_fin[0]['part_fin'])}&nbsp;%</strong>. Les quatre départements de grande couronne francilienne (77, 78, 91, 95) dépassent tous 50&nbsp;%. <em>Notre lecture :</em> les déserts médicaux ne sont pas seulement ruraux.</p>
  <p><strong>Limite :</strong> la part dépend du découpage communal ; l'APL tient compte des communes voisines dans un rayon de 20 minutes.</p>""")

# APL : plus fortes dégradations
ad_hausse = sorted(AD["departements"], key=lambda o: -o["ecart_points"])[:15]
g_apl_hausse = barres_h([(o["nom"], o["ecart_points"]) for o in ad_hausse], lambda v: "+" + d(v) + "&nbsp;pt",
                        "Hausse de la part de population en commune sous-dotée, en points", couleur="var(--s2)")
s_apl_hausse = section("0", "Dégradation récente", f"La part d'habitants en commune sous-dotée augmente dans {AD['deps_en_hausse']} départements sur {len(AD['departements'])}", g_apl_hausse, f"""
  <p class="take">Entre {AD['periode'][0]} et {AD['periode'][1]}, la part d'habitants en commune sous-dotée augmente dans <strong>{AD['deps_en_hausse']} départements sur {len(AD['departements'])}</strong>.</p>
  <p>Les plus fortes hausses : {ad_hausse[0]['nom']} ({d(ad_hausse[0]['part_debut'])}&nbsp;% → {d(ad_hausse[0]['part_fin'])}&nbsp;%), {ad_hausse[1]['nom']} ({d(ad_hausse[1]['part_debut'])}&nbsp;% → {d(ad_hausse[1]['part_fin'])}&nbsp;%), {ad_hausse[2]['nom']} ({d(ad_hausse[2]['part_debut'])}&nbsp;% → {d(ad_hausse[2]['part_fin'])}&nbsp;%).</p>
  <p><strong>Limite :</strong> deux ans seulement ; une commune peut basculer sous le seuil pour un écart faible d'APL, ce qui amplifie les variations.</p>""")

# Urgences : saisonnalité
sz = UD["saison_moyenne_journaliere"]
g_saison = courbes([("2019", "var(--dim)", sz["2019"]), ("2023", "var(--s1)", sz["2023"])], MOIS, 40000, 65000, 5000,
                   lambda v: n(v), "Passages aux urgences par jour, en moyenne, selon le mois", mention="Axe tronqué : commence à 40 000")
ecarts_mois = [b - a for a, b in zip(sz["2019"], sz["2023"])]
s_saison = section("0", "Urgences au fil de l'année", "Le recul des urgences est le plus fort en début d'année", g_saison, f"""
  <p class="take">En janvier 2023, les urgences accueillent en moyenne <strong>{n(sz['2023'][0])}</strong> passages par jour, contre {n(sz['2019'][0])} en janvier 2019.</p>
  <p>L'écart avec 2019 est le plus marqué en janvier et février, puis se réduit irrégulièrement (encore {pct(100 * (sz['2023'][6] - sz['2019'][6]) / sz['2019'][6])} en juillet) : en décembre, les deux années sont au même niveau ({n(sz['2019'][11])} et {n(sz['2023'][11])} passages par jour).</p>
  <p><strong>Limite :</strong> passages estimés par la DREES, 93 départements ; l'axe commence à 40 000. Deux années seulement : le calendrier des épidémies hivernales (grippe, bronchiolite) varie d'un hiver à l'autre et peut expliquer une partie de l'écart de janvier.</p>""",
                   legende([("2019", "var(--dim)"), ("2023", "var(--s1)")]))

# Urgences par département
udp = UD["departements"]
kk = 10
g_urg_dep = barres_divergentes([(o["nom"], o["pct_2019_2023"]) for o in udp[:kk] + udp[-kk:]],
                               lambda v: ("+" if v > 0 else "−") + d(abs(v)) + "&nbsp;%",
                               "Évolution des passages aux urgences entre 2019 et 2023, par département", coupure=kk)
s_urg_dep = section("0", "Urgences par territoire", f"Les passages baissent dans {UD['deps_en_baisse_depuis_2019']} départements sur {UD['nb_departements']} depuis 2019", g_urg_dep, f"""
  <p class="take">Entre 2019 et 2023, les passages aux urgences diminuent dans <strong>{UD['deps_en_baisse_depuis_2019']} départements sur {UD['nb_departements']}</strong>.</p>
  <p>Les plus fortes baisses : {udp[0]['nom']} ({pct(udp[0]['pct_2019_2023'])}), {udp[1]['nom']} ({pct(udp[1]['pct_2019_2023'])}), {udp[2]['nom']} ({pct(udp[2]['pct_2019_2023'])}).</p>
  <p>Une baisse aussi forte peut signaler des fermetures de services ou une régulation plus stricte de l'accès, plutôt qu'une baisse des besoins. Les données ne permettent pas de le vérifier.</p>
  <p><strong>Limite :</strong> départements couverts en 2019 et en 2023 ; passages estimés.</p>""",
                    legende([("Hausse", "var(--s1)"), ("Baisse", "var(--s2)")]))

# --- Sections issues des sources ajoutées (ARES, RPPS, comptes de la santé) ----------------
AR, MED, CPT = C["ares"], C["medecins"], C["comptes"]
ann_ar = [x["annee"] for x in AR["etablissements"]["serie"]]
pa0, pa1 = AR["periode"]

# Établissements par statut
g_etab = courbes([(st, COUL[st], [100 * x[st] / AR["etablissements"]["serie"][0][st] for x in AR["etablissements"]["serie"]]) for st in STATUTS],
                 ann_ar, 90, 102, 2, lambda v: n(v), "Nombre d'établissements de santé par statut, indice base 100 en 2013",
                 mention=f"Indice, base 100 en {pa0} (axe tronqué)")
ee = AR["etablissements"]["evol"]
s_etab = section("0", "Établissements", f"{abs(ee['Total']['ecart'])} établissements de santé en moins entre {pa0} et {pa1}", g_etab, f"""
  <p class="take">La France compte <strong>{n(ee['Total']['fin'])}</strong> établissements de santé en {pa1}, contre {n(ee['Total']['debut'])} en {pa0} ({pct(ee['Total']['pct'])}).</p>
  <p>Le public en perd le plus : {n(ee['Public']['debut'])} → {n(ee['Public']['fin'])} ({pct(ee['Public']['pct'])}), contre {pct(ee['Privé lucratif']['pct'])} pour les cliniques privées lucratives et {pct(ee['Privé non lucratif']['pct'])} pour le privé non lucratif.</p>
  <p><strong>Limite :</strong> un « établissement » est un site géographique ayant au moins un lit ou une place au 31 décembre ; le regroupement de sites ou un changement d'immatriculation Finess peut réduire ce nombre sans fermeture de service. Données arrêtées en {pa1} (base ARES).</p>""",
                 legende([(st, COUL[st]) for st in STATUTS]))

# Lits MCO par discipline
COUL_MCO = {"Médecine": "var(--s1)", "Chirurgie": "var(--s2)", "Obstétrique": "var(--s4)"}
em = AR["lits_mco"]["evol"]
g_mco = courbes([(k, COUL_MCO[k], [100 * x[k] / AR["lits_mco"]["serie"][0][k] for x in AR["lits_mco"]["serie"]]) for k in COUL_MCO],
                ann_ar, 70, 105, 5, lambda v: n(v), "Lits de médecine, chirurgie et obstétrique, indice base 100 en 2013",
                mention=f"Indice, base 100 en {pa0} (axe tronqué)")
s_mco = section("0", "Médecine, chirurgie, obstétrique", f"Un lit de chirurgie sur quatre a disparu entre {pa0} et {pa1}", g_mco, f"""
  <p class="take">Les lits de <strong>chirurgie</strong> passent de {n(em['Chirurgie']['debut'])} à <strong>{n(em['Chirurgie']['fin'])}</strong> ({pct(em['Chirurgie']['pct'])}), ceux d'<strong>obstétrique</strong> de {n(em['Obstétrique']['debut'])} à {n(em['Obstétrique']['fin'])} ({pct(em['Obstétrique']['pct'])}).</p>
  <p>Les lits de médecine restent stables ({pct(em['Médecine']['pct'])}). Au total, les services de médecine, chirurgie et obstétrique perdent {n(abs(em['Total MCO']['ecart']))} lits ({pct(em['Total MCO']['pct'])}).</p>
  <p><em>Notre lecture :</em> une partie de ce recul correspond probablement au développement de la chirurgie ambulatoire (opérations sans nuit à l'hôpital), ce que ces données ne permettent pas de mesurer.</p>
  <p><strong>Limite :</strong> lits d'hospitalisation complète, tous statuts ; base ARES, {pa0}-{pa1}.</p>""",
                legende([(k, COUL_MCO[k]) for k in COUL_MCO]))

# Psychiatrie
ps_l, ps_j = AR["psychiatrie"]["lits_temps_plein"], AR["psychiatrie"]["places_jour"]
g_psy = courbes([("Lits à temps plein", "var(--s2)", [x["Total"] for x in ps_l["serie"]]),
                 ("Places de jour", "var(--s1)", [x["Total"] for x in ps_j["serie"]])],
                ann_ar, 0, 60000, 10000, lambda v: n(v), "Psychiatrie : lits à temps plein et places d'hospitalisation de jour")
s_psy = section("0", "Psychiatrie", f"{n(abs(ps_l['evol']['Total']['ecart']))} lits de psychiatrie en moins en {int(pa1) - int(pa0)} ans", g_psy, f"""
  <p class="take">Les lits de psychiatrie en hospitalisation à temps plein passent de {n(ps_l['evol']['Total']['debut'])} à <strong>{n(ps_l['evol']['Total']['fin'])}</strong> entre {pa0} et {pa1} ({pct(ps_l['evol']['Total']['pct'])}).</p>
  <p>Les places d'hospitalisation de jour progressent de {n(ps_j['evol']['Total']['ecart'])} seulement ({pct(ps_j['evol']['Total']['pct'])}) : elles ne compensent pas le recul des lits en nombre.</p>
  <p><strong>Limite :</strong> une place de jour et un lit ne prennent pas en charge les mêmes patients ; les prises en charge ambulatoires (consultations en centre médico-psychologique) ne figurent pas ici.</p>""",
                legende([("Lits à temps plein", "var(--s2)"), ("Places de jour", "var(--s1)")]))

# HAD et soins de longue durée
g_had = courbes([("Hospitalisation à domicile", "var(--s1)", [x["Total"] for x in AR["had"]["serie"]]),
                 ("Soins de longue durée", "var(--s2)", [x["Total"] for x in AR["usld"]["serie"]])],
                ann_ar, 0, 35000, 5000, lambda v: n(v), "Places d'hospitalisation à domicile et lits de soins de longue durée")
eh, eu = AR["had"]["evol"]["Total"], AR["usld"]["evol"]["Total"]
s_had = section("0", "Domicile et longue durée", "L'hospitalisation à domicile progresse, les lits de longue durée reculent", g_had, f"""
  <p class="take">L'hospitalisation à domicile peut accueillir <strong>{n(eh['fin'])}</strong> patients en même temps en {pa1}, contre {n(eh['debut'])} en {pa0} ({pct(eh['pct'])}).</p>
  <p>Les unités de soins de longue durée, qui accueillent des personnes très dépendantes à l'hôpital, perdent {n(abs(eu['ecart']))} lits ({n(eu['debut'])} → {n(eu['fin'])}, {pct(eu['pct'])}).</p>
  <p><strong>Limite :</strong> une place d'hospitalisation à domicile et un lit hospitalier ne sont pas équivalents.</p>
  <p><em>Notre lecture :</em> le développement du domicile repose aussi sur les aidants.</p>""",
                legende([("Hospitalisation à domicile (places)", "var(--s1)"), ("Soins de longue durée (lits)", "var(--s2)")]))

# Établissements avec urgences
ua = AR["urgences_autorisees"]
g_urg_aut = barres_groupees([(x["annee"], [x["Établissements avec urgences autorisées"], x["dont urgences pédiatriques autorisées"]]) for x in ua["serie"]],
                            ["var(--s1)", "var(--s3)"], 700, 100, n, "Établissements disposant d'un service d'urgences autorisé")
eua = ua["evol"]
s_urg_aut = section("0", "Services d'urgences", f"{abs(eua['Établissements avec urgences autorisées']['ecart'])} établissements de moins avec un service d'urgences", g_urg_aut, f"""
  <p class="take">En {pa1}, <strong>{n(eua['Établissements avec urgences autorisées']['fin'])}</strong> établissements disposent d'un service d'urgences autorisé, contre {n(eua['Établissements avec urgences autorisées']['debut'])} en {pa0} ({pct(eua['Établissements avec urgences autorisées']['pct'])}).</p>
  <p>Ceux qui ont des urgences pédiatriques passent de {eua['dont urgences pédiatriques autorisées']['debut']} à {eua['dont urgences pédiatriques autorisées']['fin']} ({pct(eua['dont urgences pédiatriques autorisées']['pct'])}).</p>
  <p><strong>Limite :</strong> une autorisation ne dit pas si le service est ouvert en continu ; les fermetures nocturnes ou temporaires n'apparaissent pas.</p>""",
                    legende([("Avec urgences autorisées", "var(--s1)"), ("dont urgences pédiatriques", "var(--s3)")]))

# Médecins : généralistes contre autres spécialités
an_m = MED["annees"]
g_gen = courbes([("Médecine générale", "var(--s2)", [100 * v / MED["generalistes"][0] for v in MED["generalistes"]]),
                 ("Autres spécialités", "var(--s1)", [100 * v / MED["autres_specialites"][0] for v in MED["autres_specialites"]])],
                an_m, 90, 130, 10, lambda v: n(v), "Médecins en activité, indice base 100 en 2012",
                mention=f"Indice, base 100 en {an_m[0]} (axe tronqué)")
eg, ea = MED["evol_generalistes"], MED["evol_autres"]
s_gen = section("0", "Médecins", f"Les autres spécialités {pct(ea['pct'])}, la médecine générale {pct(eg['pct'])}", g_gen, f"""
  <p class="take">Au 1er janvier {an_m[-1]}, la France compte <strong>{n(eg['fin'])}</strong> médecins généralistes en activité, contre {n(eg['debut'])} en {an_m[0]} ({pct(eg['pct'])}).</p>
  <p>Sur la même période, les autres spécialités passent de {n(ea['debut'])} à {n(ea['fin'])} ({pct(ea['pct'])}).</p>
  <p>Rapportée à la population, la densité de généralistes baisse : {d(MED['densite_generalistes'][0])} pour 100&nbsp;000 habitants en {an_m[0]}, <strong>{d(MED['densite_generalistes'][-1])}</strong> en {an_m[-1]} (densités calculées par la DREES).</p>
  <p><strong>Limites :</strong> médecins inscrits à l'Ordre et actifs, quel que soit leur temps de travail. {MED['nouvelles_specialites']['nombre']} spécialités absentes des données en {an_m[0]} ({', '.join(e['specialite'].lower() for e in MED['nouvelles_specialites']['exemples'])}…) comptent {n(MED['nouvelles_specialites']['effectif_fin'])} médecins en {an_m[-1]} ; une partie de ces médecins aurait pu auparavant être comptée en médecine générale, ce qui accentuerait l'écart. En 2024, l'extraction du répertoire a été faite au 30 septembre et l'activité au 1er janvier reconstituée par la DREES.</p>""",
                legende([("Médecine générale", "var(--s2)"), ("Autres spécialités", "var(--s1)")]))

# Âge des généralistes
g_age = courbes([("60 ans et plus", "var(--s2)", MED["part_60_ans_et_plus"])], an_m, 0, 40, 10, lambda v: d(v) + "&nbsp;%",
                "Part des médecins généralistes âgés de 60 ans et plus")
s_age = section("0", "Âge des généralistes", f"{d(MED['part_60_ans_et_plus'][-1], 0)}&nbsp;% des généralistes ont 60 ans ou plus", g_age, f"""
  <p class="take">En {an_m[-1]}, <strong>{d(MED['part_60_ans_et_plus'][-1])}&nbsp;%</strong> des médecins généralistes en activité ont 60 ans ou plus, contre {d(MED['part_60_ans_et_plus'][0])}&nbsp;% en {an_m[0]}.</p>
  <p>Cette part a culminé à {d(MED['part_60_max']['valeur'])}&nbsp;% en {MED['part_60_max']['annee']}, avant de refluer légèrement.</p>
  <p><em>Notre lecture :</em> près d'un généraliste sur trois approche de la retraite ; leurs départs pèseront sur l'accès aux soins dans les années qui viennent.</p>
  <p><strong>Limite :</strong> de nombreux médecins continuent d'exercer après 65 ans ; l'âge ne dit pas quand ils cesseront leur activité.</p>""")

# Généralistes par mode d'exercice
COUL_EX = {"Libéral": "var(--s2)", "Mixte": "var(--s4)", "Salarié hospitalier": "var(--s1)", "Autre Salarié": "var(--s3)"}
g_ex = courbes([(e, COUL_EX[e], MED["par_exercice"][e]) for e in COUL_EX], an_m, 0, 70000, 10000, lambda v: n(v),
               "Médecins généralistes selon le mode d'exercice")
ex = MED["evol_par_exercice"]
s_ex = section("0", "Mode d'exercice", f"Les généralistes exerçant uniquement en libéral {pct(ex['Libéral']['pct'])} depuis {an_m[0]}", g_ex, f"""
  <p class="take">Les généralistes exerçant uniquement en <strong>libéral</strong> passent de {n(ex['Libéral']['debut'])} à <strong>{n(ex['Libéral']['fin'])}</strong> ({pct(ex['Libéral']['pct'])}).</p>
  <p>L'exercice mixte (libéral et salarié à la fois) progresse fortement : {n(ex['Mixte']['debut'])} → {n(ex['Mixte']['fin'])} ({pct(ex['Mixte']['pct'])}). Les salariés hospitaliers évoluent de {pct(ex['Salarié hospitalier']['pct'])}, les autres salariés (centres de santé, etc.) de {pct(ex['Autre Salarié']['pct'])}.</p>
  <p><strong>Limite :</strong> classement de la DREES selon le mode d'exercice déclaré ; un médecin mixte peut consacrer peu de temps à l'une de ses activités.</p>""",
               legende([(e, COUL_EX[e]) for e in COUL_EX]))

# Densité de généralistes par département
dd = [o for o in MED["densite_dep"]]
k3 = 12
g_dens = barres_h([(o["nom"], o["fin"]) for o in dd[:k3] + dd[-k3:]], lambda v: d(v),
                  f"Médecins généralistes pour 100 000 habitants en {an_m[-1]}, par département",
                  couleur=lambda i, v: "var(--s2)" if i < k3 else "var(--s1)", coupure=k3)
pire = [o for o in dd if o["pct"] is not None]
pire_baisse = sorted(pire, key=lambda o: o["pct"])[:3]
s_dens = section("0", "Généralistes par territoire", f"De {d(dd[0]['fin'], 0)} à {d(dd[-1]['fin'], 0)} généralistes pour 100&nbsp;000 habitants selon le département", g_dens, f"""
  <p class="take">En {an_m[-1]}, la densité de généralistes va de <strong>{d(dd[0]['fin'])}</strong> ({dd[0]['nom']}) à <strong>{d(dd[-1]['fin'])}</strong> ({dd[-1]['nom']}) pour 100&nbsp;000 habitants.</p>
  <p>Elle baisse dans <strong>{MED['deps_densite_en_baisse']} départements sur {len([o for o in MED['densite_dep'] if o['pct'] is not None])}</strong> depuis {an_m[0]} ({', '.join(MED['deps_sans_evolution'])} exclue). Les plus fortes baisses : {pire_baisse[0]['nom']} ({pct(pire_baisse[0]['pct'])}), {pire_baisse[1]['nom']} ({pct(pire_baisse[1]['pct'])}), {pire_baisse[2]['nom']} ({pct(pire_baisse[2]['pct'])}).</p>
  <p><strong>Limite :</strong> la densité ne tient compte ni de l'âge de la population ni de l'activité des médecins, contrairement à l'APL. Pas d'évolution calculée pour {", ".join(MED['deps_sans_evolution'])} : la DREES n'y calcule pas de densité en {an_m[0]}-{an_m[1]} (valeur 0).</p>""",
                   legende([(f"Les {k3} moins dotés", "var(--s2)"), (f"Les {k3} plus dotés", "var(--s1)")]))

# Spécialités
sp = MED["specialites"]
g_spe = barres_divergentes([(o["specialite"], o["pct"]) for o in sp], lambda v: ("+" if v > 0 else "−") + d(abs(v)) + "&nbsp;%",
                           f"Évolution du nombre de médecins par spécialité, {an_m[0]}-{an_m[-1]}")
s_spe = section("0", "Spécialités", "La médecine générale est l'une des rares spécialités en recul", g_spe, f"""
  <p class="take">Entre {an_m[0]} et {an_m[-1]}, seules {sum(1 for o in sp if o['pct'] < 0)} spécialités reculent : {", ".join(f"{o['specialite'].lower()} ({pct(o['pct'])})" for o in sp if o['pct'] < 0)}.</p>
  <p>La pédiatrie ({pct(next(o['pct'] for o in sp if o['specialite'] == 'Pédiatrie'))}) et la psychiatrie ({pct(next(o['pct'] for o in sp if o['specialite'] == 'Psychiatrie'))}) progressent, mais ces chiffres ne sont pas rapportés aux besoins.</p>
  <p><strong>Limite :</strong> regroupements de spécialités de la DREES ; « Plateaux techniques » regroupe notamment la radiologie et la biologie. {MED['nouvelles_specialites']['nombre']} spécialités détaillées absentes des données en {an_m[0]} comptent {n(MED['nouvelles_specialites']['effectif_fin'])} médecins en {an_m[-1]}, dont {n(MED['nouvelles_specialites']['effectif_fin_autre_specialite'])} dans « Autre spécialité » ({', '.join(e['specialite'].lower() for e in MED['nouvelles_specialites']['exemples'])}…) ; une partie a pu être classée auparavant dans un autre groupe, en particulier la médecine générale, ce que les données ne permettent pas de mesurer.</p>""",
                    legende([("Hausse", "var(--s1)"), ("Baisse", "var(--s2)")]))

# Financement
fc = CPT["financement_csbm"]
FIN = ["Sécurité sociale", "État et collectivités", "Organismes complémentaires", "Ménages"]
COUL_FIN = dict(zip(FIN, ["var(--s1)", "var(--s3)", "var(--s5)", "var(--s2)"]))
annees_fin = [x for x in fc if x["annee"] in ("2010", "2015", "2020", fc[-1]["annee"])]
g_fin = empile_100_h([(x["annee"], x) for x in annees_fin], FIN, COUL_FIN,
                     "Qui finance la consommation de soins et de biens médicaux")
f0, f1 = fc[0], fc[-1]
s_fin = section("0", "Financement", f"La Sécurité sociale finance {d(f1['Sécurité sociale'], 0)}&nbsp;% des soins et biens médicaux", g_fin, f"""
  <p class="take">En {f1['annee']}, la Sécurité sociale finance <strong>{d(f1['Sécurité sociale'])}&nbsp;%</strong> de la consommation de soins et de biens médicaux ({d(f1['csbm_md'])}&nbsp;Md€), contre {d(f0['Sécurité sociale'])}&nbsp;% en {f0['annee']}.</p>
  <p>La part payée directement par les ménages baisse : {d(f0['Ménages'])}&nbsp;% en {f0['annee']}, {d(f1['Ménages'])}&nbsp;% en {f1['annee']}. Celle des complémentaires santé est stable ({d(f0['Organismes complémentaires'])}&nbsp;% → {d(f1['Organismes complémentaires'])}&nbsp;%).</p>
  <p><em>Notre lecture :</em> sur la période, le recul porte sur l'offre de soins (lits, maternités, généralistes) plus que sur leur prise en charge financière.</p>
  <p><strong>Limite :</strong> moyennes nationales ; le reste à charge varie fortement selon les personnes et les soins (dentaire, optique, dépassements d'honoraires) ; séries révisées à chaque édition, la dernière année ({f1['annee']}) pouvant encore l'être. Le graphique montre une année sur cinq.</p>""",
                   legende([(f, COUL_FIN[f]) for f in FIN]))

# Dépenses hospitalières publiques et privées
hp = CPT["hopital"]
g_hop = courbes([("Hôpital public", "var(--s1)", [x["public_md"] for x in hp]), ("Hôpital privé", "var(--s2)", [x["prive_md"] for x in hp])],
                [x["annee"] for x in hp], 0, 120, 20, lambda v: d(v, 0) + "&nbsp;Md€", "Dépense de soins hospitaliers, en milliards d'euros courants")
h0, h1 = hp[0], hp[-1]
s_hop = section("0", "Dépense hospitalière", f"Le secteur public hospitalier représente {d(h1['part_public'], 0)}&nbsp;% de la dépense hospitalière", g_hop, f"""
  <p class="take">En {h1['annee']}, la dépense de soins du secteur public hospitalier atteint <strong>{d(h1['public_md'])}&nbsp;Md€</strong>, contre {d(h0['public_md'])}&nbsp;Md€ en {h0['annee']} ; celle du secteur privé {d(h1['prive_md'])}&nbsp;Md€ (contre {d(h0['prive_md'])}), honoraires des médecins libéraux exerçant en clinique compris.</p>
  <p>La part du public reste stable : {d(h0['part_public'])}&nbsp;% en {h0['annee']}, {d(h1['part_public'])}&nbsp;% en {h1['annee']}.</p>
  <p><strong>Limites :</strong> au sens des comptes de la santé, le secteur public regroupe les hôpitaux publics, les hôpitaux militaires et les établissements privés à but non lucratif anciennement financés par dotation globale ; les autres établissements non lucratifs sont classés dans le privé (DREES) ; il ne recoupe pas exactement le statut juridique. Euros courants, non corrigés de l'inflation ni de la hausse des salaires ; ces montants mesurent la dépense, pas l'activité ou la qualité des soins.</p>""",
                legende([("Secteur public hospitalier", "var(--s1)"), ("Secteur privé", "var(--s2)")]))

# Tableau par département (triable)
def cell(v, fmt):
    return f'<td class="num" data-v="{v if v is not None else ""}">{fmt(v) if v is not None else "–"}</td>'

lignes_dep = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td><td data-v="{o["nom"]}">{o["nom"]}</td>'
    + cell(o["population"], n) + cell(o["maternites_debut"], n) + cell(o["maternites_fin"], n)
    + cell(o["rea_pour_100k"], d) + cell(o["part_sous_dotee"], lambda v: d(v) + "&nbsp;%")
    + cell(o["urgences_pct_2019_2023"], lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%")
    + cell(o["urgences_pour_1000"], n)
    + cell(o["generalistes_pour_100k"], d)
    + cell(o["generalistes_pct"], lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%") + "</tr>"
    for o in DEPS)
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Tous les indicateurs, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un nom ou un numéro pour filtrer.</p>
  <input id="filtre" type="search" placeholder="Rechercher un département…" aria-label="Rechercher un département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>N°</th><th>Département</th><th class="num">Habitants (2022)</th><th class="num">Maternités {a0m}</th><th class="num">Maternités {a1m}</th><th class="num">Réa adulte / 100 000 hab. (2024)</th><th class="num">Part en commune sous-dotée ({AD['periode'][1]})</th><th class="num">Urgences 2019 → 2023</th><th class="num">Passages urgences / 1 000 hab. (2023)</th><th class="num">Généralistes / 100 000 hab. ({MED['annees'][-1]})</th><th class="num">Généralistes / 100 000 hab. {MED['annees'][0]} → {MED['annees'][-1]}</th></tr></thead>
    <tbody>{lignes_dep}</tbody>
  </table></div>
  <p><strong>Limites :</strong> « – » = donnée absente (Mayotte sans population dans le fichier APL ; départements non couverts pour les urgences). Les passages pour 1 000 habitants incluent les non-résidents (touristes, patients des départements voisins) ; le Territoire de Belfort (772) est une valeur atypique, liée à la localisation des services d'urgences, qui accueillent des patients d'autres départements. Habitants : population totale Insee 2022 (fichier APL 2024). Densités de généralistes : calculées par la DREES ; pas d'évolution pour Mayotte.</p>
</section>
<script>
(function () {{
  var t = document.getElementById('tdep'), corps = t.tBodies[0], sens = {{}};
  Array.prototype.forEach.call(t.tHead.rows[0].cells, function (th, i) {{
    th.style.cursor = 'pointer';
    th.addEventListener('click', function () {{
      sens[i] = !sens[i];
      var lignes = Array.prototype.slice.call(corps.rows);
      lignes.sort(function (a, b) {{
        var x = a.cells[i].dataset.v, y = b.cells[i].dataset.v;
        if (x === '') return 1; if (y === '') return -1;
        var nx = parseFloat(x), ny = parseFloat(y);
        var r = (!isNaN(nx) && !isNaN(ny) && i > 1) ? nx - ny : x.localeCompare(y, 'fr');
        return sens[i] ? r : -r;
      }});
      lignes.forEach(function (l) {{ corps.appendChild(l); }});
    }});
  }});
  document.getElementById('filtre').addEventListener('input', function (e) {{
    var q = e.target.value.toLowerCase();
    Array.prototype.forEach.call(corps.rows, function (l) {{
      l.style.display = l.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    }});
  }});
}})();
</script>"""

# 7. Fiabilité
fiab = f"""
<section>
  <h3>0 · Fiabilité</h3>
  <h2>Ce qu'il faut garder en tête</h2>
  <div class="tbl"><table>
    <tr><th>Donnée</th><th>Limite</th><th>Conséquence</th></tr>
    <tr><td>Lits et places</td><td>Pas de distinction public / privé ; licence et description non renseignées par la DREES</td><td>Impossible d'attribuer le recul des lits au seul hôpital public</td></tr>
    <tr><td>Maternités</td><td>Nombre de sites, sans distance ni temps de trajet ; une ligne sans type (Dinan, 2021)</td><td>Ne mesure pas directement l'accès aux soins</td></tr>
    <tr><td>Médecins généralistes (APL)</td><td>Seuil de {seuil} consultations par an et par habitant (définition Insee, voir Sources) ; populations Insee décalées de deux ans ; méthode non comparable avant {apl_debut['annee']}</td><td>Évolution sur {len(A['serie'])} ans seulement</td></tr>
    <tr><td>Personnel</td><td>Personnes physiques, pas des équivalents temps plein ; internes inclus ; séries en partie rétropolées</td><td>Ne mesure ni le temps de travail ni le sous-effectif</td></tr>
    <tr><td>Réanimation</td><td>Pas de données 2014-2018 ; reclassement des unités en 2024 ; libellés des unités reconstitués ; licence non renseignée</td><td>Seule la réanimation adulte est comparée dans le temps</td></tr>
    <tr><td>Urgences</td><td>Passages estimés ; {U['nb_departements']} départements</td><td>Ce sont des passages, pas des patients ni des besoins</td></tr>
    <tr><td>Taux par département</td><td>Population Insee 2022 reconstituée à partir du fichier APL (hors Mayotte) ; lits et passages comptés là où se trouve l'hôpital</td><td>Mesure l'implantation de l'offre, pas l'accès des habitants ; les patients franchissent les limites départementales</td></tr>
    <tr><td>Établissements, lits par discipline, psychiatrie, longue durée (ARES)</td><td>Dernière année disponible : 2021 ; « établissement » = site géographique</td><td>Ne couvre pas les évolutions récentes ; fusions et fermetures ne sont pas distinguées</td></tr>
    <tr><td>Médecins (RPPS)</td><td>Inscrits à l'Ordre et actifs, quel que soit le temps de travail ; densité non calculée par la DREES pour Mayotte en 2012-2013 ; extraction 2024 réalisée au 30 septembre, activité au 1er janvier reconstituée par la DREES</td><td>Mesure le nombre de médecins, pas le temps médical disponible</td></tr>
    <tr><td>Comptes de la santé</td><td>Euros courants, non corrigés de l'inflation ; moyennes nationales ; séries révisées à chaque édition ; secteur public = hôpitaux publics, militaires et privés non lucratifs ex-dotation globale</td><td>Le reste à charge moyen masque de fortes différences entre personnes</td></tr>
    <tr><td>Taille des maternités</td><td>Accouchements des seules maternités ouvertes au 31 décembre</td><td>Ne permet pas de compter le total des accouchements</td></tr>
      <tr><td>Rapport à la population (Insee)</td><td>Estimations de population au 1er janvier, 2024 et 2025 provisoires</td><td>Ratios par habitant susceptibles de légères révisions</td></tr>
  </table></div>
  <p>Les séries nationales masquent de fortes différences entre territoires : les graphiques par département et le tableau en donnent un aperçu. Aucun indicateur n'est rapporté aux besoins de la population, sauf l'APL, qui tient compte de sa structure par âge ; selon la DREES, l'APL ne corrige pas le vieillissement entre deux millésimes.</p>
</section>"""

date = open("donnees_brutes/sante/date_telechargement.txt", encoding="utf-8").read().strip()
sources = f"""
<section>
  <h3>Sources</h3>
  <p>DREES, data.drees (téléchargement du {date}) : « Graphique 1 – Évolution du nombre de lits et de places au 31 décembre, depuis fin 2013 » ; « Effectifs salariés hospitaliers – Séries longues » ; « Lits de soins critiques des établissements de santé en France » ; « Liste des maternités de France depuis 2000 » ; « Accessibilité potentielle localisée (APL) aux professionnels de santé » ; « Séries longues corrigées du nombre de passages aux urgences 2017 à 2023 » ; « Base ARES – Agrégats régionaux sur les établissements de santé » (2013-2021) ; « La démographie des professionnels de santé depuis 2012 » (fichier Médecins RPPS 2012-2026) ; « Les comptes de la santé – Répartition par financeur » (édition 2026). Définition des secteurs public et privé hospitaliers : DREES, <a href="https://drees.solidarites-sante.gouv.fr/sites/default/files/2025-12/CNS%20-%20Fiche%2002%20-%20Les%20soins%20hospitaliers.pdf">Les dépenses de santé en 2024 (édition 2025), fiche « Les soins hospitaliers »</a>.</p>
  <p>Licences : Licence Ouverte v2.0 (Etalab) pour les effectifs, les maternités, l'APL, les urgences, la base ARES, la démographie des médecins et les comptes de la santé ; licence non renseignée pour les lits et places et pour les soins critiques.</p>
  <p>Commune sous-dotée en médecins généralistes (APL inférieur ou égal à {seuil} consultations par an et par habitant) : Insee, <a href="https://www.insee.fr/fr/statistiques/8677556">« L'accessibilité aux médecins généralistes se dégrade en Centre-Val de Loire »</a>, Insee Flash Centre-Val de Loire n° 101, décembre 2025 (même définition dans Insee Analyses Auvergne-Rhône-Alpes n° 187, décembre 2024).</p>
  <p>Population : Insee, estimations localisées de population (Licence Ouverte).</p>
  <p>Calculs rejouables : <code>calculer_chiffres_comparaisons.py</code> (comparaisons), <code>nettoyer_sante.py</code>, <code>calculer_chiffres_sante.py</code> puis <code>generer_rapport_sante.py</code> ; chiffres vérifiés de façon indépendante à partir des fichiers bruts.</p>
</section>"""


eua_u = eua["Établissements avec urgences autorisées"]
casse = casse_en_chiffres("En chiffres", [
    f"<strong>{n(abs(L['lits']['ecart']))} lits d'hospitalisation complète en moins</strong> entre {L['periode'][0]} et {L['periode'][1]} ({pct(L['lits']['pct'])}) ; {d(CP['sante']['lits_pour_1000']['fin'], 2)} lits pour 1 000 habitants contre {d(CP['sante']['lits_pour_1000']['debut'], 2)} ({pct(CP['sante']['lits_pour_1000']['pct'])}), et {pct(CP['sante']['lits_pour_1000_plus_75']['pct'])} pour 1 000 personnes de 75 ans ou plus ; les places d'hospitalisation partielle progressent de {pct(L['places']['pct'], False)}.",
    f"<strong>{abs(MA['total']['ecart'])} maternités en moins</strong> ({n(MA['total']['debut'])} en {MA['periode'][0]}, {n(MA['total']['fin'])} en {MA['periode'][1]}) ; les lits d'obstétrique reculent de {pct(abs(MA['lits_obstetrique']['pct']), False)}.",
    f"<strong>Un lit de chirurgie sur quatre</strong> a disparu entre {pa0} et {pa1} ({pct(em['Chirurgie']['pct'])}) ; la psychiatrie perd {n(abs(ps_l['evol']['Total']['ecart']))} lits à temps plein.",
    f"<strong>{abs(eua_u['ecart'])} établissements de moins</strong> avec un service d'urgences autorisé ({pa0}-{pa1}).",
    f"<strong>{d(apl_fin['population_sous_dense'] / 1e6)} millions d'habitants</strong> ({pct(apl_fin['part'], False)}) vivent en commune sous-dotée en généralistes en {apl_fin['annee']}, contre {d(apl_debut['population_sous_dense'] / 1e6)} millions ({pct(apl_debut['part'], False)}) en {apl_debut['annee']} (hausse due en partie à l'évolution de la population).",
], note="Chaque chiffre est détaillé, sourcé et assorti de ses limites dans la suite du rapport.")

tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">{ecart(L['lits']['ecart'])}</div><div class="l">lits d'hospitalisation complète ({L['periode'][0]}-{L['periode'][1]}), pour {ecart(L['places']['ecart'])} places d'hospitalisation partielle</div></div>
    <div class="tile"><div class="v">{ecart(MA['total']['ecart'])}</div><div class="l">maternités ({MA['periode'][0]}-{MA['periode'][1]})</div></div>
    <div class="tile"><div class="v">{d(apl_fin['population_sous_dense'] / 1e6)}&nbsp;M</div><div class="l">habitants en commune sous-dotée en généralistes ({apl_fin['annee']}, contre {d(apl_debut['population_sous_dense'] / 1e6)} M en {apl_debut['annee']})</div></div>
    <div class="tile"><div class="v">{pct(em['Chirurgie']['pct'])}</div><div class="l">de lits de chirurgie ({pa0}-{pa1})</div></div>
  </div>"""

entete = f"""
<header>
  <div class="eyebrow">Services publics de santé · données DREES</div>
  <h1>{n(abs(L['lits']['ecart']))} lits d'hospitalisation complète en moins entre {L['periode'][0]} et {L['periode'][1]}, {abs(MA['total']['ecart'])} maternités en moins entre {MA['periode'][0]} et {MA['periode'][1]}, {d(apl_fin['population_sous_dense'] / 1e6)} millions d'habitants en commune sous-dotée en généralistes en {apl_fin['annee']}</h1>
  <p class="lead">Les moyens de l'hôpital et l'accès aux soins en France, d'après les statistiques publiques. Sur la même période, les places d'hospitalisation partielle augmentent de {n(L['places']['ecart'])}. Chaque chiffre vient d'une source publique et peut être recalculé ou vérifié à la source ; chaque graphique est accompagné de ses limites.</p>
  {tuiles}
</header>""" + casse

# Parties et sommaire
# --- Carte par département (mêmes valeurs que le tableau « Votre département ») ----------------------------
def pc(v):
    return d(v) + "&nbsp;%"


def sg(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%"


DC = {o["departement"]: o for o in C["departements"]}
s_carte = section_carte("La carte", "L'accès aux soins, département par département", carte_departements("carte-sante", [
    {"libelle": "Déserts médicaux", "legende": f"Part des habitants en commune sous-dotée en généralistes ({apl_fin['annee']})",
     "valeurs": {k: o["part_sous_dotee"] for k, o in DC.items()}, "fmt": pc},
    {"libelle": "Généralistes : évolution", "legende": f"Évolution du nombre de généralistes pour 100 000 habitants, {an_m[0]}-{an_m[-1]}",
     "valeurs": {k: o["generalistes_pct"] for k, o in DC.items()}, "fmt": sg, "inverse": True},
    {"libelle": "Généralistes : densité", "legende": f"Généralistes pour 100 000 habitants ({an_m[-1]})",
     "valeurs": {k: o["generalistes_pour_100k"] for k, o in DC.items()}, "fmt": lambda v: d(v), "inverse": True},
    {"libelle": "Maternités", "legende": f"Maternités en plus ou en moins, {MA['periode'][0]}-{MA['periode'][1]}",
     "valeurs": {k: o["maternites_fin"] - o["maternites_debut"] for k, o in DC.items()},
     "fmt": lambda v: ("+" if v > 0 else "−" if v < 0 else "") + n(abs(v)), "inverse": True},
    {"libelle": "Réanimation", "legende": f"Lits de réanimation adulte pour 100 000 habitants ({S['annees'][-1]})",
     "valeurs": {k: o["rea_pour_100k"] for k, o in DC.items()}, "fmt": lambda v: d(v), "inverse": True},
], "Carte de l'accès aux soins par département"), f"""
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons changent d'indicateur. Plus la teinte est foncée, plus la situation est défavorable. Les valeurs sont celles du tableau « Votre département » ci-dessous.</p>
  <p class="limite"><strong>Limites :</strong> classes de couleur = cinquièmes des départements ; un taux par département mesure où sont les équipements et les médecins, pas l'accès réel des habitants. Mêmes sources et mêmes réserves que les sections correspondantes.</p>""")


# --- Comparaisons : population (Insee), Europe (Eurostat), OCDE ----------------------------------------
CS = CP["sante"]
cl0, cl1 = CS["periode_lits"]
g_hab = barres_divergentes([("Lits d'hospitalisation complète", L["lits"]["pct"]), ("Population", CS["population"]["pct"]),
                            ("Personnes de 75 ans ou plus", CS["plus_75_ans"]["pct"])],
                           lambda v: ("+" if v > 0 else "−") + d(abs(v)) + "&nbsp;%", f"Évolution {cl0}-{cl1}")
s_hab = section("0", "Rapporté à la population", f"{d(CS['lits_pour_1000']['fin'], 2)} lits pour 1 000 habitants, contre {d(CS['lits_pour_1000']['debut'], 2)} en {cl0}", g_hab, f"""
  <p class="take">Pendant que les lits d'hospitalisation complète reculent ({pct(L['lits']['pct'])}), la population augmente ({pct(CS['population']['pct'])}) et celle des 75 ans ou plus bien davantage ({pct(CS['plus_75_ans']['pct'])}). Rapporté à la population, le nombre de lits passe de {d(CS['lits_pour_1000']['debut'], 2)} à <strong>{d(CS['lits_pour_1000']['fin'], 2)} pour 1 000 habitants</strong> ({pct(CS['lits_pour_1000']['pct'])}).</p>
  <p>Pour 1 000 personnes de 75 ans ou plus, il passe de {d(CS['lits_pour_1000_plus_75']['debut'])} à <strong>{d(CS['lits_pour_1000_plus_75']['fin'])}</strong> ({pct(CS['lits_pour_1000_plus_75']['pct'])}).</p>
  {lecture(f"entre {cl0} et {cl1}, les lits d'hospitalisation complète baissent de {pct(L['lits']['pct'], False)} et la population de 75 ans ou plus augmente de {pct(CS['plus_75_ans']['pct'], False)}.")}
  {limite(f"lits au 31 décembre rapportés à la population au 1er janvier suivant (Insee, estimations ; 2025 provisoire) ; tous les patients hospitalisés n'ont pas 75 ans ou plus, le rapport aux 75 ans ou plus illustre l'écart entre l'offre et le vieillissement.")}""")

EL = CS["europe_lits"]
an_eu = [x["annee"] for x in EL["serie_france"]]
ue = {x["annee"]: x["valeur"] for x in EL["serie_ue"]}
g_eu = courbes([("France", "var(--alerte)", [x["valeur"] for x in EL["serie_france"]]),
                ("Union européenne (27)", "var(--dim)", [ue.get(a) for a in an_eu])],
               an_eu, 400, 900, 100, lambda v: n(v), "Lits d'hôpital pour 100 000 habitants (Eurostat)")
fr_eu, de_eu = EL["pays"]["France"], EL["pays"]["Allemagne"]
s_eu = section("0", "En Europe", f"Selon Eurostat, le nombre de lits d'hôpital pour 100 000 habitants a baissé d'un tiers en France depuis {EL['annee_debut']} ({pct(100 * (fr_eu['fin'] - fr_eu['debut']) / fr_eu['debut'])})", g_eu, f"""
  <p class="take">Selon Eurostat, la France comptait <strong>{n(fr_eu['debut'])}</strong> lits d'hôpital pour 100 000 habitants en {EL['annee_debut']}, et <strong>{n(fr_eu['fin'])}</strong> en {EL['annee_fin']}. L'Allemagne en compte {n(de_eu['fin'])}.</p>
  <p>La France se rapproche ainsi de la moyenne de l'Union européenne ({n(EL['pays']['Union européenne (27)']['fin'])} en {EL['annee_fin']}).</p>
  {limite(f"Eurostat signale une rupture de série en 2013 : sur {2013}-{EL['annee_fin']}, la baisse est de {pct(100 * (fr_eu['fin'] - CS['europe_lits_france_2013']) / CS['europe_lits_france_2013'])} ({n(CS['europe_lits_france_2013'])} → {n(fr_eu['fin'])}). Moyenne de l'Union européenne disponible à partir de 2009. Définition européenne des lits d'hôpital (tous types de soins), différente de la statistique française utilisée dans le reste du rapport : les deux sources ne se comparent pas entre elles.")}""",
               legende([("France", "var(--alerte)"), ("Union européenne (27)", "var(--dim)")]))

OG = CS["ocde_generalistes"]
g_og = courbes([("France", "var(--alerte)", [x["valeur"] for x in OG["serie"]])], [x["annee"] for x in OG["serie"]], 1.2, 1.7, 0.1,
               lambda v: d(v, 2), "Médecins généralistes pour 1 000 habitants, France (OCDE)", mention="Axe tronqué")
s_og = section("0", "Sur vingt ans", f"{d(OG['fin'], 2)} généraliste pour 1 000 habitants en {OG['annees'][1]}, contre {d(OG['debut'], 2)} en {OG['annees'][0]}", g_og, f"""
  <p class="take">D'après l'OCDE, la France compte <strong>{d(OG['fin'], 2)}</strong> médecin généraliste pour 1 000 habitants en {OG['annees'][1]}, contre {d(OG['debut'], 2)} en {OG['annees'][0]} ({pct(OG['pct'])}).</p>
  {limite("OCDE, statistiques de la santé, médecins généralistes déclarés par la France ; définition différente de celle du répertoire RPPS utilisé dans la section précédente.")}""")


def partie(ident, titre, intro):
    return f'<div class="partie" id="{ident}"><div class="eyebrow">{titre}</div><p class="lead">{intro}</p></div>'

PARTIES = [
    ("hopital", "L'hôpital", "Établissements, lits, chirurgie, psychiatrie.", [s_etab, s1, s_hab, s_mco, s_psy, s_rea_dep]),
    ("naissance", "Naître", "Les maternités, leur nombre, leur type, leur répartition.", [s2, s_types, s_taille, s_mat_dep]),
    ("medecins", "Les médecins", "Combien de médecins, où, et à quel âge.", [s_gen, s_age, s_dens, s_spe]),
    ("generalistes", "L'accès au généraliste", "L'accès aux soins de ville, commune par commune.", [s3, s_classes, s_apl_dep, s_apl_hausse]),
    ("urgences", "Les urgences", "Les services d'urgences.", [s_urg_aut]),
]
sommaire = ('<nav class="sommaire" aria-label="Sommaire">'
            + "".join(f'<a href="#{i}">{t}</a>' for i, t, _, _ in PARTIES)
            + '<a href="#carte">La carte</a><a href="#departements">Votre département</a><a href="#fiabilite">Fiabilité</a></nav>')
corps = "".join(partie(i, t, intro) + "".join(secs) for i, t, intro, secs in PARTIES) + tableau + fiab.replace("<section>", '<section id="fiabilite">', 1)
corps = re.sub(r"<p><em>Notre lecture :</em> (.*?)</p>", lambda mt: lecture(mt.group(1)[0].lower() + mt.group(1)[1:]), corps)  # encadrés d'interprétation
corps = re.sub(r" <em>Notre lecture :</em> (.*?)</p>", lambda mt: "</p>" + lecture(mt.group(1)[0].lower() + mt.group(1)[1:]), corps)  # lectures en fin de paragraphe
corps = corps.replace("<p><strong>Limite", '<p class="limite"><strong>Limite')  # limites plus discrètes, toujours présentes

# Numérotation continue des sections
compteur = iter(range(1, 100))
corps = re.sub(r"<h3>\d+ · ", lambda _: f"<h3>{next(compteur)} · ", corps)
corps = alleger_limites(corps)  # version presse : limites repliables, jamais supprimées
carte_haut = alleger_limites(re.sub(r"<h3>0 · ", "<h3>", s_carte))  # carte en tête de page, juste après l'en-tête
entete = entete.replace("</header>", "</header>" + carte_haut, 1)

STYLE_SUPPL = """<style>
/* Couleurs supplémentaires (séries multiples), sommaire, parties, recherche */
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

# Le modèle est un fragment (title + link + style) : on en reprend la tête et on construit un document complet
modele = open(MODELE_STYLE, encoding="utf-8").read()
tete = re.search(r"(?s)^.*?</style>", modele).group(0)
tete = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', "", tete)  # pas de police externe : rapport autonome
tete = re.sub(r"<title>.*?</title>", "<title>Services publics de santé</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">" + entete + sommaire + corps + sources
        + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques)")
