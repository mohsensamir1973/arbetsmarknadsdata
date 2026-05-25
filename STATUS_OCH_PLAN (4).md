# arbetsmarknadsdata.se – Status och plan
Uppdaterad: 24 maj 2026 (kväll)

## PROJEKT
- Sajt: arbetsmarknadsdata.se (LIVE)
- GitHub: github.com/mohsensamir1973/arbetsmarknadsdata (branch: main)
- Lokalt: C:\Users\Fahmi\Documents\Arbetsmarknadsindex
- Accentfärg: #1D9E75
- Baseline satt: 18 maj 2026

---

## DATAINSAMLING – STATUS

### arbetsmarknadsindex.py (v6)
- Kör dagligen kl 07:00 via Task Scheduler
- 9 signalroller via occupation_group-ID
- CSV: arbetsmarknadsindex_trend.csv ✓
- Skapar okanda_arbetsgivare_ny.txt efter varje körning – granska en gång i veckan

### bemanningsindex.py (v7)
- Kör dagligen kl 08:00 via Task Scheduler
- 30 bolag via organisationsnummer-filtrering
- CSV: bemanningsindex_trend.csv ✓

### git_push.bat
- Kör kl 07:45 och 08:45

### Arbetsgivarlista (ARBETSGIVARE_TYP i arbetsmarknadsindex.py)
- Uppdaterad 24 maj 2026 – 172 bolag kategoriserade
- Tre kategorier: Bemanning/Rekrytering, Konsultbolag, Direktarbetsgivare
- Tumregel: kunden arbetsleder = Bemanning/Rekrytering, bolaget tar leveransansvar = Konsultbolag
- Aggregatorer (t.ex. DUVI) ska inte kategoriseras – de stör datan och tas bort
- Granska okanda_arbetsgivare_ny.txt varje vecka och uppdatera listan vid behov

---

## SIGNALROLLER 24 MAJ (vs baseline 18 maj)
- Kundtjänst: +3,4%
- Ekonomiassistent: +11,6%
- Lagerarbetare: +3,7%
- Business Controller: +6,4%
- Systemutvecklare: +7,5%
- Mekanikkonstruktör: +2,9%
- Elingenjör: +2,9%
- Sjuksköterska: +10,1%
- Undersköterska: +1,2%
Alla roller över baseline. Ekonomiassistent och Sjuksköterska starkast.

---

## BOLAG I BEMANNINGSINDEX (30 st)
Manpower, Lernia, Adecco, Perido, Randstad, Academic Work, Studentconsulting,
Poolia, Uniflex, OnePartnerGroup, Skill, Arena Personal, Tranpenad, Jobandtalent,
NearYou, SJR, Clockwork, Logent, Bemannia, Framtiden i Sverige, Professionals Nord,
Bravura, Jurek, TNG Group, Eterni Sweden, Friday, Gazella, Insitepart, Wikan Personal, Konsultia

---

## SAJT – KOMPONENTSTATUS (senaste versioner i outputs/)

### Klara komponenter:
- Hero.tsx ✓
- KpiKort.tsx ✓ – 30 bolag
- Topp20Tabell.tsx ✓ – Movers-sektion, Share of voice, drill-down
- Signalroller.tsx ✓
- SiteHeader.tsx ✓
- SiteFooter.tsx ✓ – inkl. Metodik-länk
- **Branschradar.tsx ✓ – STOR UPPDATERING 24 maj kväll (se nedan)**
- bransch.tsx ✓ – /bransch
- trender.tsx ✓ – /trender med redaktörskommentar + reservationstext
- metodik.tsx ✓
- analys.tsx ✓ – redirect till /trender

### Meny:
- Dagens data → /
- Trender → /trender
- Marknadsandelar → /bransch
- Metodik → sidfoten

---

## BRANSCHRADAR – STATUS EFTER 24 MAJ

### Datakvalitet:
- **Perioder Total/BC/WC:** 2022 Q4, 2023 Q4, 2024 Q4, 2025 Q4 (renodlat Q4-serie)
- **Perioder Rekrytering:** 2022 Q4, 2024 Q4, 2025 Q1, 2025 Q2, 2025 Q3, 2025 Q4
- Notering: 2023 Q4 för Rekrytering saknas – ej tillgänglig rapport
- Alla KF-bolag från topp 25-rapporterna inkluderade (inte bara de 30 i bemanningsindex)
- Bolag verifierade mot PDF: Total Q4 2022 ✓, BC Q4 2022 ✓, WC Q4 2022 ✓, Q4 2023 alla segment ✓, Rekrytering Q4 2022 ✓

