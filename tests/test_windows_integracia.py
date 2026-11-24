"""Testy Windows integrácie (.lnk, Odoslať do, Po spustení). Všetko v tmp – nikdy skutočné shell:startup/sendto/desktop."""
import sys
from pathlib import Path

import pytest

from nc_nastroje import windows_integracia as wi
from nc_nastroje.katalog import App


@pytest.fixture(autouse=True)
def izolacia(tmp_path, monkeypatch):
    monkeypatch.setattr(wi, "IKONY_LOKALNE", tmp_path / "ikony")
    monkeypatch.setattr(wi, "LOCAL_DIR", tmp_path / "local")


def app(id_="nastrojovy_list", nazov="Nástrojový list", prijima=(".pof", "priecinok"), ikona="nastrojovy_list.png"):
    return App(id=id_, nazov=nazov, typ="exe", zdroj=f"{id_}\\1", spustit="x.exe", prijima=list(prijima), ikona=ikona)


def cudzi_zastupca(cesta: Path):
    wi.zastupca_vytvor(cesta, sys.executable, "", "", "", "Cudzí zástupca")


# ---------- základ .lnk ----------
def test_zastupca_vytvor_a_precitaj(tmp_path):
    lnk = tmp_path / "x" / "Test.lnk"
    wi.zastupca_vytvor(lnk, sys.executable, "--aplikacia abc", str(tmp_path), "", "Popis testu")
    z = wi.zastupca_precitaj(lnk)
    assert Path(z["ciel"]).samefile(sys.executable)
    assert z["argumenty"] == "--aplikacia abc" and z["popis"] == "Popis testu"
    assert wi.zastupca_precitaj(tmp_path / "neexistuje.lnk") is None


def test_poskodeny_lnk_nespadne(tmp_path):
    (tmp_path / "zly.lnk").write_bytes(b"to nie je zastupca")
    assert wi.je_nas_zastupca(tmp_path / "zly.lnk") is False


def test_nazov_zastupcu_je_platny_nazov_suboru():
    assert wi.nazov_zastupcu(app(nazov='A/B: "C"?')) == "A_B_ _C__".replace("_ _", "_ _")  # nepovolené znaky -> _
    assert wi.nazov_zastupcu(app(nazov="Nástrojový list")) == "Nástrojový list"


# ---------- spustenie po prihlásení ----------
def test_po_prihlaseni_zapnut_a_vypnut(tmp_path):
    d = tmp_path / "startup"
    assert not wi.je_po_prihlaseni(d)
    wi.nastav_po_prihlaseni(True, d)
    z = wi.zastupca_precitaj(d / wi.NAZOV_STARTUP)
    assert z["argumenty"].endswith("--tray") and z["popis"].startswith(wi.MARKER)
    assert wi.je_po_prihlaseni(d)
    wi.nastav_po_prihlaseni(True, d)                                   # opakovane nevadí
    wi.nastav_po_prihlaseni(False, d)
    assert not (d / wi.NAZOV_STARTUP).exists() and not wi.je_po_prihlaseni(d)
    wi.nastav_po_prihlaseni(False, d)                                  # vypnúť už vypnuté nevadí


def test_po_prihlaseni_necha_cudzi_subor_na_pokoji(tmp_path):
    d = tmp_path / "startup"
    cudzi_zastupca(d / wi.NAZOV_STARTUP)
    with pytest.raises(FileExistsError):
        wi.nastav_po_prihlaseni(True, d)
    wi.nastav_po_prihlaseni(False, d)
    assert (d / wi.NAZOV_STARTUP).exists()                             # cudzí zástupca sa nezmazal


# ---------- Odoslať do ----------
def test_odoslat_do_vytvori_len_povolene_a_len_s_prijima(tmp_path):
    d = tmp_path / "sendto"
    apps = [app(), app("lupa", "Lupa", prijima=()), app("nc_editor", "NC Editor", prijima=(".h",), ikona="nc_editor.png")]
    chyby = wi.synchronizuj_odoslat_do(apps, ["nastrojovy_list", "lupa"], d)
    assert chyby == []
    assert sorted(p.name for p in d.glob("*.lnk")) == ["Nástrojový list.lnk"]      # Lupa nič neprijíma, NC Editor nepovolený
    z = wi.zastupca_precitaj(d / "Nástrojový list.lnk")
    assert z["argumenty"].endswith("--aplikacia nastrojovy_list")
    assert z["popis"] == f"{wi.MARKER}: nastrojovy_list"


