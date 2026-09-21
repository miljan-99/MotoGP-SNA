# MotoGP kao kompleksna mreza — master rad
Miljan Bodiroga · Elektrotehnicki fakultet Univerziteta u Beogradu · avgust 2026.

## Podaci
Dva nezavisna izvora, spojena u jedinstvenu tabelu:
- **Zvanicni MotoGP API** (api.motogp.pulselive.com) — 836 trka, 1949–2025,
  bogata obiljezja (gap_first, total_laps, average_speed, status, team_id).
  Za 163 trke ne daje klasifikaciju.
- **Izvedeni CSV skup** — 910 trka, 1949–2021, samo osnovna obiljezja.

Spojeno: **18.528 nastupa · 999 trka · 846 vozaca · 1949–2025** (`canonical_merged.csv`,
kolona `source` cuva porijeklo svakog reda).

Uparivanje trka ide preko sastava startne liste (Jaccard >= 0.4), ne preko imena
staza. Rezultat: 747 uparenih + 163 samo u CSV skupu = tacno broj praznih
klasifikacija iz API-ja (nezavisna potvrda).

## Pokretanje od nule
```
pip install requests pandas networkx matplotlib python-louvain scikit-learn
python src/fetch_api.py --from 1949 --to 2025   # preuzimanje (kesira se)
python src/preprocess.py                        # pomocni izvor
python src/merge_sources.py                     # spajanje izvora
python src/build_networks.py                    # mreze -> output/gexf/
python src/run_analysis.py                      # analiza -> output/*.csv
python src/figures_cyr.py                       # slike (cirilica)
python src/figures_ch5.py                       # slike za poglavlje 5
```
Svi generatori slucajnih brojeva imaju fiksno sjeme -> ponovljivi rezultati.

## Mreze (7)
| Mreza | n | m | Definicija grane |
|---|---|---|---|
| co_participation | 849 | 19.024 | nastup u istoj trci |
| rivalry_gap2 | 825 | 7.446 | oba klasifikovana, \|Δpozicija\| <= 2 |
| rivalry_time2s | 633 | 6.946 | oba klasifikovana, \|Δgap_first\| <= 2 s |
| teammates | 132 | 257 | isti tim u istoj trci |
| brandmates | 824 | 11.887 | isti proizvodjac u istoj sezoni |
| rider_constructor | 944 | 1.446 | bipartitna vozac–proizvodjac |
| constructor_transfers | 95 | 357 | projekcija na proizvodjace |
Plus 7 dekadnih presjeka mreze rivalstva (1949–59 ... 2010–25).

## Kljucni rezultati
- **Mali svijet** za sve mreze vozaca: grupisanje 14–26x vece od Erdos–Renyi
  grafa istih dimenzija, uz kratke puteve (max L = 3,87).
- **Centralnost = strukturna uloga, ne uspjeh:** najcentralniji u rivalry_gap2 je
  Jack Findlay (nikad sampion, 20 sezona). Rossi prvi po snazi (1.093) i
  sopstvenom vektoru (0,352) — jezgro, ne most.
- **Zajednice = generacije:** Q = 0,611, NMI vs. decenija debija **0,561**
  naspram 0,344 vs. proizvodjac. Potvrdjeno i na mrezi po vremenu.
- **Vremenska evolucija:** vozaca 227 -> 111, gustina 0,050 -> 0,225.
- **Rivalstvo po vremenu** mijenja poredak u korist sampiona (Agostini 1., Rossi 3.),
  ali strukturni zaključci ostaju isti.

## Struktura
- `src/` — 8 modula (preuzimanje, spajanje, mreze, metrike, zajednice, slike)
- `data/processed/` — canonical.csv, canonical_api.csv, canonical_merged.csv
- `output/gexf/` — 14 mreza za Gephi (atributi: community, first_year, wins, country)
- `output/*.csv` — 14 tabela rezultata
- `output/figures/` — slike (cirilicni natpisi, za tezu)
- `teza/` — teza (.docx) + uputstvo za Gephi + linkovi ka referencama
