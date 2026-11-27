"""Editor strojov (Súbor → Stroje…): logika bez UI – úprava zoznamu skupín, modelov a kusov v `stroje.json`.

Súbor `L:\\_Nastroje\\Nastavenia\\stroje.json` čítajú všetky aplikácie (balík `nc_parsery.stroje`). Tento modul pracuje
s kópiou údajov (slovník v tvare súboru), kontroluje ju rovnakými pravidlami ako čítanie (`stroje.zo_slovnika`) a zapíše
len vtedy, keď sa súbor medzitým nezmenil (iný počítač, „Naučiť sa“ v Triediči). Zápis: atómovo so zálohou `.bak`.

`id` vzniká z názvu a potom sa nemení – premenovanie mení len názov.
Texty v hlavičke sa v editore píšu jednoducho (obyčajný text, medzera = ľubovoľne veľa medzier); regulárny výraz
sa dá zadať s predponou `re:`.
"""
from __future__ import annotations

import copy
import os
import re
from pathlib import Path

from . import nc_parsery_cesta  # noqa: F401 – pridá priečinok balíka nc_parsery do sys.path
from nc_parsery import hlavicka as _hlavicka
from nc_parsery import stroje

PREDPONA_REGEX = "re:"
_SPECIALNE = set(".^$*+?{}[]|()\\")


class SuborZmenenyChyba(Exception):
    """Súbor stroje.json sa po načítaní zmenil (iný počítač alebo „Naučiť sa“) – najprv ho treba načítať znova."""


# ------------------------------------------------------------------ jednoduchý zápis textov hlavičky

def text_na_regex(text: str) -> str:
    """`DMC 160` -> `DMC\\s*160`: špeciálne znaky sa escapujú, medzera (aj viac) znamená „ľubovoľne veľa medzier“."""
    vystup, medzera = [], False
    for znak in text.strip():
        if znak.isspace():
            medzera = True
            continue
        if medzera:
            vystup.append(r"\s*")
            medzera = False
        vystup.append("\\" + znak if znak in _SPECIALNE else znak)
    return "".join(vystup)


def regex_na_text(regex: str) -> str | None:
    """Spätný prevod: jednoduchý výraz (len text a `\\s*`) -> obyčajný text, inak None (pokročilý výraz)."""
    text, i = [], 0
    while i < len(regex):
        if regex.startswith(r"\s*", i):
            text.append(" ")
            i += 3
        elif regex[i] == "\\":
            if i + 1 >= len(regex) or regex[i + 1] not in _SPECIALNE:
                return None
            text.append(regex[i + 1])
            i += 2
        elif regex[i] in _SPECIALNE:
            return None
        else:
            text.append(regex[i])
            i += 1
    spat = "".join(text)
    return spat if text_na_regex(spat) == regex else None


def regexy_na_riadky(regexy: list[str]) -> str:
    """Zoznam regexov modelu -> text do poľa (jeden na riadok; pokročilé s predponou `re:`)."""
    return "\n".join(regex_na_text(r) or PREDPONA_REGEX + r for r in regexy)


def riadky_na_regexy(text: str) -> list[str]:
    out = []
    for riadok in text.splitlines():
        riadok = riadok.strip()
        if not riadok:
            continue
        out.append(riadok[len(PREDPONA_REGEX):].strip() if riadok.lower().startswith(PREDPONA_REGEX) else text_na_regex(riadok))
    return [r for r in out if r]


def riadky(text: str) -> list[str]:
    """Pole „jeden na riadok“ -> zoznam neprázdnych riadkov."""
    return [r.strip() for r in text.splitlines() if r.strip()]


# ------------------------------------------------------------------ súbor

def podpis(cesta: str | os.PathLike) -> tuple[int, int] | None:
    """(čas zmeny, veľkosť) súboru alebo None, keď neexistuje – na zistenie, či ho medzitým niekto zmenil."""
    try:
        s = Path(cesta).stat()
    except OSError:
        return None
    return (s.st_mtime_ns, s.st_size)


