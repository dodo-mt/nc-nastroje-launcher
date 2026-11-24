"""F1 Nápoveda, Čo je nové, O programe."""
import tkinter as tk
from tkinter import ttk

from ..config import PROJEKT
from ..verzia import VERZIA
from .tema import FONT, centruj

NAPOVEDA = """NC Nástroje – spúšťač firemných aplikácií

Dvojklik na dlaždicu alebo tlačidlo = spustiť aplikáciu.
Pravé tlačidlo na dlaždici = ďalšie akcie.

Klávesy:
  F1        Nápoveda
  F5        Obnoviť
  Ctrl+F    Pole zákazky
  Ctrl+1…6  Spustiť aplikáciu podľa poradia
"""


def _okno(rodic, titul, text, mono=False):
    o = tk.Toplevel(rodic)
    o.title(titul)
    o.transient(rodic)
    t = tk.Text(o, width=80, height=24, wrap="word", font=("Consolas", 10) if mono else (FONT, 10), padx=12, pady=10)
    t.insert("1.0", text)
    t.configure(state="disabled")
    t.pack(fill="both", expand=True)
    zavriet = ttk.Button(o, text="Zavrieť", command=o.destroy)
    zavriet.pack(pady=8)
    o.bind("<Escape>", lambda e: o.destroy())
    centruj(o, rodic)


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
