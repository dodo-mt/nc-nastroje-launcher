"""Štart launchera. Spustenie: python -m nc_nastroje.main"""
import ctypes
import logging

from .config import nastav_logovanie


def main():
    nastav_logovanie()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # ostrý text na HiDPI
    except (AttributeError, OSError):
        pass
    from .ui.hlavne_okno import HlavneOkno
    try:
        HlavneOkno().mainloop()
    except Exception:
        logging.getLogger(__name__).exception("Neošetrená chyba")
        raise


if __name__ == "__main__":
    main()
