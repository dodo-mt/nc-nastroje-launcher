"""Čítanie stavov aplikácií (adaptéry). Launcher stav LEN ČÍTA, nikdy nezapisuje.

Jeden registrovaný adaptér = jedna funkcia `(app, kontext) -> Stav`. Adaptér smie vyhodiť
výnimku – `precitaj_stav` ju zachytí a vráti stav `nezname`. Všetko sa číta na pozadí
(`obnov_vsetko`), UI nikdy nečaká na sieť.
"""
from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

import psutil

from .katalog import App

log = logging.getLogger(__name__)

STAVY_HODNOTY = ("ok", "upozornenie", "chyba", "nova_verzia", "necinny", "nezname")
# Poradie „zlosti“ pre najhorší stav (ikona v tray): vyššie číslo = horšie.
_PORADIE = {"necinny": 0, "ok": 1, "nezname": 2, "nova_verzia": 3, "upozornenie": 4, "chyba": 5}
MAX_VEK_MIN = 1440          # súbor `subor_json` starší ako deň = stav neznámy
TNC_NEBEZI_DNI = 2          # TNC Sync: bez behu dlhšie ako 2 dni = „Záloha nebeží“
TNC_STROJ_DNI = 3           # TNC Sync: stroj bez úspešnej zálohy dlhšie ako 3 dni = chyba
LUPA_MAX_VEK_H = 24         # Lupa: sken starší ako 24 h = upozornenie
TIMEOUT_S = 10.0            # najdlhšie čakanie na sieť pri jednom obnovení


@dataclass
class Stav:
    stav: str = "nezname"
    text: str = ""                                   # text vedľa bodky; prázdny = predvolený z `tema.STAVY`
    riadky: list[str] = field(default_factory=list)
    cipy: list[tuple[str, str]] = field(default_factory=list)   # (text, stav)
    cas: datetime | None = None
    pocitac: str = ""
    log: list[str] = field(default_factory=list)


@dataclass
class Kontext:
    koren_nastrojov: Path
    koren_l: Path
    koren_r: Path
    local_dir: Path | None = None                    # %LOCALAPPDATA%\NC_Nastroje (lokálne kópie aplikácií)
    teraz: datetime = field(default_factory=datetime.now)


@dataclass
class Vysledok:
    stavy: dict[str, Stav]
    l_ok: bool
    r_ok: bool
    cas: datetime


ADAPTERY: dict[str, Callable[[App, Kontext], Stav]] = {}


def adapter(nazov: str):
    def dekorator(fn):
        ADAPTERY[nazov] = fn
        return fn
    return dekorator


# ---------- pomocné funkcie ----------
def horsi(a: str, b: str) -> str:
    return a if _PORADIE.get(a, 2) >= _PORADIE.get(b, 2) else b


def najhorsi(stavy) -> str:
    """Najhorší stav zo zoznamu (hodnoty alebo `Stav`); prázdny zoznam = `necinny`."""
    vysledok = "necinny"
    for s in stavy:
        vysledok = horsi(vysledok, s.stav if isinstance(s, Stav) else s)
    return vysledok


def formatuj_cas(dt: datetime, teraz: datetime) -> str:
    """„dnes 11:32“, „včera 11:32“, „24.11. 11:32“ (s rokom, ak je iný)."""
    cas = dt.strftime("%H:%M")
    if dt.date() == teraz.date():
        return f"dnes {cas}"
    if dt.date() == (teraz - timedelta(days=1)).date():
        return f"včera {cas}"
    datum = f"{dt.day}.{dt.month}."
    return f"{datum} {dt.year} {cas}" if dt.year != teraz.year else f"{datum} {cas}"


def _parse_cas(x) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(x))
    except (TypeError, ValueError):
        return None
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def _cesta(zaklad: Path, cesta: str) -> Path:
    p = Path(cesta)
    return p if p.is_absolute() else Path(zaklad) / p


def _nacitaj_json(p: Path) -> dict | None:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def je_dostupny(cesta) -> bool:
    try:
        return Path(cesta).exists()
    except OSError:
        return False


