"""Okno „Otvoriť v aplikácii…“: súbory pustené na launcher bez konkrétnej aplikácie
(`nc_nastroje.exe cesta1 cesta2 …`) – ponúkne len aplikácie, ktoré prijímajú VŠETKY súbory."""
import tkinter as tk
from tkinter import ttk

from .. import dnd
from ..katalog import App
from .tema import FONT, SVETLA, centruj


def kompatibilne_aplikacie(apps: list[App], cesty: list[str]) -> tuple[list[App], list[str]]:
    """(aplikácie, ktoré prijímajú všetky položky; typy položiek)."""
    typy = dnd.typy_ciest(cesty)
    return [a for a in apps if dnd.je_kompatibilna(a.prijima, typy)], typy


class VyberAplikacie(tk.Toplevel):
    def __init__(self, rodic, apps: list[App], cesty: list[str], pri_vybere):
        super().__init__(rodic)
        self.title("Otvoriť v aplikácii")
        self.transient(rodic)
        self.resizable(False, False)
        kompatibilne, typy = kompatibilne_aplikacie(apps, cesty)
        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        popis = dnd.popis_poloziek(typy) if typy else "súbory"
        if kompatibilne:
            ttk.Label(telo, text=f"Vyber aplikáciu pre {popis}:", font=(FONT, 11)).pack(anchor="w", pady=(0, 10))
            for a in kompatibilne:
                ttk.Button(telo, text=a.nazov, style="Accent.TButton", width=32,
                           command=lambda a=a: self._vyber(a, pri_vybere, cesty)).pack(pady=3)
        else:
            ttk.Label(telo, text=f"Žiadna aplikácia neprijíma {popis}.", font=(FONT, 11),
                      foreground=SVETLA["text2"]).pack(anchor="w", pady=(0, 10))
        zrusit = ttk.Button(telo, text="Zrušiť", command=self.destroy)
        zrusit.pack(pady=(10, 0))
        self.bind("<Escape>", lambda e: self.destroy())
        centruj(self, rodic)
        self.focus_set()

    def _vyber(self, app: App, pri_vybere, cesty: list[str]):
        self.destroy()
        pri_vybere(app, cesty)
