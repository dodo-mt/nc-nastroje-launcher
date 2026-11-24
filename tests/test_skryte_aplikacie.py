"""Aplikácie skryté používateľom (Nastavenia → Aplikácie) a zamknuté režimom Na prezeranie."""
from nc_nastroje.config import Nastavenia
from nc_nastroje.katalog import App, filtruj_rezim


def app(id_, **kw):
    return App(id=id_, nazov=id_.title(), typ="exe", zdroj=f"{id_}\1", spustit=f"{id_}.exe", **kw)


APPS = [app("tnc_sync", len_plny_rezim=True), app("lupa"), app("nc_editor"), app("nastrojovy_list")]


def ids(apps):
    return [a.id for a in apps]


def test_bez_skrytych_sa_nic_nemeni():
    assert ids(filtruj_rezim(APPS, "plny")) == ["tnc_sync", "lupa", "nc_editor", "nastrojovy_list"]
    assert ids(filtruj_rezim(APPS, "plny", [])) == ids(APPS)


def test_skryte_plati_v_oboch_rezimoch():
    assert ids(filtruj_rezim(APPS, "plny", ["lupa"])) == ["tnc_sync", "nc_editor", "nastrojovy_list"]
    assert ids(filtruj_rezim(APPS, "prezeranie", ["lupa"])) == ["nc_editor", "nastrojovy_list"]


def test_skryte_neznama_aplikacia_nevadi_a_vstup_sa_nemeni():
    original = list(APPS)
    assert ids(filtruj_rezim(APPS, "plny", ["neexistuje"])) == ids(APPS)
    assert APPS == original


def test_nastavenia_skryte_sa_normalizuju():
    assert Nastavenia(skryte_aplikacie="zle").skryte_aplikacie == []
    assert Nastavenia(skryte_aplikacie=["lupa", 3]).skryte_aplikacie == ["lupa", "3"]
    assert Nastavenia().skryte_aplikacie == []
