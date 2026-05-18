"""
Hämtar occupation_group direkt från jobsearch-API:et
genom att söka på varje roll och plocka ut unika grupper.
Kör: python hitta_occupation_ids_v2.py
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
print("OCCUPATION GROUP ID:N PER SIGNALROLL")
print("=" * 70)
print()

for roll, sokord in ROLLER.items():
    params = urllib.parse.urlencode({"q": sokord, "limit": 100})
    try:
        data = api_request(
            f"https://jobsearch.api.jobtechdev.se/search?{params}"
        )
        hits = data.get("hits", [])
        total = data.get("total", {}).get("value", 0)

        # Samla unika occupation_group med ID och label
        grupper = {}
        for h in hits:
            grp = h.get("occupation_group")
            if grp and grp.get("concept_id") and grp.get("label"):
                cid = grp["concept_id"]
                label = grp["label"]
                grupper[cid] = grupper.get(cid, {"label": label, "count": 0})
                grupper[cid]["count"] += 1

        print(f"{roll} (totalt {total} annonser):")
        for cid, info in sorted(grupper.items(),
                                key=lambda x: x[1]["count"],
                                reverse=True)[:6]:
            pct = round(info["count"] / len(hits) * 100) if hits else 0
            print(f"  {info['label']:<50} ID: {cid}  ({pct}%)")
        print()
        time.sleep(0.5)

    except Exception as e:
        print(f"  FEL: {e}\n")

