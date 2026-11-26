"""Okno Súbor → Prehľad počítačov…: kto má ktorú verziu aplikácií a kde beží stará (len plný režim).

Údaje sú súbory `_stav\\_pocitace\\<POCITAC>.json` na L:, ktoré zapisuje každý launcher (pocitace.py). Čítanie beží na
pozadí; okno len ukazuje farebné bodky: zelená = aktuálna, oranžová = beží stará (treba zavrieť a otvoriť),
modrá = čaká novšia z L:, sivá = nie je nainštalovaná, červená = počítač sa neozval."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from .. import pocitace, stavy
from .tema import FONT, PALETA, STAVY, Tooltip, centruj


class PocitaceOkno(tk.Toplevel):
    def __init__(self, rodic, koren: Path, pozadie, zdroj_katalogu):
        """zdroj_katalogu() -> (apps, verzia launchera v katalógu); volá sa pri každom (pre)kreslení."""
        super().__init__(rodic)
        self.title("Prehľad počítačov")
        self.transient(rodic)
        self.minsize(640, 260)
        self._rodic, self._koren, self._pozadie, self._zdroj = rodic, Path(koren), pozadie, zdroj_katalogu
        self._zaznamy: list[dict] | None = None

        horny = ttk.Frame(self, padding=(16, 14, 16, 6))
        horny.pack(fill="x")
        ttk.Label(horny, text="Prehľad počítačov", font=(FONT, 14, "bold")).pack(side="left")
        zav = ttk.Button(horny, text="Zavrieť", command=self.destroy)
        zav.pack(side="right")
        Tooltip(zav, "Zavrie okno (Esc)")
        obn = ttk.Button(horny, text="Obnoviť", command=self.nacitaj)
        obn.pack(side="right", padx=(0, 8))
        Tooltip(obn, "Znova prečíta záznamy počítačov z L:")

        self._legenda = tk.Frame(self, bg=PALETA["pozadie"])
        self._legenda.pack(fill="x", padx=16)
        for stav, text in (("ok", "aktuálna"), ("upozornenie", "beží stará – treba zavrieť a otvoriť"),
                           ("nova_verzia", "čaká novšia z L:"), ("necinny", "nie je nainštalovaná"),
                           ("chyba", "počítač sa neozval")):
            tk.Label(self._legenda, text="● ", fg=STAVY[stav][0], bg=PALETA["pozadie"], font=(FONT, 10)).pack(side="left")
            tk.Label(self._legenda, text=text + "    ", fg=PALETA["text2"], bg=PALETA["pozadie"],
                     font=(FONT, 9)).pack(side="left")

        self._telo = tk.Frame(self, bg=PALETA["karta"], highlightthickness=1, highlightbackground=PALETA["okraj"])
        self._telo.pack(fill="both", expand=True, padx=16, pady=10)
        self._pata = ttk.Label(self, text="Načítavam…", foreground=PALETA["text2"], padding=(16, 0, 16, 12))
        self._pata.pack(fill="x")
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry("1100x420")
        centruj(self, rodic, (1100, 420))
        self.nacitaj()

    # ----- načítanie -----
    def nacitaj(self):
        self._pata.configure(text="Načítavam…")
        koren = self._koren
        self._pozadie.spusti("pocitace_okno", lambda posli: pocitace.nacitaj(koren), self._po_nacitani)

    def _po_nacitani(self, zaznamy: list[dict]):
        if not self.winfo_exists():
            return
        self._zaznamy = zaznamy
        self._prekresli()

    # ----- kreslenie -----
    def _prekresli(self):
        for w in self._telo.winfo_children():
            w.destroy()
        apps, kat_launcher = self._zdroj()
        zaznamy = self._zaznamy or []
        if not zaznamy:
            tk.Label(self._telo, text="Zatiaľ sa neozval žiadny počítač.\nZáznamy sa zapisujú pri štarte a raz za 10 minút.",
                     bg=PALETA["karta"], fg=PALETA["text2"], font=(FONT, 10), justify="left", pady=24, padx=16).pack()
            self._pata.configure(text=f"Zdroj: {self._koren / pocitace.PODADRESAR}")
            return
        spravovane = [a for a in apps if a.typ != "web" and not a.priamo]
        stlpce = ["Počítač", "Naposledy", "Režim", "Launcher"] + [a.nazov for a in spravovane]
        teraz = datetime.now()
        for j, nazov in enumerate(stlpce):
            tk.Label(self._telo, text=nazov, bg=PALETA["karta"], fg=PALETA["text2"], font=(FONT, 9, "bold"),
                     anchor="w", padx=10, pady=6).grid(row=0, column=j, sticky="we")
        for i, z in enumerate(zaznamy, 1):
            neozval = pocitace.neozval_sa(z, teraz)
            pozadie = PALETA["karta"] if i % 2 else PALETA["pozadie"]
            by_id = {e.get("id"): e for e in z["aplikacie"]}
            stav_l, text_l = pocitace.stav_launchera(z.get("launcher", ""), kat_launcher)
            bunky = [
                (z["pocitac"] + (f"  ({z['uzivatel']})" if z.get("uzivatel") else ""), "chyba" if neozval else None),
                (stavy.formatuj_cas(z["_cas"], teraz) + (f"  · {(teraz - z['_cas']).days} dní" if neozval else ""),
                 "chyba" if neozval else None),
                ("Plný" if z.get("rezim") == "plny" else "Na prezeranie", None),
                (text_l, stav_l),
            ]
            for a in spravovane:
                stav, text = pocitace.stav_aplikacie(by_id.get(a.id), a.verzia)
                bunky.append((text, stav))
            for j, (text, stav) in enumerate(bunky):
                farba = STAVY[stav][0] if stav else PALETA["text"]
                if stav == "necinny":
                    farba = PALETA["text2"]
                t = ("● " + text) if stav and j >= 3 else text
                tk.Label(self._telo, text=t, bg=pozadie, fg=farba, font=(FONT, 10, "bold" if j == 0 else "normal"),
                         anchor="w", padx=10, pady=5).grid(row=i, column=j, sticky="we")
        for j in range(len(stlpce)):
            self._telo.columnconfigure(j, weight=1 if j >= 4 else 0)
        starych = pocitace.pocet_starych(zaznamy, {a.id: a.verzia for a in spravovane}, teraz)
        self._pata.configure(text=f"{len(zaznamy)} počítačov · "
                                  + (f"{starych} má otvorenú starú verziu aplikácie · " if starych else "")
                                  + f"zdroj: {self._koren / pocitace.PODADRESAR}")
