## Script for converting lat-lon locations to MGRS - Military Grid System
import mgrs

# Installer først: pip install mgrs

m = mgrs.MGRS()

koordinater = [
    # FORMAT: "(LAT, LON),"
    ### LOCATION 1
    (XX.XXXXXXX, YY.YYYYYYY),  # TARGET-NO1
    (XX.XXXXXXX, YY.YYYYYYY),  # TARGET-NO2
    (XX.XXXXXXX, YY.YYYYYYY),  # TARGET-NO3
    (XX.XXXXXXX, YY.YYYYYYY),  # TARGET-NO4
    ### LOCATION 2
    (XX.XXXXXXX, YY.YYYYYYY),  # TARGET-NO1
    # etc. as many locations as you want
]

for lat, lon in koordinater:
    mgrs_kode = m.toMGRS(lat, lon, MGRSPrecision=5)
    print(f"({lat}, {lon}) -> {mgrs_kode}")
