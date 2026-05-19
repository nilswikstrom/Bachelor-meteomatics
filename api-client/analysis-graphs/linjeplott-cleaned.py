"""
LINJEDIAGRAM — Mean range/cross vs. skytseavstand
--------------------------------------------------
Produserer to separate filer:
  - linjeplott_range.pdf
  - linjeplott_cross.pdf

Krever: pip install matplotlib numpy
"""

import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# ============== LIM INN DINE TALL HER =======================
# ============================================================
# Per format: liste med (mean_range, std_range, mean_cross, std_cross)
# i samme rekkefølge som AVSTANDER under.

AVSTANDER = [10, 20, 30]  # km

DATA = {
    "Ingen vær (kontroll)": [
        # (mean_r, std_r, mean_c, std_c)
        (52.64,  0.0, 20.78, 0.0),   # 10 km
        (133.45, 0.0, 27.58, 0.0),   # 20 km
        (246.86, 0.0, 37.10, 0.0),   # 30 km
    ],
    "METCM målt (drone)": [
        (68.21,  10.04, 22.58,  1.80),
        (201.56, 79.21, 38.70,  9.21),
        (369.62, 155.93, 48.54, 9.90),
    ],
    "METCM (fra METGM)": [
        (58.74,   4.37, 21.36,  0.53),
        (171.18, 36.71, 34.31,  4.22),
        (320.99, 74.61, 60.06, 23.26),
    ],
    "METCM (fra METGC)": [
        (81.69,   49.80, 21.55,  0.46),
        (307.28, 289.27, 38.20,  7.54),
        (583.75, 555.50, 66.64, 22.38),
    ],
}

VIS_FORMATER = [
    # "Ingen vær (kontroll)",
    "METCM målt (drone)",
    "METCM (fra METGM)",
    # "METCM (fra METGC)",   # ← fjern # for å inkludere igjen
]

STYLE = {
    "Ingen vær (kontroll)":  {"color": "#7f8c8d", "linestyle": (0,(4,2))},
    "METCM målt (drone)":    {"color": "#2980b9", "linestyle": "solid"},
    "METCM (fra METGM)":     {"color": "#c0392b", "linestyle": (0,(2,1))},
    "METCM (fra METGC)":     {"color": "#27ae60", "linestyle": (0,(2,1))},
}

TITTEL = "ODIN FSS — Predikert spredning per filkategori\nSetermoen"

# ============================================================
# ====== HERUNDER TRENGER DU IKKE Å ENDRE NOE ================
# ============================================================

# To separate figurer
fig_r, ax_r = plt.subplots(figsize=(7, 5.5), constrained_layout=True)
fig_c, ax_c = plt.subplots(figsize=(7, 5.5), constrained_layout=True)

# >>>>>>>>>>>>>>>>  TITLER  <<<<<<<<<<<<<<<<
# Kommenter ut de to linjene under for å fjerne hovedtittelen på begge figurene:
# fig_r.suptitle(TITTEL, fontsize=13, fontweight="bold")
# fig_c.suptitle(TITTEL, fontsize=13, fontweight="bold")
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

for fmt in VIS_FORMATER:
    if fmt not in DATA:
        continue
    arr = np.array(DATA[fmt])
    x = np.array(AVSTANDER)
    mean_r, std_r, mean_c, std_c = arr[:,0], arr[:,1], arr[:,2], arr[:,3]
    s = STYLE.get(fmt, {"color": "black", "linestyle": "-"})

    ax_r.plot(x, mean_r, marker="o", linewidth=2,
              color=s["color"], linestyle=s["linestyle"], label=fmt)
    ax_r.fill_between(x, mean_r - std_r, mean_r + std_r,
                       color=s["color"], alpha=0.12)

    ax_c.plot(x, mean_c, marker="o", linewidth=2,
              color=s["color"], linestyle=s["linestyle"], label=fmt)
    ax_c.fill_between(x, mean_c - std_c, mean_c + std_c,
                       color=s["color"], alpha=0.12)

# >>>>>>>>>>>>>>>>  UNDERTITLER  <<<<<<<<<<<<<<<<
# Kommenter ut de to set_title-linjene under for å fjerne undertittelen
# på hver figur ("Range (langs skuddbanen)" og "Cross (sideretning)"):
# ax_r.set_title("Range (langs skuddbanen)", fontsize=11)
# ax_c.set_title("Cross (sideretning)", fontsize=11)
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

for ax, ylabel in [(ax_r, "Range (langs skuddbanen) [m]"), (ax_c, "Cross (sideretning) [m]")]:
    ax.set_xlabel("Skytseavstand [km]", fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_xticks(AVSTANDER)
    ax.grid(True, linestyle=":", linewidth=0.5, color="#cccccc")
    ax.legend(fontsize=9, loc="upper left", framealpha=0.9)
    ax.set_ylim(bottom=0)

fig_r.savefig("clean-linjeplott_range.pdf", dpi=180, bbox_inches="tight")
fig_c.savefig("clean-linjeplott_cross.pdf", dpi=180, bbox_inches="tight")
plt.show()
print("Lagret: clean-linjeplott_range.pdf, clean-linjeplott_cross.pdf")