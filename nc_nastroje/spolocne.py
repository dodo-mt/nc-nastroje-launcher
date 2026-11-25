"""Prístup k spoločnému balíku `cnc_vykresy_spolocne` (priečinok „cnc vykresy spolocne“ vedľa tohto projektu).

Launcher ho potrebuje len na nasadzovanie spoločnej šablóny výkresu na L:\\_Nastroje\\sablony (Súbor → Nasadiť aplikáciu…
→ Šablóna výkresu); kontrola a zápis šablóny sú v balíku, aby ich používali aj aplikácie Edgecam a hyperMILL.
Import je lenivý: bez balíka launcher funguje a nasadenie šablóny ohlási zrozumiteľnú chybu.
V exe je balík zabalený pri zostavení (nastroje/zostav.py → --paths)."""
from __future__ import annotations

import sys
from pathlib import Path

PRIECINOK_BALIKA = Path(__file__).resolve().parent.parent.parent / "cnc vykresy spolocne"


def pridaj_cestu() -> None:
    """Zo zdrojového kódu pridá priečinok balíka do sys.path (v exe je balík už zabalený)."""
    cesta = str(PRIECINOK_BALIKA)
    if PRIECINOK_BALIKA.is_dir() and cesta not in sys.path:
        sys.path.insert(0, cesta)


def sablony_modul():
    """Modul `cnc_vykresy_spolocne.sablony`; ak balík nie je dostupný, vyhodí ImportError."""
    pridaj_cestu()
    from cnc_vykresy_spolocne import sablony
    return sablony
