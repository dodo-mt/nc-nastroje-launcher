"""Hľadanie priečinka zákazky na L: (a rovnakej cesty na R:). L: a R: sa len ČÍTAJÚ.

Štruktúra L: `L:\\<zákazník>\\<zákazka>\\<pozícia>\\…`; zákazníci majú za číslom aj meno
(`101270-Meno firmy`), preto sa hľadá podľa ZAČIATKU názvu. Nové zákazky `OD00021930` ležia
v priečinkoch zákazníkov, staré (`001252`) v starých zákazníkoch na najvyššej úrovni (`L:\\OD626\\001252`).
Staré a nové čísla NIE sú totožné (`OD626` je nová zákazka OD00000626, nie starý zákazník OD626).

Index `zákazník → zákazky` (len 2 úrovne L:) sa drží v cache a stavia na pozadí. Čo v cache chýba (zákazka
vznikla po poslednom indexe), skúsi sa priamym prechodom (jeden `stat` na zákazníka) a doplní sa do cache.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from . import nc_parsery_cesta  # noqa: F401 – pridá priečinok balíka nc_parsery do sys.path
from nc_parsery.cesty import priecinok_zakaznika_na_r  # noqa: F401 – názov priečinka zákazníka na R: (len číslo)
from nc_parsery.zakazky import TOKEN_ZAKAZKY as _TOKEN, Dotaz, normalizuj, vyhovuje  # noqa: F401 – normalizácia čísla zákazky je v spoločnom balíku
from .config import CACHE_DIR

log = logging.getLogger(__name__)

CACHE_SUBOR = CACHE_DIR / "zakazky.json"
FORMAT_CACHE = 1
MAX_VEK_INDEXU = timedelta(days=1)       # index sa obnovuje raz denne
IGNOROVANE_KORENE = ("_", "$", ".")       # _Nastroje, _Lupa, $RECYCLE.BIN …
IGNOROVANE_NAZVY = {"system volume information", "recycler"}
# ---------- vstup: Dotaz, normalizuj, vyhovuje sú v balíku nc_parsery.zakazky (importované vyššie) ----------


# ---------- výsledky ----------
MAX_NAVRHOV = 12                  # riadkov v zozname návrhov (ako v Lupe)
MAX_NAVRH_ZAKAZNIKOV = 4          # z toho najviac zákazníkov (ak zákaziek je málo, zákazníci zaberú viac)


class Navrhy(NamedTuple):
    polozky: list                 # najprv zákazky, potom zákazníci (Zhoda s prázdnou zakazka)
    viac: int                     # koľko ďalších zhôd sa do zoznamu nezmestilo

@dataclass(frozen=True)
class Zhoda:
    zakaznik: str
    zakazka: str                      # "" = zhoda je samotný zákazník (návrhy pod poľom)
    pocet: int = 0                    # pri zákazníkovi: počet zákaziek (len pre zobrazenie)

    @property
    def je_zakaznik(self) -> bool:
        return not self.zakazka

    @property
    def rel(self) -> str:
        return f"{self.zakaznik}\\{self.zakazka}"

    @property
    def stara(self) -> bool:
        return bool(re.match(r"^\d{6}", self.zakazka))

    def cesta(self, koren: Path) -> Path:
        return Path(koren) / self.zakaznik / self.zakazka

    def cesta_r(self, koren_r: Path) -> Path:
        """Cesta zákazky na R:. Priečinok zákazníka je tam len číslo (`101270-Meno firmy` → `101270`, programy tam ukladá Triedič NC); staré značenie (`OD626\\001252`) ostáva ako na L:."""
        return Path(koren_r) / priecinok_zakaznika_na_r(self.zakaznik) / self.zakazka


# ---------- index ----------
class IndexZakaziek:
    """Cache `zákazník -> [zákazky]` pre jeden koreň L:. Vlákna: všetko pod zámkom."""

    def __init__(self, koren_l: Path, subor: Path | None = None):
        self.koren = Path(koren_l)
        self.subor = Path(subor or CACHE_SUBOR)
        self._zakaznici: dict[str, list[str]] = {}
        self._cas: datetime | None = None
        self._zamok = threading.RLock()
        self.nacitaj()

    # ----- cache -----
    def nacitaj(self) -> bool:
        """Načíta cache (len ak je pre rovnaký koreň L:). Poškodená / cudzia cache = prázdny index."""
        with self._zamok:
            try:
                data = json.loads(self.subor.read_text(encoding="utf-8"))
                if data.get("format") != FORMAT_CACHE or data.get("koren") != str(self.koren):
                    raise ValueError("cache je pre iný koreň alebo formát")
                zak = {str(k): [str(z) for z in v] for k, v in data["zakaznici"].items()}
                self._cas = datetime.fromisoformat(data["cas"])
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                self._zakaznici, self._cas = {}, None
                return False
            self._zakaznici = zak
            return True

    def _uloz(self) -> None:
        data = {"format": FORMAT_CACHE, "koren": str(self.koren), "cas": (self._cas or datetime.now()).isoformat(timespec="seconds"),
                "zakaznici": self._zakaznici}
        self.subor.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.subor.with_name(self.subor.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.subor)

    @property
    def pocet(self) -> int:
        with self._zamok:
            return sum(len(v) for v in self._zakaznici.values())

    @property
    def cas(self) -> datetime | None:
        return self._cas

    def je_zastaraly(self, teraz: datetime | None = None) -> bool:
        return self._cas is None or (teraz or datetime.now()) - self._cas > MAX_VEK_INDEXU

    # ----- stavba (pomalé, sieť – volať z vlákna na pozadí) -----
    def zostav(self) -> int:
        """Prelistuje 2 úrovne L: (zákazník -> zákazka) a uloží cache. Vráti počet zákaziek.
        Výnimka OSError, ak koreň L: nie je dostupný (stará cache ostane). Chybu jedného zákazníka preskočí."""
        zakaznici: dict[str, list[str]] = {}
        with os.scandir(self.koren) as it:
            for z in it:
                if not _je_zakaznik(z):
                    continue
                try:
                    with os.scandir(z.path) as podit:
                        zakaznici[z.name] = sorted(e.name for e in podit if e.is_dir())
                except OSError as e:
                    log.warning("Zákazník %s sa nepodarilo prelistovať: %s", z.name, e)
        with self._zamok:
            self._zakaznici, self._cas = zakaznici, datetime.now()
            self._uloz()
        log.info("Index zákaziek: %d zákazníkov, %d zákaziek", len(zakaznici), self.pocet)
        return self.pocet

    # ----- hľadanie -----
    def _kluce(self, dotaz: Dotaz) -> list[str]:
        return [k for k in (dotaz.nova, dotaz.stara) if k]

    def hladaj(self, dotaz: Dotaz) -> list[Zhoda]:
        """Zhody v cache: nové pred starými, potom podľa zákazníka."""
        kluce = self._kluce(dotaz)
        with self._zamok:
            zhody = [Zhoda(zak, job) for zak, joby in self._zakaznici.items()
                     if not dotaz.zakaznik or vyhovuje(zak, dotaz.zakaznik)
                     for job in joby if any(vyhovuje(job, k) for k in kluce)]
        return _zorad(zhody)

    def hladaj_priamo(self, dotaz: Dotaz) -> list[Zhoda]:
        """Priamy prechod: `stat` presnej cesty `<zákazník>\\<kľúč>` (jedna operácia na zákazníka). Nájdené doplní do cache.
        Zákazníkov berie z cache, a ak ju nemá, z výpisu koreňa L:."""
        with self._zamok:
            zakaznici = list(self._zakaznici)
        if not zakaznici:
            with os.scandir(self.koren) as it:
                zakaznici = [z.name for z in it if _je_zakaznik(z)]
        zhody = []
        for zak in zakaznici:
            if dotaz.zakaznik and not vyhovuje(zak, dotaz.zakaznik):
                continue
            for kluc in self._kluce(dotaz):
                try:
                    if os.path.isdir(self.koren / zak / kluc):
                        zhody.append(Zhoda(zak, kluc))
                except OSError:
                    continue
        if zhody:
            with self._zamok:
                for z in zhody:
                    joby = self._zakaznici.setdefault(z.zakaznik, [])
                    if z.zakazka not in joby:
                        joby.append(z.zakazka)
                        joby.sort()
                self._cas = self._cas or datetime.now()
                try:
                    self._uloz()
                except OSError as e:
                    log.warning("Cache zákaziek sa nepodarilo uložiť: %s", e)
        return _zorad(zhody)

    def navrhy(self, text: str, max_riadkov: int = MAX_NAVRHOV, max_zakaznikov: int = MAX_NAVRH_ZAKAZNIKOV) -> Navrhy:
        """Návrhy počas písania (len cache v pamäti, bez siete).
        Zákazky: ČÍSLO (bez núl na začiatku) začína písaným číslom; `OD…` = len nové, `ON…` = len staré,
        `zákazník\číslo` zúži na zákazníka. Zákazníci: číslo pred pomlčkou (`101270`) alebo časť mena
        (všetky slová musia sedieť). Zákazky idú pred zákazníkmi; zákazníci majú vyhradené miesta."""
        t = " ".join(str(text or "").replace("/", "\\").split())
        zakaznik_filter = None
        if "\\" in t:
            zakaznik_filter, _, t = t.partition("\\")
            zakaznik_filter = zakaznik_filter.strip().casefold()
        m = re.fullmatch(r"(OD|ON)?\s*(\d+)", t.strip(), re.IGNORECASE)
        slova = [w for w in t.casefold().split() if w]
        if not m and (zakaznik_filter is not None or not slova):
            return Navrhy([], 0)
        predpona, cislo = ((m.group(1) or "").upper(), m.group(2).lstrip("0")) if m else ("", "")
        if m and not cislo:
            return Navrhy([], 0)
        joby_zhody: list[Zhoda] = []
        zakaznici_zhody: list[tuple[int, Zhoda]] = []
        with self._zamok:
            for zak, joby in self._zakaznici.items():
                if zakaznik_filter and not zak.casefold().startswith(zakaznik_filter):
                    continue
                if m and zakaznik_filter is None:
                    prvy = zak.split("-")[0]
                    if predpona:
                        sedi = zak.casefold().startswith(t.replace(" ", "").casefold())
                    else:
                        sedi = re.sub(r"^(OD|ON)", "", prvy, flags=re.IGNORECASE).lstrip("0").startswith(cislo)
                    if sedi:
                        zakaznici_zhody.append((0, Zhoda(zak, "", len(joby))))
                elif not m:
                    nazov = zak.casefold()
                    if all(w in nazov for w in slova):
                        zakaznici_zhody.append((0 if nazov.startswith(slova[0]) else 1, Zhoda(zak, "", len(joby))))
                if not m:
                    continue
                for job in joby:
                    mj = _TOKEN.match(job)
                    if not mj:
                        continue
                    stara = bool(re.match(r"^\d{6}", job))
                    if (predpona == "OD" and stara) or (predpona == "ON" and not stara):
                        continue
                    if mj.group(2).lstrip("0").startswith(cislo):
                        joby_zhody.append(Zhoda(zak, job))
        joby_zhody = _zorad(joby_zhody)
        zakaznici = [z for _, z in sorted(zakaznici_zhody, key=lambda x: (x[0], x[1].zakaznik.lower()))]
        nz = min(len(zakaznici), max(max_zakaznikov, max_riadkov - len(joby_zhody)))
        polozky = joby_zhody[:max_riadkov - nz] + zakaznici[:nz]
        return Navrhy(polozky, len(joby_zhody) + len(zakaznici) - len(polozky))

    def najdi(self, dotaz: Dotaz) -> list[Zhoda]:
        """Cache; ak v nej zákazka nie je, priamy prechod (doplní cache)."""
        return self.hladaj(dotaz) or self.hladaj_priamo(dotaz)


def _je_zakaznik(e: os.DirEntry) -> bool:
    try:
        return (e.is_dir() and not e.name.startswith(IGNOROVANE_KORENE)
                and e.name.lower() not in IGNOROVANE_NAZVY)
    except OSError:
        return False


def _zorad(zhody: list[Zhoda]) -> list[Zhoda]:
    return sorted(set(zhody), key=lambda z: (z.stara, z.zakaznik.lower(), z.zakazka))
