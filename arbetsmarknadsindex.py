"""
Arbetsmarknadsindex v6 – söker via occupation_group-ID för exakt data
======================================================================
Ersätter: arbetsmarknadsindex.py (v5)
Placeras i: Documents\Arbetsmarknadsindex\

Nyheter i v6 vs v5:
  - Sökning via occupation_group-ID istället för fritext
  - 100% precision per roll – inget brus
  - Daglig körning (ersätter varannan vecka)
  - Rolling 14-dagars data sparas
  - Baseline-flagga för mätning 1
"""

import urllib.request
import urllib.parse
import json
import csv
import ssl
import time
import os
from datetime import datetime, timedelta, timezone
from collections import Counter

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ── Signalroller med occupation_group-ID ────────────────────────────
# Källa: AF:s jobsearch API, concept_id från occupation_group-fältet
ROLLER = {
    "Kundtjänstmedarbetare": {
        "ids": ["pwRH_MT1_8nR"],
        "grupp": "Volym / cykel",
    },
    "Ekonomiassistent": {
        "ids": ["ij8k_EwC_zyB"],
        "grupp": "Volym / cykel",
    },
    "Lagerarbetare": {
        "ids": ["kLyY_rwr_aJr"],
        "grupp": "Volym / cykel",
    },

    "Business Controller": {
        "ids": ["Uw4n_UB2_RCW"],
        "grupp": "Framåtblickande signal",
    },
    "Systemutvecklare": {
        "ids": ["DJh5_yyF_hEM"],
        "grupp": "Framåtblickande signal",
    },
    "Mekanikkonstruktör": {
        "ids": ["K8yg_U4C_gkY", "PRQn_9yw_NJA"],
        "grupp": "Struktur / transformation",
    },
    "Elingenjör": {
        "ids": ["nDaB_vdy_eAy", "SPYW_7Z1_ShT"],
        "grupp": "Struktur / transformation",
    },
    "Sjuksköterska": {
        "ids": ["Z8ci_bBE_tmx"],
        "grupp": "Strukturell brist",
    },
    "Undersköterska": {
        "ids": ["jY19_knH_MJp"],
        "grupp": "Strukturell brist",
    },
}

API_NYCKEL  = ""
PAGE_SIZE   = 100
MAX_SIDOR   = 40
FÖRDRÖJNING = 0.4
TIMEOUT     = 30

HUVUDFIL  = "arbetsmarknadsindex_trend.csv"
REGIOFIL  = "arbetsmarknadsindex_regioner_trend.csv"
KOMMUNFIL = "arbetsmarknadsindex_kommuner_trend.csv"

# ── Arbetsgivarklassificering ────────────────────────────────────────
# Tre kategorier: Bemannings/rekryteringsbolag, Konsultbolag, Direktarbetsgivare
# Okända bolag flaggas automatiskt som "Okänd – granska"

