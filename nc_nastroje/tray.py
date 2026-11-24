"""Tray ikona (pystray v samostatnom vlákne).

Menu (podľa schváleného návrhu): hlavička „NC NÁSTROJE · L:\\ R:\\ OK“, aplikácie so stavom (klik = spustiť),
Pozastaviť triedič (ak beží), Otvoriť zákazku…, **Otvoriť NC Nástroje** (tučné, aj dvojklik), Ukončiť.

Natívne menu Windows nevie farebné bodky, preto je stav aj tvarom (✔ ⚠ ✖ ⬇ ○), nielen farbou.
Callbacky z pystray bežia v jeho vlákne: nič v UI sa tu nemení priamo, všetko ide cez `v_ui(fn)`
(front do hlavného vlákna Tkinter).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from . import stavy as st
from .ikona import vytvor_ikonu
from .katalog import App

log = logging.getLogger(__name__)

SYMBOLY = {"ok": "✔", "upozornenie": "⚠", "chyba": "✖", "nova_verzia": "⬇", "necinny": "○", "nezname": "?"}


@dataclass
class TrayPolozka:
    id: str
    nazov: str
    stav: str
    vpravo: str = ""


@dataclass
class TrayStav:
    hlavicka: str = "NC NÁSTROJE"
    polozky: list[TrayPolozka] = field(default_factory=list)
    stav: str = "necinny"                       # najhorší stav (bodka na ikone)
    pozastavit: tuple[str, bool] | None = None   # (id triediča, je pozastavený) – len ak triedič beží


def hlavicka_diskov(l_ok: bool, r_ok: bool) -> str:
    if l_ok and r_ok:
        text = "L:\\ R:\\ OK"
    elif not l_ok and not r_ok:
        text = "L:\\ R:\\ nedostupné"
    else:
        text = ("L:" if not l_ok else "R:") + "\\ nedostupný"
    return f"NC NÁSTROJE · {text}"


def _vpravo(stav: st.Stav | None, nova_verzia: bool, teraz: datetime) -> str:
    if nova_verzia:
        return "nová"
    if stav is None:
        return ""
    if stav.text == "Beží":
        return "beží"
    if stav.stav == "chyba":
        return "chyba"
    if stav.cas and stav.cas.date() == teraz.date():
        return stav.cas.strftime("%H:%M")
    return ""


def zostav_tray_stav(apps: list[App], stavy_apps: dict[str, st.Stav | None], l_ok: bool, r_ok: bool,
                     nove: set[str] | None = None, pozastavene: set[str] | None = None,
                     teraz: datetime | None = None) -> TrayStav:
    """Čistá funkcia: z aktuálnych stavov zostaví, čo sa ukáže v tray (menu, ikona, tooltip)."""
    teraz = teraz or datetime.now()
    nove, pozastavene = nove or set(), pozastavene or set()
    polozky, pozastavit = [], None
    for app in apps:
        s = stavy_apps.get(app.id)
        stav = "nova_verzia" if app.id in nove and (s is None or s.stav in ("ok", "necinny", "nezname")) \
            else (s.stav if s else "necinny")
        polozky.append(TrayPolozka(app.id, app.nazov, stav, _vpravo(s, app.id in nove, teraz)))
        if app.pozastavit and s is not None and s.text == "Beží":
            pozastavit = (app.id, app.id in pozastavene)
    najhorsi = st.najhorsi([p.stav for p in polozky]
                           + (["chyba"] if not l_ok else []) + (["upozornenie"] if not r_ok else []))
    return TrayStav(hlavicka_diskov(l_ok, r_ok), polozky, najhorsi, pozastavit)


def text_polozky(p: TrayPolozka) -> str:
    """„✔  TNC Sync<TAB>11:32“ – po tabulátore sa text v natívnom menu zarovná doprava."""
    zaklad = f"{SYMBOLY.get(p.stav, '?')}  {p.nazov}"
    return f"{zaklad}\t{p.vpravo}" if p.vpravo else zaklad


class TrayIkona:
    """Obal nad pystray. `spusti()` vráti False, ak tray nejde (napr. bez Shell), a launcher ostane bez neho."""

    def __init__(self, v_ui: Callable[[Callable], None], pri_zobraz: Callable[[], None],
                 pri_aplikacia: Callable[[str], None], pri_pozastav: Callable[[str], None],
                 pri_zakazka: Callable[[], None], pri_koniec: Callable[[], None]):
        self._v_ui = v_ui
        self._pri_zobraz, self._pri_aplikacia, self._pri_pozastav = pri_zobraz, pri_aplikacia, pri_pozastav
        self._pri_zakazka, self._pri_koniec = pri_zakazka, pri_koniec
        self._stav = TrayStav()
        self._icon = None
        self.bezi = False

    # ---------- menu ----------
    def _akcia(self, fn, *args):
        """Callback z pystray vlákna -> hlavné vlákno UI; chyba nesmie zhodiť tray."""
        def volaj(_icon=None, _item=None):
            try:
                self._v_ui(lambda: fn(*args))
            except Exception:  # noqa: BLE001
                log.exception("Akcia z tray zlyhala")
        return volaj

    def zostav_menu(self, stav: TrayStav | None = None) -> list[tuple]:
        """Zoznam položiek ako (text, akcia | None, vlastnosti) – nezávislé od pystray, preto testovateľné."""
        s = stav or self._stav
        polozky: list[tuple] = [(s.hlavicka, None, {"enabled": False})]
        polozky += [(text_polozky(p), self._akcia(self._pri_aplikacia, p.id), {}) for p in s.polozky]
        polozky.append(("-", None, {}))
        if s.pozastavit:
            id_, je = s.pozastavit
            polozky.append(("Pokračovať v triedení" if je else "Pozastaviť triedič",
                            self._akcia(self._pri_pozastav, id_), {}))
        polozky.append(("Otvoriť zákazku…", self._akcia(self._pri_zakazka), {}))
        polozky.append(("Otvoriť NC Nástroje", self._akcia(self._pri_zobraz), {"default": True}))
        polozky.append(("-", None, {}))
        polozky.append(("Ukončiť", self._akcia(self._pri_koniec), {}))
        return polozky

    def _pystray_menu(self):
        import pystray
        vysledok = []
        for text, akcia, vlastnosti in self.zostav_menu():
            if text == "-":
                vysledok.append(pystray.Menu.SEPARATOR)
            else:
                vysledok.append(pystray.MenuItem(text, akcia, **vlastnosti))
        return vysledok

    # ---------- životný cyklus ----------
    def spusti(self) -> bool:
        try:
            import pystray
            self._icon = pystray.Icon("nc_nastroje", vytvor_ikonu(self._stav.stav), self._tooltip(),
                                      menu=pystray.Menu(self._pystray_menu))   # menu sa zostaví pri každom otvorení
            self._icon.run_detached()
            self.bezi = True
            return True
        except Exception:  # noqa: BLE001
            log.exception("Tray ikonu sa nepodarilo spustiť")
            self._icon, self.bezi = None, False
            return False

    def _tooltip(self) -> str:
        return self._stav.hlavicka.replace("NC NÁSTROJE", "NC Nástroje", 1)[:127]

    def aktualizuj(self, stav: TrayStav) -> None:
        """Nový stav pre menu, ikonu (bodka) a tooltip. Volať z ktoréhokoľvek vlákna."""
        predosly, self._stav = self._stav, stav
        if not self._icon:
            return
        try:
            if predosly.stav != stav.stav:
                self._icon.icon = vytvor_ikonu(stav.stav)
            self._icon.title = self._tooltip()
        except Exception:  # noqa: BLE001
            log.exception("Aktualizácia tray ikony zlyhala")

    def upozorni(self, text: str, titul: str = "NC Nástroje") -> None:
        if self._icon and self.bezi:
            try:
                self._icon.notify(text, titul)
            except Exception:  # noqa: BLE001
                log.exception("Oznámenie z tray zlyhalo")

    def zastav(self) -> None:
        icon, self._icon, self.bezi = self._icon, None, False
        if icon:
            try:
                icon.stop()
            except Exception:  # noqa: BLE001
                log.exception("Zastavenie tray ikony zlyhalo")
