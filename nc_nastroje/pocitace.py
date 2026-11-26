"""Prehľad počítačov: kto má ktorú verziu aplikácií a či beží stará.

Každý launcher (aj v režime Na prezeranie) raz za čas zapíše malý súbor
`<koreň nástrojov>\\_stav\\_pocitace\\<POCITAC>.json` (verzie nainštalované lokálne + verzie bežiacich aplikácií).
Okno „Prehľad počítačov“ (len plný režim) ich prečíta a porovná s aktuálnym katalógom. Žiadny server, len súbory na L:.
Zápis ide vždy na pozadí a atomicky (tmp + os.replace); výnimky sa len logujú.
"""
from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime
from pathlib import Path

import psutil

from . import aktualizacie
from .katalog import App

log = logging.getLogger(__name__)

PODADRESAR = Path("_stav") / "_pocitace"
FORMAT = 1
NEOZVAL_DNI = 2          # počítač sa neozval dlhšie = červená
ZABUDNUT_DNI = 60        # staršie záznamy sa v prehľade neukazujú
LAUNCHER_ID = "launcher"


def nazov_pocitaca() -> str:
    return (os.environ.get("COMPUTERNAME") or socket.gethostname() or "?").upper()


def _norm(cesta) -> str:
    return os.path.normcase(os.path.normpath(str(cesta)))


def bezi_verzie(local_dir: Path, app_ids: list[str]) -> dict[str, str]:
    """{id aplikácie: verzia}, ktorú práve beží (proces z `%LOCALAPPDATA%\\NC_Nastroje\\apps\\<id>\\<verzia>\\…`).
    Jeden prechod procesmi pre všetky aplikácie."""
    zaklad = _norm(Path(local_dir) / "apps") + os.sep
    out: dict[str, str] = {}
    for p in psutil.process_iter(["exe", "cmdline"]):
        try:
            cesty = [p.info.get("exe") or ""] + list(p.info.get("cmdline") or [])
        except (psutil.Error, OSError):
            continue
        for c in cesty:
            n = _norm(c) if c else ""
            if not n.startswith(zaklad):
                continue
            casti = n[len(zaklad):].split(os.sep)
            if len(casti) >= 2 and casti[0] in app_ids and aktualizacie.parsuj_verziu(casti[1]):
                stara = out.get(casti[0])
                if stara is None or aktualizacie.je_novsia(casti[1], stara):
                    out[casti[0]] = casti[1]
    return out


def zostav(apps: list[App], local_dir: Path, verzia_launchera: str, rezim: str,
           teraz: datetime | None = None, bezi: dict[str, str] | None = None) -> dict:
    """Záznam tohto počítača. Aplikácie spúšťané priamo z L: (Lupa) a webové sa nezapisujú (nemajú lokálnu verziu)."""
    teraz = teraz or datetime.now()
    spravovane = [a for a in apps if a.typ != "web" and not a.priamo]
    bezi = bezi if bezi is not None else bezi_verzie(local_dir, [a.id for a in spravovane])
    aplikacie = []
    for a in spravovane:
        dir_app = Path(local_dir) / "apps" / a.id
        aktivna = aktualizacie.aktivna_verzia(dir_app) or ""
        lokalne = aktualizacie.lokalne_verzie(dir_app)
        aplikacie.append({"id": a.id, "nazov": a.nazov, "nainstalovana": lokalne[-1] if lokalne else "",
                          "aktivna": aktivna, "bezi": a.id in bezi, "bezi_verzia": bezi.get(a.id, "")})
    try:
        uzivatel = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    except Exception:
        uzivatel = ""
    return {"format": FORMAT, "pocitac": nazov_pocitaca(), "uzivatel": uzivatel, "rezim": rezim,
            "cas": teraz.isoformat(timespec="seconds"), "launcher": verzia_launchera, "aplikacie": aplikacie}


def zapis(koren_nastrojov: Path, zaznam: dict) -> Path:
    """Atomický zápis `<koreň>\\_stav\\_pocitace\\<POCITAC>.json`. OSError nechá prejsť (volá sa na pozadí)."""
    adresar = Path(koren_nastrojov) / PODADRESAR
    adresar.mkdir(parents=True, exist_ok=True)
    cesta = adresar / f"{zaznam['pocitac']}.json"
    tmp = cesta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(zaznam, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, cesta)
    return cesta


def nacitaj(koren_nastrojov: Path, teraz: datetime | None = None) -> list[dict]:
    """Záznamy všetkých počítačov (poškodené a príliš staré sa preskočia), zoradené podľa názvu počítača."""
    teraz = teraz or datetime.now()
    out = []
    try:
        subory = sorted((Path(koren_nastrojov) / PODADRESAR).glob("*.json"))
    except OSError:
        return []
    for s in subory:
        try:
            z = json.loads(s.read_text(encoding="utf-8"))
            cas = datetime.fromisoformat(z["cas"])
            if not isinstance(z.get("aplikacie"), list) or not z.get("pocitac"):
                raise ValueError("chýba pocitac / aplikacie")
        except (OSError, ValueError, KeyError, TypeError) as e:
            log.warning("Záznam počítača %s sa nedá prečítať: %s", s.name, e)
            continue
        if (teraz - cas).days > ZABUDNUT_DNI:
            continue
        z["_cas"] = cas
        out.append(z)
    return sorted(out, key=lambda z: z["pocitac"].casefold())


def neozval_sa(zaznam: dict, teraz: datetime | None = None) -> bool:
    return ((teraz or datetime.now()) - zaznam["_cas"]).total_seconds() > NEOZVAL_DNI * 86400


def stav_aplikacie(e: dict | None, verzia_katalogu: str) -> tuple[str, str]:
    """(stav, text) bunky počítač × aplikácia; stav = kľúč z `tema.STAVY`:
    ok – aktuálna · upozornenie – beží stará verzia, treba zavrieť a otvoriť · nova_verzia – čaká novšia z L: ·
    necinny – nie je nainštalovaná."""
    if not e or not e.get("nainstalovana"):
        return "necinny", "—"
    v = e["nainstalovana"]
    if e.get("bezi") and e.get("bezi_verzia") and aktualizacie.je_novsia(v, e["bezi_verzia"]):
        return "upozornenie", f"beží {aktualizacie.skrat_verziu(v, e['bezi_verzia'])} → {aktualizacie.skrat_verziu(e['bezi_verzia'], v)}"
    if verzia_katalogu and aktualizacie.je_novsia(verzia_katalogu, v):
        return "nova_verzia", f"{aktualizacie.skrat_verziu(verzia_katalogu, v)} (čaká novšia)"
    return "ok", v + (" · beží" if e.get("bezi") else "")


def stav_launchera(verzia: str, verzia_katalogu: str) -> tuple[str, str]:
    if not verzia:
        return "necinny", "—"
    if verzia_katalogu and aktualizacie.je_novsia(verzia_katalogu, verzia):
        return "nova_verzia", f"{verzia} (čaká novšia)"
    return "ok", verzia


def pocet_starych(zaznamy: list[dict], verzie_katalogu: dict[str, str], teraz: datetime | None = None) -> int:
    """Koľko počítačov má otvorenú starú verziu aplikácie (oranžová) – pre krátku poznámku v stavovom riadku."""
    n = 0
    for z in zaznamy:
        if neozval_sa(z, teraz):
            continue
        if any(stav_aplikacie(e, verzie_katalogu.get(e.get("id", ""), ""))[0] == "upozornenie" for e in z["aplikacie"]):
            n += 1
    return n
