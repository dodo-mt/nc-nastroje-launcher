"""Návrhy pod poľom zákazky (zakazky.IndexZakaziek.navrhy)."""
from pathlib import Path

import pytest

from nc_nastroje.zakazky import IndexZakaziek


@pytest.fixture
def index(tmp_path):
    i = IndexZakaziek(tmp_path / "L", tmp_path / "zakazky.json")
    i._zakaznici = {"101270-Kuka Robotics": ["OD00021930", "OD00021931"],
                    "101300-Kukla": ["OD00000626"],
                    "OD626": ["001252"]}
    return i


def rel(n):
    return [z.rel for z in n.polozky]


def test_cislo_bez_nul(index):
    assert rel(index.navrhy("219")) == ["101270-Kuka Robotics\\OD00021930", "101270-Kuka Robotics\\OD00021931"]


def test_predpona_od_on(index):
    assert "OD626\\001252" not in rel(index.navrhy("OD62"))
    assert rel(index.navrhy("ON001")) == ["OD626\\001252"]


def test_zakaznici_podla_mena_a_cisla(index):
    n = index.navrhy("kuka rob")
    assert [z.zakaznik for z in n.polozky] == ["101270-Kuka Robotics"] and n.polozky[0].je_zakaznik
    assert n.polozky[0].pocet == 2
    assert [z.zakaznik for z in index.navrhy("1012").polozky if z.je_zakaznik] == ["101270-Kuka Robotics"]


def test_zakaznik_a_cislo_zuzi_vyber(index):
    assert all(z.zakaznik.startswith("101270") for z in index.navrhy("101270\\219").polozky)


def test_prazdne_a_nuly(index):
    assert index.navrhy("").polozky == [] and index.navrhy("0").polozky == []


def test_limit_a_viac(index):
    index._zakaznici = {f"{100000 + i}-Firma {i}": [] for i in range(30)}
    n = index.navrhy("firma")
    assert len(n.polozky) == 12 and n.viac == 18
