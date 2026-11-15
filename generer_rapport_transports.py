"""Génère rapport_transports.html à partir de donnees_propres/transports/chiffres_transports.json.

Aucun chiffre n'est saisi à la main : tout vient du JSON (EDR-005). Style repris de rapport_lots.html (EDR-011),
graphiques du module partagé graphiques_svg.py.
Usage : python3 generer_rapport_transports.py [--brouillon]
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

FICHE = "donnees_propres/transports/chiffres_transports.json"
MODELE_STYLE = "rapport_lots.html"
SORTIE = "rapports/rapport_transports.html"
BROUILLON = "--brouillon" in sys.argv

C = json.load(open(FICHE, encoding="utf-8"))
T, TF, GL, EF, GA, RE, GU, AU, UR = (C[k] for k in ("ter", "ter_finances", "grandes_lignes", "effectifs", "gares",
                                                    "reseau", "guichets", "autocars", "urbain"))

# --- 1. Offre et suppressions de TER --------------------------------------------------------
ann = [x["annee"] for x in T["serie"]]
p0, p1 = T["periode"]
g_ter = courbes([("Trains programmés", "var(--s1)", [100 * x["programmes"] / T["serie"][0]["programmes"] for x in T["serie"]]),
                 ("Trains supprimés", "var(--s2)", [100 * x["supprimes"] / T["serie"][0]["supprimes"] for x in T["serie"]])],
                ann, 70, 160, 10, lambda v: n(v), f"Trains TER programmés et supprimés, indice base 100 en {p0}",
                mention=f"Indice, base 100 en {p0} (axe tronqué)")
s_ter = section("0", "TER", f"Plus de TER programmés ({pct(T['programmes']['pct'])}), mais encore plus de trains supprimés ({pct(T['supprimes']['pct'])})", g_ter, f"""
  <p class="take">Entre {p0} et {p1}, le nombre de TER programmés passe de {n(T['programmes']['debut'])} à <strong>{n(T['programmes']['fin'])}</strong> ({pct(T['programmes']['pct'])}). Les trains supprimés passent de {n(T['supprimes']['debut'])} à <strong>{n(T['supprimes']['fin'])}</strong> ({pct(T['supprimes']['pct'])}).</p>
  <p>La part des trains supprimés passe de {d(T['serie'][0]['taux_suppression'], 2)}&nbsp;% à {d(T['serie'][-1]['taux_suppression'], 2)}&nbsp;% ; la régularité varie entre {d(min(x['regularite'] for x in T['serie']))} et {d(max(x['regularite'] for x in T['serie']))}&nbsp;% de trains à l'heure selon les années.</p>
  <p><strong>Limites :</strong> un train supprimé avant 16&nbsp;h la veille (grève annoncée, travaux) n'est compté ni comme programmé ni comme supprimé : les suppressions sont un minimum. Certaines années, trains circulés et supprimés dépassent ensemble les trains programmés (suppressions partielles probablement comptées deux fois). Les Intercités transférés aux régions sont comptés en TER après leur transfert : une partie de la hausse de l'offre vient de ces transferts. Retard = arrivée au terminus avec 5 minutes ou plus. 11 régions, hors Île-de-France et Corse.</p>""",
                legende([("Trains programmés", "var(--s1)"), ("Trains supprimés", "var(--s2)")]))

# --- 2. Suppressions par région --------------------------------------------------------------
rg = T["regions"]
g_reg = barres_h([(o["region"], o["taux_suppression_fin"]) for o in rg], lambda v: d(v, 2) + "&nbsp;%",
                 f"Part des TER supprimés en {p1}, par région", couleur="var(--s2)")
s_reg = section("0", "TER par région", f"En {p1}, de {d(rg[-1]['taux_suppression_fin'], 1)} à {d(rg[0]['taux_suppression_fin'], 1)}&nbsp;% de trains supprimés selon la région", g_reg, f"""
  <p class="take">En {p1}, la part de TER supprimés va de <strong>{d(rg[-1]['taux_suppression_fin'], 2)}&nbsp;%</strong> ({rg[-1]['region']}) à <strong>{d(rg[0]['taux_suppression_fin'], 2)}&nbsp;%</strong> ({rg[0]['region']}).</p>
  <p>La régularité la plus faible est en {min(rg, key=lambda o: o['regularite_fin'])['region']} ({d(min(o['regularite_fin'] for o in rg))}&nbsp;% de trains à l'heure).</p>
  <p><strong>Limite :</strong> mêmes règles de comptage que ci-dessus ; les lots de lignes publiés séparément en {p1} sont rattachés à leur région.</p>""")

# --- 3. Financement du TER ------------------------------------------------------------------
fs = TF["serie"]
a_f = [x["annee"] for x in fs]
g_fin = courbes([("Contributions publiques", "var(--s1)", [x["contributions_md"] for x in fs]),
                 ("Recettes des voyageurs", "var(--s2)", [x["recettes_md"] for x in fs])],
                a_f, 0, 4.5, 0.5, lambda v: d(v, 2 if v % 0.5 else 1) + "&nbsp;Md€", "Financement du TER, en milliards d'euros courants")
s_fin = section("0", "Qui paie le TER ?", f"Les contributions publiques représentent {d(fs[-1]['part_contributions'], 0)}&nbsp;% des charges d'exploitation du TER, contre {d(fs[0]['part_contributions'], 0)}&nbsp;% en {a_f[0]}", g_fin, f"""
  <p class="take">En {a_f[-1]}, les contributions publiques versées aux entreprises ferroviaires pour le TER atteignent <strong>{d(TF['contributions']['fin'], 2)}&nbsp;Md€</strong>, contre {d(TF['contributions']['debut'], 2)}&nbsp;Md€ en {a_f[0]} ({pct(TF['contributions']['pct'])}).</p>
  <p>La fréquentation progresse beaucoup plus vite : {d(TF['pkt']['debut'])} → {d(TF['pkt']['fin'])} milliards de voyageurs-kilomètres ({pct(TF['pkt']['pct'])}). Les recettes des billets passent de {d(TF['recettes']['debut'], 2)} à {d(TF['recettes']['fin'], 2)}&nbsp;Md€.</p>
  <p>La part des charges d'exploitation couverte par les contributions publiques baisse, de {d(fs[0]['part_contributions'])}&nbsp;% à {d(fs[-1]['part_contributions'])}&nbsp;%, tandis que celle couverte par les billets passe de {d(fs[0]['part_recettes'])}&nbsp;% à {d(fs[-1]['part_recettes'])}&nbsp;% (les deux parts, rapportées aux charges d'exploitation, ne s'additionnent pas exactement à 100&nbsp;%).</p>
  <p><strong>Limites :</strong> euros courants, non corrigés de l'inflation ; source ART ({a_f[-1]} dernière année complète).</p>""",
                legende([("Contributions publiques", "var(--s1)"), ("Recettes des voyageurs", "var(--s2)")]))

