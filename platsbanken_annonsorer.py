"""
platsbanken_annonsorer.py – de största annonsörerna på hela Platsbanken, per dag

Internt kontrollverktyg, visas inte på sajten. Används för att:
  1. se om en enskild annonsör förklarar en rörelse i Platsbankens total
  2. hitta nya massannonsörer tidigt (se Metodik, Massannonsörer)

Hämtar Arbetsförmedlingens ögonblicksbild av alla aktiva annonser (JobStream,
ca 480 MB, ca 1,5 minut), räknar per arbetsgivare (organisationsnummer) och
sparar de 200 största. Den hämtade filen raderas direkt efteråt.

Skriver till: platsbanken_annonsorer_trend.csv
  Datum;Org-nr;Arbetsgivare;Annonser;Tjänster;Nya 7 dagar
  Första raden varje dag är Org-nr "Totalt" = alla aktiva annonser.

Körs efter platsbanken_index.py i den dagliga körningen:
  python -u platsbanken_annonsorer.py
Om dagens datum redan finns i filen hoppar skriptet över (ingen dubbelrad).
"""

import collections
import csv
import json
import os
import ssl
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta

FIL = "platsbanken_annonsorer_trend.csv"
LOGG = "platsbanken_annonsorer_logg.txt"  # fel skrivs hit, så att vi ser varför en morgonkörning missades
FORSOK = 3
PAUS_S = 120
SNAPSHOT = "https://jobstream.api.jobtechdev.se/v2/snapshot"
ANTAL = 200
KOLUMNER = ["Datum", "Org-nr", "Arbetsgivare", "Annonser", "Tjänster", "Nya 7 dagar"]

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass


def _logga(text: str) -> None:
    rad = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {text}"
    print("  " + rad)
    with open(LOGG, "a", encoding="utf-8") as f:
        f.write(rad + "\n")


def _redan_kord(datum: str) -> bool:
    if not os.path.exists(FIL):
        return False
    with open(FIL, encoding="utf-8-sig") as f:
        return any(rad.startswith(datum + ";") for rad in f)


def _hamta() -> list:
    t0 = time.time()
    req = urllib.request.Request(SNAPSHOT, headers={"Accept": "application/json"})
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with urllib.request.urlopen(req, timeout=900, context=SSL_CONTEXT) as r, os.fdopen(fd, "wb") as f:
            while True:
                bit = r.read(1024 * 1024)
                if not bit:
                    break
                f.write(bit)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    print(f"  Hämtade {len(data)} annonser på {time.time() - t0:.0f} s")
    return data


def _forra_veckan(datum: str) -> dict:
    """Antal annonser per org-nr för samma veckodag förra veckan, om den finns."""
    if not os.path.exists(FIL):
        return {}
    d7 = (datetime.strptime(datum, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    ut = {}
    with open(FIL, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["Datum"] == d7:
                ut[r["Org-nr"]] = int(r["Annonser"])
    return ut


def kor() -> None:
    datum = datetime.now().strftime("%Y-%m-%d")
    print()
    print(f"  platsbanken_annonsorer.py – {datum}")
    if _redan_kord(datum):
        print(f"  {FIL} har redan rader för {datum}, hoppar över.")
        return

    data = None
    for forsok in range(1, FORSOK + 1):
        try:
            data = _hamta()
            break
        except Exception as e:  # noqa: BLE001
            _logga(f"Försök {forsok}/{FORSOK} misslyckades: {type(e).__name__}: {e}")
            if forsok < FORSOK:
                time.sleep(PAUS_S)
    if data is None:
        _logga("Gav upp, ingen rad sparad i dag.")
        sys.exit(1)
    annonser = [a for a in data if not a.get("removed")]
    gräns = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    antal = collections.Counter()
    tjanster = collections.Counter()
    nya = collections.Counter()
    namn = {}
    for a in annonser:
        ag = a.get("employer") or {}
        k = ag.get("organization_number") or ("namn:" + (ag.get("name") or "okänd"))
        antal[k] += 1
        tjanster[k] += a.get("number_of_vacancies") or 1
        if (a.get("publication_date") or "")[:10] >= gräns:
            nya[k] += 1
        namn.setdefault(k, (ag.get("name") or "okänd").strip())

    rader = [[datum, "Totalt", "Alla annonsörer", len(annonser), sum(tjanster.values()), sum(nya.values())]]
    for k, n in antal.most_common(ANTAL):
        rader.append([datum, k, namn[k], n, tjanster[k], nya[k]])

    ny_fil = not os.path.exists(FIL)
    with open(FIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if ny_fil:
            w.writerow(KOLUMNER)
        w.writerows(rader)

    print(f"  Aktiva annonser: {len(annonser):,}".replace(",", " ") + f" · arbetsgivare: {len(antal):,}".replace(",", " "))
    print("  Största annonsörerna:")
    for k, n in antal.most_common(10):
        print(f"    {n:>5}  {namn[k]}")

    # Att granska: stora annonsörer som ökat kraftigt på en vecka, eller är nya bland de största.
    fore = _forra_veckan(datum)
    if fore:
        flagga = []
        for k, n in antal.most_common(ANTAL):
            f7 = fore.get(k)
            if n >= 100 and (f7 is None or n >= 2 * f7):
                flagga.append((n, f7, namn[k]))
        if flagga:
            print("  ATT GRANSKA (minst 100 annonser och dubbelt så många som för en vecka sedan, eller nya i listan):")
            for n, f7, nm in flagga:
                print(f"    {nm}: {f7 if f7 is not None else 'ej i listan'} -> {n}")
    print(f"  Sparat: {FIL}")


if __name__ == "__main__":
    kor()
