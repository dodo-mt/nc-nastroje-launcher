"""Okno Súbor → Nasadiť aplikáciu…: nahrá hotový build na L:\\_Nastroje a zapíše novú verziu do apps.json.

Rovnaké jadro ako `nastroje/publikuj.py` (nc_nastroje/publikovanie.py). Beží na pozadí, pred zápisom na L:
sa vždy pýta. Dostupné len v plnom režime (hlavné okno ho v režime Na prezeranie nezobrazí)."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..publikovanie import PublikaciaChyba, SABLONY_ID, publikuj, publikuj_sablonu_vykresu, zoznam_aplikacii
from .tema import FONT, PALETA, Tooltip, centruj


NAZOV_SABLONY = "Šablóna výkresu – Excel + logo (spoločná pre Edgecam a hyperMILL)"


class OknoNasadenia(tk.Toplevel):
    def __init__(self, rodic, koren: Path, pozadie, pri_hotovo):
        super().__init__(rodic)
        self.title("Nasadiť aplikáciu")
        self.transient(rodic)
        self.resizable(False, False)
        self._rodic, self._koren, self._pozadie, self._pri_hotovo = rodic, Path(koren), pozadie, pri_hotovo
        self._id_podla_nazvu: dict[str, str] = {}
        self._pracuje = False
        self._sablona = False                         # práve sa nasadzuje šablóna (nie aplikácia)

        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        ttk.Label(telo, text=f"Nasadzuje sa do: {self._koren}", font=(FONT, 10), foreground=PALETA["text2"]
                  ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(telo, text="Aplikácia:").grid(row=1, column=0, sticky="w", pady=4)
        self._app = tk.StringVar()
        self._vyber = ttk.Combobox(telo, textvariable=self._app, state="readonly", width=44)
        self._vyber.grid(row=1, column=1, columnspan=2, sticky="we", pady=4, padx=(8, 0))
        self._vyber.bind("<<ComboboxSelected>>", lambda e: self._pri_zmene_vyberu())
        Tooltip(self._vyber, "Aplikácia z apps.json, ktorej novú verziu nasadzuješ")

        self._popis_buildu = ttk.Label(telo, text="Priečinok buildu:")
        self._popis_buildu.grid(row=2, column=0, sticky="w", pady=4)
        self._build = tk.StringVar()
        pole = ttk.Entry(telo, textvariable=self._build, width=40)
        pole.grid(row=2, column=1, sticky="we", pady=4, padx=(8, 4))
        Tooltip(pole, "Hotový výstup PyInstalleru – priečinok, v ktorom je exe aplikácie")
        tlac = ttk.Button(telo, text="Vybrať…", command=self._vyber_priecinok)
        tlac.grid(row=2, column=2, pady=4)
        Tooltip(tlac, "Vybrať priečinok s buildom")

        ttk.Label(telo, text="Verzia (nepovinné):").grid(row=3, column=0, sticky="w", pady=4)
        self._verzia = tk.StringVar()
        ver = ttk.Entry(telo, textvariable=self._verzia, width=20)
        ver.grid(row=3, column=1, sticky="w", pady=4, padx=(8, 0))
        Tooltip(ver, "RRRR.MM.DD-poradie. Prázdne = dnešný dátum a ďalšie poradie. "
                     "Launcher berie verziu vždy zo svojho buildu.")

        self._stav = ttk.Label(telo, text="Načítavam zoznam aplikácií…", foreground=PALETA["text2"], wraplength=460,
                               justify="left")
        self._stav.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        tl = ttk.Frame(telo)
        tl.grid(row=5, column=0, columnspan=3, sticky="e", pady=(14, 0))
        self._nasad = ttk.Button(tl, text="Nasadiť", style="Accent.TButton", command=self._nasad_klik, state="disabled")
        self._nasad.pack(side="left", padx=(0, 8))
        Tooltip(self._nasad, "Skopíruje build na L:\\_Nastroje a zverejní novú verziu")
        self._zavri = ttk.Button(tl, text="Zavrieť", command=self._zavri_klik)
        self._zavri.pack(side="left")
        telo.columnconfigure(1, weight=1)
        self.bind("<Escape>", lambda e: self._zavri_klik())
        self.protocol("WM_DELETE_WINDOW", self._zavri_klik)
        centruj(self, rodic)
        self.focus_set()

        koren = self._koren
        self._pozadie.spusti("nasadenie_zoznam", lambda posli: self._nacitaj(koren), self._po_zozname)

    @staticmethod
    def _nacitaj(koren: Path):
        try:
            return ("ok", zoznam_aplikacii(koren))
        except PublikaciaChyba as e:
            return ("chyba", str(e))

    def _po_zozname(self, vysledok):
        if not self.winfo_exists():
            return
        if not vysledok or vysledok[0] != "ok":
            self._stav.configure(text=(vysledok[1] if vysledok else "Zoznam aplikácií sa nepodarilo načítať."),
                                 foreground=PALETA["chyba_fg"])
            return
        self._id_podla_nazvu = {f"{nazov} ({id_})": id_ for id_, nazov in vysledok[1]}
        self._id_podla_nazvu[NAZOV_SABLONY] = SABLONY_ID           # spoločná šablóna výkresu (nie je v apps.json)
        self._vyber.configure(values=list(self._id_podla_nazvu))
        self._vyber.current(0)
        self._nasad.configure(state="normal")
        self._pri_zmene_vyberu()

    def _pri_zmene_vyberu(self):
        """Popisky podľa toho, či sa nasadzuje aplikácia (build) alebo šablóna výkresu (priečinok so šablónou)."""
        if self._id_podla_nazvu.get(self._app.get()) == SABLONY_ID:
            self._popis_buildu.configure(text="Priečinok so šablónou:")
            self._stav.configure(text="Priečinok musí obsahovať Template_cnc_vykres_viena_excel.xlsx (a voliteľne "
                                      "viena logo.PNG). Pred nasadením sa šablóna skontroluje.", foreground=PALETA["text2"])
        else:
            self._popis_buildu.configure(text="Priečinok buildu:")
            self._stav.configure(text="Vyber aplikáciu a priečinok s hotovým buildom.", foreground=PALETA["text2"])

    def _vyber_priecinok(self):
        zaklad = self._build.get().strip()
        c = filedialog.askdirectory(parent=self, title="Priečinok s buildom aplikácie",
                                    initialdir=zaklad if zaklad and Path(zaklad).is_dir() else None)
        if c:
            self._build.set(str(Path(c)))

    def _chyba(self, text: str):
        self._stav.configure(text=text, foreground=PALETA["chyba_fg"])

    def _nasad_klik(self):
        if self._pracuje:
            return
        id_ = self._id_podla_nazvu.get(self._app.get())
        build = self._build.get().strip().strip('"')
        verzia = self._verzia.get().strip() or None
        if not id_:
            self._chyba("Vyber aplikáciu.")
            return
        sablona = id_ == SABLONY_ID
        if not build or not Path(build).is_dir():
            self._chyba("Vyber existujúci priečinok " + ("so šablónou." if sablona else "s buildom."))
            return
        if sablona:
            text = (f"Nasadiť šablónu výkresu z priečinka\n{build}\n\nna {self._koren}\\sablony?\n\n"
                    "Edgecam aj hyperMILL si ju prevezmú pri ďalšom spustení.")
        else:
            text = (f"Nasadiť „{self._app.get()}“ z priečinka\n{build}\n\nna {self._koren}?\n\n"
                    "Zapíše sa nová verzia a ostatné počítače si ju stiahnu.")
        if not messagebox.askyesno("Nasadiť na L:", text, parent=self):
            return
        self._sablona = sablona
        self._pracuje = True
        self._nasad.configure(state="disabled")
        self._stav.configure(text="Kopírujem na L:… (môže to chvíľu trvať)", foreground=PALETA["text2"])
        koren = self._koren

        def praca(posli):
            try:
                v = (publikuj_sablonu_vykresu(koren, Path(build), verzia) if sablona
                     else publikuj(koren, id_, Path(build), verzia))
                return ("ok", v)
            except PublikaciaChyba as e:
                return ("chyba", str(e))
            except OSError as e:
                return ("chyba", f"Chyba pri zápise na disk: {e.strerror or e}")

        self._pozadie.spusti("nasadenie", praca, self._po_nasadeni)

    def _po_nasadeni(self, vysledok):
        self._pracuje = False
        if not self.winfo_exists():
            return
        self._nasad.configure(state="normal")
        nezmenene = "aktualna.txt ostal nezmenený." if self._sablona else "apps.json ostal nezmenený."
        if not vysledok:
            self._chyba("Nasadenie zlyhalo (viac v logu launchera). " + nezmenene)
        elif vysledok[0] == "chyba":
            self._chyba(vysledok[1] + " – " + nezmenene)
        else:
            v = vysledok[1]
            if self._sablona:
                varovanie = ("  POZOR: " + "; ".join(v["varovania"])) if v.get("varovania") else ""
                text = (f"Hotovo: šablóna výkresu {v['verzia']} ({v['subory']} súborov). "
                        f"Aplikácie si ju prevezmú pri ďalšom spustení.{varovanie}")
            else:
                text = f"Hotovo: {v['app_id']} {v['verzia']} ({v['subory']} súborov). apps.json aktualizovaný."
            self._stav.configure(text=text, foreground=PALETA["text"])
            self._pri_hotovo()

    def _zavri_klik(self):
        if self._pracuje:
            return                                    # kopírovanie na L: sa nesmie prerušiť zatvorením okna
        self.destroy()
