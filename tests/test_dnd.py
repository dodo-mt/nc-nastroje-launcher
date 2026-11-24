"""Testy pravidiel drag & drop (dnd.py) – bez UI."""
import tkinter

import pytest

from nc_nastroje import dnd


def falosny_priecinok(*priecinky):
    return lambda c: c in priecinky


def test_typ_cesty():
    je = falosny_priecinok("C:\\zakazka")
    assert dnd.typ_cesty("C:\\zakazka", je) == "priecinok"
    assert dnd.typ_cesty("C:\\x\\Program1.POF", je) == ".pof"      # prípona vždy malými písmenami
    assert dnd.typ_cesty("C:\\x\\NC_BEZ_PRIPONY", je) == ""
    assert dnd.typ_cesty("C:\\x\\a.tar.gz", je) == ".gz"


def test_typ_cesty_chyba_pri_zisteni_priecinka():
    def zle(_c):
        raise OSError("sieť")
    assert dnd.typ_cesty("L:\\a\\b.h", zle) == ".h"


def test_prijima_typ():
    assert dnd.prijima_typ([".pof", "priecinok"], ".pof")
    assert dnd.prijima_typ([".pof", "priecinok"], "priecinok")
    assert not dnd.prijima_typ([".pof", "priecinok"], ".h")
    assert dnd.prijima_typ(["*"], ".cokolvek")
    assert dnd.prijima_typ(["*"], "")                  # aj súbor bez prípony
    assert not dnd.prijima_typ([], ".pof")              # prázdne = nič


def test_kompatibilita_vyzaduje_vsetky_polozky():
    nl = [".pof", "priecinok"]
    assert dnd.je_kompatibilna(nl, [".pof", ".pof", "priecinok"])
    assert not dnd.je_kompatibilna(nl, [".pof", ".h"])  # jedna nevyhovuje = nekompatibilná
    assert not dnd.je_kompatibilna([], [".pof"])
    assert not dnd.je_kompatibilna(nl, [])              # nič ťahané = nič nevyhovuje
    assert dnd.je_kompatibilna(["priecinok", "*"], [".x", "priecinok", ""])   # Lupa


def test_parsuj_data_s_medzerami_a_lomitkami():
    split = tkinter.Tcl().splitlist
    cesty = dnd.parsuj_data("{C:/Moje zákazky/a b.pof} C:/x/c.pof", split)
    assert cesty == ["C:\\Moje zákazky\\a b.pof", "C:\\x\\c.pof"]
    assert dnd.parsuj_data("", split) == []
    assert dnd.parsuj_data("   ", split) == []


@pytest.mark.parametrize("n,tvar", [(0, "súborov"), (1, "súbor"), (2, "súbory"), (4, "súbory"), (5, "súborov"), (21, "súborov")])
def test_sklonovanie(n, tvar):
    assert dnd.sklonuj(n, "súbor", "súbory", "súborov") == tvar


def test_popis_poloziek():
    assert dnd.popis_poloziek([".pof"] * 4) == "4 súbory .pof"
    assert dnd.popis_poloziek([".pof"]) == "1 súbor .pof"
    assert dnd.popis_poloziek([".pof"] * 5) == "5 súborov .pof"
    assert dnd.popis_poloziek(["priecinok"]) == "1 priečinok"
    assert dnd.popis_poloziek(["priecinok"] * 3) == "3 priečinky"
    assert dnd.popis_poloziek([".h", ".mpf", ".h"]) == "3 súbory (.h, .mpf)"
    assert dnd.popis_poloziek([".h", "priecinok"]) == "2 položky"
    assert dnd.popis_poloziek([""]) == "1 súbor bez prípony"
    assert dnd.popis_poloziek([".a", ".b", ".c", ".d"]) == "4 súbory (.a, .b, .c, …)"


def test_nazvy_skratene():
    assert dnd.nazvy_skratene(["C:\\a\\x.pof"]) == "x.pof"
    assert dnd.nazvy_skratene(["C:\\a\\x.pof", "C:\\a\\y.pof"]) == "x.pof, y.pof"
    assert dnd.nazvy_skratene(["C:\\a\\x.pof", "C:\\a\\y.pof", "C:\\a\\z.pof"]) == "x.pof, y.pof a 1 ďalší"
    assert dnd.nazvy_skratene([f"C:\\a\\{i}.pof" for i in range(5)]) == "0.pof, 1.pof a 3 ďalšie"
    assert dnd.nazvy_skratene(["C:\\zakazka\\"]) == "zakazka"
