"""Dialóg prvého spustenia (po inštalácii pre kolegov): režim, spustenie po prihlásení, zástupca na ploche."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, replace
from tkinter import ttk

from ..config import Nastavenia
from .tema import FONT, PALETA, Tooltip, centruj


@dataclass
class Volby:
    rezim: str = "prezeranie"          # kolegovia v kancelárii: Na prezeranie; programátor si zvolí Plný
    po_prihlaseni: bool = True
    na_plochu: bool = True


def volby_na_nastavenia(nast: Nastavenia, v: Volby) -> Nastavenia:
    """Premietne voľby dialógu do nastavení (nič iné nemení)."""
    rezim = v.rezim if v.rezim in ("plny", "prezeranie") else nast.rezim
    return replace(nast, rezim=rezim, spustit_po_prihlaseni=bool(v.po_prihlaseni))


class PrveSpustenie(tk.Toplevel):
    """Modálny dialóg; po „Hotovo“ zavolá `pri_potvrdeni(Volby)`, po zatvorení krížikom sa použijú predvolené voľby
    (aby sa pri každom štarte nepýtal znova – nastavenia sa uložia)."""

    def __init__(self, rodic, pri_potvrdeni, predvolene: Volby | None = None):
        super().__init__(rodic)
        self.title("Vitaj v NC Nástrojoch")
        self.transient(rodic)
        self.resizable(False, False)
        self._pri_potvrdeni = pri_potvrdeni
        v = predvolene or Volby()
        self._rezim = tk.StringVar(value=v.rezim)
        self._prihlasenie = tk.BooleanVar(value=v.po_prihlaseni)
        self._plocha = tk.BooleanVar(value=v.na_plochu)

        telo = ttk.Frame(self, padding=20)
        telo.pack(fill="both", expand=True)
        ttk.Label(telo, text="Prvé spustenie", font=(FONT, 14, "bold")).pack(anchor="w")
        ttk.Label(telo, text="Zvoľ, ako sa majú NC Nástroje na tomto počítači používať. Všetko sa dá neskôr zmeniť "
                             "v Súbor → Nastavenia.", foreground=PALETA["text2"], wraplength=440,
                  justify="left").pack(anchor="w", pady=(4, 14))
        ttk.Label(telo, text="Režim", font=(FONT, 10, "bold")).pack(anchor="w")
        ttk.Radiobutton(telo, text="Na prezeranie – kancelária (bez aplikácií len pre programátora)",
                        value="prezeranie", variable=self._rezim).pack(anchor="w", pady=(4, 2))
        ttk.Radiobutton(telo, text="Plný – CNC programátor (všetky aplikácie)", value="plny",
                        variable=self._rezim).pack(anchor="w", pady=2)
        ttk.Label(telo, text="Windows", font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 0))
        c1 = ttk.Checkbutton(telo, text="Spustiť NC Nástroje po prihlásení (do oblasti oznámení)",
                             variable=self._prihlasenie)
        c1.pack(anchor="w", pady=(4, 2))
        c2 = ttk.Checkbutton(telo, text="Pridať zástupcu NC Nástroje na plochu", variable=self._plocha)
        c2.pack(anchor="w", pady=2)
        Tooltip(c1, "Vytvorí zástupcu v priečinku Po spustení (zrušiť sa dá v Nastaveniach)")
        Tooltip(c2, "Zástupca otvorí okno NC Nástrojov")
        hotovo = ttk.Button(telo, text="Hotovo", style="Accent.TButton", command=self._hotovo)
        hotovo.pack(anchor="e", pady=(18, 0))
        Tooltip(hotovo, "Uloží voľby a začne používať NC Nástroje")
        hotovo.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._hotovo)
        self.bind("<Return>", lambda e: self._hotovo())
        centruj(self, rodic)
        self.grab_set()

    def _hotovo(self):
        v = Volby(self._rezim.get(), bool(self._prihlasenie.get()), bool(self._plocha.get()))
        self.destroy()
        self._pri_potvrdeni(v)
