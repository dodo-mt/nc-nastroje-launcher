"""Pole „Číslo zákazky / výkresu“ so sivým návodom (placeholder) – spoločné pre zobrazenie A aj B."""
from tkinter import ttk

from .tema import FONT, PALETA


class PoleZakazky(ttk.Entry):
    def __init__(self, rodic, pri_enter, navod: str, font=(FONT, 12)):
        super().__init__(rodic, font=font)
        self._navod = navod
        self._navod_aktivny = False
        self.bind("<FocusIn>", self._fokus_dnu, add="+")
        self.bind("<FocusOut>", self._fokus_von, add="+")
        self.bind("<Return>", lambda e: pri_enter())          # Enter = otvoriť na L:
        self._vloz_navod()

    def _vloz_navod(self):
        self.delete(0, "end")
        self.insert(0, self._navod)
        self.configure(foreground=PALETA["text2"])
        self._navod_aktivny = True

    def _fokus_dnu(self, _e=None):
        if self._navod_aktivny:
            self.delete(0, "end")
            self.configure(foreground=PALETA["text"])
            self._navod_aktivny = False

    def _fokus_von(self, _e=None):
        if not self.get().strip():
            self._vloz_navod()

    def text(self) -> str:
        """Zadaný text (návod sa nepočíta)."""
        return "" if self._navod_aktivny else self.get().strip()

    def fokus(self):
        self.focus_set()
        self.selection_range(0, "end")

    def prefarbi(self):
        """Po prepnutí svetlý/tmavý režim: farba textu podľa toho, či je vidieť návod."""
        self.configure(foreground=PALETA["text2"] if self._navod_aktivny else PALETA["text"])
