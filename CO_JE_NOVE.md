# Čo je nové

## 2026.11.24-18
- Nastavenia → Aplikácie: na každom počítači si môžeš zvoliť, ktoré aplikácie sa zobrazia (skryté sa nekopírujú
  a nespúšťajú). Platí popri režime Na prezeranie.
- Okno Nastavenia má pevnú (väčšiu) veľkosť, pri prepínaní sekcií sa už nemení.

## 2026.11.24-17
- Nové poradie dlaždíc (Programový list Hypermill, Nástrojový list, Programový list Edgecam / NC Editor, Triedič NC, Lupa /
  TNC Sync) a nová ikona Programového listu Hypermill (ozubené koleso).

## 2026.11.24-16
- Oprava automatickej aktualizácie launchera: pomocný aktualizátor sa spúšťal bez konzoly, v ktorej sa príkaz
  `tasklist | find` zasekol, takže čakanie na ukončenie launchera nikdy neskončilo a verzia sa neprepla. Teraz beží
  so skrytou konzolou.
- Premenovanie: Programový list → Programový list Hypermill (oranžová), CNC výkresy Edgecam → Programový list Edgecam (zelená). Lupa má novú farbu (červená).

## 2026.11.24-15
- Nová aplikácia Programový list Edgecam (`CncVykresGenerator.exe`, zelená): prijíma `.h` programy a priečinky.
- Klávesy Ctrl+1…9 spustia aplikáciu podľa poradia.

## 2026.11.24-14
- Aktualizácia launchera: po „Aktualizovať teraz“ a pri Ukončiť sa proces najneskôr po 8 s ukončí natvrdo, aby
  nová verzia nikdy nenarazila na bežiacu starú. Priebeh aktualizátora sa zapisuje do `log\aktualizator.log`.
- Neošetrené chyby okna sa zapisujú do `launcher.log` (okno nemá konzolu, predtým sa strácali).

## 2026.11.24-13
- Hľadať v Lupe: Lupa zatiaľ text z príkazového riadku neprijíma, preto sa hľadaný text skopíruje do schránky
  (v Lupe ho vložíš cez Ctrl+V). Keď Lupa dostane `--hladat`, stačí v apps.json doplniť `argumenty_hladat`.

## 2026.11.24-12
- Oprava aktualizácie launchera: po zatvorení okna proces vždy skončí. Predtým ho mohlo zdržať vlákno na pozadí a po
  „Aktualizovať teraz“ ostala bežať stará verzia, takže sa nová nespustila.

## 2026.11.24-11
- Aplikácia sa dá spúšťať priamo z pevnej cesty bez kopírovania: v apps.json `spustit` = plná cesta a bez `zdroj`
  (napr. Lupa: `L:\_Lupa\Lupa.exe`, ktorá sa kopíruje sama). Dlaždica ukáže „priamo z L:“.
- „Hľadať v Lupe“ pri exe Lupe ju len otvorí (hľadaný text zadáš v nej). Okno Nasadiť takéto aplikácie nenúka.
- Nový `nastroje/pridaj_lupu.py` pridá záznam Lupy do apps.json na L:.

## 2026.11.24-10
- Súbor → Nasadiť aplikáciu… (len plný režim): vyberieš aplikáciu a priečinok s buildom a launcher ho nasadí na
  L:\_Nastroje (rovnaké kontroly a atomický zápis apps.json ako `nastroje/publikuj.py`). Pred zápisom sa pýta.
- Jadro publikovania je v `nc_nastroje/publikovanie.py`, skript `nastroje/publikuj.py` ho len volá.

## 2026.11.24-9
- Dialóg prvého spustenia (`--prve-spustenie`): pri novej inštalácii je predvolený režim Na prezeranie, pri opakovanej
  inštalácii ostane doterajší režim.
- Zostavenie (`nastroje/zostav.py`) znova skúsi zmazať starý výstup, ak ho na chvíľu zamkne antivírus.
- Nová dokumentácia: `docs/nasadenie.md` a `docs/prvy_ostry_test.md` (návod a checklist prvého ostrého nasadenia).

## 2026.11.24-8
- Fáza 8 – režim Na prezeranie a nasadenie pre kolegov. Režim Na prezeranie skryje aplikácie len pre programátora
  (napr. Triedič NC), tie sa ani nekopírujú ani nespúšťajú pri štarte; publikovanie je v ňom zakázané. Bez hesla.
- Inštalácia: `nastroje/zostav.py` zostaví launcher (PyInstaller), `publikuj.py launcher` ho nasadí na L:\\_Nastroje
  a vytvorí `Instalovat NC Nastroje.bat`. Kolega len dvojklikne – pri prvom spustení si zvolí režim, spustenie po
  prihlásení a zástupcu na ploche.
- `nc_nastroje.exe --odinstaluj` odstráni zástupcov vytvorených NC Nástrojmi (cudzích nikdy).
- Oprava: v zostavenom exe sa aplikácie typu python spúšťajú nainštalovaným Pythonom (nie launcherom samotným).
- Verzia launchera v apps.json sa berie z `verzia.txt` v builde, aby sa aktualizácia nikdy neopakovala v kruhu.

