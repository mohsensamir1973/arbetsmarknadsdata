"""
Bemanningsindex v7 - spar annoneringsaktivitet for ledande bemanning-
och rekryteringsbolag via AF:s oppna API
=======================================================================
Ersatter: bemanningsindex.py (v6)
Placeras i: Documents\Arbetsmarknadsindex\

Nyheter i v7 vs v6:
  - Filtrering pa organisationsnummer i API-svaret (inte som sokparameter)
  - 100% precision - matcher exakt ratt bolag
  - Stodjer flera org-nummer per bolag (koncerner/regionbolag)
  - Bred API-sokning pa bolagsnamn, sedan filtrering pa org-nummer

Bolagslista: 30 utvalda bolag som speglar branschens bredd
Sparar:
  bemanningsindex_trend.csv
  bemanningsindex_regioner_trend.csv
  bemanningsindex_kommuner_trend.csv
"""

import urllib.request
import urllib.parse
import json
import csv
import ssl
import time
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from collections import Counter

os.chdir(os.path.dirname(os.path.abspath(__file__)))

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ── Bolag att folja ──────────────────────────────────────────────────
# Format: "Visningsnamn": {"sokord": "...", "org_nr": ["nr1", "nr2"]}
# sokord: bred sokning for att hitta annonserna
# org_nr: filtrering pa exakt organisationsnummer i API-svaret
BOLAG = {
    "Manpower":            {"sokord": "Manpower",            "org_nr": ["5563481588"]},
    "Lernia":              {"sokord": "Lernia",              "org_nr": ["5564727013"]},
    "Adecco":              {"sokord": "Adecco",              "org_nr": ["5564472677"]},
    "Perido":              {"sokord": "Perido",              "org_nr": ["5566396387"]},
    "Randstad":            {"sokord": "Randstad",            "org_nr": ["5562421718", "5560896572"]},
    "Academic Work":       {"sokord": "Academic Work",       "org_nr": ["5565595450"]},
    "Studentconsulting":   {"sokord": "Studentconsulting",   "org_nr": ["5566747449"]},
    "Poolia":              {"sokord": "Poolia",              "org_nr": ["5564267655"]},
    "Uniflex":             {"sokord": "Uniflex",             "org_nr": ["5566370341"]},
    "OnePartnerGroup":     {"sokord": "OnePartnerGroup",     "org_nr": [
                                "5591178107", "5563190478", "5590758180", "5569974388",
                                "5590413083", "5569466658", "5590939186", "5593283509",
                                "5568773476", "5590928619", "5568432230", "5568615545",
                                "5566766589", "5591571459", "5590937537", "5569584476",
                                "5569278475",
                            ]},
    "Skill":               {"sokord": "Skill",               "org_nr": ["5566858618"]},
    "Arena Personal":      {"sokord": "Arena Personal",      "org_nr": ["5566061916"]},
    "Tranpenad":           {"sokord": "Tranpenad",           "org_nr": ["5565970364"]},
    "Jobandtalent":        {"sokord": "Jobandtalent",        "org_nr": ["5591046148"]},
    "NearYou":             {"sokord": "NearYou",             "org_nr": ["5566007273"]},
    "SJR":                 {"sokord": "SJR",                 "org_nr": ["5566523980"]},
    "Clockwork":           {"sokord": "Clockwork",           "org_nr": ["5569137325"]},
    "Logent":              {"sokord": "Logent",              "org_nr": ["5590416714"]},
    "Bemannia":            {"sokord": "Bemannia",            "org_nr": ["5566268347"]},
    "Framtiden i Sverige": {"sokord": "Framtiden i Sverige", "org_nr": ["5566865142"]},
    "Professionals Nord":  {"sokord": "Professionals Nord",  "org_nr": [
                                "5594361650", "5593344665", "5595008029", "5592870405",
                                "5593001885", "5593456899", "5592870454", "5593489031",
                            ]},
    "Bravura":             {"sokord": "Bravura Sverige",     "org_nr": ["5567520803"]},
    "Jurek":               {"sokord": "Jurek Recruitment",   "org_nr": ["5566945324"]},
    "TNG Group":           {"sokord": "TNG Group",           "org_nr": ["5566482781"]},
    "Eterni Sweden":       {"sokord": "Eterni Sweden",       "org_nr": ["5568637283"]},
    "Friday":              {"sokord": "Friday",              "org_nr": [
                                "5591411326", "5592225253", "5594520750", "5594675117",
                            ]},
    "Gazella":             {"sokord": "Gazella",             "org_nr": ["5569733982"]},
    "Insitepart":          {"sokord": "Insitepart",          "org_nr": ["5590245048"]},
    "Wikan Personal":      {"sokord": "Wikan Personal",      "org_nr": ["5568427818"]},
    "Konsultia":           {"sokord": "Konsultia",           "org_nr": ["5569380883"]},
}

API_NYCKEL  = ""
PAGE_SIZE   = 100
MAX_SIDOR   = 50
FORDROJNING = 0.3
TIMEOUT     = 30