# --- 4. Intercités et TGV -------------------------------------------------------------------
ic = GL["intercites"]
g_ic = barres_groupees([(x["annee"], [x["programmes"], x["programmes_relations_constantes"]]) for x in ic], ["var(--dim)", "var(--s1)"],
                       100000, 20000, lambda v: n(v), "Trains Intercités programmés par an")
rc = GL["intercites_relations_constantes"]
s_ic = section("0", "Intercités", f"Intercités : sur les {rc['nombre']} liaisons suivies chaque année, {pct(rc['evol']['pct'])} de trains programmés depuis {ic[0]['annee']}", g_ic, f"""
  <p class="take">Sur les {rc['nombre']} liaisons (dans un sens donné) suivies chaque année depuis {ic[0]['annee']}, les trains programmés passent de {n(rc['evol']['debut'])} à <strong>{n(rc['evol']['fin'])}</strong> ({pct(rc['evol']['pct'])}).</p>
  <p>Sur l'ensemble des liaisons suivies, le total passe de {n(GL['intercites_evol']['debut'])} à {n(GL['intercites_evol']['fin'])} ({pct(GL['intercites_evol']['pct'])}) : une partie de cette baisse correspond au transfert de lignes Intercités aux régions, qui circulent depuis sous l'étiquette TER, et des liaisons ont aussi disparu du jeu de données. Elle ne mesure donc pas seulement des suppressions de trains.</p>
  <p><strong>Limite :</strong> la source ne couvre qu'une sélection de liaisons déterminée par l'Autorité de la qualité de service dans les transports (AQST).</p>""",
               legende([("Toutes les liaisons suivies", "var(--dim)"), (f"{rc['nombre']} liaisons suivies chaque année", "var(--s1)")]))

tg = GL["tgv_regularite"]
g_tgv = courbes([("Régularité", "var(--s1)", [x["regularite"] for x in tg])], [x["annee"] for x in tg], 80, 95, 5,
                lambda v: d(v) + "&nbsp;%", "Régularité des TGV, moyenne annuelle", mention="Axe tronqué : commence à 80 %")
s_tgv = section("0", "TGV", f"La régularité des TGV passe de {d(tg[0]['regularite'])} à {d(tg[-1]['regularite'])}&nbsp;%", g_tgv, f"""
  <p class="take">En {tg[-1]['annee']}, <strong>{d(tg[-1]['regularite'])}&nbsp;%</strong> des TGV sont à l'heure selon l'indicateur composite de la SNCF, contre {d(tg[0]['regularite'])}&nbsp;% en {tg[0]['annee']}.</p>
  <p><strong>Limite :</strong> moyenne simple (non pondérée) des taux mensuels de régularité composite publiés par la SNCF ; l'axe commence à 80&nbsp;%.</p>""")

# --- 5. Cheminots ---------------------------------------------------------------------------
es = EF["serie"]
g_eff = barres_groupees([(x["annee"], [x["statut"], x["contractuels"]]) for x in es], ["var(--s1)", "var(--s2)"], 140000, 20000,
                        lambda v: n(v), "Effectifs SNCF selon le type de contrat")
ep0, ep1 = EF["periode"]
s_eff = section("0", "Cheminots", f"Entre {ep0} et {ep1}, agents au statut {pct(EF['statut']['pct'])}, contractuels {pct(EF['contractuels']['pct'])}", g_eff, f"""
  <p class="take">Entre {ep0} et {ep1}, les agents au statut de cheminot passent de {n(EF['statut']['debut'])} à <strong>{n(EF['statut']['fin'])}</strong> ({pct(EF['statut']['pct'])}), et les contractuels de {n(EF['contractuels']['debut'])} à <strong>{n(EF['contractuels']['fin'])}</strong> ({pct(EF['contractuels']['pct'])}).</p>
  <p>Les contractuels représentent {d(es[-1]['part_contractuels'])}&nbsp;% des effectifs de la SNCF en {ep1}, contre {d(es[0]['part_contractuels'])}&nbsp;% en {ep0}.</p>
  <p><strong>Limites :</strong> effectifs de la SNCF (bilan social, hors contrats aidés), pas de l'ensemble du secteur ferroviaire. Comparaison limitée à {ep0}-{ep1} : de {EF['annees_avec_anomalies'][0]} à {EF['annees_avec_anomalies'][-1]}, la source présente des tranches d'âge manquantes ou en double.</p>""",
                legende([("Agents au statut", "var(--s1)"), ("Contractuels", "var(--s2)")]))