### Funktioner klara:
- 4 segment: Totalt / Blue Collar / White Collar / Rekrytering
- Sparklines med Q4-datapunkter
- TrendBadge: relativ % + pp vs baseline 2022 Q4 (konsekvent för alla segment)
- Sortering: Senast / Förändring / Namn
- Stabila kolumnbredder (tableLayout fixed – ingen hoppning vid segmentbyte)

### LinkedIn-delningsfunktion ✓ KLAR:
- Klicka på bolagsnamn → modal öppnas
- Välj segment i modal: Totalt / Blue Collar / White Collar / Rekrytering
- Topp 25-lista med valt bolag markerat i blått
- Placeringsförändring visas: ▲2 (grön) / ▼3 (röd) / tomt (oförändrad) / NY (grön)
- Ladda ner som PNG 1200×630px (LinkedIn-format)
- PNG-design: neutral mörkblå slate-header (inte sajtens gröna) – ser professionellt ut, ingen förväxlar det med sajtens identitet eller AW
- Header i PNG: "TOPP 25 [SEGMENT]" stort + "KOMPETENSFÖRETAGEN" till höger
- Tydlig attribution: "Baserat på Kompetensföretagens officiella Topp 25-rapport"
- Föregående placering i kortet: ▲/▼/NY direkt efter bolagsnamnet

