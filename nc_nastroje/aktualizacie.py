"""Lokálne kópie aplikácií, kontrola verzií a aktualizácie (aj samotného launchera).

Aplikácie sa NESPÚŠŤAJÚ z L: (zamknuté súbory by blokovali aktualizáciu, sieť je pomalšia).
Kopírujú sa do `%LOCALAPPDATA%\\NC_Nastroje\\apps\\<id>\\<verzia>\\`. L: sa len číta; mažú sa
výlučne priečinky verzií a `*.tmp` v lokálnom adresári aplikácie.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import CACHE_DIR, LOCAL_DIR
from .katalog import App, launcher_z_textu, nacitaj_katalog_z_textu, _zaznamy_z_textu

log = logging.getLogger(__name__)

APPS_DIR = LOCAL_DIR / "apps"
LAUNCHER_DIR = LOCAL_DIR / "launcher"
CO_JE_NOVE_LOKALNE = "CO_JE_NOVE.md"
PRIPNUTA = "_pripnuta.txt"          # verzia, na ktorú sa používateľ vrátil (návrat na predchádzajúcu)
PONECHAT_VERZII = 2                  # aktuálna + 1 predchádzajúca
_VERZIA_RE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})-(\d+)$")


# ---------- verzie ----------
def parsuj_verziu(v: str) -> tuple[int, int, int, int] | None:
    """`RRRR.MM.DD-poradie` -> (rok, mesiac, deň, poradie); neplatný formát -> None."""
    m = _VERZIA_RE.match(str(v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def je_novsia(a: str, b: str | None) -> bool:
    """Je verzia `a` novšia ako `b`? Chýbajúca `b` = áno; neplatná `a` = nie."""
    pa = parsuj_verziu(a)
    if pa is None:
        return False
    pb = parsuj_verziu(b) if b else None
    return pb is None or pa > pb


def skrat_verziu(stara: str, nova: str) -> str:
    """`2026.11.19-1`, `2026.11.24-1` -> `11.24-1` (rok sa vynechá, ak je rovnaký)."""
    if nova[:5] == stara[:5]:
        return nova[5:]
    return nova


# ---------- lokálne verzie ----------
def lokalne_verzie(dir_app: Path) -> list[str]:
    """Dokončené lokálne verzie (bez `.tmp`), od najstaršej po najnovšiu."""
    try:
        nazvy = [p.name for p in Path(dir_app).iterdir() if p.is_dir() and parsuj_verziu(p.name)]
    except OSError:
        return []
    return sorted(nazvy, key=parsuj_verziu)


def pripnuta_verzia(dir_app: Path) -> str | None:
    try:
        v = (Path(dir_app) / PRIPNUTA).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return v if v in lokalne_verzie(dir_app) else None


def aktivna_verzia(dir_app: Path) -> str | None:
    """Verzia, z ktorej sa aplikácia spúšťa: pripnutá (návrat späť), inak najnovšia lokálna."""
    pripnuta = pripnuta_verzia(dir_app)
    if pripnuta:
        return pripnuta
    lokalne = lokalne_verzie(dir_app)
    return lokalne[-1] if lokalne else None


def priecinok_aktivnej(app_id: str, apps_dir: Path | None = None) -> Path | None:
    dir_app = Path(apps_dir or APPS_DIR) / app_id
    v = aktivna_verzia(dir_app)
    return dir_app / v if v else None


def predchadzajuca_verzia(dir_app: Path) -> str | None:
    """Najbližšia staršia verzia než aktívna (cieľ pre „Návrat na predchádzajúcu verziu“)."""
    aktivna = aktivna_verzia(dir_app)
    starsie = [v for v in lokalne_verzie(dir_app) if aktivna and parsuj_verziu(v) < parsuj_verziu(aktivna)]
    return starsie[-1] if starsie else None


def pripni(dir_app: Path, verzia: str) -> None:
    if verzia not in lokalne_verzie(dir_app):
        raise ValueError(f"Verzia {verzia} nie je nainštalovaná lokálne")
    (Path(dir_app) / PRIPNUTA).write_text(verzia, encoding="utf-8")


def odpni(dir_app: Path) -> None:
    try:
        (Path(dir_app) / PRIPNUTA).unlink()
    except OSError:
        pass


# ---------- kopírovanie ----------
def _spocitaj(priecinok: Path) -> tuple[int, int]:
    n = velkost = 0
    for koren, _dirs, subory in os.walk(priecinok):
        for s in subory:
            n += 1
            velkost += os.path.getsize(os.path.join(koren, s))
    return n, velkost


def kopiruj_verziu(zdroj: Path, dir_app: Path, verzia: str) -> Path:
    """Skopíruje `zdroj` do `<dir_app>\\<verzia>.tmp`, overí počet a veľkosť súborov
    a až potom premenuje na `<verzia>`. Pri chybe nezostane nič rozkopírované."""
    zdroj, dir_app = Path(zdroj), Path(dir_app)
    if not zdroj.is_dir():
        raise FileNotFoundError(f"Zdroj verzie chýba: {zdroj}")
    ciel, tmp = dir_app / verzia, dir_app / (verzia + ".tmp")
    if ciel.exists():
        return ciel
    dir_app.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        shutil.copytree(zdroj, tmp)
        if _spocitaj(zdroj) != _spocitaj(tmp):
            raise OSError("Skopírované súbory nesedia s originálom (počet alebo veľkosť)")
        os.replace(tmp, ciel)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    log.info("Nainštalovaná verzia %s -> %s", verzia, ciel)
    return ciel


def vycisti_stare(dir_app: Path, ponechat: int = PONECHAT_VERZII) -> None:
    """Zmaže staré verzie (ponechá `ponechat` najnovších + pripnutú) a nedokončené `*.tmp`.
    Mažú sa len priečinky s názvom verzie alebo `<verzia>.tmp` v lokálnom adresári aplikácie."""
    dir_app = Path(dir_app)
    lokalne = lokalne_verzie(dir_app)
    chranit = set(lokalne[-ponechat:]) | {pripnuta_verzia(dir_app)}
    na_zmazanie = [dir_app / v for v in lokalne if v not in chranit]
    try:
        na_zmazanie += [p for p in dir_app.iterdir() if p.is_dir() and p.name.endswith(".tmp")
                        and parsuj_verziu(p.name[:-4])]
    except OSError:
        pass
    for p in na_zmazanie:
        try:
            shutil.rmtree(p)
            log.info("Zmazaná stará verzia %s", p)
        except OSError as e:   # napr. beží a súbory sú zamknuté – skúsi sa pri ďalšej aktualizácii
            log.warning("Starú verziu %s sa nepodarilo zmazať: %s", p, e)


def kopiruj_co_je_nove(app: App, koren_nastrojov: Path, dir_app: Path) -> None:
    """Lokálna kópia CO_JE_NOVE.md aplikácie (aby sa zobrazila bez siete). Chyba nie je dôvod zlyhať."""
    if not app.co_je_nove:
        return
    try:
        Path(dir_app).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(koren_nastrojov) / app.co_je_nove, Path(dir_app) / CO_JE_NOVE_LOKALNE)
    except OSError as e:
        log.warning("Čo je nové pre %s sa nepodarilo skopírovať: %s", app.id, e)


def precitaj_co_je_nove(app_id: str, apps_dir: Path | None = None) -> str | None:
    try:
        return (Path(apps_dir or APPS_DIR) / app_id / CO_JE_NOVE_LOKALNE).read_text(encoding="utf-8")
    except OSError:
        return None


# ---------- aktualizácia aplikácií ----------
@dataclass
class AppAktualizacia:
    stav: str = "aktualna"     # aktualna | kopiruje | caka (beží, použije sa pri ďalšom spustení) | chyba
    vzdialena: str = ""        # verzia v apps.json
    lokalna: str = ""          # verzia, z ktorej sa spúšťa
    sprava: str = ""
    stara: str = ""            # verzia, na ktorej beží aplikácia, kým sa nespustí znova (stav `caka`)


def aktualizuj_aplikacie(apps: list[App], koren_nastrojov: Path, bezi: Callable[[App], bool],
                         caka: dict[str, str], apps_dir: Path | None = None,
                         pri_priebehu: Callable[[str, AppAktualizacia], None] | None = None
                         ) -> dict[str, AppAktualizacia]:
    """Porovná `verzia` v apps.json s lokálnou a novšiu skopíruje (na pozadí, volať z vlákna).
    `caka` = {id: verzia, na ktorej aplikácia beží} pre aplikácie, ktoré použijú novú verziu až pri
    ďalšom spustení; mení sa na mieste (volajúci si ho drží medzi behmi)."""
    apps_dir = Path(apps_dir or APPS_DIR)
    vysledok: dict[str, AppAktualizacia] = {}
    for app in apps:
        if app.typ == "web" or not app.zdroj:
            continue
        try:
            vysledok[app.id] = _aktualizuj_jednu(app, Path(koren_nastrojov), apps_dir / app.id, bezi, caka, pri_priebehu)
        except Exception as e:  # noqa: BLE001 – jedna zlá aplikácia nesmie zastaviť ostatné
            log.exception("Aktualizácia %s zlyhala", app.id)
            vysledok[app.id] = AppAktualizacia("chyba", app.verzia, "", f"Aktualizácia zlyhala: {e}")
    return vysledok


def _aktualizuj_jednu(app: App, koren: Path, dir_app: Path, bezi, caka, pri_priebehu) -> AppAktualizacia:
    vzd = app.verzia
    if parsuj_verziu(vzd) is None:
        return AppAktualizacia("chyba", vzd, aktivna_verzia(dir_app) or "", f"Neplatná verzia '{vzd}' v apps.json")
    najnovsia = (lokalne_verzie(dir_app) or [None])[-1]
    if je_novsia(vzd, najnovsia):
        if pri_priebehu:
            pri_priebehu(app.id, AppAktualizacia("kopiruje", vzd, najnovsia or ""))
        try:
            kopiruj_verziu(koren / app.zdroj, dir_app, vzd)
        except Exception as e:  # noqa: BLE001
            log.error("Kopírovanie %s %s zlyhalo: %s", app.id, vzd, e)
            return AppAktualizacia("chyba", vzd, aktivna_verzia(dir_app) or "", f"Kopírovanie z L:\\ zlyhalo: {e}")
        odpni(dir_app)                       # nová verzia preberá miesto aktívnej (aj po návrate späť)
        kopiruj_co_je_nove(app, koren, dir_app)
        vycisti_stare(dir_app)
        if najnovsia is not None and bezi(app):
            caka[app.id] = najnovsia         # bežiaca aplikácia ostáva na starej verzii
    elif not (dir_app / CO_JE_NOVE_LOKALNE).exists():
        kopiruj_co_je_nove(app, koren, dir_app)
    if app.id in caka and not bezi(app):
        del caka[app.id]
    aktivna = aktivna_verzia(dir_app) or ""
    if app.id in caka:
        return AppAktualizacia("caka", vzd, aktivna, "Aktualizuje sa pri ďalšom spustení", stara=caka[app.id])
    return AppAktualizacia("aktualna", vzd, aktivna)


# ---------- katalóg s cache ----------
def _cache_apps(cache_dir: Path) -> Path:
    return Path(cache_dir) / "apps.json"


def _cache_koren(cache_dir: Path) -> Path:
    return Path(cache_dir) / "apps_koren.txt"


def _zapis_atomicky(cesta: Path, text: str) -> None:
    cesta.parent.mkdir(parents=True, exist_ok=True)
    tmp = cesta.with_name(cesta.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, cesta)


@dataclass
class Katalog:
    apps: list[App]
    chyby: list[str]
    zdroj: str                     # "siet" (čerstvý z L:) | "cache" (posledný uložený) | "ziadny"
    launcher: dict | None = None


def nacitaj_katalog_s_cache(koren_nastrojov: Path, cache_dir: Path | None = None,
                            len_cache: bool = False) -> Katalog:
    """Načíta apps.json z L:\\_Nastroje a uloží kópiu do cache. Ak L: nie je dostupný (alebo je apps.json
    poškodený), použije poslednú uloženú kópiu – ale len pre rovnaký koreň nástrojov.
    `len_cache=True` = nikdy nesiahne na sieť (rýchly štart UI)."""
    cache_dir = Path(cache_dir or CACHE_DIR)
    koren = str(koren_nastrojov)
    if not len_cache:
        try:
            text = (Path(koren_nastrojov) / "apps.json").read_text(encoding="utf-8")
        except (OSError, ValueError) as e:
            log.warning("apps.json na %s nie je dostupný: %s", koren, e)
            text = None
        if text is not None and _zaznamy_z_textu(text) is not None:
            try:
                _zapis_atomicky(_cache_apps(cache_dir), text)
                _zapis_atomicky(_cache_koren(cache_dir), koren)
            except OSError as e:
                log.warning("Cache apps.json sa nepodarilo uložiť: %s", e)
            apps, chyby = nacitaj_katalog_z_textu(text)
            return Katalog(apps, chyby, "siet", launcher_z_textu(text))
        if text is not None:
            log.error("apps.json na %s je poškodený – použije sa cache", koren)
    try:
        if _cache_koren(cache_dir).read_text(encoding="utf-8").strip() != koren:
            raise OSError("cache je pre iný koreň")
        text = _cache_apps(cache_dir).read_text(encoding="utf-8")
    except OSError:
        return Katalog([], [] if len_cache else ["apps.json nie je dostupný a cache neexistuje"], "ziadny")
    apps, chyby = nacitaj_katalog_z_textu(text)
    return Katalog(apps, chyby, "cache", launcher_z_textu(text))


# ---------- aktualizácia samotného launchera ----------
@dataclass
class LauncherAktualizacia:
    stav: str = "aktualny"     # aktualny | pripraveny (stiahnutý, čaká na reštart) | chyba
    verzia: str = ""
    adresar: Path | None = None
    sprava: str = ""
    spustit: str = ""
    co_je_nove: str = ""       # text Čo je nové (prečítaný z L: na pozadí)


def aktualizuj_launcher(info: dict | None, koren_nastrojov: Path, aktualna_verzia: str,
                        launcher_dir: Path | None = None) -> LauncherAktualizacia:
    """Ak je na L: novší launcher, stiahne ho do `%LOCALAPPDATA%\\NC_Nastroje\\launcher\\<verzia>\\`."""
    launcher_dir = Path(launcher_dir or LAUNCHER_DIR)
    if not info or not je_novsia(info["verzia"], aktualna_verzia):
        return LauncherAktualizacia("aktualny", aktualna_verzia)
    try:
        adresar = kopiruj_verziu(Path(koren_nastrojov) / info["zdroj"], launcher_dir, info["verzia"])
    except Exception as e:  # noqa: BLE001
        log.error("Stiahnutie launchera %s zlyhalo: %s", info["verzia"], e)
        return LauncherAktualizacia("chyba", info["verzia"], None, f"Stiahnutie novej verzie zlyhalo: {e}")
    text = ""
    if info.get("co_je_nove"):
        try:
            text = (Path(koren_nastrojov) / info["co_je_nove"]).read_text(encoding="utf-8")
        except OSError:
            pass
    return LauncherAktualizacia("pripraveny", info["verzia"], adresar,
                                spustit=info.get("spustit") or "nc_nastroje.exe", co_je_nove=text)


def zostav_aktualizator(pid: int, adresar: Path, spustit: str, verzia: str, launcher_dir: Path | None = None) -> str:
    """Text `aktualizator.bat`: počká na ukončenie launchera (PID), zapíše `aktualna.txt` a spustí novú verziu."""
    launcher_dir = Path(launcher_dir or LAUNCHER_DIR)
    exe = Path(adresar) / spustit
    trasa = LOCAL_DIR / "log" / "aktualizator.log"           # stopa behu aktualizátora (okno nemá konzolu)
    return "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'echo %date% %time% aktualizator caka na PID {pid} >> "{trasa}"',
        "set /a pokusov=0",
        ":cakaj",
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | find "{pid}" >nul',
        "if errorlevel 1 goto prepni",
        "set /a pokusov+=1",
        "if %pokusov% geq 60 goto prepni",
        "timeout /t 1 /nobreak >nul",
        "goto cakaj",
        ":prepni",
        f'echo %date% %time% prepinam na {verzia} (pokusov %pokusov%) >> "{trasa}"',
        f'> "{launcher_dir / "aktualna.txt"}" echo {verzia}',
        f'start "" /D "{adresar}" "{exe}"',
        f'echo %date% %time% nova verzia spustena >> "{trasa}"',
        "",
    ])


def spusti_aktualizator(aktualizacia: LauncherAktualizacia, pid: int | None = None) -> Path:
    """Zapíše a spustí `aktualizator.bat` (nezávisle od launchera). Volajúci potom launcher ukončí."""
    bat = LOCAL_DIR / "aktualizator.bat"
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    bat.write_text(zostav_aktualizator(pid or os.getpid(), aktualizacia.adresar, aktualizacia.spustit,
                                       aktualizacia.verzia), encoding="utf-8", newline="")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", str(bat)], creationflags=flags, close_fds=True)
    log.info("Spustený aktualizátor na verziu %s", aktualizacia.verzia)
    return bat


def je_zostaveny() -> bool:
    """Beží launcher ako zostavený exe (PyInstaller)? Zo zdrojového kódu sa launcher neaktualizuje."""
    return bool(getattr(sys, "frozen", False))
