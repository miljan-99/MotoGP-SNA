# -*- coding: utf-8 -*-
"""
fetch_api.py — Preuzimanje KOMPLETNIH rezultata iz zvanicnog MotoGP API-ja
(api.motogp.pulselive.com). Bez tokena i registracije.

Lanac poziva (potvrdjen iz racingmike_motogp_import):
  1. /results/seasons                                  -> (godina, seasonUuid)
  2. /results/events?seasonUuid=...&isFinished=true     -> trke sezone
  3. /results/categories?eventUuid=...                  -> klase na tom eventu
  4. /results/sessions?eventUuid=...&categoryUuid=...    -> sesije (trazimo trku)
  5. /results/session/{id}/classification?test=false     -> rezultati

Izlaz: data/processed/canonical_api.csv sa istim kolonama kao postojeca
kanonska tabela + DODATNA polja koja Kaggle skup ne sadrzi:
  gap_first, gap_lap, total_laps, average_speed, status, team_id, constructor_id

Pokretanje:
  pip install requests
  python src/fetch_api.py                 # premijer klasa, 1949-2025
  python src/fetch_api.py --from 2000 --to 2005
  python src/fetch_api.py --categories MotoGP 500cc Moto2 250cc

Napomena: preuzimanje cijele istorije traje 1-3 sata (oko 1000 trka, vise poziva
po trci). Sve odgovore kesira u data/raw/api_cache/, pa se prekinuto preuzimanje
nastavlja bez ponovnog pozivanja API-ja.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.motogp.pulselive.com/motogp/v1"
CACHE = Path("data/raw/api_cache")
OUT = Path("data/processed/canonical_api.csv")

# klase premijer ranga; mijenja se preko --categories
PREMIER = {"MotoGP", "500cc"}

# sesija trke: API koristi tip "RAC" (a od 2023. i "SPR" za sprint - preskacemo)
RACE_TYPES = {"RAC"}

session_http = requests.Session()
session_http.headers.update({"User-Agent": "master-thesis-research/1.0"})


def get(url: str, cache_key: str, pause: float = 0.3):
    """GET sa kesiranjem na disk i ponovnim pokusajima."""
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", cache_key)[:150]
    path = CACHE / f"{safe}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink()

    last = None
    for attempt in range(4):
        try:
            r = session_http.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                time.sleep(pause)
                return data
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(2 ** attempt)
    print(f"  [preskocen] {url} ({last})", file=sys.stderr)
    return None


def seasons(y_from: int, y_to: int):
    data = get(f"{BASE}/results/seasons", "seasons") or []
    out = [(s["year"], s["id"]) for s in data if y_from <= s["year"] <= y_to]
    return sorted(out)


def events(season_id: str, year: int):
    url = f"{BASE}/results/events?seasonUuid={season_id}&isFinished=true"
    return get(url, f"events_{year}") or []


def categories(event_id: str):
    url = f"{BASE}/results/categories?eventUuid={event_id}"
    return get(url, f"cats_{event_id}") or []


def sessions_of(event_id: str, category_id: str):
    url = f"{BASE}/results/sessions?eventUuid={event_id}&categoryUuid={category_id}"
    return get(url, f"sess_{event_id}_{category_id}") or []


def classification(session_id: str):
    url = f"{BASE}/results/session/{session_id}/classification?test=false"
    return get(url, f"class_{session_id}")


# registar: event_id -> race_id (garantuje jedinstvenost i kad API ne da sequence)
_RACE_IDS: dict[str, str] = {}
_USED_SEQ: dict[int, set[int]] = {}

# trke za koje API ne daje rezultate (za odjeljak o ogranicenjima podataka)
MISSING: list[tuple] = []


def race_id_for(ev: dict, year: int) -> str:
    """Jedinstven identifikator trke. Ako sequence nedostaje ili se ponavlja
    (API to zna vratiti), dodjeljuje se prvi slobodan redni broj."""
    ev_id = ev.get("id")
    if ev_id in _RACE_IDS:
        return _RACE_IDS[ev_id]
    used = _USED_SEQ.setdefault(year, set())
    seq = ev.get("sequence")
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        seq = None
    if seq is None or seq in used:
        seq = (max(used) + 1) if used else 1
    used.add(seq)
    rid = f"{year}_{str(seq).zfill(2)}"
    _RACE_IDS[ev_id] = rid
    return rid


def rows_for_event(ev: dict, year: int, wanted: set[str]):
    """Vraca listu redova (dict) za jednu trku, za sve zeljene klase."""
    out = []
    ev_id = ev.get("id")
    circuit = ((ev.get("circuit") or {}).get("name")
               or (ev.get("circuit") or {}).get("place") or ev.get("name"))

    for cat in categories(ev_id):
        cname = (cat.get("name") or "").strip()
        # API zna vratiti "MotoGP™" i slicno
        norm = cname.replace("™", "").strip()
        if norm not in wanted:
            continue

        for ses in sessions_of(ev_id, cat.get("id")):
            if (ses.get("type") or "").upper() not in RACE_TYPES:
                continue
            data = classification(ses.get("id"))
            if not data:
                MISSING.append((year, circuit, norm, "poziv neuspjesan"))
                continue
            if not data.get("classification"):
                MISSING.append((year, circuit, norm, "klasifikacija prazna"))
                continue
            for it in data.get("classification", []):
                rider = it.get("rider") or {}
                if not rider.get("id"):
                    continue
                team = it.get("team") or {}
                cons = it.get("constructor") or {}
                gap = it.get("gap") or {}
                pos = it.get("position")
                out.append({
                    "year": year,
                    "race_id": race_id_for(ev, year),
                    "circuit": circuit,
                    "category": norm,
                    "rider_id": rider.get("legacy_id") or rider.get("id"),
                    "rider": rider.get("full_name"),
                    "country": ((rider.get("country") or {}).get("iso")),
                    "team": team.get("name"),
                    "team_id": team.get("id"),
                    "constructor": cons.get("name"),
                    "constructor_id": cons.get("id"),
                    "position": pos if pos else "",
                    "points": it.get("points") or 0,
                    "classified": bool(pos),
                    "status": it.get("status"),
                    "time": it.get("time"),
                    "gap_first": gap.get("first"),
                    "gap_lap": gap.get("lap"),
                    "total_laps": it.get("total_laps"),
                    "average_speed": it.get("average_speed"),
                })
    return out


FIELDS = ["year", "race_id", "circuit", "category", "rider_id", "rider", "country",
          "team", "team_id", "constructor", "constructor_id", "position", "points",
          "classified", "status", "time", "gap_first", "gap_lap", "total_laps",
          "average_speed"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="y_from", type=int, default=1949)
    ap.add_argument("--to", dest="y_to", type=int, default=2025)
    ap.add_argument("--categories", nargs="+", default=sorted(PREMIER))
    args = ap.parse_args()
    wanted = set(args.categories)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows, n_races = [], 0

    for year, sid in seasons(args.y_from, args.y_to):
        evs = events(sid, year)
        print(f"{year}: {len(evs)} trka u kalendaru", flush=True)
        for ev in evs:
            rows = rows_for_event(ev, year, wanted)
            if rows:
                n_races += 1
                all_rows.extend(rows)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)

    per_year = {}
    for r in all_rows:
        per_year.setdefault(r["year"], set()).add(r["race_id"])
    print("\nTrka po godini u izlazu:")
    for y in sorted(per_year):
        print(f"  {y}: {len(per_year[y])}")

    riders = {r["rider"] for r in all_rows}
    if MISSING:
        log = OUT.parent / "api_missing_races.csv"
        with log.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["godina", "staza", "klasa", "razlog"])
            w.writerows(MISSING)
        print(f"\nTrka bez rezultata u API-ju: {len(MISSING)} (spisak: {log})")
        for m in MISSING[:10]:
            print("   ", " | ".join(str(x) for x in m))
        if len(MISSING) > 10:
            print(f"    ... i još {len(MISSING) - 10}")

    print(f"\nGOTOVO: {len(all_rows)} nastupa | {n_races} trka | {len(riders)} vozaca")
    print(f"Sacuvano: {OUT}")
    print("\nProvjera (broj nastupa poznatih vozaca):")
    for name in ("Valentino Rossi", "Alex Barros", "Giacomo Agostini"):
        k = len({r["race_id"] for r in all_rows if r["rider"] == name})
        if k:
            print(f"  {name}: {k}")


if __name__ == "__main__":
    main()
