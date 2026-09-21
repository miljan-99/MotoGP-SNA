# -*- coding: utf-8 -*-
"""make_figures.py — Deskriptivne slike + preview mreza + rezultatske slike."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from build_networks import load_canonical, rivalry_network, constructor_projection
from communities import detect

FIG = Path("output/figures"); FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 9})
df = load_canonical()

# 1. broj vozaca i trka po sezoni
fig, ax1 = plt.subplots(figsize=(9, 4))
per = df.groupby("year").agg(vozaci=("rider", "nunique"), trke=("race_id", "nunique"))
ax1.plot(per.index, per.vozaci, color="#d62828", label="Vozača u sezoni")
ax2 = ax1.twinx()
ax2.plot(per.index, per.trke, color="#219ebc", label="Trka u sezoni")
ax1.set_ylabel("Vozača", color="#d62828"); ax2.set_ylabel("Trka", color="#219ebc")
ax1.set_title("Premijer klasa 1949–2021: broj vozača i trka po sezoni")
plt.tight_layout(); plt.savefig(FIG / "01_vozaci_trke_po_sezoni.png"); plt.close()

# 2. distribucija broja trka po vozacu (log-log)
races = df.groupby("rider")["race_id"].nunique()
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(races, bins=np.logspace(0, np.log10(races.max()), 25), color="#219ebc")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Broj trka u karijeri"); ax.set_ylabel("Broj vozača")
ax.set_title("Distribucija dužine karijere (obje ose log)")
plt.tight_layout(); plt.savefig(FIG / "02_distribucija_karijera.png"); plt.close()

# 3. rivalry mreza (labele samo za top 15 po betweenness)
G = rivalry_network(df, 2)
part, Q = detect(G)
bt = nx.betweenness_centrality(G)
pos = nx.spring_layout(G, seed=42, k=0.15)
fig, ax = plt.subplots(figsize=(11, 9))
nx.draw_networkx_edges(G, pos, alpha=0.03, ax=ax)
nx.draw_networkx_nodes(G, pos, node_color=[part[n] for n in G], cmap="tab10",
                       node_size=[3 + 3000 * bt[n] for n in G], ax=ax)
top = sorted(bt, key=bt.get, reverse=True)[:15]
nx.draw_networkx_labels(G, pos, labels={n: n for n in top}, font_size=8,
                        font_weight="bold", ax=ax)
ax.set_title(f"Mreža rivalstva (n={G.number_of_nodes()}, m={G.number_of_edges()}); "
             f"boja = zajednica (Q={Q:.2f}), veličina = betweenness")
ax.axis("off"); plt.tight_layout()
plt.savefig(FIG / "03_rivalry_mreza.png"); plt.close()

# 4. distribucija stepena rivalry mreze (log-log scatter)
deg = np.array([d for _, d in G.degree()])
vals, cnts = np.unique(deg, return_counts=True)
fig, ax = plt.subplots(figsize=(6, 4))
ax.scatter(vals, cnts, s=14, color="#d62828")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Stepen k"); ax.set_ylabel("Broj čvorova")
ax.set_title("Distribucija stepena — mreža rivalstva (log-log)")
plt.tight_layout(); plt.savefig(FIG / "04_distribucija_stepena.png"); plt.close()

# 5. mreza transfera konstruktora
Gc = constructor_projection(df)
Gc = Gc.subgraph(max(nx.connected_components(Gc), key=len))
partc, Qc = detect(Gc.copy())
deg_c = dict(Gc.degree(weight="weight"))
posc = nx.spring_layout(Gc, seed=7, k=0.6, weight="weight")
fig, ax = plt.subplots(figsize=(10, 8))
nx.draw_networkx_edges(Gc, posc, alpha=0.15, ax=ax)
nx.draw_networkx_nodes(Gc, posc, node_color=[partc[n] for n in Gc], cmap="tab10",
                       node_size=[10 + 3 * deg_c[n] for n in Gc], ax=ax)
lab = sorted(deg_c, key=deg_c.get, reverse=True)[:20]
nx.draw_networkx_labels(Gc, posc, labels={n: n for n in lab}, font_size=7, ax=ax)
ax.set_title(f"Mreža transfera konstruktora (najveća komponenta, Q={Qc:.2f})")
ax.axis("off"); plt.tight_layout()
plt.savefig(FIG / "05_konstruktori_mreza.png"); plt.close()

# 6. temporalna evolucija
t = pd.read_csv("output/temporal_rivalry.csv")
lbl = ["1949–59", "1960–69", "1970–79", "1980–89", "1990–99", "2000–09", "2010–21"]
fig, ax = plt.subplots(figsize=(8, 4))
x = range(len(t))
ax.plot(x, t["gustina"], "o-", label="Gustina", color="#d62828")
ax.plot(x, t["prosj_klaster"], "s-", label="Prosj. klasterizacija", color="#219ebc")
axb = ax.twinx(); axb.bar(x, t["n"], alpha=0.15, color="gray", label="Broj vozača")
axb.set_ylabel("Broj vozača (stubići)")
ax.set_xticks(list(x)); ax.set_xticklabels(lbl, rotation=30)
ax.legend(loc="upper left"); ax.set_title("Evolucija mreže rivalstva po dekadama")
plt.tight_layout(); plt.savefig(FIG / "06_temporalna_evolucija.png"); plt.close()

# 7. zajednice vs. vrijeme: prosjecna prva sezona po zajednici
comm_years = pd.DataFrame({"c": [part[n] for n in G],
                           "fy": [G.nodes[n]["first_year"] for n in G]})
big = comm_years.groupby("c").filter(lambda g: len(g) > 30)
fig, ax = plt.subplots(figsize=(7, 4))
big.boxplot(column="fy", by="c", ax=ax)
ax.set_xlabel("Zajednica (Louvain)"); ax.set_ylabel("Prva sezona vozača")
ax.set_title("Zajednice rivalske mreže = generacije"); plt.suptitle("")
plt.tight_layout(); plt.savefig(FIG / "07_zajednice_generacije.png"); plt.close()
print("Slike:", sorted(p.name for p in FIG.glob("*.png")))
