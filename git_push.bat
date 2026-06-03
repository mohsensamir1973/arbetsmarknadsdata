@echo off
cd C:\Users\Fahmi\Documents\Arbetsmarknadsindex
"C:\Program Files\Git\bin\git.exe" pull --no-edit origin main
"C:\Program Files\Git\bin\git.exe" add *.csv
"C:\Program Files\Git\bin\git.exe" commit -m "Auto-update %date%"
"C:\Program Files\Git\bin\git.exe" push origin main
