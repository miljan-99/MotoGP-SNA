# -*- coding: utf-8 -*-
"""figures_cyr.py — Slike sa cirilicnim natpisima (zahtjev fakultetskog sablona)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from build_networks import load_canonical

FIG = Path("output/figures"); FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "font.family": "DejaVu Sans"})
df = load_canonical()

# Slika 3.2.1 — broj vozaca i trka po sezoni
per = df.groupby("year").agg(vozaci=("rider", "nunique"), trke=("race_id", "nunique"))
fig, ax1 = plt.subplots(figsize=(9, 4))
ax1.plot(per.index, per.vozaci, color="#c1272d", label="Возачи")
ax2 = ax1.twinx()
ax2.plot(per.index, per.trke, color="#1b6ca8", label="Трке")
ax1.set_xlabel("Сезона")
ax1.set_ylabel("Број возача", color="#c1272d")
ax2.set_ylabel("Број трка", color="#1b6ca8")
ax1.set_title("Број возача и трка по сезони у премијер класи (1949–2025)")
ax1.grid(alpha=0.25)
plt.tight_layout(); plt.savefig(FIG / "cyr_31_vozaci_trke.png"); plt.close()

# Slika 3.2.2 — distribucija duzine karijere
races = df.groupby("rider")["race_id"].nunique()
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.hist(races, bins=np.logspace(0, np.log10(races.max()), 25), color="#1b6ca8")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Број трка у каријери")
ax.set_ylabel("Број возача")
ax.set_title("Расподјела дужине каријере возача")
ax.grid(alpha=0.25, which="both")
plt.tight_layout(); plt.savefig(FIG / "cyr_32_karijere.png"); plt.close()

# Slika 4.1.1 — dijagram toka obrade (pipeline)
fig, ax = plt.subplots(figsize=(9, 2.6))
ax.axis("off")
boxes = [("Два извора\nAPI + CSV", "#e8e8e8"),
         ("Припрема и\nспајање\nmerge_sources.py", "#cfe3f2"),
         ("Конструкција\nмрежа\nbuild_networks.py", "#cfe3f2"),
         ("Анализа\nmetrics.py\ncommunities.py", "#cfe3f2"),
         ("Резултати\nCSV / слике\nGEXF → Gephi", "#e8e8e8")]
w, gap = 1.6, 0.42
for i, (txt, col) in enumerate(boxes):
    x = i * (w + gap)
    ax.add_patch(plt.Rectangle((x, 0), w, 1.1, facecolor=col, edgecolor="#333"))
    ax.text(x + w / 2, 0.55, txt, ha="center", va="center", fontsize=8.5)
    if i < len(boxes) - 1:
        ax.annotate("", xy=(x + w + gap, 0.55), xytext=(x + w, 0.55),
                    arrowprops=dict(arrowstyle="->", color="#333"))
ax.set_xlim(-0.2, len(boxes) * (w + gap)); ax.set_ylim(-0.2, 1.3)
plt.tight_layout(); plt.savefig(FIG / "cyr_41_pipeline.png"); plt.close()
print("OK")


# Slika 3.2.3 — udio izvora po deceniji
import numpy as _np
m = df.copy()
m["dec"] = (m["year"] // 10) * 10
src = m.groupby(["dec", "source"]).size().unstack(fill_value=0)
for c in ("api", "kaggle"):
    if c not in src:
        src[c] = 0
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(src.index.astype(str), src["api"], label="Званични API", color="#1b6ca8")
ax.bar(src.index.astype(str), src["kaggle"], bottom=src["api"],
       label="Допуна из CSV скупа", color="#c1272d")
ax.set_xlabel("Деценија"); ax.set_ylabel("Број наступа")
ax.set_title("Поријекло записа у спојеном скупу података")
ax.legend(); ax.grid(alpha=0.25, axis="y")
plt.tight_layout(); plt.savefig(FIG / "cyr_33_izvori.png"); plt.close()
print("dodata slika izvora")
