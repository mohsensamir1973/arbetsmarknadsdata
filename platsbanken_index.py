"""
platsbanken_index.py – totalen för hela Platsbanken, per dag

Sparar en rad per dag med totalt antal annonser på Arbetsförmedlingen, plus
uppdelning per yrkesområde (AF:s occupation-field) och per län. Ger
sammanhanget för de 9 signalrollerna och de 30 bolagen: hur stor del av
Platsbanken det är, och om marknaden som helhet rör sig åt samma håll.

Hämtar bara räknetal (limit=0 + stats), inga annonser. 3 API-anrop per körning.

Skriver till: platsbanken_trend.csv
  Datum;Niva;Namn;Concept_id;Aktiva;Nya 7 dagar;Nya 30 dagar
  Niva = Totalt | Yrkesomrade | Lan

Körs automatiskt i slutet av arbetsmarknadsindex.py. Kan också köras själv:
  python platsbanken_index.py
Om dagens datum redan finns i filen hoppar skriptet över (ingen dubbelrad).
"""

import csv
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

FIL = "platsbanken_trend.csv"
API = "https://jobsearch.api.jobtechdev.se/search"
TIMEOUT = 60

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

KOLUMNER = ["Datum", "Niva", "Namn", "Concept_id", "Aktiva", "Nya 7 dagar", "Nya 30 dagar"]


def _anrop(params: list) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            svar = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            svar = ""
        raise RuntimeError(f"HTTP {e.code} för {url}\n    Svar från AF: {svar}") from None


# Fungerande sätt att be om uppdelning sparas här under körningen, så att
# samma variant används för alla tre perioderna.
_STATS_VARIANT: dict = {}


def _hamta(extra: list) -> dict:
    # 1. Totalen, enklast möjliga anrop.
    data = _anrop([("limit", 0)] + extra)
    data["stats"] = []
    # 2. Uppdelning per typ, flera varianter tills någon fungerar.
    for typ in ("occupation-field", "region"):
        varianter = [_STATS_VARIANT[typ]] if typ in _STATS_VARIANT else [
            [("stats", typ), ("stats.limit", 50)],
            [("stats", typ), ("stats.limit", 30)],
            [("stats", typ)],
            [("limit", 1), ("stats", typ), ("stats.limit", 30)],
        ]
        for v in varianter:
            if v is None:
                break
            params = ([] if any(k == "limit" for k, _ in v) else [("limit", 0)]) + v + extra
            try:
                svar = _anrop(params)
                data["stats"].extend(svar.get("stats", []) or [])
                _STATS_VARIANT[typ] = v
                break
            except RuntimeError as e:
                print(f"  (provade variant för {typ}: {e})")
        else:
            _STATS_VARIANT[typ] = None
            print(f"  OBS: ingen variant för {typ} fungerade.")
    return data


def _tolka(data: dict) -> dict:
    """Returnerar {"total": int, "Yrkesomrade": {(namn, id): n}, "Lan": {...}}."""
    total = data.get("total", {}).get("value")
    if not isinstance(total, int):
        raise ValueError(f"Hittade inget totalantal i svaret (nycklar: {list(data.keys())})")
    ut = {"total": total, "Yrkesomrade": {}, "Lan": {}}
    for block in data.get("stats", []) or []:
        typ = block.get("type")
        niva = {"occupation-field": "Yrkesomrade", "region": "Lan"}.get(typ)
        if not niva:
            continue
        for v in block.get("values", []) or []:
            namn = v.get("term") or v.get("label") or ""
            cid = v.get("concept_id") or v.get("code") or ""
            n = v.get("count")
            if namn and isinstance(n, int):
                ut[niva][(namn, str(cid))] = n
    return ut


def _redan_kord(datum: str) -> bool:
    if not os.path.exists(FIL):
        return False
    with open(FIL, encoding="utf-8-sig") as f:
        return any(rad.startswith(datum + ";") for rad in f)


def kor() -> None:
    datum = datetime.now().strftime("%Y-%m-%d")
    print()
    print(f"  platsbanken_index.py – {datum}")
    if _redan_kord(datum):
        print(f"  {FIL} har redan rader för {datum}, hoppar över.")
        return

    nu = datetime.now(timezone.utc)
    sju = (nu - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    trettio = (nu - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")

    aktiva = _tolka(_hamta([]))
    nya7 = _tolka(_hamta([("published-after", sju)]))
    nya30 = _tolka(_hamta([("published-after", trettio)]))

    rader = [[datum, "Totalt", "Platsbanken", "", aktiva["total"], nya7["total"], nya30["total"]]]
    for niva in ("Yrkesomrade", "Lan"):
        for (namn, cid), n in sorted(aktiva[niva].items(), key=lambda x: -x[1]):
            rader.append([datum, niva, namn, cid, n, nya7[niva].get((namn, cid), 0), nya30[niva].get((namn, cid), 0)])

    ny_fil = not os.path.exists(FIL)
    with open(FIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if ny_fil:
            w.writerow(KOLUMNER)
        w.writerows(rader)

    print(f"  Totalt aktiva annonser: {aktiva['total']:,}".replace(",", " "))
    print(f"  Nya senaste 7 dagarna:  {nya7['total']:,}".replace(",", " "))
    print(f"  Yrkesområden: {len(aktiva['Yrkesomrade'])} · Län: {len(aktiva['Lan'])}")
    if not aktiva["Yrkesomrade"] or not aktiva["Lan"]:
        print("  OBS: uppdelningen saknas i svaret – bara totalen sparad. Visa detta för Claude.")
    print(f"  Sparat: {FIL}")


if __name__ == "__main__":
    kor()
