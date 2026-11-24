"""Model aplikácií a načítanie apps.json (chybný záznam sa preskočí a zaloguje)."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

TYPY = ("exe", "python", "web")


@dataclass
class App:
    id: str
    nazov: str
    typ: str
    popis: str = ""
    verzia: str = ""
    zdroj: str = ""
    spustit: str = ""
    ikona: str = ""
    farba: str = "#005FB8"
    prijima: list = field(default_factory=list)
    argumenty: str = "{cesty}"
    jedna_instancia: bool = False
    len_plny_rezim: bool = False
    spustit_pri_starte: bool = False
    stav: dict = field(default_factory=dict)
    co_je_nove: str = ""
    url: str = ""
    url_hladat: str = ""
    url_cesta: str = ""
    tlacidlo: str = "Spustiť"   # text hlavného tlačidla (Spustiť / Otvoriť)
    log: str = ""               # cesta k logu aplikácie (premenné prostredia sa rozbalia, relatívna ku koreňu nástrojov)
    pozastavit: bool = False    # dlaždica má tlačidlo Pozastaviť (Triedič NC)


def _app_zo_slovnika(d: dict) -> App:
    if not isinstance(d, dict):
        raise ValueError("záznam nie je objekt")
    for kluc in ("id", "nazov", "typ"):
        if not d.get(kluc):
            raise ValueError(f"chýba povinný kľúč '{kluc}'")
    if d["typ"] not in TYPY:
        raise ValueError(f"neznámy typ '{d['typ']}'")
    if d["typ"] == "web" and not d.get("url"):
        raise ValueError("web aplikácia nemá 'url'")
    if d["typ"] != "web" and not (d.get("zdroj") and d.get("spustit")):
        raise ValueError("chýba 'zdroj' alebo 'spustit'")
    prijima = d.get("prijima") or []
    if not isinstance(prijima, list):
        raise ValueError("'prijima' musí byť zoznam")
    # neznáme kľúče ignorujeme (budúca kompatibilita)
    znamy = App.__dataclass_fields__.keys()
    hodnoty = {k: v for k, v in d.items() if k in znamy}
    hodnoty["prijima"] = [str(p).lower() for p in prijima]
    hodnoty["stav"] = d.get("stav") or {}
    return App(**hodnoty)


def _zaznamy_z_textu(text: str) -> list | None:
    """Zoznam záznamov z textu apps.json, alebo None, ak štruktúra nie je platná."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    zaznamy = data.get("aplikacie") if isinstance(data, dict) else None
    return zaznamy if isinstance(zaznamy, list) else None


def nacitaj_katalog_z_textu(text: str) -> tuple[list[App], list[str]]:
    """Vráti (aplikácie, chyby). Chybný záznam sa preskočí a zaloguje, nikdy nevyhodí výnimku."""
    zaznamy = _zaznamy_z_textu(text)
    if zaznamy is None:
        msg = "apps.json: chýba zoznam 'aplikacie' alebo nie je platný JSON"
        log.error(msg)
        return [], [msg]
    chyby: list[str] = []
    apps, videne = [], set()
    for i, z in enumerate(zaznamy):
        try:
            app = _app_zo_slovnika(z)
            if app.id in videne:
                raise ValueError(f"duplicitné id '{app.id}'")
            videne.add(app.id)
            apps.append(app)
        except (ValueError, TypeError) as e:
            msg = f"apps.json: záznam #{i + 1} preskočený – {e}"
            log.warning(msg)
            chyby.append(msg)
    return apps, chyby


REZIMY = ("plny", "prezeranie")


def filtruj_rezim(apps: list[App], rezim: str) -> list[App]:
    """Režim „Na prezeranie“ skryje aplikácie s `len_plny_rezim` (napr. Triedič NC); Plný ukáže všetko."""
    if rezim == "prezeranie":
        return [a for a in apps if not a.len_plny_rezim]
    return list(apps)


def nacitaj_katalog(cesta: Path) -> tuple[list[App], list[str]]:
    """Vráti (aplikácie, chyby). Nikdy nevyhodí výnimku kvôli obsahu súboru."""
    try:
        text = Path(cesta).read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        msg = f"apps.json sa nepodarilo načítať: {e}"
        log.error(msg)
        return [], [msg]
    return nacitaj_katalog_z_textu(text)


def launcher_z_textu(text: str) -> dict | None:
    """Záznam `launcher` z apps.json: {verzia, zdroj, spustit, co_je_nove} alebo None (chýba / chybný)."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    zaznam = data.get("launcher") if isinstance(data, dict) else None
    if not isinstance(zaznam, dict) or not zaznam.get("verzia") or not zaznam.get("zdroj"):
        return None
    return {k: str(zaznam.get(k) or "") for k in ("verzia", "zdroj", "spustit", "co_je_nove")}