# --- 6. Gares et guichets --------------------------------------------------------------------
ty = {k: v for k, v in GU["par_type"].items() if k != "non renseigné"}
ordre = sorted(ty, key=lambda k: -ty[k]["part"])
g_gui = barres_h([(f"{k} ({ty[k]['gares']} gares)", ty[k]["part"]) for k in ordre], lambda v: d(v) + "&nbsp;%",
                 "Part des gares disposant d'un guichet, par type de gare", vmax=100)
s_gui = section("0", "Guichets", f"{d(GU['part_sans_guichet'], 0)}&nbsp;% des gares hors Île-de-France n'ont pas de guichet", g_gui, f"""
  <p class="take">Sur {n(GU['gares_hors_idf'])} gares voyageurs hors Île-de-France, seules <strong>{n(GU['avec_guichet'])}</strong> ({d(GU['part_avec_guichet'])}&nbsp;%) disposent d'un guichet. {n(GU['automates_seuls'])} n'ont que des automates et <strong>{n(GU['aucun_point_vente'])}</strong> n'ont aucun point de vente répertorié.</p>
  <p>Les haltes, les plus petites gares, n'ont presque jamais de guichet ({d(ty['Halte']['part'])}&nbsp;%).</p>
  <p>{n(GU['par_type']['non renseigné']['gares'])} gares de type non renseigné ({n(GU['par_type']['non renseigné']['avec_guichet'])} avec guichet) ne sont pas représentées dans le graphique.</p>
  <p><strong>Limites :</strong> photographie à une date (jeu mis en ligne en janvier 2026, données traitées en février 2024) ; gares hors Île-de-France par type et code postal ; rapprochement par code de gare, quelques points de vente peuvent manquer. Les données ne disent ni combien de guichets ont fermé, ni leurs horaires d'ouverture.</p>""")

an_g = GA["annees"]
seg = GA["voyageurs_par_segment"]
g_gar = courbes([("Gares nationales (A)", "var(--s1)", [100 * v / seg["A"][0] for v in seg["A"]]),
                 ("Gares régionales (B)", "var(--s3)", [100 * v / seg["B"][0] for v in seg["B"]]),
                 ("Gares locales (C)", "var(--s2)", [100 * v / seg["C"][0] for v in seg["C"]])],
                an_g, 40, 160, 20, lambda v: n(v), "Voyageurs par type de gare, indice base 100 en 2015", mention="Indice, base 100 en 2015 (axe tronqué)")
ev = GA["evol_2019_2024"]
s_gar = section("0", "Gares", f"Les petites gares gagnent des voyageurs : {pct(ev['C']['pct'])} entre 2019 et {an_g[-1]}", g_gar, f"""
  <p class="take">Entre 2019 et {an_g[-1]}, la fréquentation des gares locales augmente de <strong>{pct(ev['C']['pct'], False)}</strong>, celle des grandes gares nationales de {pct(ev['A']['pct'], False)}.</p>
  <p>Les gares locales sont {d(GA['part_c_gares'])}&nbsp;% des gares mais ne pèsent que {d(GA['part_c_voyageurs_2024'])}&nbsp;% des voyageurs ; {n(GA['gares_c_moins_de_100_par_jour'])} d'entre elles accueillent moins de 100 voyageurs par jour en moyenne (moins de 36&nbsp;500 en {an_g[-1]}).</p>
  <p>Hors Île-de-France, les gares régionales progressent de {pct(GA['evol_b_hors_idf_2019_2024']['pct'], False)} sur la même période (l'Île-de-France représente {d(GA['part_idf_voyageurs_b_2024'])}&nbsp;% de leurs voyageurs en {an_g[-1]}).</p>
  <p><strong>Limites :</strong> voyageurs comptés par la SNCF (billetterie hors ventes par des tiers ; trafic francilien extrapolé à partir de comptages) ; la SNCF révise chaque année sa méthode et reprend l'historique ; 2020 et 2021 sont marquées par la crise sanitaire.</p>""",
                legende([("Nationales (A)", "var(--s1)"), ("Régionales (B)", "var(--s3)"), ("Locales (C)", "var(--s2)")]))

# --- 7. Réseau ------------------------------------------------------------------------------
km = RE["km"]
g_res = barres_h([(k, v) for k, v in km.items()], lambda v: n(v) + "&nbsp;km", "Longueur du réseau ferré national selon le statut des lignes",
                 couleur=lambda i, v: "var(--s1)" if i == 0 else "var(--s2)")
s_res = section("0", "Réseau", f"{n(RE['km_non_exploites'])} km de lignes recensées ne sont pas exploités", g_res, f"""
  <p class="take">Sur {n(RE['total_km'])} km de lignes recensées par SNCF Réseau, <strong>{n(km['Exploitées'])} km</strong> sont exploités ; {d(RE['part_non_exploitee'])}&nbsp;% du linéaire est neutralisé, fermé, retranché, déclassé ou transféré en voie de service.</p>
  <p><strong>Limites :</strong> photographie à une date (traitement du 26 février 2026) : les données ne disent pas quand ces lignes ont été fermées. Une ligne « neutralisée » n'est pas fermée. Longueurs approximatives, calculées à partir des points kilométriques ; elles ne se comparent pas à celles de l'ART (section « Lignes ») : autre source, autre périmètre, autre méthode.</p>""")

# --- 8. Cars et transports urbains -----------------------------------------------------------
au = AU["serie"]
g_au = barres_groupees([(x["annee"], [x["passagers_m"]]) for x in au], ["var(--s3)"], 20, 5, lambda v: d(v),
                       "Passagers des autocars librement organisés, en millions")
