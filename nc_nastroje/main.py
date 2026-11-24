"""Štart launchera. Spustenie: python -m nc_nastroje [argumenty]

    nc_nastroje.exe                               # otvorí okno (alebo prenesie existujúce do popredia)
    nc_nastroje.exe --tray                        # štart len do tray (po prihlásení)
    nc_nastroje.exe --aplikacia <id> [cesty…]     # spustí aplikáciu s cestami (Odoslať do)
    nc_nastroje.exe [cesty…]                      # okno s výberom kompatibilnej aplikácie
    nc_nastroje.exe --prve-spustenie              # okno s dialógom prvého spustenia (volá ho inštalátor)
    nc_nastroje.exe --odinstaluj                  # odstráni zástupcov vytvorených launcherom

Launcher je jedna inštancia: druhé spustenie pošle argumenty prvej a skončí.
"""
import argparse
import ctypes
import logging
import os
import sys

from .config import nacitaj_nastavenia, nastav_logovanie

log = logging.getLogger(__name__)


def parsuj_argumenty(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="nc_nastroje", add_help=True,
                                 description="NC Nástroje – spúšťač firemných aplikácií")
    ap.add_argument("--tray", action="store_true", help="štart len do oblasti oznámení")
    ap.add_argument("--aplikacia", metavar="ID", help="spustí aplikáciu s danými cestami (Odoslať do)")
    ap.add_argument("--prve-spustenie", action="store_true", dest="prve_spustenie",
                    help="otvorí okno s dialógom prvého spustenia (inštalátor)")
    ap.add_argument("--odinstaluj", action="store_true", help="odstráni zástupcov vytvorených NC Nástrojmi")
    ap.add_argument("cesty", nargs="*", help="súbory alebo priečinky")
    return ap.parse_args(argv)


def prikaz_z_argumentov(args: argparse.Namespace, cwd: str | None = None) -> dict:
    """Príkaz pre (prvú) inštanciu. Cesty sa menia na absolútne – druhé spustenie môže mať iný pracovný priečinok."""
    cesty = [os.path.abspath(os.path.join(cwd or os.getcwd(), c)) for c in args.cesty]
    if args.aplikacia:
        return {"akcia": "aplikacia", "id": args.aplikacia, "cesty": cesty}
    if cesty:
        return {"akcia": "cesty", "cesty": cesty}
    if args.prve_spustenie:
        return {"akcia": "zobraz", "prve_spustenie": True}
    return {"akcia": "tray" if args.tray else "zobraz"}


def _oznam(text: str, titul: str = "NC Nástroje") -> None:
    """Správa používateľovi: v zostavenom exe (bez konzoly) okno správy, inak výpis."""
    if getattr(sys, "frozen", False):
        try:
            ctypes.windll.user32.MessageBoxW(0, text, titul, 0x40)
            return
        except (AttributeError, OSError):
            pass
    print(text)


def odinstaluj() -> int:
    """Odstráni zástupcov (Po spustení, Odoslať do, plocha) vytvorených launcherom. Lokálne dáta ostanú."""
    from . import windows_integracia
    try:
        zmazane = windows_integracia.odstran_zastupcov()
    except Exception as e:  # noqa: BLE001
        log.exception("Odinštalovanie zlyhalo")
        _oznam(f"Odstránenie zástupcov zlyhalo: {e}")
        return 1
    riadky = "\n".join(f" - {z}" for z in zmazane) or " (žiadni zástupcovia sa nenašli)"
    _oznam("Zástupcovia NC Nástrojov boli odstránení:\n" + riadky +
           "\n\nAk NC Nástroje ešte bežia, ukonči ich (ikona v oblasti oznámení → Ukončiť). "
           "Lokálne dáta môžeš zmazať v priečinku %LOCALAPPDATA%\\NC_Nastroje.")
    return 0


def main(argv: list[str] | None = None):
    for prud in ("stdout", "stderr"):             # zostavený exe bez konzoly: print / argparse by inak spadli
        if getattr(sys, prud) is None:
            setattr(sys, prud, open(os.devnull, "w", encoding="utf-8"))
    nastav_logovanie()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # ostrý text na HiDPI
    except (AttributeError, OSError):
        pass
    args = parsuj_argumenty(argv)
    if args.odinstaluj:
        sys.exit(odinstaluj())
    prikaz = prikaz_z_argumentov(args)
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
    tvrdy_koniec()


def tvrdy_koniec() -> None:
    """V zostavenom exe po zatvorení okna proces vždy skončí. Inak ho môže zdržať vlákno na pozadí visiace na sieti
    (L:) a nová verzia po aktualizácii by sa nespustila (beží ešte stará inštancia). Zo zdrojového kódu sa nič nerobí."""
    if getattr(sys, "frozen", False):
        logging.shutdown()
        os._exit(0)


if __name__ == "__main__":
    main()
