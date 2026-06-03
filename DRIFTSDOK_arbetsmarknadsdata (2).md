# Driftsdokument – arbetsmarknadsdata.se
*Uppdaterat 28 maj 2026*

---

## MORGONRUTIN – kontroll varje dag (tar 5 minuter)

### Steg 1 – Kolla GitHub (kl 09:00)
Gå till: https://github.com/mohsensamir1973/arbetsmarknadsdata

Kolla dessa filer – ska visa dagens datum i commit-meddelandet:
- `arbetsmarknadsindex_trend.csv`
- `bemanningsindex_trend.csv`

Ser du "Auto-update 2026-05-28" (dagens datum) → allt ok.
Ser du gårdagens datum → scriptet har kört men pushen misslyckades. Se felsökning nedan.

### Steg 2 – Kolla sajten (kl 09:00)
Gå till: https://arbetsmarknadsdata.se

Kolla att datumet i eyebrown uppe till vänster ("Arbetsmarknadsdata · 28 maj 2026") är dagens datum.

**Om båda stämmer – du är klar för dagen.**

---

## MANUELL PUSH (när automatiken misslyckas)

Öppna CMD (sök "cmd" i startmenyn) och kör raderna nedan en i taget:

```
cd C:\Users\Fahmi\Documents\Arbetsmarknadsindex
"C:\Program Files\Git\bin\git.exe" pull --no-edit origin main
"C:\Program Files\Git\bin\git.exe" add *.csv
"C:\Program Files\Git\bin\git.exe" commit -m "Manuell push idag"
"C:\Program Files\Git\bin\git.exe" push origin main
```

Ser du "main -> main" i outputen → pushen lyckades.
Ser du "rejected" → kör `pull`-raden igen och försök sedan push igen.

---

## KONTROLLERA ATT SCRIPTS HAR KÖRT

```
cd C:\Users\Fahmi\Documents\Arbetsmarknadsindex
dir arbetsmarknadsindex_trend.csv
dir bemanningsindex_trend.csv
```

Datum och tid på filerna ska vara dagens datum, kl 07:xx respektive 08:xx.

---

## OKÄNDA ARBETSGIVARE – veckorutin (en gång i veckan)

```
cd C:\Users\Fahmi\Documents\Arbetsmarknadsindex
type okanda_arbetsgivare_ny.txt
```

Listan visar bolag som dykt upp i topp 20 men saknar kategori.
Tumregel:
- Kund arbetsleder → `"Bemanning/Rekrytering"`
- Bolaget tar leveransansvar → `"Konsultbolag"`
- Myndighet/region/kommun/direktbolag → `"Direktarbetsgivare"`
- Aggregatorer (DUVI-typen) → lägg INTE in, de stör datan

Bolag med färre än 5–10 annonser = brus, kan vänta.

Lägg till nya bolag i `arbetsmarknadsindex.py` under `ARBETSGIVARE_TYP`.
Ersätt sedan filen i mappen och kör manuell push.

---

## OM GIT KRÅNGLAR

### "rejected – fetch first"
```
"C:\Program Files\Git\bin\git.exe" pull --no-edit origin main
"C:\Program Files\Git\bin\git.exe" push origin main
```

### "You have not concluded your merge"
```
"C:\Program Files\Git\bin\git.exe" merge --abort
"C:\Program Files\Git\bin\git.exe" pull --no-edit origin main
"C:\Program Files\Git\bin\git.exe" push origin main
```

### Hamnat i vim-editorn (konstigt textläge)
Tryck: `Escape` → skriv `:wq` → tryck `Enter`

### Fel mapp i CMD
```
cd C:\Users\Fahmi\Documents\Arbetsmarknadsindex
```

---

## SCRIPTS OCH TIDER

| Script | Tid | Vad den gör |
|--------|-----|-------------|
| arbetsmarknadsindex.py | kl 07:00 | 9 signalroller från AF:s API |
| bemanningsindex.py | kl 08:00 | 30 bolag via org-nummer |
| git_push.bat | kl 07:45 och 08:45 | Pushar CSV:er till GitHub |

Sajten hämtar data från GitHub CDN – cachar 5 minuter.
Sajten är alltså uppdaterad senast kl 09:10 varje vardag.

