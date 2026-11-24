"""Globálna klávesová skratka na vyvolanie okna NC Nástrojov (napr. Ctrl+Alt+Space).

Windows má Win+medzera (a väčšinu Win+kláves) vyhradené pre seba, preto sa dá registrovať len skratka bez Win alebo
s voľným Win+kláves; ak ju už používa iná aplikácia, registrácia zlyhá a launcher to ukáže.
RegisterHotKey musí bežať vo vlákne, ktoré má slučku správ – preto vlastné vlákno.
"""
from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes

log = logging.getLogger(__name__)

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
_MODIFIKATORY = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT,
                 "win": MOD_WIN, "windows": MOD_WIN}
_KLAVESY = {"space": 0x20, "medzera": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B}


def parsuj(text: str) -> tuple[int, int] | None:
    """„Ctrl+Alt+Space“ -> (modifikátory, kód klávesu). Prázdny text = vypnuté (None). Zlý zápis = ValueError."""
    text = (text or "").strip()
    if not text:
        return None
    casti = [c.strip().lower() for c in text.split("+") if c.strip()]
    if len(casti) < 2:
        raise ValueError("Skratka musí mať modifikátor a kláves, napr. Ctrl+Alt+Space")
    mods, kluc = 0, casti[-1]
    for c in casti[:-1]:
        if c not in _MODIFIKATORY:
            raise ValueError(f"Neznámy modifikátor „{c}“ (Ctrl, Alt, Shift, Win)")
        mods |= _MODIFIKATORY[c]
    if kluc in _KLAVESY:
        vk = _KLAVESY[kluc]
    elif len(kluc) == 1 and kluc.isalnum() and kluc.isascii():
        vk = ord(kluc.upper())
    elif kluc.startswith("f") and kluc[1:].isdigit() and 1 <= int(kluc[1:]) <= 24:
        vk = 0x70 + int(kluc[1:]) - 1
    else:
        raise ValueError(f"Neznámy kláves „{kluc}“ (písmeno, číslica, F1–F24, Space, Enter, Tab, Esc)")
    if mods == 0:
        raise ValueError("Skratka musí mať aspoň jeden modifikátor (Ctrl, Alt, Shift, Win)")
    return mods, vk


class GlobalnaSkratka:
    def __init__(self, pri_stlaceni):
        self._pri_stlaceni = pri_stlaceni
        self._vlakno: threading.Thread | None = None
        self._tid = 0

    def nastav(self, text: str) -> str:
        """Zaregistruje skratku (predchádzajúcu zruší). Vráti text chyby, inak ''."""
        self.zastav()
        try:
            spec = parsuj(text)
        except ValueError as e:
            return str(e)
        if spec is None:
            return ""
        vysledok: list[str] = []
        pripravene = threading.Event()

        def beh():
            self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
            user32 = ctypes.windll.user32
            if not user32.RegisterHotKey(None, 1, spec[0] | MOD_NOREPEAT, spec[1]):
                vysledok.append(f"Skratku {text} sa nepodarilo zaregistrovať (používa ju Windows alebo iná aplikácia).")
                pripravene.set()
                return
            pripravene.set()
            msg = wintypes.MSG()
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == WM_HOTKEY:
                        try:
                            self._pri_stlaceni()
                        except Exception:  # noqa: BLE001
                            log.exception("Obsluha klávesovej skratky zlyhala")
            finally:
                user32.UnregisterHotKey(None, 1)

        self._vlakno = threading.Thread(target=beh, daemon=True, name="klavesova-skratka")
        self._vlakno.start()
        pripravene.wait(2.0)
        if vysledok:
            self._vlakno = None
            log.warning(vysledok[0])
            return vysledok[0]
        return ""

    def zastav(self) -> None:
        if self._vlakno and self._vlakno.is_alive() and self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            self._vlakno.join(1.0)
        self._vlakno = None
        self._tid = 0
