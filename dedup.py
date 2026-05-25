import csv

def dedup(fil):
    with open(fil, encoding="utf-8-sig") as f:
        rader = list(csv.reader(f, delimiter=";"))
    header = rader[0]
    # Behåll SISTA raden per datum+roll (inte första)
    sedd = {}
    for rad in rader[1:]:
        nyckel = (rad[0], rad[1])
        sedd[nyckel] = rad  # skriver över – sista vinner
    rena = [header] + list(sedd.values())
    with open(fil, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerows(rena)
    print(f"{fil}: {len(rader)-1} -> {len(rena)-1} rader")

dedup("arbetsmarknadsindex_trend.csv")
dedup("bemanningsindex_trend.csv")
print("Klart – dubbletter borttagna, senaste data behållen.")
