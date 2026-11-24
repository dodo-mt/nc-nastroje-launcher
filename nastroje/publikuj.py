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
import sys
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJEKT))

from nc_nastroje.publikovanie import (INSTALATOR, PublikaciaChyba, dalsia_verzia, publikuj,  # noqa: E402,F401
                                      text_instalatora, verzia_z_buildu)


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
