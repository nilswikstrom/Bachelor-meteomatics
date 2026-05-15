import os
import time
import requests
from datetime import datetime, timedelta

# Fyll inn ønskede tidspunkt i Zulu-tid (UTC)
# Format: "YYYY-MM-DDTHH:MMZ"
TIDSPUNKT = [
    # "2026-04-10T07:18Z",
    # "2026-04-13T09:24Z",
    # "2026-04-14T06:12Z",
    # "2026-04-15T06:06Z",
    # "2026-04-16T06:06Z",
    # "2026-04-17T06:00Z",
    # "2026-04-20T06:06Z",
    # "2026-04-21T06:06Z",
    # "2026-04-22T06:12Z",
    # "2026-04-23T06:12Z",
    # "2026-04-24T06:06Z",
    # "2026-04-28T11:12Z",
    # "2026-04-29T07:36Z",
    # "2026-04-30T06:38Z",
    "2026-05-05T15:00Z",
    "2026-05-06T03:00Z",
    "2026-05-06T15:00Z",
    "2026-05-07T03:00Z",
    "2026-05-07T15:00Z",
    "2026-05-08T03:00Z",
    "2026-05-08T15:00Z",
    "2026-05-09T03:00Z",
    "2026-05-09T15:00Z",
    "2026-05-10T03:00Z",
    "2026-05-10T15:00Z",
    "2026-05-11T03:00Z",
    "2026-05-11T15:00Z",
]

AREA    = "setermoen"
OUTPUT  = "MetInst/API/metgm_filer"   # Mappe filene lagres i (opprettes automatisk)
HEADERS = {"User-Agent": "Bachelor-Meteomatics niwikstrom@mil.no"}
KJØRETIDER = [3, 9, 15, 21]  # UTC-timer METGM produseres

def nærmeste_kjøretid(dt):
    kjøretid = max((k for k in KJØRETIDER if k <= dt.hour), default=None)
    if kjøretid is None:
        return (dt - timedelta(days=1)).replace(hour=21, minute=0, second=0)
    return dt.replace(hour=kjøretid, minute=0, second=0)

os.makedirs(OUTPUT, exist_ok=True)
total = len(TIDSPUNKT)

print("\n{'='*50}")
print(f"  Område  : {AREA}")
print(f"  Antall  : {total} tidspunkt")
print(f"  Lagres i: {os.path.abspath(OUTPUT)}")
print("{'='*50}\n")

for i, ts in enumerate(TIDSPUNKT, 1):
    ønsket   = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    kjøretid = nærmeste_kjøretid(ønsket)
    api_tid  = kjøretid.strftime("%Y-%m-%dT%H:%M:%SZ")
    filnavn  = f"metgm_{AREA}_{api_tid.replace(':', '').replace('Z', 'UTC')}.gm"
    filsti   = os.path.join(OUTPUT, filnavn)

    print(f"[{i}/{total}] Ønsket tid : {ts}")
    print(f"       Kjøretid   : {api_tid}")
    print(f"       Filnavn    : {filnavn}")

    if os.path.exists(filsti):
        print("       Status     : Allerede lastet ned, hopper over\n")
        continue

    print("       Status     : Laster ned...", end=" ", flush=True)
    resp = requests.get("https://api.met.no/weatherapi/metgm/1.0/",
                        headers=HEADERS, params={"area": AREA, "time": api_tid}, timeout=120)
    if resp.status_code == 200:
        open(filsti, "wb").write(resp.content)
        print(f"OK ({len(resp.content)/1e6:.1f} MB)\n")
    else:
        print(f"FEIL [{resp.status_code}]\n")
    time.sleep(1)

print("Ferdig!")