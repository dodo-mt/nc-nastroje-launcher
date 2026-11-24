"""Widget dlaždice aplikácie (zobrazenie A).

Stavy pri ťahaní súborov (`nastav_dnd`): normal / kompatibilna (prerušovaný modrý rámik) /
nad (plný modrý rámik, svetlomodré pozadie, „Pustiť sem → …“) / siva (nekompatibilná).
"""
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageOps, ImageTk

from ..config import IKONY_DIR
from ..katalog import App
from ..stavy import Stav
from .tema import FONT, STAVY, PALETA, Tooltip

MAX_CIPOV = 8
IKONA_PX = 44


class Dlazdica(tk.Frame):
    def __init__(self, rodic, app: App, pri_spusteni, pri_menu, pri_pozastaveni=None):
        t = PALETA
        super().__init__(rodic, bg=t["karta"], highlightthickness=0)
        self.app = app
        self._pri_spusteni = pri_spusteni
        self.pri_menu = pri_menu
        self._pri_pozastaveni = pri_pozastaveni
        self._chyba_id = None
        self._stav = Stav("necinny", "Pripravený")
        self._dnd = "normal"
        self._dnd_riadky: list[str] | None = None
        self._povodne: dict = {}          # pôvodné farby widgetov (pre sivý stav a „nad ňou“)
        self.columnconfigure(1, weight=1)

        # Rámik (plný / prerušovaný) kreslí canvas pod obsahom – vytvorený ako prvý, teda najnižšie
        self._ram = tk.Canvas(self, bg=t["karta"], highlightthickness=0)
        self._ram.place(x=0, y=0, relwidth=1, relheight=1)
        self._ram.bind("<Configure>", lambda e: self._kresli_ram())

        # Ikona 44 px (PNG je 80 px kvôli ostrosti) + sivá verzia pre nekompatibilný stav
        self._ikona = self._ikona_siva = None
        subor = IKONY_DIR / (app.ikona or f"{app.id}.png")
        if subor.exists():
            rgba = Image.open(subor).convert("RGBA").resize((IKONA_PX, IKONA_PX), Image.LANCZOS)
            self._ikona = ImageTk.PhotoImage(rgba)
            siva = Image.blend(ImageOps.grayscale(rgba.convert("RGB")).convert("RGB"),
                               Image.new("RGB", rgba.size, "white"), 0.55).convert("RGBA")
            siva.putalpha(rgba.getchannel("A"))
            self._ikona_siva = ImageTk.PhotoImage(siva)
        self._ikona_lbl = tk.Label(self, image=self._ikona, bg=t["karta"])
        self._ikona_lbl.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=(16, 4))

        tk.Label(self, text=app.nazov, font=(FONT, 13, "bold"), bg=t["karta"], fg=t["text"], anchor="w")\
            .grid(row=0, column=1, sticky="sw", pady=(16, 0))
        tk.Label(self, text=app.popis, font=(FONT, 10), bg=t["karta"], fg=t["text2"], anchor="w")\
            .grid(row=1, column=1, columnspan=2, sticky="nw")

        # Stavová bodka + text (mení ich `nastav_stav` podľa adaptérov)
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

        # Čipy (napr. stroje TNC Sync); riadok 4 sa naťahuje, čipy ostávajú hore
        self._cipy = []
        self._cipy_ram = tk.Frame(self, bg=t["karta"])
        self._cipy_ram.grid(row=4, column=0, columnspan=3, sticky="nw", padx=16, pady=(8, 0))
        self.rowconfigure(4, weight=1)

        # Spodný riadok: verzia vľavo, tlačidlá vpravo
        spodok = tk.Frame(self, bg=t["karta"])
        spodok.grid(row=5, column=0, columnspan=3, sticky="sew", padx=16, pady=(0, 16))
        spodok.columnconfigure(0, weight=1)
        verzia = "web" if app.typ == "web" else ("priamo z L:" if app.priamo else f"v {app.verzia}")
        self._verzia_lbl = tk.Label(spodok, text=verzia, font=(FONT, 9), bg=t["karta"], fg=t["text2"])
        self._verzia_lbl.grid(row=0, column=0, sticky="sw")
        tlacidla = tk.Frame(spodok, bg=t["karta"])
        tlacidla.grid(row=0, column=1, sticky="se")
        self._ttk_tlacidla: list[tuple[ttk.Button, bool]] = []   # (tlačidlo, je povolené)
        if app.pozastavit:
            self._pozastavit_btn = ttk.Button(tlacidla, text="Pozastaviť", command=self._pozastavit)
            self._pozastavit_btn.pack(side="left", padx=(0, 8))
            Tooltip(self._pozastavit_btn, "Požiada aplikáciu o pozastavenie (lokálna požiadavka – aplikácia ju "
                                          "musí podporovať, viď docs/zmeny_v_aplikaciach.md)")
            self._ttk_tlacidla.append((self._pozastavit_btn, True))
        styl = "TButton" if app.pozastavit else "Accent.TButton"
        self._tlacidlo = ttk.Button(tlacidla, text=app.tlacidlo, style=styl, command=self._spusti)
        self._tlacidlo.pack(side="left")
        Tooltip(self._tlacidlo, f"{app.tlacidlo}: {app.nazov}")
        self._ttk_tlacidla.append((self._tlacidlo, True))

        self._chyba = tk.Label(self, text="", font=(FONT, 9), bg=t["karta"], fg=STAVY["chyba"][0], anchor="w")
        self._chyba.grid(row=6, column=0, columnspan=3, sticky="w", padx=16)

        # Dvojklik = spustiť, pravé tlačidlo = menu (nad celou dlaždicou aj nad jej potomkami)
        self._zviaz(self)
        self.configure(cursor="hand2")
        self._prekresli()

    def _zviaz(self, w):
        if not isinstance(w, ttk.Button):
            w.bind("<Double-Button-1>", lambda e: self._spusti(), add="+")
            w.bind("<Button-3>", lambda e: self.pri_menu(self.app, e), add="+")
        for d in w.winfo_children():
            self._zviaz(d)

    def nastav_pozastaveny(self, pozastaveny: bool):
        """Text tlačidla Pozastaviť / Pokračovať (len pre aplikácie s `pozastavit`)."""
        if self.app.pozastavit:
            self._pozastavit_btn.configure(text="Pokračovať" if pozastaveny else "Pozastaviť")

    def _pozastavit(self):
        if self._pri_pozastaveni:
            self._pri_pozastaveni(self.app)

    def nastav_aktualizaciu(self, akt):
        """Stav aktualizácie aplikácie (dlaždica ho ukazuje cez verziu a stav, nič navyše nepotrebuje)."""

    def nastav_verziu(self, text: str):
        """Text vľavo dole: `v 2026.11.24-1`, `v 2026.11.19-1 → 11.24-1`, `web`."""
        self._verzia_lbl.configure(text=text)

    # ---------- stav z adaptéra ----------
    def nastav_stav(self, stav: Stav | None):
        """Zobrazí stav z adaptéra: bodka, text, 2 riadky, čipy. `None` = „Pripravený“."""
        self._stav = stav or Stav("necinny", "Pripravený")
        self._nastav_cipy(self._stav.cipy[:MAX_CIPOV])
        self._prekresli()

    def _nastav_cipy(self, cipy: list):
        if cipy == self._cipy:
            return
        self._cipy = list(cipy)
        for w in self._cipy_ram.winfo_children():
            w.destroy()
        t = PALETA
        for i, (text, stav) in enumerate(cipy):
            c = tk.Frame(self._cipy_ram, bg=t["pozadie"], highlightbackground=t["okraj"], highlightthickness=1)
            c.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 6), pady=(0, 4))
            tk.Label(c, text="●", font=(FONT, 8), bg=t["pozadie"],
                     fg=STAVY.get(stav, STAVY["nezname"])[0]).pack(side="left", padx=(6, 2))
            tk.Label(c, text=text, font=(FONT, 9), bg=t["pozadie"], fg=t["text"]).pack(side="left", padx=(0, 6), pady=2)
        self._zviaz(self._cipy_ram)

    # ---------- ťahanie súborov ----------
    def nastav_dnd(self, stav: str, riadky: list[str] | None = None):
        """stav: normal | kompatibilna | nad | siva. `riadky` = text pre stav `nad` (Pustiť sem → …)."""
        if stav == self._dnd and riadky == self._dnd_riadky:
            return
        self._dnd, self._dnd_riadky = stav, riadky
        self._prekresli()

    def _tk_widgety(self, w=None):
        w = w if w is not None else self
        for d in w.winfo_children():
            if isinstance(d, (tk.Frame, tk.Label, tk.Canvas)):
                yield d
            yield from self._tk_widgety(d)

    def _aplikuj_farby(self):
        """Prefarbí widgety podľa stavu ťahania; pôvodné farby si pamätá pri prvom stretnutí."""
        t = PALETA
        nove_pozadie = {"nad": t["pruh"], "siva": t["siva_karta"]}.get(self._dnd)
        sivy = self._dnd == "siva"
        for w in [self, *self._tk_widgety()]:
            po = self._povodne.setdefault(w, {"bg": w.cget("bg"),
                                              "fg": w.cget("fg") if isinstance(w, tk.Label) else None})
            bg = nove_pozadie if (nove_pozadie and po["bg"] == t["karta"]) else po["bg"]
            w.configure(bg=bg)
            if po["fg"] is not None:
                w.configure(fg=t["siva_text"] if sivy else po["fg"])
        self._povodne = {w: v for w, v in self._povodne.items() if w.winfo_exists()}
        self._ikona_lbl.configure(image=(self._ikona_siva if sivy and self._ikona_siva else self._ikona))
        for b, povolene in self._ttk_tlacidla:
            b.state(["!disabled"] if povolene and not sivy else ["disabled"])

    def _vykresli_stav_a_riadky(self):
        farba, predvoleny = STAVY.get(self._stav.stav, STAVY["nezname"])
        self._bodka.itemconfigure(self._bodka_id, fill=PALETA["siva_bodka"] if self._dnd == "siva" else farba)
        self._stav_text.configure(text=self._stav.text or predvoleny)
        nad = self._dnd == "nad" and self._dnd_riadky
        riadky = self._dnd_riadky if nad else self._stav.riadky
        for i, lbl in enumerate(self._riadky):
            lbl.configure(text=riadky[i] if i < len(riadky) else "")
        if nad:   # „Pustiť sem → …“ tučne modrou
            self._riadky[0].configure(font=(FONT, 10, "bold"), fg=PALETA["akcent"])
        else:
            self._riadky[0].configure(font=(FONT, 10))

    def _kresli_ram(self):
        c = self._ram
        w, h = c.winfo_width(), c.winfo_height()
        c.delete("all")
        if w < 8 or h < 8:
            return
        akcent = PALETA["akcent"]
        if self._dnd == "kompatibilna":
            c.create_rectangle(2, 2, w - 3, h - 3, outline=akcent, width=2, dash=(6, 4))
        elif self._dnd == "nad":
            c.create_rectangle(2, 2, w - 3, h - 3, outline=akcent, width=2)
        else:
            c.create_rectangle(0, 0, w - 1, h - 1,
                               outline=PALETA["siva_okraj"] if self._dnd == "siva" else PALETA["okraj"], width=1)

    def _prekresli(self):
        self._aplikuj_farby()
        self._vykresli_stav_a_riadky()
        self._kresli_ram()

    # ---------- akcie ----------
    def _spusti(self):
        self._pri_spusteni(self.app)

    def spusti_klavesou(self):
        self._spusti()

    def ukaz_chybu(self, text: str):
        self._chyba.configure(text=text)
        if self._chyba_id:
            self.after_cancel(self._chyba_id)
        self._chyba_id = self.after(8000, lambda: self._chyba.configure(text="")) if text else None
