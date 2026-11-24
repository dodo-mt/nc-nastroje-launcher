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


def nacitaj_katalog(cesta: Path) -> tuple[list[App], list[str]]:
    """Vráti (aplikácie, chyby). Nikdy nevyhodí výnimku kvôli obsahu súboru."""
    chyby: list[str] = []
    try:
        data = json.loads(Path(cesta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        msg = f"apps.json sa nepodarilo načítať: {e}"
        log.error(msg)
        return [], [msg]
    zaznamy = data.get("aplikacie") if isinstance(data, dict) else None
    if not isinstance(zaznamy, list):
        msg = "apps.json: chýba zoznam 'aplikacie'"
        log.error(msg)
        return [], [msg]
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
