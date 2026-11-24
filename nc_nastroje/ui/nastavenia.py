"""Okno nastavení: ľavý zoznam sekcií, vpravo obsah."""
import tkinter as tk
from dataclasses import replace
from tkinter import filedialog, ttk

from ..config import Nastavenia
from .tema import FONT, Tooltip, centruj


class OknoNastaveni(tk.Toplevel):
    def __init__(self, rodic, nast: Nastavenia, pri_ulozeni):
        super().__init__(rodic)
        self.title("Nastavenia")
        self.transient(rodic)
        self.resizable(False, False)
        self._pri_ulozeni = pri_ulozeni
        self._nast = nast
        self._v = {
            "koren_nastrojov": tk.StringVar(value=nast.koren_nastrojov),
            "koren_l": tk.StringVar(value=nast.koren_l),
            "koren_r": tk.StringVar(value=nast.koren_r),
            "rezim": tk.StringVar(value=nast.rezim),
        }
        self._interval = tk.StringVar(value=str(nast.interval_stavov_s))

        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        self._sekcie = tk.Listbox(telo, exportselection=False, height=3, width=16, font=(FONT, 10), activestyle="none")
        self._sekcie.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        for s in ("Cesty", "Režim", "Stavy"):
            self._sekcie.insert("end", s)
        self._obsah = ttk.Frame(telo)
        self._obsah.grid(row=0, column=1, sticky="nsew")
        self._strany = {"Cesty": self._cesty(self._obsah), "Režim": self._rezim(self._obsah),
                        "Stavy": self._stavy(self._obsah)}
        self._sekcie.bind("<<ListboxSelect>>", lambda e: self._ukaz())
        self._sekcie.selection_set(0)
        self._ukaz()

        tlacidla = ttk.Frame(self, padding=(16, 0, 16, 16))
        tlacidla.pack(fill="x")
        ulozit = ttk.Button(tlacidla, text="Uložiť", style="Accent.TButton", command=self._uloz)
        ulozit.pack(side="right")
        zrusit = ttk.Button(tlacidla, text="Zrušiť", command=self.destroy)
        zrusit.pack(side="right", padx=8)
        Tooltip(ulozit, "Uloží nastavenia a znovu načíta aplikácie")
        Tooltip(zrusit, "Zavrie okno bez uloženia")
        self.bind("<Escape>", lambda e: self.destroy())
        centruj(self, rodic)
        self.grab_set()

    def _ukaz(self):
        sel = self._sekcie.curselection()
        if not sel:
            return
        for s in self._strany.values():
            s.grid_forget()
        self._strany[self._sekcie.get(sel[0])].grid(row=0, column=0, sticky="nsew")

    def _cesty(self, rodic):
        f = ttk.Frame(rodic)
        for i, (kluc, text) in enumerate([("koren_nastrojov", "Koreň nástrojov"),
                                          ("koren_l", "Koreň L:"), ("koren_r", "Koreň R:")]):
            ttk.Label(f, text=text).grid(row=i, column=0, sticky="w", pady=6)
            e = ttk.Entry(f, textvariable=self._v[kluc], width=48)
            e.grid(row=i, column=1, padx=8)
            b = ttk.Button(f, text="…", width=3, command=lambda k=kluc: self._prehladaj(k))
            b.grid(row=i, column=2)
            Tooltip(b, "Vybrať priečinok")
        ttk.Label(f, text="Pri vývoji používaj falošný koreň (test_data), nie skutočné L:/R:.",
                  foreground="#555555").grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
        return f

    def _rezim(self, rodic):
        f = ttk.Frame(rodic)
        ttk.Radiobutton(f, text="Plný – všetky aplikácie", value="plny", variable=self._v["rezim"]).grid(sticky="w", pady=6)
        ttk.Radiobutton(f, text="Na prezeranie – skryje aplikácie len pre programátora",
                        value="prezeranie", variable=self._v["rezim"]).grid(sticky="w", pady=6)
        return f

    def _stavy(self, rodic):
        f = ttk.Frame(rodic)
        ttk.Label(f, text="Obnovovať stavy aplikácií každých").grid(row=0, column=0, sticky="w", pady=6)
        sp = ttk.Spinbox(f, from_=5, to=600, increment=5, width=5, textvariable=self._interval)
        sp.grid(row=0, column=1, padx=8)
        ttk.Label(f, text="s").grid(row=0, column=2, sticky="w")
        Tooltip(sp, "Ako často sa na pozadí načítajú stavy aplikácií (5 – 600 s). F5 obnoví hneď.")
        return f

    def _prehladaj(self, kluc):
        cesta = filedialog.askdirectory(parent=self, initialdir=self._v[kluc].get() or None)
        if cesta:
            self._v[kluc].set(cesta.replace("/", "\\"))

    def _uloz(self):
        nast = replace(self._nast, **{k: v.get().strip() for k, v in self._v.items()},
                       interval_stavov_s=self._interval.get().strip())
        self.destroy()
        self._pri_ulozeni(nast)
