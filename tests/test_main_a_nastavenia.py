"""Testy príkazového riadka launchera, nastavení fázy 5 a ovládania (pozastavenie)."""
import json
import os

import pytest

from nc_nastroje import config, ovladanie
from nc_nastroje.main import parsuj_argumenty, prikaz_z_argumentov


def prikaz(argv, cwd):
    return prikaz_z_argumentov(parsuj_argumenty(argv), cwd)


def test_bez_argumentov_zobrazi_okno(tmp_path):
    assert prikaz([], str(tmp_path)) == {"akcia": "zobraz"}


def test_tray(tmp_path):
    assert prikaz(["--tray"], str(tmp_path)) == {"akcia": "tray"}


def test_aplikacia_s_cestami_su_absolutne(tmp_path):
    p = prikaz(["--aplikacia", "nastrojovy_list", "a b.pof", os.path.join("pod", "c.pof")], str(tmp_path))
    assert p["akcia"] == "aplikacia" and p["id"] == "nastrojovy_list"
    assert p["cesty"] == [str(tmp_path / "a b.pof"), str(tmp_path / "pod" / "c.pof")]


def test_aplikacia_bez_ciest(tmp_path):
    assert prikaz(["--aplikacia", "lupa"], str(tmp_path)) == {"akcia": "aplikacia", "id": "lupa", "cesty": []}


def test_cesty_bez_aplikacie_ponukne_vyber(tmp_path):
    p = prikaz(["x.h", "y.mpf"], str(tmp_path))
    assert p == {"akcia": "cesty", "cesty": [str(tmp_path / "x.h"), str(tmp_path / "y.mpf")]}


def test_absolutne_cesty_ostanu_ako_su(tmp_path):
    abs_cesta = str(tmp_path / "zakazka" / "p.pof")
    assert prikaz(["--aplikacia", "nl", abs_cesta], "C:\\inde")["cesty"] == [abs_cesta]


def test_cesty_maju_prednost_pred_tray(tmp_path):
    assert prikaz(["--tray", "x.h"], str(tmp_path))["akcia"] == "cesty"


# ---------- nastavenia ----------
def test_nove_nastavenia_maju_rozumne_predvolene_hodnoty():
    n = config.Nastavenia()
    assert n.spustit_po_prihlaseni is False and n.spustat_aplikacie_pri_starte is True
    assert n.odoslat_do == [] and n.port_instancie == 47653 and n.tray_oznamenie_ukazane is False


@pytest.mark.parametrize("zle", ["abc", 0, 80, 70000, None, -5])
def test_neplatny_port_sa_nahradi_predvolenym(zle):
    assert config.Nastavenia(port_instancie=zle).port_instancie == 47653


def test_odoslat_do_nie_je_zdielany_medzi_instanciami():
    a, b = config.Nastavenia(), config.Nastavenia()
    a.odoslat_do.append("x")
    assert b.odoslat_do == []


def test_ulozenie_a_nacitanie_novych_poli(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NASTAVENIA_SUBOR", tmp_path / "nastavenia.json")
    config.uloz_nastavenia(config.Nastavenia(spustit_po_prihlaseni=True, odoslat_do=["lupa", "nc_editor"],
                                             tray_oznamenie_ukazane=True, port_instancie=50000))
    n = config.nacitaj_nastavenia()
    assert n.spustit_po_prihlaseni and n.odoslat_do == ["lupa", "nc_editor"] and n.port_instancie == 50000
    assert n.tray_oznamenie_ukazane is True


def test_stary_subor_nastaveni_bez_novych_poli_a_s_neznamym_klucom(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NASTAVENIA_SUBOR", tmp_path / "nastavenia.json")
    (tmp_path / "nastavenia.json").write_text(json.dumps({"rezim": "prezeranie", "budusci_kluc": 1}), encoding="utf-8")
    n = config.nacitaj_nastavenia()
    assert n.rezim == "prezeranie" and n.spustat_aplikacie_pri_starte is True and n.odoslat_do == []


# ---------- ovládanie (pozastavenie) ----------
def test_pozastavenie_je_lokalny_priznak(tmp_path):
    assert ovladanie.je_pozastaveny("triedic_nc", tmp_path) is False
    ovladanie.nastav_pozastaveny("triedic_nc", True, tmp_path)
    assert ovladanie.je_pozastaveny("triedic_nc", tmp_path) is True
    assert (tmp_path / "triedic_nc.pozastaveny").exists()
    assert ovladanie.je_pozastaveny("ina_app", tmp_path) is False
    ovladanie.nastav_pozastaveny("triedic_nc", False, tmp_path)
    assert ovladanie.je_pozastaveny("triedic_nc", tmp_path) is False
    ovladanie.nastav_pozastaveny("triedic_nc", False, tmp_path)        # opakované vypnutie nevadí
