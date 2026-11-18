@echo off
REM ============================================================
REM daglig_korning.bat
REM
REM Kor hela den dagliga kedjan i garanterad ordning:
REM 1. Rolldata (arbetsmarknadsindex.py)
REM 2. Bolagsdata (bemanningsindex.py)
REM 3. Rensa dubbletter (dedup.py)
REM 4. Signaler (signalmotor.py)
REM 5. Totalen for hela Platsbanken (platsbanken_index.py) - stoppar INTE
REM    kedjan om det misslyckas
REM 6. Storsta annonsorerna pa hela Platsbanken (platsbanken_annonsorer.py)
REM    - internt kontrollverktyg, stoppar INTE kedjan om det misslyckas
REM 7. Pusha allt till GitHub
REM
REM Om steg 1-4 misslyckas stoppas kedjan (exit /b 1) i stallet for
REM att pusha ofullstandig eller gammal data.
REM ============================================================

cd /d C:\Users\Fahmi\Documents\Arbetsmarknadsindex

echo [%date% %time%] Steg 1/7: arbetsmarknadsindex.py
python arbetsmarknadsindex.py
if errorlevel 1 (
    echo [%date% %time%] FEL i arbetsmarknadsindex.py - avbryter
    exit /b 1
)

echo [%date% %time%] Steg 2/7: bemanningsindex.py
python bemanningsindex.py
if errorlevel 1 (
    echo [%date% %time%] FEL i bemanningsindex.py - avbryter
    exit /b 1
)

echo [%date% %time%] Steg 3/7: dedup.py
python dedup.py
if errorlevel 1 (
    echo [%date% %time%] FEL i dedup.py - avbryter
    exit /b 1
)

echo [%date% %time%] Steg 4/7: signalmotor.py
python signalmotor.py
if errorlevel 1 (
    echo [%date% %time%] FEL i signalmotor.py - avbryter
    exit /b 1
)

echo [%date% %time%] Steg 5/7: platsbanken_index.py
python platsbanken_index.py
if errorlevel 1 (
    echo [%date% %time%] VARNING: platsbanken_index.py misslyckades - fortsatter
)

echo [%date% %time%] Steg 6/7: platsbanken_annonsorer.py
python -u platsbanken_annonsorer.py
if errorlevel 1 (
    echo [%date% %time%] VARNING: platsbanken_annonsorer.py misslyckades - fortsatter med push
)

echo [%date% %time%] Steg 7/7: git push
"C:\Program Files\Git\bin\git.exe" pull --no-edit origin main
"C:\Program Files\Git\bin\git.exe" add *.csv
"C:\Program Files\Git\bin\git.exe" commit -m "Auto-update %date%"
"C:\Program Files\Git\bin\git.exe" push origin main

echo [%date% %time%] Klart - hela kedjan kord.
