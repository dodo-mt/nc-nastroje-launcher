# Čo je nové

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