## 2026.11.24-7
- Fáza 7 – zobrazenie B (Zobraziť → Zoznam + detail): zoznam aplikácií vľavo, vpravo detail vybranej aplikácie
  s tromi kartami (z riadkov stavu), posledné záznamy (ak ich aplikácia vráti) a tlačidlá Priečinok, Log,
  Čo je nové, Nápoveda. Pole zákazky je vľavo hore; ťahanie súborov, menu aj stavy fungujú rovnako ako v dlaždiciach.
- Tmavý režim (Zobraziť → Tmavý režim): prepína sa hneď, bez reštartu; kontrast textu min. 4.5:1.
- Voľba zobrazenia a režimu sa pamätá.
- Nový voliteľný kľúč `log` v apps.json (cesta k logu aplikácie pre tlačidlo Log).
- Pozn.: hlavné menu okna (Súbor, Zobraziť…) má farbu Windows a v tmavom režime ostáva svetlé.

## 2026.11.24-6
- Fáza 6 – rýchle akcie: pole „Číslo zákazky / výkresu“ nájde priečinok zákazky na L: (Enter alebo Otvoriť L:),
  Otvoriť R: otvorí rovnakú cestu na R:, Hľadať v Lupe otvorí Lupu s hľadaným textom.
- Rozumie `21930`, `OD21930`, `OD00021930` aj `21930-1A`; staré zákazky ako `001252`, `ON001252` alebo `OD626\001252`.
- Viac zhôd = okno s výberom, žiadna zhoda = ponuka Hľadať v Lupe. Tray → Otvoriť zákazku… otvorí malé okno s poľom.
- Index zákaziek (2 úrovne L:) sa stavia na pozadí raz denne alebo cez Súbor → Obnoviť index zákaziek.
  Zákazka, ktorá v indexe ešte nie je, sa nájde priamym prechodom a doplní sa.

## 2026.11.24-5
- Fáza 5 – tray a Windows: ikona v oblasti oznámení so stavovou bodkou (najhorší stav), menu s aplikáciami
  (klik = spustiť), Pozastaviť triedič, Otvoriť zákazku…, Otvoriť NC Nástroje (aj dvojklik), Ukončiť.
- Zatvorenie okna (X) ho len skryje do tray (prvýkrát oznámenie). Ukončiť sa dá z menu Súbor alebo z tray.
- Jedna inštancia: druhé spustenie prenesie okno do popredia alebo odovzdá argumenty a skončí.
- Príkazový riadok: `--tray`, `--aplikacia <id> [cesty]` (Odoslať do), `[cesty]` (výber kompatibilnej aplikácie).
- Nastavenia → Windows: spustiť po prihlásení, spustiť aplikácie označené v katalógu, výber aplikácií pre Odoslať do.
- Menu dlaždice: Vytvoriť zástupcu na ploche. Tlačidlo Pozastaviť zapíše lokálnu požiadavku (aplikácia ju musí podporovať).
- Oprava: zástupcovia (.lnk) uvoľňujú COM objekty pred ukončením COM (predtým mohol spadnúť proces).

## 2026.11.24-4
- Fáza 4 – distribúcia: aplikácie sa spúšťajú z lokálnych kópií (`%LOCALAPPDATA%\NC_Nastroje\apps`), nie z L:.
- Pri štarte a potom každých 10 min sa porovná verzia v `apps.json` s lokálnou a novšia sa skopíruje na pozadí.
  Beží aplikácia? Nová verzia sa použije pri jej ďalšom spustení (modrá bodka „Nová verzia“, pruh nad dlaždicami).
- Ponechá sa aktuálna a 1 predchádzajúca verzia; v menu dlaždice je Návrat na predchádzajúcu verziu a Čo je nové.
- L:\ nedostupný? Launcher beží z lokálnych kópií a z poslednej uloženej kópie `apps.json`.
- Nová verzia samotného launchera sa stiahne a ponúkne sa reštart (pomocný `aktualizator.bat`).
- `nastroje/publikuj.py` nasadí novú verziu na L:\_Nastroje (kontrola súborov, záloha a atomický zápis `apps.json`).
- Oprava: rozpoznanie bežiacej aplikácie nezáleží na lomítkach a veľkosti písmen v ceste.

## 2026.11.24-3
- Fáza 3 – ťahanie súborov: súbory a priečinky z Prieskumníka sa dajú pustiť na dlaždicu aplikácie.
- Počas ťahania sa aplikácie, ktoré súbory prijímajú, zvýraznia (prerušovaný rámik), dlaždica pod kurzorom
  ukáže „Pustiť sem →“ a ostatné zosivejú. Horný pruh ukáže, čo ťaháš.
- Pustenie na nekompatibilnú dlaždicu alebo mimo dlaždice nič nespustí, ukáže sa upozornenie.
- Veľa ciest naraz (nad ~30 000 znakov) sa odovzdá aplikácii ako `@subor.txt`.

## 2026.11.24-2
- Fáza 2 – stavy aplikácií: farebná bodka, text, dva riadky stavu a čipy (napr. stroje TNC Sync) na dlaždiciach.
- Stavy sa čítajú na pozadí každých 30 s (zmena v Nastaveniach → Stavy), F5 ich obnoví hneď.
- Adaptéry: Nástrojový list (stavový súbor), Triedič NC (beží / nebeží), TNC Sync, Lupa (posledný sken).
- Stavový riadok ukazuje, či sú L:\ a R:\ pripojené.

## 2026.11.24-1
- Prvá verzia (fáza 1 – kostra): hlavné okno s dlaždicami, spúšťanie aplikácií, nastavenia, menu.
