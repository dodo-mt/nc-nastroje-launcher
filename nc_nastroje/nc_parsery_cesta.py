"""Zapojenie spoločného balíka `nc_parsery` (priečinok `NC parsery` vedľa tohto projektu) do sys.path.

Launcher ho potrebuje pri štarte (normalizácia čísla zákazky, cesta zákazníka na R:), preto sa na rozdiel od `spolocne.py` importuje hneď.
V exe je balík zabalený pri zostavení (nastroje/zostav.py → --paths). Ak sa pri spustení zo zdroja nenájde, program skončí s čitateľnou hláškou.
"""
import sys
from pathlib import Path

_KANDIDATI = (Path(__file__).resolve().parent.parent.parent / "NC parsery",     # vývoj: vedľa projektu
              Path(__file__).resolve().parent.parent / "NC parsery")            # v priečinku projektu


def _zapoj():
    try:
        import nc_parsery  # noqa: F401
        return
    except ImportError:
        pass
    for cesta in _KANDIDATI:
        if cesta.is_dir() and str(cesta) not in sys.path:
            sys.path.insert(0, str(cesta))
    try:
        import nc_parsery  # noqa: F401
    except ImportError:
        raise SystemExit("NC Nástroje: chýba spoločný balík nc_parsery. Nechaj priečinok 'NC parsery' vedľa priečinka s programom "
                         "(github.com/dodo-mt/nc-parsery).")


_zapoj()
