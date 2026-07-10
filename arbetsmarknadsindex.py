"""
Arbetsmarknadsindex v7 – automatisk arbetsgivarklassificering via SNI
======================================================================
Ersätter: arbetsmarknadsindex.py (v6)
Placeras i: Documents\Arbetsmarknadsindex\

Nyheter i v7 vs v6:
  - Automatisk klassificering via Bolagsverkets API + SNI-koder
  - Cache-fil (arbetsgivare_cache.json) sparar uppslag lokalt
  - Manuell lista är fortfarande override – ändras aldrig automatiskt
  - Exkluderingslista för aggregatorer och irrelevanta aktörer
  - CSV-data är identisk med v6 – ingen påverkan på trendhistorik

Fix v7.1:
  - okanda_arbetsgivare_ny.txt skrivs om varje körning med dagens datum
  - Org-nummer visas i filen för snabbare manuell klassificering
  - Sorterat efter volym – viktigaste bolagen överst
"""

import urllib.request
import urllib.parse
import urllib.error
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

# ── Sökväg till cache-fil ────────────────────────────────────────────
CACHE_FIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arbetsgivare_cache.json")

# ── Signalroller med occupation_group-ID ────────────────────────────
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
OKANDA_FIL = "okanda_arbetsgivare_ny.txt"

# ── SNI-mappning ─────────────────────────────────────────────────────
SNI_MAPPNING = {
    "7810": "Bemanning/Rekrytering",
    "7820": "Bemanning/Rekrytering",
    "7830": "Bemanning/Rekrytering",
    "6201": "Konsultbolag",
    "6202": "Konsultbolag",
    "6203": "Konsultbolag",
    "6209": "Konsultbolag",
    "7111": "Konsultbolag",
    "7112": "Konsultbolag",
    "7120": "Konsultbolag",
    "7021": "Konsultbolag",
    "7022": "Konsultbolag",
    "6920": "Konsultbolag",
}

# ── Exkluderade bolag ────────────────────────────────────────────────
EXKLUDERA = {
    "DUVI GROUP AB",
    "Jobs By Nordics AB",
    "Degerfors IF",
    "Willem Kralik, Jana",
}

