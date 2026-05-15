# =============================================================================
# MeteoFetch_test.py
# Fetches METGM files from the Meteomatics API and saves them locally
# Requires: Python 3.6+ (no external packages)
# =============================================================================

import urllib.request
import threading

# ─── LOCATION (lat, lon) ──────────────────────────────────────────────────────
Setermoen = (68.8, 18.4)

# ─── TIME PERIODS (FROM, TO) ──────────────────────────────────────────────────
STEP = "PT1H"   # PT1H | PT3H | PT6H | PT12H | PT24H

# Setermoen
PERIODS = [
    ("2026-04-10T07:19:30Z", "2026-04-10T19:19:30Z"),
    ("2026-04-13T06:24:38Z", "2026-04-13T18:24:38Z"),
    ("2026-04-14T06:17:36Z", "2026-04-14T18:17:36Z"),
    ("2026-04-15T06:09:53Z", "2026-04-15T18:09:53Z"),
    ("2026-04-16T06:09:08Z", "2026-04-16T18:09:08Z"),
    ("2026-04-17T06:02:51Z", "2026-04-17T18:02:51Z"),
    ("2026-04-20T06:08:07Z", "2026-04-20T18:08:07Z"),
    ("2026-04-21T06:06:54Z", "2026-04-21T18:06:54Z"),
    ("2026-04-22T06:16:46Z", "2026-04-22T18:16:46Z"),
    ("2026-04-23T06:12:59Z", "2026-04-23T18:12:59Z"),
    ("2026-04-24T06:07:32Z", "2026-04-24T18:07:32Z"),
    ("2026-04-28T11:15:37Z", "2026-04-28T23:15:37Z"),
    ("2026-04-29T07:37:20Z", "2026-04-29T19:37:20Z"),
]

# =============================================================================

lat, lon = Setermoen
 
def fetch(from_time, to_time):
    url = f"https://mil.meteomatics.com/metgm/{from_time}--{to_time}:{STEP}/{lat:.4f},{lon:.4f}"
    filename = from_time[:19].replace(":", "-") + "Z_METGM.gm"
    print(f"  Starting : {filename}")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"  Saved    : {filename}")
    except Exception as e:
        print(f"  ERROR ({filename}): {e}")
 
print(f"Location : Setermoen ({lat}, {lon})")
print(f"Fetching {len(PERIODS)} periods in parallel...\n")
 
threads = [threading.Thread(target=fetch, args=(from_time, to_time))
           for from_time, to_time in PERIODS]
 
for t in threads:
    t.start()
for t in threads:
    t.join()
 
print("\nDone.")