"""Hlavné okno – zobrazenie A (dlaždice)."""
import logging
import queue
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, ttk

import sv_ttk
from PIL import ImageTk
from tkinterdnd2 import COPY, DND_FILES, TkinterDnD

from .. import aktualizacie, dnd, ovladanie, spustac, stavy, tray, windows_integracia
from ..config import LOCAL_DIR, Nastavenia, nacitaj_nastavenia, uloz_nastavenia
from ..ikona import vytvor_ikonu
from ..katalog import App
from ..pozadie import Pozadie
from ..verzia import VERZIA
from . import napoveda
from .dlazdica import Dlazdica
from .nastavenia import OknoNastaveni
from .tema import FONT, STAVY, SVETLA, Tooltip
from .vyber_aplikacie import VyberAplikacie

log = logging.getLogger(__name__)
STLPCE_ZUZENE_POD = 1000          # px: pri užšom okne 2 stĺpce
KATALOG_INTERVAL_MS = 10 * 60 * 1000   # kontrola nových verzií na L: každých 10 min
OKRAJ_PRUHU = "#B9D3EE"


class HlavneOkno(TkinterDnD.Tk):
    def __init__(self, prikaz: dict | None = None, instancia=None, s_tray: bool = True):
        """`prikaz` = príkaz z príkazového riadka ({"akcia": zobraz|tray|aplikacia|cesty, …}),
        `instancia` = server jednej inštancie (príkazy od druhých spustení), `s_tray` = spustiť tray ikonu."""
        super().__init__()
        self.withdraw()                           # okno sa ukáže až na konci (a len ak to príkaz chce)
        self._prikaz = prikaz or {"akcia": "zobraz"}
        self._instancia = instancia
        self._ui_fronta: queue.Queue = queue.Queue()   # práce z iných vlákien (tray, server inštancie)
        self._tray: tray.TrayIkona | None = None
        self._katalog_apps: list[App] = []        # celý katalóg (bez filtra režimu)
        self._disky_ok = {"L": True, "R": True}
        self._katalog_hotovy = False              # prvý beh na pozadí (kopírovanie verzií) dobehol
        self._cakajuce_prikazy: list[dict] = []
        self._koniec = False
        self.nast: Nastavenia = nacitaj_nastavenia()
        self.title("NC Nástroje")
        self.geometry("1160x740")
        self.minsize(900, 600)
        try:
            self._ikona_okna = ImageTk.PhotoImage(vytvor_ikonu(None, 64))   # ikona okna a panela úloh
            self.iconphoto(True, self._ikona_okna)
        except Exception:  # noqa: BLE001 – ikona nie je dôvod nespustiť okno
            log.exception("Ikona okna sa nepodarila")
        sv_ttk.set_theme("light")
        self.update_idletasks()  # téma cez <<ThemeChanged>> volá tk_setPalette – musí dobehnúť pred našimi farbami
        self.configure(bg=SVETLA["pozadie"])
        self.dlazdice: dict[str, Dlazdica] = {}
        self.apps: list[App] = []                  # zobrazené aplikácie (po filtri režimu)
        self._stlpcov = 0
        self._pozadie = Pozadie(self)              # sieť a kopírovanie bežia vo vlákne, UI nečaká
        self._stavy: dict[str, stavy.Stav] = {}    # posledné prečítané stavy (prežijú prekreslenie dlaždíc)
        self._katalog_zdroj = "ziadny"             # siet | cache | ziadny
        self._aktual: dict[str, aktualizacie.AppAktualizacia] = {}
        self._launcher_akt: aktualizacie.LauncherAktualizacia | None = None
        self._caka: dict[str, str] = {}            # bežiace aplikácie, ktoré použijú novú verziu až pri ďalšom spustení
        self._dnd_cesty: list[str] = []            # ťahané cesty (ak ich systém prezradí už pri vstupe)
        self._dnd_typy: list[str] | None = None    # None = typy zatiaľ neznáme (zistia sa pri pustení)
        self._dnd_aktivne = False
        self._pruh_id = None

        self._postav_menu()
        self._postav_horny_riadok()
        self._pruh_chyb = tk.Label(self, text="", bg="#FDE7E9", fg="#C42B1C", font=(FONT, 10), anchor="w", padx=12, pady=6)
        self._postav_pruh_aktualizacie()
        self._postav_pruh_dnd()
        self.mriezka = tk.Frame(self, bg=SVETLA["pozadie"])
        self.mriezka.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self._postav_stavovy_riadok()
        self.mriezka.bind("<Configure>", lambda e: self._rozloz())

        self.bind("<F1>", lambda e: napoveda.ukaz_napovedu(self))
        self.bind("<F5>", lambda e: self.nacitaj())  # znova načíta katalóg, aktualizácie aj stavy
        self.bind("<Control-f>", lambda e: (self.pole.focus_set(), self.pole.selection_range(0, "end")))
        for i in range(1, 7):
            self.bind(f"<Control-Key-{i}>", lambda e, i=i: self._spusti_podla_poradia(i - 1))
        self._nastav_dnd()
        self.protocol("WM_DELETE_WINDOW", self.skry_do_tray)   # X = skryť do tray, ukončiť sa dá z menu / tray
        if s_tray:
            self._spusti_tray()
        if self._instancia:
            self._instancia.nastav_obsluhu(lambda p: self.v_ui(lambda: self._spracuj_prikaz(p)))
        self.after(100, self._ui_pump)
        self.after(30_000, self._katalog_hotovy_force)          # poistka, keby pozadie nikdy nedobehlo
        self.nacitaj()
        self.after(self.nast.interval_stavov_s * 1000, self._casovac_stavov)
        self.after(KATALOG_INTERVAL_MS, self._casovac_katalogu)
        self._spracuj_prikaz(self._prikaz, prvy=True)

    # ---------- stavba UI ----------
    def _postav_menu(self):
        m = tk.Menu(self)
        subor = tk.Menu(m, tearoff=0)
        subor.add_command(label="Nastavenia…", command=self.otvor_nastavenia)
        subor.add_separator()
        subor.add_command(label="Ukončiť", command=self.ukonci)
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
        self._horny_riadok = r
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

    def _postav_pruh_aktualizacie(self):
        """Modrý pruh „Na L:\\_Nastroje je nová verzia: … Aktualizuje sa pri ďalšom spustení.“"""
        bg = SVETLA["pruh"]
        self._pruh_akt = tk.Frame(self, bg=bg, highlightbackground=OKRAJ_PRUHU, highlightthickness=1)
        tk.Label(self._pruh_akt, text="↓", font=(FONT, 13, "bold"), bg=bg, fg=SVETLA["akcent"]).pack(
            side="left", padx=(14, 8), pady=8)
        self._akt_pre = tk.Label(self._pruh_akt, font=(FONT, 11), bg=bg, fg=SVETLA["text"], padx=0)
        self._akt_pre.pack(side="left")
        self._akt_tucne = tk.Label(self._pruh_akt, font=(FONT, 11, "bold"), bg=bg, fg=SVETLA["text"], padx=0)
        self._akt_tucne.pack(side="left")
        self._akt_po = tk.Label(self._pruh_akt, font=(FONT, 11), bg=bg, fg=SVETLA["text"], padx=0)
        self._akt_po.pack(side="left")
        self._akt_tlacidlo = ttk.Button(self._pruh_akt, text="Aktualizovať teraz", command=self._aktualizuj_teraz)
        self._akt_tlacidlo.pack(side="right", padx=(10, 12), pady=6)
        Tooltip(self._akt_tlacidlo, "Skontroluje L:\\_Nastroje a skopíruje nové verzie hneď "
                                    "(pri novej verzii launchera ho reštartuje)")
        odkaz = tk.Label(self._pruh_akt, text="Čo je nové", font=(FONT, 11, "underline"), bg=bg,
                         fg=SVETLA["akcent"], cursor="hand2")
        odkaz.pack(side="right", padx=(10, 0))
        odkaz.bind("<Button-1>", lambda e: self._ukaz_co_je_nove_pruhu())
        Tooltip(odkaz, "Zobrazí, čo je v novej verzii nové")

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
        self._zdroj_text = tk.Label(s, bg=SVETLA["pozadie"], fg=SVETLA["text2"], font=(FONT, 9))
        self._zdroj_text.pack(side="right", padx=20)
        self._aktualizuj_rezim()
        self._aktualizuj_zdroj_text()

    def _aktualizuj_rezim(self):
        self._rezim.configure(text="Režim: " + ("Plný" if self.nast.rezim == "plny" else "Na prezeranie"))

    def _aktualizuj_zdroj_text(self):
        if self._katalog_zdroj == "cache":
            text = f"Aplikácie z lokálnej kópie (L:\\ nedostupný) · launcher v {VERZIA}"
        else:
            text = f"Aplikácie z {self.nast.koren_nastrojov} · launcher v {VERZIA}"
        self._zdroj_text.configure(text=text)

    # ---------- katalóg, aktualizácie a dlaždice ----------
    def nacitaj(self, sila: bool = False):
        """Rýchlo zobrazí katalóg z lokálnej cache (bez siete), potom na pozadí načíta čerstvý
        apps.json z L:, skopíruje nové verzie a prečíta stavy. `sila` = prekresliť dlaždice vždy."""
        kat = aktualizacie.nacitaj_katalog_s_cache(Path(self.nast.koren_nastrojov), len_cache=True)
        self._pouzi_katalog(kat, sila=sila)
        self.obnov_katalog()
        self.obnov_stavy()

    def _filtruj(self, apps: list[App]) -> list[App]:
        if self.nast.rezim == "prezeranie":
            return [a for a in apps if not a.len_plny_rezim]
        return list(apps)

    def _pouzi_katalog(self, kat: aktualizacie.Katalog, sila: bool = False):
        self._katalog_zdroj = kat.zdroj
        self._aktualizuj_zdroj_text()
        self._ukaz_chyby(kat.chyby)
        if kat.zdroj == "ziadny":
            return                                # nič nové: ostanú dlaždice, ktoré už sú
        self._katalog_apps = kat.apps
        apps = self._filtruj(kat.apps)
        if sila or apps != self.apps:
            self._postav_dlazdice(apps)

    def _ukaz_chyby(self, chyby: list[str]):
        if chyby:
            self._pruh_chyb.configure(text="  " + " | ".join(chyby))
            if not self._pruh_chyb.winfo_ismapped():
                self._pruh_chyb.pack(fill="x", padx=20, pady=(0, 12), before=self.mriezka)
        else:
            self._pruh_chyb.pack_forget()

    def _postav_dlazdice(self, apps: list[App]):
        self.apps = apps
        for d in self.dlazdice.values():
            d.destroy()
        self.dlazdice = {a.id: Dlazdica(self.mriezka, a, self.spusti, self._menu_dlazdice, self._prepni_pozastavenie)
                         for a in apps}
        self._stlpcov = 0
        self._rozloz()
        self._prekresli_aktualizacie()          # verzie, stavy (posledné známe) a pruh

    def obnov_katalog(self):
        """Na pozadí: apps.json z L: (+ cache), kopírovanie nových verzií, kontrola novej verzie launchera."""
        koren, kontext, caka, rezim = Path(self.nast.koren_nastrojov), self._kontext(), self._caka, self.nast.rezim

        def praca(posli):
            kat = aktualizacie.nacitaj_katalog_s_cache(koren)
            posli(("katalog", kat))                           # dlaždice hneď, kopírovanie potom
            akt, launcher = {}, None
            if kat.zdroj == "siet":
                apps = [a for a in kat.apps if not (rezim == "prezeranie" and a.len_plny_rezim)]
                akt = aktualizacie.aktualizuj_aplikacie(
                    apps, koren, lambda a: stavy.bezi_aplikacia(a, kontext), caka,
                    pri_priebehu=lambda id_, s: posli(("app", id_, s)))
                if aktualizacie.je_zostaveny():
                    launcher = aktualizacie.aktualizuj_launcher(kat.launcher, koren, VERZIA)
            return kat, akt, launcher

        self._pozadie.spusti("katalog", praca, self._po_obnove_katalogu, self._pri_priebehu_katalogu)

    def _pri_priebehu_katalogu(self, obj):
        if obj[0] == "katalog":
            self._pouzi_katalog(obj[1])
        elif obj[0] == "app":
            self._aktual[obj[1]] = obj[2]
            self._prekresli_aktualizacie()

    def _po_obnove_katalogu(self, vysledok):
        kat, akt, launcher = vysledok
        if kat.zdroj == "siet":                    # offline sa ponechá posledný známy stav
            self._aktual = dict(akt)
            self._launcher_akt = launcher
        self._prekresli_aktualizacie()
        self.obnov_stavy()                         # mohla pribudnúť / ubudnúť aplikácia
        self._po_prvom_katalogu()

    def _casovac_katalogu(self):
        self.obnov_katalog()
        self.after(KATALOG_INTERVAL_MS, self._casovac_katalogu)

    def _text_verzie(self, app: App) -> str:
        """`v 2026.11.24-1`, `v 2026.11.19-1 → 11.24-1`, `v … (staršia)` po návrate späť, `web`."""
        if app.typ == "web":
            return "web"
        dir_app = aktualizacie.APPS_DIR / app.id
        aktivna = aktualizacie.aktivna_verzia(dir_app)
        akt = self._aktual.get(app.id)
        if aktivna is None:
            return f"v {app.verzia} · " + ("kopíruje sa" if akt and akt.stav == "kopiruje" else "nie je skopírovaná")
        if akt and akt.stav == "caka" and akt.stara:
            return f"v {akt.stara} → {aktualizacie.skrat_verziu(akt.stara, aktivna)}"
        if akt and akt.stav == "kopiruje" and akt.vzdialena != aktivna:
            return f"v {aktivna} → {aktualizacie.skrat_verziu(aktivna, akt.vzdialena)}"
        if aktivna != aktualizacie.lokalne_verzie(dir_app)[-1]:
            return f"v {aktivna} (staršia)"
        return f"v {aktivna}"

    def _stav_pre(self, id_: str) -> stavy.Stav | None:
        """Stav z adaptéra, prípadne prekrytý stavom aktualizácie (modrá „Nová verzia“ / „Kopíruje sa…“)."""
        s, akt = self._stavy.get(id_), self._aktual.get(id_)
        app = self.dlazdice[id_].app if id_ in self.dlazdice else None
        if app and app.pozastavit and ovladanie.je_pozastaveny(id_) and s is not None and s.text == "Beží":
            return replace(s, stav="upozornenie", text="Pozastavený (požiadavka)")
        if akt and akt.stav == "kopiruje" and not akt.lokalna:
            return stavy.Stav("necinny", "Kopíruje sa…", s.riadky if s else [], s.cipy if s else [])
        if akt and akt.stav in ("kopiruje", "caka"):
            if s is None:
                return stavy.Stav("nova_verzia", "Nová verzia")
            if s.stav in ("ok", "necinny", "nezname"):
                return replace(s, stav="nova_verzia", text="Nová verzia")
        return s

    def _prekresli_aktualizacie(self):
        for id_, d in self.dlazdice.items():
            d.nastav_verziu(self._text_verzie(d.app))
            d.nastav_pozastaveny(ovladanie.je_pozastaveny(id_))
            d.nastav_stav(self._stav_pre(id_))
            akt = self._aktual.get(id_)
            if akt and akt.stav == "chyba":
                d.ukaz_chybu(akt.sprava)
        self._aktualizuj_pruh()
        self._publikuj_tray()

    def _cakajuce_aplikacie(self) -> list[tuple[App, aktualizacie.AppAktualizacia]]:
        return [(a, self._aktual[a.id]) for a in self.apps
                if a.id in self._aktual and self._aktual[a.id].stav in ("kopiruje", "caka")]

    def _aktualizuj_pruh(self):
        la, cakajuce = self._launcher_akt, self._cakajuce_aplikacie()
        if la and la.stav == "pripraveny":
            pre, tucne, po = "Je nová verzia NC Nástrojov: ", la.verzia, ". Aktualizácia reštartuje launcher."
        elif cakajuce:
            pre = "Na L:\\_Nastroje je nová verzia: " if len(cakajuce) == 1 else "Na L:\\_Nastroje sú nové verzie: "
            tucne = ", ".join(f"{a.nazov} {s.vzdialena}" for a, s in cakajuce)
            po = (". Aktualizuje sa pri ďalšom spustení." if any(s.stav == "caka" for _, s in cakajuce)
                  else ". Kopírujem na tento počítač…")
        else:
            self._pruh_akt.pack_forget()
            return
        self._akt_pre.configure(text=pre)
        self._akt_tucne.configure(text=tucne)
        self._akt_po.configure(text=po)
        if not self._pruh_akt.winfo_ismapped():
            self._pruh_akt.pack(fill="x", padx=20, pady=(0, 12), after=self._horny_riadok)

    def _ukaz_co_je_nove_pruhu(self):
        la, casti = self._launcher_akt, []
        if la and la.stav == "pripraveny":
            casti.append(f"NC Nástroje {la.verzia}\n\n{la.co_je_nove or '(bez poznámok)'}")
        else:
            for a, s in self._cakajuce_aplikacie():
                casti.append(f"{a.nazov} {s.vzdialena}\n\n{aktualizacie.precitaj_co_je_nove(a.id) or '(bez poznámok)'}")
        napoveda.ukaz_text(self, "Čo je nové", "\n\n――――――――――――――――\n\n".join(casti) or "Bez poznámok.")

    def _aktualizuj_teraz(self):
        la = self._launcher_akt
        if la and la.stav == "pripraveny":
            if not messagebox.askyesno("Aktualizácia NC Nástrojov",
                                       f"Launcher sa ukončí a spustí sa nová verzia {la.verzia}.\n\nPokračovať?",
                                       parent=self):
                return
            try:
                aktualizacie.spusti_aktualizator(la)
            except Exception:  # noqa: BLE001 – UI nesmie spadnúť
                log.exception("Aktualizátor sa nepodarilo spustiť")
                self._upozorni("Aktualizáciu launchera sa nepodarilo spustiť.")
                return
            self.destroy()
            return
        self.obnov_katalog()                       # nové verzie aplikácií sa kopírujú hneď, nečakať 10 min

    # ---------- stavy aplikácií (na pozadí) ----------
    def _kontext(self) -> stavy.Kontext:
        return stavy.Kontext(Path(self.nast.koren_nastrojov), Path(self.nast.koren_l),
                             Path(self.nast.koren_r), LOCAL_DIR)

    def obnov_stavy(self):
        """Spustí čítanie stavov vo vlákne; UI nečaká. Ak už beží, po dobehnutí sa spustí znova."""
        apps, kontext = list(self.apps), self._kontext()
        self._pozadie.spusti("stavy", lambda posli: stavy.obnov_vsetko(apps, kontext), self._pouzi_stavy)

    def _casovac_stavov(self):
        self.obnov_stavy()
        self.after(self.nast.interval_stavov_s * 1000, self._casovac_stavov)

    def _pouzi_stavy(self, v: "stavy.Vysledok"):
        self._stavy.update(v.stavy)
        for id_, d in self.dlazdice.items():
            if id_ in v.stavy:
                d.nastav_stav(self._stav_pre(id_))
        self._disky_ok = {"L": v.l_ok, "R": v.r_ok}
        self._publikuj_tray()
        for pismeno, ok in (("L", v.l_ok), ("R", v.r_ok)):
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
            if not d.winfo_ismapped():
                continue
            if d.winfo_rootx() <= x < d.winfo_rootx() + d.winfo_width() \
                    and d.winfo_rooty() <= y < d.winfo_rooty() + d.winfo_height():
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

    # ---------- tray, skrývanie okna, jedna inštancia ----------
    def v_ui(self, fn):
        """Zaradí `fn` do hlavného vlákna. Smie sa volať z ktoréhokoľvek vlákna (tray, server inštancie)."""
        self._ui_fronta.put(fn)

    def _ui_pump(self):
        try:
            while True:
                fn = self._ui_fronta.get_nowait()
                try:
                    fn()
                except Exception:  # noqa: BLE001 – chyba jednej akcie nesmie zastaviť ostatné
                    log.exception("Akcia v hlavnom vlákne zlyhala")
        except queue.Empty:
            pass
        if not self._koniec:
            self.after(100, self._ui_pump)

    def _spusti_tray(self):
        self._tray = tray.TrayIkona(self.v_ui, self.zobraz_okno, self.spusti_podla_id, self._prepni_pozastavenie_id,
                                    self.otvor_zakazku, self.ukonci)
        if not self._tray.spusti():
            self._tray = None                      # bez tray sa X správa ako ukončenie

    def _publikuj_tray(self):
        if not self._tray:
            return
        nove = {i for i, a in self._aktual.items() if a.stav in ("kopiruje", "caka")}
        pozastavene = {a.id for a in self.apps if ovladanie.je_pozastaveny(a.id)}
        self._tray.aktualizuj(tray.zostav_tray_stav(
            self.apps, {a.id: self._stavy.get(a.id) for a in self.apps},
            self._disky_ok["L"], self._disky_ok["R"], nove, pozastavene))

    def zobraz_okno(self):
        """Ukáže okno a dá ho do popredia (aj z tray / od druhého spustenia)."""
        self.deiconify()
        if self.state() == "iconic":
            self.state("normal")
        self.lift()
        self.attributes("-topmost", True)          # Windows inak často nepustí okno pred ostatné
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def skry_do_tray(self):
        """Zatvorenie okna (X) = skryť do tray; prvýkrát oznámenie. Bez tray ikony sa launcher ukončí."""
        if not self._tray:
            self.ukonci()
            return
        self.withdraw()
        if not self.nast.tray_oznamenie_ukazane:
            self.nast.tray_oznamenie_ukazane = True
            try:
                uloz_nastavenia(self.nast)
            except OSError:
                log.exception("Nastavenia sa nepodarilo uložiť")
            self._tray.upozorni("NC Nástroje bežia ďalej v oblasti oznámení. Okno otvoríš dvojklikom na ikonu, "
                                "ukončiť ich môžeš cez pravé tlačidlo → Ukončiť.")

    def ukonci(self):
        self.destroy()

    def destroy(self):
        self._koniec = True
        if self._tray:
            self._tray.zastav()
            self._tray = None
        if self._instancia:
            self._instancia.zatvor()
        super().destroy()

    def otvor_zakazku(self):
        """Tray → Otvoriť zákazku…: okno s poľom zákazky (samotné hľadanie príde vo fáze 6)."""
        self.zobraz_okno()
        self.pole.focus_set()
        self.pole.selection_range(0, "end")

    def _oznam(self, text: str):
        """Správa používateľovi: v pruhu, ak je okno vidieť, inak oznámením z tray."""
        if self.winfo_viewable():
            self._upozorni(text)
        elif self._tray:
            self._tray.upozorni(text)

    def _katalog_hotovy_force(self):
        if not self._katalog_hotovy:
            log.warning("Katalóg sa do 30 s nedokončil – spracúvam čakajúce príkazy aj tak")
            self._po_prvom_katalogu()

    def _po_prvom_katalogu(self):
        """Po prvom dobehnutí kopírovania verzií (aby aplikácie boli lokálne) sa spracujú príkazy, ktoré čakali,
        a spustia sa aplikácie so `spustit_pri_starte`."""
        if self._katalog_hotovy:
            return
        self._katalog_hotovy = True
        cakajuce, self._cakajuce_prikazy = self._cakajuce_prikazy, []
        for p in cakajuce:
            self._spracuj_prikaz(p)
        if self._prikaz.get("akcia") in ("zobraz", "tray") and self.nast.spustat_aplikacie_pri_starte:
            kontext = self._kontext()
            for a in self.apps:
                if a.spustit_pri_starte and not stavy.bezi_aplikacia(a, kontext):
                    log.info("Spúšťam pri štarte: %s", a.id)
                    self.spusti(a)

    def spusti_podla_id(self, id_: str, cesty: list[str] | None = None):
        app = next((a for a in self.apps if a.id == id_), None)
        if app is None:
            self._oznam(f"Aplikácia '{id_}' nie je v katalógu")
            return
        self.spusti(app, cesty)

    def _prepni_pozastavenie_id(self, id_: str):
        app = next((a for a in self.apps if a.id == id_), None)
        if app:
            self._prepni_pozastavenie(app)

    def _prepni_pozastavenie(self, app: App):
        """Pozastaviť / Pokračovať (lokálna požiadavka pre aplikáciu s `pozastavit`)."""
        try:
            ovladanie.nastav_pozastaveny(app.id, not ovladanie.je_pozastaveny(app.id))
        except OSError as e:
            log.exception("Pozastavenie %s zlyhalo", app.id)
            self._oznam(f"Pozastavenie sa nepodarilo: {e}")
            return
        self._prekresli_aktualizacie()

    def _spracuj_prikaz(self, p: dict, prvy: bool = False):
        """Príkaz z príkazového riadka (vlastný štart alebo druhé spustenie):
        zobraz | tray | aplikacia <id> [cesty] | cesty [cesty]."""
        akcia = p.get("akcia", "zobraz")
        if akcia in ("zobraz", "cesty"):
            self.zobraz_okno()
        elif akcia == "tray" and not prvy:
            return                                    # už beží – nič netreba
        if akcia in ("aplikacia", "cesty") and not self._katalog_hotovy:
            self._cakajuce_prikazy.append(p)          # aplikácie ešte nie sú skopírované – počkaj
            return
        if akcia == "aplikacia":
            self.spusti_podla_id(str(p.get("id", "")), list(p.get("cesty") or []))
        elif akcia == "cesty":
            cesty = list(p.get("cesty") or [])
            if cesty:
                VyberAplikacie(self, self.apps, cesty, lambda app, c: self.spusti(app, c))

    # ---------- Windows integrácia ----------
    def _aplikuj_windows(self, stara: Nastavenia, nova: Nastavenia):
        """Po uložení nastavení: zástupca v Po spustení a „Odoslať do“ (len ak sa niečo zmenilo)."""
        chyby = []
        if stara.spustit_po_prihlaseni != nova.spustit_po_prihlaseni:
            try:
                windows_integracia.nastav_po_prihlaseni(nova.spustit_po_prihlaseni)
            except Exception as e:  # noqa: BLE001
                log.exception("Spustenie po prihlásení zlyhalo")
                chyby.append(f"Spustenie po prihlásení: {e}")
        if set(stara.odoslat_do) != set(nova.odoslat_do):
            chyby += windows_integracia.synchronizuj_odoslat_do(self._katalog_apps, nova.odoslat_do)
        if chyby:
            self._upozorni(" · ".join(chyby))

    def _zastupca_na_ploche(self, app: App):
        ok, sprava = windows_integracia.vytvor_na_ploche(app)
        d = self.dlazdice.get(app.id)
        if d:
            d.ukaz_chybu(sprava if not ok else "")
        if ok:
            self._upozorni(sprava)

    # ---------- akcie ----------
    def spusti(self, app: App, cesty: list[str] | None = None):
        ok, sprava = spustac.spusti(app, cesty)
        d = self.dlazdice.get(app.id)
        if d:
            d.ukaz_chybu("" if ok else sprava)
        if not ok and not self.winfo_viewable():      # okno je skryté v tray – chybu ukáž oznámením
            self._oznam(f"{app.nazov}: {sprava}")

    def _spusti_podla_poradia(self, i: int):
        if i < len(self.apps):
            self.spusti(self.apps[i])

    def _menu_dlazdice(self, app: App, event):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label=app.tlacidlo, command=lambda: self.spusti(app))
        if app.typ != "web":
            m.add_command(label="Otvoriť priečinok aplikácie", command=lambda: self._otvor_priecinok(app))
        m.add_separator()
        co = aktualizacie.precitaj_co_je_nove(app.id) if app.typ != "web" else None
        m.add_command(label="Čo je nové", state="normal" if co else "disabled",
                      command=lambda: napoveda.ukaz_text(self, f"Čo je nové – {app.nazov}", co))
        self._pridaj_navrat(m, app)
        m.add_command(label="Vytvoriť zástupcu na ploche", command=lambda: self._zastupca_na_ploche(app))
        m.tk_popup(event.x_root, event.y_root)

    def _pridaj_navrat(self, m: tk.Menu, app: App):
        nazov = "Návrat na predchádzajúcu verziu"
        if app.typ == "web":
            m.add_command(label=nazov, state="disabled")
            return
        dir_app = aktualizacie.APPS_DIR / app.id
        lokalne = aktualizacie.lokalne_verzie(dir_app)
        if aktualizacie.pripnuta_verzia(dir_app) and lokalne:
            m.add_command(label=f"Použiť najnovšiu verziu (v {lokalne[-1]})",
                          command=lambda: self._zmen_verziu(app, None))
            return
        predch = aktualizacie.predchadzajuca_verzia(dir_app)
        if predch:
            m.add_command(label=f"{nazov} (v {predch})", command=lambda: self._zmen_verziu(app, predch))
        else:
            m.add_command(label=nazov, state="disabled")

    def _zmen_verziu(self, app: App, verzia: str | None):
        """Návrat na predchádzajúcu lokálnu verziu (alebo späť na najnovšiu). Použije sa pri ďalšom spustení."""
        dir_app = aktualizacie.APPS_DIR / app.id
        try:
            if verzia:
                if not messagebox.askyesno(
                        "Návrat na predchádzajúcu verziu",
                        f"{app.nazov} sa bude spúšťať vo verzii {verzia}.\n\nBežiacu aplikáciu to nezmení – "
                        f"použije sa pri ďalšom spustení. Novšia verzia sa vráti, až keď bude na L:\\_Nastroje "
                        f"ešte novšia, alebo cez „Použiť najnovšiu verziu“.\n\nPokračovať?", parent=self):
                    return
                aktualizacie.pripni(dir_app, verzia)
            else:
                aktualizacie.odpni(dir_app)
        except (OSError, ValueError) as e:
            log.exception("Zmena verzie %s zlyhala", app.id)
            self.dlazdice[app.id].ukaz_chybu(f"Zmena verzie zlyhala: {e}")
            return
        self._prekresli_aktualizacie()

    def _otvor_priecinok(self, app: App):
        ok, sprava = spustac.otvor_priecinok(app)
        if not ok:
            self.dlazdice[app.id].ukaz_chybu(sprava)

    def otvor_nastavenia(self):
        OknoNastaveni(self, self.nast, self._pri_ulozeni_nastaveni, self._filtruj(self._katalog_apps))

    def _pri_ulozeni_nastaveni(self, nast: Nastavenia):
        zmena_korena = nast.koren_nastrojov != self.nast.koren_nastrojov
        stara, self.nast = self.nast, nast
        uloz_nastavenia(nast)
        self._aktualizuj_rezim()
        self._aplikuj_windows(stara, nast)
        if zmena_korena:                          # stavy a aktualizácie z iného koreňa neplatia
            self._stavy, self._aktual, self._launcher_akt, self._caka = {}, {}, None, {}
        self.nacitaj(sila=True)
