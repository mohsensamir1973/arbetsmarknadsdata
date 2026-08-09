# -*- coding: utf-8 -*-
"""
signalmotor.py

Regelbaserad signaldetektor för arbetsmarknadsdata.se.

Syfte: automatiskt upptäcka statistiskt ovanliga händelser i den dagliga
bemanningsindex-datan, utan manuell redaktionell text. Varje signal är
spårbar till en exakt regel och siffra – ingen fri tolkning.

Körs som steg i den dagliga pipelinen, EFTER dedup.py och EFTER att
bemanningsindex_trend.csv / bemanningsindex_regioner_trend.csv är
uppdaterade för dagen, FÖRE git push.

Output: signaler_log.csv (append-only logg, en rad per detekterad signal)
Kolumner: Datum;Typ;Bolag;Varde;Beskrivning;Styrka;Kalla

Designprincip (viktigt, ändra inte utan att förstå varför):
- Trösklar är PER BOLAG (percentil av bolagets egen historik), inte en
  fast procentsats för alla. Analys 2026-08-09 visade att en fast 15%-
  regel systematiskt missar stora bolag (normal veckovolatilitet 2-5%)
  och överflaggar små bolag (normal veckovolatilitet 11-14%).
- Kräver minst MIN_HISTORIK_DAGAR dagars historik per bolag innan en
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
REGIONER_CSV = "bemanningsindex_regioner_trend.csv"
SIGNAL_LOG_CSV = "signaler_log.csv"

MIN_HISTORIK_DAGAR = 42          # ~6 veckor innan percentil-signaler aktiveras
PERCENTIL_STARK_RORELSE = 0.90   # topp 10% av bolagets egna veckorörelser
PERCENTIL_LAG_NYANNONSERING = 0.10  # botten 10% av bolagets egen nyannonsering
STOCK_STABIL_GRANS_PCT = 5.0     # aktiva annonser ±5% räknas som "stabilt"
REGIONAL_MIN_NYA_ANNONSER = 5    # 0 -> minst 5 annonser = nyetablering
ANDELSSKIFTE_MIN_PP = 1.0        # ±1 procentenhet marknadsandel över 30 dagar
MIN_AKTIVA_FOR_SIGNAL = 10        # bolag under denna nivå ger för brusiga %-tal

KALLA = "Arbetsförmedlingens öppna API"


def ladda_bemanningsdata():
    df = pd.read_csv(BEMANNING_CSV, sep=";", encoding="utf-8-sig")
    df["Datum"] = pd.to_datetime(df["Datum"])
    df = df.sort_values(["Bolag", "Datum"]).reset_index(drop=True)
    return df


def ladda_regiondata():
    df = pd.read_csv(REGIONER_CSV, sep=";", encoding="utf-8-sig")
    df["Datum"] = pd.to_datetime(df["Datum"])
    df = df.sort_values(["Bolag", "Region", "Datum"]).reset_index(drop=True)
    return df


# ============================================================
# SIGNAL 1: STARK RÖRELSE V/V (per-bolag percentil)
# ============================================================

def detektera_stark_rorelse(df, dagens_datum):
    """
    Flaggar bolag vars vecka-till-vecka-förändring (7 dagar) ligger bland
    de 10% starkaste rörelserna i BOLAGETS EGEN historik sedan mätstart.
    Kräver minst MIN_HISTORIK_DAGAR dagars data för att undvika falska
    signaler tidigt i tidsserien.
    """
    signaler = []
    for bolag, g in df.groupby("Bolag"):
        g = g.sort_values("Datum").reset_index(drop=True)
        if len(g) < MIN_HISTORIK_DAGAR + 7:
            continue
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue  # för litet bolag, %-tal blir brus (se Gazella-fallet)

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
            styrka = abs(varde_idag) / troskel  # >1 = över tröskeln
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Stark rörelse v/v",
                "Bolag": bolag,
                "Varde": round(varde_idag, 1),
                "Beskrivning": (
                    f"{bolag} har {riktning} {abs(varde_idag):.0f}% i aktiva "
                    f"annonser senaste 7 dagarna – en av bolagets starkaste "
                    f"veckorörelser sedan mätstart."
                ),
                "Styrka": round(styrka, 2),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 2: NYTT EXTREMVÄRDE SEDAN MÄTSTART (binärt, ingen kalibrering)
# ============================================================

def detektera_extremvarde(df, dagens_datum):
    signaler = []
    for bolag, g in df.groupby("Bolag"):
        g = g.sort_values("Datum").reset_index(drop=True)
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue  # för litet bolag, se Gazella-fallet
        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue
        varde_idag = rad_idag["Antal annonser"].values[0]
        historik = g[g["Datum"] < dagens_datum]["Antal annonser"]
        if len(historik) < MIN_HISTORIK_DAGAR:
            continue
        snitt = round(historik.mean())

        if varde_idag > historik.max():
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Nytt extremvärde",
                "Bolag": bolag,
                "Varde": int(varde_idag),
                "Beskrivning": (
                    f"{bolag} har idag {int(varde_idag)} aktiva annonser – "
                    f"högsta nivån sedan mätstart 20 maj 2026 (snitt över perioden: {snitt})."
                ),
                "Styrka": 1.0,
                "Kalla": KALLA,
            })
        elif varde_idag < historik.min():
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Nytt extremvärde",
                "Bolag": bolag,
                "Varde": int(varde_idag),
                "Beskrivning": (
                    f"{bolag} har idag {int(varde_idag)} aktiva annonser – "
                    f"lägsta nivån sedan mätstart 20 maj 2026 (snitt över perioden: {snitt})."
                ),
                "Styrka": 1.0,
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 3: STOCK-PARADOX (aktiva stabilt, nyannonsering historiskt lågt)
# ============================================================

def detektera_stock_paradox(df, dagens_datum):
    signaler = []
    for bolag, g in df.groupby("Bolag"):
        g = g.sort_values("Datum").reset_index(drop=True)
        if len(g) < MIN_HISTORIK_DAGAR + 7:
            continue
        if g["Antal annonser"].median() < MIN_AKTIVA_FOR_SIGNAL:
            continue  # för litet bolag, se Gazella-fallet

        g["pct_7d_aktiva"] = (
            g["Antal annonser"] - g["Antal annonser"].shift(7)
        ) / g["Antal annonser"].shift(7) * 100

        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue

        pct_aktiva = rad_idag["pct_7d_aktiva"].values[0]
        nya_7d_idag = pd.to_numeric(rad_idag["Nya annonser 7d"], errors="coerce").values[0]
        if pd.isna(pct_aktiva) or pd.isna(nya_7d_idag):
            continue
        if abs(pct_aktiva) > STOCK_STABIL_GRANS_PCT:
            continue  # inte stabilt -> ingen paradox

        historik_nya = pd.to_numeric(
            g[g["Datum"] < dagens_datum]["Nya annonser 7d"], errors="coerce"
        ).dropna()
        if len(historik_nya) < MIN_HISTORIK_DAGAR:
            continue

        troskel = historik_nya.quantile(PERCENTIL_LAG_NYANNONSERING)
        if nya_7d_idag <= troskel:
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Sinande nyinflöde",
                "Bolag": bolag,
                "Varde": int(nya_7d_idag),
                "Beskrivning": (
                    f"{bolag} har stabil annonsvolym (±{abs(pct_aktiva):.0f}% "
                    f"senaste 7 dagarna), men bara {int(nya_7d_idag)} nya annonser senaste "
                    f"7 dagarna – bland bolagets lägsta nyinflöde sedan mätstart. Om trenden "
                    f"håller minskar den totala volymen inom kommande veckor."
                ),
                "Styrka": round(1 - (nya_7d_idag / (troskel + 1)), 2),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 4: REGIONAL NYETABLERING (0 -> minst 5 annonser på 30 dagar)
# ============================================================

def detektera_regional_nyetablering(df_regioner, dagens_datum):
    signaler = []
    for (bolag, region), g in df_regioner.groupby(["Bolag", "Region"]):
        g = g.sort_values("Datum").reset_index(drop=True)
        rad_idag = g[g["Datum"] == dagens_datum]
        if rad_idag.empty:
            continue
        varde_idag = rad_idag["Antal annonser"].values[0]
        if varde_idag < REGIONAL_MIN_NYA_ANNONSER:
            continue

        datum_30d_sedan = dagens_datum - pd.Timedelta(days=30)
        historik_fore = g[
            (g["Datum"] <= datum_30d_sedan)
        ]["Antal annonser"]
        if historik_fore.empty:
            continue  # ingen data 30 dagar tillbaka, kan inte avgöra "ny"

        if historik_fore.iloc[-1] == 0:
            signaler.append({
                "Datum": dagens_datum.strftime("%Y-%m-%d"),
                "Typ": "Regional nyetablering",
                "Bolag": bolag,
                "Varde": f"{region}: {int(varde_idag)}",
                "Beskrivning": (
                    f"{bolag} annonserar nu {int(varde_idag)} tjänster i "
                    f"{region} – ingen aktivitet där för 30 dagar sedan."
                ),
                "Styrka": min(varde_idag / REGIONAL_MIN_NYA_ANNONSER, 3.0),
                "Kalla": KALLA,
            })
    return signaler


# ============================================================
# SIGNAL 5: ANDELSSKIFTE (marknadsandel ±1pp över 30 dagar)
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
# HUVUDFLÖDE
# ============================================================

def kor_signalmotor():
    df = ladda_bemanningsdata()
    df_regioner = ladda_regiondata()
    dagens_datum = df["Datum"].max()

    alla_signaler = []
    alla_signaler += detektera_stark_rorelse(df, dagens_datum)
    alla_signaler += detektera_extremvarde(df, dagens_datum)
    alla_signaler += detektera_stock_paradox(df, dagens_datum)
    alla_signaler += detektera_regional_nyetablering(df_regioner, dagens_datum)
    alla_signaler += detektera_andelsskifte(df, dagens_datum)

    resultat = pd.DataFrame(alla_signaler)

    if resultat.empty:
        print(f"[{dagens_datum.date()}] Inga signaler idag.")
        return resultat

    resultat = resultat.sort_values("Styrka", ascending=False).reset_index(drop=True)

    # Skydd mot dubbletter: om scriptet körs flera gånger samma dag (t.ex. vid
    # test eller omkörning), ta bort ev. tidigare rader för DAGENS datum innan
    # vi skriver de nya - annars dubbleras signalerna i loggen. Samma princip
    # som dedup.py använder för trend-CSV:erna (senaste körningen vinner).
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
