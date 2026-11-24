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

from .config import CACHE_DIR

log = logging.getLogger(__name__)

CACHE_SUBOR = CACHE_DIR / "zakazky.json"
FORMAT_CACHE = 1
MAX_VEK_INDEXU = timedelta(days=1)       # index sa obnovuje raz denne
IGNOROVANE_KORENE = ("_", "$", ".")       # _Nastroje, _Lupa, $RECYCLE.BIN …
IGNOROVANE_NAZVY = {"system volume information", "recycler"}
_TOKEN = re.compile(r"^(OD|ON)?(\d+)(?:[-_ .].*)?$", re.IGNORECASE)   # 21930, OD21930, 21930-1A, ON001252


# ---------- vstup ----------
@dataclass(frozen=True)
class Dotaz:
    text: str
    nova: str | None = None           # `OD00021930`
    stara: str | None = None          # `001252`
    zakaznik: str | None = None       # začiatok názvu zákazníka (z `OD626\001252` alebo `101270\21930`)


def _kluce_zakazky(token: str) -> tuple[str | None, str | None] | None:
    """(nová, stará) podľa jedného tokenu. None = nepoznáme."""
    m = _TOKEN.match(token.strip())
    if not m:
        return None
    predpona, cislice = (m.group(1) or "").upper(), m.group(2)
    n = len(cislice)
    nova = f"OD{int(cislice):08d}" if n <= 8 else None
    stara = f"{int(cislice):06d}" if n <= 6 else None
    if predpona == "OD":
        stara = None                   # OD… je vždy nové značenie
    elif predpona == "ON":
        nova = None                    # ON… je vždy staré značenie
    elif n >= 7:
        stara = None
    if nova is None and stara is None:
        return None
    return nova, stara


def normalizuj(text: str) -> Dotaz | None:
    """`21930`, `OD21930`, `OD00021930`, `21930-1A` -> nová `OD00021930` (a pri ≤6 číslicach aj stará `021930`);
    `ON001252` alebo `OD626\\001252` -> stará. None = nevyzerá ako číslo zákazky."""
    t = " ".join(str(text or "").replace("/", "\\").split())
    if not t:
        return None
    zakaznik = None
    if "\\" in t:
        casti = [c for c in t.split("\\") if c.strip()]
        if len(casti) < 2:
            return None
        zakaznik, t = casti[0].strip(), casti[1].strip()
        kluce = _kluce_zakazky(t)
        if kluce is None:
            return None
        nova, stara = kluce
        if re.fullmatch(r"OD\d+", zakaznik, re.IGNORECASE) and nova and not t.upper().startswith("OD"):
            nova = None                # `OD626\001252`: za starým zákazníkom je stará zákazka
        return Dotaz(text.strip(), nova, stara, zakaznik)
    kluce = _kluce_zakazky(t)
    if kluce is None:
        return None
    return Dotaz(text.strip(), kluce[0], kluce[1], None)


def vyhovuje(nazov: str, kluc: str) -> bool:
    """Názov začína kľúčom a hneď za ním nie je číslica (`OD0002193` nesmie sedieť na `OD00021930`)."""
    n, k = nazov.upper(), kluc.upper()
    return n.startswith(k) and not (len(n) > len(k) and n[len(k)].isdigit())


# ---------- výsledky ----------
@dataclass(frozen=True)
class Zhoda:
    zakaznik: str
    zakazka: str

    @property
    def rel(self) -> str:
        return f"{self.zakaznik}\\{self.zakazka}"

    @property
    def stara(self) -> bool:
        return bool(re.match(r"^\d{6}", self.zakazka))

    def cesta(self, koren: Path) -> Path:
        return Path(koren) / self.zakaznik / self.zakazka


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
