"""Okno Súbor → Stroje…: načítanie, strom, úprava polí, pridanie/odstránenie, uloženie (bez displeja sa preskočí)."""
import tkinter as tk
from tkinter import messagebox

import pytest

from nc_nastroje import nc_parsery_cesta  # noqa: F401 – pridá balík nc_parsery do sys.path
from nc_nastroje import stroje_editor
from nc_nastroje.ui import stroje_okno
from nc_parsery import stroje


class PozadieSynchronne:
    """Náhrada `Pozadie`: práca sa vykoná hneď a výsledok sa odovzdá (UI test bez vlákien)."""
    def spusti(self, kluc, praca, pri_vysledku=None, pri_priebehu=None):
        vys = praca(lambda obj: None)
        if pri_vysledku:
            pri_vysledku(vys)
        return True


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("bez displeja")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def ticho(monkeypatch):
    """Dialógy sa nezobrazujú; zaznamenajú sa a odpovedajú „áno“."""
    zaznam = []
    for meno in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, meno, lambda *a, _m=meno, **k: zaznam.append((_m, a)))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: zaznam.append(("askyesno", a)) or True)
    return zaznam


def otvor(root, koren):
    okno = stroje_okno.StrojeOkno(root, koren, PozadieSynchronne())
    okno.update()
    return okno


def test_bez_suboru_ponukne_vytvorenie(root, ticho, tmp_path):
    okno = otvor(root, tmp_path)
    assert okno._ed is None and not stroje.cesta_suboru(tmp_path).exists()
    okno._vytvor()                                          # potvrdí „áno“ -> vytvorí zo vstavaných hodnôt a načíta
    okno.update()
    assert stroje.cesta_suboru(tmp_path).exists() and okno._ed is not None
    assert "s:evo" in okno._strom.get_children("") or okno._strom.exists("s:evo")
    okno.destroy()


def test_strom_formular_a_uprava(root, ticho, tmp_path):
    stroje_editor.vytvor_z_predvolenych(stroje.cesta_suboru(tmp_path))
    okno = otvor(root, tmp_path)
    st = okno._strom
    assert st.exists("s:evo") and st.exists("m:evo80") and st.exists("k:evo_80_a")
    assert st.exists(stroje_okno._VYRADENE) and st.exists("s:dmc60") and st.parent("s:dmc60") == stroje_okno._VYRADENE
    st.selection_set("s:evo")
    okno.update()
    assert okno._vs["priecinok"].get() == "eVo 80" and okno._vs["riadenie"].get() == "Heidenhain"
    okno._vs["kinematika"].set("5x upravené")                 # úprava poľa sa zapíše do údajov
    assert okno._ed.skupina("evo")["kinematika"] == "5x upravené" and okno._ed.zmenene
    assert str(okno._b_uloz.cget("state")) == "normal"
    st.selection_set("m:evo60")
    okno.update()
    assert okno._t_hlavicka.get("1.0", "end").strip() == "re:DMU\\s*60\\s*eVo|(?<![A-Za-z])eVo\\s*60"
    assert okno._t_triedic.get("1.0", "end").strip() == "(STROJ: eVo 60)"
    okno._t_hlavicka.insert("end", "\nDMU 60 eVo - Edgecam")
    okno._zapis()
    assert okno._ed.model("evo60")["hlavicka"][-1] == r"DMU\s*60\s*eVo\s*-\s*Edgecam"
    okno.destroy()


def test_chyba_blokuje_ulozenie(root, ticho, tmp_path):
    stroje_editor.vytvor_z_predvolenych(stroje.cesta_suboru(tmp_path))
    okno = otvor(root, tmp_path)
    okno._strom.selection_set("m:kondia")
    okno.update()
    okno._t_triedic.insert("end", "\nzly text bez zatvoriek")
    okno._zapis()
    assert str(okno._b_uloz.cget("state")) == "disabled" and "chýb" in okno._stav.cget("text")
    okno.destroy()


def test_pridanie_a_odstranenie(root, ticho, tmp_path):
    stroje_editor.vytvor_z_predvolenych(stroje.cesta_suboru(tmp_path))
    okno = otvor(root, tmp_path)
    okno._pridaj_skupinu()
    okno.update()
    assert okno._strom.exists("s:nova_skupina") and okno._strom.selection() == ("s:nova_skupina",)
    okno._pridaj_model()
    assert okno._strom.exists("m:novy_model") and okno._ed.model("novy_model")["skupina"] == "nova_skupina"
    okno._pridaj_kus()
    assert okno._ed.kus("novy_kus")["model"] == "novy_model"
    okno._strom.selection_set("s:nova_skupina")
    okno._odstran()                                           # skupina má model -> informácia, nič sa nezmaže
    assert okno._ed.skupina("nova_skupina") and ticho[-1][0] == "showinfo"
    okno._strom.selection_set("m:novy_model")
    okno._odstran()                                           # potvrdí „áno“; kus ostane bez modelu
    assert okno._ed.model("novy_model") is None and okno._ed.kus("novy_kus")["model"] is None
    okno._strom.selection_set("k:novy_kus")
    okno._odstran()
    okno._strom.selection_set("s:nova_skupina")
    okno._odstran()
    assert okno._ed.skupina("nova_skupina") is None and okno._ed.chyby() == []
    okno.destroy()


def test_filter_a_test_hlavicky(root, ticho, tmp_path):
    stroje_editor.vytvor_z_predvolenych(stroje.cesta_suboru(tmp_path))
    okno = otvor(root, tmp_path)
    okno._hladaj.set("kondia")
    okno.update()
    assert okno._strom.exists("m:kondia") and not okno._strom.exists("m:evo80")
    okno._v_test.set("DMG DMC 160")
    okno._otestuj()
    txt = okno._v_vysl.cget("text")
    assert "DMC 160" in txt and "Triedič: DMC 160" in txt
    okno.destroy()


def test_ulozenie_a_cudzia_zmena(root, ticho, tmp_path):
    cesta = stroje.cesta_suboru(tmp_path)
    stroje_editor.vytvor_z_predvolenych(cesta)
    okno = otvor(root, tmp_path)
    okno._strom.selection_set("s:evo")
    okno.update()
    okno._vs["kinematika"].set("moja zmena")
    okno._uloz()
    okno.update()
    assert stroje.nacitaj(cesta).skupina("evo").kinematika == "moja zmena" and not okno._ed.zmenene
    assert (cesta.parent / "stroje.json.bak").exists()
    # iný počítač zmení súbor, okno sa pokúsi uložiť -> odmietne a ponúkne načítanie
    iny = stroje_editor.Editor(stroje.nacitaj(cesta))
    iny.skupina("dmc160")["kinematika"] = "cudzia zmena"
    stroje.uloz(iny.zoznam(), cesta)
    okno._vs["kinematika"].set("moja druha zmena")
    okno._uloz()
    okno.update()
    assert stroje.nacitaj(cesta).skupina("dmc160").kinematika == "cudzia zmena"
    assert stroje.nacitaj(cesta).skupina("evo").kinematika == "moja zmena"        # druhá zmena sa neprepísala
    assert any(t[0] == "askyesno" and "zmenil" in t[1][1] for t in ticho)
    okno.destroy()
