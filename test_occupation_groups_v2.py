"""
Testscript v2 – hämtar occupation_group från faktiska annonser
Kör: python test_occupation_groups_v2.py
"""
import urllib.request
import urllib.parse
import json
import ssl
import time
from collections import Counter

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

ROLLER = {
    "Kundtjänstmedarbetare": "kundtjänst kundservice",
    "Ekonomiassistent":      "ekonomiassistent",
    "Lagerarbetare":         "lagerarbetare",
    "Account Manager":       "account manager",
    "Business Controller":   "business controller",
    "Systemutvecklare":      "systemutvecklare",
    "Mekanikkonstruktör":    "mekanikkonstruktör",
    "Elingenjör":            "elingenjör",
    "Sjuksköterska":         "sjuksköterska",
    "Undersköterska":        "undersköterska",
}

def api_request(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as r:
        return json.loads(r.read())

print("=" * 70)
print("OCCUPATION GROUPS PER SIGNALROLL (urval 100 annonser)")
print("=" * 70)
print()

for roll, sokord in ROLLER.items():
    params = urllib.parse.urlencode({"q": sokord, "limit": 100})
    try:
        data = api_request(
            f"https://jobsearch.api.jobtechdev.se/search?{params}"
        )
        total = data.get("total", {}).get("value", 0)
        hits = data.get("hits", [])

        grp_counter = Counter()
        emp_counter = Counter()

        for h in hits:
            grp = h.get("occupation_group", {})
            if grp and grp.get("label"):
                grp_counter[grp["label"]] += 1
            emp = h.get("employer", {}).get("name", "")
            if emp:
                emp_counter[emp] += 1

        print(f"{roll} (totalt {total} annonser, urval {len(hits)}):")
        print("  Yrkesgrupper:")
        for grp, cnt in grp_counter.most_common(8):
            pct = round(cnt / len(hits) * 100) if hits else 0
            print(f"    {grp:<45} {cnt:>4} ({pct}%)")
        print("  Topp arbetsgivare:")
        for emp, cnt in emp_counter.most_common(5):
            print(f"    {emp:<45} {cnt:>4}")
        print()
        time.sleep(0.5)

    except Exception as e:
        print(f"  FEL: {e}\n")

