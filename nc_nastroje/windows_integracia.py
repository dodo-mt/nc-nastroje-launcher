"""Integrácia s Windows: zástupcovia (.lnk) pre spustenie po prihlásení, „Odoslať do“ a plochu.

Zástupcu vytvára a maže len launcher a len takého, ktorého popis začína `MARKER` – cudzích
zástupcov (iné programy, vlastné súbory používateľa) nikdy neprepíše ani nezmaže.
Funkcie berú voliteľný cieľový priečinok, aby sa dali testovať v tmp bez zásahu do profilu.
"""
from __future__ import annotations

import gc
import logging
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import ikona
from .config import IKONY_DIR, LOCAL_DIR, PROJEKT
from .katalog import App

log = logging.getLogger(__name__)

MARKER = "NC Nástroje (spúšťač)"
NAZOV_STARTUP = "NC Nástroje.lnk"
EXE_NAZOV = "nc_nastroje.exe"
IKONY_LOKALNE = LOCAL_DIR / "ikony"
_NEPLATNE_V_NAZVE = re.compile(r'[<>:"/\\|?*]')


# ---------- zástupcovia ----------
def priecinok(druh: str) -> Path:
    """Priečinok shellu: `startup` (shell:startup), `sendto` (shell:sendto) alebo `desktop`."""
    from win32com.shell import shell, shellcon
    csidl = {"startup": shellcon.CSIDL_STARTUP, "sendto": shellcon.CSIDL_SENDTO,
             "desktop": shellcon.CSIDL_DESKTOPDIRECTORY}[druh]
    return Path(shell.SHGetFolderPath(0, csidl, 0, 0))


@contextmanager
def _com():
    """COM v tomto vlákne. Objekty (zástupca, shell) sa MUSIA uvoľniť pred `CoUninitialize`, inak spadne
    celý proces (access violation) – preto ich volajúci drží len v `with` a pred koncom ich zruší (`del`)."""
    import pythoncom
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        gc.collect()
        pythoncom.CoUninitialize()


def zastupca_vytvor(cesta: Path, ciel: str, argumenty: str = "", pracovny: str = "",
                    ikona_cesta: str = "", popis: str = "", okno: int = 1) -> None:
    """Zapíše .lnk (WScript.Shell). `okno`: 1 normálne, 7 minimalizované (pre .bat)."""
    import win32com.client
    cesta = Path(cesta)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    with _com():
        shell = win32com.client.Dispatch("WScript.Shell")
        lnk = shell.CreateShortCut(str(cesta))
        try:
            lnk.TargetPath = ciel
            lnk.Arguments = argumenty
            lnk.WorkingDirectory = pracovny
            lnk.Description = popis
            lnk.WindowStyle = okno
            if ikona_cesta:
                lnk.IconLocation = ikona_cesta
            lnk.Save()
        finally:
            del lnk, shell


def zastupca_precitaj(cesta: Path) -> dict | None:
    """{'ciel', 'argumenty', 'popis'} existujúceho .lnk, alebo None (neexistuje / nečitateľný)."""
    import win32com.client
    cesta = Path(cesta)
    if not cesta.is_file():
        return None
    with _com():
        shell = lnk = None
        vysledok = None
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            lnk = shell.CreateShortCut(str(cesta))
            vysledok = {"ciel": lnk.TargetPath, "argumenty": lnk.Arguments, "popis": lnk.Description}
        except Exception:  # noqa: BLE001 – poškodený .lnk nesmie zhodiť launcher
            log.warning("Zástupcu %s sa nepodarilo prečítať", cesta)
        finally:
            lnk = shell = None          # COM objekty sa uvoľnia ešte pred CoUninitialize (viď _com)
        return vysledok


def je_nas_zastupca(cesta: Path, id_aplikacie: str | None = None) -> bool:
    """Vytvoril tohto zástupcu launcher? (podľa značky v popise; voliteľne aj pre danú aplikáciu)"""
    z = zastupca_precitaj(cesta)
    if not z or not z["popis"].startswith(MARKER):
        return False
    return id_aplikacie is None or z["popis"] == f"{MARKER}: {id_aplikacie}"


def _zmaz_ak_nas(cesta: Path, id_aplikacie: str | None = None) -> bool:
    if je_nas_zastupca(cesta, id_aplikacie):
        Path(cesta).unlink()
        return True
    return False


