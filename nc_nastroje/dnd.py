"""Pravidlá drag & drop: typ ťahaných položiek, „prijíma“, popis pre horný pruh.

Čistá logika bez UI (testuje sa samostatne). Typ položky je prípona malými písmenami
s bodkou (`.pof`), `priecinok` pre priečinok, alebo prázdny reťazec (súbor bez prípony).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

PRIECINOK = "priecinok"
VSETKO = "*"


def typ_cesty(cesta: str, je_priecinok: Callable[[str], bool] = os.path.isdir) -> str:
    """`priecinok`, prípona (`.pof`) alebo "" (súbor bez prípony)."""
    try:
        if je_priecinok(cesta):
            return PRIECINOK
    except OSError:
        pass
    return Path(cesta).suffix.lower()


def typy_ciest(cesty: list[str], je_priecinok: Callable[[str], bool] = os.path.isdir) -> list[str]:
    return [typ_cesty(c, je_priecinok) for c in cesty]


def prijima_typ(prijima: list[str], typ: str) -> bool:
    """Prijíma aplikácia položku daného typu? `*` = čokoľvek, prázdny zoznam = nič."""
    return VSETKO in prijima or typ in prijima


def je_kompatibilna(prijima: list[str], typy: list[str]) -> bool:
    """Dlaždica je kompatibilná, ak prijíma VŠETKY ťahané položky."""
    return bool(prijima) and bool(typy) and all(prijima_typ(prijima, t) for t in typy)


def parsuj_data(data: str, splitlist: Callable[[str], tuple]) -> list[str]:
    """Zoznam ciest z `event.data` (Tcl zoznam; cesty s medzerami sú v zátvorkách {…})."""
    if not data:
        return []
    cesty = []
    for c in splitlist(data):
        c = str(c).strip()
        if c:
            cesty.append(os.path.normpath(c))
    return cesty


def sklonuj(n: int, jeden: str, dva_styri: str, pat_viac: str) -> str:
    """Slovenské číslovky: 1 súbor, 2–4 súbory, 0 a 5+ súborov."""
    if n == 1:
        return jeden
    return dva_styri if 2 <= n <= 4 else pat_viac


def popis_poloziek(typy: list[str]) -> str:
    """„4 súbory .pof“, „1 priečinok“, „3 súbory (.h, .mpf)“, „5 položiek“."""
    n = len(typy)
    priecinky = sum(1 for t in typy if t == PRIECINOK)
    if priecinky == n:
        return f"{n} " + sklonuj(n, "priečinok", "priečinky", "priečinkov")
    if priecinky:
        return f"{n} " + sklonuj(n, "položka", "položky", "položiek")
    pripony = sorted(set(typy))
    slovo = sklonuj(n, "súbor", "súbory", "súborov")
    if len(pripony) == 1:
        return f"{n} {slovo} " + (pripony[0] or "bez prípony")
    ukaz = [p or "bez prípony" for p in pripony[:3]] + (["…"] if len(pripony) > 3 else [])
    return f"{n} {slovo} ({', '.join(ukaz)})"


def nazvy_skratene(cesty: list[str], max_nazvov: int = 2) -> str:
    """„a.pof, b.pof a 3 ďalšie“ – názvy ťahaných položiek pre dlaždicu."""
    nazvy = [os.path.basename(c.rstrip("\\/")) or c for c in cesty]
    text = ", ".join(nazvy[:max_nazvov])
    zvysok = len(nazvy) - max_nazvov
    if zvysok > 0:
        text += f" a {zvysok} " + sklonuj(zvysok, "ďalší", "ďalšie", "ďalších")
    return text