---

## VIKTIGA FILER OCH VAR DE FINNS

| Fil | Plats | Syfte |
|-----|-------|-------|
| arbetsmarknadsindex.py | C:\Users\Fahmi\Documents\Arbetsmarknadsindex | Script för signalroller |
| bemanningsindex.py | Samma mapp | Script för bemanningsbolag |
| git_push.bat | Samma mapp | Automatisk push till GitHub |
| okanda_arbetsgivare_ny.txt | Samma mapp | Veckovis granskning av nya bolag |
| arbetsmarknadsindex_trend.csv | Samma mapp + GitHub | Signalrollsdata |
| bemanningsindex_trend.csv | Samma mapp + GitHub | Bemanningsbolagsdata |

---

## TASK SCHEDULER – om scripten slutar köra

Öppna Task Scheduler (sök i startmenyn).
Kolla att dessa uppgifter finns och har status "Ready":
- Arbetsmarkn... (kl 07:00)
- Bemanningsi... (kl 08:00)
- Git Push CSV (kl 07:45)
- Git Push CSV... (kl 08:45)

Om "Last Run Result" visar fel:
Högerklicka → Properties → Settings → kryssa i "Run task as soon as possible after a scheduled start is missed"

---

## BREVO – MEJLUTSKICK

API-nyckel: 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
Lista-ID: 3
Nästa utskick: 10 juni kl 07:00

---

## STRATEGISKA INSIKTER ATT INTE GLÖMMA

### KF-rapportens trovärdighet
Den nya KF-rapporten (Q1 2026) kommer förändra rankingen markant.
Anledningen: tidigare har koncernintern omsättning räknats med.
- Manpower har haft Academic Work som underleverantör – den omsättningen har redovisats hos Manpower
- Calviks omsättning kommer till stor del från Keyman (konsultmäklare) – inte ren bemanningsomsättning
- Marknaden är uppblåst med den gamla metodiken

När den nya rapporten kommer och siffrorna ser annorlunda ut – du vet redan varför. Det är en unik möjlighet att publicera en analys som förklarar förändringarna innan alla andra förstår dem.

**Spara detta:** VD på AW har lobbat för detta i branschen. Det är ett legitimt metodproblem, inte kontroversiellt.

### Hypotesen att bevaka
Framåtblickande roller (Business Controller, Systemutvecklare) leder uppgången med +8–10% sedan 18 maj.
Hypotes: volymroller (Kundtjänst, Lager, Ekonomiassistent) följer efter inom 6–8 veckor.
Följs upp: 10 juli 2026.

### Vad produkten ska bli
Inte en dashboard med siffror.
Ett beslutsstöd som svarar på: "Vad ska jag förstå och göra annorlunda efter att ha sett det här?"

Tre lager:
1. Marknadsbild – vad händer? (finns idag)
2. Konkurrensbild – hur rör sig mina konkurrenter? (Konkurrentradar, byggs sept 2026)
3. Kundbilden – vilka av mina kunder/prospects visar tidiga signaler? (framtid)

### Konkurrentradar – rätt timing
Starta i september 2026 när:
- 90+ dagars annonsdata finns
- Årsredovisningar 2025 har börjat komma
- Du har 5 bolag att börja med

Inte nu. Halvgjort skadar trovärdigheten.

### Bemanningsbriefens struktur
1. Marknadspuls – ett tal
2. Tre observationer
3. En hypotes
4. En konkurrentrörelse
5. En säljsignal
6. Reservationsrad om mätseriens längd (tas bort efter 18 juni)

---

## ROADMAP – GROVT

| När | Vad |
|-----|-----|
| Nu – 18 juni | Stabild drift, morgonrutinen fungerar, okända bolag kategoriseras |
| 10 juni | Första Bemanningsbriefens |
| 18 juni | Ta bort reservationstext, uppdatera redaktörskommentar |
| Juli | Hypotes 1 följs upp |
| Augusti | KF Q2-rapport – publicera analys som förklarar metodbytet |
| September | Starta Konkurrentradar med 5 bolag och årsredovisningar |
| Sept–okt | Betalvägg – mål 25 betalande kunder vid årets slut |

---

*Dokumentet uppdateras när något förändras. Håll det enkelt.*
