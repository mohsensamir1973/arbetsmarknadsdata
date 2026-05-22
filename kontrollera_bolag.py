"""
Kontrollerar totalt antal API-traff per bolag utan filter.
Kors i Documents\Arbetsmarknadsindex\ och jamfor med platsbanken.
"""
import urllib.request
import urllib.parse
import json
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BOLAG = [
    ("Manpower",            "Manpower"),
    ("Lernia",              "Lernia"),
    ("Adecco",              "Adecco"),
    ("Perido",              "Perido"),
    ("Randstad",            "Randstad"),
    ("Academic Work",       "Academic Work Sweden"),
    ("Studentconsulting",   "Studentconsulting"),
    ("Poolia",              "Poolia"),
    ("Uniflex",             "Uniflex"),
    ("OnePartnerGroup",     "OnePartnerGroup"),
    ("Skill",               "Skill"),
    ("Arena Personal",      "Arena Personal"),
    ("Tranpenad",           "Tranpenad"),
    ("Jobandtalent",        "Jobandtalent"),
    ("NearYou",             "NearYou"),
    ("SJR",                 "SJR"),
    ("Clockwork",           "Clockwork"),
    ("Logent",              "Logent"),
    ("Bemannia",            "Bemannia"),
    ("Framtiden i Sverige", "Framtiden i Sverige"),
    ("A-hub",               "A Hub"),
    ("Professionals Nord",  "Professionals Nord"),
    ("Bravura",             "Bravura Sverige"),
    ("Jurek",               "Jurek Recruitment"),
    ("TNG Group",           "Tng Group"),
    ("Eterni Sweden",       "Eterni Sweden"),
    ("Friday",              "Friday"),
    ("Gazella",             "Gazella"),
    ("Insitepart",          "Insitepart"),
    ("Wikan Personal",      "Wikan Personal"),
    ("Konsultia",           "Konsultia"),
]

print(f"{'Bolag':<25} {'API-total':>10}")
print("-" * 37)

for namn, sokord in BOLAG:
    try:
        url = "https://jobsearch.api.jobtechdev.se/search?" + urllib.parse.urlencode({"q": sokord, "limit": 1})
        r = urllib.request.urlopen(url, context=ctx, timeout=15)
        data = json.loads(r.read())
        total = data["total"]["value"]
        print(f"{namn:<25} {total:>10}")
    except Exception as e:
        print(f"{namn:<25} FEL: {e}")
    time.sleep(0.3)

print()
print("Jamfor API-total med platsbanken.")
print("Stor avvikelse = sokord behover justeras.")
