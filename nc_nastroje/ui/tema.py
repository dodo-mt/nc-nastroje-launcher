"""Farby (svetlý aj tmavý režim), fonty, pomocné funkcie pre UI.

`PALETA` je AKTUÁLNA paleta (jeden objekt, obsah sa pri prepnutí režimu vymení) – widgety si z nej čítajú farby pri
vytvorení a už vytvorené sa prefarbia cez `prefarbi_strom`. `SVETLA` a `TMAVA` sú nemenné predlohy.
Kontrast textu min. 4.5:1 (testuje sa v tests/test_tema.py); `siva_*` sú zámerne nízky kontrast (nekompatibilná dlaždica).
"""
import tkinter as tk

import sv_ttk

FONT = "Segoe UI"

SVETLA = dict(
    pozadie="#F3F3F3", karta="#FFFFFF", karta2="#F5F6F8", okraj="#E0E3E7", vyber="#E4E7EC",
    text="#1B1B1B", text2="#555555", akcent="#005FB8", odznak_fg="#FDFDFD",
    pruh="#DDEBF9", okraj_pruhu="#B9D3EE",
    chyba_bg="#FDE7E9", chyba_fg="#C42B1C", var_bg="#FFF4CE", var_fg="#5A4400",
    siva_karta="#F7F7F7", siva_text="#A9AEB3", siva_bodka="#C8CCD0", siva_okraj="#ECECEC",
    tip_bg="#FFFFE1", tip_fg="#1B1B1B",
)
TMAVA = dict(
    pozadie="#1E1E1E", karta="#2A2A2A", karta2="#323232", okraj="#444444", vyber="#3A3A3A",
    text="#F2F2F2", text2="#BDBDBD", akcent="#6CB6FF", odznak_fg="#0B0B0B",
    pruh="#1C3550", okraj_pruhu="#2F5C8F",
    chyba_bg="#4B2323", chyba_fg="#FF8279", var_bg="#4A3A06", var_fg="#FFE29A",
    siva_karta="#252525", siva_text="#707070", siva_bodka="#585858", siva_okraj="#333333",
    tip_bg="#3C3C3C", tip_fg="#F2F2F2",
)

_STAVY_SVETLE = {
    "ok": ("#0F7B0F", "OK"),
    "upozornenie": ("#9D5D00", "Upozornenie"),
    "chyba": ("#C42B1C", "Chyba"),
    "nova_verzia": ("#005FB8", "Nová verzia"),
    "necinny": ("#9AA0A6", "Pripravený"),
    "nezname": ("#9AA0A6", "Neznámy"),
}
_STAVY_TMAVE = {
    "ok": ("#4CC264", "OK"),
    "upozornenie": ("#E8A33D", "Upozornenie"),
    "chyba": ("#FF8279", "Chyba"),
    "nova_verzia": ("#6CB6FF", "Nová verzia"),
    "necinny": ("#8B949E", "Pripravený"),
    "nezname": ("#8B949E", "Neznámy"),
}

PALETA: dict[str, str] = dict(SVETLA)       # aktuálna paleta
STAVY: dict[str, tuple[str, str]] = dict(_STAVY_SVETLE)   # aktuálne farby stavov: stav -> (farba, text)
_stav_tmavy = False


def je_tmava() -> bool:
    return _stav_tmavy


def nastav_temu(tmava: bool) -> dict[str, str]:
    """Prepne aktuálnu paletu (na mieste). Vráti mapu starých farieb na nové pre `prefarbi_strom`."""
    global _stav_tmavy
    stara_paleta, stare_stavy = dict(PALETA), dict(STAVY)
    PALETA.clear()
    PALETA.update(TMAVA if tmava else SVETLA)
    STAVY.clear()
    STAVY.update(_STAVY_TMAVE if tmava else _STAVY_SVETLE)
    _stav_tmavy = tmava
    mapa = {}
    for kluc, stara in stara_paleta.items():
        mapa.setdefault(stara.lower(), PALETA[kluc])
    for kluc, (stara, _t) in stare_stavy.items():
        mapa.setdefault(stara.lower(), STAVY[kluc][0])
    return mapa


_FAREBNE_VOLBY = ("bg", "fg", "background", "foreground", "highlightbackground", "highlightcolor",
                  "activebackground", "activeforeground", "disabledforeground", "selectbackground",
                  "selectforeground", "insertbackground", "troughcolor")


