# -*- coding: utf-8 -*-
"""
build_networks.py — Mreze iz kanonske tabele (granularnost: TRKA).

1. co_participation : vozaci u istoj trci; tezina = broj zajednickih trka
2. rivalry_gapN     : oba klasifikovana u istoj trci i |Δpozicija| <= N;
                      tezina = broj takvih trka (podrazumijevano N=2)
3. teammates        : isti tim u istoj trci (samo gdje je tim poznat, ~2005+)
4. brandmates       : isti konstruktor u istoj sezoni (cijela istorija)
5. rider_constructor: bipartitna vozac-konstruktor + projekcija na konstruktore
6. build_for_period : bilo koja mreza za opseg godina
"""
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
from networkx.algorithms import bipartite

DATA = Path("data/processed/canonical_merged.csv")
GEXF = Path("output/gexf")


def load_canonical() -> pd.DataFrame:
    return pd.read_csv(DATA)


def _add_edge(G, a, b, w=1):
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)


def _rider_attrs(G, df):
    stats = df.groupby("rider").agg(
        races=("race_id", "nunique"), first_year=("year", "min"),
        last_year=("year", "max"), points=("points", "sum"),
        wins=("position", lambda p: int((p == 1).sum())),
        country=("country", "first"))
    for r, row in stats.iterrows():
        if r in G:
            G.nodes[r].update(races=int(row.races), first_year=int(row.first_year),
                              last_year=int(row.last_year), points=float(row.points),
                              wins=int(row.wins), country=str(row.country))


def co_participation_network(df) -> nx.Graph:
    G = nx.Graph(name="co_participation")
    for _, grp in df.groupby("race_id"):
        for a, b in combinations(sorted(grp["rider"].unique()), 2):
            _add_edge(G, a, b)
    _rider_attrs(G, df)
    return G


def rivalry_network(df, max_gap: int = 2) -> nx.Graph:
    G = nx.Graph(name=f"rivalry_gap{max_gap}")
    d = df[df["classified"]].dropna(subset=["position"])
    for _, grp in d.groupby("race_id"):
        rows = list(grp[["rider", "position"]].drop_duplicates("rider")
                    .itertuples(index=False))
        for (r1, p1), (r2, p2) in combinations(rows, 2):
            if abs(p1 - p2) <= max_gap:
                _add_edge(G, r1, r2)
    _rider_attrs(G, df)
    return G


def rivalry_time_network(df, max_sec: float = 2.0) -> nx.Graph:
    """Rivalstvo po VREMENU: oba klasifikovana u istoj trci i razlika njihovih
    zaostataka za prvim <= max_sec sekundi. Precizniji kriterijum od razlike
    pozicija, dostupan za trke sa mjerenjem vremena."""
    G = nx.Graph(name=f"rivalry_time{max_sec:g}s")
    d = df[df["classified"] == True].copy()
    d["gap_first"] = pd.to_numeric(d["gap_first"], errors="coerce")
    d = d.dropna(subset=["gap_first"])
    d = d[d.groupby("race_id")["gap_first"].transform("max") > 0]  # trke sa mjerenjem
    for _, grp in d.groupby("race_id"):
        rows = list(grp[["rider", "gap_first"]].drop_duplicates("rider")
                    .itertuples(index=False))
        for (r1, g1), (r2, g2) in combinations(rows, 2):
            if abs(g1 - g2) <= max_sec:
                _add_edge(G, r1, r2)
    _rider_attrs(G, df)
    return G


def teammate_network(df) -> nx.Graph:
    G = nx.Graph(name="teammates")
    d = df.dropna(subset=["team"])
    for _, grp in d.groupby(["race_id", "team"]):
        for a, b in combinations(sorted(grp["rider"].unique()), 2):
            _add_edge(G, a, b)
    _rider_attrs(G, df)
    return G


def brandmate_network(df) -> nx.Graph:
    """Isti konstruktor u istoj sezoni — 'brend kolege' kroz cijelu istoriju."""
    G = nx.Graph(name="brandmates")
    for _, grp in df.groupby(["year", "constructor"]):
        for a, b in combinations(sorted(grp["rider"].unique()), 2):
            _add_edge(G, a, b)
    _rider_attrs(G, df)
    return G


def rider_constructor_bipartite(df) -> nx.Graph:
    B = nx.Graph(name="rider_constructor")
    pairs = (df.dropna(subset=["constructor"])
               .groupby(["rider", "constructor"])["race_id"].nunique()
               .reset_index(name="weight"))
    B.add_nodes_from(pairs["rider"].unique(), bipartite="rider")
    B.add_nodes_from(pairs["constructor"].unique(), bipartite="constructor")
    B.add_weighted_edges_from(pairs.itertuples(index=False, name=None))
    return B


def constructor_projection(df) -> nx.Graph:
    B = rider_constructor_bipartite(df)
    cons = {n for n, d in B.nodes(data=True) if d.get("bipartite") == "constructor"}
    G = bipartite.weighted_projected_graph(B, cons)
    G.name = "constructor_transfers"
    return G


def build_for_period(df, y1, y2, builder=co_participation_network, **kw):
    sub = df[(df["year"] >= y1) & (df["year"] <= y2)]
    G = builder(sub, **kw)
    G.name = f"{G.name}_{y1}-{y2}"
    return G


DECADES = [(1949, 1959), (1960, 1969), (1970, 1979), (1980, 1989),
           (1990, 1999), (2000, 2009), (2010, 2025)]


def export_gexf(G) -> Path:
    GEXF.mkdir(parents=True, exist_ok=True)
    p = GEXF / f"{G.name}.gexf"
    nx.write_gexf(G, p)
    print(f"[gexf] {p.name}: n={G.number_of_nodes()}, m={G.number_of_edges()}")
    return p


def main():
    df = load_canonical()
    for G in (co_participation_network(df), rivalry_network(df, 2),
              rivalry_time_network(df, 2.0),
              teammate_network(df), brandmate_network(df),
              rider_constructor_bipartite(df), constructor_projection(df)):
        export_gexf(G)
    for y1, y2 in DECADES:
        export_gexf(build_for_period(df, y1, y2, builder=rivalry_network, max_gap=2))


if __name__ == "__main__":
    main()
