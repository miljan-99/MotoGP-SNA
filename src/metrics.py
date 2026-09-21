# -*- coding: utf-8 -*-
"""metrics.py — Globalne metrike, random baseline i centralnosti."""
import networkx as nx
import pandas as pd


def global_metrics(G: nx.Graph) -> dict:
    n, m = G.number_of_nodes(), G.number_of_edges()
    out = {
        "mreza": G.name, "n": n, "m": m,
        "gustina": round(nx.density(G), 4),
        "prosj_stepen": round(2 * m / n, 2) if n else 0,
        "prosj_klaster": round(nx.average_clustering(G), 4),
        "komponente": nx.number_connected_components(G),
    }
    giant = G.subgraph(max(nx.connected_components(G), key=len))
    out["najveca_komp"] = giant.number_of_nodes()
    out["prosj_put"] = round(nx.average_shortest_path_length(giant), 3)
    out["dijametar"] = nx.diameter(giant)
    return out


def random_baseline(G: nx.Graph, seed=42) -> dict:
    """Erdos-Renyi G(n,m) — za small-world poredjenje."""
    R = nx.gnm_random_graph(G.number_of_nodes(), G.number_of_edges(), seed=seed)
    R.name = f"{G.name}_RANDOM"
    return global_metrics(R)


def centralities(G: nx.Graph) -> pd.DataFrame:
    df = pd.DataFrame({
        "degree": dict(G.degree()),
        "strength": dict(G.degree(weight="weight")),
        "betweenness": nx.betweenness_centrality(G, weight=None),
        "closeness": nx.closeness_centrality(G),
        "pagerank": nx.pagerank(G, weight="weight"),
        "eigenvector": nx.eigenvector_centrality(G, weight="weight", max_iter=1000),
    })
    return df.round(4).sort_values("pagerank", ascending=False)