# ── Manuell lista – override, alltid rätt ───────────────────────────
ARBETSGIVARE_TYP = {
    # BEMANNINGS/REKRYTERINGSBOLAG
    "ACADEMIC WORK SWEDEN AB":                          "Bemanning/Rekrytering",
    "Academic Work Sweden AB":                          "Bemanning/Rekrytering",
    "Adecco Sweden AB":                                 "Bemanning/Rekrytering",
    "ADECCO SWEDEN AKTIEBOLAG":                         "Bemanning/Rekrytering",
    "Agile Resources AB":                               "Bemanning/Rekrytering",
    "Almia AB":                                         "Bemanning/Rekrytering",
    "Andara Group AB":                                  "Bemanning/Rekrytering",
    "Ants Akademiskt Nätverk av Tekniska Studenter AB": "Bemanning/Rekrytering",
    "Arena Personal Sverige AB":                        "Bemanning/Rekrytering",
    "Athletic Work Nordic AB":                          "Bemanning/Rekrytering",
    "Atteviksgruppen AB":                               "Bemanning/Rekrytering",
    "Aura Personal AB":                                 "Bemanning/Rekrytering",
    "Avanzera AB":                                      "Bemanning/Rekrytering",
    "Awexia Executive Search AB":                       "Bemanning/Rekrytering",
    "A Hub AB":                                         "Bemanning/Rekrytering",
    "Balkefors & Ponsiluoma Aktiebolag":                "Bemanning/Rekrytering",
    "Barona Professionals AB":                          "Bemanning/Rekrytering",
    "Boxflow Staffing Syd AB":                          "Bemanning/Rekrytering",
    "Bravura Sverige AB":                               "Bemanning/Rekrytering",
    "Charlie AB":                                       "Bemanning/Rekrytering",
    "Clockwork Bemanning & Rekrytering AB":             "Bemanning/Rekrytering",
    "Co-Worker Technology Sweden AB":                   "Bemanning/Rekrytering",
    "Consensus Sverige AB":                             "Bemanning/Rekrytering",
    "Consort Nordic AB":                                "Bemanning/Rekrytering",
    "Delta Consulting AB":                              "Bemanning/Rekrytering",
    "Eqwiry AB":                                        "Bemanning/Rekrytering",
    "Flodin Rekrytering & Bemanning AB":                "Bemanning/Rekrytering",
    "Framtiden i Sverige AB":                           "Bemanning/Rekrytering",
    "Friday Väst AB":                                   "Bemanning/Rekrytering",
    "Hero AB":                                          "Bemanning/Rekrytering",
    "Hire Solutions AB":                                "Bemanning/Rekrytering",
    "Hireq AB":                                         "Bemanning/Rekrytering",
    "Ideal BM AB":                                      "Bemanning/Rekrytering",
    "Insitepart AB":                                    "Bemanning/Rekrytering",
    "Job Solution Sweden Consulting AB":                "Bemanning/Rekrytering",
    "Jobandtalent Sweden AB":                           "Bemanning/Rekrytering",
    "Jobbakuten Väst AB":                               "Bemanning/Rekrytering",
    "Jobbusters AB":                                    "Bemanning/Rekrytering",
    "Jobway AB":                                        "Bemanning/Rekrytering",
    "Jobs Europe AB":                                   "Bemanning/Rekrytering",
    "Jovi Konsult AB":                                  "Bemanning/Rekrytering",
    "Jurek Recruitment & Consulting AB":                "Bemanning/Rekrytering",
    "Kraftsam Rekrytering & Bemanning AB":              "Bemanning/Rekrytering",
    "Lernia Bemanning AB":                              "Bemanning/Rekrytering",
    "Libera i Sverige AB":                              "Bemanning/Rekrytering",
    "Logent Bemanning AB":                              "Bemanning/Rekrytering",
    "Lyten Ett AB":                                     "Bemanning/Rekrytering",
    "MACC PEOPLE AB":                                   "Bemanning/Rekrytering",
    "Medla Sverige AB":                                 "Bemanning/Rekrytering",
    "Mpya Finance AB":                                  "Bemanning/Rekrytering",
    "MultiMind Holding AB":                             "Bemanning/Rekrytering",
    "Nexer Recruit AB":                                 "Bemanning/Rekrytering",
    "Nexify bemanning & rekrytering AB":                "Bemanning/Rekrytering",
    "OIO Väst AB":                                      "Bemanning/Rekrytering",
    "OnePartnerGroup GGVV AB":                          "Bemanning/Rekrytering",
    "OnePartnerGroup Halland AB":                       "Bemanning/Rekrytering",
    "OnePartnerGroup Jönköping AB":                     "Bemanning/Rekrytering",
    "Palmelind Konsult AB":                             "Bemanning/Rekrytering",
    "PartnerFlow Group AB":                             "Bemanning/Rekrytering",
    "Påverka Nu Sverige AB":                            "Bemanning/Rekrytering",
    "People of Interim & Finance Sweden AB":            "Bemanning/Rekrytering",
    "Performiq AB":                                     "Bemanning/Rekrytering",
    "PersonalExpressen AB":                             "Bemanning/Rekrytering",
    "Pokayoke AB":                                      "Bemanning/Rekrytering",
    "Poolia AB":                                        "Bemanning/Rekrytering",
    "Posti Logistics Staffing AB":                      "Bemanning/Rekrytering",
    "Procruitment AB":                                  "Bemanning/Rekrytering",
    "Professionals Nord Eskilstuna AB":                 "Bemanning/Rekrytering",
    "Professionals Nord Linköping AB":                  "Bemanning/Rekrytering",
    "Professionals Nord Norra Norrland AB":             "Bemanning/Rekrytering",
    "Ps Partner AB":                                    "Bemanning/Rekrytering",
    "Randstad AB":                                      "Bemanning/Rekrytering",
    "Recruitive AB":                                    "Bemanning/Rekrytering",
    "Responda Group AB":                                "Bemanning/Rekrytering",
    "Resultat i Sverige AB":                            "Bemanning/Rekrytering",
    "Sanandum AB":                                      "Bemanning/Rekrytering",
    "Simplex Bemanning AB":                             "Bemanning/Rekrytering",
    "SJR in Sweden AB":                                 "Bemanning/Rekrytering",
    "Skill Kompetenspartner AB":                        "Bemanning/Rekrytering",
    "Sorenson Recruiting":                              "Bemanning/Rekrytering",
    "STANDBY WORKTEAM AB":                              "Bemanning/Rekrytering",
    "StudentConsulting Sweden AB (publ)":               "Bemanning/Rekrytering",
    "Studentconsulting Sweden AB":                      "Bemanning/Rekrytering",
    "Studentconsulting Sweden AB (Publ)":               "Bemanning/Rekrytering",
    "Submit AB":                                        "Bemanning/Rekrytering",
    "Sway Sourcing Sweden AB":                          "Bemanning/Rekrytering",
    "Sway Sourcing Sweden Aktiebolag":                  "Bemanning/Rekrytering",
    "Systrarnas bemanning AB":                          "Bemanning/Rekrytering",
    "Te Crea Care AB":                                  "Bemanning/Rekrytering",
    "Techrytera AB":                                    "Bemanning/Rekrytering",
    "Technologist 365 AB":                              "Bemanning/Rekrytering",
    "Tng Group AB":                                     "Bemanning/Rekrytering",
    "Tranpenad AB":                                     "Bemanning/Rekrytering",
    "Uniflex AB":                                       "Bemanning/Rekrytering",
    "Unik Resurs i Sverige AB":                         "Bemanning/Rekrytering",
    "UNIK Resurs i Sverige AB":                         "Bemanning/Rekrytering",
    "Urbansgruppen AB":                                 "Bemanning/Rekrytering",
    "Vindex AB":                                        "Bemanning/Rekrytering",
    "Viraliv AB":                                       "Bemanning/Rekrytering",
    "Viva Bemanning AB":                                "Bemanning/Rekrytering",
    "Vårdbemanning Sverige AB":                         "Bemanning/Rekrytering",
    "VårdIX AB":                                        "Bemanning/Rekrytering",
    "WeStaff Sweden AB":                                "Bemanning/Rekrytering",
    "Workz Sweden AB":                                  "Bemanning/Rekrytering",
    "Wrknest AB":                                       "Bemanning/Rekrytering",
    "Xamera AB":                                        "Bemanning/Rekrytering",
    "CO-WORKER TECHNOLOGY SWEDEN AB":                   "Bemanning/Rekrytering",
    "LERNIA BEMANNING AB":                              "Bemanning/Rekrytering",
    "TNG Group AB":                                     "Bemanning/Rekrytering",
    "DFDS Professionals AB":                            "Bemanning/Rekrytering",
    "The Place AB":                                     "Bemanning/Rekrytering",
    "AdwiseHR i Väst AB":                               "Bemanning/Rekrytering",
    "NearYou Sverige AB":                               "Bemanning/Rekrytering",
    "The Finance Family AB":                            "Bemanning/Rekrytering",
    "Intensogruppen AB":                                "Bemanning/Rekrytering",
    "Integro Consulting AB":                            "Bemanning/Rekrytering",
    "LN Personal AB":                                   "Bemanning/Rekrytering",
    "NDP IT AB":                                        "Bemanning/Rekrytering",
    "Quattro Bemanning & Rekrytering AB":               "Bemanning/Rekrytering",
    "2Complete AB":                                     "Bemanning/Rekrytering",
    "Snabb Jobb Sverige AB":                            "Bemanning/Rekrytering",
    "MiJob Bemanning & Rekrytering i Sverige AB":       "Bemanning/Rekrytering",
    "Emploid AB":                                       "Bemanning/Rekrytering",
    "Newr AB":                                          "Bemanning/Rekrytering",

    # KONSULTBOLAG
    "AFRY AB":                                          "Konsultbolag",
    "AKKA Talent Management AB":                        "Konsultbolag",
    "Akkodis Sweden Electrical Solutions AB":           "Konsultbolag",
    "Alten Sverige AB":                                 "Konsultbolag",
    "Avalon Innovation Technology AB":                  "Konsultbolag",
    "Avaron AB":                                        "Konsultbolag",
    "AxÖ Consulting AB":                                "Konsultbolag",
    "Capgemini Engineering Sverige AB":                 "Konsultbolag",
    "Centio Consulting Group AB":                       "Konsultbolag",
    "Cloudgruppen Sverige AB":                          "Konsultbolag",
    "Collen AB":                                        "Konsultbolag",
    "Combitech AB":                                     "Konsultbolag",
    "Cubane Solutions AB":                              "Konsultbolag",
    "Devotum AB":                                       "Konsultbolag",
    "Experis AB":                                       "Konsultbolag",
    "Fellowmind Sweden AB":                             "Konsultbolag",
    "GVU AB":                                           "Konsultbolag",
    "Iver Sverige AB":                                  "Konsultbolag",
    "Knightec Group Hardware and Design AB":            "Konsultbolag",
    "Knightec Group Software and Cloud AB":             "Konsultbolag",
    "Knightec Group Compliance and Management AB":      "Konsultbolag",
    "Knowit AB":                                        "Konsultbolag",
    "Knowit AB (Publ)":                                 "Konsultbolag",
    "Lynqa AB":                                         "Konsultbolag",
    "Nexer AB":                                         "Konsultbolag",
    "Quest Consulting Sverige AB":                      "Konsultbolag",
    "SKPA Consulting AB":                               "Konsultbolag",
    "Semicon Service Nordic AB":                        "Konsultbolag",
    "Sopra Steria Sweden AB":                           "Konsultbolag",
    "Syntronic AB":                                     "Konsultbolag",
    "SYNTRONIC AKTIEBOLAG":                             "Konsultbolag",
    "Knowit Aktiebolag (publ)":                         "Konsultbolag",
    "One Nordic AB":                                    "Direktarbetsgivare",
    "Veritaz AB":                                       "Konsultbolag",

    # DIREKTARBETSGIVARE
    "44:AN FÖRVALTNINGS AKTIEBOLAG":                    "Direktarbetsgivare",
    "ABB AB":                                           "Direktarbetsgivare",
    "Aleo Care AB":                                     "Direktarbetsgivare",
    "Aleris Sjukvård AB":                               "Direktarbetsgivare",
    "Allegio Omsorg AB":                                "Direktarbetsgivare",
    "Arken Zoo AB":                                     "Direktarbetsgivare",
    "Arvika kommun":                                    "Direktarbetsgivare",
    "Astani Wear AB":                                   "Direktarbetsgivare",
    "Attendo Sverige AB":                               "Direktarbetsgivare",
    "Axis Communications AB":                           "Direktarbetsgivare",
    "AXIS COMMUNICATIONS AKTIEBOLAG":                   "Direktarbetsgivare",
    "Bae Systems Hägglunds AB":                         "Direktarbetsgivare",
    "BODENS KOMMUN":                                    "Direktarbetsgivare",
    "BOTKYRKA KOMMUN":                                  "Direktarbetsgivare",
    "Capio Sverige AB":                                 "Direktarbetsgivare",
    "Concentrix Sweden AB":                             "Direktarbetsgivare",
    "DEROME AKTIEBOLAG":                                "Direktarbetsgivare",
    "E.ON Sverige Aktiebolag":                          "Direktarbetsgivare",
    "Epiroc Rock Drills Aktiebolag":                    "Direktarbetsgivare",
    "Eveo AB":                                          "Direktarbetsgivare",
    "Falkenbergs kommun":                               "Direktarbetsgivare",
    "Fibio Nordic AB":                                  "Direktarbetsgivare",
    "First Camp Sverige AB":                            "Direktarbetsgivare",
    "Forenede Care AB":                                 "Direktarbetsgivare",
    "FÖREN BLOMSTERFONDEN":                             "Direktarbetsgivare",
    "Foundever Sweden AB":                              "Direktarbetsgivare",
    "Försäkringskassan":                                "Direktarbetsgivare",
    "Försvarets Materielverk":                          "Direktarbetsgivare",
    "Gävle kommun":                                     "Direktarbetsgivare",
    "GÖTEBORGS KOMMUN":                                 "Direktarbetsgivare",
    "Göteborgs Universitet":                            "Direktarbetsgivare",
    "H & K Entreprenad AB":                             "Direktarbetsgivare",
    "H & M Hennes & Mauritz Gbc AB":                    "Direktarbetsgivare",
    "Hemfrid i Sverige AB":                             "Direktarbetsgivare",
    "Hitachi Energy Sweden AB":                         "Direktarbetsgivare",
    "HÖGSKOLAN I SKÖVDE":                               "Direktarbetsgivare",
    "Humana AB":                                        "Direktarbetsgivare",
    "Ingka Services AB":                                "Direktarbetsgivare",
    "Jollyroom AB":                                     "Direktarbetsgivare",
    "Kronans Apotek AB":                                "Direktarbetsgivare",
    "Kungälvs kommun":                                  "Direktarbetsgivare",
    "KUNGSBACKA KOMMUN":                                "Direktarbetsgivare",
    "Lifestyle Media Partner Sverige AB":               "Direktarbetsgivare",
    "LINKÖPINGS KOMMUN":                                "Direktarbetsgivare",
    "Lovable Labs Sweden AB":                           "Direktarbetsgivare",
    "Lunds kommun":                                     "Direktarbetsgivare",
    "Lycksele kommun":                                  "Direktarbetsgivare",
    "Maskinförsäljning Europa AB":                      "Direktarbetsgivare",
    "Mervida AB":                                       "Direktarbetsgivare",
    "NCC AKTIEBOLAG":                                   "Direktarbetsgivare",
    "Noga Omsorg Haninge AB":                           "Direktarbetsgivare",
    "Norlandia Care AB":                                "Direktarbetsgivare",
    "Omsorg & Behandling 1 AB":                         "Direktarbetsgivare",
    "Prima Printer Nordic AB":                          "Direktarbetsgivare",
    "REGION GÄVLEBORG":                                 "Direktarbetsgivare",
    "REGION GOTLAND":                                   "Direktarbetsgivare",
    "REGION JÄMTLAND HÄRJEDALEN":                       "Direktarbetsgivare",
    "REGION JÖNKÖPINGS LÄN":                            "Direktarbetsgivare",
    "REGION NORRBOTTEN":                                "Direktarbetsgivare",
    "REGION SKÅNE":                                     "Direktarbetsgivare",
    "REGION STOCKHOLM":                                 "Direktarbetsgivare",
    "REGION SÖRMLAND":                                  "Direktarbetsgivare",
    "REGION UPPSALA":                                   "Direktarbetsgivare",
    "REGION VÄSTERBOTTEN":                              "Direktarbetsgivare",
    "REGION ÖSTERGÖTLAND":                              "Direktarbetsgivare",
    "Releasy Customer Management AB":                   "Direktarbetsgivare",
    "Rituals Cosmetics Sweden AB":                      "Direktarbetsgivare",
    "SAAB AB":                                          "Direktarbetsgivare",
    "SAAB AKTIEBOLAG":                                  "Direktarbetsgivare",
    "SAMESKOLSTYRELSEN":                                "Direktarbetsgivare",
    "Sellhelp AB":                                      "Direktarbetsgivare",
    "Siemens Energy AB":                                "Direktarbetsgivare",
    "Silex Microsystems AB":                            "Direktarbetsgivare",
    "SJ AB":                                            "Direktarbetsgivare",
    "SKARA KOMMUN":                                     "Direktarbetsgivare",
    "Skatteverket":                                     "Direktarbetsgivare",
    "Stockholms kommun":                                "Direktarbetsgivare",
    "STOCKHOLMS LIVSMEDELSHANDLAREFÖRENING":            "Direktarbetsgivare",
    "Svenska Kraftnät":                                 "Direktarbetsgivare",
    "Svenska Trygghetslösningar AB":                    "Direktarbetsgivare",
    "Synsam Group Sweden AB":                           "Direktarbetsgivare",
    "Takteam i Sverige AB":                             "Direktarbetsgivare",
    "Teleperformance Nordic AB":                        "Direktarbetsgivare",
    "Transcom AB":                                      "Direktarbetsgivare",
    "Trädgårdsanläggare Hallblom AB":                   "Direktarbetsgivare",
    "Täta Tak Energi Sverige AB":                       "Direktarbetsgivare",
    "Ur & Penn AB":                                     "Direktarbetsgivare",
    "Uppsala Universitet":                              "Direktarbetsgivare",
    "VADSTENA KOMMUN":                                  "Direktarbetsgivare",
    "Vardaga AB":                                       "Direktarbetsgivare",
    "Vattenfall AB":                                    "Direktarbetsgivare",
    "Verisure Sverige AB":                              "Direktarbetsgivare",
    "Vinnergi AB":                                      "Direktarbetsgivare",
    "Västervik Miljö och Energi AB":                    "Direktarbetsgivare",
    "VÄSTRA GÖTALANDSREGIONEN":                         "Direktarbetsgivare",
    "YRKESKLÄDER FÖR PROFFS SVERIGE AB":                "Direktarbetsgivare",
    "ÖRNSKÖLDSVIKS KOMMUN":                             "Direktarbetsgivare",
    "FALKENBERGS KOMMUN":                               "Direktarbetsgivare",
    "UMEÅ KOMMUN":                                      "Direktarbetsgivare",
    "KUNGÄLVS KOMMUN":                                  "Direktarbetsgivare",
    "YSTAD KOMMUN":                                     "Direktarbetsgivare",
    "NACKA KOMMUN":                                     "Direktarbetsgivare",
    "LUNDS KOMMUN":                                     "Direktarbetsgivare",
    "ÄLVDALENS KOMMUN":                                 "Direktarbetsgivare",
    "MITTUNIVERSITETET":                                "Direktarbetsgivare",
    "Swedbank AB":                                      "Direktarbetsgivare",
    "S.Bil Stockholm AB":                               "Direktarbetsgivare",
    "VOLVO BUSINESS SERVICES AKTIEBOLAG":               "Direktarbetsgivare",
    "AVL MTC MOTORTESTCENTER AB":                       "Direktarbetsgivare",
    "AKTIEBOLAGET BLÅKLÄDER":                           "Direktarbetsgivare",
    "INDUSTRI SUPPORT VÄRMLAND AB":                     "Direktarbetsgivare",
    "STANDARD AUDIO SYSTEMS AB":                        "Direktarbetsgivare",
    "Nordpolen energi AB":                              "Direktarbetsgivare",
    "FÖRENINGEN TIDIGT FÖRÄLDRASTÖD":                   "Direktarbetsgivare",
    "Doktorse Nordic AB":                               "Direktarbetsgivare",
    "BOKNINGSSERVICE I SVERIGE AB":                     "Direktarbetsgivare",
    "STIFTELSEN BRÄCKE DIAKONI":                        "Direktarbetsgivare",
    "OSKARSHAMNS KOMMUN":                               "Direktarbetsgivare",
    "LIDKÖPINGS KOMMUN":                                "Direktarbetsgivare",
    "FALKÖPINGS KOMMUN":                                "Direktarbetsgivare",
    "SALEMS KOMMUN":                                    "Direktarbetsgivare",
    "ÖDESHÖGS KOMMUN":                                  "Direktarbetsgivare",
    "JÄRFÄLLA KOMMUN":                                  "Direktarbetsgivare",
    "GÄLLIVARE KOMMUN":                                 "Direktarbetsgivare",
    "LÄNSSTYRELSEN I VÄSTRA GÖTALANDS LÄN":             "Direktarbetsgivare",
    "Micasa Fastigheter i Stockholm AB":                "Direktarbetsgivare",

    # TILLAGDA 14 JUNI 2026 – veckans granskning av okanda_arbetsgivare_ny.txt
    "REGION DALARNA":                                   "Direktarbetsgivare",
    "VÄRNAMO KOMMUN":                                   "Direktarbetsgivare",
    "STATENS MUSIKVERK":                                "Direktarbetsgivare",
    "LUNDS UNIVERSITET":                                "Direktarbetsgivare",
    "NKT HV Cables AB":                                 "Direktarbetsgivare",
    "Stegra AB":                                        "Direktarbetsgivare",
    "P94 Group AB":                                     "Direktarbetsgivare",
    "Aleja AB":                                         "Bemanning/Rekrytering",
    "A-Talent Tech Management Sweden AB":               "Bemanning/Rekrytering",
    "Nordisk kompetens AB":                             "Bemanning/Rekrytering",
    "Manpower Aktiebolag":                              "Bemanning/Rekrytering",
    "Gazella AB":                                       "Bemanning/Rekrytering",
    "BEMANNIA AB (PUBL.)":                              "Bemanning/Rekrytering",

    # TILLAGDA 19 JUNI 2026 – veckans granskning av okanda_arbetsgivare_ny.txt
    "Eccera Professionals AB":                          "Bemanning/Rekrytering",
    "JobBusters Aktiebolag":                            "Bemanning/Rekrytering",
    "Incluso AB":                                       "Bemanning/Rekrytering",
    "Sententia Rekrytering & Konsult AB":               "Bemanning/Rekrytering",
    "Perido AB":                                        "Bemanning/Rekrytering",
    "RIKSBYGGEN EKONOMISK FÖRENING":                    "Direktarbetsgivare",
    "SIGTUNA KOMMUN":                                   "Direktarbetsgivare",
    "Bredablick Förvaltning i Sverige AB":              "Direktarbetsgivare",
    "Jicon Works AB":                                   "Direktarbetsgivare",
    "HARALD PIHL AKTIEBOLAG":                           "Direktarbetsgivare",

    # TILLAGDA 15 JUNI 2026
    "ULRICEHAMNS KOMMUN":                               "Direktarbetsgivare",
    "Tiohundra AB":                                     "Direktarbetsgivare",
    "BokFix AB":                                        "Direktarbetsgivare",

    # TILLAGDA 16 JUNI 2026
    "Valora bemanning AB":                              "Bemanning/Rekrytering",
    "REGION VÄSTERNORRLAND":                            "Direktarbetsgivare",
    "JOKKMOKKS KOMMUN":                                 "Direktarbetsgivare",
    "BERGS KOMMUN":                                     "Direktarbetsgivare",
    "Needo Recruitment Sthlm AB":                       "Bemanning/Rekrytering",
    "Nordic Exsense AB":                                "Bemanning/Rekrytering",

    # TILLAGDA 17 JUNI 2026
    "Health Connect 365 AB":                            "Bemanning/Rekrytering",
    "Alten Sverige Aktiebolag":                         "Konsultbolag",
    "Senzum AB":                                        "Direktarbetsgivare",
    "Assistansbolaget Försäkring Sverige AB":            "Direktarbetsgivare",
    "HR Resursen på västkusten AB":                     "Bemanning/Rekrytering",
    "Sandvik Aktiebolag":                               "Direktarbetsgivare",
    "VägJobb i Sverige AB":                             "Direktarbetsgivare",
    "Lundin & Boström HR AB":                           "Bemanning/Rekrytering",
    "TULLVERKET":                                       "Direktarbetsgivare",
    # 2026-06-27
    "OFELIA VÅRD AB":                                   "Bemanning/Rekrytering",
    "Promediqa Group Sweden AB":                        "Bemanning/Rekrytering",
    "Bertrandt Sverige AB":                             "Konsultbolag",
    "Tata Technologies Nordics AB":                     "Konsultbolag",
    "The We Select Company AB":                         "Bemanning/Rekrytering",
    "FVB SVERIGE AB":                                   "Konsultbolag",
    "Indivd AB":                                        "Direktarbetsgivare",
    "BORÅS KOMMUN":                                     "Direktarbetsgivare",
    "GINA TRICOT AB":                                   "Direktarbetsgivare",
    "DALOC TRÄDÖRRAR AKTIEBOLAG":                       "Direktarbetsgivare",
    "KARLSTADS KOMMUN":                                 "Direktarbetsgivare",
    "MÖLNDALS KOMMUN":                                  "Direktarbetsgivare",
    "MJÖLBY KOMMUN":                                    "Direktarbetsgivare",
    # 2026-07-10
    "Hemstyrkan i Stockholm AB":                        "Direktarbetsgivare",
    "UPPSALA KOMMUN":                                   "Direktarbetsgivare",
    "SAAND Service & Omsorg AB":                        "Direktarbetsgivare",
    "KINDA KOMMUN":                                     "Direktarbetsgivare",
    "Hirely AB":                                        "Bemanning/Rekrytering",
    "AKTIEBOLAGET TETRA PAK":                           "Direktarbetsgivare",
    "VÄXJÖ KOMMUN":                                     "Direktarbetsgivare",
    "Collen Aktiebolag":                                "Direktarbetsgivare",
    "KRAMFORS KOMMUN":                                  "Direktarbetsgivare",
    "EISS Rekrytering & Search AB":                     "Bemanning/Rekrytering",
    "Soltech Energy Sweden AB (publ)":                  "Direktarbetsgivare",
    # 2026-07-04
    "Etteplan Sweden AB":                               "Konsultbolag",
    "Norconsult Sverige AB":                            "Konsultbolag",
    "Sodajo Consulting AB":                             "Konsultbolag",
    "Ernst & Young Aktiebolag":                         "Konsultbolag",
    "KFX HR-partner Skandinavien AB":                   "Bemanning/Rekrytering",
    "Novare Bemanning AB":                              "Bemanning/Rekrytering",
    "TROLLHÄTTANS KOMMUN":                              "Direktarbetsgivare",
    "Digental AB":                                      "Direktarbetsgivare",
    "REGION KRONOBERG":                                 "Direktarbetsgivare",
    "FÖRSVARSMAKTEN":                                   "Direktarbetsgivare",
    "Boliden Mineral AB":                               "Direktarbetsgivare",
    "STOCKHOLMS UNIVERSITET":                           "Direktarbetsgivare",
    "MEKOMEK i Flen AB":                                "Direktarbetsgivare",
    # 2026-07-01
    "Combitech Aktiebolag":                             "Konsultbolag",
    "BAE Systems Hägglunds Aktiebolag":                 "Direktarbetsgivare",
    "Prowork Bemanning AB":                             "Bemanning/Rekrytering",
    "Medkomp Vårdbemanning Aktiebolag":                 "Bemanning/Rekrytering",
    "TaxiCaller Nordic AB":                             "Direktarbetsgivare",
    "ICOMERA AB":                                       "Direktarbetsgivare",
    # 2026-06-30
    "HALMSTADS KOMMUN":                                 "Direktarbetsgivare",
    "AB Effektiv Väst":                                 "Bemanning/Rekrytering",
    "Assistansporten AB":                               "Direktarbetsgivare",
    "MÄLARDALENS UNIVERSITET":                          "Direktarbetsgivare",
    "STATENS INSTITUTIONSSTYRELSE":                     "Direktarbetsgivare",
    "Din Rekryteringspartner i Umeå AB":                "Bemanning/Rekrytering",
    "SKELLEFTEÅ LASTBILSSTATION AKTIEBOLAG":            "Direktarbetsgivare",
    "SIMRISHAMNS KOMMUN":                               "Direktarbetsgivare",
    "ICA SVERIGE AB":                                   "Direktarbetsgivare",
    "AF Bygg Syd AB":                                   "Direktarbetsgivare",
}

