import mgrs

# Installer først: pip install mgrs

m = mgrs.MGRS()

koordinater = [
    ### Setermoen
    # (68.8, 18.4),
    # (69.1, 15.7),  # Andøya
    # (68.8332,16.5766),  # Harstad
    # ## Utgangsposisjoner
    # (68.82255565534426, 18.314766024626415), # Setermoen
    # (69.1397568, 15.6806463),  # Andøya
    # (68.5815180, 16.8414712),  # Harstad
    # ## Målposisjon
    # ### Setermoen targets
    # (68.7598473, 18.4982224),  # AA0001
    # (68.6984561, 18.6753170),  # AA0002
    # (68.6280492, 18.8793296),  # AA0003
    # (68.5739018, 19.0305251),  # AA0004
    # ### Andøya targets
    # (69.0512567, 15.7229823),  # BB0001
    # (68.9584923, 15.7670021),  # BB0002
    # (68.8737840, 15.8068463),  # BB0003
    # ### Harstad targets
    # (68.4367712, 17.3864176),  # CC0001
    # (68.4418522, 17.4413815),  # CC0002
    # (68.4282947, 17.4245494),  # CC0003
    (68.6274734, 17.0642882),  # Firing pos NARVIK 2
]

for lat, lon in koordinater:
    mgrs_kode = m.toMGRS(lat, lon, MGRSPrecision=5)
    print(f"({lat}, {lon}) -> {mgrs_kode}")