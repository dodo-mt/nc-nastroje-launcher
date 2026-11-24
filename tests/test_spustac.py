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


def test_dlhe_cesty_idu_cez_subor(tmp_path, monkeypatch):
    from nc_nastroje import spustac
    monkeypatch.setattr(spustac, "TMP_DIR", tmp_path / "tmp")
    cesty = [f"L:/zakaznik/zakazka/pozicia/NC/program_{i:05d}.h" for i in range(1000)]
    p = zostav_prikaz(app(), Path("K"), cesty)
    assert len(p) == 2 and p[1].startswith("@")
    obsah = Path(p[1][1:]).read_text(encoding="utf-8").splitlines()
    assert obsah == cesty


def test_kratke_cesty_idu_priamo(tmp_path, monkeypatch):
    from nc_nastroje import spustac
    monkeypatch.setattr(spustac, "TMP_DIR", tmp_path / "tmp")
    p = zostav_prikaz(app(), Path("K"), ["a.pof", "b.pof"])
    assert p[1:] == ["a.pof", "b.pof"] and not (tmp_path / "tmp").exists()


def test_stare_docasne_subory_sa_zmazu(tmp_path, monkeypatch):
    import os
    import time
    from nc_nastroje import spustac
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    stary, cerstvy, cudzi = tmp / "cesty_stary.txt", tmp / "cesty_cerstvy.txt", tmp / "iny.txt"
    for f in (stary, cerstvy, cudzi):
        f.write_text("x")
    star = time.time() - 3 * 24 * 3600
    os.utime(stary, (star, star))
    os.utime(cudzi, (star, star))
    monkeypatch.setattr(spustac, "TMP_DIR", tmp)
    spustac._cesty_do_suboru(["a"])
    assert not stary.exists() and cerstvy.exists() and cudzi.exists()   # cudzie súbory sa nikdy nemažú
