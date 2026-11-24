"""Widget dlaždice aplikácie (zobrazenie A)."""
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from ..config import IKONY_DIR
from ..katalog import App
from .tema import FONT, STAVY, SVETLA, Tooltip


class Dlazdica(tk.Frame):
    def __init__(self, rodic, app: App, pri_spusteni, pri_menu):
        t = SVETLA
        super().__init__(rodic, bg=t["karta"], highlightbackground=t["okraj"], highlightthickness=1)
        self.app = app
        self._pri_spusteni = pri_spusteni
        self.pri_menu = pri_menu
        self._chyba_id = None
        self.columnconfigure(1, weight=1)

        # Ikona 40 px vo farebnom štvorci (PNG je 80 px kvôli ostrosti)
        self._ikona = None
        subor = IKONY_DIR / (app.ikona or f"{app.id}.png")
        if subor.exists():
            self._ikona = ImageTk.PhotoImage(Image.open(subor).resize((44, 44), Image.LANCZOS))
        tk.Label(self, image=self._ikona, bg=t["karta"]).grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=(16, 4))

        tk.Label(self, text=app.nazov, font=(FONT, 13, "bold"), bg=t["karta"], fg=t["text"], anchor="w")\
            .grid(row=0, column=1, sticky="sw", pady=(16, 0))
        tk.Label(self, text=app.popis, font=(FONT, 10), bg=t["karta"], fg=t["text2"], anchor="w")\
            .grid(row=1, column=1, columnspan=2, sticky="nw")

        # Stavová bodka + text (fáza 2 ich bude meniť podľa adaptérov)
        stav = tk.Frame(self, bg=t["karta"])
        stav.grid(row=0, column=2, sticky="ne", padx=16, pady=(20, 0))
        self._bodka = tk.Canvas(stav, width=12, height=12, bg=t["karta"], highlightthickness=0)
        self._bodka.pack(side="left", padx=(0, 6))
        self._bodka_id = self._bodka.create_oval(1, 1, 11, 11, fill=STAVY["necinny"][0], outline="")
        self._stav_text = tk.Label(stav, text="Pripravený", font=(FONT, 10), bg=t["karta"], fg=t["text2"])
        self._stav_text.pack(side="left")

        self._riadky = [tk.Label(self, text="", font=(FONT, 10), bg=t["karta"], fg=t["text"], anchor="w")
                        for _ in range(2)]
        for i, lbl in enumerate(self._riadky):
            lbl.grid(row=2 + i, column=0, columnspan=3, sticky="nw", padx=16, pady=(10 if i == 0 else 0, 0))
        self.rowconfigure(4, weight=1)

        # Spodný riadok: verzia vľavo, tlačidlá vpravo
        spodok = tk.Frame(self, bg=t["karta"])
        spodok.grid(row=5, column=0, columnspan=3, sticky="sew", padx=16, pady=(0, 16))
        spodok.columnconfigure(0, weight=1)
        verzia = "web" if app.typ == "web" else f"v {app.verzia}"
        tk.Label(spodok, text=verzia, font=(FONT, 9), bg=t["karta"], fg=t["text2"]).grid(row=0, column=0, sticky="sw")
        tlacidla = tk.Frame(spodok, bg=t["karta"])
        tlacidla.grid(row=0, column=1, sticky="se")
        if app.pozastavit:
            b = ttk.Button(tlacidla, text="Pozastaviť", state="disabled")
            b.pack(side="left", padx=(0, 8))
            Tooltip(b, "Pozastaví triedenie (pripravuje sa vo fáze 5)")
        styl = "TButton" if app.pozastavit else "Accent.TButton"
        self._tlacidlo = ttk.Button(tlacidla, text=app.tlacidlo, style=styl, command=self._spusti)
        self._tlacidlo.pack(side="left")
        Tooltip(self._tlacidlo, f"{app.tlacidlo}: {app.nazov}")

        self._chyba = tk.Label(self, text="", font=(FONT, 9), bg=t["karta"], fg=STAVY["chyba"][0], anchor="w")
        self._chyba.grid(row=6, column=0, columnspan=3, sticky="w", padx=16)

        # Dvojklik = spustiť, pravé tlačidlo = menu (nad celou dlaždicou aj nad jej potomkami)
        self._zviaz(self)
        self.configure(cursor="hand2")

    def _zviaz(self, w):
        if not isinstance(w, ttk.Button):
            w.bind("<Double-Button-1>", lambda e: self._spusti())
            w.bind("<Button-3>", lambda e: self.pri_menu(self.app, e))
        for d in w.winfo_children():
            self._zviaz(d)

    def _spusti(self):
        self._pri_spusteni(self.app)

    def spusti_klavesou(self):
        self._spusti()

    def ukaz_chybu(self, text: str):
        self._chyba.configure(text=text)
        if self._chyba_id:
            self.after_cancel(self._chyba_id)
        self._chyba_id = self.after(8000, lambda: self._chyba.configure(text="")) if text else None
