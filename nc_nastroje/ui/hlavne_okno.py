"""Hlavné okno – zobrazenie A (dlaždice)."""
import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import sv_ttk

from .. import spustac
from ..config import Nastavenia, nacitaj_nastavenia, uloz_nastavenia
from ..katalog import App, nacitaj_katalog
from ..verzia import VERZIA
from . import napoveda
from .dlazdica import Dlazdica
from .nastavenia import OknoNastaveni
from .tema import FONT, SVETLA, Tooltip

log = logging.getLogger(__name__)
STLPCE_ZUZENE_POD = 1000  # px: pri užšom okne 2 stĺpce


class HlavneOkno(tk.Tk):
    def __init__(self):
        super().__init__()
        self.nast: Nastavenia = nacitaj_nastavenia()
        self.title("NC Nástroje")
        self.geometry("1160x740")
        self.minsize(900, 600)
        sv_ttk.set_theme("light")
        self.update_idletasks()  # téma cez <<ThemeChanged>> volá tk_setPalette – musí dobehnúť pred našimi farbami
        self.configure(bg=SVETLA["pozadie"])
        self.dlazdice: dict[str, Dlazdica] = {}
        self._stlpcov = 0

        self._postav_menu()
        self._postav_horny_riadok()
        self._pruh_chyb = tk.Label(self, text="", bg="#FDE7E9", fg="#C42B1C", font=(FONT, 10), anchor="w", padx=12, pady=6)
        self.mriezka = tk.Frame(self, bg=SVETLA["pozadie"])
        self.mriezka.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self._postav_stavovy_riadok()
        self.mriezka.bind("<Configure>", lambda e: self._rozloz())

        self.bind("<F1>", lambda e: napoveda.ukaz_napovedu(self))
        self.bind("<F5>", lambda e: self.nacitaj())  # fáza 2: obnoví aj stavy
        self.bind("<Control-f>", lambda e: (self.pole.focus_set(), self.pole.selection_range(0, "end")))
        for i in range(1, 7):
            self.bind(f"<Control-Key-{i}>", lambda e, i=i: self._spusti_podla_poradia(i - 1))
        self.nacitaj()

    # ---------- stavba UI ----------
    def _postav_menu(self):
        m = tk.Menu(self)
        subor = tk.Menu(m, tearoff=0)
        subor.add_command(label="Nastavenia…", command=self.otvor_nastavenia)
        subor.add_separator()
        subor.add_command(label="Ukončiť", command=self.destroy)
        m.add_cascade(label="Súbor", menu=subor)
        zobr = tk.Menu(m, tearoff=0)
        zobr.add_radiobutton(label="Dlaždice", value="A", variable=tk.StringVar(value="A"))
        zobr.add_radiobutton(label="Zoznam + detail (fáza 7)", state="disabled")
        zobr.add_separator()
        zobr.add_checkbutton(label="Tmavý režim (fáza 7)", state="disabled")
        m.add_cascade(label="Zobraziť", menu=zobr)
        nap = tk.Menu(m, tearoff=0)
        nap.add_command(label="Nápoveda", accelerator="F1", command=lambda: napoveda.ukaz_napovedu(self))
        nap.add_command(label="Čo je nové", command=lambda: napoveda.ukaz_co_je_nove(self))
        nap.add_command(label="O programe", command=lambda: napoveda.ukaz_o_programe(self))
        m.add_cascade(label="Nápoveda", menu=nap)
        self.config(menu=m)

    def _postav_horny_riadok(self):
        r = tk.Frame(self, bg=SVETLA["pozadie"])
        r.pack(fill="x", padx=20, pady=(16, 12))
        r.columnconfigure(0, weight=1)
        self.pole = ttk.Entry(r, font=(FONT, 12))
        self.pole.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 12))
        Tooltip(self.pole, "Číslo zákazky / výkresu (Ctrl+F) – hľadanie príde vo fáze 6")
        for i, (text, tip, styl) in enumerate([
            ("Otvoriť L:", "Otvorí priečinok zákazky na L:\\", "TButton"),
            ("Otvoriť R:", "Otvorí priečinok zákazky na R:\\", "TButton"),
            ("Hľadať v Lupe", "Otvorí Lupu s hľadaným textom", "Accent.TButton"),
        ]):
            b = ttk.Button(r, text=text, style=styl, state="disabled")
            b.grid(row=0, column=i + 1, padx=(0, 8) if i < 2 else 0, ipady=4)
            Tooltip(b, tip + " (pripravuje sa vo fáze 6)")

    def _postav_stavovy_riadok(self):
        s = tk.Frame(self, bg=SVETLA["pozadie"], highlightbackground=SVETLA["okraj"], highlightthickness=1)
        s.pack(side="bottom", fill="x")
        self._rezim = tk.Label(s, bg=SVETLA["pozadie"], fg=SVETLA["text2"], font=(FONT, 9))
        self._rezim.pack(side="left", padx=20, pady=6)
        tk.Label(s, text=f"Aplikácie z {self.nast.koren_nastrojov} · launcher v {VERZIA}",
                 bg=SVETLA["pozadie"], fg=SVETLA["text2"], font=(FONT, 9)).pack(side="right", padx=20)
        self._aktualizuj_rezim()

    def _aktualizuj_rezim(self):
        self._rezim.configure(text="Režim: " + ("Plný" if self.nast.rezim == "plny" else "Na prezeranie"))

    # ---------- katalóg a dlaždice ----------
    def nacitaj(self):
        apps, chyby = nacitaj_katalog(Path(self.nast.koren_nastrojov) / "apps.json")
        if self.nast.rezim == "prezeranie":
            apps = [a for a in apps if not a.len_plny_rezim]
        self.apps = apps
        if chyby:
            self._pruh_chyb.configure(text="  " + " | ".join(chyby))
            self._pruh_chyb.pack(fill="x", padx=20, pady=(0, 12), before=self.mriezka)
        else:
            self._pruh_chyb.pack_forget()
        for d in self.dlazdice.values():
            d.destroy()
        self.dlazdice = {a.id: Dlazdica(self.mriezka, a, self.spusti, self._menu_dlazdice) for a in apps}
        self._stlpcov = 0
        self._rozloz()

    def _rozloz(self):
        stlpcov = 2 if self.winfo_width() < STLPCE_ZUZENE_POD else 3
        if stlpcov == self._stlpcov and self.dlazdice and self.mriezka.grid_slaves():
            return
        self._stlpcov = stlpcov
        for d in self.dlazdice.values():
            d.grid_forget()
        riadkov = -(-len(self.dlazdice) // stlpcov)
        for c in range(6):
            self.mriezka.columnconfigure(c, weight=1 if c < stlpcov else 0, uniform="s" if c < stlpcov else "")
        for r in range(8):
            self.mriezka.rowconfigure(r, weight=1 if r < riadkov else 0, uniform="r" if r < riadkov else "")
        for i, d in enumerate(self.dlazdice.values()):
            d.grid(row=i // stlpcov, column=i % stlpcov, sticky="nsew", padx=6, pady=6)

    # ---------- akcie ----------
    def spusti(self, app: App, cesty: list[str] | None = None):
        ok, sprava = spustac.spusti(app, Path(self.nast.koren_nastrojov), cesty)
        self.dlazdice[app.id].ukaz_chybu("" if ok else sprava)

    def _spusti_podla_poradia(self, i: int):
        if i < len(self.apps):
            self.spusti(self.apps[i])

    def _menu_dlazdice(self, app: App, event):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label=app.tlacidlo, command=lambda: self.spusti(app))
        if app.typ != "web":
            m.add_command(label="Otvoriť priečinok aplikácie", command=lambda: self._otvor_priecinok(app))
        m.add_separator()
        m.add_command(label="Čo je nové (fáza 4)", state="disabled")
        m.add_command(label="Návrat na predchádzajúcu verziu (fáza 4)", state="disabled")
        m.add_command(label="Vytvoriť zástupcu na ploche (fáza 5)", state="disabled")
        m.tk_popup(event.x_root, event.y_root)

    def _otvor_priecinok(self, app: App):
        ok, sprava = spustac.otvor_priecinok(app, Path(self.nast.koren_nastrojov))
        if not ok:
            self.dlazdice[app.id].ukaz_chybu(sprava)

    def otvor_nastavenia(self):
        OknoNastaveni(self, self.nast, self._pri_ulozeni_nastaveni)

    def _pri_ulozeni_nastaveni(self, nast: Nastavenia):
        self.nast = nast
        uloz_nastavenia(nast)
        self._aktualizuj_rezim()
        self.nacitaj()