class Editor:
    """Pracovná kópia zoznamu strojov s operáciami editora a kontrolou."""

    def __init__(self, zoznam: stroje.Zoznam):
        self._povodne = copy.deepcopy(zoznam.na_slovnik())
        self.d = copy.deepcopy(self._povodne)

    # ----- prístup -----
    @property
    def skupiny(self) -> list[dict]:
        return self.d["skupiny"]

    @property
    def modely(self) -> list[dict]:
        return self.d["modely"]

    @property
    def kusy(self) -> list[dict]:
        return self.d["kusy"]

    def skupina(self, id_: str) -> dict | None:
        return next((s for s in self.skupiny if s["id"] == id_), None)

    def model(self, id_: str) -> dict | None:
        return next((m for m in self.modely if m["id"] == id_), None)

    def kus(self, id_: str) -> dict | None:
        return next((k for k in self.kusy if k["id"] == id_), None)

    def modely_skupiny(self, id_skupiny: str) -> list[dict]:
        return [m for m in self.modely if m["skupina"] == id_skupiny]

    def kusy_modelu(self, id_modelu: str) -> list[dict]:
        return [k for k in self.kusy if k["model"] == id_modelu]

    @property
    def zmenene(self) -> bool:
        return self.d != self._povodne

    def oznac_ulozene(self) -> None:
        self._povodne = copy.deepcopy(self.d)

    # ----- operácie -----
    def _nove_id(self, nazov: str, existujuce: set[str]) -> str:
        zaklad = stroje.slug(nazov) or "stroj"
        id_, n = zaklad, 2
        while id_ in existujuce:
            id_ = f"{zaklad}_{n}"
            n += 1
        return id_

    def pridaj_skupinu(self, nazov: str = "Nová skupina") -> str:
        id_ = self._nove_id(nazov, {s["id"] for s in self.skupiny})
        self.skupiny.append({"id": id_, "nazov": nazov, "riadenie": "", "typ_riadenia": "", "kinematika": "",
                             "priecinok": "", "v_prevadzke": True})
        return id_

    def pridaj_model(self, nazov: str, skupina: str) -> str:
        if not self.skupina(skupina):
            raise ValueError("neznáma skupina")
        id_ = self._nove_id(nazov, {m["id"] for m in self.modely})
        self.modely.append({"id": id_, "nazov": nazov, "skratka": "", "skupina": skupina, "hlavicka": [], "pripony": []})
        return id_

    def pridaj_kus(self, nazov: str, model: str | None = None) -> str:
        id_ = self._nove_id(nazov, {k["id"] for k in self.kusy})
        self.kusy.append({"id": id_, "nazov": nazov, "model": model if model and self.model(model) else None})
        return id_

    def zmaz_skupinu(self, id_: str) -> None:
        if self.modely_skupiny(id_):
            raise ValueError("Skupina má modely – najprv ich presuň do inej skupiny alebo zmaž.")
        self.d["skupiny"] = [s for s in self.skupiny if s["id"] != id_]

    def zmaz_model(self, id_: str) -> int:
        """Zmaže model; jeho kusy ostanú bez modelu. Vráti počet takých kusov."""
        kusy = self.kusy_modelu(id_)
        for k in kusy:
            k["model"] = None
        self.d["modely"] = [m for m in self.modely if m["id"] != id_]
        return len(kusy)

    def zmaz_kus(self, id_: str) -> None:
        self.d["kusy"] = [k for k in self.kusy if k["id"] != id_]

    def posun_model(self, id_: str, smer: int) -> bool:
        """Poradie modelov = priorita rozpoznania; posun o jedno miesto hore (-1) / dole (+1) medzi modelmi všetkých skupín."""
        i = next((i for i, m in enumerate(self.modely) if m["id"] == id_), None)
        j = None if i is None else i + smer
        if i is None or j < 0 or j >= len(self.modely):
            return False
        self.modely[i], self.modely[j] = self.modely[j], self.modely[i]
        return True

    def nastav_texty_modelu(self, id_: str, hlavicka_text: str, triedic_text: str, pripony_text: str) -> None:
        """Polia formulára modelu -> údaje: hlavička (jednoduchý zápis / `re:`), presné texty Triediča, prípony."""
        m = self.model(id_)
        m["hlavicka"] = riadky_na_regexy(hlavicka_text)
        match = riadky(triedic_text)
        if match:
            m["triedic"] = {"match": match}
        else:
            m.pop("triedic", None)
        m["pripony"] = [(p if p.startswith(".") else "." + p).lower()
                        for p in re.split(r"[,;\s]+", pripony_text.strip()) if p]

    # ----- kontrola -----
    def chyby(self) -> list[str]:
        """Všetko, čo by pri čítaní súboru zahodilo záznam alebo je podozrivé (neznáme riadenie sa len ponecháva, ale hlási)."""
        out = []
        try:
            out += stroje.zo_slovnika(copy.deepcopy(self.d)).chyby
        except ValueError as e:
            out.append(str(e))
        for m in self.modely:
            for t in (m.get("triedic") or {}).get("match", []):
                if not re.match(r"^\(\s*stroj\s*:.*\)$", t, re.IGNORECASE):
                    out.append(f"model {m['id']}: text pre Triedič „{t}“ musí mať tvar (STROJ: …)")
        return out

    def zoznam(self) -> stroje.Zoznam:
        z = stroje.zo_slovnika(copy.deepcopy(self.d))
        z.zdroj = "subor"
        return z


