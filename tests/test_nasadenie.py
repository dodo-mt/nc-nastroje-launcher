"""Testy fázy 8: režim Na prezeranie, nasadenie pre kolegov (prvé spustenie, odinštalovanie, zostavenie, exe)."""
import importlib.util
import sys
from pathlib import Path

import pytest

from nc_nastroje import spustac, windows_integracia as wi
from nc_nastroje.config import Nastavenia
from nc_nastroje.katalog import App, filtruj_rezim
from nc_nastroje.main import parsuj_argumenty, prikaz_z_argumentov
from nc_nastroje.ui.prve_spustenie import Volby, volby_na_nastavenia


def app(id_, **kw):
    return App(id=id_, nazov=id_.title(), typ="exe", zdroj=f"{id_}\\1", spustit=f"{id_}.exe", **kw)


APPS = [app("tnc_sync"), app("triedic_nc", len_plny_rezim=True), app("lupa"), app("nc_editor")]


# ---------- režim ----------
def test_plny_rezim_ukaze_vsetko():
    assert [a.id for a in filtruj_rezim(APPS, "plny")] == ["tnc_sync", "triedic_nc", "lupa", "nc_editor"]


def test_prezeranie_skryje_aplikacie_len_pre_programatora():
    assert [a.id for a in filtruj_rezim(APPS, "prezeranie")] == ["tnc_sync", "lupa", "nc_editor"]


def test_neznamy_rezim_sa_sprava_ako_plny_a_vstup_sa_nemeni():
    original = list(APPS)
    assert len(filtruj_rezim(APPS, "nieco")) == 4
    assert filtruj_rezim(APPS, "prezeranie") is not APPS and APPS == original


