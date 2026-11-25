"""Nasadenie spoločnej šablóny výkresu na L:\\_Nastroje\\sablony (iba falošný koreň, nikdy skutočný L:)."""
import json
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

from nc_nastroje import publikovanie
from nc_nastroje.publikovanie import PublikaciaChyba, SABLONY_ID, publikuj_sablonu_vykresu
from nc_nastroje.spolocne import sablony_modul

sb = sablony_modul()


def vyrob_sablonu(priecinok: Path, oblast="A1:J30", logo=True) -> Path:
    priecinok.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    for adresa, text in sb.POVINNE_POPISY.items():
        ws[adresa] = text + ":"
    for z in sb.POVINNE_ZLUCENE:
        ws.merge_cells(z)
    for i, c in enumerate("ABCDEFGHIJ"):
        ws.column_dimensions[c].width = 10 + i
    ws.print_area = oblast
    wb.save(priecinok / sb.SUBOR_SABLONY)
    if logo:
        (priecinok / sb.SUBOR_LOGA).write_bytes(b"\x89PNG fake")
    return priecinok


@pytest.fixture
def koren(tmp_path):
    k = tmp_path / "L" / "_Nastroje"
    k.mkdir(parents=True)
    (k / "apps.json").write_text(json.dumps({"verzia_formatu": 1, "aplikacie": [
        {"id": "lupa", "nazov": "Lupa", "typ": "web", "url": "file:///x"},
        {"id": "editor", "nazov": "Editor", "typ": "exe", "verzia": "2026.11.24-1", "zdroj": "editor\2026.11.24-1",
         "spustit": "editor.exe"}]}), encoding="utf-8")
    return k


def test_nasadi_verziu_a_aktualna_a_nezmeni_apps_json(koren, tmp_path):
    apps_pred = (koren / "apps.json").read_text(encoding="utf-8")
    zdroj = vyrob_sablonu(tmp_path / "zdroj")
    v = publikuj_sablonu_vykresu(koren, zdroj)
    assert v["app_id"] == SABLONY_ID and v["subory"] == 2
    assert (koren / "sablony" / "aktualna.txt").read_text(encoding="utf-8").strip() == v["verzia"]
    assert (koren / "sablony" / v["verzia"] / sb.SUBOR_SABLONY).is_file()
    assert (koren / "apps.json").read_text(encoding="utf-8") == apps_pred          # katalóg aplikácií sa nedotkol
    assert not (koren / "apps.json.bak").exists()


def test_druhe_nasadenie_je_nova_verzia_a_stara_ostane(koren, tmp_path):
    zdroj = vyrob_sablonu(tmp_path / "zdroj")
    v1 = publikuj_sablonu_vykresu(koren, zdroj)
    v2 = publikuj_sablonu_vykresu(koren, zdroj)
    assert v1["verzia"] != v2["verzia"]
    assert (koren / "sablony" / v1["verzia"]).is_dir()
    assert (koren / "sablony" / "aktualna.txt").read_text(encoding="utf-8").strip() == v2["verzia"]


def test_chybna_sablona_sa_nenasadi(koren, tmp_path):
    zdroj = vyrob_sablonu(tmp_path / "zdroj", oblast="A1:J10")
    with pytest.raises(PublikaciaChyba) as e:
        publikuj_sablonu_vykresu(koren, zdroj)
    assert "Tlačová oblasť" in str(e.value)
    assert not (koren / "sablony").exists()


def test_chyba_ked_chyba_subor_alebo_priecinok(koren, tmp_path):
    with pytest.raises(PublikaciaChyba):
        publikuj_sablonu_vykresu(koren, tmp_path / "prazdny_priecinok")
    with pytest.raises(PublikaciaChyba):
        publikuj_sablonu_vykresu(tmp_path / "ziadny_koren", vyrob_sablonu(tmp_path / "zdroj"))


def test_prikaz_publikuj_sablony(koren, tmp_path, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("publikuj_skript", Path(__file__).resolve().parent.parent / "nastroje" / "publikuj.py")
    skript = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skript)
    zdroj = vyrob_sablonu(tmp_path / "zdroj")
    assert skript.main(["sablony", str(zdroj), "--koren", str(koren), "--ano"]) == 0
    vystup = capsys.readouterr().out
    assert "Hotovo: sablony" in vystup and "aktualna.txt" in vystup
    zly = vyrob_sablonu(tmp_path / "zly", oblast="A1:J5")
    assert skript.main(["sablony", str(zly), "--koren", str(koren), "--ano"]) == 1


def test_zostavenie_exe_zabali_spolocny_balik():
    import importlib.util
    spec = importlib.util.spec_from_file_location("zostav_skript", Path(__file__).resolve().parent.parent / "nastroje" / "zostav.py")
    z = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(z)
    prikaz = z.prikaz_pyinstaller(Path("dist"), Path("build"), Path("x.ico"))
    assert any(str(p).endswith("cnc vykresy spolocne") for p in prikaz)


# ---------- okno Súbor → Nasadiť aplikáciu… ----------
class FalosnePozadie:
    """Spúšťa prácu hneď (v teste nie je vlákno)."""

    def spusti(self, nazov, praca, po):
        po(praca(lambda *a, **k: None))


@pytest.fixture
def tk_root():
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk nie je dostupné")
    root.withdraw()
    yield root
    root.destroy()


def test_okno_ma_polozku_sablona_a_nasadi_ju(koren, tmp_path, tk_root, monkeypatch):
    from tkinter import messagebox
    from nc_nastroje.ui.nasadenie_okno import NAZOV_SABLONY, OknoNasadenia
    hotovo = []
    okno = OknoNasadenia(tk_root, koren, FalosnePozadie(), lambda: hotovo.append(1))
    tk_root.update()
    assert NAZOV_SABLONY in okno._vyber.cget("values")
    okno._app.set(NAZOV_SABLONY)
    okno._pri_zmene_vyberu()
    assert "šablónou" in okno._popis_buildu.cget("text")
    okno._build.set(str(vyrob_sablonu(tmp_path / "zdroj")))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    okno._nasad_klik()
    assert "šablóna výkresu" in okno._stav.cget("text") and hotovo
    assert (koren / "sablony" / "aktualna.txt").is_file()
    # aplikácia sa vráti k pôvodným popiskám
    okno._app.set(next(n for n in okno._vyber.cget("values") if n != NAZOV_SABLONY))
    okno._pri_zmene_vyberu()
    assert "buildu" in okno._popis_buildu.cget("text")
    okno.destroy()


def test_okno_chybna_sablona_ukaze_chybu_bez_zapisu(koren, tmp_path, tk_root, monkeypatch):
    from tkinter import messagebox
    from nc_nastroje.ui.nasadenie_okno import NAZOV_SABLONY, OknoNasadenia
    okno = OknoNasadenia(tk_root, koren, FalosnePozadie(), lambda: None)
    tk_root.update()
    okno._app.set(NAZOV_SABLONY)
    okno._build.set(str(vyrob_sablonu(tmp_path / "zdroj", oblast="A1:J3")))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    okno._nasad_klik()
    assert "aktualna.txt ostal nezmenený" in okno._stav.cget("text")
    assert not (koren / "sablony").exists()
    okno.destroy()
