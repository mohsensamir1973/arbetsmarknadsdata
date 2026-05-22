"""
Verifierar att alla bolag i bemanningsindex ger korrekta siffror.
Soker via AF:s API med org-nummer-filtrering och skriver ut resultatet.
Jamfor mot platsbanken manuellt for att bekrafta.
"""
import urllib.request
import urllib.parse
import json
import ssl
import time
from collections import Counter

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PAGE_SIZE = 100
MAX_SIDOR = 50

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

def rakna_annonser(sokord, org_nummers):
    org_set = set(org_nummers)
    antal = 0
    offset = 0
    total = 0
    api_total = 0

    while True:
        params = {"q": sokord, "limit": PAGE_SIZE, "offset": offset}
        url = f"https://jobsearch.api.jobtechdev.se/search?{urllib.parse.urlencode(params)}"
        try:
            r = urllib.request.urlopen(url, context=ctx, timeout=15)
            data = json.loads(r.read())
        except Exception as e:
            print(f"  API-fel: {e}")
            break

        if offset == 0:
            api_total = data.get("total", {}).get("value", 0)
            total = api_total

        hits = data.get("hits", [])
        if not hits:
            break

        for h in hits:
            org_nr = h.get("employer", {}).get("organization_number", "")
            if org_nr in org_set:
                antal += 1

        offset += PAGE_SIZE
        if offset >= total or offset >= MAX_SIDOR * PAGE_SIZE:
            break

        time.sleep(0.2)

    return antal, api_total

print(f"{'Bolag':<25} {'Annonser':>10} {'API-total':>10}  Status")
print("-" * 60)

for namn, info in BOLAG.items():
    antal, api_total = rakna_annonser(info["sokord"], info["org_nr"])
    # Varning om API-total ar nara 2100-gransen
    varning = " *** KOLLA!" if api_total >= 2000 else ""
    print(f"{namn:<25} {antal:>10} {api_total:>10}  {varning}")
    time.sleep(0.3)

print()
print("Kolumner: Bolag | Antal annonser (efter org-nr filter) | API-total (fore filter)")
print("*** KOLLA = API-total nar 2100-gransen, kan ge underskattning")
print()
print("Jamfor 'Antal annonser' mot platsbanken.arbetsformedlingen.se")
print("Acceptabel avvikelse: +-10% (timing-skillnad)")
print("Rod flagga: avvikelse >20%")
