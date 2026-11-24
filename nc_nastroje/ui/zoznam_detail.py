"""Zobrazenie B: zoznam aplikácií vľavo (270 px) + detail vybranej aplikácie vpravo.

`RiadokZoznamu` má rovnaké rozhranie ako `Dlazdica` (nastav_stav, nastav_verziu, nastav_pozastaveny, ukaz_chybu,
nastav_dnd, `.app`), preto hlavné okno s oboma zobrazeniami pracuje rovnako (stavy, ťahanie súborov, menu).
Čisté funkcie `rozdel_riadok` a `karty_z_stavu` (z `riadky` stavu vyrobia 3 čísla detailu) sa testujú bez UI.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from PIL import Image, ImageTk

from ..aktualizacie import AppAktualizacia
from ..config import IKONY_DIR
from ..katalog import App
from ..stavy import Stav, najhorsi
from .pole_zakazky import PoleZakazky
from .tema import FONT, PALETA, STAVY, Tooltip

SIRKA_ZOZNAMU = 270
MAX_ZAZNAMOV = 12


# ---------- čisté funkcie (bez UI) ----------
@dataclass
class Karta:
    nazov: str
    hodnota: str
    podtext: str = ""
    stav: str = "necinny"      # farba podtextu


def rozdel_riadok(riadok: str) -> tuple[str, str]:
    """`Posledná záloha: dnes 11:32` -> (`Posledná záloha`, `dnes 11:32`); bez dvojbodky -> ("", celý riadok)."""
    nazov, sep, hodnota = riadok.partition(": ")
    if sep and 0 < len(nazov) <= 28:
        return nazov.strip(), hodnota.strip()
    return "", riadok.strip()


def karty_z_stavu(stav: Stav | None, verzia_text: str, akt: AppAktualizacia | None = None) -> list[Karta]:
    """Vždy 3 karty detailu: z prvých riadkov stavu (`nazov: hodnota`), doplnené kartami Verzia a Stav;
    nevyplnené sú prázdne (`Karta("", "")`) a detail ich skryje."""
    karty: list[Karta] = []
    if stav:
        for r in stav.riadky[:3]:
            nazov, hodnota = rozdel_riadok(r)
            karty.append(Karta(nazov or "Stav", hodnota))
        if karty:                                           # 1. karta: slovný stav adaptéra farbou stavu
            karty[0].podtext = stav.text or STAVY.get(stav.stav, STAVY["nezname"])[1]
            karty[0].stav = stav.stav
        if len(karty) > 1 and stav.cipy:                    # 2. karta: čo nie je v poriadku (napr. vypnutý stroj)
            zle = [(t, s) for t, s in stav.cipy if s != "ok"]
            karty[1].podtext = ", ".join(t for t, _ in zle) if zle else "všetko v poriadku"
            karty[1].stav = najhorsi([s for _, s in zle]) if zle else "ok"
    doplnky = []
    verzia = verzia_text.removeprefix("v ") if verzia_text else "–"
    if akt and akt.stav == "caka":
        doplnky.append(Karta("Verzia", verzia, "Aktualizuje sa pri ďalšom spustení", "nova_verzia"))
    elif akt and akt.stav == "kopiruje":
        doplnky.append(Karta("Verzia", verzia, "Kopíruje sa nová verzia", "nova_verzia"))
    elif akt and akt.stav == "chyba":
        doplnky.append(Karta("Verzia", verzia, akt.sprava, "chyba"))
    else:
        doplnky.append(Karta("Verzia", verzia, "aktuálna" if verzia != "–" else "", "ok" if verzia != "–" else "necinny"))
    doplnky.append(Karta("Stav", (stav.text if stav and stav.text else STAVY.get(stav.stav if stav else "necinny")[1]),
                         "", stav.stav if stav else "necinny"))
    for d in doplnky:
        if len(karty) >= 3:
            break
        karty.append(d)
    while len(karty) < 3:
        karty.append(Karta("", ""))             # prázdna karta – detail ju nezobrazí
    return karty[:3]


# ---------- ikony ----------
_IKONY: dict[tuple[str, int], ImageTk.PhotoImage | None] = {}


def ikona_aplikacie(app: App, px: int) -> ImageTk.PhotoImage | None:
    kluc = (app.id, px)
    if kluc not in _IKONY:
        subor = IKONY_DIR / (app.ikona or f"{app.id}.png")
        try:
            _IKONY[kluc] = ImageTk.PhotoImage(Image.open(subor).convert("RGBA").resize((px, px), Image.LANCZOS))
        except (OSError, ValueError):
            _IKONY[kluc] = None
    return _IKONY[kluc]


# ---------- riadok zoznamu ----------
class RiadokZoznamu(tk.Frame):
    """Jedna aplikácia v zozname vľavo: ikona, názov, bodka (alebo odznak NOVÉ), ľavý pásik pri výbere."""

    def __init__(self, rodic, app: App, pri_vybere, pri_spusteni, pri_menu, pri_zmene):
        t = PALETA
        super().__init__(rodic, bg=t["pozadie"], highlightthickness=1, highlightbackground=t["pozadie"],
                         highlightcolor=t["pozadie"], cursor="hand2")
        self.app = app
        self._pri_vybere, self._pri_spusteni, self._pri_menu, self._pri_zmene = pri_vybere, pri_spusteni, pri_menu, pri_zmene
        self.stav: Stav | None = None
        self.verzia_text = ""
        self.pozastaveny = False
        self.chyba_text = ""
        self.akt: AppAktualizacia | None = None
        self.vybrany = False
        self._dnd = "normal"
        self._chyba_id = None
        self.columnconfigure(2, weight=1)

        self._pasik = tk.Frame(self, width=3, bg=t["pozadie"])
        self._pasik.grid(row=0, column=0, sticky="ns", pady=6)
        self._ikona = ikona_aplikacie(app, 24)
        self._ikona_lbl = tk.Label(self, image=self._ikona, bg=t["pozadie"])
        self._ikona_lbl.grid(row=0, column=1, padx=(10, 10), pady=8)
        self._nazov = tk.Label(self, text=app.nazov, font=(FONT, 11), bg=t["pozadie"], fg=t["text"], anchor="w")
        self._nazov.grid(row=0, column=2, sticky="ew")
        self._koniec = tk.Frame(self, bg=t["pozadie"])
        self._koniec.grid(row=0, column=3, padx=(6, 12))
        self._bodka = tk.Canvas(self._koniec, width=12, height=12, bg=t["pozadie"], highlightthickness=0)
        self._bodka_id = self._bodka.create_oval(1, 1, 11, 11, fill=STAVY["necinny"][0], outline="")
        self._odznak = tk.Label(self._koniec, text="NOVÉ", font=(FONT, 8, "bold"), bg=t["akcent"], fg=t["odznak_fg"],
                                padx=7, pady=1)
        self._bodka.pack()

        self._zviaz(self)
        self._prekresli()

    def _zviaz(self, w):
        w.bind("<Button-1>", lambda e: self._pri_vybere(self.app), add="+")
        w.bind("<Double-Button-1>", lambda e: self._pri_spusteni(self.app), add="+")
        w.bind("<Button-3>", lambda e: (self._pri_vybere(self.app), self._pri_menu(self.app, e)), add="+")
        for d in w.winfo_children():
            self._zviaz(d)

    # ---------- rozhranie spoločné s Dlazdica ----------
    def nastav_stav(self, stav: Stav | None):
        self.stav = stav
        self._prekresli()
        self._pri_zmene(self)

    def nastav_verziu(self, text: str):
        self.verzia_text = text
        self._pri_zmene(self)

    def nastav_pozastaveny(self, pozastaveny: bool):
        self.pozastaveny = pozastaveny
        self._pri_zmene(self)

    def nastav_aktualizaciu(self, akt: AppAktualizacia | None):
        self.akt = akt
        self._pri_zmene(self)

    def ukaz_chybu(self, text: str):
        self.chyba_text = text
        if self._chyba_id:
            self.after_cancel(self._chyba_id)
            self._chyba_id = None
        if text:
            self._chyba_id = self.after(8000, lambda: self.ukaz_chybu(""))
        self._pri_zmene(self)

    def nastav_dnd(self, stav: str, riadky: list[str] | None = None):
        """normal | kompatibilna | nad | siva – rovnaké stavy ako dlaždica pri ťahaní súborov."""
        if stav == self._dnd and (stav != "nad" or riadky == getattr(self, "_dnd_riadky", None)):
            return
        self._dnd, self._dnd_riadky = stav, riadky
        self._prekresli()

    # ---------- výber a vzhľad ----------
    def nastav_vyber(self, vybrany: bool):
        self.vybrany = vybrany
        self._prekresli()

    def _prekresli(self):
        t = PALETA
        siva = self._dnd == "siva"
        bg = {"nad": t["pruh"], "siva": t["pozadie"]}.get(self._dnd, t["vyber"] if self.vybrany else t["pozadie"])
        okraj = {"kompatibilna": t["akcent"], "nad": t["akcent"]}.get(self._dnd, bg)
        self.configure(bg=bg, highlightbackground=okraj, highlightcolor=okraj)
        for w in (self._ikona_lbl, self._nazov, self._koniec, self._bodka):
            w.configure(bg=bg)
        self._pasik.configure(bg=t["akcent"] if self.vybrany and not siva else bg)
        self._nazov.configure(fg=t["siva_text"] if siva else (t["akcent"] if self._dnd == "nad" else t["text"]),
                              font=(FONT, 11, "bold") if self.vybrany or self._dnd == "nad" else (FONT, 11),
                              text="Pustiť sem →" if self._dnd == "nad" else self.app.nazov)
        stav = self.stav.stav if self.stav else "necinny"
        if stav == "nova_verzia" and not siva:
            self._bodka.pack_forget()
            self._odznak.configure(bg=t["akcent"], fg=t["odznak_fg"])
            self._odznak.pack()
        else:
            self._odznak.pack_forget()
            self._bodka.pack()
            self._bodka.itemconfigure(self._bodka_id, fill=t["siva_bodka"] if siva else STAVY.get(stav, STAVY["nezname"])[0])


# ---------- detail ----------
class DetailAplikacie(tk.Frame):
    def __init__(self, rodic, okno):
        t = PALETA
        super().__init__(rodic, bg=t["karta"])
        self._okno = okno
        self._app: App | None = None
        self._ikona_ref = None

        hlavicka = tk.Frame(self, bg=t["karta"])
        hlavicka.pack(fill="x", padx=28, pady=(28, 0))
        hlavicka.columnconfigure(1, weight=1)
        self._ikona = tk.Label(hlavicka, bg=t["karta"])
        self._ikona.grid(row=0, column=0, rowspan=2, padx=(0, 16))
        self._nazov = tk.Label(hlavicka, font=(FONT, 20, "bold"), bg=t["karta"], fg=t["text"], anchor="w")
        self._nazov.grid(row=0, column=1, sticky="sw")
        self._popis = tk.Label(hlavicka, font=(FONT, 10), bg=t["karta"], fg=t["text2"], anchor="w", justify="left")
        self._popis.grid(row=1, column=1, sticky="nw")
        tl = tk.Frame(hlavicka, bg=t["karta"])
        tl.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
        self._pozastavit = ttk.Button(tl, text="Pozastaviť", command=lambda: self._okno._prepni_pozastavenie(self._app))
        Tooltip(self._pozastavit, "Požiada aplikáciu o pozastavenie (lokálna požiadavka)")
        self._spustit = ttk.Button(tl, style="Accent.TButton", command=lambda: self._okno.spusti(self._app))
        self._spustit.pack(side="right", ipady=4)

        self._karty_ram = tk.Frame(self, bg=t["karta"])
        self._karty_ram.pack(fill="x", padx=28, pady=(22, 0))
        for i in range(3):
            self._karty_ram.columnconfigure(i, weight=1, uniform="karta")
        self._karty: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Label]] = []
        for i in range(3):
            k = tk.Frame(self._karty_ram, bg=t["karta2"])
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))
            n = tk.Label(k, font=(FONT, 10), bg=t["karta2"], fg=t["text2"], anchor="w")
            h = tk.Label(k, font=(FONT, 18, "bold"), bg=t["karta2"], fg=t["text"], anchor="w")
            p = tk.Label(k, font=(FONT, 10), bg=t["karta2"], fg=t["text2"], anchor="w")
            n.pack(fill="x", padx=16, pady=(14, 0))
            h.pack(fill="x", padx=16)
            p.pack(fill="x", padx=16, pady=(0, 14))
            self._karty.append((k, n, h, p))

        self._chyba = tk.Label(self, font=(FONT, 10), bg=t["karta"], fg=t["chyba_fg"], anchor="w", justify="left")
        self._zaznamy_nadpis = tk.Label(self, text="Posledné záznamy", font=(FONT, 11, "bold"), bg=t["karta"],
                                        fg=t["text"], anchor="w")
        self._zaznamy_ram = tk.Frame(self, bg=t["karta"], highlightthickness=1, highlightbackground=t["okraj"])
        self._zaznamy: list[tk.Label] = []

        self._dolne = tk.Frame(self, bg=t["karta"])
        self._dolne.pack(side="bottom", fill="x", padx=28, pady=(0, 24))
        self._tl: dict[str, ttk.Button] = {}
        for kluc, text, tip, cmd in (
                ("priecinok", "Priečinok", "Otvorí priečinok aplikácie v Prieskumníkovi", lambda: self._okno._otvor_priecinok(self._app)),
                ("log", "Log", "Otvorí log aplikácie (ak ho aplikácia uvádza v apps.json)", lambda: self._okno.otvor_log(self._app)),
                ("co_je_nove", "Čo je nové", "Zobrazí poznámky k verziám aplikácie", lambda: self._okno.ukaz_co_je_nove_app(self._app)),
                ("napoveda", "Nápoveda", "Nápoveda launchera (F1)", lambda: self._okno.ukaz_napovedu())):
            b = ttk.Button(self._dolne, text=text, command=cmd)
            b.pack(side="left", padx=(0, 10), ipady=3)
            Tooltip(b, tip)
            self._tl[kluc] = b

    def ukaz(self, riadok: RiadokZoznamu | None):
        """Zobrazí detail vybraného riadka (stav, verzia, chyba, pozastavenie)."""
        t = PALETA
        if riadok is None:
            self._app = None
            self._nazov.configure(text="")
            self._popis.configure(text="Žiadna aplikácia")
            return
        app, stav = riadok.app, riadok.stav
        self._app = app
        self._ikona_ref = ikona_aplikacie(app, 56)
        self._ikona.configure(image=self._ikona_ref)
        self._nazov.configure(text=app.nazov)
        self._popis.configure(text=" · ".join(x for x in (app.popis, riadok.verzia_text) if x))
        self._spustit.configure(text=app.tlacidlo)
        if app.pozastavit:
            self._pozastavit.configure(text="Pokračovať" if riadok.pozastaveny else "Pozastaviť")
            self._pozastavit.pack(side="right", padx=(0, 8), ipady=4)
        else:
            self._pozastavit.pack_forget()
        for (k, n, h, p), karta in zip(self._karty, karty_z_stavu(stav, riadok.verzia_text, riadok.akt)):
            if not karta.nazov and not karta.hodnota:
                k.grid_remove()
                continue
            k.grid()
            n.configure(text=karta.nazov)
            h.configure(text=karta.hodnota)
            p.configure(text=karta.podtext, fg=STAVY.get(karta.stav, STAVY["nezname"])[0] if karta.podtext else t["text2"])
        if riadok.chyba_text:
            self._chyba.configure(text=riadok.chyba_text)
            self._chyba.pack(fill="x", padx=28, pady=(12, 0), after=self._karty_ram)
        else:
            self._chyba.pack_forget()
        self._ukaz_zaznamy(stav.log if stav else [])
        self._tl["priecinok"].state(["!disabled"] if app.typ != "web" else ["disabled"])
        self._tl["log"].state(["!disabled"] if app.log else ["disabled"])

    def _ukaz_zaznamy(self, riadky: list[str]):
        """Posledné záznamy – len ak ich adaptér vrátil (`log`)."""
        for lbl in self._zaznamy:
            lbl.destroy()
        self._zaznamy = []
        if not riadky:
            self._zaznamy_nadpis.pack_forget()
            self._zaznamy_ram.pack_forget()
            return
        t = PALETA
        self._zaznamy_nadpis.pack(fill="x", padx=28, pady=(24, 6), after=self._karty_ram if not self._chyba.winfo_ismapped() else self._chyba)
        self._zaznamy_ram.pack(fill="x", padx=28, after=self._zaznamy_nadpis)
        for r in riadky[:MAX_ZAZNAMOV]:
            lbl = tk.Label(self._zaznamy_ram, text=r, font=("Consolas", 10), bg=t["karta"], fg=t["text"], anchor="w",
                           justify="left")
            lbl.pack(fill="x", padx=14, pady=3)
            self._zaznamy.append(lbl)


# ---------- celé zobrazenie B ----------
class ZoznamDetail(tk.Frame):
    def __init__(self, rodic, okno):
        t = PALETA
        super().__init__(rodic, bg=t["pozadie"])
        self._okno = okno
        self.polozky: dict[str, RiadokZoznamu] = {}
        self.vybrana: str | None = None

        lavy = tk.Frame(self, bg=t["pozadie"], width=SIRKA_ZOZNAMU)
        lavy.pack(side="left", fill="y")
        lavy.pack_propagate(False)
        self.pole = PoleZakazky(lavy, lambda: okno.rychla_akcia("L"), "Číslo zákazky / výkresu…", font=(FONT, 11))
        self.pole.pack(fill="x", padx=16, pady=(16, 6), ipady=3)
        self.pole_tip = Tooltip(self.pole, "")
        akcie = tk.Frame(lavy, bg=t["pozadie"])
        akcie.pack(fill="x", padx=16)
        self._tl = {}
        for i, (text, a, tip) in enumerate((("Otvoriť L:", "L", "Nájde priečinok zákazky a otvorí ho na L:\\ (Enter)"),
                                            ("R:", "R", "Otvorí rovnakú cestu na R:\\"),
                                            ("Lupa", "lupa", "Otvorí Lupu s hľadaným textom"))):
            b = ttk.Button(akcie, text=text, command=lambda a=a: okno.rychla_akcia(a))
            b.pack(side="left", fill="x", expand=(i == 0), padx=(0, 6 if i < 2 else 0))
            tp = Tooltip(b, tip)
            if a in ("L", "R"):
                self._tl[a] = (b, tp)
        tk.Label(lavy, text="APLIKÁCIE", font=(FONT, 9, "bold"), bg=t["pozadie"], fg=t["text2"], anchor="w").pack(
            fill="x", padx=20, pady=(22, 6))
        self._zoznam = tk.Frame(lavy, bg=t["pozadie"])
        self._zoznam.pack(fill="x", padx=10)

        self.detail = DetailAplikacie(self, okno)
        self.detail.pack(side="left", fill="both", expand=True, padx=(0, 0))

    def nastav_popisky(self, pop: dict):
        for a, (b, tp) in self._tl.items():
            b.config(text=pop[a][1])
            tp.text = pop[a][2]

    def postav(self, apps: list[App], pri_spusteni, pri_menu) -> dict[str, RiadokZoznamu]:
        """(Znova) vytvorí riadky zoznamu; výber sa zachová, inak prvá aplikácia."""
        for r in self.polozky.values():
            r.destroy()
        self.polozky = {a.id: RiadokZoznamu(self._zoznam, a, self.vyber_app, pri_spusteni, pri_menu, self._riadok_zmenen)
                        for a in apps}
        for r in self.polozky.values():
            r.pack(fill="x", pady=1)
        self.vybrana = self.vybrana if self.vybrana in self.polozky else (next(iter(self.polozky), None))
        self._oznac()
        return self.polozky

    def vyber_app(self, app: App):
        self.vybrana = app.id
        self._oznac()

    def _oznac(self):
        for id_, r in self.polozky.items():
            r.nastav_vyber(id_ == self.vybrana)
        self.detail.ukaz(self.polozky.get(self.vybrana) if self.vybrana else None)

    def _riadok_zmenen(self, riadok: RiadokZoznamu):
        """Zmenil sa stav / verzia / chyba riadka – ak je vybraný, obnoví sa detail."""
        if riadok.app.id == self.vybrana:
            self.detail.ukaz(riadok)

    def prefarbi(self):
        self.pole.prefarbi()
