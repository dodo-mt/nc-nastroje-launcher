"""Štart launchera. Spustenie: python -m nc_nastroje.main [argumenty]

    nc_nastroje.exe                               # otvorí okno (alebo prenesie existujúce do popredia)
    nc_nastroje.exe --tray                        # štart len do tray (po prihlásení)
    nc_nastroje.exe --aplikacia <id> [cesty…]     # spustí aplikáciu s cestami (Odoslať do)
    nc_nastroje.exe [cesty…]                      # okno s výberom kompatibilnej aplikácie

Launcher je jedna inštancia: druhé spustenie pošle argumenty prvej a skončí.
"""
import argparse
import ctypes
import logging
import os

from .config import nacitaj_nastavenia, nastav_logovanie

log = logging.getLogger(__name__)


def parsuj_argumenty(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="nc_nastroje", add_help=True,
                                 description="NC Nástroje – spúšťač firemných aplikácií")
    ap.add_argument("--tray", action="store_true", help="štart len do oblasti oznámení")
    ap.add_argument("--aplikacia", metavar="ID", help="spustí aplikáciu s danými cestami (Odoslať do)")
    ap.add_argument("cesty", nargs="*", help="súbory alebo priečinky")
    return ap.parse_args(argv)


def prikaz_z_argumentov(args: argparse.Namespace, cwd: str | None = None) -> dict:
    """Príkaz pre (prvú) inštanciu. Cesty sa menia na absolútne – druhé spustenie môže mať iný pracovný priečinok."""
    cesty = [os.path.abspath(os.path.join(cwd or os.getcwd(), c)) for c in args.cesty]
    if args.aplikacia:
        return {"akcia": "aplikacia", "id": args.aplikacia, "cesty": cesty}
    if cesty:
        return {"akcia": "cesty", "cesty": cesty}
    return {"akcia": "tray" if args.tray else "zobraz"}


def main(argv: list[str] | None = None):
    nastav_logovanie()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # ostrý text na HiDPI
    except (AttributeError, OSError):
        pass
    prikaz = prikaz_z_argumentov(parsuj_argumenty(argv))
    from .instancia import Instancia
    instancia = Instancia(nacitaj_nastavenia().port_instancie)
    if not instancia.spusti_alebo_posli(prikaz):
        log.info("Launcher už beží – príkaz %s odovzdaný, končím", prikaz.get("akcia"))
        return
    from .ui.hlavne_okno import HlavneOkno
    try:
        HlavneOkno(prikaz, instancia).mainloop()
    except Exception:
        log.exception("Neošetrená chyba")
        raise
    finally:
        instancia.zatvor()


if __name__ == "__main__":
    main()
