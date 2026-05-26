import csv

fil = "arbetsmarknadsindex_trend.csv"

with open(fil, "r", encoding="utf-8-sig") as f:
    rader = list(csv.reader(f, delimiter=";"))

ny_header = [
    "Datum", "Roll", "Grupp", "Baseline",
    "Antal annonser", "Index (baseline=100)",
    "Antal tjänster",
    "Nya 7 dagar", "Nya 7 dagar tjänster",
    "Nya 14 dagar", "Nya 14 dagar tjänster",
    "Nya 30 dagar", "Nya 30 dagar tjänster",
    "% heltid", "% tills vidare", "% lang", "% kort",
    "% erfarenhet", "% nystartsjobb",
    "Top 3 regioner (totalt)", "Top 3 regioner (7 dagar)",
    "Top 20 arbetsgivare",
]

rader[0] = ny_header

with open(fil, "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f, delimiter=";").writerows(rader)

print(f"Klar – header uppdaterad med {len(ny_header)} kolumner")
