# CLAUDE.md – NC Nástroje (launcher / dashboard)

## Účel

Jedno okno (a jedna tray ikona), z ktorého sa spúšťajú všetky naše firemné aplikácie
na CNC programovanie, vidieť ich stav a dajú sa na ne pretiahnuť súbory.
Aplikáciu používa programátor (plný režim) a kolegovia v kancelárii (~10 ľudí, režim
„Na prezeranie“). Všetko beží na Windows, bez IT oddelenia a bez vlastného servera –
spoločné veci sú na sieťovom disku **L:**.

Vizuálny návrh (schválený): https://claude.ai/artifact/9LfxHwiq46hNFpnkDUkqft
- **A – Dlaždice**: hlavné okno (predvolené).
- **B – Zoznam + detail**: druhé zobrazenie (prepínač v menu Zobraziť).
- **Menu tray ikony**.
- **A – Ťahanie súborov**: stav okna počas drag & drop.

Komunikácia, texty v UI, komentáre a commit správy: **po slovensky**.

## Aplikácie, ktoré launcher spúšťa

| id | Názov | Typ | Čo robí |
|---|---|---|---|
| `tnc_sync` | TNC Sync | tkinter exe | Záloha odladených programov zo strojov (Heidenhain, Sinumerik) na L: |
| `triedic_nc` | Triedič NC | tray exe | Triedi programy z hyperMILL z `NC\` do podpriečinkov podľa stroja, kópia na R: |
| `lupa` | Lupa | web (prehliadač) | Prehliadač zákaziek na L:\ |
| `nastrojovy_list` | Nástrojový list | tkinter exe | Nástrojové listy z .pof súborov hyperMILL (HTML/PDF) |
| `programovy_list` | Programový list | skript/exe | Nákresy upnutia (p1a, p1b, p2a…) do Excel šablóny + PDF |
| `nc_editor` | NC Editor | exe | Úprava a porovnanie NC programov |

Launcher **nemení kód týchto aplikácií**. Ak je pre funkciu potrebná zmena v aplikácii
(napr. čítanie `sys.argv`, zápis stavového súboru), napíš ju ako samostatný návrh
do `docs/zmeny_v_aplikaciach.md` – urobí sa v repozitári danej aplikácie.

## Disky a cesty

- `L:\` – zákazky (`L:\<zákazník>\<zákazka>\<pozícia>\…`), priečinky zákazníkov majú
  za číslom aj meno (`L:\101270-Meno firmy\OD00021930\21930-1A\NC\`). Hľadať podľa
  **začiatku** názvu. Staré zákazky sú na najvyššej úrovni (`L:\OD626\001252`, predpona
  `ON` = stará) a **nie sú** totožné s novými `OD00000626`.
- `R:\` – zrkadlo L: len s programami na nahratie do strojov.
- `L:\_Nastroje\` – koreň launchera (nastaviteľný). **L: a R: launcher len číta**,
  zapisuje iba do `L:\_Nastroje\` (a to len publikačný skript, nie bežný beh).
- Lokálne: `%LOCALAPPDATA%\NC_Nastroje\` (kópie aplikácií, cache, logy),
  `%APPDATA%\NC_Nastroje\nastavenia.json` (nastavenia používateľa).

Pri vývoji a testoch **vždy použi falošný koreň** (napr. `test_data\L\`, `test_data\R\`)
nastaviteľný v nastaveniach – nikdy nesiahaj na skutočné L:/R:.

## Technológie

- Python 3.11+, Windows 10/11.
- `tkinter` + `sv-ttk` (rovnaká téma ako TNC Sync, svetlý/tmavý režim).
- `tkinterdnd2` – drag & drop súborov do okna.
- `pystray` + `Pillow` – tray ikona.
- `psutil` – zistenie, či aplikácia beží.
- `pywin32` – vytváranie zástupcov (.lnk) pre „Odoslať do“ a Po spustení.
- Balenie: PyInstaller `--onedir --windowed`.
- Žiadna databáza, žiadny server. Konfigurácia v JSON.

## Štruktúra projektu

```
nc_nastroje/
  main.py                 # štart, single instance, argumenty
  verzia.py               # VERZIA = "2026.11.24-1"
  config.py               # načítanie nastavení + apps.json, cesty
  katalog.py              # model aplikácií (dataclass App), validácia apps.json
  spustac.py              # spúšťanie procesov, odovzdanie ciest, kontrola behu
  aktualizacie.py         # porovnanie verzií L: vs lokálne, kopírovanie
  stavy.py                # čítanie stavov aplikácií (adaptéry)
  zakazky.py              # hľadanie priečinka zákazky na L:/R:
  dnd.py                  # pravidlá „prijíma“, zvýrazňovanie dlaždíc
  tray.py                 # pystray v samostatnom vlákne
  windows_integracia.py   # Odoslať do, spustenie po prihlásení
  ui/
    hlavne_okno.py        # zobrazenie A (dlaždice)
    zoznam_detail.py      # zobrazenie B
    dlazdica.py           # widget dlaždice (stavy: normál / prijíma / nad ňou / sivá)
    nastavenia.py
    napoveda.py           # F1, Čo je nové
    tema.py               # farby, fonty, ikony
  ikony/                  # PNG ikony aplikácií (aj tray ikona so stavovou bodkou)
