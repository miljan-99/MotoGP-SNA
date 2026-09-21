# -*- coding: utf-8 -*-
"""communities.py — Louvain detekcija zajednica + modularnost."""
import community as community_louvain  # python-louvain
import networkx as nx
import pandas as pd


def detect(G: nx.Graph, seed=42):
    part = community_louvain.best_partition(G, weight="weight", random_state=seed)
    Q = community_louvain.modularity(part, G, weight="weight")
    nx.set_node_attributes(G, part, "community")
    return part, Q


def stability(G: nx.Graph, runs=20):
    """Louvain je stohastican — provjera stabilnosti broja zajednica i Q."""
    res = []
    for s in range(runs):
        p = community_louvain.best_partition(G, weight="weight", random_state=s)
        res.append((len(set(p.values())),
                    community_louvain.modularity(p, G, weight="weight")))
    df = pd.DataFrame(res, columns=["broj_zajednica", "Q"])
    return df.describe().loc[["mean", "std", "min", "max"]].round(3)
