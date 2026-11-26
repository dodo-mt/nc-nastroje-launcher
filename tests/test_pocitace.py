"""Prehľad počítačov: záznam o počítači, zápis a čítanie súborov na L:, stavy buniek, okno."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nc_nastroje import pocitace
from nc_nastroje.katalog import App

TERAZ = datetime(2026, 11, 26, 15, 0, 0)
APPS = [App(id="nc_editor", nazov="NC Editor", typ="exe", verzia="2026.11.26-13", zdroj="nc_editor\\2026.11.26-13"),
        App(id="triedic_nc", nazov="Triedič NC", typ="exe", verzia="2026.11.24-3", zdroj="triedic_nc\\2026.11.24-3"),
        App(id="lupa", nazov="Lupa", typ="web", url="file:///x"),
        App(id="tnc_sync", nazov="TNC Sync", typ="exe", verzia="2026.11.24-1", zdroj="tnc_sync\\2026.11.24-1")]


def nainstaluj(local_dir, app_id, *verzie):
    for v in verzie:
        (local_dir / "apps" / app_id / v).mkdir(parents=True)


def test_zostav_zaznam(tmp_path):
    nainstaluj(tmp_path, "nc_editor", "2026.11.24-8", "2026.11.26-13")
    nainstaluj(tmp_path, "triedic_nc", "2026.11.24-3")
    z = pocitace.zostav(APPS, tmp_path, "2026.11.26-1", "prezeranie", TERAZ, bezi={"nc_editor": "2026.11.24-8"})
    assert z["launcher"] == "2026.11.26-1" and z["rezim"] == "prezeranie" and z["cas"] == "2026-11-26T15:00:00"
    por = {e["id"]: e for e in z["aplikacie"]}
    assert set(por) == {"nc_editor", "triedic_nc", "tnc_sync"}                     # web aplikácia sa nezapisuje
    assert por["nc_editor"]["nainstalovana"] == "2026.11.26-13" and por["nc_editor"]["bezi_verzia"] == "2026.11.24-8"
    assert por["nc_editor"]["bezi"] is True and por["triedic_nc"]["bezi"] is False
    assert por["tnc_sync"]["nainstalovana"] == ""                                  # nenainštalovaná


def test_zapis_a_nacitanie(tmp_path):
    koren = tmp_path / "L"
    z = pocitace.zostav(APPS, tmp_path / "local", "2026.11.26-1", "plny", TERAZ, bezi={})
    z["pocitac"] = "PC-A"
    cesta = pocitace.zapis(koren, z)
    assert cesta == koren / "_stav" / "_pocitace" / "PC-A.json" and not list(cesta.parent.glob("*.tmp"))
    z2 = {**z, "pocitac": "pc-b", "cas": (TERAZ - timedelta(days=3)).isoformat(timespec="seconds")}
    pocitace.zapis(koren, z2)
    (cesta.parent / "pokazeny.json").write_text("{nie json", encoding="utf-8")
    (cesta.parent / "stary.json").write_text(json.dumps({**z, "pocitac": "STARY", "cas": "2025-01-01T00:00:00"}),
                                             encoding="utf-8")
    (cesta.parent / "bezcasu.json").write_text(json.dumps({"pocitac": "X", "aplikacie": []}), encoding="utf-8")
    nacitane = pocitace.nacitaj(koren, TERAZ)
    assert [p["pocitac"] for p in nacitane] == ["PC-A", "pc-b"]                    # poškodené a staré sa preskočia
    assert not pocitace.neozval_sa(nacitane[0], TERAZ) and pocitace.neozval_sa(nacitane[1], TERAZ)
    assert pocitace.nacitaj(tmp_path / "neexistuje", TERAZ) == []


def test_bunka_aplikacie():
    e = {"id": "x", "nainstalovana": "2026.11.26-13", "bezi": False, "bezi_verzia": ""}
    assert pocitace.stav_aplikacie(e, "2026.11.26-13") == ("ok", "2026.11.26-13")
    assert pocitace.stav_aplikacie({**e, "bezi": True, "bezi_verzia": "2026.11.26-13"}, "2026.11.26-13")[1].endswith("beží")
    stav, text = pocitace.stav_aplikacie({**e, "bezi": True, "bezi_verzia": "2026.11.24-8"}, "2026.11.26-13")
    assert stav == "upozornenie" and "beží" in text and "treba" not in text
    assert pocitace.stav_aplikacie(e, "2026.11.27-1")[0] == "nova_verzia"           # na L: je novšia než lokálna
    assert pocitace.stav_aplikacie({**e, "nainstalovana": ""}, "2026.11.26-13") == ("necinny", "—")
    assert pocitace.stav_aplikacie(None, "2026.11.26-13") == ("necinny", "—")
    # beží stará a zároveň čaká novšia z L: -> oranžová (najprv treba zavrieť)
    assert pocitace.stav_aplikacie({**e, "bezi": True, "bezi_verzia": "2026.11.24-8"}, "2026.11.27-1")[0] == "upozornenie"


def test_bunka_launchera():
    assert pocitace.stav_launchera("2026.11.26-1", "2026.11.26-1")[0] == "ok"
    assert pocitace.stav_launchera("2026.11.25-35", "2026.11.26-1")[0] == "nova_verzia"
    assert pocitace.stav_launchera("", "2026.11.26-1")[0] == "necinny"


def test_pocet_starych():
    def zaznam(den, bezi_v):
        e = {"id": "nc_editor", "nainstalovana": "2026.11.26-13", "bezi": True, "bezi_verzia": bezi_v}
        return {"pocitac": "A", "_cas": TERAZ - timedelta(days=den), "aplikacie": [e]}
    katalog = {"nc_editor": "2026.11.26-13"}
    assert pocitace.pocet_starych([zaznam(0, "2026.11.24-8"), zaznam(0, "2026.11.26-13"), zaznam(5, "2026.11.24-8")],
                                  katalog, TERAZ) == 1           # neozvaný počítač sa nepočíta


def test_bezi_verzie_podla_cesty_procesu(tmp_path, monkeypatch):
    local = tmp_path / "NC_Nastroje"

    class P:
        def __init__(self, exe, cmd=()):
            self.info = {"exe": str(exe), "cmdline": list(cmd)}

    procesy = [P(local / "apps" / "nc_editor" / "2026.11.24-8" / "NCEditor.exe"),
               P(local / "apps" / "nc_editor" / "2026.11.26-13" / "NCEditor.exe"),
               P(local / "apps" / "triedic_nc" / "2026.11.24-3" / "Triedic.exe"),
               P(tmp_path / "ina" / "x.exe"), P(local / "apps" / "neznama" / "2026.11.24-3" / "a.exe"),
               P(local / "apps" / "tnc_sync" / "nie_verzia" / "a.exe")]
    monkeypatch.setattr(pocitace.psutil, "process_iter", lambda attrs=None: iter(procesy))
    v = pocitace.bezi_verzie(local, ["nc_editor", "triedic_nc", "tnc_sync"])
    assert v == {"nc_editor": "2026.11.26-13", "triedic_nc": "2026.11.24-3"}      # pri viacerých verziách novšia


def test_okno_prehladu(tmp_path):
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("bez displeja")
    from nc_nastroje.ui.pocitace_okno import PocitaceOkno
    koren = tmp_path / "L"
    z = pocitace.zostav(APPS, tmp_path / "local", "2026.11.26-1", "plny", datetime.now(),
                        bezi={"nc_editor": "2026.11.24-8"})
    nainstaluj(tmp_path / "local", "nc_editor", "2026.11.26-13")
    z = pocitace.zostav(APPS, tmp_path / "local", "2026.11.26-1", "plny", datetime.now(),
                        bezi={"nc_editor": "2026.11.24-8"})
    z["pocitac"] = "PC-A"
    pocitace.zapis(koren, z)

    class SynchronnePozadie:
        def spusti(self, kluc, praca, pri_vysledku=None, pri_priebehu=None):
            pri_vysledku(praca(lambda x: None))

    try:
        okno = PocitaceOkno(root, koren, SynchronnePozadie(), lambda: (APPS, "2026.11.26-1"))
        root.update()
        texty = [w.cget("text") for w in okno._telo.winfo_children() if isinstance(w, tk.Label)]
        assert any("PC-A" in t for t in texty) and any("beží" in t for t in texty)
        assert "1 počítačov" in okno._pata.cget("text") and "starú verziu" in okno._pata.cget("text")
        okno.destroy()
        okno2 = PocitaceOkno(root, tmp_path / "prazdny", SynchronnePozadie(), lambda: (APPS, ""))
        root.update()
        assert "neozval žiadny počítač" in [w.cget("text") for w in okno2._telo.winfo_children()][0]
    finally:
        root.destroy()