# ---------- Python v zostavenom exe ----------
def test_python_zo_zdrojoveho_kodu_je_ten_co_spustil_launcher(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert Path(spustac.najdi_pythonw()).name.lower() in ("pythonw.exe", "python.exe")


def test_v_zostavenom_exe_sa_nepouzije_sys_executable(monkeypatch, tmp_path):
    """V exe je `sys.executable` samotný launcher – skripty typu python sa nesmú spúšťať ním."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(spustac.shutil, "which", lambda n: "C:\\Python\\pythonw.exe" if n == "pythonw" else None)
    assert spustac.najdi_pythonw() == "C:\\Python\\pythonw.exe"
    monkeypatch.setattr(spustac.shutil, "which", lambda n: "C:\\Python\\python.exe" if n == "python" else None)
    assert spustac.najdi_pythonw() == "C:\\Python\\python.exe"
    monkeypatch.setattr(spustac.shutil, "which", lambda n: None)
    assert spustac.najdi_pythonw() is None


def test_skript_bez_nainstalovaneho_pythonu_zlyha_zrozumitelne(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(spustac.shutil, "which", lambda n: None)
    d = tmp_path / "apps"
    (d / "x" / "2026.11.24-1").mkdir(parents=True)
    (d / "x" / "2026.11.24-1" / "x.py").write_text("print(1)")
    monkeypatch.setattr("nc_nastroje.aktualizacie.APPS_DIR", d)
    a = App(id="x", nazov="X", typ="python", zdroj="x\\1", spustit="x.py")
    ok, sprava = spustac.spusti(a)
    assert not ok and "Python" in sprava


# ---------- prvé spustenie ----------
def test_volby_prvého_spustenia_sa_premietnu_do_nastaveni():
    n = Nastavenia(rezim="plny", spustit_po_prihlaseni=False, tmavy_rezim=True, odoslat_do=["lupa"])
    novy = volby_na_nastavenia(n, Volby("prezeranie", True, False))
    assert novy.rezim == "prezeranie" and novy.spustit_po_prihlaseni is True
    assert novy.tmavy_rezim is True and novy.odoslat_do == ["lupa"]          # ostatné sa nemení
    assert n.rezim == "plny"                                                  # pôvodný objekt sa nemení


def test_neplatny_rezim_z_dialogu_nezmeni_nastavenia():
    assert volby_na_nastavenia(Nastavenia(rezim="plny"), Volby("blbost")).rezim == "plny"


def test_predvolene_volby_su_pre_kolegov_v_kancelarii():
    v = Volby()
    assert v.rezim == "prezeranie" and v.po_prihlaseni and v.na_plochu


# ---------- príkazový riadok ----------
def test_prve_spustenie_a_odinstaluj_z_prikazoveho_riadka(tmp_path):
    args = parsuj_argumenty(["--prve-spustenie"])
    assert prikaz_z_argumentov(args, str(tmp_path)) == {"akcia": "zobraz", "prve_spustenie": True}
    assert parsuj_argumenty(["--odinstaluj"]).odinstaluj is True
    assert parsuj_argumenty([]).odinstaluj is False and parsuj_argumenty([]).prve_spustenie is False


# ---------- zástupcovia: plocha a odinštalovanie ----------
@pytest.fixture
def izolacia(tmp_path, monkeypatch):
    monkeypatch.setattr(wi, "IKONY_LOKALNE", tmp_path / "ikony")
    monkeypatch.setattr(wi, "LOCAL_DIR", tmp_path / "local")
    return tmp_path


def cudzi(cesta: Path):
    wi.zastupca_vytvor(cesta, sys.executable, "", "", "", "Cudzí zástupca")


def test_zastupca_launchera_na_ploche(izolacia):
    d = izolacia / "desktop"
    ok, sprava = wi.vytvor_launcher_na_ploche(d)
    assert ok and (d / wi.NAZOV_PLOCHA).exists()
    assert wi.je_nas_zastupca(d / wi.NAZOV_PLOCHA)
    assert wi.zastupca_precitaj(d / wi.NAZOV_PLOCHA)["popis"] == f"{wi.MARKER}: plocha"
    assert wi.vytvor_launcher_na_ploche(d)[0]                                  # opakovane prepíše vlastného


def test_zastupca_launchera_neprepise_cudzi_subor(izolacia):
    d = izolacia / "desktop"
    cudzi(d / wi.NAZOV_PLOCHA)
    ok, sprava = wi.vytvor_launcher_na_ploche(d)
    assert not ok and "nepremazávam" in sprava
    assert wi.zastupca_precitaj(d / wi.NAZOV_PLOCHA)["popis"] == "Cudzí zástupca"


def test_odinstalovanie_zmaze_len_nasich_zastupcov(izolacia):
    startup, sendto, desktop = izolacia / "startup", izolacia / "sendto", izolacia / "desktop"
    wi.nastav_po_prihlaseni(True, startup)
    wi.synchronizuj_odoslat_do([app("nc_editor", prijima=[".h"], ikona="nc_editor.png")], ["nc_editor"], sendto)
    wi.vytvor_launcher_na_ploche(desktop)
    wi.vytvor_na_ploche(app("lupa", prijima=["*"], ikona="lupa.png"), desktop)
    cudzi(desktop / "Moj vlastny.lnk")
    cudzi(sendto / "Dokumenty.lnk")
    (desktop / "poznamka.txt").write_text("nie je zástupca")

    zmazane = wi.odstran_zastupcov(startup, sendto, desktop)

    assert len(zmazane) == 4                                                    # Po spustení, Odoslať do, 2× plocha
    assert sorted(p.name for p in desktop.iterdir()) == ["Moj vlastny.lnk", "poznamka.txt"]
    assert [p.name for p in sendto.iterdir()] == ["Dokumenty.lnk"]
    assert list(startup.iterdir()) == []


def test_odinstalovanie_bez_zastupcov_nepadne(izolacia):
    assert wi.odstran_zastupcov(izolacia / "a", izolacia / "b", izolacia / "c") == []


# ---------- zostavenie (PyInstaller) ----------
def nacitaj_zostav():
    spec = importlib.util.spec_from_file_location("zostav", Path(__file__).resolve().parent.parent / "nastroje" / "zostav.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_prikaz_pyinstaller_ma_potrebne_volby(tmp_path):
    z = nacitaj_zostav()
    prikaz = z.prikaz_pyinstaller(tmp_path / "dist", tmp_path / "build", tmp_path / "x.ico")
    spolu = " ".join(prikaz)
    assert prikaz[1:3] == ["-m", "PyInstaller"]
    for volba in ("--onedir", "--windowed", "--noconfirm", "--collect-data sv_ttk", "--collect-all tkinterdnd2",
                  "--hidden-import pystray._win32", "--name nc_nastroje"):
        assert volba in spolu, volba
    assert "nc_nastroje/ikony" in spolu and "CO_JE_NOVE.md" in spolu           # dáta potrebné za behu
    assert prikaz[-1].endswith("vstup.py")
    assert Path(prikaz[-1]).is_file()


def test_vstupny_skript_a_modul_main_existuju():
    koren = Path(__file__).resolve().parent.parent
    assert (koren / "nastroje" / "vstup.py").is_file() and (koren / "nc_nastroje" / "__main__.py").is_file()
