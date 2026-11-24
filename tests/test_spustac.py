import os
import time
from pathlib import Path

import pytest

from nc_nastroje import spustac
from nc_nastroje.katalog import App
from nc_nastroje.spustac import spusti, zostav_prikaz


def app(**kw):
    return App(id="x", nazov="X", typ="exe", zdroj="x\\1", spustit="x.exe", **kw)


@pytest.fixture
def apps_dir(tmp_path, monkeypatch):
    """Lokálne kópie aplikácií v tmp: apps/x/2026.11.24-1 (aktívna) – nikdy skutočný %LOCALAPPDATA%."""
    d = tmp_path / "apps"
    (d / "x" / "2026.11.24-1").mkdir(parents=True)
    monkeypatch.setattr("nc_nastroje.aktualizacie.APPS_DIR", d)
    monkeypatch.setattr(spustac, "TMP_DIR", tmp_path / "tmp")
    return d


def test_prikaz_z_lokalnej_kopie_s_cestami(apps_dir):
    p = zostav_prikaz(app(), ["a b.pof", "c.pof"])
    assert p == [str(apps_dir / "x" / "2026.11.24-1" / "x.exe"), "a b.pof", "c.pof"]


def test_prikaz_bez_ciest(apps_dir):
    assert len(zostav_prikaz(app())) == 1


def test_spusta_najnovsiu_lokalnu_verziu(apps_dir):
    (apps_dir / "x" / "2026.11.25-2").mkdir()
    assert Path(zostav_prikaz(app())[0]).parent.name == "2026.11.25-2"


def test_nie_je_lokalne_nespadne(tmp_path, monkeypatch):
    monkeypatch.setattr("nc_nastroje.aktualizacie.APPS_DIR", tmp_path / "prazdne")
    ok, sprava = spusti(app())
    assert not ok and "skopírovať" in sprava
    with pytest.raises(FileNotFoundError):
        zostav_prikaz(app())


def test_chybajuci_subor_nespadne(apps_dir):
    ok, sprava = spusti(app())          # priečinok verzie existuje, x.exe v ňom nie
    assert not ok and "súbor chýba" in sprava


def test_nespusta_z_l(apps_dir):
    """Aplikácia sa spúšťa len z lokálnej kópie, nikdy z koreňa nástrojov (L:)."""
    assert "apps" in zostav_prikaz(app())[0]


def test_dlhe_cesty_idu_cez_subor(apps_dir):
    cesty = [f"L:/zakaznik/zakazka/pozicia/NC/program_{i:05d}.h" for i in range(1000)]
    p = zostav_prikaz(app(), cesty)
    assert len(p) == 2 and p[1].startswith("@")
    obsah = Path(p[1][1:]).read_text(encoding="utf-8").splitlines()
    assert obsah == cesty


def test_kratke_cesty_idu_priamo(apps_dir, tmp_path):
    p = zostav_prikaz(app(), ["a.pof", "b.pof"])
    assert p[1:] == ["a.pof", "b.pof"] and not (tmp_path / "tmp").exists()


def test_stare_docasne_subory_sa_zmazu(tmp_path, monkeypatch):
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


def test_priamo_spustana_aplikacia_sa_nekopiruje(tmp_path):
    from nc_nastroje.katalog import App
    exe = tmp_path / "Lupa" / "Lupa.exe"
    app = App(id="lupa", nazov="Lupa", typ="exe", spustit=str(exe))
    assert spustac.priecinok_aplikacie(app) == exe.parent
    assert spustac.zostav_prikaz(app, ["C:/x"])[0] == str(exe)
    ok, sprava = spustac.spusti(app)                                      # súbor neexistuje
    assert not ok and "chýba" in sprava


def test_hladanie_v_exe_aplikacii_s_argumentmi(tmp_path, monkeypatch):
    exe = tmp_path / "Lupa.exe"
    exe.write_bytes(b"x")
    app = App(id="lupa", nazov="Lupa", typ="exe", spustit=str(exe), argumenty_hladat="--hladat {text}")
    volane = []
    monkeypatch.setattr(spustac.subprocess, "Popen", lambda prikaz, **kw: volane.append(prikaz))
    assert spustac.spusti_hladaj(app, "21930-1A mala") == (True, "")
    assert volane == [[str(exe), "--hladat", "21930-1A mala"]]               # text ostane jedným argumentom