# ---------- adaptér: subor_json ----------
def _cipy_zo_zoznamu(zoznam) -> list[tuple[str, str]]:
    cipy = []
    for c in zoznam if isinstance(zoznam, list) else []:
        if isinstance(c, dict) and c.get("text"):
            stav = c.get("stav") if c.get("stav") in STAVY_HODNOTY else "nezname"
            cipy.append((str(c["text"]), stav))
    return cipy


@adapter("subor_json")
def _subor_json(app: App, k: Kontext) -> Stav:
    """Štandard pre nové aplikácie: `<cesta>\\*.json` (jeden súbor na počítač).
    Súbor starší ako `max_vek_min` sa ignoruje; stav = najhorší z čerstvých, detaily z najnovšieho."""
    cesta = app.stav.get("cesta")
    if not cesta:
        return Stav("nezname", "Bez údajov", ["V apps.json chýba stav.cesta"])
    p = _cesta(k.koren_nastrojov, cesta)
    if p.is_file():
        subory = [p]
    elif p.is_dir():
        subory = sorted(p.glob("*.json"))
    else:
        subory = []
    max_vek = timedelta(minutes=float(app.stav.get("max_vek_min", MAX_VEK_MIN)))
    cerstve: list[tuple[datetime, Stav]] = []
    zastarane = 0
    for s in subory:
        data = _nacitaj_json(s)
        if data is None:
            log.warning("Stavový súbor sa nedá prečítať: %s", s)
            continue
        try:
            cas = _parse_cas(data.get("cas")) or datetime.fromtimestamp(s.stat().st_mtime)
        except OSError:
            continue
        if k.teraz - cas > max_vek:
            zastarane += 1
            continue
        stav = data.get("stav") if data.get("stav") in STAVY_HODNOTY else "nezname"
        cerstve.append((cas, Stav(
            stav=stav, riadky=[str(r) for r in data.get("riadky") or []],
            cipy=_cipy_zo_zoznamu(data.get("cipy")), cas=cas,
            pocitac=str(data.get("pocitac") or s.stem),
            log=[str(r) for r in data.get("log") or []])))
    if not cerstve:
        if zastarane:
            return Stav("nezname", "Údaje sú staré", [f"Stavové súbory sú staršie ako {int(max_vek.total_seconds() // 60)} min"])
        return Stav("nezname", "Bez údajov", [])
    cerstve.sort(key=lambda x: x[0], reverse=True)
    vysledok = cerstve[0][1]
    vysledok.stav = najhorsi(s.stav for _, s in cerstve)
    return vysledok


# ---------- adaptér: proces ----------
def _norm(cesta) -> str:
    """Cesta na porovnanie: zjednotené lomítka, malé písmená, bez koncového lomítka."""
    return os.path.normcase(os.path.normpath(str(cesta)))


def _priecinky_aplikacie(app: App, k: Kontext) -> list[str]:
    priecinky = []
    if app.zdroj:
        priecinky.append(Path(k.koren_nastrojov) / app.zdroj)
    if k.local_dir:
        priecinky.append(Path(k.local_dir) / "apps" / app.id)
    return [_norm(p) + os.sep for p in priecinky]


def _bezi_proces(app: App, k: Kontext) -> bool:
    priecinky = tuple(_priecinky_aplikacie(app, k))
    if not priecinky:
        return False
    for p in psutil.process_iter(["exe", "cmdline"]):
        try:
            cesty = [p.info.get("exe") or ""] + list(p.info.get("cmdline") or [])
        except (psutil.Error, OSError):
            continue
        if any(_norm(c).startswith(priecinky) for c in cesty if c):
            return True
    return False


def bezi_aplikacia(app: App, k: Kontext) -> bool:
    """Beží aplikácia (proces z jej priečinka na L: alebo z lokálnych kópií)?"""
    return _bezi_proces(app, k)


