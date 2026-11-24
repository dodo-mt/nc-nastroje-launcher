"""Okno nastavení: ľavý zoznam sekcií, vpravo obsah."""
import tkinter as tk
from dataclasses import replace
from tkinter import filedialog, ttk

from ..config import Nastavenia
from ..katalog import App
from .tema import FONT, PALETA, Tooltip, centruj, farby_zoznamu


class OknoNastaveni(tk.Toplevel):
    def __init__(self, rodic, nast: Nastavenia, pri_ulozeni, apps: list[App] | None = None):
        super().__init__(rodic)
        self.title("Nastavenia")
        self.transient(rodic)
        self.resizable(False, False)
        self._pri_ulozeni = pri_ulozeni
        self._nast = nast
        self._apps = [a for a in (apps or []) if a.prijima]   # „Odoslať do“ má zmysel len pri aplikáciách s `prijima`
        self._v = {
            "koren_nastrojov": tk.StringVar(value=nast.koren_nastrojov),
            "koren_l": tk.StringVar(value=nast.koren_l),
            "koren_r": tk.StringVar(value=nast.koren_r),
            "rezim": tk.StringVar(value=nast.rezim),
        }
        self._interval = tk.StringVar(value=str(nast.interval_stavov_s))
        self._po_prihlaseni = tk.BooleanVar(value=nast.spustit_po_prihlaseni)
        self._app_pri_starte = tk.BooleanVar(value=nast.spustat_aplikacie_pri_starte)
        self._odoslat = {a.id: tk.BooleanVar(value=a.id in nast.odoslat_do) for a in self._apps}

        telo = ttk.Frame(self, padding=16)
        telo.pack(fill="both", expand=True)
        self._sekcie = tk.Listbox(telo, exportselection=False, height=4, width=16, font=(FONT, 10), activestyle="none",
                                  **farby_zoznamu())
        self._sekcie.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        for s in ("Cesty", "Režim", "Stavy", "Windows"):
            self._sekcie.insert("end", s)
        self._obsah = ttk.Frame(telo)
        self._obsah.grid(row=0, column=1, sticky="nsew")
        self._strany = {"Cesty": self._cesty(self._obsah), "Režim": self._rezim(self._obsah),
                        "Stavy": self._stavy(self._obsah), "Windows": self._windows(self._obsah)}
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
                  foreground=PALETA["text2"]).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
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

    def _windows(self, rodic):
        f = ttk.Frame(rodic)
        c1 = ttk.Checkbutton(f, text="Spustiť NC Nástroje po prihlásení do Windows (do oblasti oznámení)",
                             variable=self._po_prihlaseni)
        c1.grid(row=0, column=0, sticky="w", pady=6)
        Tooltip(c1, "Vytvorí zástupcu v priečinku Po spustení (shell:startup) s parametrom --tray")
        c2 = ttk.Checkbutton(f, text="Pri štarte spustiť aplikácie označené v katalógu (spustit_pri_starte)",
                             variable=self._app_pri_starte)
        c2.grid(row=1, column=0, sticky="w", pady=6)
        Tooltip(c2, "Spustí sa len to, čo ešte nebeží")
        ram_odoslat = ttk.LabelFrame(f, text="Odoslať do – pravý klik na súbor → Odoslať do", padding=10)
        ram_odoslat.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        if self._apps:
            for i, a in enumerate(self._apps):
                c = ttk.Checkbutton(ram_odoslat, text=a.nazov, variable=self._odoslat[a.id])
                c.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 24), pady=2)
                Tooltip(c, f"Pridá do ponuky Odoslať do: {a.nazov}")
        else:
            ttk.Label(ram_odoslat, text="Katalóg aplikácií ešte nie je načítaný.", foreground=PALETA["text2"]).grid()
        return f

    def _prehladaj(self, kluc):
        cesta = filedialog.askdirectory(parent=self, initialdir=self._v[kluc].get() or None)
        if cesta:
            self._v[kluc].set(cesta.replace("/", "\\"))

    def _odoslat_vyber(self) -> list[str]:
        """Zvolené aplikácie + tie, ktoré sa tu nezobrazujú (napr. skryté v režime Na prezeranie) ostanú, ako boli."""
        ostatne = [i for i in self._nast.odoslat_do if i not in self._odoslat]
        return ostatne + [i for i, v in self._odoslat.items() if v.get()]

    def _uloz(self):
        nast = replace(self._nast, **{k: v.get().strip() for k, v in self._v.items()},
                       interval_stavov_s=self._interval.get().strip(),
                       spustit_po_prihlaseni=bool(self._po_prihlaseni.get()),
                       spustat_aplikacie_pri_starte=bool(self._app_pri_starte.get()),
                       odoslat_do=self._odoslat_vyber())
        self.destroy()
        self._pri_ulozeni(nast)