s_au = section("0", "Cars longue distance", f"Les cars longue distance transportent {d(au[-1]['passagers_m'])} millions de passagers", g_au, f"""
  <p class="take">Les autocars librement organisés (« cars Macron »), autorisés depuis 2015, transportent <strong>{d(au[-1]['passagers_m'])} millions</strong> de passagers en {au[-1]['annee']} (liaisons domestiques et internationales), contre {d(AU['passagers']['debut'])} millions en 2016.</p>
  <p>Ils desservent {au[-1]['villes']} unités urbaines par {n(au[-1]['liaisons'])} liaisons commercialisées ({au[-1]['annee']}).</p>
  <p><strong>Limites :</strong> services commerciaux, sans convention avec une autorité publique : ce ne sont pas des services publics. Ouverture en août 2015, d'où la comparaison à partir de 2016.</p>""")

g_ur = courbes([("Voyages", "var(--s1)", [100 * v / UR["voyages_m"][0] for v in UR["voyages_m"]]),
                ("Kilomètres offerts", "var(--s2)", [100 * v / UR["km_m"][0] for v in UR["km_m"]])],
               UR["annees"], 90, 130, 10, lambda v: n(v), "Transports urbains : voyages et offre, indice base 100 en 2005",
               mention="Indice, base 100 en 2005 (axe tronqué)")
s_ur = section("0", "Transports urbains", f"Bus, tram et métro : voyages {pct(UR['voyages']['pct'])} entre 2005 et 2016", g_ur, f"""
  <p class="take">Sur {UR['nb_reseaux']} réseaux urbains suivis chaque année, les voyages passent de {d(UR['voyages']['debut'] / 1000, 2)} à <strong>{d(UR['voyages']['fin'] / 1000, 2)} milliards</strong> entre 2005 et 2016 ({pct(UR['voyages']['pct'])}), et les kilomètres offerts de {n(UR['km']['debut'])} à {n(UR['km']['fin'])} millions ({pct(UR['km']['pct'])}).</p>
  <p><strong>Limites :</strong> hors Île-de-France ; déclarations des exploitants des réseaux ; données publiées jusqu'en 2016, elles ne disent rien de l'évolution récente.</p>""",
               legende([("Voyages", "var(--s1)"), ("Kilomètres offerts", "var(--s2)")]))


# --- Recentrage : lignes perdues, offre et fréquentation ----------------------------------------
RV, FO = C["reseau_evolution"], C["frequentation_offre"]
rv0, rv1 = RV["periode"]
g_rfn = courbes([("Réseau classique (SNCF Réseau, hors LGV)", "var(--alerte)", [x["classique_km"] / 1000 for x in RV["serie"]])],
                [x["annee"] for x in RV["serie"]], 23, 28, 1, lambda v: d(v, 1),
                "Longueur du réseau ferré classique, en milliers de km de lignes", mention=f"Milliers de km de lignes (axe tronqué) ; {d(RV['serie'][0]['classique_km'] / 1000, 1)} en {rv0}")
sv = RV["petites_lignes_sans_voyageurs"]
s_rfn = section("0", "Lignes", f"Le réseau ferré classique géré par SNCF Réseau compte {n(-RV['classique']['ecart'])} km de lignes de moins qu'en {rv0}", g_rfn, f"""
  <p class="take">Entre {rv0} et {rv1}, le réseau ferré classique géré par SNCF Réseau passe de {n(RV['classique']['debut'])} à <strong>{n(RV['classique']['fin'])} km de lignes</strong> : {n(-RV['classique']['ecart'])} km en moins ({pct(RV['classique']['pct'])}).</p>
  <p>Avec les lignes à grande vitesse, dont trois gérées par d'autres gestionnaires que SNCF Réseau (LISEA, OC'VIA, ERE), présentes dans les données à partir de 2017, le réseau ferré national total recule de {n(-RV['total']['ecart'])} km ({pct(RV['total']['pct'])}), de {n(RV['total']['debut'])} à {n(RV['total']['fin'])} km.</p>
  <p>Plus de la moitié de cette baisse ({d(RV['part_sans_voyageurs_dans_baisse_classique'], 0)}&nbsp;%, soit {n(-sv['ecart'])} km) concerne des petites lignes sans trafic voyageurs (catégories 7 à 9), passées de {n(sv['debut'])} à {n(sv['fin'])} km : des lignes sans trains de voyageurs (fret ou aucune circulation).</p>
  {lecture("le réseau classique se resserre année après année ; une ligne qui en sort sans être reprise par une région, même sans voyageurs aujourd'hui, est une ligne sur laquelle il deviendra plus difficile de faire rouler un train demain.")}
  {limite("ART, onglet « 1.1 - RFN », km de lignes au 31 décembre, par gestionnaire de la maintenance. La source ne dit pas quelles lignes sont sorties de ce périmètre ni pourquoi : fermeture, déclassement ou transfert de gestion à une région (possible depuis la loi d'orientation des mobilités de 2019) ; « sortie du réseau » n'est donc pas synonyme de « fermée ». Couverture incomplète en 2018 selon l'ART. Ces longueurs ne se comparent pas à celles de la section « Réseau » ci-dessous (autre source, autre méthode).")}""")

g_rreg = barres_h([(o["region"], -o["ecart"]) for o in RV["par_region"]], lambda v: n(v) + "&nbsp;km",
                  f"Km de lignes classiques en moins par région, {rv0}-{rv1}", couleur="var(--alerte)")