# ---------- ako spustiť launcher ----------
@dataclass
class PrikazLauncheru:
    ciel: str
    argumenty: str        # základné argumenty (pred argumentmi launchera)
    pracovny: str
    okno: int = 1


def je_zostaveny() -> bool:
    return bool(getattr(sys, "frozen", False))


def text_startovaca(zalozny_exe: Path, launcher_dir: Path) -> str:
    """Text štartéra `spustit_launcher.bat`: spustí verziu z `launcher\\aktualna.txt` (po aktualizácii
    launchera), inak záložný exe. Zástupcovia mieria na štartér, takže prežijú aktualizáciu."""
    aktualna = Path(launcher_dir) / "aktualna.txt"
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'set "EXE={zalozny_exe}"',
        f'if not exist "{aktualna}" goto spusti',
        f'set /p VERZIA=<"{aktualna}"',
        f'if exist "{launcher_dir}\\%VERZIA%\\{EXE_NAZOV}" set "EXE={launcher_dir}\\%VERZIA%\\{EXE_NAZOV}"',
        ":spusti",
        'start "" "%EXE%" %*',
        "",
    ])


def zapis_startovac(subor: Path | None = None) -> Path:
    subor = Path(subor) if subor else LOCAL_DIR / "spustit_launcher.bat"
    subor.parent.mkdir(parents=True, exist_ok=True)
    subor.write_text(text_startovaca(Path(sys.executable), subor.parent / "launcher"), encoding="utf-8", newline="")
    return subor


def prikaz_launchera() -> PrikazLauncheru:
    """Zostavený exe: cez štartér (.bat). Zo zdrojového kódu (vývoj): `pythonw -m nc_nastroje.main`."""
    if je_zostaveny():
        return PrikazLauncheru(str(zapis_startovac()), "", str(LOCAL_DIR), okno=7)
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return PrikazLauncheru(str(pythonw if pythonw.exists() else sys.executable), "-m nc_nastroje.main", str(PROJEKT))


def _ikona_launchera() -> str:
    try:
        return str(ikona.uloz_ico(ikona.vytvor_ikonu(None, 256), IKONY_LOKALNE / "nc_nastroje.ico"))
    except OSError as e:
        log.warning("Ikonu launchera sa nepodarilo uložiť: %s", e)
        return ""


def ikona_aplikacie(app: App) -> str:
    """.ico aplikácie (z PNG v `ikony\\`) pre zástupcu; "" ak sa nedá."""
    zdroj = IKONY_DIR / (app.ikona or f"{app.id}.png")
    try:
        from PIL import Image
        return str(ikona.uloz_ico(Image.open(zdroj).convert("RGBA"), IKONY_LOKALNE / f"{app.id}.ico"))
    except (OSError, ValueError) as e:
        log.warning("Ikonu aplikácie %s sa nepodarilo pripraviť: %s", app.id, e)
        return ""


def _argumenty(p: PrikazLauncheru, *dalsie: str) -> str:
    return " ".join(x for x in (p.argumenty, *dalsie) if x)


# ---------- spustenie po prihlásení ----------
def nastav_po_prihlaseni(zapnut: bool, dir_startup: Path | None = None) -> None:
    lnk = (Path(dir_startup) if dir_startup else priecinok("startup")) / NAZOV_STARTUP
    if not zapnut:
        _zmaz_ak_nas(lnk)
        return
    if lnk.exists() and not je_nas_zastupca(lnk):
        raise FileExistsError(f"V priečinku Po spustení už je cudzí súbor '{NAZOV_STARTUP}'")
    p = prikaz_launchera()
    zastupca_vytvor(lnk, p.ciel, _argumenty(p, "--tray"), p.pracovny, _ikona_launchera(),
                    f"{MARKER}: spustenie po prihlásení", p.okno)


def je_po_prihlaseni(dir_startup: Path | None = None) -> bool:
    return je_nas_zastupca((Path(dir_startup) if dir_startup else priecinok("startup")) / NAZOV_STARTUP)


# ---------- „Odoslať do“ a plocha ----------
def nazov_zastupcu(app: App) -> str:
    return _NEPLATNE_V_NAZVE.sub("_", app.nazov).strip() or app.id