ARBETSGIVARE_TYP = {
    # BEMANNINGS/REKRYTERINGSBOLAG
    "Academic Work Sweden AB":                  "Bemanning/Rekrytering",
    "Studentconsulting Sweden AB":              "Bemanning/Rekrytering",
    "Studentconsulting Sweden AB (Publ)":       "Bemanning/Rekrytering",
    "Lernia Bemanning AB":                      "Bemanning/Rekrytering",
    "Uniflex AB":                               "Bemanning/Rekrytering",
    "Tranpenad AB":                             "Bemanning/Rekrytering",
    "Poolia AB":                                "Bemanning/Rekrytering",
    "SJR in Sweden AB":                         "Bemanning/Rekrytering",
    "Clockwork Bemanning & Rekrytering AB":     "Bemanning/Rekrytering",
    "Framtiden i Sverige AB":                   "Bemanning/Rekrytering",
    "Bravura Sverige AB":                       "Bemanning/Rekrytering",
    "PersonalExpressen AB":                     "Bemanning/Rekrytering",
    "Aura Personal AB":                         "Bemanning/Rekrytering",
    "Boxflow Staffing Syd AB":                  "Bemanning/Rekrytering",
    "Jobandtalent Sweden AB":                   "Bemanning/Rekrytering",
    "Simplex Bemanning AB":                     "Bemanning/Rekrytering",
    "Pokayoke AB":                              "Bemanning/Rekrytering",
    "Professionals Nord Linköping AB":          "Bemanning/Rekrytering",
    "Professionals Nord Norra Norrland AB":     "Bemanning/Rekrytering",
    "Performiq AB":                             "Bemanning/Rekrytering",
    "Viva Bemanning AB":                        "Bemanning/Rekrytering",
    "Kraftsam Rekrytering & Bemanning AB":      "Bemanning/Rekrytering",
    "Wrknest AB":                               "Bemanning/Rekrytering",
    "Submit AB":                                "Bemanning/Rekrytering",
    "Andara Group AB":                          "Bemanning/Rekrytering",
    "Mpya Finance AB":                          "Bemanning/Rekrytering",
    "Medla Sverige AB":                         "Bemanning/Rekrytering",
    "Procruitment AB":                          "Bemanning/Rekrytering",
    "Eqwiry AB":                                "Bemanning/Rekrytering",
    "Almia AB":                                 "Bemanning/Rekrytering",
    "Palmelind Konsult AB":                     "Bemanning/Rekrytering",
    "Te Crea Care AB":                          "Bemanning/Rekrytering",
    "Techrytera AB":                            "Bemanning/Rekrytering",
    "Jobbakuten Väst AB":                       "Bemanning/Rekrytering",
    "Lyten Ett AB":                             "Bemanning/Rekrytering",
    "PartnerFlow Group AB":                     "Bemanning/Rekrytering",
    "Workz Sweden AB":                          "Bemanning/Rekrytering",
    "Xamera AB":                                "Bemanning/Rekrytering",
    "Friday Väst AB":                           "Bemanning/Rekrytering",
    "OIO Väst AB":                              "Bemanning/Rekrytering",
    "Adecco Sweden AB":                         "Bemanning/Rekrytering",
    "Randstad AB":                              "Bemanning/Rekrytering",
    "Flodin Rekrytering & Bemanning AB":        "Bemanning/Rekrytering",
    "Jurek Recruitment & Consulting AB":        "Bemanning/Rekrytering",
    "Recruitive AB":                            "Bemanning/Rekrytering",
    "A Hub AB":                                 "Bemanning/Rekrytering",
    "Skill Kompetenspartner AB":                "Bemanning/Rekrytering",
    "Vindex AB":                                "Bemanning/Rekrytering",
    # KONSULTBOLAG
    "AFRY AB":                                  "Konsultbolag",
    "AKKA Talent Management AB":                "Konsultbolag",
    "Akkodis Sweden Electrical Solutions AB":   "Konsultbolag",
    "Alten Sverige AB":                         "Konsultbolag",
    "Avalon Innovation Technology AB":          "Konsultbolag",
    "Avaron AB":                                "Konsultbolag",
    "Cloudgruppen Sverige AB":                  "Konsultbolag",
    "Experis AB":                               "Konsultbolag",
    "Fellowmind Sweden AB":                     "Konsultbolag",
    "Iver Sverige AB":                          "Konsultbolag",
    "Knightec Group Hardware and Design AB":    "Konsultbolag",
    "Knowit AB":                                "Konsultbolag",
    "Knowit AB (Publ)":                         "Konsultbolag",
    "SKPA Consulting AB":                       "Konsultbolag",
    "Semicon Service Nordic AB":                "Konsultbolag",
    "Veritaz AB":                               "Konsultbolag",
    "Combitech AB":                             "Konsultbolag",
    "Syntronic AB":                             "Konsultbolag",
    "Collen AB":                                "Konsultbolag",
    # DIREKTARBETSGIVARE
    "REGION ÖSTERGÖTLAND":                      "Direktarbetsgivare",
    "REGION SKÅNE":                             "Direktarbetsgivare",
    "REGION STOCKHOLM":                         "Direktarbetsgivare",
    "REGION JÖNKÖPINGS LÄN":                    "Direktarbetsgivare",
    "REGION UPPSALA":                           "Direktarbetsgivare",
    "VÄSTRA GÖTALANDSREGIONEN":                 "Direktarbetsgivare",
    "Skatteverket":                             "Direktarbetsgivare",
    "Stockholms kommun":                        "Direktarbetsgivare",
    "Uppsala Universitet":                      "Direktarbetsgivare",
    "Vattenfall AB":                            "Direktarbetsgivare",
    "Hitachi Energy Sweden AB":                 "Direktarbetsgivare",
    "SAAB AB":                                  "Direktarbetsgivare",
    "ABB AB":                                   "Direktarbetsgivare",
    "Rituals Cosmetics Sweden AB":              "Direktarbetsgivare",
    "Kronans Apotek AB":                        "Direktarbetsgivare",
    "Arken Zoo AB":                             "Direktarbetsgivare",
    "Synsam Group Sweden AB":                   "Direktarbetsgivare",
    "H & M Hennes & Mauritz Gbc AB":            "Direktarbetsgivare",
    "First Camp Sverige AB":                    "Direktarbetsgivare",
    "Hemfrid i Sverige AB":                     "Direktarbetsgivare",
    "Lifestyle Media Partner Sverige AB":        "Direktarbetsgivare",
    "Attendo Sverige AB":                       "Direktarbetsgivare",
    "Vardaga AB":                               "Direktarbetsgivare",
    "Forenede Care AB":                         "Direktarbetsgivare",
    "Norlandia Care AB":                        "Direktarbetsgivare",
    "Humana AB":                                "Direktarbetsgivare",
    "Ur & Penn AB":                             "Direktarbetsgivare",
    "Verisure Sverige AB":                      "Direktarbetsgivare",
    "Svenska Trygghetslösningar AB":            "Direktarbetsgivare",
    "Axis Communications AB":                   "Direktarbetsgivare",
    "Concentrix Sweden AB":                     "Direktarbetsgivare",
    "Försäkringskassan":                        "Direktarbetsgivare",
    "GÖTEBORGS KOMMUN":                         "Direktarbetsgivare",
    "Göteborgs Universitet":                    "Direktarbetsgivare",
    "Kungsbacka kommun":                        "Direktarbetsgivare",
    "Svenska Kraftnät":                         "Direktarbetsgivare",
    "Maskinförsäljning Europa AB":              "Direktarbetsgivare",
    "Teleperformance Nordic AB":                "Direktarbetsgivare",
    "Mervida AB":                               "Direktarbetsgivare",
    "Takteam i Sverige AB":                     "Direktarbetsgivare",
    "Täta Tak Energi Sverige AB":               "Direktarbetsgivare",
    "YRKESKLÄDER FÖR PROFFS SVERIGE AB":        "Direktarbetsgivare",
    "Gävle kommun":                             "Direktarbetsgivare",
    "Nexer AB":                                 "Konsultbolag",
    "Responda Group AB":                        "Bemanning/Rekrytering",
    "Technologist 365 AB":                      "Bemanning/Rekrytering",
    "Hero AB":                    "Bemanning/Rekrytering",
    "Avanzera AB":                "Bemanning/Rekrytering",
    "Omsorg & Behandling 1 AB":   "Direktarbetsgivare",
    "Allegio Omsorg AB":          "Direktarbetsgivare",
    # Tillagda 2026-05-25
    "REGION DALARNA":             "Direktarbetsgivare",
    "Capgemini Engineering Sverige AB": "Konsultbolag",
    "Athletic Work Nordic AB":    "Bemanning/Rekrytering",
    "Mölndals kommun":            "Direktarbetsgivare",
    "Klippan Safety AB":          "Direktarbetsgivare",
}

