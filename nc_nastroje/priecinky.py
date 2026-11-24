"""Otvorenie priečinka zákazky: Prieskumník (predvolene) alebo nová záložka v Total Commanderi."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

OTVARAT_V = ("prieskumnik", "totalcmd")
EXE_NAZVY = ("TOTALCMD64.EXE", "TOTALCMD.EXE")
BEZNE_CESTY = (r"C:\Program Files\totalcmd", r"C:\totalcmd", r"C:\Program Files (x86)\totalcmd",
               r"C:\Program Files\Total Commander", r"C:\Program Files (x86)\Total Commander")


def _exe_v_priecinku(priecinok) -> Path | None:
    for nazov in EXE_NAZVY:
        p = Path(priecinok) / nazov
        if p.is_file():
            return p
    return None


def najdi_total_commander(nastavena: str = "") -> Path | None:
    """Exe Total Commandera: z nastavenia (súbor alebo priečinok), potom premenná COMMANDER_PATH, register, bežné cesty."""
    if nastavena:
        p = Path(os.path.expandvars(nastavena))
        if p.is_file():
            return p
        if p.is_dir():
            return _exe_v_priecinku(p)
    kandidati = []
    if os.environ.get("COMMANDER_PATH"):
        kandidati.append(os.environ["COMMANDER_PATH"])
    try:
        import winreg
        for koren, kluc in ((winreg.HKEY_CURRENT_USER, r"Software\Ghisler\Total Commander"),
                            (winreg.HKEY_LOCAL_MACHINE, r"Software\Ghisler\Total Commander"),
                            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Ghisler\Total Commander")):
            try:
                with winreg.OpenKey(koren, kluc) as k:
                    kandidati.append(winreg.QueryValueEx(k, "InstallDir")[0])
            except OSError:
                pass
    except ImportError:
        pass
    kandidati.extend(BEZNE_CESTY)
    for c in kandidati:
        p = _exe_v_priecinku(c)
        if p:
            return p
    return None


def prikaz_total_commander(exe, cesta) -> str:
    """Príkazový riadok: /O = použiť bežiaci Total Commander, /T = nová záložka, /L = ľavý panel."""
    return f'"{exe}" /O /T /L="{cesta}"'


def otvor_priecinok(cesta, otvarat_v: str = "prieskumnik", totalcmd_cesta: str = "") -> str:
    """Otvorí priečinok. Vráti text výhrady (napr. že Total Commander sa nenašiel a otvoril sa Prieskumník), inak ''.
    Pri zlyhaní otvorenia vyhodí OSError."""
    if otvarat_v == "totalcmd":
        exe = najdi_total_commander(totalcmd_cesta)
        if exe is None:
            os.startfile(str(cesta))
            return "Total Commander sa nenašiel (Nastavenia → Cesty), otvoril sa Prieskumník."
        subprocess.Popen(prikaz_total_commander(exe, cesta), cwd=str(exe.parent))
        log.info("Total Commander: %s", cesta)
        return ""
    os.startfile(str(cesta))
    return ""
