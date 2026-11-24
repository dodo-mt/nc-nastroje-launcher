"""Malé okná rýchlych akcií: výber z viacerých zhôd, „zákazka sa nenašla“ a okno z tray (Otvoriť zákazku…)."""
import tkinter as tk
from tkinter import ttk

from ..zakazky import Zhoda
from .tema import FONT, PALETA, Tooltip, centruj, farby_zoznamu


class VyberZakazky(tk.Toplevel):
    """Viac zhôd -> výber (dvojklik / Enter = otvoriť)."""

    def __init__(self, rodic, zhody: list[Zhoda], pri_vybere, kde: str = "L:"):
        super().__init__(rodic)
        self.title("Vyber zákazku")
        self.transient(rodic)
        self._zhody, self._pri_vybere = zhody, pri_vybere
        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        ttk.Label(telo, text=f"Nájdených je {len(zhody)} zhôd – ktorú otvoriť na {kde}?", font=(FONT, 11)).pack(anchor="w", pady=(0, 8))
        self._zoznam = tk.Listbox(telo, height=min(max(len(zhody), 3), 12), width=70, font=(FONT, 10),
                                  activestyle="none", exportselection=False, **farby_zoznamu())
        for z in zhody:
            self._zoznam.insert("end", f"{z.zakazka}   ·   {z.zakaznik}" + ("   (staré značenie)" if z.stara else ""))
        self._zoznam.pack(fill="both", expand=True)
        self._zoznam.selection_set(0)
        self._zoznam.focus_set()
        self._zoznam.bind("<Double-Button-1>", lambda e: self._vyber())
        self._zoznam.bind("<Return>", lambda e: self._vyber())
        tl = ttk.Frame(telo)
        tl.pack(fill="x", pady=(12, 0))
        otvorit = ttk.Button(tl, text="Otvoriť", style="Accent.TButton", command=self._vyber)
        otvorit.pack(side="right")
        zrusit = ttk.Button(tl, text="Zrušiť", command=self.destroy)
        zrusit.pack(side="right", padx=8)
        Tooltip(otvorit, "Otvorí vybranú zákazku v Prieskumníkovi")
        Tooltip(zrusit, "Zavrie okno bez otvorenia")
        self.bind("<Escape>", lambda e: self.destroy())
        centruj(self, rodic)

    def _vyber(self):
        sel = self._zoznam.curselection()
        if sel:
            zhoda = self._zhody[sel[0]]
            self.destroy()
            self._pri_vybere(zhoda)


class NenaslaZakazku(tk.Toplevel):
    """Žiadna zhoda -> ponuka Hľadať v Lupe."""

    def __init__(self, rodic, text: str, pri_lupe, lupa_dostupna: bool = True):
        super().__init__(rodic)
        self.title("Zákazka sa nenašla")
        self.transient(rodic)
        self.resizable(False, False)
        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        ttk.Label(telo, text=f"Zákazka „{text}“ sa na L:\\ nenašla.", font=(FONT, 11)).pack(anchor="w")
        ttk.Label(telo, text="Môže byť pod iným číslom alebo ešte nie je založená. Skús ju nájsť v Lupe.",
                  foreground=PALETA["text2"]).pack(anchor="w", pady=(4, 12))
        tl = ttk.Frame(telo)
        tl.pack(fill="x")
        if lupa_dostupna:
            lupa = ttk.Button(tl, text="Hľadať v Lupe", style="Accent.TButton", command=lambda: self._lupa(pri_lupe))
            lupa.pack(side="right")
            Tooltip(lupa, "Otvorí Lupu s hľadaným textom")
            lupa.focus_set()
        zavriet = ttk.Button(tl, text="Zavrieť", command=self.destroy)
        zavriet.pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self.destroy())
        centruj(self, rodic)

    def _lupa(self, pri_lupe):
        self.destroy()
        pri_lupe()


class OknoZakazky(tk.Toplevel):
    """Malé okno s poľom (tray → Otvoriť zákazku…). Nie je pripojené k hlavnému oknu, takže sa ukáže aj keď je skryté."""

    def __init__(self, rodic, pri_akcii):
        super().__init__(rodic)
        self.title("Otvoriť zákazku")
        self.resizable(False, False)
        self._pri_akcii = pri_akcii
        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        ttk.Label(telo, text="Číslo zákazky / výkresu", font=(FONT, 11)).pack(anchor="w")
        self._pole = ttk.Entry(telo, font=(FONT, 12), width=34)
        self._pole.pack(fill="x", pady=(6, 12), ipady=4)
        Tooltip(self._pole, "Napr. 21930, OD21930, OD00021930 alebo OD626\\001252 (Enter = otvoriť na L:)")
        tl = ttk.Frame(telo)
        tl.pack(fill="x")
        self._tl = {}
        for text, akcia, styl, tip in (("Hľadať v Lupe", "lupa", "TButton", "Otvorí Lupu s hľadaným textom"),
                                       ("Otvoriť R:", "R", "TButton", "Otvorí rovnakú cestu na R:\\"),
                                       ("Otvoriť L:", "L", "Accent.TButton", "Otvorí priečinok zákazky na L:\\")):
            b = ttk.Button(tl, text=text, style=styl, command=lambda a=akcia: self._akcia(a))
            b.pack(side="right", padx=(8, 0))
            tp = Tooltip(b, tip)
            if akcia in ("L", "R"):
                self._tl[akcia] = (b, tp)
        self._pole.bind("<Return>", lambda e: self._akcia("L"))
        self.bind("<Escape>", lambda e: self.destroy())
        centruj(self, rodic)
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.lift()
        self.focus_force()
        self._pole.focus_set()

    def nastav_popisky(self, pop: dict):
        for a, (b, tp) in self._tl.items():
            b.config(text=pop[a][0])
            tp.text = pop[a][2]

    def _akcia(self, akcia: str):
        text = self._pole.get().strip()
        if not text:
            self._pole.focus_set()
            return
        self.destroy()
        self._pri_akcii(akcia, text)
