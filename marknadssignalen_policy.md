# Marknadssignalen – Redaktionell policy
*arbetsmarknadsdata.se · Version 1.0 · Juni 2026*

---

## Vad vi är

Ett datanyhetsbrev som rapporterar vad AF-annonsdata visar.
Vi tolkar inte. Vi drar inga slutsatser. Vi hjälper läsaren se mönster i data de inte har tid att ta fram själva.

**Vi är aldrig mer säkra än datan tillåter.**

---

## Vad vi mäter

Antal aktiva annonser på Arbetsförmedlingen för:
- 30 utvalda bemannings- och rekryteringsbolag (bemanningsindex)
- 9 signalroller (arbetsmarknadsindex)

Det är ett mått på synlig rekryteringsaktivitet i AF-kanalen – inte på omsättning, tillsatta tjänster eller branschens faktiska volym.

**Denna begränsning kommuniceras alltid, kort, i varje nummer.**

---

## Vad varje brev alltid innehåller

### 1. Marknadspuls
Rullande tvåveckorssnitt (v.N + v.N-1 mot v.N-2 + v.N-3).
Aldrig enskild vecka mot enskild vecka som primärt mått.
Varför: tvåveckorssnittet dämpar kalendereffekter (midsommar, påsk, klämdagar) utan att vi behöver förklara dem varje gång.

Format: tre tal – period A, period B, förändring i procent och absolut. Inget mer.

### 2. Momentumspår – bolag
De tre bolag med starkast uppåtgående och nedåtgående linjär trend senaste fyra veckorna.
Beräknat som lutning (polyfit), inte enskild veckas rörelse.
Fast regel, körs varje gång, presenteras utan tolkning.

### 3. Signalrollstabell
Alla nio roller. Tre kolumner: aktuellt värde, förändring sedan förra numret, status sedan mätstart.
Status är mekanisk: NY LÄGSTANIVÅ / NY HÖGSTANIVÅ / ÅTERHÄMTNING / NORMALT.
Ingen friformstext per roll.

### 4. Avvikelseblock (kan vara tomt)
Bolag eller roller som avviker mer än två standardavvikelser från sitt eget historiska mönster.
Om inget passerar tröskeln: en rad som säger det.
Om något passerar: vad avviker, hur mycket, sedan när. Ingen tolkning av varför.

---

## Vad vi aldrig skriver

- Slutsatser om varför något rör sig ("troligen på grund av...")
- Råd eller rekommendationer ("bolag bör fokusera på...")
- Starka påståenden om framtiden ("signalerar att...")
- Dramatiseringar av säsongsnormala rörelser

**Undantag:** En kort kalenderrad i ingressen när det är uppenbart relevant.
Format: *"v.25 sammanfaller med midsommar."* En mening, sedan vidare.

---

## Hypoteslogg

Varje gång vi lyfter ett observerat mönster som vi "följer vidare" –
ska det loggas med datum och ett uppföljningsdatum.

Format i brevet: *"Vi följer om [X] håller i sig. Nästa kontroll: [datum]."*
Uppföljningen sker alltid i det nummer vars datum är utlovat.
Om mönstret inte höll: det sägs rakt ut.

---

## Datakvalitetsregler

**Volymdata (Antal annonser):** Tillförlitlig från mätstart (18/20 maj 2026).

**Top 20 arbetsgivare och regiondata i arbetsmarknadsindex:**
Tillförlitlig från 9 juni 2026. Används inte för analys av perioden dessförinnan.

**Regiondata (separata regionalfiler):**
Används som kontextuellt stöd, inte som primär story, förrän minst 12 veckors historik finns.

**Kommundata:**
Används inte i nyhetsbrevet ännu. Återprövas när historiken motiverar det.

**Okategoriserade arbetsgivare:**
Exkluderas alltid ur "Vem rekryterar?"-beräkningar. Gissas aldrig.

---

## Kalender och säsong

Dessa veckor behandlas alltid med extra försiktighet:
- Midsommar (v.25 2026, v.25 2027)
- Påsk
- Julveckan (v.52–v.1)
- Klämdagsveckor med >2 röda dagar

Under dessa veckor: rullande tvåveckorssnitt används som enda primärt mått.
Avvikelseblocket tolkas mot säsongsbakgrunden, inte som isolerat fynd.

---

## Publiceringsformat

- Varannan tisdag, kl 07:00
- HTML-format, samma visuella system som Nr 1
- Längd: kortare är bättre. Om vi inte har tre starka avvikelser – skriver vi inte tre avvikelser.
- Nästa nummer annonseras alltid med vad vi specifikt följer upp

---

## Vad som avgör om ett fynd är värt att ta med

Tre krav, alla måste uppfyllas:

1. **Minst tre datapunkter** stödjer mönstret (inte en enskild veckas rörelse)
2. **Mekaniskt verifierbart** – en annan person med samma data ska kunna räkna fram samma siffra
3. **Beskrivbart utan tolkning** – om vi inte kan skriva det som ett faktapåstående är det en hypotes, inte ett fynd

---

*Policyn revideras när mätserien når 20 veckors historik (oktober 2026),
då regiondata och kommundata troligen är mogna för fler dimensioner.*
