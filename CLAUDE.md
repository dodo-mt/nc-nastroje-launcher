# CLAUDE.md – NC Nástroje (launcher / dashboard)

## Účel

Jedno okno (a jedna tray ikona), z ktorého sa spúšťajú všetky naše firemné aplikácie na CNC programovanie, vidieť ich stav
a dajú sa na ne pretiahnuť súbory. Používa ho programátor (plný režim) a kolegovia v kancelárii (~10 ľudí, režim
„Na prezeranie“). Všetko beží na Windows, bez IT oddelenia a bez vlastného servera – spoločné veci sú na sieťovom disku **L:**.

Vizuálny návrh (schválený): https://claude.ai/artifact/9LfxHwiq46hNFpnkDUkqft (A – Dlaždice, B – Zoznam + detail, menu tray, ťahanie súborov).
Komunikácia, texty v UI, komentáre a commit správy: **po slovensky**.

**Verzia:** `nc_nastroje/verzia.py` (`VERZIA = "RRRR.MM.DD-poradie"`). **Po každej zmene kódu verziu zvýš** a dopíš záznam do
`CO_JE_NOVE.md` (zobrazuje sa v Nápoveda → Čo je nové). Podrobná špecifikácia (JSON príklad, stavy, drag & drop, UI, tray, fázy
vývoja): `docs/specifikacia_podrobne.md`. Ďalšie: `docs/distribucia.md`, `nasadenie.md`, `prvy_ostry_test.md`.
CNC znalosti (stroje, prípony, syntax NC a .pof, disky L:\ R:\, vzorky) sú v osobnom skille `cnc-programy` (`%USERPROFILE%\.claude\skills\cnc-programy`).

## Aplikácie, ktoré launcher spúšťa

| id | Názov | Typ | Čo robí |
|---|---|---|---|
| `tnc_sync` | TNC Sync | tkinter exe | Záloha odladených programov zo strojov (Heidenhain, Sinumerik) na L: |
| `triedic_nc` | Triedič NC | tray exe | Triedi programy z hyperMILL z `NC\` do podpriečinkov podľa stroja, kópia na R: |
| `lupa` | Lupa | web / exe | Prehliadač zákaziek na L:\ |
| `nastrojovy_list` | Nástrojový list | tkinter exe | Nástrojové listy z .pof súborov hyperMILL (HTML/PDF) |
| `programovy_list` | Programový list Hypermill | skript/exe | Nákresy upnutia (p1a, p1b, p2a…) do Excel šablóny + PDF |
| `nc_editor` | NC Editor | exe | Úprava a porovnanie NC programov |
| `cnc_vykres_edgecam` | Programový list Edgecam | exe | Výkres upnutia (screenshoty) z NC programu `.h` → Excel + PDF (`CncVykresGenerator.exe`) |

Launcher **nemení kód týchto aplikácií**. Ak je pre funkciu potrebná zmena v aplikácii (napr. `sys.argv`, stavový súbor), napíš
ju ako samostatný návrh do `docs/zmeny_v_aplikaciach.md` – urobí sa v repozitári danej aplikácie.

## Disky a cesty

- `L:\` – zákazky (štruktúra, staré zákazky `OD626`, priečinky zákazníkov: skill `cnc-programy`). Hľadať podľa **začiatku** názvu priečinka.
- `R:\` – zrkadlo L: len s programami na nahratie do strojov.
- `L:\_Nastroje\` – koreň launchera (nastaviteľný). **L: a R: launcher len číta**, zapisuje iba do `L:\_Nastroje\`
  (publikačný skript; od 2026.11.26-2 aj bežný launcher, ale **výhradne** malý záznam o počítači
  `L:\_Nastroje\_stav\_pocitace\<POCITAC>.json` pre Súbor → Prehľad počítačov, aj v režime Na prezeranie – rozhodnutie
  používateľa 2026.11.26; `pocitace.py`).
- Lokálne: `%LOCALAPPDATA%\NC_Nastroje\` (kópie aplikácií, cache, logy), `%APPDATA%\NC_Nastroje\nastavenia.json`.
- Pri vývoji a testoch **vždy falošný koreň** (`test_data\L\`, `test_data\R\`) nastaviteľný v nastaveniach – nikdy nesiahaj na skutočné L:/R:.

## Technológie a štruktúra

Python 3.11+, Windows 10/11, `tkinter` + `sv-ttk`, `tkinterdnd2` (drag & drop), `pystray` + `Pillow` (tray), `psutil`,
`pywin32` (.lnk zástupcovia). Balenie PyInstaller `--onedir --windowed`. Bez databázy a servera, konfigurácia v JSON.
**Nové knižnice len po opýtaní.**

```
nc_nastroje/  main.py (štart, single instance, argumenty) · verzia.py · config.py · katalog.py (App, validácia apps.json)
              spustac.py · aktualizacie.py · stavy.py (adaptéry) · zakazky.py · dnd.py · tray.py · windows_integracia.py
              pocitace.py · ui/ (hlavne_okno, zoznam_detail, dlazdica, nastavenia, napoveda, tema) · ikony/
