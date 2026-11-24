"""Nasadenie novej verzie aplikácie (alebo launchera) do koreňa nástrojov (L:\\_Nastroje).

    python nastroje/publikuj.py <app_id> <cesta_k_buildu> [--verzia RRRR.MM.DD-N] [--koren CESTA] [--ano]

Postup (jediné miesto, kde sa zapisuje na L:\\_Nastroje; bežný beh launchera len číta):
  1. skopíruje build do <koren>\\<app_id>\\<verzia>.tmp\\ a overí počet a veľkosť súborov,
  2. premenuje na <koren>\\<app_id>\\<verzia>\\,
  3. urobí zálohu apps.json.bak,
  4. zapíše novú verziu do apps.json ATOMICKY (apps.json.tmp + os.replace).
Kým nie je hotový krok 4, klienti o novej verzii nevedia. `app_id` = `launcher` publikuje samotný launcher.
Bez `--koren` sa použije koreň z nastavení (pri vývoji falošný test_data\\L\\_Nastroje).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJEKT))

from nc_nastroje.aktualizacie import _spocitaj, je_novsia, parsuj_verziu  # noqa: E402


INSTALATOR = "Instalovat NC Nastroje.bat"     # pre kolegov: dvojklik na L:\\_Nastroje\\Instalovat NC Nastroje.bat


class PublikaciaChyba(Exception):
    """Zrozumiteľná chyba pre používateľa (nič sa nezapísalo do apps.json)."""


def verzia_z_buildu(build: Path) -> str | None:
    """Verzia zapísaná do `verzia.txt` pri zostavení (nastroje/zostav.py); None, ak súbor nie je."""
    try:
        v = (Path(build) / "verzia.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return v or None


def text_instalatora(verzia: str, spustit: str = "nc_nastroje.exe") -> str:
    """Text `Instalovat NC Nastroje.bat`: skopíruje launcher z L: do %LOCALAPPDATA%\\NC_Nastroje\\launcher\\<verzia>,
    zapíše `aktualna.txt` a spustí launcher s dialógom prvého spustenia. Verzia je zapečená pri publikovaní."""
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'set "VERZIA={verzia}"',
        'set "ZDROJ=%~dp0launcher\\%VERZIA%"',
        'set "ZAKLAD=%LOCALAPPDATA%\\NC_Nastroje\\launcher"',
        'set "CIEL=%ZAKLAD%\\%VERZIA%"',
        f'if exist "%ZDROJ%\\{spustit}" goto kopiruj',
        "echo Instalacia sa nenasla: %ZDROJ%",
        "pause",
        "exit /b 1",
        ":kopiruj",
        "echo Instalujem NC Nastroje %VERZIA% ...",
        'robocopy "%ZDROJ%" "%CIEL%" /E /NFL /NDL /NJH /NJS /NP >nul',
        "if errorlevel 8 goto chyba",
        '> "%ZAKLAD%\\aktualna.txt" echo %VERZIA%',
        f'start "" "%CIEL%\\{spustit}" --prve-spustenie',
        "exit /b 0",
        ":chyba",
        "echo Kopirovanie zlyhalo.",
        "pause",
        "exit /b 1",
        "",
    ])


def dalsia_verzia(existujuce: list[str], dnes: date | None = None) -> str:
    """Ďalšia verzia `RRRR.MM.DD-N` pre dnešok: N = najvyššie dnešné poradie + 1."""
    dnes = dnes or date.today()
    predpona = (dnes.year, dnes.month, dnes.day)
    poradia = [p[3] for v in existujuce if (p := parsuj_verziu(v)) and p[:3] == predpona]
    return f"{dnes.year}.{dnes.month:02d}.{dnes.day:02d}-{max(poradia, default=0) + 1}"


def _nacitaj_apps(cesta: Path) -> dict:
    try:
        data = json.loads(cesta.read_text(encoding="utf-8"))
    except OSError as e:
        raise PublikaciaChyba(f"apps.json sa nedá prečítať: {e}") from e
    except ValueError as e:
        raise PublikaciaChyba(f"apps.json nie je platný JSON: {e}") from e
    if not isinstance(data, dict):
        raise PublikaciaChyba("apps.json má neočakávaný tvar")
    return data


def _zaznam(data: dict, app_id: str) -> dict:
    if app_id == "launcher":
        z = data.get("launcher")
        if not isinstance(z, dict):
            raise PublikaciaChyba("V apps.json chýba záznam 'launcher' – pridaj ho (verzia, zdroj, spustit).")
        return z
    for z in data.get("aplikacie") or []:
        if isinstance(z, dict) and z.get("id") == app_id:
            if z.get("typ") == "web":
                raise PublikaciaChyba(f"'{app_id}' je webová aplikácia – nemá čo publikovať")
            return z
    raise PublikaciaChyba(f"Aplikácia '{app_id}' nie je v apps.json – najprv pridaj jej záznam.")


def publikuj(koren: Path, app_id: str, build: Path, verzia: str | None = None, dnes: date | None = None) -> dict:
    """Vráti {'app_id', 'verzia', 'cielovy', 'subory', 'bajty'}. Pri chybe vyhodí PublikaciaChyba
    a apps.json ostane nezmenený."""
    koren, build = Path(koren), Path(build)
    apps_json = koren / "apps.json"
    data = _nacitaj_apps(apps_json)
    zaznam = _zaznam(data, app_id)
    if not build.is_dir() or not any(build.rglob("*")):
        raise PublikaciaChyba(f"Build '{build}' neexistuje alebo je prázdny")

    spustit = str(zaznam.get("spustit") or "nc_nastroje.exe")
    if app_id == "launcher":
        # verzia v apps.json MUSÍ sedieť s verziou v exe, inak by launcher po aktualizácii hlásil starú verziu a
        # ponúkal aktualizáciu donekonečna – preto sa berie z verzia.txt, ktorý zapísal nastroje/zostav.py
        z_buildu = verzia_z_buildu(build)
        if z_buildu:
            if verzia and verzia != z_buildu:
                raise PublikaciaChyba(f"Verzia {verzia} nesedí s verzia.txt v builde ({z_buildu}) – exe by hlásil inú "
                                      "verziu a aktualizácia launchera by sa opakovala")
            verzia = z_buildu
        elif verzia is None:
            raise PublikaciaChyba("Build launchera nemá verzia.txt – zostav ho cez nastroje/zostav.py (alebo zadaj --verzia)")
        if not (build / spustit).is_file():
            raise PublikaciaChyba(f"Build launchera neobsahuje {spustit}")

    app_dir = koren / app_id
    existujuce = [p.name for p in app_dir.iterdir() if p.is_dir()] if app_dir.is_dir() else []
    aktualna = str(zaznam.get("verzia") or "")
    if verzia is None:
        verzia = dalsia_verzia(existujuce + [aktualna], dnes)
    elif parsuj_verziu(verzia) is None:
        raise PublikaciaChyba(f"Neplatná verzia '{verzia}' (očakávaný tvar RRRR.MM.DD-poradie)")
    if aktualna and parsuj_verziu(aktualna) and not je_novsia(verzia, aktualna):
        raise PublikaciaChyba(f"Verzia {verzia} nie je novšia ako súčasná {aktualna} – klienti by ju neprevzali")

    ciel, tmp = app_dir / verzia, app_dir / (verzia + ".tmp")
    if ciel.exists():
        raise PublikaciaChyba(f"Verzia {verzia} už existuje: {ciel} (nič sa neprepisuje)")
    app_dir.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        shutil.copytree(build, tmp)
        zdroj_pocty, ciel_pocty = _spocitaj(build), _spocitaj(tmp)
        if zdroj_pocty != ciel_pocty:
            raise PublikaciaChyba(f"Kontrola zlyhala: build má {zdroj_pocty[0]} súborov / {zdroj_pocty[1]} B, "
                                  f"kópia {ciel_pocty[0]} / {ciel_pocty[1]} B")
        os.replace(tmp, ciel)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    poznamky = build / "CO_JE_NOVE.md"        # poznámky k verzii pre „Čo je nové“ (v koreni aplikácie)
    if poznamky.is_file():
        shutil.copyfile(poznamky, app_dir / "CO_JE_NOVE.md")

    # až teraz sa o novej verzii dozvedia klienti: záloha + atomický zápis apps.json
    zaznam["verzia"] = verzia
    zaznam["zdroj"] = f"{app_id}\\{verzia}"
    shutil.copy2(apps_json, koren / "apps.json.bak")
    novy = apps_json.with_name("apps.json.tmp")
    novy.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(novy, apps_json)
    vysledok = {"app_id": app_id, "verzia": verzia, "cielovy": ciel, "subory": ciel_pocty[0], "bajty": ciel_pocty[1]}
    if app_id == "launcher":                       # inštalátor pre kolegov so zapečenou novou verziou
        instalator = koren / INSTALATOR
        instalator.write_text(text_instalatora(verzia, spustit), encoding="utf-8", newline="")
        vysledok["instalator"] = instalator
    return vysledok


def _je_testovaci_koren(koren: Path) -> bool:
    try:
        koren.resolve().relative_to((PROJEKT / "test_data").resolve())
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Publikuje novú verziu aplikácie do L:\\_Nastroje")
    ap.add_argument("app_id", help="id aplikácie z apps.json (alebo 'launcher')")
    ap.add_argument("build", help="priečinok s hotovým buildom")
    ap.add_argument("--verzia", help="RRRR.MM.DD-poradie (predvolene dnešná, ďalšie poradie)")
    ap.add_argument("--koren", help="koreň nástrojov (predvolene z nastavení)")
    ap.add_argument("--ano", action="store_true", help="nepýtať sa na potvrdenie pri skutočnom koreni")
    a = ap.parse_args(argv)

    from nc_nastroje.config import nacitaj_nastavenia
    nast = nacitaj_nastavenia()
    if nast.rezim == "prezeranie":
        print("Publikovanie je v režime „Na prezeranie“ vypnuté.", file=sys.stderr)
        return 2
    koren = Path(a.koren or nast.koren_nastrojov)
    if not _je_testovaci_koren(koren) and not a.ano:
        print(f"POZOR: zapisuje sa do skutočného koreňa nástrojov: {koren}")
        if input("Pokračovať? (ano/nie): ").strip().lower() != "ano":
            print("Zrušené.")
            return 1
    try:
        v = publikuj(koren, a.app_id, Path(a.build), a.verzia)
    except PublikaciaChyba as e:
        print(f"CHYBA: {e}", file=sys.stderr)
        return 1
    print(f"Hotovo: {v['app_id']} {v['verzia']} -> {v['cielovy']} ({v['subory']} súborov, {v['bajty']} B)")
    print("apps.json aktualizovaný (záloha apps.json.bak).")
    if "instalator" in v:
        print(f"Inštalátor pre kolegov: {v['instalator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
