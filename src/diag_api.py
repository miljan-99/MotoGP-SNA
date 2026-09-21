# -*- coding: utf-8 -*-
"""
diag_api.py — Dijagnostika: za zadatu godinu ispisuje svaki event, njegove klase
i tipove sesija, pa se vidi tacno koji event ne daje trku premijer klase i zasto.

Pokretanje:
  python src/diag_api.py 2000
"""
import sys

from fetch_api import categories, events, seasons, sessions_of, classification

PREMIER = {"MotoGP", "500cc"}


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    ss = seasons(year, year)
    if not ss:
        print("nema sezone"); return
    _, sid = ss[0]

    evs = events(sid, year)
    print(f"{year}: {len(evs)} eventa\n")

    for i, ev in enumerate(evs, 1):
        name = ev.get("name") or (ev.get("circuit") or {}).get("name")
        cats = categories(ev.get("id"))
        cat_names = [(c.get("name") or "").replace("™", "").strip() for c in cats]
        match = [c for c, n in zip(cats, cat_names) if n in PREMIER]

        print(f"{i:2d}. {str(name)[:42]:42s} seq={ev.get('sequence')} "
              f"test={ev.get('test')}")
        print(f"    klase: {cat_names}")

        if not match:
            print("    >>> NEMA premijer klase u ovom eventu")
            continue

        for c in match:
            sess = sessions_of(ev.get("id"), c.get("id"))
            types = [(s.get("type") or "").upper() for s in sess]
            print(f"    sesije za {(c.get('name') or '').strip()}: {types}")
            races = [s for s in sess if (s.get("type") or "").upper() == "RAC"]
            if not races:
                print("    >>> NEMA sesije tipa RAC")
            for s in races:
                d = classification(s.get("id"))
                n = len((d or {}).get("classification", []))
                print(f"    RAC {s.get('id')[:8]}: {n} rezultata")
                if n == 0:
                    print("    >>> KLASIFIKACIJA PRAZNA")


if __name__ == "__main__":
    main()