def test_odoslat_do_odstrani_odobrane_ale_len_nase(tmp_path):
    d = tmp_path / "sendto"
    apps = [app(), app("nc_editor", "NC Editor", prijima=(".h",), ikona="nc_editor.png")]
    wi.synchronizuj_odoslat_do(apps, ["nastrojovy_list", "nc_editor"], d)
    cudzi_zastupca(d / "Moj vlastny.lnk")
    wi.synchronizuj_odoslat_do(apps, ["nc_editor"], d)
    assert sorted(p.name for p in d.glob("*.lnk")) == ["Moj vlastny.lnk", "NC Editor.lnk"]


def test_odoslat_do_neprepise_cudzieho_zastupcu_s_rovnakym_nazvom(tmp_path):
    d = tmp_path / "sendto"
    cudzi_zastupca(d / "Nástrojový list.lnk")
    chyby = wi.synchronizuj_odoslat_do([app()], ["nastrojovy_list"], d)
    assert len(chyby) == 1 and "nie je od NC Nástrojov" in chyby[0]
    assert wi.zastupca_precitaj(d / "Nástrojový list.lnk")["popis"] == "Cudzí zástupca"
    # a pri odobratí sa ten cudzí tiež nezmaže
    wi.synchronizuj_odoslat_do([app()], [], d)
    assert (d / "Nástrojový list.lnk").exists()


def test_odoslat_do_zastupca_inej_aplikacie_sa_nezmaze(tmp_path):
    d = tmp_path / "sendto"
    wi.synchronizuj_odoslat_do([app()], ["nastrojovy_list"], d)
    iny = app("ina", "Nástrojový list")                                # rovnaký názov, iné id
    wi.synchronizuj_odoslat_do([iny], [], d)
    assert (d / "Nástrojový list.lnk").exists()


# ---------- plocha ----------
def test_zastupca_na_ploche(tmp_path):
    d = tmp_path / "desktop"
    ok, sprava = wi.vytvor_na_ploche(app(), d)
    assert ok and "na ploche" in sprava
    assert (d / "Nástrojový list.lnk").exists()
    assert wi.vytvor_na_ploche(app(), d)[0]                            # opakovane prepíše vlastného
    assert (tmp_path / "ikony" / "nastrojovy_list.ico").stat().st_size > 0


def test_zastupca_na_ploche_neprepise_cudzieho(tmp_path):
    d = tmp_path / "desktop"
    cudzi_zastupca(d / "Nástrojový list.lnk")
    ok, sprava = wi.vytvor_na_ploche(app(), d)
    assert not ok and "nepremazávam" in sprava
    assert wi.zastupca_precitaj(d / "Nástrojový list.lnk")["popis"] == "Cudzí zástupca"


def test_chybajuca_ikona_nie_je_dovod_nevytvorit_zastupcu(tmp_path):
    ok, _ = wi.vytvor_na_ploche(app(ikona="neexistuje.png"), tmp_path / "desktop")
    assert ok


# ---------- ako sa spúšťa launcher ----------
def test_prikaz_launchera_zo_zdrojoveho_kodu(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    p = wi.prikaz_launchera()
    assert Path(p.ciel).name.lower() in ("pythonw.exe", "python.exe")
    assert p.argumenty == "-m nc_nastroje.main"
    assert Path(p.pracovny) == wi.PROJEKT


def test_prikaz_launchera_zostaveny_exe_ide_cez_startovac(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    p = wi.prikaz_launchera()
    assert p.ciel.endswith("spustit_launcher.bat") and Path(p.ciel).exists() and p.okno == 7
    assert p.argumenty == ""


def test_text_startovaca(tmp_path):
    text = wi.text_startovaca(Path("C:/zaloha/nc_nastroje.exe"), tmp_path / "launcher")
    riadky = text.split("\r\n")
    assert 'set "EXE=C:\\zaloha\\nc_nastroje.exe"' in riadky or any(r.startswith('set "EXE=') for r in riadky)
    assert any("aktualna.txt" in r and r.startswith("if not exist") for r in riadky)
    assert any("%VERZIA%" in r and "nc_nastroje.exe" in r for r in riadky)
    assert riadky[-2] == 'start "" "%EXE%" %*'                         # argumenty sa odovzdajú ďalej
    assert text.index("aktualna.txt") < text.index("start ")
