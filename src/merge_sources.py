# -*- coding: utf-8 -*-
"""
merge_sources.py — Spajanje dva izvora u jedinstvenu kanonsku tabelu.

Problem: nijedan izvor nije potpun.
  * API (canonical_api.csv): 836 trka, 1949-2025, bogata obiljezja
    (gap_first, total_laps, average_speed, status, team_id, constructor_id),
    ali za 163 trke ne daje klasifikaciju (uglavnom 1949-1999).
  * Kaggle (canonical.csv): 910 trka, 1949-2021, samo osnovna obiljezja,
    ali sadrzi vecinu trka koje API ne daje.

Rjesenje: API je primarni izvor; trke koje API ne daje popunjavaju se iz Kaggle
skupa. Rezultat ima kolonu `source` ('api' / 'kaggle') pa je svaki red sljediv.

Uparivanje trka NE ide preko imena staze (izvori koriste razlicite nazive), nego
preko preklapanja startne liste (Jaccard indeks nad skupom vozaca). Time se
izbjegava rucno mapiranje imena staza i moguce greske.

Identitet vozaca: imena se normalizuju (bez dijakritika, mala slova), pa se
vozacima iz Kaggle skupa dodjeljuje `rider_id` iz API-ja kad se ime poklopi.
Vozaci koji postoje samo u Kaggle skupu dobijaju ID sa prefiksom 'K'.

Pokretanje: python src/merge_sources.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

API = Path("data/processed/canonical_api.csv")
KAG = Path("data/processed/canonical.csv")
OUT = Path("data/processed/canonical_merged.csv")
JACCARD_MIN = 0.4          # iznad ovoga se smatra da je rijec o istoj trci


def norm_name(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return " ".join(s.split())


def load():
    a = pd.read_csv(API)
    k = pd.read_csv(KAG)
    a["rider_key"] = a["rider"].map(norm_name)
    k["rider_key"] = k["rider"].map(norm_name)
    return a, k


def match_races(a: pd.DataFrame, k: pd.DataFrame):
    """Vraca (mapa kaggle_race_id -> api_race_id, spisak nesparenih kaggle trka)."""
    matched, unmatched = {}, []
    for year in sorted(k["year"].unique()):
        ay = a[a["year"] == year]
        ky = k[k["year"] == year]
        api_sets = {rid: set(g["rider_key"]) for rid, g in ay.groupby("race_id")}
        kag_sets = {rid: set(g["rider_key"]) for rid, g in ky.groupby("race_id")}
        taken = set()
        # greedy: za svaku kaggle trku najbolja slobodna api trka
        for krid, ks in sorted(kag_sets.items()):
            best, best_j = None, 0.0
            for arid, as_ in api_sets.items():
                if arid in taken or not ks or not as_:
                    continue
                j = len(ks & as_) / len(ks | as_)
                if j > best_j:
                    best, best_j = arid, j
            if best is not None and best_j >= JACCARD_MIN:
                matched[krid] = best
                taken.add(best)
            else:
                unmatched.append(krid)
    return matched, unmatched


def build_merged(a: pd.DataFrame, k: pd.DataFrame, unmatched: list) -> pd.DataFrame:
    # mapa: normalizovano ime -> rider_id iz API-ja
    name2id = (a.dropna(subset=["rider_id"])
                .groupby("rider_key")["rider_id"].first().to_dict())

    a2 = a.copy()
    a2["source"] = "api"

    fill = k[k["race_id"].isin(unmatched)].copy()
    fill["source"] = "kaggle"
    # prefiks da se kaggle race_id ne sudari sa api race_id
    fill["race_id"] = fill["race_id"].astype(str) + "_K"

    unresolved = sorted(set(fill.loc[~fill["rider_key"].isin(name2id), "rider_key"]))
    fill["rider_id"] = [
        name2id.get(rk, f"K{abs(hash(rk)) % 10**6}") for rk in fill["rider_key"]]

    # kolone koje Kaggle ne posjeduje
    for c in ("category", "team_id", "constructor_id", "status", "time",
              "gap_first", "gap_lap", "total_laps", "average_speed"):
        if c not in fill.columns:
            fill[c] = pd.NA
    fill["category"] = fill["year"].map(lambda y: "MotoGP" if y >= 2002 else "500cc")

    cols = [c for c in a2.columns if c in set(a2.columns) | set(fill.columns)]
    merged = pd.concat([a2[cols], fill.reindex(columns=cols)], ignore_index=True)
    return merged, unresolved


def main():
    a, k = load()
    print(f"API   : {len(a):6d} nastupa | {a.race_id.nunique():4d} trka | "
          f"{a.year.min()}-{a.year.max()}")
    print(f"Kaggle: {len(k):6d} nastupa | {k.race_id.nunique():4d} trka | "
          f"{k.year.min()}-{k.year.max()}")

    matched, unmatched = match_races(a, k)
    print(f"\nUparene trke (isti dogadjaj u oba izvora): {len(matched)}")
    print(f"Kaggle trke kojih nema u API-ju (dodaju se): {len(unmatched)}")

    merged, unresolved = build_merged(a, k, unmatched)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False)

    print(f"\nSPOJENO: {len(merged)} nastupa | {merged.race_id.nunique()} trka | "
          f"{merged.rider_id.nunique()} vozaca | {merged.year.min()}-{merged.year.max()}")
    print("Izvor redova:", merged.source.value_counts().to_dict())
    if unresolved:
        print(f"\nVozaci samo u Kaggle skupu (novi ID): {len(unresolved)}")
        print("  primjeri:", unresolved[:8])

    print("\nKontrola broja nastupa:")
    for name, zvan in [("Valentino Rossi", 372), ("Alex Barros", 246),
                       ("Nicky Hayden", 218), ("Giacomo Agostini", None)]:
        key = norm_name(name)
        n = merged[merged.rider_key == key].race_id.nunique() if "rider_key" in merged \
            else merged[merged.rider.map(norm_name) == key].race_id.nunique()
        print(f"  {name:20s} spojeno {n:3d} | zvanicno {zvan}")

    print(f"\nSacuvano: {OUT}")


if __name__ == "__main__":
    main()
