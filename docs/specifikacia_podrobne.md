# Podrobná špecifikácia NC Nástrojov (katalóg, stavy, drag & drop, UI, tray, fázy vývoja)

Presunuté z CLAUDE.md bez zmeny textu (stručný výber pravidiel ostáva v CLAUDE.md).

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
- Klávesy: F1 nápoveda, F5 obnoviť stavy, Ctrl+F pole zákazky, Ctrl+1…9 spustiť aplikáciu.
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

## Nastavenia (`%APPDATA%\NC_Nastroje\nastavenia.json`)

Koreň nástrojov (default `L:\_Nastroje`), koreň L:, koreň R:, režim, zobrazenie (A/B),
tmavý režim, spustiť po prihlásení do Windows (zástupca v `shell:startup`),
spúšťať aplikácie s `spustit_pri_starte`, interval obnovy stavov, pridať/odobrať
„Odoslať do“ zástupcov (`shell:sendto`, napr. „Nástrojový list“ → launcher s
`--aplikacia nastrojovy_list <cesty>`). Okno nastavení: ľavý zoznam sekcií.

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