# ------------------------------------------------------------------ zápis a test

def uloz(editor: Editor, cesta: str | os.PathLike, podpis_pri_nacitani: tuple[int, int] | None) -> None:
    """Zapíše zoznam (atómovo, záloha `.bak`). Ak sa súbor od načítania zmenil, vyhodí `SuborZmenenyChyba`.
    Chyby v údajoch (`Editor.chyby`) zápis zablokujú (ValueError)."""
    chyby = editor.chyby()
    if chyby:
        raise ValueError("Zoznam má chyby: " + "; ".join(chyby[:3]))
    if podpis(cesta) != podpis_pri_nacitani:
        raise SuborZmenenyChyba(str(cesta))
    stroje.uloz(editor.zoznam(), cesta)
    editor.oznac_ulozene()


def vytvor_z_predvolenych(cesta: str | os.PathLike) -> None:
    """Prvé nasadenie: vytvorí stroje.json zo vstavaných hodnôt. Existujúci súbor nikdy neprepíše."""
    if Path(cesta).exists():
        raise FileExistsError(str(cesta))
    stroje.uloz(stroje.predvolene(), cesta)


def otestuj_hlavicku(zoznam: stroje.Zoznam, text: str, vybrane: set[str] | None = None) -> dict:
    """Čo by rozpoznali aplikácie: text je buď celý riadok / hlavička programu s `STROJ:`, alebo len názov stroja.
    Vráti {"stroj": text za STROJ:, "model", "skupina" (Lupa), "triedic": [priečinky zhôd Triediča]}."""
    stroj = _hlavicka.stroj_z_hlavicky(text) or text.strip()
    riadok = text if _hlavicka.riadok_stroja(text) else f"(STROJ: {stroj})"
    m = zoznam.rozpoznaj(stroj)
    s = zoznam.skupina(m.skupina) if m else None
    nizsi = riadok.lower()
    triedic = [t["folder"] for t in zoznam.triedic_stroje(vybrane) if any(x.lower() in nizsi for x in t["match"])]
    return {"stroj": stroj, "model": m, "skupina": s, "triedic": triedic}


def otestuj_subor(zoznam: stroje.Zoznam, cesta: str | os.PathLike, vybrane: set[str] | None = None) -> dict:
    with open(cesta, "rb") as f:
        text = f.read(8192).decode("cp1250", errors="replace")
    return otestuj_hlavicku(zoznam, text, vybrane)
