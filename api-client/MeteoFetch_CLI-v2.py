# =============================================================================
# MeteoFetch_test.py
# Fetches METGM files from the Meteomatics API and saves them locally
# Requires: Python 3.6+ (no external packages)
# =============================================================================

import urllib.request
import threading

# ─── LOCATION (lat, lon) ──────────────────────────────────────────────────────
NAME-OF-LOCATION = (lat, lon)

# ─── TIME PERIODS (FROM, TO) ──────────────────────────────────────────────────
STEP = "PT1H"   # PT1H | PT3H | PT6H | PT12H | PT24H

# NAME-OF-LOCATION
PERIODS = [
    ("start-YYYY-MM-DDTHH:MM:SSZ", "end-YYYY-MM-DDTHH:MM:SSZ"),
    ("start-YYYY-MM-DDTHH:MM:SSZ", "end-YYYY-MM-DDTHH:MM:SSZ"),
    # ... etc. as mmany timeslots as you want
]

# =============================================================================

lat, lon = NAME-OF-LOCATION
 
def fetch(from_time, to_time):
    url = f"URL-TO-API/{from_time}--{to_time}:{STEP}/{lat:.4f},{lon:.4f}"
    filename = from_time[:19].replace(":", "-") + "Z_METGM.gm"
    print(f"  Starting : {filename}")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"  Saved    : {filename}")
    except Exception as e:
        print(f"  ERROR ({filename}): {e}")
 
print(f"Location : NAME-OF-LOCATION ({lat}, {lon})")
print(f"Fetching {len(PERIODS)} periods in parallel...\n")
 
threads = [threading.Thread(target=fetch, args=(from_time, to_time))
           for from_time, to_time in PERIODS]
 
for t in threads:
    t.start()
for t in threads:
    t.join()
 
print("\nDone.")
