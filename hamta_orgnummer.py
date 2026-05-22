"""
Hamtar organisationsnummer for alla 30 bolag fran AF:s API.
Kors en gang - kopiera resultatet och skicka till Claude.
"""
import urllib.request
import urllib.parse
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Sokord per bolag - bred sokning for att hitta ratt org-nummer
BOLAG = [
    ("Manpower",            "Manpower"),
    ("Lernia",              "Lernia Bemanning"),
    ("Adecco",              "Adecco"),
    ("Perido",              "Perido"),
    ("Randstad",            "Randstad"),
    ("Academic Work",       "Academic Work Sweden"),
    ("Studentconsulting",   "Studentconsulting"),
    ("Poolia",              "Poolia"),
    ("Uniflex",             "Uniflex"),
    ("OnePartnerGroup",     "OnePartnerGroup"),
    ("Skill",               "Skill Kompetenspartner"),
    ("Arena Personal",      "Arena Personal"),
    ("Tranpenad",           "Tranpenad"),
    ("Jobandtalent",        "Jobandtalent"),
    ("NearYou",             "NearYou"),
    ("SJR",                 "SJR in Sweden"),
    ("Clockwork",           "Clockwork Bemanning"),
    ("Logent",              "Logent"),
    ("Bemannia",            "Bemannia"),
    ("Framtiden i Sverige", "Framtiden i Sverige"),
    ("A-hub",               "A Hub AB"),
    ("Professionals Nord",  "Professionals Nord"),
    ("Bravura",             "Bravura Sverige"),
    ("Jurek",               "Jurek Recruitment"),
    ("TNG Group",           "Tng Group"),
    ("Eterni Sweden",       "Eterni Sweden"),
    ("Friday",              "Friday Vast"),
    ("Gazella",             "Gazella"),
    ("Insitepart",          "Insitepart"),
    ("Wikan Personal",      "Wikan Personal"),
    ("Konsultia",           "Konsultia"),
]

print(f"{'Bolag':<25} {'Arbetsgivare':<40} {'Org-nummer'}")
print("-" * 80)

for namn, sokord in BOLAG:
    try:
        url = "https://jobsearch.api.jobtechdev.se/search?" + urllib.parse.urlencode({
            "q": sokord,
            "limit": 5
        })
        r = urllib.request.urlopen(url, context=ctx, timeout=15)
        data = json.loads(r.read())
        hits = data.get("hits", [])
        
        seen = {}
        for h in hits:
            emp = h.get("employer", {})
            emp_name = emp.get("name", "")
            org_nr = emp.get("organization_number", "")
            if org_nr and org_nr not in seen:
                seen[org_nr] = emp_name

        if seen:
            for org_nr, emp_name in seen.items():
                print(f"{namn:<25} {emp_name:<40} {org_nr}")
        else:
            print(f"{namn:<25} {'INGA TRAFF':<40}")
        
    except Exception as e:
        print(f"{namn:<25} FEL: {e}")
    
    time.sleep(0.3)

print()
print("Kopiera resultatet och skicka till Claude.")
