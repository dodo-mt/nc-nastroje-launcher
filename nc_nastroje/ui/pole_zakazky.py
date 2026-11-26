"""Pole „Číslo zákazky / výkresu“ so sivým návodom (placeholder) a rozbaľovacím oknom návrhov
(vzhľad ako v Lupe) – spoločné pre zobrazenie A aj B."""
import re
import tkinter as tk
from tkinter import ttk

from .tema import FONT, PALETA

MIN_ZNAKOV = 2          # od koľkých znakov sa ukážu návrhy
ZDRZANIE_MS = 120       # krátka pauza po písaní
MIN_SIRKA = 460         # ako v Lupe: číslo, zákazník, doplnok


def _farba_rama() -> str:
    """Rámik okna návrhov: stredná farba medzi okrajom kariet a textom – v svetlom aj tmavom režime viditeľný."""
    a, b = PALETA["okraj"].lstrip("#"), PALETA["text2"].lstrip("#")
    return "#" + "".join(f"{(int(a[i:i + 2], 16) + int(b[i:i + 2], 16)) // 2:02x}" for i in (0, 2, 4))


class PoleZakazky(ttk.Entry):
    def __init__(self, rodic, pri_enter, navod: str, font=(FONT, 12), navrhy=None, pri_vybere=None):
        """navrhy(text) -> Navrhy (len z pamäte, nikdy sieť); pri_vybere(zhoda) = klik / Enter na návrhu."""
        super().__init__(rodic, font=font)
        self._navod = navod
        self._navod_aktivny = False
        self._pri_enter = pri_enter
        self._navrhy, self._pri_vybere = navrhy, pri_vybere
        self._zhody: list = []
        self._viac = 0
        self._popup: tk.Toplevel | None = None
        self._riadky: list = []
        self._i = -1
        self._casovac = None
        self._skry_casovac = None
        self._vybrane_sipkou = False
        self.bind("<FocusIn>", self._fokus_dnu, add="+")
        self.bind("<FocusOut>", self._fokus_von, add="+")
        self.bind("<Return>", self._enter)                      # Enter = otvoriť na L: (alebo vybraný návrh)
        self.bind("<KeyRelease>", self._po_pisani, add="+")
        self.bind("<Down>", lambda e: self._posun(1))
        self.bind("<Up>", lambda e: self._posun(-1))
        self.bind("<Escape>", self._esc)
        self.bind("<Destroy>", lambda e: self._skry(), add="+")
        self.bind("<Map>", lambda e: self._napoj_okno(), add="+")
        self._vloz_navod()

    # ----- návod -----
    def _vloz_navod(self):
        self.delete(0, "end")
        self.insert(0, self._navod)
        self.configure(foreground=PALETA["text2"])
        self._navod_aktivny = True

    def _fokus_dnu(self, _e=None):
        if self._navod_aktivny:
            self.delete(0, "end")
            self.configure(foreground=PALETA["text"])
            self._navod_aktivny = False

    def _fokus_von(self, _e=None):
        if not self.get().strip():
            self._vloz_navod()
        # krátke oneskorenie: klik do okna návrhov najprv zoberie poľu fokus
        self._skry_casovac = self.after(250, self._skry)

    def text(self) -> str:
        """Zadaný text (návod sa nepočíta)."""
        return "" if self._navod_aktivny else self.get().strip()

    def vymaz(self):
        """Po potvrdení hľadania: text zmizne (s fokusom prázdne pole, bez fokusu sivý návod)."""
        self._skry()
        self.delete(0, "end")
        self._navod_aktivny = False
        self.configure(foreground=PALETA["text"])
        if self.focus_get() is not self:
            self._vloz_navod()

    def fokus(self):
        self.focus_set()
        self.selection_range(0, "end")

    def prefarbi(self):
        """Po prepnutí svetlý/tmavý režim: farba textu podľa toho, či je vidieť návod."""
        self.configure(foreground=PALETA["text2"] if self._navod_aktivny else PALETA["text"])
        self._skry()

    # ----- návrhy -----
    def _napoj_okno(self):
        """Pohyb / zmena veľkosti okna zavrie návrhy (nesmú ostať visieť na starom mieste)."""
        okno = self.winfo_toplevel()
        if not getattr(okno, "_navrhy_zakazky_napojene", False):
            okno._navrhy_zakazky_napojene = True
            okno.bind("<Configure>", lambda e: self._skry() if e.widget is okno else None, add="+")

    def _po_pisani(self, e):
        if e.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R",
                        "Alt_L", "Alt_R", "Left", "Right", "Home", "End"):
            return
        if self._casovac:
            self.after_cancel(self._casovac)
        self._casovac = self.after(ZDRZANIE_MS, self._aktualizuj)

    def _aktualizuj(self):
        self._casovac = None
        text = self.text()
        if self._navrhy is None or len(text) < MIN_ZNAKOV:
            self._skry()
            return
        try:
            n = self._navrhy(text)
            self._zhody, self._viac = list(n.polozky), n.viac
        except Exception:                                       # návrhy nikdy nezhodia UI
            self._zhody, self._viac = [], 0
        if not self._zhody:
            self._skry()
            return
        self._ukaz()

    def _ukaz(self):
        """Okno ako v Lupe: biela karta, hlavičky skupín, číslo zákazky + zákazník, pätka s ovládaním."""
        self._zrus_popup()
        t = PALETA
        tien = tk.Toplevel(self)                                # tieň: tmavé polopriehľadné okno kúsok vedľa
        tien.withdraw()                                         # ukáže sa až na správnom mieste (nie v rohu obrazovky)
        tien.overrideredirect(True)
        tien.attributes("-topmost", True)
        tien.attributes("-alpha", 0.22)
        tien.configure(bg="#000000")
        self._tien = tien
        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=_farba_rama())                       # rámik výraznejší ako okraje kariet v okne
        karta = tk.Frame(popup, bg=t["karta"])
        karta.pack(fill="both", expand=True, padx=1, pady=1)
        self._popup, self._riadky, self._i = popup, [], -1
        skupina_pred = None
        for i, h in enumerate(self._zhody):
            skupina = "ZÁKAZNÍCI" if h.je_zakaznik else "ZÁKAZKY"
            if skupina != skupina_pred:
                skupina_pred = skupina
                tk.Label(karta, text=skupina, bg=t["karta"], fg=t["text2"], font=(FONT, 8, "bold"),
                         anchor="w").pack(fill="x", padx=14, pady=(8, 2))
            self._riadky.append(self._riadok(karta, i, h))
        if self._viac:
            tk.Label(karta, text=f"… a ďalších {self._viac} – spresni hľadanie", bg=t["karta"], fg=t["text2"],
                     font=(FONT, 9), anchor="w").pack(fill="x", padx=14, pady=(4, 0))
        tk.Label(karta, text="Enter = otvoriť · ↑↓ výber · Esc zavrieť", bg=t["karta"], fg=t["text2"],
                 font=(FONT, 9), anchor="w").pack(fill="x", padx=14, pady=(4, 6))
        popup.bind("<Escape>", self._esc)
        self.update_idletasks()
        sirka = max(self.winfo_width(), MIN_SIRKA)
        vyska, x, y = popup.winfo_reqheight(), self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 2
        popup.geometry(f"{sirka}x{vyska}+{x}+{y}")
        tien.geometry(f"{sirka + 4}x{vyska + 4}+{x + 1}+{y + 3}")
        tien.update_idletasks()
        popup.update_idletasks()
        tien.geometry(f"{sirka + 4}x{vyska + 4}+{x + 1}+{y + 3}")
        popup.geometry(f"{sirka}x{vyska}+{x}+{y}")           # po update_idletasks znova: Windows inak okno nechá v rohu
        tien.deiconify()
        popup.deiconify()
        tien.lift()
        popup.lift()

    def _riadok(self, rodic, i: int, h) -> list:
        """Jeden riadok návrhu; vráti jeho widgety (pozadie sa mení pri výbere)."""
        t = PALETA
        r = tk.Frame(rodic, bg=t["karta"], cursor="hand2")
        r.pack(fill="x", padx=4, pady=1)
        widgety = [r]
        nazov = h.zakaznik if h.je_zakaznik else h.zakazka
        prvy = True
        for text, tucne in self._rozdel(nazov):
            w = tk.Label(r, text=text, bg=t["karta"], fg=t["text"], anchor="w",
                         font=("Consolas", 10, "bold" if tucne else "normal"))
            w.pack(side="left", padx=(10 if prvy else 0, 0), pady=5)
            widgety.append(w)
            prvy = False
        if h.je_zakaznik:
            n = h.pocet
            sub = f"{n} {'zákazka' if n == 1 else 'zákazky' if 2 <= n <= 4 else 'zákaziek'}"
        else:
            sub = h.zakaznik + ("   (staré značenie)" if h.stara else "")
        w = tk.Label(r, text=sub, bg=t["karta"], fg=t["text2"], font=(FONT, 9), anchor="w")
        w.pack(side="left", padx=(14, 10), fill="x", expand=True)
        widgety.append(w)
        for x in widgety:
            x.bind("<Enter>", lambda e, i=i: self._oznac(i, mys=True))
            x.bind("<Button-1>", lambda e, i=i: self._klik(i))
        return widgety

    def _rozdel(self, nazov: str) -> list[tuple[str, bool]]:
        """Názov na úseky (text, tučne): zhoda s písaným číslom / textom je tučná."""
        hladane = [w for w in re.split(r"[\s\\]+", self.text()) if w]
        cislo = next((re.sub(r"^(OD|ON)", "", w, flags=re.IGNORECASE).lstrip("0") for w in hladane
                      if re.fullmatch(r"(OD|ON)?\d+", w, re.IGNORECASE)), "") or (hladane[0] if hladane else "")
        i = nazov.casefold().find(cislo.casefold()) if cislo else -1
        if i < 0:
            return [(nazov, False)]
        casti = ((nazov[:i], False), (nazov[i:i + len(cislo)], True), (nazov[i + len(cislo):], False))
        return [c for c in casti if c[0]]

    def _oznac(self, i: int, mys: bool = False):
        """Vybraný riadok má svetlomodré pozadie; myš mení výber, ale Enter ho berie len po šípkach."""
        t = PALETA
        self._i = i
        for j, widgety in enumerate(self._riadky):
            farba = t["pruh"] if j == i else t["karta"]
            for w in widgety:
                w.configure(bg=farba)
        self._vybrane_sipkou = not mys

    def _zrus_popup(self):
        for okno in (self._popup, getattr(self, "_tien", None)):
            if okno is not None:
                try:
                    okno.destroy()
                except tk.TclError:
                    pass
        self._popup, self._tien, self._riadky, self._i = None, None, [], -1

    def _skry(self):
        if self._casovac:
            try:
                self.after_cancel(self._casovac)
            except tk.TclError:
                pass
            self._casovac = None
        self._zrus_popup()
        self._vybrane_sipkou = False

    def _otvorene(self) -> bool:
        return self._popup is not None

    def _posun(self, krok: int):
        if not self._otvorene():
            if krok > 0 and self._navrhy is not None and len(self.text()) >= MIN_ZNAKOV:
                self._aktualizuj()                              # šípka dole znova otvorí zoznam
            return "break"
        n = len(self._zhody)
        i = (self._i + krok) % n if self._i >= 0 else (0 if krok > 0 else n - 1)
        self._oznac(i)
        return "break"

    def _klik(self, i: int):
        if self._skry_casovac:
            self.after_cancel(self._skry_casovac)
            self._skry_casovac = None
        self._vyber(i)
        return "break"

    def _vyber(self, i: int):
        if 0 <= i < len(self._zhody):
            zhoda = self._zhody[i]
            self._skry()
            self.focus_set()
            if self._pri_vybere:
                self._pri_vybere(zhoda)

    def _enter(self, _e):
        if self._otvorene() and self._vybrane_sipkou and self._i >= 0:
            self._vyber(self._i)
            return "break"
        self._skry()
        self._pri_enter()
        return "break"

    def _esc(self, _e):
        if self._otvorene():                                    # 1. Esc zavrie okno, 2. vymaže text (ako v Lupe)
            self._skry()
            self.focus_set()
            return "break"
        if self.text():
            self.delete(0, "end")
            return "break"
        return None