@adapter("proces")
def _proces(app: App, k: Kontext) -> Stav:
    """Len či beží proces aplikácie (podľa cesty exe / skriptu v priečinku aplikácie)."""
    if _bezi_proces(app, k):
        return Stav("ok", "Beží")
    return Stav("necinny", "Nebeží")


# ---------- adaptér: tnc_sync ----------
_TNC_VYSLEDKY = {  # výsledok behu zálohy -> (stav, text)
    "OK": ("ok", "OK"),
    "UPOZORNENIE": ("upozornenie", "OK s upozornením"),
    "CIASTOCNE": ("upozornenie", "Čiastočne"),
    "ZRUSENE": ("upozornenie", "Zrušené"),
    "ZLYHALO": ("chyba", "Zlyhalo"),
}
TNC_SUBOR = Path("_tnc_sync") / "_tnc_sync_stav.json"


def _tnc_cipy(stroje, k: Kontext) -> list[tuple[str, str]]:
    cipy = []
    for nazov, e in (stroje.items() if isinstance(stroje, dict) else []):
        e = e if isinstance(e, dict) else {}
        ok, skus = _parse_cas(e.get("last_ok")), _parse_cas(e.get("last_try"))
        if ok and skus and ok >= skus:
            stav = "ok"
        elif ok and (k.teraz.date() - ok.date()).days <= TNC_STROJ_DNI:
            stav = "upozornenie"
        elif ok or skus:
            stav = "chyba"
        else:
            stav = "nezname"
        cipy.append((str(nazov), stav))
    return cipy


@adapter("tnc_sync")
def _tnc_sync(app: App, k: Kontext) -> Stav:
    """Číta stavový súbor TNC Sync (`_tnc_sync\\_tnc_sync_stav.json` v koreni L:, formát 1).
    `stav.cesta` (relatívna ku koreňu L:) ho vie prepísať, ak má TNC Sync spoločný adresár inde."""
    p = _cesta(k.koren_l, app.stav.get("cesta") or str(TNC_SUBOR))
    data = _nacitaj_json(p)
    if data is None:
        return Stav("nezname", "Bez údajov", ["Stavový súbor TNC Sync sa nenašiel"])
    beh = data.get("last_run") if isinstance(data.get("last_run"), dict) else {}
    koniec = _parse_cas(beh.get("end") or beh.get("start"))
    stav, text = _TNC_VYSLEDKY.get(str(beh.get("result")), ("nezname", "Neznámy výsledok"))
    riadky = ["Posledná záloha: " + (formatuj_cas(koniec, k.teraz) if koniec else "–")]
    ok_n, spolu = beh.get("machines_ok"), beh.get("machines_total")
    if ok_n is not None and spolu is not None:
        riadky.append(f"Stroje: {ok_n} / {spolu}")
    cipy = _tnc_cipy(data.get("machines"), k)
    if stav == "ok" and any(s in ("upozornenie", "chyba") for _, s in cipy):
        stav, text = "upozornenie", "OK s upozornením"
    limit = timedelta(days=float(app.stav.get("missing_days", TNC_NEBEZI_DNI)))
    if koniec is None or k.teraz - koniec > limit:
        stav, text = "chyba", "Záloha nebeží"
    return Stav(stav, text, riadky, cipy, koniec, str(data.get("pc") or ""),
                [str(e) for e in beh.get("errors") or []])


# ---------- adaptér: lupa_sken ----------
def _lupa_cesta(app: App, k: Kontext) -> Path | None:
    """`lupa_scan.json` vedľa databázy Lupy: z `stav.cesta` (relatívna ku koreňu L:), inak z `url`."""
    c = app.stav.get("cesta")
    if c:
        p = _cesta(k.koren_l, c)
        return p if p.suffix.lower() == ".json" else p / "lupa_scan.json"
    u = urlparse(app.url or "")
    if u.scheme != "file" or u.netloc:
        return None
    rel = unquote(u.path)
    m = re.match(r"^/?[A-Za-z]:[/\\](.*)$", rel)   # file:///L:/_Lupa/index.html -> _Lupa/index.html
    rel = m.group(1) if m else rel.lstrip("/")
    return Path(k.koren_l) / Path(rel).parent / "lupa_scan.json"


