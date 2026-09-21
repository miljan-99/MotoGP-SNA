# -*- coding: utf-8 -*-
"""
preprocess.py — FILTERED_ROWS.csv (rezultati po trkama, 1949-2021)
-> kanonska tabela: (year, race_id, circuit, rider_id, rider, country,
                     team, constructor, position, points, classified)

Odluke predobrade (dokumentovano za tezu):
- Zadrzavamo samo premijer klasu: 500cc (1949-2001) + MotoGP (2002-).
- position < 1 su kodovi za neklasifikovane (DNF/DNS/DSQ; poeni uvijek 0)
  -> classified=False, position=NaN. Red se zadrzava (vozac JESTE ucestvovao).
- team_name '?' -> NaN (poznat tek od ~2005); konstruktor je 100% popunjen,
  pa je konstruktor primarna osa grupisanja kroz istoriju.
- Vozac je identifikovan numerickim ID-jem (kolona rider) -> nema problema
  varijanti imena; rider_name sluzi samo za prikaz.
"""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/FILTERED_ROWS.csv")
OUT = Path("data/processed/canonical.csv")
PREMIER = {"500cc", "MotoGP"}


def load_and_clean() -> pd.DataFrame:
    df = pd.read_csv(RAW)
    df = df[df["category"].isin(PREMIER)].copy()

    df["race_id"] = df["year"].astype(str) + "_" + df["sequence"].astype(str).str.zfill(2)
    df["classified"] = df["position"] >= 1
    df.loc[~df["classified"], "position"] = pd.NA
    df["team_name"] = df["team_name"].replace("?", pd.NA)

    # "Prezime, Ime" -> "Ime Prezime"
    df["rider_name"] = df["rider_name"].map(
        lambda s: " ".join(reversed([p.strip() for p in str(s).split(",")]))
        if "," in str(s) else str(s).strip())

    out = df.rename(columns={
        "rider": "rider_id", "rider_name": "rider", "team_name": "team",
        "bike_name": "constructor", "circuit_name": "circuit",
    })[["year", "race_id", "circuit", "rider_id", "rider", "country",
        "team", "constructor", "position", "points", "classified"]]
    return out.drop_duplicates()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = load_and_clean()
    n_races = df["race_id"].nunique()
    print(f"Kanonska tabela: {len(df)} redova, {df['rider_id'].nunique()} vozaca, "
          f"{n_races} trka, {df['year'].min()}-{df['year'].max()}")
    print(f"Klasifikovano: {df['classified'].mean():.1%}, "
          f"konstruktora: {df['constructor'].nunique()}")
    df.to_csv(OUT, index=False)
    print(f"Sacuvano: {OUT}")


if __name__ == "__main__":
    main()
