"""Zostaví launcher do `dist\\nc_nastroje\\` (PyInstaller --onedir --windowed) a zapíše `verzia.txt`.

    python nastroje/zostav.py [--vystup CESTA]

`verzia.txt` je verzia z `nc_nastroje/verzia.py`; `publikuj.py launcher` ju z nej berie, aby verzia v `apps.json`
presne sedela s verziou v exe (inak by sa aktualizácia launchera opakovala donekonečna).
Potom: `python nastroje/publikuj.py launcher dist\\nc_nastroje`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJEKT))

from nc_nastroje.verzia import VERZIA  # noqa: E402

NAZOV = "nc_nastroje"


def prikaz_pyinstaller(vystup: Path, praca: Path, ico: Path) -> list[str]:
    """Príkaz PyInstalleru (testuje sa bez spustenia). Dáta: ikony aplikácií a CO_JE_NOVE.md (Nápoveda → Čo je nové)."""
    return [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", NAZOV, "--distpath", str(vystup), "--workpath", str(praca), "--specpath", str(praca),
        "--icon", str(ico), "--paths", str(PROJEKT),
        "--add-data", f"{PROJEKT / 'nc_nastroje' / 'ikony'};nc_nastroje/ikony",
        "--add-data", f"{PROJEKT / 'CO_JE_NOVE.md'};.",
        "--collect-data", "sv_ttk", "--collect-all", "tkinterdnd2",
        "--hidden-import", "pystray._win32", "--hidden-import", "win32com.shell.shell",
        str(PROJEKT / "nastroje" / "vstup.py"),
    ]


def zostav(vystup: Path) -> Path:
    from nc_nastroje.ikona import uloz_ico, vytvor_ikonu
    praca = PROJEKT / "build"
    praca.mkdir(exist_ok=True)
    ico = uloz_ico(vytvor_ikonu(None, 256), praca / "nc_nastroje.ico")
    ciel = Path(vystup) / NAZOV
    for pokus in range(4):                       # antivírus po zostavení občas na chvíľu zamkne staré súbory
        if not ciel.exists():
            break
        try:
            shutil.rmtree(ciel)
        except OSError as e:
            if pokus == 3:
                raise SystemExit(f"Starý výstup {ciel} sa nepodarilo zmazať (zamknutý súbor?): {e}")
            time.sleep(3)
    print(f"Zostavujem NC Nástroje {VERZIA} …")
    subprocess.run(prikaz_pyinstaller(Path(vystup), praca, ico), check=True)
    exe = ciel / f"{NAZOV}.exe"
    if not exe.is_file():
        raise SystemExit(f"Zostavenie zlyhalo: {exe} neexistuje")
    (ciel / "verzia.txt").write_text(VERZIA + "\n", encoding="utf-8")
    subory = [p for p in ciel.rglob("*") if p.is_file()]
    velkost = sum(p.stat().st_size for p in subory) / 1e6
    print(f"Hotovo: {ciel} ({len(subory)} súborov, {velkost:.0f} MB, verzia {VERZIA})")
    print(f"Publikovať: python nastroje/publikuj.py launcher \"{ciel}\"")
    return ciel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Zostaví launcher (PyInstaller --onedir --windowed)")
    ap.add_argument("--vystup", default=str(PROJEKT / "dist"), help="kam zostaviť (predvolene dist\\)")
    a = ap.parse_args(argv)
    zostav(Path(a.vystup))
    return 0


if __name__ == "__main__":
    sys.exit(main())