nastroje/
  publikuj.py             # nasadenie novej verzie aplikácie na L:\_Nastroje
docs/
  zmeny_v_aplikaciach.md
test_data/
tests/
```

## Katalóg aplikácií – `L:\_Nastroje\apps.json`

Jediný zdroj pravdy o aplikáciách. Číta ho každý počítač.

```json
{
  "verzia_formatu": 1,
  "aplikacie": [
    {
      "id": "nastrojovy_list",
      "nazov": "Nástrojový list",
      "popis": "Z .pof súborov hyperMILL",
      "typ": "exe",
      "verzia": "2026.11.24-1",
      "zdroj": "nastrojovy_list\\2026.11.24-1",
      "spustit": "nastrojovy_list.exe",
      "ikona": "nastrojovy_list.png",
      "farba": "#0B7A55",
      "prijima": [".pof", "priecinok"],
      "argumenty": "{cesty}",
      "jedna_instancia": false,
      "len_plny_rezim": false,
      "spustit_pri_starte": false,
      "stav": { "adapter": "subor_json", "cesta": "_stav\\nastrojovy_list" },
      "co_je_nove": "nastrojovy_list\\CO_JE_NOVE.md"
    },
    {
      "id": "lupa",
      "nazov": "Lupa",
      "popis": "Prehliadač zákaziek na L:\\",
      "typ": "web",
      "url": "file:///L:/_Lupa/index.html",
      "url_hladat": "{url}?q={text}",
      "url_cesta": "{url}?cesta={cesta}",
      "prijima": ["priecinok", "*"],
      "stav": { "adapter": "lupa_sken" }
    }
  ]
}
```

Pravidlá:
- `typ`: `exe` | `python` (spustí `pythonw.exe skript.py`) | `web` (otvorí URL v predvolenom prehliadači).
- `zdroj` je relatívny ku koreňu `L:\_Nastroje\`.
- `prijima`: zoznam prípon (s bodkou, malými písmenami), `priecinok`, alebo `*` (čokoľvek).
  Prázdne / chýba = aplikácia nič neprijíma.
- `argumenty`: šablóna, `{cesty}` = všetky cesty v úvodzovkách oddelené medzerou.
- `len_plny_rezim: true` → v režime Na prezeranie sa dlaždica nezobrazí (napr. Triedič NC).
- Neznáme kľúče ignoruj (budúca kompatibilita), chybný záznam preskoč a zaloguj – launcher
  nesmie spadnúť kvôli jednej zlej aplikácii.
- Cesty, URL a verzie v príklade sú ilustračné – skutočné hodnoty doplní používateľ.

Predvolené pravidlá `prijima` (návrh, finálne v apps.json):
- Nástrojový list: `.pof`, `priecinok` (zákazka / pozícia / POF).
- NC Editor: `.h`, `.i`, `.mpf`, `.spf`, `.nc` (2 súbory = porovnanie – rieši editor).
- Programový list: `.png`, `.jpg`, `.xlsx`, `priecinok`.
- Triedič NC: `.h`, `.mpf`.
- TNC Sync: `priecinok` (otvorí Prehľad lokálnych programov zákazky).
- Lupa: `priecinok`, `*`.

## Distribúcia a aktualizácie

Štruktúra na L::
```
L:\_Nastroje\
  apps.json
  launcher\2026.11.24-1\...          # aj samotný launcher
  nastrojovy_list\2026.11.19-1\...
  nastrojovy_list\2026.11.24-1\...
  _stav\<app_id>\<POCITAC>.json      # stavové súbory (viď nižšie)
