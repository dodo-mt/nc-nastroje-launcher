"""Otvorenie priečinka zákazky: Prieskumník alebo Total Commander."""
from nc_nastroje import priecinky
from nc_nastroje.config import Nastavenia


def test_prikaz_total_commander_s_medzerami():
    p = priecinky.prikaz_total_commander(r"C:\totalcmd\TOTALCMD64.EXE", r"L:\100016-Welser s.r.o\OD00000777")
    assert p == r'"C:\totalcmd\TOTALCMD64.EXE" /O /T /L="L:\100016-Welser s.r.o\OD00000777"'


def test_najdi_z_nastavenia_subor_aj_priecinok(tmp_path):
    exe = tmp_path / "TOTALCMD64.EXE"
    exe.write_text("x")
    assert priecinky.najdi_total_commander(str(exe)) == exe
    assert priecinky.najdi_total_commander(str(tmp_path)) == exe


def test_otvor_prieskumnik_a_totalcmd(tmp_path, monkeypatch):
    otvorene, spustene = [], []
    monkeypatch.setattr(priecinky.os, "startfile", lambda c: otvorene.append(c), raising=False)
    monkeypatch.setattr(priecinky.subprocess, "Popen", lambda prikaz, **kw: spustene.append(prikaz))
    exe = tmp_path / "TOTALCMD64.EXE"
    exe.write_text("x")
    assert priecinky.otvor_priecinok(r"L:\x\y") == ""
    assert otvorene == [r"L:\x\y"] and not spustene
    assert priecinky.otvor_priecinok(r"L:\x\y", "totalcmd", str(exe)) == ""
    assert spustene == [priecinky.prikaz_total_commander(exe, r"L:\x\y")]


def test_totalcmd_nenajdeny_otvori_prieskumnik(monkeypatch):
    otvorene = []
    monkeypatch.setattr(priecinky.os, "startfile", lambda c: otvorene.append(c), raising=False)
    monkeypatch.setattr(priecinky, "najdi_total_commander", lambda n="": None)
    vyhrada = priecinky.otvor_priecinok(r"L:\x", "totalcmd")
    assert "Prieskumník" in vyhrada and otvorene == [r"L:\x"]


def test_nastavenia_otvarat_v_sa_normalizuje():
    assert Nastavenia(otvarat_v="nieco").otvarat_v == "prieskumnik"
    assert Nastavenia(otvarat_v="totalcmd").otvarat_v == "totalcmd"
