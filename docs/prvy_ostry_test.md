# Prvé ostré nasadenie – návod a checklist

Pre CNC programátora, ktorý nasadzuje NC Nástroje prvýkrát na skutočný `L:\_Nastroje`. Na konci je krátka časť pre
kolegov. Odporúčané poradie: **1. pripraviť → 2. vyskúšať na vlastnom PC → 3. jeden kolega → 4. všetci**.

Pravidlo, ktoré platí celý čas: launcher **L: a R: len číta**. Zapisuje sa na `L:\_Nastroje` iba skriptom
`publikuj.py`, a vždy sa pred tým urobí záloha `apps.json.bak`.

---

## A. Príprava (programátor, ~1 hodina)

### A1. Zálohy a miesto
- [ ] Skopíruj si `L:\_Nastroje` (ak už existuje) niekam bokom.
- [ ] Over, že máš právo zapisovať do `L:\_Nastroje` (a len tam).
- [ ] Over, že na kancelárskych PC je L: pripojený ako **L:** (nie len cez `\\server\...`).

### A2. Katalóg `L:\_Nastroje\apps.json`
Vzor: `test_data\L\_Nastroje\apps.json`. Pre každú skutočnú aplikáciu uprav:

- [ ] `typ`: `exe` (nie `python` – to by vyžadovalo Python na každom PC),
- [ ] `spustit`: názov exe (napr. `tnc_sync.exe`), `zdroj` a `verzia` doplní `publikuj.py`,
- [ ] `prijima` podľa CLAUDE.md (napr. Nástrojový list: `.pof`, `priecinok`),
- [ ] `stav` – adaptér: TNC Sync `{"adapter": "tnc_sync"}`, Lupa `{"adapter": "lupa_sken"}`, Triedič `{"adapter": "proces"}`,
- [ ] `len_plny_rezim: true` pri Triediči NC (skryje ho kolegom),
- [ ] Lupa: `typ: web`, `url` na skutočný `file:///L:/_Lupa/index.html`, `url_hladat`: `{url}?q={text}`,
- [ ] voliteľne `log` (cesta k logu aplikácie pre tlačidlo Log) a `co_je_nove`.

Záznam launchera (kým ho prvýkrát nepublikuješ, stačí zástupná verzia):

```json
"launcher": { "verzia": "2000.01.01-1", "zdroj": "launcher\\2000.01.01-1",
              "spustit": "nc_nastroje.exe", "co_je_nove": "launcher\\CO_JE_NOVE.md" }
```

- [ ] `apps.json` je platný JSON (otvor ho v prehliadači alebo editore).

### A3. Stavové súbory (aby bodky na dlaždiciach niečo ukazovali)
- [ ] **TNC Sync**: launcher číta `<koreň L:>\_tnc_sync\_tnc_sync_stav.json`. Ak má TNC Sync spoločný adresár inde,
      nastav `"stav": {"adapter": "tnc_sync", "cesta": "kam\\je\\_tnc_sync_stav.json"}` (cesta ku koreňu L:).
- [ ] **Lupa**: launcher číta `lupa_scan.json` vedľa databázy, teda `L:\_Lupa\lupa_scan.json` (odvodí sa z `url`).
- [ ] Ostatné aplikácie bez stavu ukážu len verziu a „Pripravený“ – to je v poriadku.

