# -*- coding: utf-8 -*-
"""figures_ch5.py — Slike za poglavlje 5 (cirilicni natpisi)."""
import os
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
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "font.family": "DejaVu Sans"})
df = load_canonical()
G = rivalry_network(df, 2)
part, Q = detect(G)

# --- 5.1.1 mreza rivalstva sa zajednicama ---
bt = nx.betweenness_centrality(G)
pos = nx.spring_layout(G, seed=42, k=0.15)
fig, ax = plt.subplots(figsize=(10, 8))
nx.draw_networkx_edges(G, pos, alpha=0.03, ax=ax)
nx.draw_networkx_nodes(G, pos, node_color=[part[n] for n in G], cmap="tab10",
                       node_size=[4 + 2500 * bt[n] for n in G], ax=ax)
top = sorted(bt, key=bt.get, reverse=True)[:14]
nx.draw_networkx_labels(G, pos, labels={n: n for n in top}, font_size=8,
                        font_weight="bold", ax=ax)
ax.set_title(f"Мрежа ривалства: боја = заједница, величина = релациона централност (Q = {Q:.2f})")
ax.axis("off"); plt.tight_layout(); plt.savefig(FIG / "c51_mreza.png"); plt.close()

# --- 5.2.1 stepen vs medjupolozenost ---
deg = dict(G.degree())
fig, ax = plt.subplots(figsize=(7, 4.6))
ax.scatter([deg[n] for n in G], [bt[n] for n in G], s=12, alpha=0.55, color="#1b6ca8")
for n in sorted(bt, key=bt.get, reverse=True)[:6]:
    ax.annotate(n, (deg[n], bt[n]), fontsize=7.5, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("Степен чвора"); ax.set_ylabel("Релациона централност")
ax.set_title("Однос степена и релационе централности у мрежи ривалства")
ax.grid(alpha=0.25)
plt.tight_layout(); plt.savefig(FIG / "c52_stepen_medju.png"); plt.close()

# --- 5.3.1 raspodjela stepena ---
d = np.array([v for _, v in G.degree()])
vals, cnts = np.unique(d, return_counts=True)
fig, ax = plt.subplots(figsize=(6.5, 4.2))
ax.scatter(vals, cnts, s=16, color="#c1272d")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Степен k"); ax.set_ylabel("Број чворова")
ax.set_title("Расподјела степена у мрежи ривалства")
ax.grid(alpha=0.25, which="both")
plt.tight_layout(); plt.savefig(FIG / "c53_stepen.png"); plt.close()

# --- 5.4.1 zajednice kao generacije ---
data = pd.DataFrame({"c": [part[n] for n in G],
                     "fy": [G.nodes[n]["first_year"] for n in G]})
red = data.groupby("c")["fy"].median().sort_values().index
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.boxplot([data[data.c == c]["fy"] for c in red],
           tick_labels=[f"З{i+1}\n(n={len(data[data.c==c])})" for i, c in enumerate(red)])
ax.set_ylabel("Прва сезона возача"); ax.set_xlabel("Заједница")
ax.set_title("Заједнице мреже ривалства одговарају генерацијама возача")
ax.grid(alpha=0.25, axis="y")
plt.tight_layout(); plt.savefig(FIG / "c54_generacije.png"); plt.close()

# --- 5.5.1 temporalna evolucija ---
t = pd.read_csv("output/temporal_rivalry.csv")
lbl = ["1949–59", "1960–69", "1970–79", "1980–89", "1990–99", "2000–09", "2010–25"]
fig, ax = plt.subplots(figsize=(8, 4.2))
x = range(len(t))
axb = ax.twinx()
axb.bar(x, t["n"], alpha=0.18, color="gray")
axb.set_ylabel("Број возача (стубићи)")
ax.plot(x, t["gustina"], "o-", color="#c1272d", label="Густина")
ax.plot(x, t["prosj_klaster"], "s-", color="#1b6ca8", label="Коеф. кластерисања")
ax.set_xticks(list(x)); ax.set_xticklabels(lbl, rotation=25)
ax.set_ylim(0, 0.85); ax.legend(loc="upper left")
ax.set_title("Еволуција мреже ривалства по деценијама")
ax.set_zorder(axb.get_zorder() + 1); ax.patch.set_visible(False)
plt.tight_layout(); plt.savefig(FIG / "c55_evolucija.png"); plt.close()

# --- 5.6.1 mreza transfera proizvodjaca ---
Gc = constructor_projection(df)
Gc = Gc.subgraph(max(nx.connected_components(Gc), key=len)).copy()
pc, Qc = detect(Gc)
dc = dict(Gc.degree(weight="weight"))
posc = nx.spring_layout(Gc, seed=7, k=0.6, weight="weight")
fig, ax = plt.subplots(figsize=(9, 7))
nx.draw_networkx_edges(Gc, posc, alpha=0.15, ax=ax)
nx.draw_networkx_nodes(Gc, posc, node_color=[pc[n] for n in Gc], cmap="tab10",
                       node_size=[12 + 2.5 * dc[n] for n in Gc], ax=ax)
lab = sorted(dc, key=dc.get, reverse=True)[:18]
nx.draw_networkx_labels(Gc, posc, labels={n: n for n in lab}, font_size=7.5, ax=ax)
ax.set_title("Мрежа трансфера произвођача (највећа компонента)")
ax.axis("off"); plt.tight_layout(); plt.savefig(FIG / "c56_proizvodjaci.png"); plt.close()
print("OK", sorted(p.name for p in FIG.glob("c5*.png")))

# --- 5.6.1 mreza rivalstva po vremenu ---
from build_networks import rivalry_time_network
Gt = rivalry_time_network(df, 2.0)
Gt = Gt.subgraph(max(nx.connected_components(Gt), key=len)).copy()
pt, Qt = detect(Gt)
btt = nx.betweenness_centrality(Gt)
post = nx.spring_layout(Gt, seed=11, k=0.16)
fig, ax = plt.subplots(figsize=(10, 8))
nx.draw_networkx_edges(Gt, post, alpha=0.03, ax=ax)
nx.draw_networkx_nodes(Gt, post, node_color=[pt[n] for n in Gt], cmap="tab10",
                       node_size=[4 + 2200 * btt[n] for n in Gt], ax=ax)
topt = sorted(btt, key=btt.get, reverse=True)[:14]
nx.draw_networkx_labels(Gt, post, labels={n: n for n in topt}, font_size=8,
                        font_weight="bold", ax=ax)
ax.set_title(f"Мрежа ривалства по временској разлици (Q = {Qt:.2f})")
ax.axis("off"); plt.tight_layout(); plt.savefig(FIG / "c57_rivalstvo_vrijeme.png"); plt.close()
print("dodata slika mreze po vremenu")
