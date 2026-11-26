"""Rýchle spúšťanie aplikácií z poľa zákazky: hľadanie, skratky, validácia."""
from nc_nastroje.config import Nastavenia
from nc_nastroje.katalog import App
from nc_nastroje.rychle_spustanie import bez_diakritiky, chyba_aliasu, najdi_aplikacie

APPS = [App(id="tnc_sync", nazov="TNC Sync", typ="exe"),
        App(id="nastrojovy_list", nazov="Nástrojový list", typ="exe"),
        App(id="nc_editor", nazov="NC Editor", typ="exe", popis="Úprava NC programov"),
        App(id="lupa", nazov="Lupa", typ="web"),
        App(id="cnc_vykres_edgecam", nazov="Programový list Edgecam", typ="exe")]


def ids(text, aliasy=None):
    return [z.app_id for z in najdi_aplikacie(text, APPS, aliasy)]


def test_diakritika():
    assert bez_diakritiky("Nástrojový LIST") == "nastrojovy list"


def test_podla_nazvu_bez_diakritiky():
    assert ids("edi") == ["nc_editor"]
    assert ids("nastr") == ["nastrojovy_list"]
    assert ids("Nástroj") == ["nastrojovy_list"]
    assert ids("edge") == ["cnc_vykres_edgecam"]          # začiatok slova v názve
    assert ids("tnc sy") == ["tnc_sync"]


def test_alias_ma_prednost():
    assert ids("e", {"nc_editor": "e"}) == ["nc_editor"] + [i for i in ids("e") if i != "nc_editor"]
    assert ids("l", {"lupa": "l"})[0] == "lupa"
    assert ids("tn", {"tnc_sync": "tn"})[0] == "tnc_sync"


def test_cislo_zakazky_nenavrhne_aplikaciu():
    assert ids("21930") == [] and ids("OD21930") == [] and ids("OD626\001252") == []
    assert ids("") == []


def test_maximum_a_ikona_popis():
    z = najdi_aplikacie("n", APPS, None, maximum=2)
    assert len(z) == 2
    e = najdi_aplikacie("nc ed", APPS)[0]
    assert (e.popis, e.ikona) == ("Úprava NC programov", "nc_editor.png") and e.je_aplikacia


def test_chyba_aliasu():
    assert chyba_aliasu("", "lupa", {}) == ""
    assert chyba_aliasu("e", "nc_editor", {"nc_editor": "e"}) == ""
    assert "už použitá" in chyba_aliasu("e", "lupa", {"nc_editor": "e", "lupa": "e"})
    assert "číslo zákazky" in chyba_aliasu("21930", "lupa", {})
    assert "číslo zákazky" in chyba_aliasu("od21930", "lupa", {})
    assert "len písmená" in chyba_aliasu("a b!", "lupa", {})


def test_nastavenia_aliasy_cistenie():
    n = Nastavenia(aliasy_aplikacii={"lupa": " l ", "x": "", "y": 5})
    assert n.aliasy_aplikacii == {"lupa": "l", "y": "5"}
    assert Nastavenia(aliasy_aplikacii="zle").aliasy_aplikacii == {}


def test_pole_enter_spusti_aplikaciu_a_cislo_otvori_zakazku(tmp_path):
    import tkinter as tk
    import pytest
    from nc_nastroje import zakazky
    from nc_nastroje.rychle_spustanie import najdi_aplikacie as hladaj
    from nc_nastroje.ui.pole_zakazky import PoleZakazky
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("bez displeja")
    index = zakazky.IndexZakaziek(tmp_path / "L", tmp_path / "z.json")
    index._zakaznici = {"101270-Kuka": ["OD00021930"]}

    def navrhy(text):
        a = hladaj(text, APPS, {"nc_editor": "e"})
        n = index.navrhy(text) if len(text.strip()) >= 2 else zakazky.Navrhy([], 0)
        return zakazky.Navrhy(a + list(n.polozky), n.viac)

    vybrane, enter = [], []
    p = PoleZakazky(root, lambda: enter.append(1), "návod", navrhy=navrhy, pri_vybere=vybrane.append)
    p.pack()
    root.update()
    try:
        p._fokus_dnu()
        p.insert(0, "e")                                   # jeden znak = skratka, bez čakania na návrhy
        p._enter(None)
        assert [z.app_id for z in vybrane] == ["nc_editor"] and not enter
        p.delete(0, "end")
        p.insert(0, "edi")                                 # okno návrhov sa s aplikáciou aj zákazníkmi vykreslí
        p._aktualizuj()
        root.update()
        assert p._otvorene() and getattr(p._zhody[0], "je_aplikacia", False)
        p.delete(0, "end")
        p.insert(0, "kuk")
        p._aktualizuj()
        root.update()
        assert p._otvorene()
        vybrane.clear()
        p.delete(0, "end")
        p.insert(0, "21930")                               # číslo = ako doteraz (otvoriť na L:)
        p._aktualizuj()
        root.update()
        assert not any(getattr(z, "je_aplikacia", False) for z in p._zhody)
        p._enter(None)
        assert enter == [1] and not vybrane
    finally:
        root.destroy()


def test_ui_moduly_sa_daju_importovat():
    import importlib
    for m in ("hlavne_okno", "nastavenia", "pole_zakazky", "zakazka_okna"):
        importlib.import_module(f"nc_nastroje.ui.{m}")
