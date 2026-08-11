import csv

def dedup(fil, nyckel_kolumner):
    """
    nyckel_kolumner: lista med kolumnindex som tillsammans identifierar en unik
    rad (t.ex. [0,1] för Datum+Roll, eller [0,1,2] för Datum+Bolag+Region).
    Behåller SISTA raden per unik nyckel (inte första).
    """
    with open(fil, encoding="utf-8-sig") as f:
        rader = list(csv.reader(f, delimiter=";"))
    header = rader[0]
    sedd = {}
    for rad in rader[1:]:
        nyckel = tuple(rad[i] for i in nyckel_kolumner)
        sedd[nyckel] = rad  # skriver över – sista vinner
    rena = [header] + list(sedd.values())
    with open(fil, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerows(rena)
    print(f"{fil}: {len(rader)-1} -> {len(rena)-1} rader")

# Huvudfiler: nyckel = Datum + Roll/Bolag (kolumn 0 och 1)
dedup("arbetsmarknadsindex_trend.csv", [0, 1])
dedup("bemanningsindex_trend.csv", [0, 1])

# Regiondata: nyckel måste inkludera Region också (kolumn 0,1,2), annars räknas
# t.ex. "Academic Work i Skåne" och "Academic Work i Stockholm" som samma rad
# och en av dem skulle raderas av misstag.
# bemanningsindex_regioner_trend.csv: Datum;Bolag;Region;...
dedup("bemanningsindex_regioner_trend.csv", [0, 1, 2])
# arbetsmarknadsindex_regioner_trend.csv: Datum;Roll;Grupp;Region;... (Region är kolumn 3, inte 2)
dedup("arbetsmarknadsindex_regioner_trend.csv", [0, 1, 3])

print("Klart – dubbletter borttagna, senaste data behållen.")
