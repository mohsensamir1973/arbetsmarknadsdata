import csv

fil = "bemanningsindex_trend.csv"

with open(fil, "r", encoding="utf-8-sig") as f:
    rader = list(csv.reader(f, delimiter=";"))

ny_header = [
    "Datum", "Bolag",
    "Antal annonser", "Antal tjanster",
    "Nya annonser 30d", "Nya tjanster 30d",
    "Nya annonser 14d", "Nya tjanster 14d",
    "Nya annonser 7d", "Nya tjanster 7d",
    "Aktivitetstakt % (14d)",
    "% heltid", "% tills vidare", "% lang", "% kort",
    "% erfarenhet kravs",
    "Top 3 regioner (totalt)", "Top 3 regioner (14 dagar)",
    "Top 3 yrkesomraden", "Top 5 yrkesgrupper",
]

rader[0] = ny_header

with open(fil, "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f, delimiter=";").writerows(rader)

print(f"Klar – bemanningsindex header uppdaterad med {len(ny_header)} kolumner")
