"""Spúšťanie aplikácií."""
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import quote

from . import aktualizacie
from .config import LOCAL_DIR
from .katalog import App

log = logging.getLogger(__name__)

MAX_CESTY_ZNAKOV = 30_000          # dlhšie cesty sa odovzdajú ako @subor.txt (limit príkazového riadka ~32 767)
TMP_DIR = LOCAL_DIR / "tmp"        # dočasné súbory so zoznamom ciest
TMP_VEK_S = 24 * 3600              # staršie dočasné súbory sa pri ďalšom zápise zmažú


NIE_JE_LOKALNE = "Aplikácia sa ešte nestihla skopírovať z L:\\ – skús o chvíľu"


def priecinok_aplikacie(app: App) -> Path | None:
    """Priečinok aktívnej LOKÁLNEJ verzie (apps/<id>/<verzia> v %LOCALAPPDATA%/NC_Nastroje);
    z L: sa aplikácie nespúšťajú. None = zatiaľ nie je skopírovaná."""
    return aktualizacie.priecinok_aktivnej(app.id) if app.zdroj else None


def _cesty_do_suboru(cesty: list[str]) -> str:
    """Zapíše cesty (jedna na riadok, UTF-8) do dočasného súboru a vráti `@cesta`.
    Aplikácia to musí podporovať (viď docs/zmeny_v_aplikaciach.md). Maže len v LOCAL_DIR/tmp (v %LOCALAPPDATA%/NC_Nastroje)."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    for stary in TMP_DIR.glob("cesty_*.txt"):
        try:
            if time.time() - stary.stat().st_mtime > TMP_VEK_S:
                stary.unlink()
        except OSError:
            pass
    subor = TMP_DIR / f"cesty_{uuid.uuid4().hex[:10]}.txt"
    subor.write_text("\n".join(cesty) + "\n", encoding="utf-8")
    return "@" + str(subor)


def najdi_pythonw() -> str | None:
    """Python na spúšťanie aplikácií typu `python`. Zo zdrojového kódu je to ten, ktorý spustil launcher; v zostavenom
    exe je `sys.executable` samotný launcher (nie Python), preto sa hľadá nainštalovaný `pythonw`."""
    if not getattr(sys, "frozen", False):
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        return str(pythonw if pythonw.exists() else sys.executable)
    return shutil.which("pythonw") or shutil.which("python")


def zostav_prikaz(app: App, cesty: list[str] | None = None) -> list[str]:
    priecinok = priecinok_aplikacie(app)
    if priecinok is None:
        raise FileNotFoundError(NIE_JE_LOKALNE)
    cesta_programu = str(priecinok / app.spustit)
    if app.typ == "python":
        pythonw = najdi_pythonw()
        if not pythonw:
            raise FileNotFoundError("Aplikácia je skript v Pythone a Python nie je na tomto počítači nainštalovaný")
        zaklad = [pythonw, cesta_programu]
    else:
        zaklad = [cesta_programu]
    arg = []
    for token in (app.argumenty or "").split():
        if token == "{cesty}":
            if cesty and len(subprocess.list2cmdline(cesty)) > MAX_CESTY_ZNAKOV:
                arg.append(_cesty_do_suboru(cesty))
            else:
                arg.extend(cesty or [])
        else:
            arg.append(token)
    return zaklad + arg


def spusti(app: App, cesty: list[str] | None = None) -> tuple[bool, str]:
    """Vráti (ok, správa pre používateľa). Nikdy nevyhodí výnimku."""
    try:
        if app.typ == "web":
            url = app.url
            if cesty and app.url_cesta:
                url = app.url_cesta.format(url=app.url, cesta=quote(cesty[0]))
            webbrowser.open(url)
            return True, ""
        if priecinok_aplikacie(app) is None:
            log.warning("Aplikácia %s nie je lokálne nainštalovaná", app.id)
            return False, NIE_JE_LOKALNE
        prikaz = zostav_prikaz(app, cesty)
        if not Path(prikaz[0]).exists() or (app.typ == "python" and not Path(prikaz[1]).exists()):
            log.error("Súbor aplikácie %s chýba: %s", app.id, prikaz)
            return False, "Nepodarilo sa spustiť – súbor chýba"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if app.typ == "python" else 0
        subprocess.Popen(prikaz, cwd=str(priecinok_aplikacie(app)), creationflags=flags)
        log.info("Spustené %s: %s", app.id, prikaz)
        return True, ""
    except Exception as e:  # noqa: BLE001 – UI nesmie spadnúť
        log.exception("Spustenie %s zlyhalo", app.id)
        return False, f"Nepodarilo sa spustiť – {e}"


def spusti_hladaj(app: App, text: str) -> tuple[bool, str]:
    """Otvorí webovú aplikáciu (Lupu) s hľadaným textom cez `url_hladat` (URL-enkódovaný). Bez `url_hladat` ju
    otvorí len tak. Vráti (ok, správa). Nikdy nevyhodí výnimku."""
    try:
        if app.typ != "web" or not app.url:
            return False, "Aplikácia nevie hľadať (nie je webová)"
        url = app.url_hladat.format(url=app.url, text=quote(text)) if app.url_hladat else app.url
        webbrowser.open(url)
        log.info("Hľadanie v %s: %s", app.id, url)
        return True, ""
    except Exception as e:  # noqa: BLE001 – UI nesmie spadnúť
        log.exception("Hľadanie v %s zlyhalo", app.id)
        return False, f"Nepodarilo sa otvoriť – {e}"


def otvor_priecinok(app: App) -> tuple[bool, str]:
    p = priecinok_aplikacie(app)
    if not p or not p.exists():
        return False, "Priečinok aplikácie neexistuje"
    try:
        os.startfile(str(p))
        return True, ""
    except OSError as e:
        log.exception("Otvorenie priečinka zlyhalo")
        return False, str(e)
