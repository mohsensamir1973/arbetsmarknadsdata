# -*- coding: utf-8 -*-
"""
signalmotor.py

Regelbaserad signaldetektor för arbetsmarknadsdata.se.

Syfte: automatiskt upptäcka statistiskt ovanliga händelser i den dagliga
datan, utan manuell redaktionell text. Varje signal är spårbar till en
exakt regel och siffra - ingen fri tolkning.

Körs som steg i den dagliga pipelinen, EFTER dedup.py och EFTER att alla
trend-CSV:er är uppdaterade för dagen, FÖRE git push.

Output: signaler_log.csv (en rad per detekterad signal, skrivs om varje
körning för dagens datum - se dubblettskydd i kor_signalmotor())
Kolumner: Datum;Typ;Bolag;Varde;Beskrivning;Styrka;Kalla

(OBS: kolumnen heter "Bolag" av historiska skäl men innehåller namnet på
VILKEN ENTITET signalen gäller - kan vara ett bolag, en signalroll, eller
"Hela marknaden". Byts inte till "Entitet" eftersom frontend redan läser
kolumnnamnet "Bolag" för att markera namnet i texten.)

NIVÅER SOM SCANNAS (tillagt 2026-08-10):
1. Bolag (bemanningsindex_trend.csv) - alla fem signaltyper
2. Signalroller (arbetsmarknadsindex_trend.csv) - tre kärnsignaler
   (stark rörelse, extremvärde, sinande nyinflöde) + regional nyetablering.
   Andelsskifte (marknadsandel) gäller bara bolag - har ingen direkt
   motsvarighet på rollnivå ännu (extern andel/vem-rekryterar-skifte är
   en möjlig framtida signal, kräver tolkning av "Top 20 arbetsgivare"-
   fältet - inte byggt än).
3. Hela marknaden (summan av alla 30 bolag) - stark rörelse + extremvärde
   på totalnivå, en ny nivå utöver enskilda bolag/roller.

Designprincip (viktigt, ändra inte utan att förstå varför):
- Trösklar är PER ENTITET (percentil av entitetens egen historik), inte
  en fast procentsats för alla. Analys 2026-08-09 visade att en fast 15%-
  regel systematiskt missar stora bolag (normal veckovolatilitet 2-5%)
  och överflaggar små bolag (normal veckovolatilitet 11-14%).
- Kräver minst MIN_HISTORIK_DAGAR dagars historik per entitet innan en
  percentil-baserad signal kan triggas, annars är percentilen inte
  tillförlitlig.
- "Nytt extremvärde" och "Regional nyetablering" är binära fakta och
  kräver ingen kalibrering.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# ============================================================
# KONFIGURATION
# ============================================================

BEMANNING_CSV = "bemanningsindex_trend.csv"
BEMANNING_REGIONER_CSV = "bemanningsindex_regioner_trend.csv"
ARBETSMARKNAD_CSV = "arbetsmarknadsindex_trend.csv"
ARBETSMARKNAD_REGIONER_CSV = "arbetsmarknadsindex_regioner_trend.csv"
SIGNAL_LOG_CSV = "signaler_log.csv"

MIN_HISTORIK_DAGAR = 42          # ~6 veckor innan percentil-signaler aktiveras
PERCENTIL_STARK_RORELSE = 0.90   # topp 10% av entitetens egna veckorörelser
PERCENTIL_LAG_NYANNONSERING = 0.10  # botten 10% av entitetens egen nyannonsering
STOCK_STABIL_GRANS_PCT = 5.0     # aktiva annonser ±5% räknas som "stabilt"
KOMMUN_MIN_NY_AKTIVITET = 15  # kalibrerat 2026-08-13 mot faktisk fördelning: median=8, 75:e percentilen=18
ANDELSSKIFTE_MIN_PP = 1.0        # ±1 procentenhet marknadsandel över 30 dagar
MIN_AKTIVA_FOR_SIGNAL = 10       # entitet under denna nivå ger för brusiga %-tal
MARKNADSNIVA_STYRKA_FAKTOR = 2.0  # marknadsnivå-signaler väger tyngre än enskilda entiteter
REGIONAL_NIVA_STYRKA_FAKTOR = 1.3  # regionsignaler väger något tyngre än enskilda bolag/roller

KALLA = "Arbetsförmedlingens öppna API"
BASELINE_TEXT = "20 maj 2026"
BASELINE_DATUM = pd.Timestamp("2026-05-20")
# Region- och kommundata spårade bara EN geografi per bolag (ingen riktig
# uppdelning) fram till 2026-06-05 - upptäckt 2026-08-13 (rader/dag gick
# från ~30 till 350+ den 6 juni). All jämförelse mot "historik" för
# regioner/kommuner ska starta härifrån, annars jämförs mot en konstgjort
# låg period som bara fångade ett enda bolags data.
REGION_STABIL_DATUM = pd.Timestamp("2026-06-06")


def ladda_csv(path, sort_cols):
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    df["Datum"] = pd.to_datetime(df["Datum"])
    df = df.sort_values(sort_cols).reset_index(drop=True)
    return df


# ============================================================
# SIGNAL 1: STARK RÖRELSE V/V (per-entitet percentil)
# Fungerar på bolag OCH roller - samma kolumn "Antal annonser" i båda.
# ============================================================

def detektera_stark_rorelse(df, dagens_datum, entity_col="Bolag"):
    """
    Flaggar entiteter (bolag eller roller) vars vecka-till-vecka-förändring
    (7 dagar) ligger bland de 10% starkaste rörelserna i ENTITETENS EGEN
    historik sedan mätstart.
    """
    signaler = []
    for namn, g in df.groupby(entity_col):
        g = g.sort_values("Datum").reset_index(drop=True)
        if len(g) < MIN_HISTORIK_DAGAR + 7:
            continue
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue

        g["pct_7d"] = (
            g["Antal annonser"] - g["Antal annonser"].shift(7)
        ) / g["Antal annonser"].shift(7) * 100
        g["pct_7d"] = g["pct_7d"].replace([np.inf, -np.inf], np.nan)

        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty or pd.isna(rad_idag["pct_7d"].values[0]):
            continue

        varde_idag = rad_idag["pct_7d"].values[0]
        historik = g[g["Datum"] < dagens_datum]["pct_7d"].dropna()
        if len(historik) < MIN_HISTORIK_DAGAR:
            continue

        troskel = historik.abs().quantile(PERCENTIL_STARK_RORELSE)
        if abs(varde_idag) >= troskel and troskel > 0:
            riktning = "ökat" if varde_idag > 0 else "minskat"
            styrka = abs(varde_idag) / troskel
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Stark rörelse v/v",
                "Bolag": namn,
                "Varde": round(varde_idag, 1),
                "Beskrivning": (
                    f"{namn} har {riktning} {abs(varde_idag):.0f}% i aktiva "
                    f"annonser senaste 7 dagarna – en av de starkaste "
                    f"veckorörelserna sedan mätstart."
                ),
                "Styrka": round(styrka, 2),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 2: NYTT EXTREMVÄRDE SEDAN MÄTSTART (binärt, ingen kalibrering)
# Fungerar på bolag OCH roller.
# ============================================================

def detektera_extremvarde(df, dagens_datum, entity_col="Bolag"):
    """
    Upptäcker nya högsta/lägsta nivåer sedan mätstart.

    VECKODAGSJUSTERAT (tillagt 2026-08-13): måndagar ligger systematiskt
    ~5% lägre än andra veckodagar (bekräftat 2026-08-10 - se analys av
    bemanningsindex_trend.csv). En rak jämförelse av råvärden mot hela
    historiken riskerar att flagga en helt normal måndag som "nytt lägsta"
    bara för att den råkar vara lägre än söndagar/fredagar i jämförelsen,
    inte för att något faktiskt förändrats.

    Fix: varje värde normaliseras mot sin egen veckodags typiska nivå
    innan jämförelsen (inte genom att bara jämföra mot samma veckodag,
    vilket skulle kräva ~7x mer historik än vi har och i praktiken stänga
    av signalen i månader). Den RAPPORTERADE siffran är fortfarande
    råvärdet - bara BESLUTET om det är ett extremvärde är justerat.
    """
    signaler = []
    for namn, g in df.groupby(entity_col):
        g = g.sort_values("Datum").reset_index(drop=True)
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue
        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue
        varde_idag = rad_idag["Antal annonser"].values[0]

        historik_df = g[g["Datum"] < dagens_datum].copy()
        if len(historik_df) < MIN_HISTORIK_DAGAR:
            continue
        snitt = round(historik_df["Antal annonser"].mean())
        veckor = max(1, round((dagens_datum - BASELINE_DATUM).days / 7))

        # Veckodagsjustering
        historik_df["veckodag"] = historik_df["Datum"].dt.dayofweek
        veckodag_snitt = historik_df.groupby("veckodag")["Antal annonser"].mean()
        overall_snitt = historik_df["Antal annonser"].mean()

        def justera(varde, veckodag):
            vs = veckodag_snitt.get(veckodag, overall_snitt)
            if vs <= 0:
                return varde
            return varde * (overall_snitt / vs)

        historik_justerat = historik_df.apply(lambda r: justera(r["Antal annonser"], r["veckodag"]), axis=1)
        varde_idag_justerat = justera(varde_idag, dagens_datum.dayofweek)

        if varde_idag_justerat > historik_justerat.max():
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Nytt extremvärde",
                "Bolag": namn,
                "Varde": int(varde_idag),
                "Beskrivning": (
                    f"{namn} har idag {int(varde_idag)} aktiva annonser – "
                    f"högsta nivån på de {veckor} veckor vi mätt hittills (sedan {BASELINE_TEXT}), "
                    f"snitt över perioden: {snitt}."
                ),
                "Styrka": 1.0,
                "Kalla": KALLA,
            })
        elif varde_idag_justerat < historik_justerat.min():
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Nytt extremvärde",
                "Bolag": namn,
                "Varde": int(varde_idag),
                "Beskrivning": (
                    f"{namn} har idag {int(varde_idag)} aktiva annonser – "
                    f"lägsta nivån på de {veckor} veckor vi mätt hittills (sedan {BASELINE_TEXT}), "
                    f"snitt över perioden: {snitt}."
                ),
                "Styrka": 1.0,
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 3: SINANDE NYINFLÖDE (aktiva stabilt, nyannonsering historiskt lågt)
# Fungerar på bolag OCH roller - men kolumnnamnet för "nya senaste 7d"
# skiljer sig mellan datakällorna, därför parametriserat.
# ============================================================

def detektera_sinande_nyinflode(df, dagens_datum, entity_col="Bolag", nya_7d_col="Nya annonser 7d"):
    signaler = []
    for namn, g in df.groupby(entity_col):
        g = g.sort_values("Datum").reset_index(drop=True)
        if len(g) < MIN_HISTORIK_DAGAR + 7:
            continue
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue

        g["pct_7d_aktiva"] = (
            g["Antal annonser"] - g["Antal annonser"].shift(7)
        ) / g["Antal annonser"].shift(7) * 100

        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue

        pct_aktiva = rad_idag["pct_7d_aktiva"].values[0]
        nya_7d_idag = pd.to_numeric(rad_idag[nya_7d_col], errors="coerce").values[0]
        if pd.isna(pct_aktiva) or pd.isna(nya_7d_idag):
            continue
        if abs(pct_aktiva) > STOCK_STABIL_GRANS_PCT:
            continue

        historik_nya = pd.to_numeric(
            g[g["Datum"] < dagens_datum][nya_7d_col], errors="coerce"
        ).dropna()
        if len(historik_nya) < MIN_HISTORIK_DAGAR:
            continue

        troskel = historik_nya.quantile(PERCENTIL_LAG_NYANNONSERING)
        if nya_7d_idag <= troskel:
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Sinande nyinflöde",
                "Bolag": namn,
                "Varde": int(nya_7d_idag),
                "Beskrivning": (
                    f"{namn} har stabil annonsvolym (±{abs(pct_aktiva):.0f}% "
                    f"senaste 7 dagarna), men bara {int(nya_7d_idag)} nya annonser senaste "
                    f"7 dagarna – bland de lägsta nyinflödena sedan mätstart. Om trenden "
                    f"håller minskar den totala volymen inom kommande veckor."
                ),
                "Styrka": round(1 - (nya_7d_idag / (troskel + 1)), 2),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 4: REGIONAL NYETABLERING (0 -> minst 5 annonser på 30 dagar)
# Fungerar på bolag+region OCH roll+region.
# ============================================================

def detektera_kommun_aktivitet(df_kommuner, dagens_datum, alla_datum):
    """
    Ersätter den gamla "Regional nyetablering" (länsnivå, per bolag) - den
    visade sig ALDRIG ha triggat i hela historiken (verifierat 2026-08-13,
    backtest mot all data), eftersom ett enskilt läns geografi är för
    grovkornig för att en enskild etablering ska synas som 0->N.

    Kommunnivå, TOTALT över alla 30 bolag (inte per bolag) - kalibrerat
    mot faktisk fördelning av kommunaktivitet. Medvetet neutralt namngiven
    ("ny/avslutad aktivitet", inte "nyetablering") eftersom vi inte kan
    avgöra om en ökning beror på ett enskilt kontrakt eller en permanent
    etablering - bara att aktiviteten börjat eller upphört.

    VIKTIGT (fix 2 av 2, 2026-08-13): en ren "jämför mot igår"-lösning
    missade gradvisa förändringar (som Trollhättans uppgång 4->20 över två
    veckor - aldrig ett enda stort dagshopp). Rätt lösning behåller
    30-dagarsjämförelsen (den fångar gradvisa trender) men triggar bara
    signalen den FÖRSTA dagen villkoret blir sant - genom att även
    kontrollera att villkoret INTE redan var sant igår. Självbegränsande
    utan att tappa förmågan att se gradvisa förändringar.
    Kräver även samma MIN_HISTORIK_DAGAR-mognad som resten av signalmotorn
    (42 dagar sedan mätstart) innan den börjar trigga - annars räknas
    pipelinens egen uppstartsperiod (då stora städer som Stockholm och
    Göteborg också såg ut att "dyka upp" bara för att kommundata-
    insamlingen fortfarande stabiliserades) som falska signaler.
    """
    if (dagens_datum - BASELINE_DATUM).days < MIN_HISTORIK_DAGAR:
        return []

    totalt = df_kommuner.groupby(["Datum", "Kommun"])["Antal annonser"].sum().reset_index()
    alla_kommuner = totalt["Kommun"].unique()
    grid = pd.MultiIndex.from_product([alla_datum, alla_kommuner], names=["Datum", "Kommun"]).to_frame(index=False)
    komplett = grid.merge(totalt, on=["Datum", "Kommun"], how="left")
    komplett["Antal annonser"] = komplett["Antal annonser"].fillna(0)

    def varde_pa_datum(g, datum):
        rad = g[g["Datum"] == datum]
        return rad["Antal annonser"].values[0] if not rad.empty else None

    signaler = []
    for kommun, g in komplett.groupby("Kommun"):
        g = g.sort_values("Datum").reset_index(drop=True)

        varde_idag = varde_pa_datum(g, dagens_datum)
        if varde_idag is None:
            continue
        igar = dagens_datum - pd.Timedelta(days=1)
        varde_igar = varde_pa_datum(g, igar)
        if varde_igar is None:
            continue

        def varde_30d_fore(datum):
            hist = g[g["Datum"] <= datum - pd.Timedelta(days=30)]["Antal annonser"]
            return hist.iloc[-1] if not hist.empty else None

        fore_idag = varde_30d_fore(dagens_datum)
        fore_igar = varde_30d_fore(igar)
        if fore_idag is None or fore_igar is None:
            continue

        villkor_ny_idag = fore_idag == 0 and varde_idag >= KOMMUN_MIN_NY_AKTIVITET
        villkor_ny_igar = fore_igar == 0 and varde_igar >= KOMMUN_MIN_NY_AKTIVITET
        villkor_avslutad_idag = fore_idag >= KOMMUN_MIN_NY_AKTIVITET and varde_idag == 0
        villkor_avslutad_igar = fore_igar >= KOMMUN_MIN_NY_AKTIVITET and varde_igar == 0

        if villkor_ny_idag and not villkor_ny_igar:
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Ny aktivitet i kommunen",
                "Bolag": kommun,
                "Varde": int(varde_idag),
                "Beskrivning": (
                    f"{kommun} har idag {int(varde_idag)} aktiva annonser totalt över alla "
                    f"bevakade bolag – ingen aktivitet där för 30 dagar sedan."
                ),
                "Styrka": min(varde_idag / KOMMUN_MIN_NY_AKTIVITET, 3.0),
                "Kalla": KALLA,
            })
        elif villkor_avslutad_idag and not villkor_avslutad_igar:
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Avslutad aktivitet i kommunen",
                "Bolag": kommun,
                "Varde": int(fore_idag),
                "Beskrivning": (
                    f"{kommun} har idag inga aktiva annonser – hade {int(fore_idag)} för "
                    f"30 dagar sedan. Aktiviteten har klingat av."
                ),
                "Styrka": min(fore_idag / KOMMUN_MIN_NY_AKTIVITET, 3.0),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 5: ANDELSSKIFTE (marknadsandel ±1pp över 30 dagar) - endast bolag
# ============================================================

def detektera_andelsskifte(df, dagens_datum):
    signaler = []
    totalt_per_dag = df.groupby("Datum")["Antal annonser"].sum()

    datum_30d_sedan = dagens_datum - pd.Timedelta(days=30)
    if dagens_datum not in totalt_per_dag.index:
        return signaler

    for bolag, g in df.groupby("Bolag"):
        g = g.sort_values("Datum").reset_index(drop=True)
        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue
        andel_idag = rad_idag["Antal annonser"].values[0] / totalt_per_dag[dagens_datum] * 100

        g_fore = g[g["Datum"] <= datum_30d_sedan]
        if g_fore.empty:
            continue
        datum_fore = g_fore["Datum"].iloc[-1]
        if datum_fore not in totalt_per_dag.index:
            continue
        varde_fore = g_fore["Antal annonser"].iloc[-1]
        andel_fore = varde_fore / totalt_per_dag[datum_fore] * 100

        skifte_pp = andel_idag - andel_fore
        if abs(skifte_pp) >= ANDELSSKIFTE_MIN_PP:
            riktning = "ökat" if skifte_pp > 0 else "minskat"
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Andelsskifte",
                "Bolag": bolag,
                "Varde": round(skifte_pp, 1),
                "Beskrivning": (
                    f"{bolag} har {riktning} sin annonsmarknadsandel med "
                    f"{abs(skifte_pp):.1f} procentenheter senaste 30 dagarna "
                    f"({andel_fore:.1f}% → {andel_idag:.1f}%)."
                ),
                "Styrka": round(abs(skifte_pp) / ANDELSSKIFTE_MIN_PP, 2),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 6: MARKNADSNIVÅ (summan av alla 30 bolag - stark rörelse +
# extremvärde på totalen, dvs "hela branschen" snarare än ett bolag)
# ============================================================

def detektera_marknadsniva(df, dagens_datum):
    totalt = df.groupby("Datum")["Antal annonser"].sum().reset_index()
    totalt = totalt.sort_values("Datum").reset_index(drop=True)
    totalt["Entitet"] = "Hela marknaden"
    # Återanvänd samma detektorer genom att ge dem en dataframe med en
    # enda "entitet" (totalen) i samma kolumnform som de förväntar sig.
    # OBS: Typ lämnas OFÖRÄNDRAD ("Stark rörelse v/v" / "Nytt extremvärde")
    # eftersom frontends ikonlogik skiljer sig åt mellan dessa två typer
    # (tecken på Varde för rörelse, "högsta"/"lägsta" i texten för
    # extremvärde) - en gemensam "Marknadsnivå"-typ skulle ge fel pil för
    # extremvärdessignaler. Namnet "Hela marknaden" i texten räcker för
    # att särskilja marknadsnivå från enskilda bolag/roller.
    signaler = detektera_stark_rorelse(totalt, dagens_datum, entity_col="Entitet")
    signaler += detektera_extremvarde(totalt, dagens_datum, entity_col="Entitet")

    for s in signaler:
        s["Beskrivning"] = s["Beskrivning"].replace(
            "aktiva annonser", "aktiva annonser totalt över de 30 bevakade bolagen"
        )
        # Marknadsnivå-signaler väger tyngre än en enskild entitets signal
        # med samma råstyrka - de påverkar alla läsare, inte bara ett bolag
        # eller en roll. Utan boost hamnar t.ex. "Hela marknaden på lägsta
        # nivån sedan mätstart" (styrka 1.0, som alla extremvärden) långt
        # ner bland enskilda bolagssignaler - fel prioritering för läsaren.
        s["Styrka"] = round(s["Styrka"] * MARKNADSNIVA_STYRKA_FAKTOR, 2)
    return signaler


# ============================================================
# SIGNAL 7: REGIONAL NIVÅ (summan av alla 30 bolag PER REGION - stark
# rörelse + extremvärde på regionens totala aktivitet, oavsett vilket
# bolag som annonserar. Skiljer sig från "Regional nyetablering" (signal
# 4) som bara fångar 0->N för EN entitet i EN region - den här fångar
# hela regionens temperatur, t.ex. "Östergötlands län har fallit till
# lägsta nivån sedan mätstart", oavsett vilket bolag som driver det.
# ============================================================

def detektera_regional_niva(df_regioner, dagens_datum):
    totalt = df_regioner.groupby(["Datum", "Region"])["Antal annonser"].sum().reset_index()
    totalt = totalt.rename(columns={"Region": "Entitet"})

    signaler = detektera_stark_rorelse(totalt, dagens_datum, entity_col="Entitet")
    signaler += detektera_extremvarde(totalt, dagens_datum, entity_col="Entitet")

    for s in signaler:
        s["Beskrivning"] = s["Beskrivning"].replace(
            "aktiva annonser", "aktiva annonser totalt över alla bevakade bolag i regionen"
        )
        s["Styrka"] = round(s["Styrka"] * REGIONAL_NIVA_STYRKA_FAKTOR, 2)
    return signaler


# ============================================================
# HUVUDFLÖDE
# ============================================================

BEMANNING_KOMMUNER_CSV = "bemanningsindex_kommuner_trend.csv"

def kor_signalmotor():
    df_bolag = ladda_csv(BEMANNING_CSV, ["Bolag", "Datum"])
    df_bolag_regioner = ladda_csv(BEMANNING_REGIONER_CSV, ["Bolag", "Region", "Datum"])
    df_roll = ladda_csv(ARBETSMARKNAD_CSV, ["Roll", "Datum"])
    df_bolag_kommuner = ladda_csv(BEMANNING_KOMMUNER_CSV, ["Bolag", "Kommun", "Datum"])

    # Filtrera bort den instabila uppstartsperioden (se REGION_STABIL_DATUM
    # ovan) - annars jämförs regionala/kommunala signaler mot en konstgjort
    # låg period som bara fångade ett enda bolags data per geografi.
    df_bolag_regioner = df_bolag_regioner[df_bolag_regioner["Datum"] >= REGION_STABIL_DATUM]
    df_bolag_kommuner = df_bolag_kommuner[df_bolag_kommuner["Datum"] >= REGION_STABIL_DATUM]

    dagens_datum = df_bolag["Datum"].max()

    alla_signaler = []

    # Nivå 1: Bolag - fyra signaltyper (regional nyetablering ersatt av kommunaktivitet nedan)
    alla_signaler += detektera_stark_rorelse(df_bolag, dagens_datum, entity_col="Bolag")
    alla_signaler += detektera_extremvarde(df_bolag, dagens_datum, entity_col="Bolag")
    alla_signaler += detektera_sinande_nyinflode(df_bolag, dagens_datum, entity_col="Bolag", nya_7d_col="Nya annonser 7d")
    alla_signaler += detektera_andelsskifte(df_bolag, dagens_datum)

    # Nivå 2: Signalroller - tre kärnsignaler
    alla_signaler += detektera_stark_rorelse(df_roll, dagens_datum, entity_col="Roll")
    alla_signaler += detektera_extremvarde(df_roll, dagens_datum, entity_col="Roll")
    alla_signaler += detektera_sinande_nyinflode(df_roll, dagens_datum, entity_col="Roll", nya_7d_col="Nya 7 dagar")

    # Nivå 3: Hela marknaden
    alla_signaler += detektera_marknadsniva(df_bolag, dagens_datum)

    # Nivå 4: Regional nivå (bolagens totala aktivitet per LÄN)
    alla_signaler += detektera_regional_niva(df_bolag_regioner, dagens_datum)

    # Nivå 5: Kommunnivå (ny/avslutad aktivitet per KOMMUN, ersätter gamla
    # länsbaserade "Regional nyetablering" som aldrig triggade i historiken)
    alla_signaler += detektera_kommun_aktivitet(df_bolag_kommuner, dagens_datum, sorted(df_bolag["Datum"].unique()))

    resultat = pd.DataFrame(alla_signaler)

    if resultat.empty:
        print(f"[{dagens_datum.date()}] Inga signaler idag.")
        return resultat

    resultat = resultat.sort_values("Styrka", ascending=False).reset_index(drop=True)

    dagens_datum_str = dagens_datum.strftime("%Y-%m-%d")
    if os.path.exists(SIGNAL_LOG_CSV):
        befintlig = pd.read_csv(SIGNAL_LOG_CSV, sep=";", encoding="utf-8-sig")
        befintlig = befintlig[befintlig["Datum"] != dagens_datum_str]
        combined = pd.concat([befintlig, resultat], ignore_index=True)
        combined.to_csv(SIGNAL_LOG_CSV, mode="w", header=True, index=False, sep=";", encoding="utf-8-sig")
    else:
        resultat.to_csv(SIGNAL_LOG_CSV, mode="w", header=True, index=False, sep=";", encoding="utf-8-sig")

    print(f"[{dagens_datum.date()}] {len(resultat)} signal(er) upptäckta:")
    for _, rad in resultat.iterrows():
        print(f"  [{rad['Typ']}] {rad['Beskrivning']} (styrka {rad['Styrka']})")

    print(f"\nDAGENS SIGNAL (starkast): {resultat.iloc[0]['Beskrivning']}")

    return resultat


if __name__ == "__main__":
    kor_signalmotor()
