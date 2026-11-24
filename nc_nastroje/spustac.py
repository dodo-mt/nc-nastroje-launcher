"""Spúšťanie aplikácií."""
import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote

from .katalog import App

log = logging.getLogger(__name__)


def priecinok_aplikacie(app: App, koren_nastrojov: Path) -> Path | None:
    """Fáza 1: priamo zo zdroja v koreni nástrojov (lokálne kópie prídu vo fáze 4)."""
    return (Path(koren_nastrojov) / app.zdroj) if app.zdroj else None


def zostav_prikaz(app: App, koren_nastrojov: Path, cesty: list[str] | None = None) -> list[str]:
    priecinok = priecinok_aplikacie(app, koren_nastrojov)
    cesta_programu = str(priecinok / app.spustit)
    if app.typ == "python":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        zaklad = [str(pythonw if pythonw.exists() else sys.executable), cesta_programu]
    else:
        zaklad = [cesta_programu]
    arg = []
    for token in (app.argumenty or "").split():
        if token == "{cesty}":
            arg.extend(cesty or [])
        else:
            arg.append(token)
    return zaklad + arg


def spusti(app: App, koren_nastrojov: Path, cesty: list[str] | None = None) -> tuple[bool, str]:
    """Vráti (ok, správa pre používateľa). Nikdy nevyhodí výnimku."""
    try:
        if app.typ == "web":
            url = app.url
            if cesty and app.url_cesta:
                url = app.url_cesta.format(url=app.url, cesta=quote(cesty[0]))
            webbrowser.open(url)
            return True, ""
        prikaz = zostav_prikaz(app, koren_nastrojov, cesty)
        if not Path(prikaz[0]).exists() or (app.typ == "python" and not Path(prikaz[1]).exists()):
            log.error("Súbor aplikácie %s chýba: %s", app.id, prikaz)
            return False, "Nepodarilo sa spustiť – súbor chýba"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if app.typ == "python" else 0
        subprocess.Popen(prikaz, cwd=str(priecinok_aplikacie(app, koren_nastrojov)), creationflags=flags)
        log.info("Spustené %s: %s", app.id, prikaz)
        return True, ""
    except Exception as e:  # noqa: BLE001 – UI nesmie spadnúť
        log.exception("Spustenie %s zlyhalo", app.id)
        return False, f"Nepodarilo sa spustiť – {e}"


def otvor_priecinok(app: App, koren_nastrojov: Path) -> tuple[bool, str]:
    p = priecinok_aplikacie(app, koren_nastrojov)
    if not p or not p.exists():
        return False, "Priečinok aplikácie neexistuje"
    try:
        os.startfile(str(p))
        return True, ""
    except OSError as e:
        log.exception("Otvorenie priečinka zlyhalo")
        return False, str(e)
