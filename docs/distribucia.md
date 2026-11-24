# Distribúcia a aktualizácie (fáza 4)

## Rozloženie

```
L:\_Nastroje\                          (spoločné, launcher ho len číta)
  apps.json                            katalóg aplikácií + záznam launchera
  <id>\<verzia>\...                    zostavená aplikácia (jedna verzia = jeden priečinok)
  <id>\CO_JE_NOVE.md                   poznámky k verziám (odkaz `co_je_nove` v apps.json)
  launcher\<verzia>\nc_nastroje.exe    samotný launcher (PyInstaller --onedir)

%LOCALAPPDATA%\NC_Nastroje\            (na každom počítači)
  apps\<id>\<verzia>\...               lokálna kópia, z ktorej sa aplikácia spúšťa
  apps\<id>\_pripnuta.txt              verzia, na ktorú sa používateľ vrátil (Návrat na predchádzajúcu)
  apps\<id>\CO_JE_NOVE.md              lokálna kópia poznámok
  launcher\<verzia>\...                stiahnutá nová verzia launchera
  launcher\aktualna.txt                verzia, ktorú má spustiť štartér po prepnutí
  cache\apps.json (+ apps_koren.txt)   posledný známy katalóg (keď je L:\ nedostupný)
  tmp\cesty_*.txt                      dlhé zoznamy ciest (`@subor.txt`)
```

## Záznam launchera v `apps.json`

Vedľa `aplikacie` je v koreňovom objekte voliteľný kľúč `launcher` (iné programy ho ignorujú):

```json
"launcher": { "verzia": "2026.11.24-4", "zdroj": "launcher\\2026.11.24-4",
              "spustit": "nc_nastroje.exe", "co_je_nove": "launcher\\CO_JE_NOVE.md" }
```

## Ako to beží

- Pri štarte (z cache hneď, bez siete) a potom každých 10 min / na F5 / na „Aktualizovať teraz“:
  na pozadí sa prečíta `apps.json`, uloží sa do cache a porovnajú sa verzie ako tuple `(rok, mesiac, deň, poradie)`.
- Novšia verzia sa skopíruje do `<verzia>.tmp\`, overí sa počet a veľkosť súborov a až potom sa premenuje.
- Ponechá sa aktuálna a jedna predchádzajúca verzia, staršie a nedokončené `*.tmp` sa zmažú.
- Bežiaca aplikácia ostane na starej verzii, nová sa použije pri ďalšom spustení.
- Launcher sa aktualizuje len ako zostavený exe (zo zdrojového kódu nie): stiahne sa nová verzia a po potvrdení
  `aktualizator.bat` počká na ukončenie, zapíše `launcher\aktualna.txt` a spustí novú verziu.

## Publikovanie

```
python nastroje/publikuj.py nastrojovy_list C:\build\nastrojovy_list            # verzia = dnes, ďalšie poradie
python nastroje/publikuj.py launcher C:\build\nc_nastroje --verzia 2026.11.25-1
```

Bez `--koren` sa použije koreň z nastavení (pri vývoji falošný `test_data\L\_Nastroje`). Pri skutočnom koreni
sa skript opýta na potvrdenie. Záznam aplikácie musí v `apps.json` už existovať (`launcher` tiež).

## Voliteľné kľúče záznamu aplikácie v `apps.json`

- `log` – cesta k logu aplikácie (súbor alebo priečinok) pre tlačidlo Log v zobrazení B. Premenné prostredia sa
  rozbalia (`%LOCALAPPDATA%\TNC_Sync\logy`), relatívna cesta je ku koreňu nástrojov. Bez neho je tlačidlo neaktívne.

## Štartér a zástupcovia (fáza 5)

Zástupcovia v „Po spustení“, „Odoslať do“ a na ploche nemieria priamo na `nc_nastroje.exe`, ale (v zostavenom exe)
na štartér `%LOCALAPPDATA%\NC_Nastroje\spustit_launcher.bat`. Ten spustí `launcher\<verzia z aktualna.txt>\nc_nastroje.exe`
(po aktualizácii launchera sa tak spustí nová verzia) a ak `aktualna.txt` chýba, záložný exe, z ktorého bol štartér
vytvorený. Zo zdrojového kódu (vývoj) zástupcovia spúšťajú `pythonw -m nc_nastroje.main`.

Zástupcov vytvára a maže len launcher a len takých, ktorých popis začína „NC Nástroje (spúšťač)“; cudzích nikdy.

## Jedna inštancia

Prvý launcher obsadí `127.0.0.1:<port_instancie>` (predvolene 47653, v `nastavenia.json`) a počúva. Druhé spustenie
pošle príkaz (zobraz / tray / aplikacia / cesty) s tokenom z `%LOCALAPPDATA%\NC_Nastroje\instancia.token` a skončí.

## Na neskôr (fáza 8, nasadenie pre kolegov)

Prvá inštalácia (kópia zostaveného launchera do `launcher\<verzia>\` a zápis `aktualna.txt`) – štartér to už vie použiť.