def _vytvor_pre_aplikaciu(lnk: Path, app: App) -> None:
    p = prikaz_launchera()
    zastupca_vytvor(lnk, p.ciel, _argumenty(p, "--aplikacia", app.id), p.pracovny,
                    ikona_aplikacie(app), f"{MARKER}: {app.id}", p.okno)


def synchronizuj_odoslat_do(apps: list[App], povolene: list[str], dir_sendto: Path | None = None) -> list[str]:
    """Vytvorí zástupcov pre `povolene` aplikácie (len tie, čo niečo prijímajú) a zmaže našich
    zástupcov ostatných. Vráti zoznam chýb (prázdny = všetko v poriadku)."""
    d = Path(dir_sendto) if dir_sendto else priecinok("sendto")
    chyby = []
    for app in apps:
        lnk = d / f"{nazov_zastupcu(app)}.lnk"
        try:
            if app.id in povolene and app.prijima:
                if lnk.exists() and not je_nas_zastupca(lnk, app.id):
                    chyby.append(f"Odoslať do: '{lnk.name}' už existuje a nie je od NC Nástrojov – ponechané")
                    continue
                _vytvor_pre_aplikaciu(lnk, app)
            else:
                _zmaz_ak_nas(lnk, app.id)
        except Exception as e:  # noqa: BLE001
            log.exception("Odoslať do pre %s zlyhalo", app.id)
            chyby.append(f"Odoslať do ({app.nazov}): {e}")
    return chyby


NAZOV_PLOCHA = "NC Nástroje.lnk"


def vytvor_launcher_na_ploche(dir_desktop: Path | None = None) -> tuple[bool, str]:
    """Zástupca samotného launchera (otvorí okno) na ploche. Cudzí súbor s rovnakým názvom nepremaže."""
    try:
        lnk = (Path(dir_desktop) if dir_desktop else priecinok("desktop")) / NAZOV_PLOCHA
        if lnk.exists() and not je_nas_zastupca(lnk):
            return False, f"Na ploche už je '{NAZOV_PLOCHA}' – nepremazávam ho"
        p = prikaz_launchera()
        zastupca_vytvor(lnk, p.ciel, _argumenty(p), p.pracovny, _ikona_launchera(), f"{MARKER}: plocha", p.okno)
        return True, f"Zástupca '{NAZOV_PLOCHA}' je na ploche"
    except Exception as e:  # noqa: BLE001
        log.exception("Zástupca launchera na ploche zlyhal")
        return False, f"Zástupcu sa nepodarilo vytvoriť: {e}"


def odstran_zastupcov(dir_startup: Path | None = None, dir_sendto: Path | None = None,
                      dir_desktop: Path | None = None) -> list[str]:
    """Odinštalovanie: zmaže VŠETKÝCH zástupcov vytvorených launcherom (Po spustení, Odoslať do, plocha).
    Cudzích zástupcov (bez našej značky) nechá. Vráti zoznam zmazaných súborov."""
    zmazane = []
    priecinky = (Path(dir_startup) if dir_startup else priecinok("startup"),
                 Path(dir_sendto) if dir_sendto else priecinok("sendto"),
                 Path(dir_desktop) if dir_desktop else priecinok("desktop"))
    for d in priecinky:
        try:
            lnky = sorted(d.glob("*.lnk"))
        except OSError:
            continue
        for lnk in lnky:
            try:
                if _zmaz_ak_nas(lnk):
                    zmazane.append(str(lnk))
            except OSError as e:
                log.warning("Zástupcu %s sa nepodarilo zmazať: %s", lnk, e)
    return zmazane


def vytvor_na_ploche(app: App, dir_desktop: Path | None = None) -> tuple[bool, str]:
    """Zástupca aplikácie na ploche (spustí ju cez launcher). Vráti (ok, správa)."""
    try:
        d = Path(dir_desktop) if dir_desktop else priecinok("desktop")
        lnk = d / f"{nazov_zastupcu(app)}.lnk"
        if lnk.exists() and not je_nas_zastupca(lnk, app.id):
            return False, f"Na ploche už je '{lnk.name}' – nepremazávam ho"
        _vytvor_pre_aplikaciu(lnk, app)
        return True, f"Zástupca '{lnk.name}' je na ploche"
    except Exception as e:  # noqa: BLE001
        log.exception("Zástupca na ploche pre %s zlyhal", app.id)
        return False, f"Zástupcu sa nepodarilo vytvoriť: {e}"