@adapter("lupa_sken")
def _lupa_sken(app: App, k: Kontext) -> Stav:
    p = _lupa_cesta(app, k)
    data = _nacitaj_json(p) if p else None
    try:
        koniec = datetime.fromtimestamp(float(data["finished"])) if data else None
    except (KeyError, TypeError, ValueError, OSError):
        koniec = None
    if koniec is None:
        return Stav("nezname", "Bez údajov", ["Stav skenu Lupy (lupa_scan.json) sa nenašiel"])
    chyb = int(data.get("errors") or 0)
    riadky = ["Posledný sken: " + formatuj_cas(koniec, k.teraz),
              ("Úplný" if data.get("full") else "Inkrementálny") + f" sken · chýb: {chyb}"]
    max_vek = timedelta(hours=float(app.stav.get("max_vek_h", LUPA_MAX_VEK_H)))
    if k.teraz - koniec > max_vek:
        return Stav("upozornenie", "Starý sken", riadky, [], koniec)
    if chyb:
        return Stav("upozornenie", "Chyby pri skene", riadky, [], koniec)
    return Stav("ok", "OK", riadky, [], koniec)


# ---------- čítanie všetkých stavov na pozadí ----------
_posledna_chyba: dict[str, str] = {}   # aby sa rovnaká chyba nelogovala každých 30 s


def _loguj_raz(id_: str, sprava: str, vynimka=False):
    if _posledna_chyba.get(id_) == sprava:
        return
    _posledna_chyba[id_] = sprava
    (log.exception if vynimka else log.warning)("Stav %s: %s", id_, sprava)


def precitaj_stav(app: App, k: Kontext) -> Stav:
    """Stav jednej aplikácie. Nikdy nevyhodí výnimku."""
    nazov = (app.stav or {}).get("adapter")
    if not nazov:
        return Stav("necinny", "Pripravený")
    fn = ADAPTERY.get(nazov)
    if fn is None:
        _loguj_raz(app.id, f"neznámy adaptér '{nazov}'")
        return Stav("nezname", "Neznámy adaptér")
    try:
        stav = fn(app, k)
        _posledna_chyba.pop(app.id, None)
        return stav
    except Exception as e:  # noqa: BLE001 – adaptér nesmie zhodiť launcher
        _loguj_raz(app.id, f"adaptér '{nazov}' zlyhal: {e!r}", vynimka=True)
        return Stav("nezname", "Chyba čítania stavu")


_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="stavy")
_BEZI: dict[str, Future] = {}   # úlohy, ktoré visia na sieti – znova sa nezadávajú


def _zadaj(kluc: str, fn, *args) -> Future:
    f = _BEZI.get(kluc)
    if f is None or f.done():
        f = _BEZI[kluc] = _POOL.submit(fn, *args)
    return f


def obnov_vsetko(apps: list[App], k: Kontext, timeout_s: float = TIMEOUT_S) -> Vysledok:
    """Prečíta stavy všetkých aplikácií a dostupnosť L:/R:. Volať z vlákna na pozadí
    (najviac jedno naraz). Úloha, ktorá nestihne timeout, dá `nezname`, UI nečaká."""
    ulohy = {a.id: _zadaj(a.id, precitaj_stav, a, k) for a in apps}
    f_l = _zadaj("__L", je_dostupny, k.koren_l)
    f_r = _zadaj("__R", je_dostupny, k.koren_r)
    wait([*ulohy.values(), f_l, f_r], timeout=timeout_s)
    stavy = {}
    for id_, f in ulohy.items():
        if f.done() and not f.cancelled() and f.exception() is None:
            stavy[id_] = f.result()
        else:
            stavy[id_] = Stav("nezname", "Čas vypršal", ["Čítanie stavu trvá príliš dlho"])
    dostupny = lambda f: f.done() and f.exception() is None and f.result()  # noqa: E731
    return Vysledok(stavy, bool(dostupny(f_l)), bool(dostupny(f_r)), k.teraz)