HUVUDFIL  = "bemanningsindex_trend.csv"
REGIOFIL  = "bemanningsindex_regioner_trend.csv"
KOMMUNFIL = "bemanningsindex_kommuner_trend.csv"
LOGGFIL   = "bemanningsindex_logg.txt"


def logg(meddelande: str):
    rad = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {meddelande}"
    print(rad)
    with open(LOGGFIL, "a", encoding="utf-8") as f:
        f.write(rad + "\n")


def klassificera_duration(label: str) -> str:
    if not label:
        return "okand"
    l = label.lower()
    if "tills vidare" in l:
        return "tills_vidare"
    if "6 manader" in l or "langre" in l:
        return "lang"
    return "kort"


def api_request(url: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    if API_NYCKEL:
        req.add_header("api-key", API_NYCKEL)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as r:
        return json.loads(r.read())


def hamta_alla(sokord: str, org_nummers: list, extra_params: dict = None) -> dict:
    """
    Soker brett pa sokord, filtrerar sedan pa org-nummer i svaret.
    100% precision - matcher exakt ratt bolag/koncern.
    """
    org_set = set(org_nummers)

    region_counter     = Counter()
    kommun_counter     = Counter()
    yrkesfalt_counter  = Counter()
    yrkesgrupp_counter = Counter()
    duration_counter   = Counter()
    arbetstid_counter  = Counter()

    tot_tjanster    = 0
    krav_erfarenhet = 0
    antal_hits      = 0
    offset          = 0
    total           = 0

    while True:
        params = {"q": sokord, "limit": PAGE_SIZE, "offset": offset}
        if extra_params:
            params.update(extra_params)

        try:
            data = api_request(
                f"https://jobsearch.api.jobtechdev.se/search?{urllib.parse.urlencode(params)}"
            )
        except Exception as e:
            logg(f"  API-fel vid offset {offset}: {e}")
            break

        if offset == 0:
            total = data.get("total", {}).get("value", 0)

        hits = data.get("hits", [])
        if not hits:
            break

        for h in hits:
            emp = h.get("employer", {})
            org_nr = emp.get("organization_number", "")

            # Filtrera pa org-nummer - 100% precision
            if org_nr not in org_set:
                continue

            antal_hits += 1

            adr = h.get("workplace_address", {})
            reg = adr.get("region", "")
            kom = adr.get("municipality", "")
            if reg: region_counter[reg] += 1
            if kom: kommun_counter[kom] += 1

            yf = h.get("occupation_field", {})
            yg = h.get("occupation_group", {})
            if yf and yf.get("label"): yrkesfalt_counter[yf["label"]] += 1
            if yg and yg.get("label"): yrkesgrupp_counter[yg["label"]] += 1

            tot_tjanster += h.get("number_of_vacancies", 1) or 1

            dur = h.get("duration", {})
            dur_label = dur.get("label", "") if dur else ""
            duration_counter[klassificera_duration(dur_label)] += 1

            at = h.get("working_hours_type", {})
            at_label = at.get("label", "") if at else ""
            if at_label: arbetstid_counter[at_label] += 1

            if h.get("experience_required"):
                krav_erfarenhet += 1

        offset += PAGE_SIZE
        if offset >= total or offset >= MAX_SIDOR * PAGE_SIZE:
            break

        time.sleep(FORDROJNING)

    n = max(antal_hits, 1)

    return {
        "total":             antal_hits,
        "tot_tjanster":      tot_tjanster,
        "region_counter":    region_counter,
        "kommun_counter":    kommun_counter,
        "yrkesfalt_counter": yrkesfalt_counter,
        "yrkesgrupp_counter":yrkesgrupp_counter,
        "duration_counter":  duration_counter,
        "arbetstid_counter": arbetstid_counter,
        "pct_heltid":        round(min(arbetstid_counter.get("Heltid", 0) / n * 100, 100), 1),
        "pct_tills_vidare":  round(min(duration_counter.get("tills_vidare", 0) / n * 100, 100), 1),
        "pct_lang":          round(min(duration_counter.get("lang", 0) / n * 100, 100), 1),
        "pct_kort":          round(min(duration_counter.get("kort", 0) / n * 100, 100), 1),
        "pct_erfarenhet":    round(min(krav_erfarenhet / n * 100, 100), 1),
    }


def hamta_detaljer(sokord: str, org_nummers: list) -> dict:
    alla = hamta_alla(sokord, org_nummers)

    fjorton = (datetime.now(timezone.utc) - timedelta(days=14)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_14d = hamta_alla(sokord, org_nummers, extra_params={"published-after": fjorton})

    sju = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_7d = hamta_alla(sokord, org_nummers, extra_params={"published-after": sju})

    return {
        "total":               alla["total"],
        "tot_tjanster":        alla["tot_tjanster"],
        "nya_14d":             nya_14d["total"],
        "nya_14d_tjanster":    nya_14d["tot_tjanster"],
        "nya_7d":              nya_7d["total"],
        "nya_7d_tjanster":     nya_7d["tot_tjanster"],
        "aktivitetstakt":      round(nya_14d["total"] / max(alla["total"], 1) * 100, 1),
        "reg_alla":            alla["region_counter"],
        "reg_nya":             nya_14d["region_counter"],
        "kom_alla":            alla["kommun_counter"],
        "yrkesfalt":           alla["yrkesfalt_counter"],
        "yrkesgrupp":          alla["yrkesgrupp_counter"],
        "pct_heltid":          alla["pct_heltid"],
        "pct_tills_vidare":    alla["pct_tills_vidare"],
        "pct_lang":            alla["pct_lang"],
        "pct_kort":            alla["pct_kort"],
        "pct_erfarenhet":      alla["pct_erfarenhet"],
    }


def kor_analys():
    logg("=" * 65)
    logg("BEMANNINGSINDEX v7")
    logg(f"Arbetsmapp: {os.getcwd()}")
    logg("=" * 65)

    resultat = {}
    for bolag, info in BOLAG.items():
        logg(f"  Hamtar: {bolag}...")
        try:
            d = hamta_detaljer(info["sokord"], info["org_nr"])
            resultat[bolag] = d

            top3r  = d["reg_alla"].most_common(3)
            top3yf = d["yrkesfalt"].most_common(3)
            reg_str = "  |  ".join(f"{r} ({n})" for r, n in top3r)
            yf_str  = "  |  ".join(f"{y} ({n})" for y, n in top3yf)

            takt = d["aktivitetstakt"]
            pil  = "upp" if takt >= 30 else ("ok" if takt >= 15 else "ned")

            logg(f"  {bolag:<25} {d['total']:>4} annonser / {d['tot_tjanster']:>5} tjanster")
            logg(f"  {'':25} Nya 14d: {d['nya_14d']} ({takt}% aktivitetstakt {pil})")
            logg(f"  {'':25} Nya 7d: {d['nya_7d']}")
            logg(f"  {'':25} Heltid: {d['pct_heltid']}%  Tills vidare: {d['pct_tills_vidare']}%")
            if reg_str: logg(f"  {'':25} Regioner: {reg_str}")
            if yf_str:  logg(f"  {'':25} Yrkesomraden: {yf_str}")
            logg("")

        except Exception as e:
            resultat[bolag] = None
            logg(f"  FEL  {bolag}  {e}")
            logg(traceback.format_exc())

    datum = datetime.now().strftime("%Y-%m-%d")

    def fmt(lst): return " | ".join(f"{k} ({v})" for k, v in lst)

    huvud_ny = not os.path.exists(HUVUDFIL)
    with open(HUVUDFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if huvud_ny:
            w.writerow([
                "Datum", "Bolag",
                "Antal annonser", "Antal tjanster",
                "Nya annonser 14d", "Nya tjanster 14d",
                "Nya annonser 7d", "Nya tjanster 7d",
                "Aktivitetstakt % (14d)",
                "% heltid", "% tills vidare", "% lang", "% kort",
                "% erfarenhet kravs",
                "Top 3 regioner (totalt)", "Top 3 regioner (14 dagar)",
                "Top 3 yrkesomraden", "Top 5 yrkesgrupper",
            ])
        for bolag, d in resultat.items():
            if d is None:
                w.writerow([datum, bolag] + ["Fel"] * 16)
                continue
            w.writerow([
                datum, bolag,
                d["total"], d["tot_tjanster"],
                d["nya_14d"], d["nya_14d_tjanster"],
                d["nya_7d"], d["nya_7d_tjanster"],
                d["aktivitetstakt"],
                d["pct_heltid"], d["pct_tills_vidare"], d["pct_lang"], d["pct_kort"],
                d["pct_erfarenhet"],
                fmt(d["reg_alla"].most_common(3)),
                fmt(d["reg_nya"].most_common(3)),
                fmt(d["yrkesfalt"].most_common(3)),
                fmt(d["yrkesgrupp"].most_common(5)),
            ])

    reg_ny = not os.path.exists(REGIOFIL)
    with open(REGIOFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if reg_ny:
            w.writerow(["Datum", "Bolag", "Region", "Antal annonser", "Nya 14 dagar"])
        for bolag, d in resultat.items():
            if d is None: continue
            for region in sorted(set(d["reg_alla"]) | set(d["reg_nya"])):
                w.writerow([
                    datum, bolag, region,
                    d["reg_alla"].get(region, 0),
                    d["reg_nya"].get(region, 0),
                ])

    kom_ny = not os.path.exists(KOMMUNFIL)
    with open(KOMMUNFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if kom_ny:
            w.writerow(["Datum", "Bolag", "Kommun", "Antal annonser"])
        for bolag, d in resultat.items():
            if d is None: continue
            for kommun, antal in d["kom_alla"].most_common(5):
                w.writerow([datum, bolag, kommun, antal])

    logg(f"Sparat: {HUVUDFIL}")
    logg(f"Sparat: {REGIOFIL}")
    logg(f"Sparat: {KOMMUNFIL}")
    logg("Kor dagligen kl 08:00 for att bygga konkurrensanalys over tid.")


if __name__ == "__main__":
    try:
        kor_analys()
    except Exception as e:
        logg(f"KRITISKT FEL: {e}")
        logg(traceback.format_exc())
        sys.exit(1)