rg = RV["par_region"]
s_rreg = section("0", "Lignes par région", f"{rg[0]['region']} et {rg[1]['region']} : plus de {n(min(-rg[0]['ecart'], -rg[1]['ecart']) // 100 * 100)} km de lignes classiques en moins chacune dans le réseau géré par SNCF Réseau", g_rreg, f"""
  <p class="take">Le réseau classique géré par SNCF Réseau recule dans toutes les régions. Les pertes les plus fortes : <strong>{rg[0]['region']}</strong> ({n(-rg[0]['ecart'])} km, {pct(rg[0]['pct'])}), <strong>{rg[1]['region']}</strong> ({n(-rg[1]['ecart'])} km, {pct(rg[1]['pct'])}), {rg[2]['region']} ({n(-rg[2]['ecart'])} km, {pct(rg[2]['pct'])}).</p>
  {limite("découpage régional actuel ; mêmes réserves que ci-dessus (une ligne dont la gestion est transférée à sa région sort de ce périmètre sans forcément fermer ; la source ne permet pas de savoir si de tels transferts expliquent une partie de ces baisses). La source ne descend pas au département.")}""")

fs_ = FO["serie"]
fo0, fo1 = FO["periode"]
g_freq = courbes([("Passagers-km", "var(--alerte)", [x["indice_pkt"] for x in fs_]),
                  ("Sièges-km offerts", "var(--s3)", [x["indice_sieges_km"] for x in fs_]),
                  ("Trains-km", "var(--s1)", [x["indice_trains_km"] for x in fs_])],
                 [x["annee"] for x in fs_], 70, 180, 10, lambda v: n(v), f"TER : fréquentation et offre, indice base 100 en {fo0}",
                 mention=f"Indice, base 100 en {fo0} (axe tronqué)")
s_freq = section("0", "Fréquentation et offre", f"La fréquentation des TER augmente de {d(FO['pkt'], 0)}&nbsp;%, les places offertes de {d(FO['sieges_km'], 0)}&nbsp;%", g_freq, f"""
  <p class="take">Entre {fo0} et {fo1}, la fréquentation des TER (passagers-km) augmente de <strong>{d(FO['pkt'], 0)}&nbsp;%</strong> : quatre fois plus que les trains-km ({pct(FO['trains_km'])}) et deux fois plus que les places offertes (sièges-km, {pct(FO['sieges_km'])}).</p>
  <p>Résultat : les trains sont plus remplis. Le taux d'occupation moyen passe de {d(FO['taux_occupation']['debut'])}&nbsp;% à <strong>{d(FO['taux_occupation']['fin'])}&nbsp;%</strong> (moyenne sur toute la journée et tout le réseau).</p>
  {lecture("les usagers sont de plus en plus nombreux dans le train régional, mais l'offre ne suit pas au même rythme : plus de monde dans des trains qui n'augmentent pas autant.")}
  {limite(f"ART, onglet « 9.1 », total TER hors Transilien ; {fo1} = dernière année complète. Taux d'occupation moyen sur la journée et le réseau : il ne mesure pas la saturation aux heures de pointe. Intercités transférés aux régions entre 2017 et 2020 comptés en TER (gonfle à la fois l'offre et la fréquentation) ; 2020-2021 marquées par la crise sanitaire.")}""",
                legende([("Passagers-km", "var(--alerte)"), ("Sièges-km offerts", "var(--s3)"), ("Trains-km", "var(--s1)")]))

# --- Fiabilité, sources, assemblage -----------------------------------------------------------
# --- Ajouts : suppressions de dernière minute, dessertes, gares par département -------------------
FI, DS, GD = C["fiabilite"]["par_service"], C["dessertes"], C["gares_departements"]
COUL_SV = {"TER": "var(--alerte)", "Transilien": "var(--s4)", "Intercités": "var(--s1)"}
an_fi = [x["annee"] for x in FI["TER"]["serie"]]
series_fi = []
for sv in ("TER", "Transilien", "Intercités"):
    vals = {x["annee"]: x["part_annules_derniere_minute"] for x in FI[sv]["serie"]}
    series_fi.append((sv, COUL_SV[sv], [vals.get(a) for a in an_fi]))  # Transilien : pas de donnée la première année
g_annul = courbes(series_fi, an_fi, 0, 6, 1, lambda v: d(v) + "&nbsp;%", "Part des trains annulés au dernier moment (trains programmés)",
                  mention=f"Transilien à partir de {FI['Transilien']['periode'][0]} ; TER {an_fi[1]} : valeur atypique (basse)")
ter_f, tr_f, ic_f = FI["TER"], FI["Transilien"], FI["Intercités"]
s_annul = section("0", "Suppressions de dernière minute", f"TER supprimés au dernier moment : {pct(ter_f['annules_derniere_minute']['pct'])} en {int(ter_f['periode'][1]) - int(ter_f['periode'][0])} ans", g_annul, f"""
  <p class="take">En {ter_f['periode'][1]}, <strong>{d(ter_f['annules_derniere_minute']['fin'])}</strong> TER en moyenne sont supprimés chaque jour au dernier moment ({d(ter_f['serie'][-1]['annules_totaux_jour'])} totalement, {d(ter_f['annules_derniere_minute']['fin'] - ter_f['serie'][-1]['annules_totaux_jour'])} sur une partie du trajet), après la publication du plan de transport de la veille, contre {d(ter_f['annules_derniere_minute']['debut'])} en {ter_f['periode'][0]} ({pct(ter_f['annules_derniere_minute']['pct'])}).</p>
  <p>Rapportée aux trains programmés, la part des TER annulés au dernier moment passe de {d(ter_f['taux_annules_derniere_minute']['debut'], 2)}&nbsp;% ({ter_f['periode'][0]}) à <strong>{d(ter_f['taux_annules_derniere_minute']['fin'], 2)}&nbsp;%</strong> ({ter_f['periode'][1]}). En Île-de-France, celle des Transilien passe de {d(tr_f['taux_annules_derniere_minute']['debut'], 2)}&nbsp;% ({tr_f['periode'][0]}) à {d(tr_f['taux_annules_derniere_minute']['fin'], 2)}&nbsp;% ; celle des Intercités de {d(ic_f['taux_annules_derniere_minute']['debut'], 2)}&nbsp;% ({ic_f['periode'][0]}) à {d(ic_f['taux_annules_derniere_minute']['fin'], 2)}&nbsp;%.</p>
  <p>Les trains retirés avant 16&nbsp;h la veille (déprogrammations) n'apparaissent pas dans la statistique de régularité de la SNCF ; l'ART, elle, les compte à part. Les suppressions de dernière minute, décidées après cette heure, sont comptées par les deux. Aucune des deux sources ne publie de répartition chiffrée des causes de ces suppressions (manque de personnel, de matériel, travaux, grève…) ; la SNCF ne donne que des commentaires mensuels ponctuels.</p>
  {lecture("ce sont les suppressions les plus pénibles pour les usagers : le train était annoncé la veille et ne vient pas, ou ne va pas jusqu'au bout. Leur part augmente pour les trois types de trains.")}
  {limite(f"moyennes de trains par jour (ART). Les trains retirés plus tôt du plan de transport (déprogrammations, y compris pour travaux) baissent : la part totale de TER non circulés est de {d(ter_f['serie'][-1]['part_non_circules'], 2)}&nbsp;% en {ter_f['periode'][1]}, contre {d(ter_f['serie'][0]['part_non_circules'], 2)}&nbsp;% en {ter_f['periode'][0]}. Années atypiques : 2017 (valeur TER basse), 2018, 2019 et 2023 (grèves), 2020 et 2021 (crise sanitaire).")}""",
                    legende([(sv, col) for sv, col, _ in series_fi]))

