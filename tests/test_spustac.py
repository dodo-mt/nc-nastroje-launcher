from pathlib import Path

from nc_nastroje.katalog import App
from nc_nastroje.spustac import spusti, zostav_prikaz


def app(**kw):
    return App(id="x", nazov="X", typ="exe", zdroj="x\1", spustit="x.exe", **kw)


def test_prikaz_s_cestami():
    p = zostav_prikaz(app(), Path("K"), ["a b.pof", "c.pof"])
    assert p == [str(Path("K") / "x\1" / "x.exe"), "a b.pof", "c.pof"]


def test_prikaz_bez_ciest():
    assert len(zostav_prikaz(app(), Path("K"))) == 1


def test_chybajuci_subor_nespadne(tmp_path):
    ok, sprava = spusti(app(), tmp_path)
    assert not ok and "súbor chýba" in sprava
