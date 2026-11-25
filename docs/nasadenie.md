# Nasadenie pre kolegov (fáza 8)

Pre programátora: zostaviť launcher, nasadiť ho na `L:\_Nastroje`, kolegovia ho nainštalujú dvojklikom.

## 1. Zostavenie (programátor)

```
python nastroje/zostav.py
```

Vznikne `dist\nc_nastroje\` (PyInstaller `--onedir --windowed`, ~50 MB) a v ňom `verzia.txt` s verziou z
`nc_nastroje/verzia.py`. **Pred zostavením zvýš verziu** a doplň `CO_JE_NOVE.md` (pravidlo projektu).

## 2. Publikovanie na L:\_Nastroje (programátor)

```
python nastroje/publikuj.py launcher dist\nc_nastroje
```

- Verzia sa berie z `verzia.txt` (musí sedieť s verziou v exe, inak by sa aktualizácia opakovala v kruhu).
- Build sa skopíruje do `L:\_Nastroje\launcher\<verzia>\`, skontroluje sa počet a veľkosť súborov, urobí sa záloha
  `apps.json.bak` a až potom sa atomicky prepíše `apps.json` (kľúč `launcher`).
- Vytvorí sa (a pri každej novej verzii prepíše) **`L:\_Nastroje\Instalovat NC Nastroje.bat`** s verziou v sebe.
- Záznam `launcher` musí v `apps.json` už existovať (`verzia`, `zdroj`, `spustit`, voliteľne `co_je_nove`).
- Bez `--koren` sa použije koreň z nastavení (pri vývoji falošný `test_data\L\_Nastroje`); pri skutočnom koreni sa
  skript pýta na potvrdenie. V režime Na prezeranie je publikovanie zakázané.

Ostatné aplikácie sa publikujú rovnako: `python nastroje/publikuj.py <app_id> <build>`.
To isté urobí v okne launchera Súbor → Nasadiť aplikáciu… (len plný režim; od verzie 2026.11.24-10).

## 2b. Spoločná šablóna výkresu (Excel + logo)

Šablóna `Template_cnc_vykres_viena_excel.xlsx` a `viena logo.PNG` sú spoločné pre Edgecam aj hyperMILL a ležia na L:\_Nastroje\sablony\<verzia>\ (`aktualna.txt` = platná verzia; staré verzie ostávajú, návrat späť = prepísať `aktualna.txt`).

```
python nastroje/publikuj.py sablony <priecinok_so_sablonou> [--verzia RRRR.MM.DD-N]
```

alebo v okne **Súbor → Nasadiť aplikáciu… → Šablóna výkresu – Excel + logo**. Pred zápisom sa šablóna skontroluje (popisy hlavičky, plochy na obrázky `A11:D29` / `E11:J29`, tlačová oblasť `A1:J30`, šírky stĺpcov); chybná sa nenasadí. `apps.json` sa nemení. Aplikácie (Edgecam, hyperMILL) si šablónu pri štarte skopírujú do `%LOCALAPPDATA%\NC_Nastroje\sablony` a používajú cache; ak L: nie je dostupný alebo je šablóna chybná, ostane predošlá kópia (a nakoniec šablóna zabalená v exe). Kód je v spoločnom balíku `cnc_vykresy_spolocne.sablony` (priečinok „cnc vykresy spolocne“ vedľa projektu; `zostav.py` ho zabalí do exe).

## 3. Inštalácia (kolega)

Dvojklik na `L:\_Nastroje\Instalovat NC Nastroje.bat`. Skript skopíruje launcher do
`%LOCALAPPDATA%\NC_Nastroje\launcher\<verzia>\`, zapíše `aktualna.txt` a spustí launcher. Pri prvom spustení sa objaví
dialóg:

- **Režim**: *Na prezeranie* (predvolené pre kanceláriu) alebo *Plný* (CNC programátor),
- **Spustiť po prihlásení** (zástupca v Po spustení, štart do oblasti oznámení),
- **Zástupca na ploche**.

Všetko sa dá neskôr zmeniť v Súbor → Nastavenia. Aplikácie si launcher sám skopíruje z L: a drží aktuálne.

## 4. Režim Na prezeranie

Skryje aplikácie s `len_plny_rezim: true` v `apps.json` (napr. Triedič NC). Skryté aplikácie sa nekopírujú, nespúšťajú
pri štarte a nemajú „Odoslať do“. Publikovanie je v ňom zakázané. Prepína sa v Nastaveniach, bez hesla (ochrana pred
omylom, nie zabezpečenie).

## 5. Aktualizácia launchera

Launcher sa raz za 10 min pozrie do `apps.json`. Ak je tam novšia verzia, stiahne ju do
`%LOCALAPPDATA%\NC_Nastroje\launcher\<nová>\` a nad dlaždicami ukáže pruh „Je nová verzia NC Nástrojov“. Po
potvrdení (Aktualizovať teraz) `aktualizator.bat` počká na ukončenie, zapíše `aktualna.txt` a spustí novú verziu.
Zástupcovia mieria na štartér `%LOCALAPPDATA%\NC_Nastroje\spustit_launcher.bat`, ktorý číta `aktualna.txt`, takže
spúšťajú vždy aktuálnu verziu.

## 6. Odinštalovanie

```
nc_nastroje.exe --odinstaluj
```

Odstráni zástupcov vytvorených NC Nástrojmi (Po spustení, Odoslať do, plocha); cudzích nikdy. Predtým ukonči bežiaci
launcher (ikona v oblasti oznámení → Ukončiť). Lokálne dáta (`%LOCALAPPDATA%\NC_Nastroje`, nastavenia v
`%APPDATA%\NC_Nastroje`) môžeš potom zmazať ručne.

## 7. Poznámky

- Aplikácie typu `python` v `apps.json` vyžadujú na počítači nainštalovaný Python (`pythonw` v PATH). Exe aplikácie
  to nepotrebujú.
- PyInstaller exe býva niekedy falošne označený antivírusom; ak sa to stane, pridaj výnimku pre
  `%LOCALAPPDATA%\NC_Nastroje`.
- Návrat na staršiu verziu launchera: v `apps.json` nastav `launcher.verzia`/`zdroj` na staršiu verziu a v
  `%LOCALAPPDATA%\NC_Nastroje\launcher\aktualna.txt` verziu, ktorá je lokálne nainštalovaná (staršie verzie sa po
  aktualizácii zmažú, ponechá sa aktuálna a predchádzajúca).

## Aplikácia spúšťaná priamo z L: (Lupa)

Lupa má vlastný spúšťač `L:\_Nastroje\lupa\Lupa.exe`, ktorý sa kopíruje do počítača sám. V apps.json má preto `typ: exe`,
`spustit` = plná cesta a **žiadny `zdroj`** – launcher ju nekopíruje, len spustí. Záznam pridá
`python nastroje/pridaj_lupu.py` (záloha apps.json.bak). Nasadzuje sa mimo launchera (`build.py` v repozitári Lupy).