# ── Aggregatorer och felaktiga poster – exkluderas helt från datan ───
# Dessa bolag stör totalen och ska inte räknas alls.
# Lägg till nya aggregatorer här när de hittas.
EXKLUDERA_ARBETSGIVARE = {
    "DUVI GROUP AB",
    "Duvi Group AB",
    "Akhtar, Naeem",
}

def klassificera_ag(namn: str) -> str:
    """Klassificerar arbetsgivare. Okända flaggas för granskning."""
    return ARBETSGIVARE_TYP.get(namn, "Okänd – granska")

def klassificera_duration(label: str) -> str:
    if not label:
        return "okänd"
    l = label.lower()
    if "tills vidare" in l:
        return "tills_vidare"
    if "6 månader" in l or "längre" in l:
        return "lång"
    return "kort"

def api_request(url: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    if API_NYCKEL:
        req.add_header("api-key", API_NYCKEL)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as r:
        return json.loads(r.read())

def bygg_url(ids: list, extra_params: dict = None) -> str:
    """Bygger URL med ett eller flera occupation-group-ID:n."""
    params = []
    for oid in ids:
        params.append(("occupation-group", oid))
    params.append(("limit", PAGE_SIZE))
    if extra_params:
        for k, v in extra_params.items():
            params.append((k, v))
    query = urllib.parse.urlencode(params)
    return f"https://jobsearch.api.jobtechdev.se/search?{query}"

def hamta_alla(ids: list, extra_params: dict = None) -> dict:
    """Paginerar alla annonser för givna occupation_group-ID:n."""
    region_counter    = Counter()
    kommun_counter    = Counter()
    ag_counter        = Counter()
    duration_counter  = Counter()
    arbetstid_counter = Counter()

    tot_tjanster    = 0
    krav_erfarenhet = 0
    nystartsjobb    = 0
    antal_hits      = 0
    offset          = 0
    total           = 0

    while True:
        ep = extra_params.copy() if extra_params else {}
        ep["offset"] = offset

        try:
            data = api_request(bygg_url(ids, ep))
        except Exception:
            break

        if offset == 0:
            total = data.get("total", {}).get("value", 0)

        hits = data.get("hits", [])
        if not hits:
            break

        for h in hits:
            ag = h.get("employer", {}).get("name", "")

            # Hoppa över aggregatorer och felaktiga poster
            if ag in EXKLUDERA_ARBETSGIVARE:
                continue

            antal_hits += 1

            adr = h.get("workplace_address", {})
            reg = adr.get("region", "")
            kom = adr.get("municipality", "")
            if reg: region_counter[reg] += 1
            if kom: kommun_counter[kom] += 1

            if ag: ag_counter[ag] += 1

            tot_tjanster += h.get("number_of_vacancies", 1) or 1

            dur = h.get("duration", {})
            dur_label = dur.get("label", "") if dur else ""
            duration_counter[klassificera_duration(dur_label)] += 1

            at = h.get("working_hours_type", {})
            at_label = at.get("label", "") if at else ""
            if at_label: arbetstid_counter[at_label] += 1

            if h.get("experience_required"):
                krav_erfarenhet += 1

            labels = h.get("label", []) or []
            if "nystartsjobb" in labels:
                nystartsjobb += 1

        offset += PAGE_SIZE
        if offset >= total or offset >= MAX_SIDOR * PAGE_SIZE:
            break

        time.sleep(FÖRDRÖJNING)

    n = max(antal_hits, 1)

    return {
        "total":             total,
        "tot_tjanster":      tot_tjanster,
        "region_counter":    region_counter,
        "kommun_counter":    kommun_counter,
        "ag_counter":        ag_counter,
        "duration_counter":  duration_counter,
        "arbetstid_counter": arbetstid_counter,
        "pct_heltid":        round(min(arbetstid_counter.get("Heltid", 0) / n * 100, 100), 1),
        "pct_tills_vidare":  round(min(duration_counter.get("tills_vidare", 0) / n * 100, 100), 1),
        "pct_lang":          round(min(duration_counter.get("lång", 0) / n * 100, 100), 1),
        "pct_kort":          round(min(duration_counter.get("kort", 0) / n * 100, 100), 1),
        "pct_erfarenhet":    round(min(krav_erfarenhet / n * 100, 100), 1),
        "pct_nystartsjobb":  round(min(nystartsjobb / n * 100, 100), 1),
    }

def hamta_detaljer(ids: list) -> dict:
    alla = hamta_alla(ids)

    # Nya senaste 30 dagar
    trettio = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_30d = hamta_alla(ids, extra_params={"published-after": trettio})

    # Nya senaste 14 dagar (rolling window)
    fjorton = (datetime.now(timezone.utc) - timedelta(days=14)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_14d = hamta_alla(ids, extra_params={"published-after": fjorton})

    # Nya senaste 7 dagar
    sju = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_7d = hamta_alla(ids, extra_params={"published-after": sju})

    return {
        "total":            alla["total"],
        "tot_tjanster":     alla["tot_tjanster"],
        "nya_30d":          nya_30d["total"],
        "nya_30d_tjanster": nya_30d["tot_tjanster"],
        "nya_14d":          nya_14d["total"],
        "nya_14d_tjanster": nya_14d["tot_tjanster"],
        "nya_7d":           nya_7d["total"],
        "nya_7d_tjanster":  nya_7d["tot_tjanster"],
        "reg_alla":         alla["region_counter"],
        "reg_nya":          nya_7d["region_counter"],
        "reg_14d":          nya_14d["region_counter"],
        "kom_alla":         alla["kommun_counter"],
        "ag_counter":       alla["ag_counter"],
        "pct_erfarenhet":   alla["pct_erfarenhet"],
        "pct_nystartsjobb": alla["pct_nystartsjobb"],
        "pct_heltid":       alla["pct_heltid"],
        "pct_tills_vidare": alla["pct_tills_vidare"],
        "pct_lang":         alla["pct_lang"],
        "pct_kort":         alla["pct_kort"],
    }

def kör_analys():
    datum    = datetime.now().strftime("%Y-%m-%d")
    klockslag = datetime.now().strftime("%H:%M")
    is_baseline = not os.path.exists(HUVUDFIL)

    print("=" * 65)
    print("ARBETSMARKNADSINDEX v6")
    print(f"Datum: {datum} {klockslag}")
    if is_baseline:
        print("*** BASELINE-MÄTNING (mätning 1) ***")
    print("=" * 65)
    print()

    resultat = {}
    for roll, info in ROLLER.items():
        print(f"  Hämtar: {roll}...")
        try:
            d = hamta_detaljer(info["ids"])
            resultat[roll] = d

            top3r = d["reg_alla"].most_common(3)
            top3a = d["ag_counter"].most_common(3)
            reg_str = "  |  ".join(f"{r} ({n})" for r, n in top3r)
            ag_str  = "  |  ".join(f"{a} ({n})" for a, n in top3a)

            print(f"  {roll:<30} {d['total']:>5} annonser / {d['tot_tjanster']:>6} tjänster")
            print(f"  {'':30} Nya 7d: {d['nya_7d']} | Nya 14d: {d['nya_14d']}")
            print(f"  {'':30} Heltid: {d['pct_heltid']}% | Tills vidare: {d['pct_tills_vidare']}% | Lång: {d['pct_lang']}% | Kort: {d['pct_kort']}%")
            print(f"  {'':30} Erfarenhet: {d['pct_erfarenhet']}% | Nystartsjobb: {d['pct_nystartsjobb']}%")
            if reg_str: print(f"  {'':30} Regioner: {reg_str}")
            if ag_str:  print(f"  {'':30} Arbetsgivare: {ag_str}")
            print()

        except Exception as e:
            resultat[roll] = None
            print(f"  FEL  {roll}  {e}\n")

    def fmt(lst): return " | ".join(f"{k} ({v})" for k, v in lst)

    # ── Läs baseline-värden om de finns ─────────────────────────────
    baseline_values = {}
    if os.path.exists(HUVUDFIL):
        with open(HUVUDFIL, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row.get("Baseline", "").lower() in ("true", "1", "yes"):
                    baseline_values[row["Roll"]] = int(row["Antal annonser"]) if row["Antal annonser"].isdigit() else None

    def beräkna_index(roll: str, antal: int) -> str:
        if roll not in baseline_values or baseline_values[roll] is None:
            return "100 (baseline)"
        base = baseline_values[roll]
        if base == 0:
            return "–"
        index = round(antal / base * 100, 1)
        diff = round(index - 100, 1)
        sign = "+" if diff >= 0 else ""
        return f"{index} ({sign}{diff})"

    # ── Huvudfil ─────────────────────────────────────────────────────
    huvud_ny = not os.path.exists(HUVUDFIL)
    with open(HUVUDFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if huvud_ny:
            w.writerow([
                "Datum", "Roll", "Grupp", "Baseline",
                "Antal annonser", "Index (baseline=100)",
                "Antal tjänster",
                "Nya 7 dagar", "Nya 7 dagar tjänster",
                "Nya 14 dagar", "Nya 14 dagar tjänster",
                "Nya 30 dagar", "Nya 30 dagar tjänster",
                "% heltid", "% tills vidare", "% lång", "% kort",
                "% erfarenhet", "% nystartsjobb",
                "Top 3 regioner (totalt)", "Top 3 regioner (7 dagar)",
                "Top 20 arbetsgivare",
            ])
        for roll, d in resultat.items():
            grupp = ROLLER[roll]["grupp"]
            if d is None:
                w.writerow([datum, roll, grupp, is_baseline] + ["Fel"] * 18)
                continue
            # Bygg klassificerad arbetsgivarlista
            ag_klassad = " | ".join(
                f"{ag} ({n}) [{klassificera_ag(ag)}]"
                for ag, n in d["ag_counter"].most_common(20)
            )
            index_str = beräkna_index(roll, d["total"])
            w.writerow([
                datum, roll, grupp, is_baseline,
                d["total"], index_str,
                d["tot_tjanster"],
                d["nya_7d"], d["nya_7d_tjanster"],
                d["nya_14d"], d["nya_14d_tjanster"],
                d["nya_30d"], d["nya_30d_tjanster"],
                d["pct_heltid"], d["pct_tills_vidare"],
                d["pct_lang"], d["pct_kort"],
                d["pct_erfarenhet"], d["pct_nystartsjobb"],
                fmt(d["reg_alla"].most_common(3)),
                fmt(d["reg_nya"].most_common(3)),
                ag_klassad,
            ])

    # ── Rapportera okända arbetsgivare (bara topp 10 per roll) ───────
    # ── Okända arbetsgivare – rapportera bara de med 10+ annonser ───────
    # Tröskeln filtrerar bort småbolag som sällan återkommer.
    # Bolag med 10+ annonser är tillräckligt aktiva för att påverka datan.
    TRÖSKEL_OKÄND = 10
    okanda = {}  # namn -> (totalt_annonser, roller)
    for roll, d in resultat.items():
        if d is None: continue
        for ag, antal in d["ag_counter"].most_common(20):
            if klassificera_ag(ag) == "Okänd – granska":
                if ag not in okanda:
                    okanda[ag] = {"totalt": 0, "roller": []}
                okanda[ag]["totalt"] += antal
                okanda[ag]["roller"].append(f"{roll} ({antal})")

    okanda_viktiga = {ag: v for ag, v in okanda.items() if v["totalt"] >= TRÖSKEL_OKÄND}

    # Spara alla okända (även små) till fil för veckovis granskning
    with open("okanda_arbetsgivare_ny.txt", "w", encoding="utf-8") as f:
        f.write(f"OKÄNDA ARBETSGIVARE – {datum}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Antal okända: {len(okanda)}\n")
        f.write("Kontrollera en gång i veckan och lägg till i ARBETSGIVARE_TYP\n\n")
        for ag, v in sorted(okanda.items(), key=lambda x: -x[1]["totalt"]):
            roller_str = ", ".join(v["roller"])
            f.write(f"  {ag:<50} totalt={v['totalt']}  [{roller_str}]\n")

    # Visa bara viktiga (10+) i konsolen
    if okanda_viktiga:
        print()
        print(f"⚠️  {len(okanda_viktiga)} OKÄNDA ARBETSGIVARE med 10+ annonser – lägg till i ARBETSGIVARE_TYP:")
        for ag, v in sorted(okanda_viktiga.items(), key=lambda x: -x[1]["totalt"]):
            roller_str = ", ".join(v["roller"])
            print(f"   {ag:<50} {v['totalt']} annonser  [{roller_str}]")
        print(f"   (+ {len(okanda) - len(okanda_viktiga)} bolag med färre än {TRÖSKEL_OKÄND} annonser – se okanda_arbetsgivare_ny.txt)")
    else:
        print()
        print(f"✓  Inga okända arbetsgivare med {TRÖSKEL_OKÄND}+ annonser idag.")

    # ── Regionfil ────────────────────────────────────────────────────
    reg_ny = not os.path.exists(REGIOFIL)
    with open(REGIOFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if reg_ny:
            w.writerow(["Datum", "Roll", "Grupp", "Region",
                        "Antal annonser", "Nya 7 dagar", "Nya 14 dagar"])
        for roll, d in resultat.items():
            if d is None: continue
            for region in sorted(set(d["reg_alla"]) | set(d["reg_nya"]) | set(d["reg_14d"])):
                w.writerow([
                    datum, roll, ROLLER[roll]["grupp"], region,
                    d["reg_alla"].get(region, 0),
                    d["reg_nya"].get(region, 0),
                    d["reg_14d"].get(region, 0),
                ])

    # ── Kommunfil ────────────────────────────────────────────────────
    kom_ny = not os.path.exists(KOMMUNFIL)
    with open(KOMMUNFIL, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if kom_ny:
            w.writerow(["Datum", "Roll", "Grupp", "Kommun", "Antal annonser"])
        for roll, d in resultat.items():
            if d is None: continue
            for kommun, antal in d["kom_alla"].most_common(5):
                w.writerow([datum, roll, ROLLER[roll]["grupp"], kommun, antal])

    print(f"Sparat: {HUVUDFIL}")
    print(f"Sparat: {REGIOFIL}")
    print(f"Sparat: {KOMMUNFIL}")
    if is_baseline:
        print()
        print("*** Baseline satt. Nästa körning visar förändring mot denna. ***")
    print()
    print("Kör dagligen för att bygga trenddata.")

if __name__ == "__main__":
    kör_analys()
