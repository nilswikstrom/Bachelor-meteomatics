"""
ELLIPSEDIAGRAM — Predikerte spredningsellipser + treffområde-sirkel
-------------------------------------------------------------------
Produserer én separat fil per avstand:
  - ellipser_10km.pdf
  - ellipser_20km.pdf
  - ellipser_30km.pdf

Verdiene tolkes som FULL DIAMETER av ellipsen.
Treff-sirkelen er definert ved RADIUS.

Krever: pip install matplotlib numpy
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
import matplotlib.patches as mpatches


# ============================================================
# ============== LIM INN DINE TALL HER =======================
# ============================================================
# Per avstand: dict { format: (mean_range, mean_cross) }   ← FULL diameter

AVSTANDER = {
    ## Placeholder numbers and locations, replace with real numbers and location names
    "10 km": {
        "Ingen vær (kontroll)":  (aa.aa, bb.bb),
        "LOCATION-NAME 1":       (cc.cc, dd.dd),
        "LOCATION-NAME 2":       (ee.ee, ff.ff),
        "LOCATION-NAME 3":       (gg.gg, hh.hh),
    },
    "20 km": {
        "Ingen vær (kontroll)":  (iii.ii, jjj.jj),
        "LOCATION-NAME 1":       (kkk.kk, lll.ll),
        "LOCATION-NAME 2":       (mmm.mm, nnn.nn),
        "LOCATION-NAME 3":       (ooo.oo, ppp.pp),
    },
    "30 km": {
        "Ingen vær (kontroll)":  (qqq.qq, rrr.rr),
        "LOCATION-NAME 1":       (sss.ss, ttt.tt),
        "LOCATION-NAME 2":       (uuu.uu, vvv.vv),
        "LOCATION-NAME 3":       (www.ww, xxx.xx),
    },
}

VIS_AVSTANDER = ["10 km", "20 km", "30 km"]

VIS_FORMATER = [
    "Ingen vær (kontroll)",
    "LOCATION-NAME 1",
    "LOCATION-NAME 2",
    "LOCATION-NAME 3",   # ← fjern # for å inkludere igjen
]

TREFF_RADIUS_M = 70   # treffområdets radius (m)

FARGE = {
    "Ingen vær (kontroll)":  "#7f8c8d",
    "LOCATION-NAME 1":    "#2980b9",
    "LOCATION-NAME 2":     "#c0392b",
    "LOCATION-NAME 3":     "#27ae60",
}

TITTEL = "<<name-of-artillery fire management system>> — Predikerte spredningsellipser\nSetermoen"

# ============================================================
# ====== HERUNDER TRENGER DU IKKE Å ENDRE NOE ================
# ============================================================

# Bygg legend-elementer én gang før løkken
legend_patches = [
    mpatches.Patch(facecolor=FARGE[f], edgecolor=FARGE[f], label=f, alpha=0.7)
    for f in VIS_FORMATER if f in FARGE
]
treff_handle = plt.Line2D([0], [0], color="#e67e22", linewidth=2.2,
                           linestyle="--",
                           label=f"Treffområde ({TREFF_RADIUS_M} m radius)")

# Ett separat plot per avstand
for avstand_label in VIS_AVSTANDER:
    fig, ax = plt.subplots(figsize=(7, 7), constrained_layout=True)

    # >>>>>>>>>>>>>>>>  HOVEDTITTEL  <<<<<<<<<<<<<<<<
    # Kommenter ut linjen under for å fjerne hovedtittelen ("ODIN FSS — ..."):
    # fig.suptitle(TITTEL, fontsize=13, fontweight="bold")
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    data = AVSTANDER[avstand_label]
    max_extent = TREFF_RADIUS_M

    for fmt in VIS_FORMATER:
        if fmt not in data:
            continue
        mean_r, mean_c = data[fmt]
        color = FARGE.get(fmt, "black")
        ax.add_patch(Ellipse(
            xy=(0, 0), width=mean_c, height=mean_r,
            facecolor=color, edgecolor="none",
            alpha=0.15, zorder=2,
        ))
        ax.add_patch(Ellipse(
            xy=(0, 0), width=mean_c, height=mean_r,
            facecolor="none", edgecolor=color,
            linewidth=2, zorder=3,
        ))
        max_extent = max(max_extent, mean_r / 2, mean_c / 2)

    ax.add_patch(Circle(
        xy=(0, 0), radius=TREFF_RADIUS_M,
        facecolor="none", edgecolor="#e67e22",
        linewidth=2.2, linestyle="--", zorder=4,
    ))

    half = max_extent * 1.15
    ax.set_xlim(-half, half)
    ax.set_ylim(-half, half)
    ax.set_aspect("equal")
    ax.axhline(0, color="#cccccc", linewidth=0.5, zorder=1)
    ax.axvline(0, color="#cccccc", linewidth=0.5, zorder=1)
    ax.plot(0, 0, "k+", markersize=10, markeredgewidth=1.5, zorder=5)

    # >>>>>>>>>>>>>>>>  UNDERTITTEL (avstand)  <<<<<<<<<<<<<<<<
    # Kommenter ut linjen under for å fjerne avstands-etiketten ("10 km" / "20 km" / "30 km"):
    # ax.set_title(avstand_label, fontsize=12, fontweight="bold")
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    ax.set_xlabel("Cross (sideretning) [m]", fontsize=10)
    ax.set_ylabel("Range (langs skuddbane) [m]", fontsize=10)
    ax.grid(True, linestyle=":", linewidth=0.4, color="#cccccc")

    fig.legend(handles=legend_patches + [treff_handle],
               loc="lower center", ncol=2,
               fontsize=10, framealpha=0.9, bbox_to_anchor=(0.5, -0.12))
    fig.savefig(f"ellipser_{avstand_label.replace(' ', '')}-drone.pdf",
                dpi=180, bbox_inches="tight")

plt.show()
print("Ferdig.")
