"""Okno Súbor → Stroje…: editor zdieľaného zoznamu strojov `L:\\_Nastroje\\Nastavenia\\stroje.json` (len plný režim).

Vľavo strom skupina → model → kus (vyradené skupiny sú zbalené v časti „vyradené“), vpravo formulár vybranej položky
a test hlavičky. Logika (operácie, kontrola, zápis so zálohou, ochrana pred cudzou zmenou) je v `stroje_editor.py`;
okno je len tenká vrstva. Čítanie a zápis na L: bežia na pozadí. Ak by strom + formulár nevyhovoval, dá sa prepnúť
na záložky Skupiny / Modely / Kusy (rovnaké formuláre).
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import nc_parsery_cesta  # noqa: F401 – pridá priečinok balíka nc_parsery do sys.path
from .. import stroje_editor
from nc_parsery import stroje
from .tema import FONT, PALETA, STAVY, Tooltip, centruj

_BEZ_MODELU = "— bez modelu —"
_VYRADENE = "vyr"
_BEZ_MODELU_UZOL = "kb"


def _nazvy(polozky: list[dict]) -> dict[str, str]:
    """{zobrazený názov: id}; rovnaké názvy sa odlíšia id v hranatej zátvorke."""
    pocet: dict[str, int] = {}
    for p in polozky:
        pocet[p["nazov"]] = pocet.get(p["nazov"], 0) + 1
    return {(p["nazov"] if pocet[p["nazov"]] == 1 else f"{p['nazov']} [{p['id']}]"): p["id"] for p in polozky}


class StrojeOkno(tk.Toplevel):
    def __init__(self, rodic, koren: Path, pozadie, pri_ulozeni=None):
        super().__init__(rodic)
        self.title("Stroje")
        self.configure(bg=PALETA["pozadie"])
        self.transient(rodic)
        self.minsize(900, 580)
        self._rodic, self._cesta, self._pozadie, self._pri_ulozeni = rodic, stroje.cesta_suboru(koren), pozadie, pri_ulozeni
        self._ed: stroje_editor.Editor | None = None
        self._podpis = None
        self._plnim = False                 # práve sa plní formulár (zmeny polí sa nezapisujú)
        self._pracuje = False

        horny = ttk.Frame(self, padding=(16, 12, 16, 4))
        horny.pack(fill="x")
        ttk.Label(horny, text="Stroje", font=(FONT, 14, "bold")).pack(side="left")
        ttk.Label(horny, text=f"  {self._cesta}  (zdieľaný súbor)", foreground=PALETA["text2"]).pack(side="left")

        pata = ttk.Frame(self, padding=(16, 6, 16, 12))
        pata.pack(side="bottom", fill="x")
        self._stav = ttk.Label(pata, text="Načítavam…", cursor="hand2")
        self._stav.pack(side="left")
        self._stav.bind("<Button-1>", lambda e: self._ukaz_chyby())
        zav = ttk.Button(pata, text="Zavrieť", command=self._zavri)
        zav.pack(side="right")
        Tooltip(zav, "Zavrie okno (Esc)")
        self._b_uloz = ttk.Button(pata, text="Uložiť", command=self._uloz, state="disabled")
        self._b_uloz.pack(side="right", padx=(0, 8))
        Tooltip(self._b_uloz, "Zapíše zoznam na L: (záloha stroje.json.bak). Aplikácie ho načítajú po reštarte\n"
                              "alebo po „Znovu načítať nastavenia“.")
        self._b_obnov = ttk.Button(pata, text="Znovu načítať", command=self._znovu)
        self._b_obnov.pack(side="right", padx=(0, 8))
        Tooltip(self._b_obnov, "Znova prečíta súbor z L: (neuložené zmeny sa zahodia)")

        self._obsah = ttk.Frame(self, padding=(16, 4, 16, 0))
        self._obsah.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self._zavri)
        self.bind("<Escape>", lambda e: self._zavri())
        self.geometry("1020x680")
        centruj(self, rodic, (1020, 680))
        self._nacitaj()

    # ------------------------------------------------------------------ načítanie a stavy okna

    def _vymaz_obsah(self):
        for w in self._obsah.winfo_children():
            w.destroy()

    def _text_stav(self, text: str, tlacidlo: tuple[str, callable] | None = None):
        self._ed = None
        self._vymaz_obsah()
        self._b_uloz.configure(state="disabled")
        self._stav.configure(text="", foreground=PALETA["text"])
        ttk.Label(self._obsah, text=text, justify="left", wraplength=760).pack(anchor="w", pady=24)
        if tlacidlo:
            b = ttk.Button(self._obsah, text=tlacidlo[0], command=tlacidlo[1])
            b.pack(anchor="w")

    def _nacitaj(self):
        self._stav.configure(text="Načítavam…", foreground=PALETA["text2"])
        cesta = self._cesta

        def praca(posli):
            try:
                p = stroje_editor.podpis(cesta)
                if p is None:
                    return {"existuje": False}
                z = stroje.nacitaj(cesta)
                if z.zdroj != "subor":
                    return {"existuje": True, "chyba": "Súbor sa nedá prečítať (poškodený alebo nedostupný)."}
                return {"existuje": True, "zoznam": z, "podpis": p}
            except Exception as e:  # noqa: BLE001
                return {"existuje": True, "chyba": str(e)}
        self._pozadie.spusti("stroje_okno_nacitaj", praca, self._po_nacitani)

    def _po_nacitani(self, vys):
        if not self.winfo_exists():
            return
        if vys is None or vys.get("chyba"):
            self._text_stav((vys or {}).get("chyba") or "Načítanie zlyhalo.", ("Skúsiť znova", self._nacitaj))
        elif not vys["existuje"]:
            self._text_stav("Súbor stroje.json zatiaľ neexistuje. Aplikácie dnes používajú vstavané hodnoty.\n"
                            "Môžeš ho vytvoriť zo vstavaných hodnôt (existujúci súbor sa nikdy neprepíše) "
                            "a potom stroje upravovať tu.", ("Vytvoriť stroje.json zo vstavaných hodnôt…", self._vytvor))
        else:
            self._ed, self._podpis = stroje_editor.Editor(vys["zoznam"]), vys["podpis"]
            self._postav_editor()
            if vys["zoznam"].chyby:
                messagebox.showwarning("Stroje", "Súbor obsahuje chybné záznamy, ktoré sa pri uložení stratia:\n\n"
                                       + "\n".join(vys["zoznam"].chyby[:10]), parent=self)

    def _vytvor(self):
        if not messagebox.askyesno("Stroje", f"Vytvoriť {self._cesta}\nzo vstavaných hodnôt?\n\n"
                                   "Tým sa zoznam strojov nasadí pre všetky počítače.", parent=self):
            return
        cesta = self._cesta

        def praca(posli):
            try:
                stroje_editor.vytvor_z_predvolenych(cesta)
                return None
            except Exception as e:  # noqa: BLE001
                return str(e)

        def hotovo(chyba):
            if chyba:
                messagebox.showerror("Stroje", f"Súbor sa nepodarilo vytvoriť:\n{chyba}", parent=self)
            self._nacitaj()
        self._pozadie.spusti("stroje_okno_vytvor", praca, hotovo)

    def _znovu(self):
        if self._ed and self._ed.zmenene and not messagebox.askyesno(
                "Stroje", "Neuložené zmeny sa zahodia. Načítať súbor znova?", parent=self):
            return
        self._nacitaj()

    def _zavri(self):
        if self._ed and self._ed.zmenene and not messagebox.askyesno(
                "Stroje", "Neuložené zmeny sa zahodia. Zavrieť okno?", parent=self):
            return
        self.destroy()

    # ------------------------------------------------------------------ postavenie editora

    def _postav_editor(self):
        self._vymaz_obsah()
        panely = ttk.PanedWindow(self._obsah, orient="horizontal")
        panely.pack(fill="both", expand=True)

        # ----- vľavo: hľadanie, strom, tlačidlá -----
        lavy = ttk.Frame(panely)
        panely.add(lavy, weight=1)
        r = ttk.Frame(lavy)
        r.pack(fill="x", pady=(0, 6))
        ttk.Label(r, text="Hľadať:").pack(side="left")
        self._hladaj = tk.StringVar()
        e = ttk.Entry(r, textvariable=self._hladaj)
        e.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._hladaj.trace_add("write", lambda *a: self._postav_strom(self._vyber_iid()))
        Tooltip(e, "Filtruje stroje podľa názvu, skratky a textov v hlavičke")
        tb = ttk.Frame(lavy)
        tb.pack(side="bottom", fill="x", pady=(6, 0))
        for text, cmd, tip in (("+ Skupina", self._pridaj_skupinu, "Nová skupina strojov (kinematika + riadenie, priečinok Triediča)"),
                               ("+ Model", self._pridaj_model, "Nový model / post v označenej skupine (text STROJ: v hlavičke)"),
                               ("+ Kus", self._pridaj_kus, "Nový fyzický stroj (kus) pri označenom modeli"),
                               ("Odstrániť", self._odstran, "Odstráni označenú položku")):
            b = ttk.Button(tb, text=text, command=cmd)
            b.pack(side="left", padx=(0, 6))
            Tooltip(b, tip)
        sv = ttk.Frame(lavy)
        sv.pack(fill="both", expand=True)
        self._strom = ttk.Treeview(sv, show="tree", selectmode="browse")
        sb = ttk.Scrollbar(sv, orient="vertical", command=self._strom.yview)
        self._strom.configure(yscrollcommand=sb.set)
        self._strom.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._strom.bind("<<TreeviewSelect>>", lambda e: self._ukaz_formular())

        # ----- vpravo: formuláre + test -----
        pravy = ttk.Frame(panely, padding=(14, 0, 0, 0))
        panely.add(pravy, weight=2)
        self._formy = ttk.Frame(pravy)
        self._formy.pack(fill="both", expand=True)
        self._f_prazdny = ttk.Label(self._formy, text="Vyber skupinu, model alebo kus vľavo.",
                                    foreground=PALETA["text2"])
        self._postav_skupinu()
        self._postav_model()
        self._postav_kus()
        self._postav_test(pravy)
        self._postav_strom()
        self._aktualizuj_stav()

    def _riadok(self, rodic, riadok: int, popis: str, widget, tip: str = "", stlpec_span: int = 1):
        ttk.Label(rodic, text=popis).grid(row=riadok, column=0, sticky="nw", padx=(0, 10), pady=4)
        widget.grid(row=riadok, column=1, columnspan=stlpec_span, sticky="we", pady=4)
        if tip:
            Tooltip(widget, tip)

    def _text(self, rodic, vyska: int):
        t = tk.Text(rodic, height=vyska, wrap="word", font=("Consolas", 10), padx=6, pady=4, undo=True,
                    bg=PALETA["karta"], fg=PALETA["text"], insertbackground=PALETA["text"],
                    highlightthickness=1, highlightbackground=PALETA["okraj"], relief="flat")
        t.bind("<KeyRelease>", lambda e: self._zapis())
        t.bind("<FocusOut>", lambda e: self._zapis())
        return t

    def _var(self, mena: list[str]) -> dict[str, tk.StringVar]:
        v = {m: tk.StringVar() for m in mena}
        for var in v.values():
            var.trace_add("write", lambda *a: self._zapis())
        return v

    # ----- skupina -----
    def _postav_skupinu(self):
        f = self._f_skupina = ttk.Frame(self._formy)
        f.columnconfigure(1, weight=1)
        self._vs = self._var(["nazov", "riadenie", "typ", "kinematika", "priecinok", "vprevadzke"])
        self._riadok(f, 0, "Názov:", ttk.Entry(f, textvariable=self._vs["nazov"]),
                     "Názov skupiny (zobrazený text; pevné id sa nemení)")
        cb = ttk.Combobox(f, textvariable=self._vs["riadenie"], values=("",) + stroje.RIADENIA, state="readonly", width=16)
        cb.bind("<<ComboboxSelected>>", lambda e: self._zapis())
        self._riadok(f, 1, "Riadenie:", cb, "Heidenhain / Sinumerik / Fanuc / Mazak")
        self._riadok(f, 2, "Typ riadenia:", ttk.Entry(f, textvariable=self._vs["typ"], width=22), "napr. H530, H640, 840D, 31i")
        self._riadok(f, 3, "Kinematika:", ttk.Entry(f, textvariable=self._vs["kinematika"]), "napr. 5x, 3x, 2-kanálové sústružnícko-frézovacie")
        self._riadok(f, 4, "Priečinok Triediča:", ttk.Entry(f, textvariable=self._vs["priecinok"]),
                     "Podpriečinok v NC\\ pre Triedič NC. Prázdny = netriedi sa.\n"
                     "Zmena nepremenuje existujúce priečinky na L: a R:!")
        ch = ttk.Checkbutton(f, text="v prevádzke", variable=self._vs["vprevadzke"], onvalue="1", offvalue="0")
        self._riadok(f, 5, "", ch, "Vyradené skupiny sa v zozname schovajú do časti „vyradené“")
        self._i_skupina = ttk.Label(f, foreground=PALETA["text2"], justify="left", wraplength=520)
        self._i_skupina.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ----- model -----
    def _postav_model(self):
        f = self._f_model = ttk.Frame(self._formy)
        f.columnconfigure(1, weight=1)
        self._vm = self._var(["nazov", "skratka", "skupina", "pripony"])
        self._riadok(f, 0, "Názov:", ttk.Entry(f, textvariable=self._vm["nazov"]), "Názov modelu / postprocesora")
        self._riadok(f, 1, "Skratka (Lupa):", ttk.Entry(f, textvariable=self._vm["skratka"], width=22),
                     "Krátky názov stroja v Lupe (napr. eVo 80)")
        self._cb_skupina = ttk.Combobox(f, textvariable=self._vm["skupina"], state="readonly")
        self._cb_skupina.bind("<<ComboboxSelected>>", lambda e: self._zapis())
        self._riadok(f, 2, "Skupina:", self._cb_skupina, "Skupina, do ktorej model patrí (určuje priečinok Triediča)")
        self._t_hlavicka = self._text(f, 4)
        self._riadok(f, 3, "Texty v hlavičke:", self._t_hlavicka,
                     "Čo stojí za STROJ: v hlavičke programu (hyperMILL aj Edgecam), jeden text na riadok.\n"
                     "Medzera = ľubovoľne veľa medzier, veľkosť písmen nehrá rolu. Pokročilý regulárny výraz: re:…")
        ttk.Label(f, text="jeden na riadok; regulárny výraz s predponou re:", foreground=PALETA["text2"]).grid(
            row=4, column=1, sticky="w")
        self._t_triedic = self._text(f, 3)
        self._riadok(f, 5, "Texty pre Triedič:", self._t_triedic,
                     "Presné riadky (STROJ: …) so zátvorkami, ktoré Triedič NC triedi (len hyperMILL a DMC 105).\n"
                     "Jeden na riadok; prázdne = Triedič tento model netriedi.")
        self._riadok(f, 6, "Prípony:", ttk.Entry(f, textvariable=self._vm["pripony"], width=22),
                     "Prípony programov oddelené čiarkou (.h, .mpf)")
        r = ttk.Frame(f)
        r.grid(row=7, column=1, sticky="w", pady=(8, 0))
        for text, smer, tip in (("▲ Vyššia priorita", -1, "Model sa skúša skôr (prvá zhoda vyhráva)"),
                                ("▼ Nižšia priorita", 1, "Model sa skúša neskôr")):
            b = ttk.Button(r, text=text, command=lambda s=smer: self._posun(s))
            b.pack(side="left", padx=(0, 8))
            Tooltip(b, tip)
        self._i_model = ttk.Label(f, foreground=PALETA["text2"], justify="left", wraplength=520)
        self._i_model.grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ----- kus -----
    def _postav_kus(self):
        f = self._f_kus = ttk.Frame(self._formy)
        f.columnconfigure(1, weight=1)
        self._vk = self._var(["nazov", "model"])
        self._riadok(f, 0, "Názov:", ttk.Entry(f, textvariable=self._vk["nazov"]),
                     "Konkrétny stroj v hale (napr. monoBLOCK 65 A)")
        self._cb_model = ttk.Combobox(f, textvariable=self._vk["model"], state="readonly")
        self._cb_model.bind("<<ComboboxSelected>>", lambda e: self._zapis())
        self._riadok(f, 1, "Model:", self._cb_model, "Model / post, podľa ktorého stroj pracuje")
        self._i_kus = ttk.Label(f, foreground=PALETA["text2"], justify="left", wraplength=520)
        self._i_kus.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ----- test hlavičky -----
    def _postav_test(self, rodic):
        lf = ttk.LabelFrame(rodic, text="Otestovať hlavičku", padding=8)
        lf.pack(side="bottom", fill="x", pady=(10, 0))
        lf.columnconfigure(0, weight=1)
        self._v_test = tk.StringVar()
        e = ttk.Entry(lf, textvariable=self._v_test)
        e.grid(row=0, column=0, sticky="we")
        e.bind("<Return>", lambda ev: self._otestuj())
        Tooltip(e, "Vlož riadok z programu, napr. (STROJ: DMG DMC 160), alebo len názov stroja")
        b1 = ttk.Button(lf, text="Otestovať", command=self._otestuj)
        b1.grid(row=0, column=1, padx=(8, 0))
        b2 = ttk.Button(lf, text="Súbor…", command=self._otestuj_subor)
        b2.grid(row=0, column=2, padx=(6, 0))
        Tooltip(b2, "Prečíta hlavičku NC programu a ukáže, ako by ju rozpoznali Lupa a Triedič")
        self._v_vysl = ttk.Label(lf, text="", justify="left", wraplength=560)
        self._v_vysl.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _vyhodnot(self, r: dict):
        m, s = r["model"], r["skupina"]
        riadky = [f"Text: {r['stroj']}"]
        if m:
            riadky.append(f"Lupa: {m.kratky} – model {m.nazov}, skupina {s.nazov if s else '?'}")
        else:
            riadky.append("Lupa: nerozpoznané (zobrazí sa text z hlavičky)")
        riadky.append("Triedič: " + (", ".join(r["triedic"]) if r["triedic"] else "netriedi sa (ostane v NC)")
                      + ("  ⚠ viac zhôd – ostane v NC" if len(r["triedic"]) > 1 else ""))
        self._v_vysl.configure(text="\n".join(riadky))

    def _otestuj(self):
        if self._ed:
            self._vyhodnot(stroje_editor.otestuj_hlavicku(self._ed.zoznam(), self._v_test.get()))

    def _otestuj_subor(self):
        if not self._ed:
            return
        p = filedialog.askopenfilename(parent=self, title="NC program na otestovanie",
                                       filetypes=[("NC programy", "*.h *.mpf *.i *.spf *.nc *.eia"), ("Všetky súbory", "*.*")])
        if not p:
            return
        try:
            self._vyhodnot(stroje_editor.otestuj_subor(self._ed.zoznam(), p))
        except OSError as e:
            messagebox.showerror("Stroje", f"Súbor sa nedá prečítať:\n{e}", parent=self)

    # ------------------------------------------------------------------ strom

    def _vyber_iid(self) -> str | None:
        s = self._strom.selection() if hasattr(self, "_strom") else ()
        return s[0] if s else None

    @staticmethod
    def _popis_skupiny(s: dict) -> str:
        r = " ".join(x for x in (s.get("riadenie", ""), s.get("typ_riadenia", "")) if x)
        return s["nazov"] + (f"   ·  {r}" if r else "")

    def _zhoduje(self, filtr: str, *polozky: str) -> bool:
        return not filtr or any(filtr in (p or "").lower() for p in polozky)

    def _postav_strom(self, vyber: str | None = None):
        ed, filtr = self._ed, self._hladaj.get().strip().lower()
        if not self._strom.winfo_exists():
            return
        self._plnim = True
        try:
            self._strom.delete(*self._strom.get_children())
            vyr = self._strom.insert("", "end", iid=_VYRADENE, text="vyradené", open=bool(filtr))
            kusy_pouzite: set[str] = set()
            vyradene_n = 0
            for s in ed.skupiny:
                modely = ed.modely_skupiny(s["id"])
                podstrom = []
                for m in modely:
                    kusy = ed.kusy_modelu(m["id"])
                    kusy_pouzite |= {k["id"] for k in kusy}
                    texty = " ".join(m.get("hlavicka", [])) + " " + " ".join((m.get("triedic") or {}).get("match", []))
                    kusy_f = [k for k in kusy if self._zhoduje(filtr, k["nazov"])]
                    if self._zhoduje(filtr, s["nazov"], m["nazov"], m.get("skratka", ""), texty) or kusy_f:
                        podstrom.append((m, kusy if self._zhoduje(filtr, s["nazov"], m["nazov"], m.get("skratka", ""), texty) else kusy_f))
                if filtr and not podstrom and not self._zhoduje(filtr, s["nazov"], s.get("priecinok", "")):
                    continue
                rodic = "" if s.get("v_prevadzke", True) else vyr
                if not s.get("v_prevadzke", True):
                    vyradene_n += 1
                self._strom.insert(rodic, "end", iid="s:" + s["id"], text=self._popis_skupiny(s), open=True)
                for m, kusy in podstrom:
                    self._strom.insert("s:" + s["id"], "end", iid="m:" + m["id"], text=m["nazov"], open=True)
                    for k in kusy:
                        self._strom.insert("m:" + m["id"], "end", iid="k:" + k["id"], text=k["nazov"])
            bez = [k for k in ed.kusy if k["id"] not in kusy_pouzite and self._zhoduje(filtr, k["nazov"])]
            if bez:
                self._strom.insert("", "end", iid=_BEZ_MODELU_UZOL, text="kusy bez modelu", open=True)
                for k in bez:
                    self._strom.insert(_BEZ_MODELU_UZOL, "end", iid="k:" + k["id"], text=k["nazov"])
            if not vyradene_n:
                self._strom.delete(_VYRADENE)
            else:
                self._strom.item(_VYRADENE, text=f"vyradené ({vyradene_n})")
        finally:
            self._plnim = False
        if vyber and self._strom.exists(vyber):
            self._strom.selection_set(vyber)
            self._strom.see(vyber)
        else:
            self._ukaz_formular()

    # ------------------------------------------------------------------ formulár ↔ údaje

    def _ukaz_formular(self):
        if self._plnim or not self._ed:
            return
        iid = self._vyber_iid() or ""
        for f in (self._f_prazdny, self._f_skupina, self._f_model, self._f_kus):
            f.pack_forget()
        druh, _, id_ = iid.partition(":")
        ed = self._ed
        self._plnim = True
        try:
            if druh == "s" and ed.skupina(id_):
                s = ed.skupina(id_)
                for k, v in (("nazov", s["nazov"]), ("riadenie", s["riadenie"]), ("typ", s["typ_riadenia"]),
                             ("kinematika", s["kinematika"]), ("priecinok", s["priecinok"]),
                             ("vprevadzke", "1" if s.get("v_prevadzke", True) else "0")):
                    self._vs[k].set(v)
                mm = ed.modely_skupiny(id_)
                self._i_skupina.configure(text=f"Modely: {', '.join(m['nazov'] for m in mm) or '–'}\n"
                                               f"Kusy: {sum(len(ed.kusy_modelu(m['id'])) for m in mm)}\n"
                                               f"id: {id_}")
                self._f_skupina.pack(fill="both", expand=True, anchor="n")
            elif druh == "m" and ed.model(id_):
                m = ed.model(id_)
                self._skupiny_naz = _nazvy(ed.skupiny)
                self._cb_skupina.configure(values=list(self._skupiny_naz))
                sk = next((n for n, i in self._skupiny_naz.items() if i == m["skupina"]), "")
                for k, v in (("nazov", m["nazov"]), ("skratka", m.get("skratka", "")),
                             ("skupina", sk), ("pripony", ", ".join(m.get("pripony", [])))):
                    self._vm[k].set(v)
                self._t_hlavicka.delete("1.0", "end")
                self._t_hlavicka.insert("1.0", stroje_editor.regexy_na_riadky(m.get("hlavicka", [])))
                self._t_triedic.delete("1.0", "end")
                self._t_triedic.insert("1.0", "\n".join((m.get("triedic") or {}).get("match", [])))
                poradie = [x["id"] for x in ed.modely].index(id_) + 1
                self._i_model.configure(text=f"Poradie (priorita rozpoznania): {poradie} z {len(ed.modely)}\n"
                                             f"Kusy: {', '.join(k['nazov'] for k in ed.kusy_modelu(id_)) or '–'}\nid: {id_}")
                self._f_model.pack(fill="both", expand=True, anchor="n")
            elif druh == "k" and ed.kus(id_):
                k = ed.kus(id_)
                self._modely_naz = _nazvy(ed.modely)
                self._cb_model.configure(values=[_BEZ_MODELU] + list(self._modely_naz))
                mod = ed.model(k["model"]) if k["model"] else None
                self._vk["nazov"].set(k["nazov"])
                self._vk["model"].set(next((n for n, i in self._modely_naz.items() if i == k["model"]), _BEZ_MODELU))
                sk = ed.skupina(mod["skupina"]) if mod else None
                self._i_kus.configure(text=(f"Skupina: {sk['nazov']}\n" if sk else "") + f"id: {id_}")
                self._f_kus.pack(fill="both", expand=True, anchor="n")
            else:
                self._f_prazdny.pack(anchor="w", pady=12)
        finally:
            self._plnim = False

    def _zapis(self):
        """Zmena v poli formulára -> údaje vybranej položky, obnovenie stromu a stavu."""
        if self._plnim or not self._ed:
            return
        iid = self._vyber_iid() or ""
        druh, _, id_ = iid.partition(":")
        ed = self._ed
        prestavat = False
        if druh == "s" and ed.skupina(id_):
            s, v = ed.skupina(id_), self._vs
            vpred = v["vprevadzke"].get() != "0"
            prestavat = vpred != s.get("v_prevadzke", True)
            s.update(nazov=v["nazov"].get(), riadenie=v["riadenie"].get(), typ_riadenia=v["typ"].get(),
                     kinematika=v["kinematika"].get(), priecinok=v["priecinok"].get().strip(), v_prevadzke=vpred)
            self._strom.item(iid, text=self._popis_skupiny(s))
        elif druh == "m" and ed.model(id_):
            m, v = ed.model(id_), self._vm
            nova = self._skupiny_naz.get(v["skupina"].get())
            if nova and nova != m["skupina"]:
                m["skupina"] = nova
                prestavat = True
            m["nazov"], m["skratka"] = v["nazov"].get(), v["skratka"].get()
            ed.nastav_texty_modelu(id_, self._t_hlavicka.get("1.0", "end"), self._t_triedic.get("1.0", "end"),
                                   v["pripony"].get())
            self._strom.item(iid, text=m["nazov"])
        elif druh == "k" and ed.kus(id_):
            k, v = ed.kus(id_), self._vk
            novy = self._modely_naz.get(v["model"].get())
            if novy != k["model"]:
                k["model"] = novy
                prestavat = True
            k["nazov"] = v["nazov"].get()
            self._strom.item(iid, text=k["nazov"])
        if prestavat:
            self._postav_strom(iid)
            self._ukaz_formular()
        self._aktualizuj_stav()

    def _aktualizuj_stav(self):
        if not self._ed:
            return
        ch = self._ed.chyby()
        if ch:
            text, farba = f"● {len(ch)} chýb – {ch[0]}", STAVY["chyba"][0]
        elif self._ed.zmenene:
            text, farba = "● Zmenené, neuložené", STAVY["upozornenie"][0]
        else:
            text, farba = "● Bez zmien", STAVY["ok"][0]
        self._stav.configure(text=text, foreground=farba)
        self._b_uloz.configure(state="normal" if self._ed.zmenene and not ch and not self._pracuje else "disabled")

    def _ukaz_chyby(self):
        if self._ed and (ch := self._ed.chyby()):
            messagebox.showwarning("Stroje – chyby", "\n".join(ch), parent=self)

    # ------------------------------------------------------------------ operácie

    def _vyber_druh(self) -> tuple[str, str]:
        druh, _, id_ = (self._vyber_iid() or "").partition(":")
        return druh, id_

    def _pridaj_skupinu(self):
        iid = self._ed.pridaj_skupinu()
        self._postav_strom("s:" + iid)
        self._aktualizuj_stav()

    def _pridaj_model(self):
        druh, id_ = self._vyber_druh()
        ed = self._ed
        skupina = (id_ if druh == "s" else ed.model(id_)["skupina"] if druh == "m" and ed.model(id_)
                   else ed.model(ed.kus(id_)["model"])["skupina"] if druh == "k" and ed.kus(id_) and ed.kus(id_)["model"] else None)
        if not skupina:
            messagebox.showinfo("Stroje", "Najprv vyber skupinu, do ktorej model patrí.", parent=self)
            return
        iid = ed.pridaj_model("Nový model", skupina)
        self._postav_strom("m:" + iid)
        self._aktualizuj_stav()

    def _pridaj_kus(self):
        druh, id_ = self._vyber_druh()
        ed = self._ed
        model = (id_ if druh == "m" else ed.kus(id_)["model"] if druh == "k" and ed.kus(id_) else None)
        iid = ed.pridaj_kus("Nový kus", model)
        self._postav_strom("k:" + iid)
        self._aktualizuj_stav()

    def _odstran(self):
        druh, id_ = self._vyber_druh()
        ed = self._ed
        if druh == "s" and ed.skupina(id_):
            if ed.modely_skupiny(id_):
                messagebox.showinfo("Stroje", "Skupina má modely – najprv ich presuň do inej skupiny alebo zmaž.", parent=self)
                return
            if messagebox.askyesno("Stroje", f"Odstrániť skupinu „{ed.skupina(id_)['nazov']}“?", parent=self):
                ed.zmaz_skupinu(id_)
        elif druh == "m" and ed.model(id_):
            n = len(ed.kusy_modelu(id_))
            if messagebox.askyesno("Stroje", f"Odstrániť model „{ed.model(id_)['nazov']}“?"
                                   + (f"\nJeho {n} kusov ostane bez modelu." if n else ""), parent=self):
                ed.zmaz_model(id_)
        elif druh == "k" and ed.kus(id_):
            if messagebox.askyesno("Stroje", f"Odstrániť kus „{ed.kus(id_)['nazov']}“?", parent=self):
                ed.zmaz_kus(id_)
        else:
            return
        self._postav_strom()
        self._aktualizuj_stav()

    def _posun(self, smer: int):
        druh, id_ = self._vyber_druh()
        if druh == "m" and self._ed.posun_model(id_, smer):
            self._ukaz_formular()
            self._aktualizuj_stav()

    # ------------------------------------------------------------------ uloženie

    def _uloz(self):
        if not self._ed or self._pracuje:
            return
        self._pracuje = True
        self._aktualizuj_stav()
        ed, cesta, podpis = self._ed, self._cesta, self._podpis

        def praca(posli):
            try:
                stroje_editor.uloz(ed, cesta, podpis)
                return {"ok": True, "podpis": stroje_editor.podpis(cesta)}
            except stroje_editor.SuborZmenenyChyba:
                return {"zmenene": True}
            except Exception as e:  # noqa: BLE001
                return {"chyba": str(e)}
        self._pozadie.spusti("stroje_okno_uloz", praca, self._po_ulozeni)

    def _po_ulozeni(self, vys):
        self._pracuje = False
        if not self.winfo_exists():
            return
        vys = vys or {"chyba": "Zápis zlyhal."}
        if vys.get("ok"):
            self._podpis = vys["podpis"]
            self._aktualizuj_stav()
            self._stav.configure(text="● Uložené", foreground=STAVY["ok"][0])
            if self._pri_ulozeni:
                self._pri_ulozeni()
            messagebox.showinfo("Stroje", "Zoznam strojov je uložený.\nLupa a Triedič ho načítajú po reštarte "
                                "alebo po „Znovu načítať nastavenia“.", parent=self)
        elif vys.get("zmenene"):
            self._aktualizuj_stav()
            if messagebox.askyesno("Stroje", "Súbor stroje.json sa medzitým zmenil (iný počítač alebo „Naučiť sa“ "
                                   "v Triediči), preto sa neuložil.\n\nNačítať ho znova? Neuložené zmeny sa zahodia.",
                                   parent=self):
                self._nacitaj()
        else:
            self._aktualizuj_stav()
            messagebox.showerror("Stroje", f"Uloženie zlyhalo:\n{vys.get('chyba')}", parent=self)
