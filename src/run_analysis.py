# -*- coding: utf-8 -*-
"""run_analysis.py — Kompletna analiza -> output/*.csv"""
from pathlib import Path
import pandas as pd
import networkx as nx

from build_networks import (load_canonical, co_participation_network, rivalry_time_network,
                            rivalry_network, teammate_network, brandmate_network,
                            constructor_projection, build_for_period,
                            export_gexf, DECADES)
from metrics import global_metrics, random_baseline, centralities
from communities import detect, stability

OUT = Path("output"); OUT.mkdir(exist_ok=True)
df = load_canonical()

G_co = co_participation_network(df)
G_riv = rivalry_network(df, 2)
G_rvt = rivalry_time_network(df, 2.0)
G_tm = teammate_network(df)
G_bm = brandmate_network(df)
G_ct = constructor_projection(df)
mains = [G_co, G_riv, G_rvt, G_tm, G_bm, G_ct]

# 1) globalne metrike + ER baseline
rows = []
for G in mains:
    rows.append(global_metrics(G)); rows.append(random_baseline(G))
gm = pd.DataFrame(rows); gm.to_csv(OUT / "global_metrics.csv", index=False)
print("== GLOBALNE METRIKE ==\n", gm.to_string(index=False))

# 2) rivalry osjetljivost na max_gap
pd.DataFrame([global_metrics(rivalry_network(df, g)) for g in (1, 2, 3)]
             ).to_csv(OUT / "rivalry_sensitivity.csv", index=False)

# 3) centralnosti + korelacije
for G in (G_co, G_riv, G_rvt, G_ct):
    c = centralities(G); c.to_csv(OUT / f"centralities_{G.name}.csv")
c_riv = pd.read_csv(OUT / "centralities_rivalry_gap2.csv", index_col=0)
print("\n== TOP 12 RIVALRY (PageRank) ==\n", c_riv.head(12).to_string())
c_riv.corr(method="spearman").round(2).to_csv(OUT / "centrality_correlations.csv")

# 4) distribucija stepena + assortativnost
deg = pd.Series(dict(G_riv.degree()), name="degree")
deg.to_csv(OUT / "degree_distribution_rivalry.csv")
assort = {G.name: round(nx.degree_assortativity_coefficient(G), 3) for G in mains}
pd.Series(assort, name="assortativity").to_csv(OUT / "assortativity.csv")
print("\nAssortativnost:", assort)

# 5) zajednice + stabilnost
comm = []
for G in (G_riv, G_rvt, G_bm, G_ct):
    part, Q = detect(G)
    sizes = sorted(pd.Series(part).value_counts().tolist(), reverse=True)
    comm.append({"mreza": G.name, "zajednica": len(sizes), "Q": round(Q, 3),
                 "velicine_top5": str(sizes[:5])})
    export_gexf(G)
    pd.Series(part, name="community").rename_axis("node").to_csv(
        OUT / f"communities_{G.name}.csv")
print("\n== ZAJEDNICE ==\n", pd.DataFrame(comm).to_string(index=False))
pd.DataFrame(comm).to_csv(OUT / "communities_summary.csv", index=False)
print("\nStabilnost Louvain (rivalry):\n", stability(G_riv))

# 5b) NMI: zajednice vs. dekada prve sezone / dominantni konstruktor
from sklearn.metrics import normalized_mutual_info_score as nmi
part, _ = detect(G_riv)
nodes = list(part)
dec = {r: (G_riv.nodes[r]["first_year"] // 10) * 10 for r in nodes}
domc = df.groupby(["rider", "constructor"])["race_id"].nunique() \
         .reset_index().sort_values("race_id").groupby("rider").last()["constructor"]
res = {"NMI_zajednice_vs_dekada": round(nmi([part[n] for n in nodes],
                                            [dec[n] for n in nodes]), 3),
       "NMI_zajednice_vs_konstruktor": round(nmi([part[n] for n in nodes],
                                            [str(domc.get(n)) for n in nodes]), 3)}
pd.Series(res).to_csv(OUT / "nmi.csv"); print("\nNMI:", res)

# 6) temporalna evolucija (rivalry po dekadama)
temp = [global_metrics(build_for_period(df, y1, y2, builder=rivalry_network,
                                        max_gap=2)) for y1, y2 in DECADES]
pd.DataFrame(temp).to_csv(OUT / "temporal_rivalry.csv", index=False)
print("\n== TEMPORALNO ==\n", pd.DataFrame(temp).to_string(index=False))