nastroje/publikuj.py   # nasadenie novej verzie aplikácie na L:\_Nastroje
docs/  test_data/  tests/
```

## Katalóg aplikácií – `L:\_Nastroje\apps.json`

Jediný zdroj pravdy, číta ho každý počítač (príklad záznamu: `docs/specifikacia_podrobne.md`).
- `typ`: `exe` | `python` (`pythonw.exe skript.py`) | `web` (URL v prehliadači, `url_hladat`, `url_cesta`). `zdroj` je relatívny ku koreňu.
- `prijima`: prípony (s bodkou, malými písmenami), `priecinok`, alebo `*`; prázdne = nič neprijíma. `argumenty`: šablóna, `{cesty}` = cesty v úvodzovkách.
- `len_plny_rezim: true` → v režime Na prezeranie sa dlaždica nezobrazí (Triedič NC). Ďalej `jedna_instancia`, `spustit_pri_starte`, `stav`, `co_je_nove`.
- Neznáme kľúče ignoruj, chybný záznam preskoč a zaloguj – launcher nesmie spadnúť kvôli jednej zlej aplikácii.
- Predvolené `prijima`: Nástrojový list `.pof` + priečinok · NC Editor `.h .i .mpf .spf .nc` · Programový list `.png .jpg .xlsx` + priečinok ·
  Triedič `.h .mpf` · TNC Sync priečinok · Lupa priečinok + `*`.

## Distribúcia a aktualizácie

- Na L: `launcher\<verzia>\`, `<app_id>\<verzia>\`, `_stav\<app_id>\<POCITAC>.json`, `apps.json`.
- Aplikácie sa **nespúšťajú priamo z L:** (zamknuté súbory, pomalá sieť) – kópia do `%LOCALAPPDATA%\NC_Nastroje\apps\<id>\<verzia>\`.
- Pri štarte a každých 10 min porovnanie `verzia` (tuple `(rok, mesiac, deň, poradie)`); novšia → kopírovanie na pozadí do `<verzia>.tmp\`, potom
  premenovanie. Bežiaca aplikácia: nová verzia až pri ďalšom spustení. Ponechaj **1 predchádzajúcu verziu** (návrat späť), staršie zmaž.
- L: nedostupný → lokálne kópie a posledný `apps.json` (cache), v stavovom riadku červená bodka „L:\ nedostupný“.
- Aktualizácia launchera: stiahne, ponúkne reštart; `aktualizator.exe` (alebo .bat) počká, prepne verziu a spustí launcher.
- `nastroje/publikuj.py <app_id> <cesta_k_buildu> [--verzia X]`: kópia do `L:\_Nastroje\<id>\<verzia>\`, kontrola počtu a veľkosti,
  až potom zápis do `apps.json` (atomicky `apps.json.tmp` + `os.replace`), pred zápisom záloha `apps.json.bak`.

## Stavy aplikácií (bodky)

Len číta, každých 30 s, na pozadí, nikdy neblokuje UI. Hodnoty: `ok` #0F7B0F, `upozornenie` #9D5D00, `chyba` #C42B1C, `nova_verzia` #005FB8,
`necinny` #9AA0A6, `nezname`. Adaptéry (`stavy.py`, jeden = jedna funkcia): `subor_json` (štandard: `_stav\<app_id>\*.json` s `stav`, `riadky`, `cipy`,
`cas`, `pocitac`; starší ako `max_vek_min` = 1440 → `nezname`), `tnc_sync` (existujúci stavový súbor TNC Sync, nemeniť ho), `proces` (psutil podľa
cesty exe), `lupa_sken`. Bez stavu: verzia a „Pripravený“.

## Drag & drop a spúšťanie

- Celé okno je cieľ. Dlaždica je **kompatibilná**, ak prijíma **všetky** ťahané položky (prerušovaný modrý rámik; nad ňou plný rámik + „Pustiť sem → …“;
  nekompatibilná = sivá). Horný pruh „Ťaháš N súborov .pof – pusť ich na zvýraznenú aplikáciu. Esc = zrušiť“. Pustenie na nekompatibilnú / mimo → nič + upozornenie.
- Spustenie: `subprocess.Popen([exe, *cesty], cwd=priecinok_aplikacie)`; `web` cez `url_cesta` (URL-enkódovaná). Príkazový riadok nad ~30 000 znakov →
  cesty do dočasného súboru a `@subor.txt` (aplikácia to musí podporovať – zapísať do `docs/zmeny_v_aplikaciach.md`). Rovnako pre „Odoslať do“.
- Na tray ikonu sa súbory pustiť nedajú (obmedzenie Windows) – nič také nerieš.

## Rýchle akcie (pole „Číslo zákazky / výkresu“) – `zakazky.py`

Enter / Otvoriť L: (Prieskumník), Otvoriť R: (rovnaká relatívna cesta), Hľadať v Lupe (`url_hladat`). Normalizácia: `21930`, `OD21930`, `OD00021930` →
`OD00021930`; starý formát `OD626\001252` / `001252` hľadaj v starých priečinkoch na najvyššej úrovni. Index zákazka → cesta v cache
(`%LOCALAPPDATA%\NC_Nastroje\cache\zakazky.json`), stavia sa na pozadí (2 úrovne L:), obnova raz denne alebo tlačidlom; chýbajúca zákazka → priamy
prechod a doplnenie cache. Viac zhôd → okno s výberom; žiadna → ponúkni Lupu.

## UI, tray, režimy, nastavenia

- Okno ~1160×740 (min 900×600), dlaždice 3 stĺpce (užšie 2); zobrazenie B = zoznam (270 px) + detail. Tooltipy na všetkých tlačidlách, dialógy v strede
  hlavného okna, font Segoe UI, kontrast textu min. 4.5:1, svetlý aj tmavý režim. Klávesy: F1, F5 obnoviť stavy, Ctrl+F pole zákazky, Ctrl+1…9 spustiť. Dvojklik = Spustiť.
- Zatvorenie okna (X) = skryť do tray (prvýkrát oznámenie); ukončenie len z menu alebo tray. Tray: `pystray` v samostatnom vlákne, zmeny UI cez
  `root.after(0, …)`, ikona so stavovou bodkou = najhorší stav, predvolená akcia „Otvoriť NC Nástroje“.
- Režimy: **Plný**; **Na prezeranie** (skryje aplikácie s `len_plny_rezim` aj publikovanie; prepína sa v Nastaveniach bez hesla).
- Nastavenia: koreň nástrojov / L: / R:, režim, zobrazenie A/B, tmavý režim, spustenie po prihlásení (`shell:startup`), `spustit_pri_starte`, interval stavov,
  „Odoslať do“ zástupcovia (`shell:sendto`, `--aplikacia <id> <cesty>`). Podrobnosti UI: `docs/specifikacia_podrobne.md`.

## Príkazový riadok a jedna inštancia

```
nc_nastroje.exe                            # okno (alebo do popredia)
nc_nastroje.exe --tray                     # len do tray (po prihlásení)
nc_nastroje.exe --aplikacia <id> [cesty…]  # spustí aplikáciu s cestami (Odoslať do)
nc_nastroje.exe [cesty…]                   # okno s výberom kompatibilnej aplikácie
```

Druhé spustenie pošle argumenty prvej inštancii (lokálny socket na 127.0.0.1, port z nastavení, alebo pomenovaná rúra) a skončí.

## Logovanie a chyby

- `logging` do `%LOCALAPPDATA%\NC_Nastroje\log\launcher.log` (rotácia 5 × 1 MB).
- Žiadna výnimka nesmie zhodiť UI: chyby adaptérov, kopírovania a spúšťania zaloguj a ukáž zrozumiteľne pri dlaždici („Nepodarilo sa spustiť – súbor chýba“).
- Sieťové operácie (L:, R:) vždy na pozadí s timeoutom; UI nikdy nečaká na sieť.

## Pravidlá pre Claude Code

- Najprv krátky plán, potom kód. Pri väčších zmenách UI najprv návrh, kód až po odsúhlasení. Malé, samostatne testovateľné kroky; nemeň nesúvisiaci kód.
- L: a R: len čítať. Nič nemazať mimo `%LOCALAPPDATA%\NC_Nastroje\`.
- Testy (`pytest`): porovnanie verzií, pravidlá `prijima`, normalizácia čísla zákazky, parsovanie apps.json (aj chybného), adaptér `subor_json`.
- Po každej fáze / väčšej zmene: spustiť, skontrolovať screenshotom, zvýšiť verziu, commit (len na pokyn používateľa).