### A4. Zostavenie a publikovanie aplikácií
Pre každú aplikáciu (ich vlastný build):
```
python nastroje\publikuj.py nastrojovy_list C:\cesta\k\buildu --koren L:\_Nastroje
```
- [ ] Skript sa opýta na potvrdenie (skutočný koreň) – prečítaj cestu a potvrď.
- [ ] Skontroluj `L:\_Nastroje\<id>\<verzia>\` a že `apps.json` má novú `verzia`/`zdroj` (a existuje `apps.json.bak`).

### A5. Zostavenie a publikovanie launchera
1. Zvýš verziu v `nc_nastroje\verzia.py`, doplň `CO_JE_NOVE.md`.
2. `python nastroje\zostav.py`  → `dist\nc_nastroje\` (+ `verzia.txt`).
3. `python nastroje\publikuj.py launcher dist\nc_nastroje --koren L:\_Nastroje`
- [ ] Vznikol `L:\_Nastroje\launcher\<verzia>\nc_nastroje.exe`.
- [ ] Vznikol `L:\_Nastroje\Instalovat NC Nastroje.bat`.

---

## B. Test na vlastnom PC (programátor, Plný režim)

Inštalácia: dvojklik na `L:\_Nastroje\Instalovat NC Nastroje.bat`.

**Prvé spustenie**
- [ ] Objaví sa dialóg „Vitaj v NC Nástrojoch“. Vyber **Plný**, zaškrtni zástupcu na ploche; spustenie po prihlásení si
      zaškrtni až neskôr (po teste).
- [ ] Okno sa otvorí, v stavovom riadku svieti `L:\ pripojený` a `R:\ pripojený` (zelené).
- [ ] Aplikácie sa po chvíli skopírujú (v `%LOCALAPPDATA%\NC_Nastroje\apps\`); dlaždice ukážu verzie `v 2026…`.

**Stavy**
- [ ] TNC Sync ukazuje poslednú zálohu a stroje (čipy); Lupa čas posledného skenu.
- [ ] Triedič NC ukazuje „Beží“, keď beží, inak „Nebeží“.
- [ ] F5 stavy obnoví.

**Spúšťanie a súbory**
- [ ] Spustiť každej aplikácie (tlačidlo aj dvojklik).
- [ ] Pretiahni z Prieskumníka `.pof` súbory do okna: zvýraznia sa len aplikácie, ktoré ich prijímajú; pusti na
      Nástrojový list → spustí sa s cestami. Skús aj nekompatibilný súbor (nič sa nespustí, ukáže sa upozornenie).
- [ ] Pravý klik na súbor → **Odoslať do** (po zapnutí v Nastaveniach → Windows) → aplikácia sa spustí so súborom.

**Rýchle akcie**
- [ ] Do poľa napíš skutočnú novú zákazku (`21930`, `OD21930`) → Enter otvorí priečinok na L:.
- [ ] Starú zákazku (`001252`, prípadne `OD626\001252`) – ak je viac zhôd, ukáže sa výber.
- [ ] **Otvoriť R:** otvorí rovnakú cestu (alebo vysvetlí, že tam zákazka nie je).
- [ ] Neexistujúce číslo → ponuka **Hľadať v Lupe**; Lupa sa otvorí s hľadaným textom.
- [ ] Súbor → Obnoviť index zákaziek: zapíš si, ako dlho trval prvý výpis L: (pri ~42 000 zákazkách).

**Tray a okno**
- [ ] X okno skryje do oblasti oznámení (prvýkrát oznámenie); dvojklik na ikonu ho vráti.
- [ ] Menu ikony: aplikácie, Otvoriť zákazku…, Otvoriť NC Nástroje, Ukončiť. Zapíš si, či vyzerá prijateľne.
- [ ] Druhé spustenie z plochy len prenesie okno do popredia (nespustí sa druhá kópia).

**Zobrazenie**
- [ ] Zobraziť → Zoznam + detail, a späť; Tmavý režim; po reštarte sa voľba pamätá.

**L: sa nemení**
- [ ] Po celom teste na `L:` ani `R:` nepribudlo nič nové (okrem toho, čo si publikoval).

**Aktualizácia aplikácie**
- [ ] Publikuj novšiu verziu jednej aplikácie → do 10 min (alebo cez F5 / Aktualizovať teraz) sa skopíruje;
      pri bežiacej aplikácii pruh „Aktualizuje sa pri ďalšom spustení“.
- [ ] Pravý klik na dlaždicu → Návrat na predchádzajúcu verziu → aplikácia sa spustí v starej verzii.

**Aktualizácia launchera**
- [ ] Publikuj novšiu verziu launchera → objaví sa pruh „Je nová verzia NC Nástrojov“ → **Aktualizovať teraz** →
      launcher sa reštartuje do novej verzie (v stavovom riadku nová verzia). *Toto sa v testoch ešte neklikalo – over!*

**Po prihlásení**
- [ ] Zapni Nastavenia → Windows → Spustiť po prihlásení; odhlás sa a prihlás: ikona je v oblasti oznámení bez okna.

---

## C. Jeden kolega (Na prezeranie)

- [ ] Dvojklik na `Instalovat NC Nastroje.bat`; v dialógu nechaj **Na prezeranie**, zaškrtni oboje.
- [ ] Triedič NC (a iné `len_plny_rezim` aplikácie) sa **nezobrazí**.
- [ ] Spustenie aplikácie, ťahanie súborov, vyhľadanie zákazky, Lupa – ako v časti B.
- [ ] Po prihlásení sa launcher spustí do oznámení. Kolega vie okno otvoriť (dvojklik na ikonu).
- [ ] Antivírus / SmartScreen exe neblokuje (ak áno, pridať výnimku pre `%LOCALAPPDATA%\NC_Nastroje`).
- [ ] Aplikácie typu `python` (ak nejaké ostali) – ak chýba Python, ukáže sa zrozumiteľná chyba.

**Rozhodnutie:** nasadiť všetkým, ak je všetko v časti B a C splnené a v `%LOCALAPPDATA%\NC_Nastroje\log\launcher.log`
nie sú riadky `ERROR` alebo `Traceback`.

---

## D. Návod pre kolegov (môžeš poslať e-mailom)

> **NC Nástroje – inštalácia**
> 1. Na disku **L:** otvor priečinok `_Nastroje`.
> 2. Dvojklikni na **Instalovat NC Nastroje.bat**. Počkaj pár sekúnd, otvorí sa okno „Vitaj v NC Nástrojoch“.
> 3. Nechaj **Na prezeranie** a obe políčka zaškrtnuté, klikni **Hotovo**.
> 4. Hotovo. NC Nástroje sa spúšťajú samé po prihlásení a bežia v oblasti oznámení (pri hodinách). Okno otvoríš
>    dvojklikom na ikonu. Zatvorením okna (X) sa nevypnú, vypnúť ich môžeš pravým klikom na ikonu → Ukončiť.
>
> **Ako ich používať:** do poľa hore napíš číslo zákazky (napr. 21930) a stlač Enter – otvorí sa jej priečinok.
> Súbory môžeš pretiahnuť na aplikáciu v okne, alebo pravý klik na súbor → Odoslať do → aplikácia.
>
> Nefunguje niečo? Napíš mi a pošli súbor `%LOCALAPPDATA%\NC_Nastroje\log\launcher.log`.

---

## E. Keď sa niečo pokazí

| Príznak | Príčina / riešenie |
|---|---|
| Všetky bodky sivé, v stavovom riadku „L:\ nedostupný“ | L: nie je pripojený. Launcher beží z lokálnych kópií a poslednej cache; po pripojení F5. |
| „Aplikácia sa ešte nestihla skopírovať z L:\“ | Prvé kopírovanie ešte beží (alebo L: nie je dostupný). Počkať, F5. |
| Dlaždica Lupa/TNC Sync bez stavu („Bez údajov“) | Chýba stavový súbor, pozri A3 (`stav.cesta`). |
| Pri štarte sa nič nestane a okno sa neukáže | Port jednej inštancie `47653` je obsadený: v `%APPDATA%\NC_Nastroje\nastavenia.json` zmeň `port_instancie`. |
| Zákazka sa nenájde, hoci existuje | Súbor → Obnoviť index zákaziek; skontroluj názov priečinka (hľadá sa podľa začiatku názvu). |
| Zlá verzia na L: (chybný build) | Obnov `L:\_Nastroje\apps.json` zo zálohy `apps.json.bak`; klienti sa vrátia k predošlej verzii (lokálne ju majú). |
| Zlý launcher | Obnov `apps.json.bak`; v `%LOCALAPPDATA%\NC_Nastroje\launcher\aktualna.txt` môže byť ručne verzia, ktorá je lokálne nainštalovaná. |
| Treba všetko odstrániť | Ukonči launcher (ikona → Ukončiť), spusti `nc_nastroje.exe --odinstaluj`, potom zmaž `%LOCALAPPDATA%\NC_Nastroje` a `%APPDATA%\NC_Nastroje`. |

**Logy:** `%LOCALAPPDATA%\NC_Nastroje\log\launcher.log` (rotácia 5 × 1 MB). **Nastavenia:** `%APPDATA%\NC_Nastroje\nastavenia.json`.

---

## F. Čo ešte nebolo overené v reálnom prostredí

Tieto veci sa v testoch len simulovali alebo vôbec nevyskúšali – pri ostrom teste ich sleduj osobitne:

1. Tlačidlo **Aktualizovať teraz** pri novom launcheri (reštart cez `aktualizator.bat`).
2. Potvrdenie dialógu prvého spustenia (vytvorenie zástupcov) a `--odinstaluj` v zostavenom exe.
3. Vzhľad menu tray ikony a oznámenia Windows.
4. Ťahanie súborov **priamo z Prieskumníka** (testované so zdrojom ťahania v Tk, nie s Prieskumníkom).
5. Rýchlosť prvého výpisu skutočného L: (index zákaziek) a pomenovania starých zákaziek na reálnych dátach.
6. **Pozastaviť triedič** zatiaľ nemá žiadny účinok – Triedič NC musí začať čítať príznakový súbor
   (návrh: `docs/zmeny_v_aplikaciach.md`).
