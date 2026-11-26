"""F1 Nápoveda, Čo je nové, O programe."""
import tkinter as tk
from tkinter import ttk

from ..config import PROJEKT
from ..verzia import VERZIA
from .tema import FONT, centruj, farby_zoznamu

NAPOVEDA = """NC Nástroje – spúšťač firemných aplikácií

Dvojklik na dlaždicu alebo tlačidlo = spustiť aplikáciu.
Pravé tlačidlo na dlaždici = ďalšie akcie.

Ťahanie súborov: pretiahni súbory alebo priečinky z Prieskumníka do okna.
Aplikácie, ktoré ich prijímajú, sa zvýraznia (ostatné zosivejú). Pusti ich na zvýraznenú
dlaždicu – aplikácia sa spustí s týmito súbormi. Esc = zrušiť ťahanie.

Zatvorenie okna (X) ho len skryje do oblasti oznámení. Ukončiť: Súbor → Ukončiť alebo pravý klik na ikonu → Ukončiť.
Dvojklik na ikonu v oblasti oznámení otvorí okno.

Zákazka: do poľa hore napíš číslo (napr. 21930, OD21930, OD00021930 alebo starú 001252, OD626/001252)
a stlač Enter (otvorí priečinok na L:) alebo tlačidlo Otvoriť R: / Hľadať v Lupe.

Aplikácia: do toho istého poľa (aj v rýchlom okne Ctrl+Alt+Q) napíš názov alebo vlastnú skratku
(napr. „edi“ alebo „e“) a Enter aplikáciu spustí. Skratky si nastavíš v Nastaveniach → Rýchle spúšťanie.

Zobrazenie: Zobraziť → Dlaždice alebo Zoznam + detail. Zobraziť → Tmavý režim.
V zozname klikni na aplikáciu, vpravo uvidíš jej detail. Pravé tlačidlo = ďalšie akcie.

Klávesy:
  F1        Nápoveda
  F5        Obnoviť
  Ctrl+F    Pole zákazky
  Ctrl+1…9  Spustiť aplikáciu podľa poradia
"""


def _okno(rodic, titul, text, mono=False):
    o = tk.Toplevel(rodic)
    o.title(titul)
    o.transient(rodic)
    t = tk.Text(o, width=80, height=24, wrap="word", font=("Consolas", 10) if mono else (FONT, 10), padx=12, pady=10,
                **farby_zoznamu())
    t.insert("1.0", text)
    t.configure(state="disabled")
    t.pack(fill="both", expand=True)
    zavriet = ttk.Button(o, text="Zavrieť", command=o.destroy)
    zavriet.pack(pady=8)
    o.bind("<Escape>", lambda e: o.destroy())
    centruj(o, rodic)


def ukaz_text(rodic, titul, text):
    """Okno s textom (napr. Čo je nové aplikácie), v strede hlavného okna."""
    _okno(rodic, titul, text)


def ukaz_napovedu(rodic):
    _okno(rodic, "Nápoveda", NAPOVEDA)


def ukaz_co_je_nove(rodic):
    try:
        text = (PROJEKT / "CO_JE_NOVE.md").read_text(encoding="utf-8")
    except OSError:
        text = "Súbor CO_JE_NOVE.md sa nenašiel."
    _okno(rodic, "Čo je nové", text)


def ukaz_o_programe(rodic):
    _okno(rodic, "O programe", f"NC Nástroje\nVerzia {VERZIA}\n\nSpúšťač firemných aplikácií na CNC programovanie.")
