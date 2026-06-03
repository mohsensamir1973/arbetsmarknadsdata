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


# TILLAGDA 2026-06-01
    "Releasy Customer Management AB":          "Direktarbetsgivare",
    "Foundever Sweden AB":                     "Direktarbetsgivare",
    "Transcom AB":                             "Direktarbetsgivare",
    "Ideal BM AB":                             "Bemanning/Rekrytering",
    "Sanandum AB":                             "Bemanning/Rekrytering",
    "REGION NORRBOTTEN":                       "Direktarbetsgivare",
    "REGION SÖRMLAND":                         "Direktarbetsgivare",
    "Logent Bemanning AB":                     "Bemanning/Rekrytering",
    "Sopra Steria Sweden AB":                  "Konsultbolag",
    "Lovable Labs Sweden AB":                  "Direktarbetsgivare",
    "Ants Akademiskt Nätverk av Tekniska Studenter AB": "Bemanning/Rekrytering",
    "Lynqa AB":                                "Konsultbolag",
    "Capgemini Engineering Sverige AB":        "Konsultbolag",
    "Agile Resources AB":                      "Bemanning/Rekrytering",
    "Försvarets Materielverk":                 "Direktarbetsgivare",
    "People of Interim & Finance Sweden AB":   "Bemanning/Rekrytering",
    "AxÖ Consulting AB":                       "Konsultbolag",
    "SJ AB":                                   "Direktarbetsgivare",
    "Ingka Services AB":                       "Direktarbetsgivare",
    "Posti Logistics Staffing AB":             "Bemanning/Rekrytering",
    "Libera i Sverige AB":                     "Bemanning/Rekrytering",
    "Astani Wear AB":                          "Direktarbetsgivare",
    "Jovi Konsult AB":                         "Bemanning/Rekrytering",
    "Arena Personal Sverige AB":               "Bemanning/Rekrytering",
    "Nexify bemanning & rekrytering AB":       "Bemanning/Rekrytering",
    "Systrarnas bemanning AB":                 "Bemanning/Rekrytering",
    "Vårdbemanning Sverige AB":                "Bemanning/Rekrytering",
    "MACC PEOPLE AB":                          "Bemanning/Rekrytering",
    "Fibio Nordic AB":                         "Direktarbetsgivare",
    "Barona Professionals AB":                 "Bemanning/Rekrytering",

# TILLAGDA 2026-05-31
    "Insitepart AB":              "Bemanning/Rekrytering",
    "Jollyroom AB":               "Direktarbetsgivare",
    "Gekomm AB":                  "Direktarbetsgivare",
    "DEROME AKTIEBOLAG":          "Direktarbetsgivare",
    "KUNGSBACKA KOMMUN":          "Direktarbetsgivare",
    "BODENS KOMMUN":              "Direktarbetsgivare",
    "Silex Microsystems AB":      "Direktarbetsgivare",
    "Unik Resurs i Sverige AB":   "Bemanning/Rekrytering",
    "VårdIX AB":                  "Bemanning/Rekrytering",
    "Viraliv AB":                 "Bemanning/Rekrytering",

# TILLAGDA 2026-05-30
    "Consensus Sverige AB":                  "Bemanning/Rekrytering",
    "Jobway AB":                             "Bemanning/Rekrytering",
    "Co-Worker Technology Sweden AB":        "Bemanning/Rekrytering",
    "Sway Sourcing Sweden AB":               "Bemanning/Rekrytering",
    "Sway Sourcing Sweden Aktiebolag":       "Bemanning/Rekrytering",
    "Delta Consulting AB":                   "Bemanning/Rekrytering",
    "STANDBY WORKTEAM AB":                   "Bemanning/Rekrytering",
    "ACADEMIC WORK SWEDEN AB":               "Bemanning/Rekrytering",
    "StudentConsulting Sweden AB (publ)":    "Bemanning/Rekrytering",
    "Balkefors & Ponsiluoma Aktiebolag":     "Bemanning/Rekrytering",
    "Bae Systems Hägglunds AB":              "Direktarbetsgivare",
    "Jobbusters AB":                         "Bemanning/Rekrytering",
    "Hireq AB":                              "Bemanning/Rekrytering",
    "Resultat i Sverige AB":                 "Bemanning/Rekrytering",
    "Ps Partner AB":                         "Bemanning/Rekrytering",
    # TILLAGDA 2026-05-27
    "Tng Group AB":               "Bemanning/Rekrytering",
    "Cubane Solutions AB":        "Konsultbolag",
    "Lycksele kommun":            "Direktarbetsgivare",
    "Nexer Recruit AB":           "Bemanning/Rekrytering",
    "Sellhelp AB":                "Direktarbetsgivare",
    "Charlie AB":                 "Bemanning/Rekrytering",
    "MultiMind Holding AB":       "Bemanning/Rekrytering",
    "OnePartnerGroup Halland AB": "Bemanning/Rekrytering",

    # EXKLUDERADE – aggregatorer och irrelevanta aktörer
    "DUVI GROUP AB":                      "Exkludera",
    "Jobs By Nordics AB":                 "Exkludera",
    "Degerfors IF":                       "Exkludera",

    # TILLAGDA 2026-06-02
    "Vinnergi AB":                        "Direktarbetsgivare",
    "ADECCO SWEDEN AKTIEBOLAG":           "Bemanning/Rekrytering",
    "Athletic Work Nordic AB":            "Bemanning/Rekrytering",
    "GVU AB":                             "Konsultbolag",
    "HÖGSKOLAN I SKÖVDE":                 "Direktarbetsgivare",
    "Epiroc Rock Drills Aktiebolag":      "Direktarbetsgivare",
    "44:AN FÖRVALTNINGS AKTIEBOLAG":      "Direktarbetsgivare",
    "FÖREN BLOMSTERFONDEN":               "Direktarbetsgivare",}

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
            antal_hits += 1

            adr = h.get("workplace_address", {})
            reg = adr.get("region", "")
            kom = adr.get("municipality", "")
            if reg: region_counter[reg] += 1
            if kom: kommun_counter[kom] += 1

            ag = h.get("employer", {}).get("name", "")
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
                "% heltid", "% tills vidare", "% lång", "% kort",
                "% erfarenhet", "% nystartsjobb",
                "Top 3 regioner (totalt)", "Top 3 regioner (7 dagar)",
                "Top 20 arbetsgivare",
            ])
        for roll, d in resultat.items():
            grupp = ROLLER[roll]["grupp"]
            if d is None:
                w.writerow([datum, roll, grupp, is_baseline] + ["Fel"] * 16)
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
                d["pct_heltid"], d["pct_tills_vidare"],
                d["pct_lang"], d["pct_kort"],
                d["pct_erfarenhet"], d["pct_nystartsjobb"],
                fmt(d["reg_alla"].most_common(3)),
                fmt(d["reg_nya"].most_common(3)),
                ag_klassad,
            ])

    # ── Rapportera okända arbetsgivare (bara topp 10 per roll) ───────
    okanda = set()
    for roll, d in resultat.items():
        if d is None: continue
        for ag, _ in d["ag_counter"].most_common(20):
            if klassificera_ag(ag) == "Okänd – granska":
                okanda.add(ag)
    if okanda:
        print()
        print("⚠️  OKÄNDA ARBETSGIVARE i topp 10 – lägg till i ARBETSGIVARE_TYP:")
        for ag in sorted(okanda):
            print(f"   {ag}")

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
