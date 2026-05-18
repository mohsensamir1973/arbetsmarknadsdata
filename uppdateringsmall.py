"""
Uppdateringsmall – genererar sajtuppdatering från CSV-data
===========================================================
Placeras i: Documents\Arbetsmarknadsindex\
Kör: python uppdateringsmall.py

Producerar färdig text för:
1. Hero-korten (4 faktakort med toppregion)
2. Marknadspuls (alla 10 roller)
3. Insikter (automatiskt genererade observationer)
"""

import csv
import os
from datetime import datetime
from collections import defaultdict

HUVUDFIL  = "arbetsmarknadsindex_trend.csv"
REGIOFIL  = "arbetsmarknadsindex_regioner_trend.csv"

def läs_senaste(fil, nyckel="Roll"):
    """Läser senaste raden per roll från CSV."""
    data = {}
    with open(fil, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            data[row[nyckel]] = row
    return data

def läs_baseline(fil):
    """Läser baseline-värden från CSV."""
    baseline = {}
    with open(fil, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if row.get("Baseline", "").lower() in ("true", "1", "yes"):
                try:
                    baseline[row["Roll"]] = int(row["Antal annonser"])
                except:
                    pass
    return baseline

ROLL_LABELS = {
    "Sjuksköterska":        "sjuksköterskeannonser",
    "Systemutvecklare":     "systemutvecklarannonser",
    "Lagerarbetare":        "lagerarbetarannonser",
    "Business Controller":  "Business Controller-annonser",
    "Kundtjänstmedarbetare":"kundtjänstannonser",
    "Ekonomiassistent":     "ekonomiassistentannonser",
    "Account Manager":      "Account Manager-annonser",
    "Mekanikkonstruktör":   "mekanikkonstruktörsannonser",
    "Elingenjör":           "elingenjörsannonser",
    "Undersköterska":       "undersköterskannonser",
}

REGION_KORTNAMN = {
    "Stockholms län":          "Stockholm",
    "Västra Götalands län":    "VGR",
    "Skåne län":               "Skåne",
    "Östergötlands län":       "Östergötland",
    "Uppsala län":             "Uppsala",
    "Jönköpings län":          "Jönköping",
    "Hallands län":            "Halland",
    "Örebro län":              "Örebro",
    "Västmanlands län":        "Västmanland",
    "Dalarnas län":            "Dalarna",
    "Norrbottens län":         "Norrbotten",
    "Västerbottens län":       "Västerbotten",
    "Gävleborgs län":          "Gävleborg",
    "Västernorrlands län":     "Västernorrland",
    "Kronobergs län":          "Kronoberg",
    "Kalmar län":              "Kalmar",
    "Blekinge län":            "Blekinge",
    "Gotlands län":            "Gotland",
    "Södermanlands län":       "Södermanland",
    "Värmlands län":           "Värmland",
    "Jämtlands län":           "Jämtland",
}

def läs_alla_rader(fil, nyckel="Roll"):
    """Läser alla rader från CSV, grupperade per nyckel."""
    data = defaultdict(list)
    with open(fil, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            data[row[nyckel]].append(row)
    return data

def hitta_topp_region(roll, regioner_data):
    """Hittar regionen med flest nya annonser senaste 7 dagarna."""
    rader = regioner_data.get(roll, [])
    # Ta bara senaste datum
    if not rader:
        return "–", 0
    senaste_datum = max(r["Datum"] for r in rader)
    senaste = [r for r in rader if r["Datum"] == senaste_datum]
    bäst = max(senaste, key=lambda r: int(r.get("Nya 7 dagar", 0) or 0))
    region = bäst["Region"].replace(" län", "")
    antal = int(bäst.get("Nya 7 dagar", 0) or 0)
    return region, antal

def beräkna_index(roll, antal, baseline):
    if roll not in baseline or baseline[roll] == 0:
        return "100 (baseline)"
    index = round(antal / baseline[roll] * 100, 1)
    diff = round(index - 100, 1)
    sign = "+" if diff >= 0 else ""
    return f"{index} ({sign}{diff})"

def aktivitetstakt(nya, totalt):
    if totalt == 0:
        return 0
    return round(nya / totalt * 100, 1)

# ── Huvud ────────────────────────────────────────────────────────────

if not os.path.exists(HUVUDFIL):
    print(f"FEL: {HUVUDFIL} saknas.")
    exit()

senaste    = läs_senaste(HUVUDFIL)
baseline   = läs_baseline(HUVUDFIL)
regioner   = läs_alla_rader(REGIOFIL)
datum      = list(senaste.values())[0]["Datum"] if senaste else "okänt"
nästa      = "26 maj 2026"  # uppdatera manuellt varannan måndag

print("=" * 65)
print("UPPDATERINGSMALL – ARBETSMARKNADSDATA.SE")
print(f"Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Baserad på mätning: {datum}")
print("=" * 65)

# ── 1. HERO-KORTEN ───────────────────────────────────────────────────
print("\n── HERO-KORTEN ─────────────────────────────────────────────\n")

# Välj de 4 mest talande rollerna baserat på nya 7 dagar
hero_roller = ["Sjuksköterska", "Systemutvecklare", "Lagerarbetare", "Business Controller"]

for roll in hero_roller:
    if roll not in senaste:
        continue
    d = senaste[roll]
    nya_7d = int(d.get("Nya 7 dagar", 0) or 0)
    topp_region, topp_antal = hitta_topp_region(roll, regioner)

    label = ROLL_LABELS.get(roll, f"{roll.lower()}annonser")
    region_kort = REGION_KORTNAMN.get(topp_region + " län", topp_region)

    print(f"KORT: {roll}")
    print(f"  Siffra:    {nya_7d}")
    print(f"  Label:     Nya {label} på 7 dagar")
    print(f"  Undertext: Flest nya i {region_kort} — {topp_antal}")
    print()

# ── 2. MARKNADSPULS ──────────────────────────────────────────────────
print("── MARKNADSPULS ────────────────────────────────────────────\n")

grupper = {
    "Volym / cykel":             ["Kundtjänstmedarbetare", "Ekonomiassistent", "Lagerarbetare"],
    "Framåtblickande signal":    ["Account Manager", "Business Controller", "Systemutvecklare"],
    "Struktur / transformation": ["Mekanikkonstruktör", "Elingenjör"],
    "Strukturell brist":         ["Sjuksköterska", "Undersköterska"],
}

for grupp, roller in grupper.items():
    print(f"{grupp.upper()}")
    for roll in roller:
        if roll not in senaste:
            continue
        d = senaste[roll]
        totalt  = int(d.get("Antal annonser", 0) or 0)
        tjanster = int(d.get("Antal tjänster", 0) or 0)
        nya_7d  = int(d.get("Nya 7 dagar", 0) or 0)
        nya_14d = int(d.get("Nya 14 dagar", 0) or 0)
        takt    = aktivitetstakt(nya_7d, totalt)
        index   = beräkna_index(roll, totalt, baseline)

        print(f"  {roll:<28} {totalt:>5} ann / {tjanster:>6} tj")
        print(f"  {'':28} Nya 7d: {nya_7d} | Nya 14d: {nya_14d} | Aktivitetstakt: {takt}%")
        print(f"  {'':28} Index: {index}")
    print()

# ── 3. INSIKTER ──────────────────────────────────────────────────────
print("── AUTOMATISKA INSIKTER ────────────────────────────────────\n")

# Högst aktivitetstakt
takter = []
for roll, d in senaste.items():
    totalt = int(d.get("Antal annonser", 0) or 0)
    nya_7d = int(d.get("Nya 7 dagar", 0) or 0)
    if totalt > 0:
        takter.append((roll, aktivitetstakt(nya_7d, totalt), nya_7d, totalt))

takter.sort(key=lambda x: x[1], reverse=True)
högst = takter[0]
lägst = takter[-1]

print(f"1. HÖGST AKTIVITETSTAKT: {högst[0]}")
print(f"   {högst[2]} nya av {högst[3]} totalt = {högst[1]}%")
print()
print(f"2. LÄGST AKTIVITETSTAKT: {lägst[0]}")
print(f"   {lägst[2]} nya av {lägst[3]} totalt = {lägst[1]}%")
print()

# Högst tjänster/annons ratio
ratios = []
for roll, d in senaste.items():
    totalt   = int(d.get("Antal annonser", 0) or 0)
    tjanster = int(d.get("Antal tjänster", 0) or 0)
    if totalt > 0:
        ratios.append((roll, round(tjanster / totalt, 1), tjanster, totalt))

ratios.sort(key=lambda x: x[1], reverse=True)
högst_ratio = ratios[0]
print(f"3. HÖGST TJÄNSTER/ANNONS: {högst_ratio[0]}")
print(f"   {högst_ratio[2]} tjänster / {högst_ratio[3]} annonser = {högst_ratio[1]}x per annons")

# ── 4. FOOTER-TEXT ───────────────────────────────────────────────────
try:
    d = datetime.strptime(datum, "%Y-%m-%d")
    månader = ["januari","februari","mars","april","maj","juni",
               "juli","augusti","september","oktober","november","december"]
    datum_fmt = f"{d.day} {månader[d.month-1]} {d.year}"
except:
    datum_fmt = datum

print()
print("── FOOTER/DATUM ────────────────────────────────────────────\n")
print(f"Senast publicerat: {datum_fmt}")
print(f"Nästa publicering: {nästa} kl 15:00")
print(f"Underrubrik datum: {datum_fmt} — jobbefterfrågan inom lager, kundtjänst, sälj, tech, industri och vård")

