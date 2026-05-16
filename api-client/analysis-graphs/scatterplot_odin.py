"""
Scatterplot av predikert ellipse fra ODIN.

Genererer to figurer:
  1. Hovedplot:    Alle skytinger samlet i ett plot.
  2. Per-lokasjon: Tre subplots (Setermoen, Andøya, Narvik) i én figur.

X-akse: missdistance_range  (ellipse-diameter i lengde)
Y-akse: missdistance_cross  (ellipse-diameter i bredde)

Farge:  værkilde (Drone, METGM, METGC, ICAO)
Form:   måldistanse (10/20/30 km for hovedstudien, ett felles symbol for Narvik)

KONFIGURASJON ligger øverst i scriptet -- juster der.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ============================================================================
# KONFIGURASJON
# ============================================================================

FILE = "/home/yuki/Downloads/testmatrise.xlsx"

# Ta med høybane i plottet? False = kun lavbane (anbefalt for hovedanalyse)
INCLUDE_HIGH = False

# Inkluder ICAO ("no weather") som referansekilde?
INCLUDE_ICAO = True

# Filtrer på tidsintervall etter måling (i minutter).
# Sett til None for å ta med alle tider, eller for eksempel [30].
TIME_FILTER = None

# Lagre figurene?
SAVE_MAIN = "scatter_odin_alle_skytinger.png"
SAVE_LOC  = "scatter_odin_per_lokasjon.png"

# ============================================================================
# DATAINNLESNING
# ============================================================================

SOURCES = {
    "Drone (Meteomatics)": 'METCM (Meteomatics)',
    "METGM":              'METCM (from METGM)',
    "METGC":              'METCM (from METGC)',
    "ICAO (no weather)":  'ICAO "no weather"',
}

TARGET_DIST = {
    "AA0001": 10, "AA0002": 20, "AA0003": 30,
    "BB0001": 10, "BB0002": 20, "BB0003": 30,
    "CC0001": 25, "CC0002": 26, "CC0003": 27,
}

TARGET_LOC = {
    "AA0001": "Setermoen", "AA0002": "Setermoen", "AA0003": "Setermoen",
    "BB0001": "Andøya",    "BB0002": "Andøya",    "BB0003": "Andøya",
    "CC0001": "Narvik",    "CC0002": "Narvik",    "CC0003": "Narvik",
}

WEATHER_LOC_MAP = {
    "CM pos. Setermoen": "Setermoen",
    "CM pos. Andøya":    "Andøya",
    "CM pos. Harstad":   "Narvik",
}


def load_sheet(sheet_name):
    df = pd.read_excel(FILE, sheet_name=sheet_name, header=[0, 1])
    df.columns = [
        '_'.join([str(c) for c in col if 'Unnamed' not in str(c)]).strip('_')
        for col in df.columns
    ]
    for col in ['Angle of fire', 'Weather pos.', 'Target name']:
        if col in df.columns:
            df[col] = df[col].ffill()
    return df


def parse_dtg(s):
    try:
        return pd.to_datetime(str(s).strip(), format='%d%H%MZ %b %y')
    except Exception:
        return pd.NaT


frames = []
for label, sheet in SOURCES.items():
    if label == "ICAO (no weather)" and not INCLUDE_ICAO:
        continue
    df = load_sheet(sheet)
    df['source_label'] = label
    frames.append(df)

data = pd.concat(frames, ignore_index=True, sort=False)

for col in ['missdistance_range', 'missdistance_cross']:
    data[col] = pd.to_numeric(data[col], errors='coerce')

data['weather_t'] = data['Timestamps_Weather DTG'].apply(parse_dtg)
data['fire_t']    = data['Timestamps_Fire DTG'].apply(parse_dtg)
data['delta_min'] = (data['fire_t'] - data['weather_t']).dt.total_seconds() / 60

data['dist_km'] = data['Target name'].map(TARGET_DIST)
data['location'] = data['Weather pos.'].map(WEATHER_LOC_MAP)
data['location'] = data['location'].fillna(data['Target name'].map(TARGET_LOC))

if 'no. of rounds' in data.columns:
    data = data[data['no. of rounds'].isna()]

if not INCLUDE_HIGH and 'Angle of fire' in data.columns:
    data = data[data['Angle of fire'] != 'High']

if TIME_FILTER is not None:
    data = data[data['delta_min'].isin(TIME_FILTER)]

data = data.dropna(subset=['missdistance_range', 'missdistance_cross', 'dist_km'])

print(f"Antall datapunkter etter filtrering: {len(data)}")

# ============================================================================
# PLOT-STIL
# ============================================================================

SOURCE_COLORS = {
    "Drone (Meteomatics)": "#1f77b4",
    "METGM":               "#2ca02c",
    "METGC":               "#d62728",
    "ICAO (no weather)":   "#7f7f7f",
}


def dist_marker(dist):
    """Form pr distanse. Narvik (25/26/27 km) deler samme diamant."""
    if dist == 10:
        return "o"
    if dist == 20:
        return "s"
    if dist == 30:
        return "^"
    return "D"


def make_scatter(ax, df, title=None):
    for src_label, src_color in SOURCE_COLORS.items():
        src_data = df[df['source_label'] == src_label]
        for dist in sorted(src_data['dist_km'].unique()):
            sub = src_data[src_data['dist_km'] == dist]
            if len(sub) > 0:
                ax.scatter(
                    sub['missdistance_range'],
                    sub['missdistance_cross'],
                    c=src_color, marker=dist_marker(dist),
                    s=65, alpha=0.6,
                    edgecolors='black', linewidth=0.5,
                )
    ax.axvline(70, color='black', linestyle=':', alpha=0.6, linewidth=1)
    ax.set_xlabel('Ellipse-diameter, lengde [m]')
    ax.set_ylabel('Ellipse-diameter, bredde [m]')
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.3)


def make_legend(ax, df):
    src_handles = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=c,
               markeredgecolor='black', markersize=9, label=name)
        for name, c in SOURCE_COLORS.items()
        if name in df['source_label'].unique()
    ]
    dist_legend_specs = [
        (10, "o", "10 km"),
        (20, "s", "20 km"),
        (30, "^", "30 km"),
        (25, "D", "Narvik (25-27 km)"),
    ]
    dist_handles = [
        Line2D([0], [0], marker=m, color='w', markerfacecolor='gray',
               markeredgecolor='black', markersize=9, label=label)
        for d, m, label in dist_legend_specs
        if d in df['dist_km'].unique()
    ]
    legend1 = ax.legend(handles=src_handles, title='Vaerkilde',
                        loc='upper left', bbox_to_anchor=(1.02, 1.0),
                        fontsize=9, title_fontsize=10)
    ax.add_artist(legend1)
    ax.legend(handles=dist_handles, title='Maaldistanse',
              loc='upper left', bbox_to_anchor=(1.02, 0.55),
              fontsize=9, title_fontsize=10)


# ============================================================================
# FIGUR 1: HOVEDPLOT
# ============================================================================

fig, ax = plt.subplots(figsize=(13, 8))
make_scatter(ax, data, title='Predikert ellipse fra ODIN: alle skyteberegninger')
make_legend(ax, data)
if SAVE_MAIN:
    plt.savefig(SAVE_MAIN, dpi=150, bbox_inches='tight')
    print(f"Figur 1 lagret: {SAVE_MAIN}")
plt.close()

# ============================================================================
# FIGUR 2: PER LOKASJON
# ============================================================================

locations = ['Setermoen', 'Andoya', 'Narvik']
loc_keys = ['Setermoen', 'Andøya', 'Narvik']  # for filtering

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for ax, loc_disp, loc_key in zip(axes, locations, loc_keys):
    loc_data = data[data['location'] == loc_key]
    make_scatter(ax, loc_data, title=loc_disp)

all_src = data['source_label'].unique()
src_handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c,
           markeredgecolor='black', markersize=10, label=name)
    for name, c in SOURCE_COLORS.items() if name in all_src
]
dist_legend_specs = [
    (10, "o", "10 km"),
    (20, "s", "20 km"),
    (30, "^", "30 km"),
    (25, "D", "Narvik (25-27 km)"),
]
dist_handles = [
    Line2D([0], [0], marker=m, color='w', markerfacecolor='gray',
           markeredgecolor='black', markersize=10, label=label)
    for d, m, label in dist_legend_specs
    if d in data['dist_km'].unique()
]
all_handles = src_handles + dist_handles
fig.legend(handles=all_handles, ncol=len(all_handles),
           loc='lower center', bbox_to_anchor=(0.5, -0.02),
           fontsize=9, frameon=True)

plt.suptitle('Predikert ellipse fra ODIN per lokasjon',
             fontsize=13, y=1.02)
plt.tight_layout()
if SAVE_LOC:
    plt.savefig(SAVE_LOC, dpi=150, bbox_inches='tight')
    print(f"Figur 2 lagret: {SAVE_LOC}")
plt.close()
