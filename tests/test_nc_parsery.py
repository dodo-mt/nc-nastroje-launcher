"""Spoločný balík nc_parsery: launcher berie normalizáciu čísla zákazky z balíka a exe ho obsahuje (--paths)."""
from pathlib import Path

from nc_nastroje import zakazky
from nc_parsery import zakazky as balik


def test_zakazky_pouziva_funkcie_balika():
    assert zakazky.normalizuj is balik.normalizuj and zakazky.vyhovuje is balik.vyhovuje and zakazky.Dotaz is balik.Dotaz
    assert zakazky._TOKEN is balik.TOKEN_ZAKAZKY


def test_zostavenie_exe_zabali_nc_parsery():
    import importlib.util
    spec = importlib.util.spec_from_file_location("zostav_skript", Path(__file__).resolve().parent.parent / "nastroje" / "zostav.py")
    z = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(z)
    prikaz = z.prikaz_pyinstaller(Path("dist"), Path("build"), Path("x.ico"))
    assert any(str(p).endswith("NC parsery") for p in prikaz)


def test_cesta_zakazky_na_r_ma_zakaznika_len_ako_cislo(tmp_path):
    zh = zakazky.Zhoda("101270-Firma Alfa spol", "OD00021930")
    assert zh.cesta(tmp_path) == tmp_path / "101270-Firma Alfa spol" / "OD00021930"           # L: celý názov
    assert zh.cesta_r(tmp_path) == tmp_path / "101270" / "OD00021930"                         # R: len číslo zákazníka
    assert zakazky.Zhoda("OD626", "001252").cesta_r(tmp_path) == tmp_path / "OD626" / "001252"      # staré značenie ostáva
    assert zakazky.Zhoda("101270-Firma", "").cesta_r(tmp_path) == tmp_path / "101270"          # zhoda = samotný zákazník
    assert zakazky.Zhoda("100020-Beta AG", "OD00000626").cesta_r(tmp_path) == tmp_path / "100020" / "OD00000626"