def prefarbi_strom(korien: tk.Misc, mapa: dict[str, str]) -> None:
    """Prefarbí už vytvorené tk widgety (Frame, Label, Canvas, Listbox, Text…) podľa mapy stará→nová farba.
    ttk widgety sa nedotýkajú (tie prepína sv_ttk). Farby mimo mapy (napr. farby aplikácií) ostanú."""
    for w in korien.winfo_children():
        zmeny = {}
        for volba in _FAREBNE_VOLBY:
            try:
                hodnota = str(w.cget(volba)).lower()
            except tk.TclError:
                continue
            if hodnota in mapa:
                zmeny[volba] = mapa[hodnota]
        if zmeny:
            try:
                w.configure(**zmeny)
            except tk.TclError:
                pass
        # položky plátna (bodky) majú vlastné farby výplne
        if isinstance(w, tk.Canvas):
            for polozka in w.find_all():
                try:
                    vypln = str(w.itemcget(polozka, "fill")).lower()
                    if vypln in mapa:
                        w.itemconfigure(polozka, fill=mapa[vypln])
                except tk.TclError:
                    pass
        prefarbi_strom(w, mapa)


def prepni_ttk_temu(root: tk.Tk, tmava: bool) -> None:
    """`sv_ttk.set_theme` BEZ `tk_setPalette`. Ten by za behu prefarbil aj naše tk widgety (na predvolenú farbu témy)
    a prebil by naše farby – preto sa na čas prepnutia nahradí prázdnou procedúrou (vrátane odloženého
    <<ThemeChanged>>, ktorý dobehne v `update`). Farby tk widgetov riadi `PALETA`."""
    tcl = root.tk
    mame = bool(tcl.eval("info commands tk_setPalette"))
    if mame:
        tcl.eval("rename tk_setPalette ::_nc_tk_setPalette_povodny")
        tcl.eval("proc tk_setPalette args {}")
    try:
        sv_ttk.set_theme("dark" if tmava else "light")
        root.update()
    finally:
        if mame:
            tcl.eval("rename tk_setPalette {}")
            tcl.eval("rename ::_nc_tk_setPalette_povodny tk_setPalette")


def farby_zoznamu() -> dict[str, str]:
    """Výslovné farby pre tk.Listbox / tk.Text (inak by si vzali farbu zo štartu aplikácie)."""
    return dict(bg=PALETA["karta"], fg=PALETA["text"], selectbackground=PALETA["akcent"],
                selectforeground=PALETA["odznak_fg"], highlightbackground=PALETA["okraj"],
                highlightcolor=PALETA["akcent"], relief="flat", highlightthickness=1)


def _luminancia(farba: str) -> float:
    r, g, b = (int(farba.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def kontrast(a: str, b: str) -> float:
    """Pomer kontrastu dvoch farieb (WCAG), 1–21."""
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def centruj(okno: tk.Misc, rodic: tk.Misc, velkost: tuple[int, int] | None = None) -> None:
    """Umiestni dialóg do stredu hlavného okna (`velkost` = pevná veľkosť okna, inak podľa obsahu)."""
    okno.update_idletasks()
    w, h = velkost or (okno.winfo_reqwidth(), okno.winfo_reqheight())
    if rodic.winfo_viewable():
        x = rodic.winfo_rootx() + (rodic.winfo_width() - w) // 2
        y = rodic.winfo_rooty() + (rodic.winfo_height() - h) // 2
    else:                                      # hlavné okno je skryté v tray – do stredu obrazovky
        x = (okno.winfo_screenwidth() - w) // 2
        y = (okno.winfo_screenheight() - h) // 3
    okno.geometry((f"{w}x{h}" if velkost else "") + f"+{max(x, 0)}+{max(y, 0)}")


class Tooltip:
    """Jednoduchý tooltip po 500 ms nad widgetom."""

    def __init__(self, widget: tk.Misc, text: str):
        self.widget, self.text, self._id, self._okno = widget, text, None, None
        widget.bind("<Enter>", self._plan, add="+")
        widget.bind("<Leave>", self._zrus, add="+")
        widget.bind("<ButtonPress>", self._zrus, add="+")

    def _plan(self, _e=None):
        self._zrus()
        self._id = self.widget.after(500, self._ukaz)

    def _ukaz(self):
        x, y = self.widget.winfo_rootx() + 10, self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._okno = tk.Toplevel(self.widget)
        self._okno.wm_overrideredirect(True)
        self._okno.wm_geometry(f"+{x}+{y}")
        tk.Label(self._okno, text=self.text, bg=PALETA["tip_bg"], fg=PALETA["tip_fg"], relief="solid", bd=1,
                 font=(FONT, 9), padx=6, pady=3, justify="left").pack()

    def _zrus(self, _e=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._okno:
            self._okno.destroy()
            self._okno = None
