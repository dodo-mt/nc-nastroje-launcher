"""Hlavné okno – zobrazenie A (dlaždice)."""
import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import sv_ttk
from tkinterdnd2 import COPY, DND_FILES, TkinterDnD

from .. import dnd, spustac, stavy
from ..config import LOCAL_DIR, Nastavenia, nacitaj_nastavenia, uloz_nastavenia
from ..katalog import App, nacitaj_katalog
from ..verzia import VERZIA
from . import napoveda
from .dlazdica import Dlazdica
from .nastavenia import OknoNastaveni
from .tema import FONT, STAVY, SVETLA, Tooltip

log = logging.getLogger(__name__)
STLPCE_ZUZENE_POD = 1000  # px: pri užšom okne 2 stĺpce


class HlavneOkno(TkinterDnD.Tk):
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
        self._stavy: dict[str, stavy.Stav] = {}   # posledné prečítané stavy (prežijú prekreslenie dlaždíc)
        self._fronta: queue.Queue = queue.Queue()  # výsledky z vlákna na pozadí
        self._obnova_bezi = False
        self._obnova_znova = False
        self._dnd_cesty: list[str] = []            # ťahané cesty (ak ich systém prezradí už pri vstupe)
        self._dnd_typy: list[str] | None = None    # None = typy zatiaľ neznáme (zistia sa pri pustení)
        self._dnd_aktivne = False
        self._pruh_id = None

        self._postav_menu()
        self._postav_horny_riadok()
        self._pruh_chyb = tk.Label(self, text="", bg="#FDE7E9", fg="#C42B1C", font=(FONT, 10), anchor="w", padx=12, pady=6)
        self._postav_pruh_dnd()
        self.mriezka = tk.Frame(self, bg=SVETLA["pozadie"])
        self.mriezka.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self._postav_stavovy_riadok()
        self.mriezka.bind("<Configure>", lambda e: self._rozloz())

        self.bind("<F1>", lambda e: napoveda.ukaz_napovedu(self))
        self.bind("<F5>", lambda e: self.nacitaj())  # znova načíta katalóg aj stavy
        self.bind("<Control-f>", lambda e: (self.pole.focus_set(), self.pole.selection_range(0, "end")))
        for i in range(1, 7):
            self.bind(f"<Control-Key-{i}>", lambda e, i=i: self._spusti_podla_poradia(i - 1))
        self._nastav_dnd()
        self.nacitaj()
        self.after(200, self._skontroluj_frontu)
        self.after(self.nast.interval_stavov_s * 1000, self._casovac_stavov)

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

    def _postav_pruh_dnd(self):
        """Horný pruh: počas ťahania „Ťaháš N súborov…“, po zlom pustení krátke upozornenie."""
        self._pruh_dnd = tk.Frame(self, bg=SVETLA["karta"], highlightbackground=SVETLA["okraj"], highlightthickness=1)
        self._pruh_sipka = tk.Label(self._pruh_dnd, text="↓", font=(FONT, 13, "bold"), bg=SVETLA["karta"], fg=SVETLA["akcent"])
        self._pruh_sipka.pack(side="left", padx=(14, 8), pady=8)
        self._pruh_text = tk.Label(self._pruh_dnd, text="", font=(FONT, 11), bg=SVETLA["karta"], fg=SVETLA["text"], anchor="w")
        self._pruh_text.pack(side="left", fill="x", expand=True)
        self._pruh_esc = tk.Label(self._pruh_dnd, text="Esc = zrušiť", font=(FONT, 10), bg=SVETLA["karta"], fg=SVETLA["text2"])
        self._pruh_esc.pack(side="right", padx=14)

    def _postav_stavovy_riadok(self):
        s = tk.Frame(self, bg=SVETLA["pozadie"], highlightbackground=SVETLA["okraj"], highlightthickness=1)
        s.pack(side="bottom", fill="x")
        self._disky = {}
        for pismeno in ("L", "R"):
            bodka = tk.Label(s, text="●", bg=SVETLA["pozadie"], fg=STAVY["nezname"][0], font=(FONT, 9))
            bodka.pack(side="left", padx=(20 if pismeno == "L" else 12, 3), pady=6)
            text = tk.Label(s, text=pismeno + ":\\ …", bg=SVETLA["pozadie"], fg=SVETLA["text2"], font=(FONT, 9))
            text.pack(side="left")
            self._disky[pismeno] = (bodka, text)
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
        for id_, d in self.dlazdice.items():
            d.nastav_stav(self._stavy.get(id_))   # posledné známe stavy hneď, čerstvé prídu z pozadia
        self.obnov_stavy()

    # ---------- stavy aplikácií (na pozadí) ----------
    def _kontext(self) -> stavy.Kontext:
        return stavy.Kontext(Path(self.nast.koren_nastrojov), Path(self.nast.koren_l),
                             Path(self.nast.koren_r), LOCAL_DIR)

    def obnov_stavy(self):
        """Spustí čítanie stavov vo vlákne; UI nečaká. Ak už beží, po dobehnutí sa spustí znova."""
        if self._obnova_bezi:
            self._obnova_znova = True
            return
        self._obnova_bezi = True
        apps, kontext = list(self.apps), self._kontext()

        def praca():
            try:
                vysledok = stavy.obnov_vsetko(apps, kontext)
            except Exception:  # noqa: BLE001
                log.exception("Obnova stavov zlyhala")
                vysledok = None
            self._fronta.put(vysledok)
        threading.Thread(target=praca, daemon=True, name="obnova-stavov").start()

    def _skontroluj_frontu(self):
        """Volá sa v hlavnom vlákne: prevezme výsledky z pozadia (bez `after` z cudzieho vlákna)."""
        try:
            while True:
                vysledok = self._fronta.get_nowait()
                self._obnova_bezi = False
                if vysledok is not None:
                    self._pouzi_stavy(vysledok)
                if self._obnova_znova:
                    self._obnova_znova = False
                    self.obnov_stavy()
        except queue.Empty:
            pass
        self.after(200, self._skontroluj_frontu)

    def _casovac_stavov(self):
        self.obnov_stavy()
        self.after(self.nast.interval_stavov_s * 1000, self._casovac_stavov)

    def _pouzi_stavy(self, v: "stavy.Vysledok"):
        self._stavy.update(v.stavy)
        for id_, d in self.dlazdice.items():
            if id_ in v.stavy:
                d.nastav_stav(v.stavy[id_])
        for pismeno, ok, koren in (("L", v.l_ok, self.nast.koren_l), ("R", v.r_ok, self.nast.koren_r)):
            bodka, text = self._disky[pismeno]
            bodka.configure(fg=STAVY["ok" if ok else "chyba"][0])
            text.configure(text=pismeno + ":\\ " + ("pripojený" if ok else "nedostupný"))

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

    # ---------- drag & drop ----------
    def _nastav_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<DropEnter>>", self._dnd_vstup)
        self.dnd_bind("<<DropPosition>>", self._dnd_pozicia)
        self.dnd_bind("<<DropLeave>>", self._dnd_odchod)
        self.dnd_bind("<<Drop>>", self._dnd_pusti)
        self.bind("<Escape>", lambda e: self._dnd_koniec())

    def _precitaj_taha(self, e) -> None:
        """Ak systém prezradí ťahané cesty už pri ťahaní, zapamätá ich a zistí typy; inak ostanú neznáme
        (dlaždice sa zvýraznia podľa `prijima` a skutočná kontrola príde pri pustení)."""
        cesty = dnd.parsuj_data(getattr(e, "data", "") or "", self.tk.splitlist)
        if cesty and cesty != self._dnd_cesty:
            self._dnd_cesty = cesty
            self._dnd_typy = dnd.typy_ciest(cesty)

    def _dnd_vstup(self, e):
        self._dnd_aktivne = True
        self._precitaj_taha(e)
        log.info("DropEnter: data=%r, typy=%r", getattr(e, "data", None), self._dnd_typy)
        self._dnd_prekresli(e.x_root, e.y_root)
        return COPY

    def _dnd_pozicia(self, e):
        if self._dnd_aktivne:
            self._precitaj_taha(e)
            self._dnd_prekresli(e.x_root, e.y_root)
        return COPY

    def _dnd_odchod(self, e):
        self._dnd_koniec()
        return COPY

    def _dlazdica_pod(self, x: int, y: int) -> Dlazdica | None:
        for d in self.dlazdice.values():
            if d.winfo_ismapped() and d.winfo_rootx() <= x < d.winfo_rootx() + d.winfo_width()                     and d.winfo_rooty() <= y < d.winfo_rooty() + d.winfo_height():
                return d
        return None

    def _dnd_prekresli(self, x: int, y: int):
        typy = self._dnd_typy
        pod = self._dlazdica_pod(x, y)
        for d in self.dlazdice.values():
            kompatibilna = bool(d.app.prijima) if typy is None else dnd.je_kompatibilna(d.app.prijima, typy)
            if not kompatibilna:
                d.nastav_dnd("siva")
            elif d is pod:
                akcia = d.app.tlacidlo.lower() + (f" · {dnd.popis_poloziek(typy)}" if typy else "")
                d.nastav_dnd("nad", [f"Pustiť sem → {akcia}", dnd.nazvy_skratene(self._dnd_cesty)])
            else:
                d.nastav_dnd("kompatibilna")
        popis = dnd.popis_poloziek(typy) if typy else "súbory"
        self._ukaz_pruh(f"Ťaháš {popis} – pusť na zvýraznenú aplikáciu.", esc=True)

    def _dnd_koniec(self):
        self._dnd_aktivne = False
        self._dnd_cesty, self._dnd_typy = [], None
        for d in self.dlazdice.values():
            d.nastav_dnd("normal")
        self._skry_pruh()

    def _dnd_pusti(self, e):
        """Pustenie: kontrola sa robí tu podľa skutočne pustených položiek (nie podľa stavu pri ťahaní)."""
        cesty = dnd.parsuj_data(getattr(e, "data", "") or "", self.tk.splitlist)
        pod = self._dlazdica_pod(e.x_root, e.y_root)
        self._dnd_koniec()
        if not cesty:
            self._upozorni("Nepodarilo sa zistiť, čo bolo pustené – nič sa nespustilo.")
        elif pod is None:
            self._upozorni("Pusť súbory na dlaždicu aplikácie – mimo dlaždice sa nič nespustí.")
        else:
            typy = dnd.typy_ciest(cesty)
            if dnd.je_kompatibilna(pod.app.prijima, typy):
                self.after(10, lambda: self.spusti(pod.app, cesty))   # drop handler sa vráti hneď
            else:
                self._upozorni(f"{pod.app.nazov} neprijíma {dnd.popis_poloziek(typy)} – nič sa nespustilo.")
        return COPY

    def _ukaz_pruh(self, text: str, esc: bool, upozornenie: bool = False):
        bg, fg = ("#FFF4CE", "#5A4400") if upozornenie else (SVETLA["karta"], SVETLA["text"])
        self._pruh_dnd.configure(bg=bg)
        for w, f in ((self._pruh_sipka, SVETLA["akcent"] if not upozornenie else fg), (self._pruh_text, fg),
                     (self._pruh_esc, SVETLA["text2"] if not upozornenie else fg)):
            w.configure(bg=bg, fg=f)
        self._pruh_sipka.configure(text="!" if upozornenie else "↓")
        self._pruh_text.configure(text=text)
        if esc:
            self._pruh_esc.pack(side="right", padx=14)
        else:
            self._pruh_esc.pack_forget()
        if not self._pruh_dnd.winfo_ismapped():
            self._pruh_dnd.pack(fill="x", padx=20, pady=(0, 12), before=self.mriezka)

    def _skry_pruh(self):
        if self._pruh_id:
            self.after_cancel(self._pruh_id)
            self._pruh_id = None
        self._pruh_dnd.pack_forget()

    def _upozorni(self, text: str):
        """Krátke upozornenie v hornom pruhu (zmizne samo)."""
        self._skry_pruh()
        self._ukaz_pruh(text, esc=False, upozornenie=True)
        self._pruh_id = self.after(5000, self._skry_pruh)

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
