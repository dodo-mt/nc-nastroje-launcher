"""Okno návrhov pod poľom zákazky: nesmie pri písaní zanikať (blikalo by)."""
import tkinter as tk

import pytest

from nc_nastroje.ui.pole_zakazky import PoleZakazky
from nc_nastroje.zakazky import IndexZakaziek


@pytest.fixture
def pole(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("bez displeja")
    index = IndexZakaziek(tmp_path / "L", tmp_path / "zakazky.json")
    index._zakaznici = {"101270-Kuka Robotics": ["OD00021930", "OD00021931"], "101300-Kukla": ["OD00000626"]}
    p = PoleZakazky(root, lambda: None, "návod", navrhy=index.navrhy, pri_vybere=lambda z: None)
    p.pack()
    root.update()
    yield p, root
    root.destroy()


def napis(p, root, text):
    p._fokus_dnu()
    p.delete(0, "end")
    p.insert(0, text)
    p._aktualizuj()
    root.update()


def test_okno_sa_pri_pisani_nezrusi(pole):
    p, root = pole
    napis(p, root, "21")
    okno, tien = p._popup, p._tien
    napis(p, root, "219")
    napis(p, root, "kuk")
    assert p._popup is okno and p._tien is tien and p._otvorene()
    assert len(p._riadky) == 2


def test_nezmeneny_zoznam_sa_neprekresli(pole):
    p, root = pole
    napis(p, root, "219")
    karta = p._karta
    p._aktualizuj()
    assert p._karta is karta


def test_skry_len_skryje_a_znova_ukaze(pole):
    p, root = pole
    napis(p, root, "219")
    okno = p._popup
    p._skry()
    assert not p._otvorene() and p._popup is okno
    napis(p, root, "219")
    assert p._otvorene() and p._popup is okno


def test_esc_zavrie_a_potom_vymaze(pole):
    p, root = pole
    napis(p, root, "219")
    assert p._esc(None) == "break" and not p._otvorene() and p.get() == "219"
    assert p._esc(None) == "break" and p.get() == ""


def test_rychle_okno_akcie_a_esc(pole):
    from nc_nastroje.ui.zakazka_okna import RychleOkno
    _, root = pole
    akcie = []
    o = RychleOkno(root, lambda a, t: akcie.append((a, t)))
    root.update()
    o._akcia("L")                                   # prázdne pole: nič sa nespustí, okno ostane
    assert akcie == [] and o.winfo_exists()
    o._pole._fokus_dnu()
    o._pole.insert(0, "21930")
    o._akcia("R")
    assert akcie == [("R", "21930")] and not o.winfo_exists()
    o2 = RychleOkno(root, lambda a, t: akcie.append((a, t)))
    o2._akcia("lupa")                               # Lupa ide aj bez textu
    assert akcie[-1] == ("lupa", "")


def test_rychle_okno_klavesy(pole):
    """Shift+Enter = R:, Ctrl+Enter = Lupa. Klávesu nevysielame cez event_generate (záleží na fokuse od Windows,
    test by bol nestabilný) – kontroluje sa väzba a vykonanie jej akcie."""
    from nc_nastroje.ui.zakazka_okna import RychleOkno
    _, root = pole
    akcie = []
    o = RychleOkno(root, lambda a, t: akcie.append((a, t)))
    root.update()
    assert o._pole.bind("<Shift-Return>") and o._pole.bind("<Control-Return>")
    o._pole._fokus_dnu()
    o._pole.insert(0, "21930")
    assert o._pole._klavesa(lambda: o._akcia("R")) == "break"
    assert akcie == [("R", "21930")]