```

- Aplikácie sa **nespúšťajú priamo z L:** (zamknuté súbory by blokovali aktualizáciu, sieť
  je pomalšia). Launcher ich kopíruje do `%LOCALAPPDATA%\NC_Nastroje\apps\<id>\<verzia>\`.
- Pri štarte (a potom každých 10 min) porovná `verzia` v apps.json s lokálnou.
  Novšia verzia → kopírovanie na pozadí do `<verzia>.tmp\`, po dokončení premenovanie.
  Ak aplikácia práve beží, nová verzia sa použije pri ďalšom spustení.
- Ponechaj **1 predchádzajúcu verziu** lokálne (návrat späť v menu dlaždice), staršie zmaž.
- Pruh „Na L:\_Nastroje je nová verzia…“ + odkaz Čo je nové + tlačidlo Aktualizovať teraz.
- Formát verzie `RRRR.MM.DD-poradie`, porovnávať ako tuple `(rok, mesiac, deň, poradie)`.
- L: nedostupný → launcher funguje z lokálnych kópií a posledného uloženého apps.json
  (cache v `%LOCALAPPDATA%`), v stavovom riadku červená bodka „L:\ nedostupný“.
- Aktualizácia samotného launchera: stiahne novú verziu, ponúkne reštart; pomocný
  `aktualizator.exe` (alebo .bat) počká na ukončenie, prepne verziu a spustí launcher.

`nastroje/publikuj.py <app_id> <cesta_k_buildu> [--verzia X]`:
skopíruje build do `L:\_Nastroje\<id>\<verzia>\`, overí počet a veľkosť súborov,
až potom zapíše novú verziu do apps.json (atomicky: zápis do `apps.json.tmp` + `os.replace`).
Pred zápisom urobí zálohu `apps.json.bak`.

## Stavy aplikácií (bodky na dlaždiciach)

Launcher stav **len číta**, každých 30 s, na pozadí (vlákno), nikdy neblokuje UI.
Hodnoty: `ok` (zelená #0F7B0F), `upozornenie` (oranžová #9D5D00), `chyba` (červená #C42B1C),
`nova_verzia` (modrá #005FB8), `necinny` (sivá #9AA0A6), `nezname`.

Adaptéry (`stavy.py`, jeden registrovaný adaptér = jedna funkcia):
- `subor_json` – štandard pre nové aplikácie: `L:\_Nastroje\_stav\<app_id>\*.json`
  ```json
  { "stav": "ok", "riadky": ["Posledná záloha: dnes 11:32", "Stroje: 5 / 6"],
    "cipy": [{"text": "MB65 A", "stav": "ok"}, {"text": "DMC 160 vyp.", "stav": "upozornenie"}],
    "cas": "2026-11-24T11:32:00", "pocitac": "PC-PROG1" }
  ```
  Súbor starší ako `max_vek_min` (default 1440) → stav `nezname`.
- `tnc_sync` – číta existujúci stavový súbor TNC Sync v jeho spoločnom adresári na L:
  (cestu a formát zisti z repozitára TNC Sync, nemeniť ho). Mapovanie: OK → ok,
  OK s upozornením → upozornenie, „Záloha nebeží“ (> 2 dni) → chyba.
- `proces` – len či beží proces (psutil podľa cesty exe): beží → ok „Beží“, nebeží → necinny.
- `lupa_sken` – čas posledného skenu z indexu Lupy (zistiť z repozitára NC Lupa).

Ak aplikácia nemá stav, dlaždica ukáže len verziu a „Pripravený“.

## Drag & drop

- Celé okno je cieľ (`tkinterdnd2`). Pri `<<DropEnter>>` launcher zistí typy ťahaných
  položiek (ak sa dajú zistiť až pri pustení, zvýrazni podľa posledného známeho stavu
  a validuj pri `<<Drop>>`).
- Dlaždica je **kompatibilná**, ak prijíma **všetky** ťahané položky.
  Stavy dlaždice: kompatibilná = prerušovaný modrý rámik, nad ňou = plný modrý rámik +
  svetlomodré pozadie + text „Pustiť sem → …“, nekompatibilná = sivá (bez farieb, nízky kontrast).
- Horný pruh počas ťahania: „Ťaháš N súborov .pof – pusť ich na zvýraznenú aplikáciu.
  Esc = zrušiť“.
- Pustenie na nekompatibilnú dlaždicu alebo mimo → nič sa nespustí, krátke upozornenie.
- Pustenie na zoznam v zobrazení B funguje rovnako.
- Spustenie: `subprocess.Popen([exe, *cesty], cwd=priecinok_aplikacie)`; pri `web`
  sa cesta odovzdá cez `url_cesta` (URL-enkódovaná).
- Dlhé zoznamy ciest: ak by príkazový riadok presiahol ~30 000 znakov, zapíš cesty do
  dočasného súboru a odovzdaj `@subor.txt` (aplikácia to musí podporovať – zapíš do
  `docs/zmeny_v_aplikaciach.md`).
- Rovnaké pravidlá platia pre zástupcov „Odoslať do“.

## Rýchle akcie (horný riadok v A, pole vľavo hore v B)

Pole „Číslo zákazky / výkresu“:
- `Enter` / **Otvoriť L:** – nájde priečinok zákazky a otvorí ho v Prieskumníkovi.
- **Otvoriť R:** – rovnaká relatívna cesta na R:.
- **Hľadať v Lupe** – otvorí Lupu s `url_hladat`.

Hľadanie (`zakazky.py`):
- Vstup normalizuj: `21930`, `OD21930`, `OD00021930` → `OD00021930`; starý formát
  `OD626\001252` alebo `001252` hľadaj v starých priečinkoch na najvyššej úrovni.
- Index `zákazka → cesta` drž v cache (`%LOCALAPPDATA%\NC_Nastroje\cache\zakazky.json`),
  stavaj ho na pozadí výpisom 2 úrovní L: (zákazník → zákazka), obnov raz denne
  alebo tlačidlom. Ak cache neobsahuje zákazku, skús priamy prechod a cache doplň.
- Viac zhôd → malé okno s výberom. Žiadna zhoda → ponúkni Hľadať v Lupe.

## UI

Podľa návrhu (odkaz hore). Hlavné body:
- Okno ~1160×740, minimálne 900×600; dlaždice v mriežke 3 stĺpce (pri užšom okne 2).
- Dlaždica: ikona 40 px vo farebnom štvorci, názov, popis, stavová bodka + text,
  2 riadky stavu, čipy (napr. stroje TNC Sync), verzia vľavo dole, tlačidlo vpravo dole
  (Spustiť / Otvoriť; Triedič: Pozastaviť + Otvoriť).
- Pravé tlačidlo na dlaždici: Spustiť, Otvoriť priečinok aplikácie, Čo je nové,
  Návrat na predchádzajúcu verziu, Vytvoriť zástupcu na ploche.
- Dvojklik na dlaždicu = Spustiť.
- Zobrazenie B: zoznam vľavo (270 px), detail vpravo: 3 čísla (z `riadky` stavu),
  posledné záznamy (ak adaptér vráti `log`), tlačidlá Priečinok, Log, Čo je nové, Nápoveda.
- Stavový riadok: L:\ a R:\ pripojený/nedostupný, režim, verzia launchera.
- Menu: Súbor (Nastavenia, Ukončiť), Zobraziť (Dlaždice / Zoznam, Tmavý režim),
  Nápoveda (F1 Nápoveda, Čo je nové, O programe).
- Klávesy: F1 nápoveda, F5 obnoviť stavy, Ctrl+F pole zákazky, Ctrl+1…6 spustiť aplikáciu.
- Tooltipy na všetkých tlačidlách.
- Všetky dialógy otvárať v strede hlavného okna.
- Farby (svetlý režim): pozadie #F3F3F3, karty #FFFFFF, okraj #E0E3E7, text #1B1B1B,
  sekundárny text #555555, akcent #005FB8. Font Segoe UI. Kontrast textu min. 4.5:1.
- Zatvorenie okna (X) = skryť do tray (prvýkrát ukáž oznámenie). Ukončenie len z menu
  alebo tray.

## Tray ikona

- `pystray` v samostatnom vlákne; všetky zmeny UI z tray cez `root.after(0, …)`.
- Ikona launchera so stavovou bodkou = najhorší stav zo všetkých aplikácií.
- Menu: hlavička „NC NÁSTROJE · L:\ R:\ OK“, aplikácie so stavom (klik = spustiť),
  Pozastaviť triedič (ak beží), Otvoriť zákazku… (malé okno s poľom), **Otvoriť NC Nástroje**
  (tučné, predvolená akcia aj pri dvojkliku), Ukončiť.
- Na tray ikonu sa súbory pustiť nedajú (obmedzenie Windows) – nič také nerieš.

## Režimy

- **Plný** – všetko.
- **Na prezeranie** – skryje aplikácie s `len_plny_rezim`, skryje publikovanie.
  Prepína sa v Nastaveniach (rovnako ako v TNC Sync), bez hesla.

## Nastavenia (`%APPDATA%\NC_Nastroje\nastavenia.json`)

Koreň nástrojov (default `L:\_Nastroje`), koreň L:, koreň R:, režim, zobrazenie (A/B),
tmavý režim, spustiť po prihlásení do Windows (zástupca v `shell:startup`),
spúšťať aplikácie s `spustit_pri_starte`, interval obnovy stavov, pridať/odobrať
„Odoslať do“ zástupcov (`shell:sendto`, napr. „Nástrojový list“ → launcher s
`--aplikacia nastrojovy_list <cesty>`). Okno nastavení: ľavý zoznam sekcií.

## Príkazový riadok launchera

```
nc_nastroje.exe                                  # otvorí okno (alebo prenesie do popredia)
nc_nastroje.exe --tray                           # štart len do tray (po prihlásení)
nc_nastroje.exe --aplikacia <id> [cesty…]        # spustí aplikáciu s cestami (Odoslať do)
nc_nastroje.exe [cesty…]                         # okno s výberom kompatibilnej aplikácie
```

Launcher je **jedna inštancia**: druhé spustenie pošle argumenty prvej (lokálny socket
na 127.0.0.1, port z nastavení, alebo pomenovaná rúra) a skončí.

## Logovanie a chyby

- `logging` do `%LOCALAPPDATA%\NC_Nastroje\log\launcher.log` (rotácia 5 × 1 MB).
- Žiadna výnimka nesmie zhodiť UI: chyby adaptérov, kopírovania a spúšťania zaloguj
  a ukáž zrozumiteľne pri dlaždici („Nepodarilo sa spustiť – súbor chýba“).
- Sieťové operácie (L:, R:) vždy na pozadí s timeoutom; UI nikdy nečaká na sieť.

## Verzie a Čo je nové

- `verzia.py`: `VERZIA = "RRRR.MM.DD-poradie"`. **Po každej zmene kódu verziu zvýš**
  a dopíš záznam do `CO_JE_NOVE.md` (zobrazuje sa v Nápoveda → Čo je nové).

## Postup vývoja (fázy)

Po každej fáze: spustiť, skontrolovať screenshotom, zvýšiť verziu, commit.

1. **Kostra**: `apps.json` (testovací, 6 aplikácií s fiktívnymi exe v `test_data`),
   načítanie katalógu, hlavné okno A s dlaždicami, Spustiť, sv-ttk téma, menu, nastavenia.
2. **Stavy**: adaptéry `subor_json`, `proces`, potom `tnc_sync` a `lupa_sken`;
   obnova na pozadí, bodky, čipy, stavový riadok L:/R:.
3. **Drag & drop**: `prijima`, zvýrazňovanie dlaždíc, odovzdanie ciest, horný pruh.
4. **Distribúcia**: lokálne kópie, kontrola verzií, pruh novej verzie, návrat späť,
   `nastroje/publikuj.py`, aktualizácia samotného launchera.
5. **Tray a Windows**: tray menu, skrývanie do tray, jedna inštancia, spustenie po
   prihlásení, „Odoslať do“.
6. **Rýchle akcie**: hľadanie zákazky (cache), Otvoriť L:/R:, Hľadať v Lupe.
7. **Zobrazenie B** (zoznam + detail) a tmavý režim.
8. **Režim Na prezeranie** a nasadenie pre kolegov.

## Pravidlá pre Claude Code

- Najprv krátky plán, potom kód. Pri väčších zmenách UI najprv návrh, kód až po odsúhlasení.
- Malé, samostatne testovateľné kroky; nemeň nesúvisiaci kód.
- L: a R: len čítať. Nič nemazať mimo `%LOCALAPPDATA%\NC_Nastroje\`.
- Testy (`pytest`) pre: porovnanie verzií, pravidlá `prijima`, normalizáciu čísla zákazky,
  parsovanie apps.json (aj chybného), adaptér `subor_json`.
- Nepoužívaj nové knižnice bez opýtania (okrem tých v sekcii Technológie).