### Designbeslut Branschradar:
- LinkedIn-kort i neutral slate-färg (#1e293b) – inte sajtens gröna
- Valt bolag markerat i blått (#2563eb) i både modal och PNG
- "ditt bolag markerat i blått" konsekvent i all copy
- Oförändrad placering = tomt (inte "–"), nytt inträde = "NY"
- Tabellkolumner fasta bredder – ingen layout-hoppning

---

## COPY-BESLUT (gäller hela sajten)
- H1: "Marknadsintelligens för bemanningsbranschen – varje dag"
- Ingress: "Vi följer 30 ledande bemannings- och rekryteringsbolag och 9 nyckelroller på Arbetsförmedlingen – varje dag. Så att du som leder ett bemanningsbolag vet var du står, vad konkurrenterna gör och vart marknaden är på väg."
- Mejlkort rubrik: "Få branschbriefen varannan tisdag"
- Bolagstabell rubrik: "Vilka bolag är mest aktiva just nu?"
- Signalroller rubrik: "Vart är efterfrågan på väg?"
- Movers bolag: "Störst rörelse senaste 7 dagarna"
- Movers signalroller: "Starkaste signaler sedan mätstart"
- "30 utvalda bolag" (ej ledande/topp)
- Bloomberg-ton: saklig, faktabaserad
- Tankstreck: – (inte —)
- Inga AI-triggers i copy

---

## DESIGNBESLUT
- Drill-down panel: glider in från höger (desktop), upp från botten (mobil)
- Movers: vit bakgrund, threshold ≥5 annonser för bolag
- Share of voice i bolagspanelen: "Annonsandel X% av 30 bolag totalt"
- Sparklines: div-punkter (aldrig ovala SVG-cirklar)
- "sedan 18 maj" istället för "vs baseline" i all copy
- "✓ Alla roller över baseline" när inga signalroller är nedåt

---

## TEKNISKA BESLUT
- bemanningsindex v7: org-nummer-filtrering i API-svaret
- AF:s API max 2100 träffar per sökning
- Sajten hämtar CSV direkt från raw.githubusercontent.com
- GitHub CDN cachar 5 min
- Google Analytics: G-X2XBT5VL4B (arbetsmarknadsdata.se-property, fixat 24 maj)
- Brevo API: lista-ID 3, prenumeranter: 2
- Lovable använder useIsMobile från @/hooks/use-mobile

---

## REDAKTIONELLA PRINCIPER

### Dataintegritet – vad vi vet vs vad vi tolkar
**Data (fakta):**
- Antal annonser, index vs baseline, nya 7/14 dagar
- Vilka bolag är mest aktiva
- Regionfördelning och arbetsgivarfördelning

**Hypotes (tolkning, kräver reservation):**
- Slutsatser om trender och marknadsmönster
- Jämförelser med historiska mönster

**Standardreservation (gäller till ca 18 juni):**
> "Mätserien startade 18 maj – slutsatser om trender kräver minst 30 dagars data.
> Det vi ser är en riktning, inte ett bekräftat mönster."

### Redaktörskommentarens form
- Beskriv alltid implikation, inte bara observation
- Fel: "Ekonomiassistent steg mest"
- Rätt: "Ekonomiassistent +12% – finans/ekonomikompetens efterfrågas tidigare än normalt inför höst."
- Avsluta alltid med reservation om mätseriens längd när relevant

---

## BEMANNINGSBRIEFENS STRUKTUR (varannan tisdag)
1. Marknadspuls – ett tal som sammanfattar läget
2. Topp 3 signaler – de viktigaste rörelserna sedan förra briefen
3. Movers – bolag som rört sig mest uppåt/nedåt
4. Signalroller – vilken roll är starkast och vad signalerar det
5. Redaktionens take – 3-4 meningar med tolkning + implikation + reservation

### Principer:
- Mejlet ska tillföra mer än sajten – djupare tolkning, explicit jämförelse med förra briefen
- Bloomberg-ton: saklig, faktabaserad
- Kort – ska kunna läsas på 2 minuter
- Ämnesrad specifik: "Systemutvecklare accelererar – vecka 22" inte "Nyhetsbrev"
- Reservation om mätseriens längd i varje mejl fram till 30+ dagars data

---

## REDAKTÖRSKOMMENTAR (aktuell, trender.tsx)
"Business Controller och Ekonomiassistent leder uppgången med +10% sedan mätstart,
följda av Systemutvecklare på +8%. Volymrollerna Kundtjänst och Lagerarbetare är
mer dämpade på +3-4%. Mönstret är konsekvent uppåt i alla kategorier – för tidigt
att dra slutsatser, men riktningen är tydlig."
Datum: 22 maj 2026
Nästa uppdatering: 10 juni 2026

---

## ROADMAP – NÄRMAST

### Åtgärda inom kort:
1. Granska okanda_arbetsgivare_ny.txt efter morgondagens körning (kl 07:00)
2. Komplettera Rekrytering med 2023 Q4 när rapporten hittas

### När vi har 30+ dagars data (från ca 18 juni):
3. Ta bort standardreservationen om mätseriens längd
4. Rullande 30-dagarsvy i panelerna
5. Veckodelta i tabellen
6. Uppdatera redaktörskommentar varannan tisdag
7. Lägg till Movers-bolag och Marknadspuls på /trender
8. Kompetensföretagen Q1 2026 när rapporten kommer
9. Skicka första Bemanningsbriefens när vi har minst 4 veckors data

### Medellång sikt:
10. Betalvägg – "ange ditt bolag" som trigger
11. Koppla Kompetensföretagen mot AF-data explicit
12. Fyll på Branschradar med fler historiska Q4-perioder

### Strategiskt:
13. Styrelserapport-kit
14. Säljmorgon-vy
15. Competitor alerts via mejl
16. Supabase för automatisk sajtuppdatering

---

## ANALYTISK INSIKT ATT BEVAKA
Framåtblickande roller (Business Controller, Systemutvecklare) leder uppgången
före volymroller (Kundtjänst, Lagerarbetare). Historiskt föregår det bredare
rekryteringstillväxt med 1–2 kvartal. Hypotes – kräver bekräftelse med mer data.

Rekryteringsmarknaden (KF-data): -5,4% Q4 2025 vs Q4 2024. Bemanning +8,6%
och omställning +14,1% växer. Intressant divergens värd att bevaka.

Från Branschradar rekrytering: Professionals Nord +164% sedan 2022 Q4, NGS Group
+70%. TNG Group -24%, Randstad -53%. Tydliga vinnare och förlorare sedan 2022.

---

## KONTAKTER
- A-hub – Fahmi känner dem, kontakta om AF-annonsstruktur

---

## BREVO API-NYCKEL
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
Lista-ID: 3
