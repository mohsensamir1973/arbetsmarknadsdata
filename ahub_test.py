import urllib.request
import urllib.parse
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ORG_NR = "5591779656"
SOKORD = ["A Hub", "A-hub", "ahub", "a hub ab", "A Hub AB"]

ids = set()

for q in SOKORD:
    url = "https://jobsearch.api.jobtechdev.se/search?" + urllib.parse.urlencode({"q": q, "limit": 100})
    r = urllib.request.urlopen(url, context=ctx, timeout=15)
    data = json.loads(r.read())
    total = data["total"]["value"]
    matches = 0
    for h in data["hits"]:
        if h.get("employer", {}).get("organization_number", "") == ORG_NR:
            ids.add(h.get("id", ""))
            matches += 1
    print(f"Sokord '{q}': {total} totalt, {matches} A Hub AB-matcher i topp 100")
    time.sleep(0.3)

print()
print(f"Unika A Hub AB annonser totalt: {len(ids)}")
print()
print("Slutsats: Om detta ar langa under 163 ar problemet att annonserna")
print("ar utspridda bortom 2100-gransen oavsett sokord.")
