# Návrhy zmien v aplikáciách

Launcher kód aplikácií nemení. Čo treba doplniť, sa urobí v repozitári danej aplikácie.

## Stavový súbor pre launcher (adaptér `subor_json`) – nové aplikácie

Ak má aplikácia ukazovať stav na dlaždici (napr. Nástrojový list), po behu zapíše
`L:\_Nastroje\_stav\<app_id>\<POCITAC>.json` (atomicky: zápis do `.tmp` + `os.replace`):

```json
{ "stav": "ok", "riadky": ["Posledná záloha: dnes 11:32", "Stroje: 5 / 6"],
  "cipy": [{"text": "MB65 A", "stav": "ok"}],
  "cas": "2026-11-24T11:32:00", "pocitac": "PC-PROG1" }
```

- `stav`: `ok` | `upozornenie` | `chyba` | `nova_verzia` | `necinny`.
- Súbor starší ako `max_vek_min` (default 1440) launcher ignoruje (stav `nezname`).
- Viac počítačov = viac súborov; launcher ukáže najhorší stav a detaily z najnovšieho.

TNC Sync a Lupa už stavový súbor zapisujú (`_tnc_sync_stav.json`, `lupa_scan.json`) – tam netreba nič meniť.

## Pozastavenie Triediča NC – príznakový súbor

Tlačidlo Pozastaviť na dlaždici a položka „Pozastaviť triedič“ v tray zapíšu LOKÁLNY príznak
`%LOCALAPPDATA%\NC_Nastroje\ovladanie\triedic_nc.pozastaveny` (obsah nie je dôležitý) a pri Pokračovať ho zmažú.
Na L: ani R: sa nezapisuje nič. Launcher kód Triediča nemení, preto **zatiaľ nemá žiadny účinok**, kým Triedič
príznak nezačne čítať.

Návrh pre Triedič NC: pred spracovaním každého programu (alebo raz za pár sekúnd) skontrolovať, či príznak existuje.
Ak áno, nič netriediť a počkať (programy ostávajú v `NC\`); po zmiznutí príznaku pokračovať. V tray ikone Triediča
stačí ukázať „Pozastavené“. Launcher zobrazuje stav „Pozastavený (požiadavka)“ a nič viac nepredpokladá.

## Parametre pre „Odoslať do“ a zástupcov – všetky aplikácie s `prijima`

Zástupcovia (Odoslať do, plocha) spúšťajú `nc_nastroje.exe --aplikacia <id> <cesta1> <cesta2> …`; launcher aplikáciu
spustí so zoznamom ciest ako s argumentmi (alebo `@subor.txt`, viď nižšie). Aplikácie netreba meniť, kým už čítajú
cesty z `sys.argv`.

## Zoznam ciest v súbore `@subor.txt` – všetky aplikácie s `prijima`

Keď launcher dostane veľa súborov (príkazový riadok by presiahol ~30 000 znakov), zapíše cesty do
dočasného súboru (`%LOCALAPPDATA%\NC_Nastroje\tmp\cesty_<id>.txt`, UTF-8, jedna cesta na riadok)
a aplikácii odovzdá jediný argument `@<cesta k súboru>`.

Aplikácia, ktorá prijíma súbory (`sys.argv`), má argument začínajúci `@` rozbaliť:

```python
def rozbal_argumenty(argv):
    cesty = []
    for a in argv:
        if a.startswith("@"):
            cesty += [r for r in open(a[1:], encoding="utf-8").read().splitlines() if r]
        else:
            cesty.append(a)
    return cesty
```

Pri bežnom počte súborov sa cesty odovzdávajú priamo ako argumenty (bez `@`).