ds0, ds1 = DS["annees"][0], DS["annees"][-1]
g_des = barres_h([("Moins de dessertes", DS["gares_en_baisse"]), ("dont plus de 10 % en moins", DS["gares_en_baisse_plus_10pct"]),
                  ("dont plus de 20 % en moins", DS["gares_en_baisse_plus_20pct"]), ("Plus de dessertes", DS["gares_en_hausse"])],
                 n, f"Gares selon l'évolution de leurs dessertes, {ds0}-{ds1}",
                 couleur=lambda i, v: "var(--s1)" if i == 3 else "var(--alerte)")
s_des = section("0", "Dessertes des gares", f"Près d'une gare sur deux ({d(DS['part_gares_en_baisse'], 0)}&nbsp;%) a perdu des arrêts de trains entre {ds0} et {ds1}", g_des, f"""
  <p class="take">Sur {n(DS['gares_suivies'])} gares, <strong>{n(DS['gares_en_baisse'])}</strong> sont moins desservies en {ds1} qu'en {ds0} ; {n(DS['gares_en_baisse_plus_10pct'])} ont perdu plus de 10&nbsp;% de leurs arrêts, {n(DS['gares_en_baisse_plus_20pct'])} plus de 20&nbsp;%.</p>
  <p>Dans le même temps, le nombre total d'arrêts augmente ({pct(DS['dessertes_total_evol']['pct'])}) et {n(DS['gares_en_hausse'])} gares sont mieux desservies.</p>
  {lecture("l'offre se concentre : des trains en plus sur certaines lignes et dans certaines gares, des arrêts en moins dans près d'une gare sur deux.")}
  {limite(f"nombre de dessertes publié par l'ART, gares présentes en {ds0} et en {ds1} ({DS['gares_absentes_fin']} gares de {ds0} absentes en {ds1}, hors calcul) ; 2020 et 2021 marquées par la crise sanitaire.")}""")

cl = GD["classement_sans_guichet"]
k_g = 15
g_gdep = barres_h([(f"{o['departement']} ({o['gares']} gares)", o["part_sans_guichet"]) for o in cl[:k_g]], lambda v: d(v) + "&nbsp;%",
                  "Part des gares sans guichet, départements hors Île-de-France (au moins 10 gares)", couleur="var(--alerte)", vmax=100)
s_gdep = section("0", "Guichets par département", f"Dans {GD['deps_majorite_sans_guichet']} départements sur {GD['nb_deps_classes']}, la majorité des gares n'a pas de guichet", g_gdep, f"""
  <p class="take">Hors Île-de-France, la majorité des gares n'a pas de guichet dans <strong>{GD['deps_majorite_sans_guichet']} départements sur {GD['nb_deps_classes']}</strong> (départements d'au moins 10 gares).</p>
  <p>En tête : département {cl[0]['departement']} ({cl[0]['gares'] - cl[0]['avec_guichet']} gares sur {cl[0]['gares']} sans guichet), {cl[1]['departement']} ({cl[1]['gares'] - cl[1]['avec_guichet']} sur {cl[1]['gares']}), {cl[2]['departement']} ({cl[2]['gares'] - cl[2]['avec_guichet']} sur {cl[2]['gares']}).</p>
  {lecture(f"dans la plupart des départements, la majorité des gares n'a pas de guichet : on y achète son billet à un automate, sur un écran, ou nulle part (hors Île-de-France, {n(GU['aucun_point_vente'])} gares n'ont aucun point de vente répertorié).")}
  {limite("photographie (points de vente traités en février 2024) : les données ne disent pas combien de guichets ont fermé ; « sans guichet » ne veut pas dire « sans automate » ; départements désignés par leur numéro.")}""")


def cellule(v, fmt):
    return f'<td class="num" data-v="{v if v is not None else ""}">{fmt(v) if v is not None else "–"}</td>'