# ── Cache – laddas en gång vid start ────────────────────────────────
def _ladda_cache() -> dict:
    if os.path.exists(CACHE_FIL):
        try:
            with open(CACHE_FIL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _spara_cache(cache: dict):
    try:
        with open(CACHE_FIL, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  Varning: kunde inte spara cache: {e}")

def _slå_upp_sni(org_nr: str) -> str:
    """Slår upp SNI-kod via Bolagsverkets API. Returnerar kategori."""
    org_nr_rensat = org_nr.replace("-", "").strip()
    if not org_nr_rensat or len(org_nr_rensat) < 10:
        return "Okänd – granska"
    url = f"https://api.bolagsverket.se/foretagsinformation/v1/foretag/{org_nr_rensat}"
    try:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read())
        sni = (
            data.get("sni_kod") or
            data.get("branschkod") or
            data.get("sni") or ""
        )
        if sni:
            sni_short = str(sni).replace(".", "").replace(" ", "")[:4]
            return SNI_MAPPNING.get(sni_short, "Direktarbetsgivare")
        return "Direktarbetsgivare"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "Okänd – granska"
        return "Okänd – granska"
    except Exception:
        return "Okänd – granska"

_ag_cache = _ladda_cache()
_cache_ändrad = False

# Case-insensitive lookup-tabell – byggs en gång vid start
_ARBETSGIVARE_TYP_LOWER = {k.lower(): v for k, v in ARBETSGIVARE_TYP.items()}
_EXKLUDERA_LOWER = {e.lower() for e in EXKLUDERA}

def klassificera_ag(namn: str, org_nr: str = "") -> str:
    """
    Klassificerar arbetsgivare. Prioritetsordning:
      1. Exkluderingslista (exakt + case-insensitive)
      2. Manuell lista (exakt + case-insensitive)
      3. Cache (tidigare API-uppslag, nyckel = org_nr eller namn)
      4. Bolagsverkets API (nytt uppslag om org_nr finns)
      5. Okänd – granska
    """
    global _ag_cache, _cache_ändrad

    # Exkludera – exakt
    if namn in EXKLUDERA:
        return "Exkludera"
    # Exkludera – case-insensitive
    if namn.lower() in _EXKLUDERA_LOWER:
        return "Exkludera"

    # Manuell lista – exakt
    if namn in ARBETSGIVARE_TYP:
        return ARBETSGIVARE_TYP[namn]
    # Manuell lista – case-insensitive fallback
    if namn.lower() in _ARBETSGIVARE_TYP_LOWER:
        return _ARBETSGIVARE_TYP_LOWER[namn.lower()]

    cache_nyckel = org_nr if org_nr else namn
    if cache_nyckel in _ag_cache:
        return _ag_cache[cache_nyckel]

    if org_nr:
        time.sleep(0.2)
        kategori = _slå_upp_sni(org_nr)
        _ag_cache[cache_nyckel] = kategori
        _cache_ändrad = True
        return kategori

    return "Okänd – granska"

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
    region_counter    = Counter()
    kommun_counter    = Counter()
    ag_counter        = Counter()
    ag_orgnr          = {}
    orgnr_to_name     = {}
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

            emp = h.get("employer", {})
            ag_raw = emp.get("name", "").strip()
            org_nr = emp.get("organization_number", "")
            if ag_raw:
                if org_nr and org_nr in orgnr_to_name:
                    ag = orgnr_to_name[org_nr]
                else:
                    ag = ag_raw
                    if org_nr:
                        orgnr_to_name[org_nr] = ag
                ag_counter[ag] += 1
                if org_nr and ag not in ag_orgnr:
                    ag_orgnr[ag] = org_nr

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
        "ag_orgnr":          ag_orgnr,
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

    trettio = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_30d = hamta_alla(ids, extra_params={"published-after": trettio})

    fjorton = (datetime.now(timezone.utc) - timedelta(days=14)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    nya_14d = hamta_alla(ids, extra_params={"published-after": fjorton})

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
        "ag_orgnr":         alla["ag_orgnr"],
        "pct_erfarenhet":   alla["pct_erfarenhet"],
        "pct_nystartsjobb": alla["pct_nystartsjobb"],
        "pct_heltid":       alla["pct_heltid"],
        "pct_tills_vidare": alla["pct_tills_vidare"],
        "pct_lang":         alla["pct_lang"],
        "pct_kort":         alla["pct_kort"],
    }

def kör_analys():
    datum     = datetime.now().strftime("%Y-%m-%d")
    klockslag = datetime.now().strftime("%H:%M")
    is_baseline = not os.path.exists(HUVUDFIL)

    # ── Dublett-kontroll – kör aldrig två gånger samma dag ───────────
    if os.path.exists(HUVUDFIL):
        with open(HUVUDFIL, "r", encoding="utf-8-sig") as f:
            for rad in f:
                if rad.startswith(datum):
                    print(f"Already ran today ({datum}) – avslutar utan att skriva.")
                    return

    print("=" * 65)
    print("ARBETSMARKNADSINDEX v7")
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
                w.writerow([datum, roll, grupp, is_baseline] + ["Fel"] * 16)
                continue
            ag_items = [
                (ag, n, klassificera_ag(ag, d['ag_orgnr'].get(ag, '')))
                for ag, n in d["ag_counter"].most_common(20)
            ]
            ag_klassad = " | ".join(
                f"{ag} ({n}) [{kat}]"
                for ag, n, kat in ag_items
                if kat != "Exkludera"
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

    # ── Rapportera okända arbetsgivare – skrivs om varje körning ─────
    okanda_detaljer = {}  # ag -> {"roller": [...], "org_nr": "", "totalt": 0}
    for roll, d in resultat.items():
        if d is None: continue
        for ag, antal in d["ag_counter"].most_common(20):
            org_nr = d["ag_orgnr"].get(ag, "")
            if klassificera_ag(ag, org_nr) == "Okänd – granska":
                if ag not in okanda_detaljer:
                    okanda_detaljer[ag] = {"roller": [], "org_nr": org_nr, "totalt": 0}
                okanda_detaljer[ag]["roller"].append(f"{roll} ({antal})")
                okanda_detaljer[ag]["totalt"] += antal

    with open(OKANDA_FIL, "w", encoding="utf-8") as f:
        f.write(f"OKÄNDA ARBETSGIVARE – {datum}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Antal okända: {len(okanda_detaljer)}\n")
        f.write("Kontrollera en gång i veckan och lägg till i ARBETSGIVARE_TYP\n\n")
        if okanda_detaljer:
            for ag in sorted(okanda_detaljer, key=lambda x: -okanda_detaljer[x]["totalt"]):
                info = okanda_detaljer[ag]
                org_str = f"  org.nr: {info['org_nr']}" if info["org_nr"] else ""
                roller_str = ", ".join(info["roller"])
                f.write(f"  {ag:<50} totalt={info['totalt']}  [{roller_str}]{org_str}\n")
        else:
            f.write("  Inga okända arbetsgivare – alla klassificerade.\n")

    if okanda_detaljer:
        print(f"\n⚠️  {len(okanda_detaljer)} okända arbetsgivare – se {OKANDA_FIL}")
    else:
        print(f"\n✓ Alla arbetsgivare klassificerade.")

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

    # ── Spara cache om den ändrats ───────────────────────────────────
    if _cache_ändrad:
        _spara_cache(_ag_cache)
        print(f"  Cache uppdaterad: {len(_ag_cache)} bolag sparade i arbetsgivare_cache.json")

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