lignes_dep = "".join(
    f'<tr><td data-v="{o["departement"]}">{o["departement"]}</td>' + cellule(o["gares"], n) + cellule(o["avec_guichet"], n)
    + cellule(o["part_sans_guichet"], lambda v: d(v) + "&nbsp;%") + cellule(o["voyageurs_2019"], n) + cellule(o["voyageurs_2024"], n)
    + cellule(o["pct_voyageurs"], lambda v: ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%") + "</tr>"
    for o in GD["departements"])
tableau = f"""
<section id="departements">
  <h3>0 · Votre département</h3>
  <h2>Gares, guichets et voyageurs, département par département</h2>
  <p>Cliquez sur un en-tête pour trier ; tapez un numéro de département pour filtrer.</p>
  <input id="filtre" type="search" placeholder="Numéro de département…" aria-label="Filtrer par département">
  <div class="tbl"><table id="tdep">
    <thead><tr><th>Département</th><th class="num">Gares</th><th class="num">Avec guichet</th><th class="num">Part sans guichet</th><th class="num">Voyageurs 2019</th><th class="num">Voyageurs 2024</th><th class="num">Évolution</th></tr></thead>
    <tbody>{lignes_dep}</tbody>
  </table></div>
  {limite("gares SNCF par département de leur code postal ; guichets : photographie de février 2024 (hors Transilien en Île-de-France) ; voyageurs comptés par la SNCF (billetterie, trafic francilien extrapolé).")}
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
        var r = (!isNaN(nx) && !isNaN(ny) && i > 0) ? nx - ny : x.localeCompare(y, 'fr');
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

casse = casse_en_chiffres("La casse en chiffres", [
    f"<strong>{n(-RV['classique']['ecart'])} km de lignes classiques</strong> en moins dans le réseau géré par SNCF Réseau entre {rv0} et {rv1} ({pct(RV['classique']['pct'])}), dans toutes les régions ; plus de la moitié sans trafic voyageurs.",
    f"Fréquentation des TER <strong>{pct(FO['pkt'])}</strong>, places offertes {pct(FO['sieges_km'])}, trains-km {pct(FO['trains_km'])} ({fo0}-{fo1}) : l'offre ne suit pas au même rythme.",
    f"<strong>Près d'une gare sur deux</strong> ({d(DS['part_gares_en_baisse'], 0)}&nbsp;%) a perdu des arrêts de trains entre {ds0} et {ds1}, alors que le nombre total d'arrêts progresse de {d(DS['dessertes_total_evol']['pct'])}&nbsp;% : l'offre se concentre.",
    f"À la SNCF, les contractuels augmentent de <strong>{d(EF['contractuels']['pct'])}&nbsp;%</strong> en deux ans, pendant que les agents au statut baissent de {pct(EF['statut']['pct'], False)} ({EF['periode'][0]}-{EF['periode'][1]}).",
    f"Dans <strong>{GD['deps_majorite_sans_guichet']} départements sur {GD['nb_deps_classes']}</strong> (hors Île-de-France), la majorité des gares n'a pas de guichet (photographie de février 2024).",
], note="« Casse » : lecture militante de ces évolutions. Chaque chiffre est détaillé, sourcé et assorti de ses limites dans la suite du rapport ; les sorties du réseau ne sont pas toutes des fermetures (transferts de gestion aux régions).")

fiab = f"""
<section id="fiabilite">
  <h3>0 · Fiabilité</h3>
  <h2>Ce qu'il faut garder en tête</h2>
  <div class="tbl"><table>
    <tr><th>Donnée</th><th>Limite</th><th>Conséquence</th></tr>
    <tr><td>TER (SNCF)</td><td>Suppressions annoncées la veille avant 16 h non comptées ; périmètre complet seulement à partir de 2017</td><td>Suppressions sous-estimées, surtout les jours de grève</td></tr>
    <tr><td>Financement TER (ART)</td><td>Euros courants ; dernière année complète {a_f[-1]}</td><td>Hausses à relativiser par l'inflation</td></tr>
    <tr><td>Intercités</td><td>Sélection de liaisons de l'AQST ; transferts de lignes aux régions</td><td>La baisse du total ne mesure pas seulement des suppressions</td></tr>
    <tr><td>Effectifs SNCF</td><td>Tranches d'âge manquantes ou en double de {EF['annees_avec_anomalies'][0]} à {EF['annees_avec_anomalies'][-1]} ; effectifs totaux à partir de 2019</td><td>Seule {EF['periode'][0]}-{EF['periode'][1]} est comparée</td></tr>
    <tr><td>Gares</td><td>Trafic francilien extrapolé ; méthode révisée chaque année</td><td>Évolutions à lire avec prudence</td></tr>
    <tr><td>Guichets, réseau</td><td>Photographies à une date ; rapprochement par code de gare</td><td>Pas d'évolution dans le temps</td></tr>
    <tr><td>Suppressions de dernière minute (ART)</td><td>Moyennes par jour ; années de grève et de crise sanitaire atypiques</td><td>Les déprogrammations anticipées, elles, baissent</td></tr>
    <tr><td>Réseau ferré national (ART)</td><td>Km de lignes au 31 décembre par gestionnaire de la maintenance ; ne distingue pas fermeture, déclassement et transfert aux régions ; couverture incomplète en 2018 ; non comparable aux « lignes par statut » de SNCF Réseau</td><td>« Sorti du réseau » n'est pas synonyme de « fermé »</td></tr>
    <tr><td>Fréquentation TER (ART)</td><td>Nombre de voyages non retenu (estimé par la source jusqu'en 2020) ; Intercités transférés comptés en TER ; taux d'occupation moyen sur la journée</td><td>Ne mesure pas la saturation aux heures de pointe</td></tr>
    <tr><td>Dessertes des gares (ART)</td><td>2019-2023 ; gares disparues du jeu hors calcul</td><td>Concentration de l'offre, total des arrêts en hausse</td></tr>
    <tr><td>Autocars librement organisés</td><td>Services commerciaux ; liaisons domestiques et internationales ; ouverture en août 2015</td><td>Pas un service public ; comparaison à partir de 2016</td></tr>
    <tr><td>Transports urbains</td><td>Hors Île-de-France ; déclarations des exploitants ; données jusqu'en 2016</td><td>Pas de données récentes</td></tr>
  </table></div>
</section>"""
date = open("donnees_brutes/transports/sncf/date_telechargement.txt", encoding="utf-8").read().strip()
sources = f"""
<section>
  <h3>Sources</h3>
  <p>SNCF Open Data (téléchargement du {date}, licence ODbL) : régularité mensuelle TER, Intercités et TGV ; répartition par âge de l'effectif ; fréquentation en gares ; lignes par statut (SNCF Réseau) ; points de vente.</p>
  <p>Autorité de régulation des transports (Licence Ouverte) : données du transport ferroviaire (onglets RFN, TER, Fiabilité et Gares) ; données des services librement organisés d'autocars. Cerema : enquête nationale sur les transports collectifs urbains, 1995-2016 (Licence Ouverte), réalisée par le Gart et l'UTP depuis 2016. Données ART et Cerema téléchargées le {date}.</p>
  <p>Calculs rejouables : <code>nettoyer_transports.py</code>, <code>calculer_chiffres_transports.py</code> puis <code>generer_rapport_transports.py</code>.</p>
</section>"""

bandeau = ('<div class="take" style="border-color:var(--warn)"><strong>Brouillon en cours de vérification</strong> : '
           'chiffres non encore validés de façon indépendante, ne pas diffuser.</div>') if BROUILLON else ""
tuiles = f"""
  <div class="tiles">
    <div class="tile"><div class="v">−{n(-RV['classique']['ecart'])}&nbsp;km</div><div class="l">de lignes classiques gérées par SNCF Réseau ({rv0}-{rv1}), fermetures, déclassements et transferts confondus</div></div>
    <div class="tile"><div class="v">{pct(FO['pkt'])}</div><div class="l">de fréquentation des TER, pour {pct(FO['sieges_km'])} de places offertes ({fo0}-{fo1})</div></div>
    <div class="tile"><div class="v">{d(GU['part_sans_guichet'], 0)}&nbsp;%</div><div class="l">des gares hors Île-de-France sans guichet</div></div>
    <div class="tile"><div class="v">{pct(EF['contractuels']['pct'])}</div><div class="l">de contractuels à la SNCF ({EF['periode'][0]}-{EF['periode'][1]})</div></div>
  </div>"""
entete = f"""
<header>
  <div class="eyebrow">Services publics de transport · données SNCF, ART, Cerema</div>
  <h1>Des TER de plus en plus remplis, un réseau classique qui rétrécit : l'offre ferroviaire ne suit pas le rythme de la fréquentation</h1>
  <p class="lead">Ce que disent les données publiques sur le train, les cars et les transports urbains. Chaque chiffre vient d'une source officielle et peut être recalculé ; chaque graphique est accompagné de ses limites.</p>
  {bandeau}
  {tuiles}
</header>""" + casse


# --- Carte par département (mêmes valeurs que le tableau « Votre département ») ----------------------------
def sg(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + d(abs(v)) + "&nbsp;%"


DC = {o["departement"]: o for o in GD["departements"]}
s_carte = section_carte("La carte", "Gares et guichets, département par département", carte_departements("carte-transports", [
    {"libelle": "Gares sans guichet", "legende": "Part des gares sans guichet (hors Île-de-France)",
     "valeurs": {k: (None if o["ile_de_france"] else o["part_sans_guichet"]) for k, o in DC.items()}, "fmt": lambda v: d(v) + "&nbsp;%"},
    {"libelle": "Voyageurs en gare", "legende": "Évolution du nombre de voyageurs en gare, 2019-2024",
     "valeurs": {k: o["pct_voyageurs"] for k, o in DC.items()}, "fmt": sg, "inverse": True},
], "Carte des gares et guichets par département"), f"""
  <p>Survolez ou touchez un département pour lire sa valeur ; les boutons changent d'indicateur. Plus la teinte est foncée, plus la situation est défavorable. Les valeurs sont celles du tableau « Votre département » ci-dessous.</p>
  <p class="limite"><strong>Limites :</strong> classes de couleur = cinquièmes des départements ; guichets : photographie (points de vente traités en février 2024), hors Île-de-France où la donnée exclut le Transilien ; « sans guichet » ne veut pas dire « sans automate » ; départements d'outre-mer sans gare dans ces données.</p>""")


def partie(ident, titre, intro):
    return f'<div class="partie" id="{ident}"><div class="eyebrow">{titre}</div><p class="lead">{intro}</p></div>'


PARTIES = [
    ("lignes", "Les lignes", "Le réseau ferré national, année par année.", [s_rfn, s_rreg, s_res]),
    ("train-regional", "Le train régional", "Fréquentation, offre et suppressions des TER.", [s_freq, s_ter, s_annul, s_reg]),
    ("grandes-lignes", "Les grandes lignes", "La régularité des TGV.", [s_tgv]),
    ("cheminots", "Les cheminots", "Statut et contrats à la SNCF.", [s_eff]),
    ("gares", "Gares et réseau", "Guichets, arrêts de trains, statut des lignes.", [s_des, s_gui, s_gdep]),
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
tete = re.sub(r"<title>.*?</title>", "<title>Services publics de transport</title>", tete)
html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + tete + "\n" + STYLE_SUPPL + "\n" + STYLE_MILITANT + "\n" + STYLE_CARTE + "\n</head>\n<body>\n<div class=\"wrap\">" + entete + sommaire + corps + sources
        + "\n</div>\n</body>\n</html>\n")
with open(SORTIE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{SORTIE} généré ({len(html) // 1024} Ko, {html.count('<svg')} graphiques){' — BROUILLON' if BROUILLON else ''}")
