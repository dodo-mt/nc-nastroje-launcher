"""Testy adaptérov stavov (stavy.py). Len falošné súbory v tmp, nikdy skutočné L:/R:."""
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nc_nastroje import stavy
from nc_nastroje.katalog import App
from nc_nastroje.stavy import Kontext, Stav

TERAZ = datetime(2026, 11, 24, 12, 0, 0)


def iso(dt):
    return dt.isoformat(timespec="seconds")


@pytest.fixture
def k(tmp_path):
    koren = tmp_path / "L"
    (koren / "_Nastroje").mkdir(parents=True)
    return Kontext(koren / "_Nastroje", koren, tmp_path / "R", tmp_path / "local", TERAZ)


def app_s(stav, **kw):
    return App(id=kw.pop("id", "x"), nazov="X", typ=kw.pop("typ", "python"), stav=stav, **kw)


def zapis(cesta: Path, data):
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(json.dumps(data), encoding="utf-8")


# ---------- pomocné ----------
def test_formatuj_cas():
    assert stavy.formatuj_cas(datetime(2026, 11, 24, 11, 32), TERAZ) == "dnes 11:32"
    assert stavy.formatuj_cas(datetime(2026, 11, 23, 9, 5), TERAZ) == "včera 09:05"
    assert stavy.formatuj_cas(datetime(2026, 11, 20, 9, 5), TERAZ) == "20.11. 09:05"
    assert stavy.formatuj_cas(datetime(2025, 12, 1, 9, 5), TERAZ) == "1.12. 2025 09:05"


def test_najhorsi():
    assert stavy.najhorsi([]) == "necinny"
    assert stavy.najhorsi(["ok", "upozornenie", "ok"]) == "upozornenie"
    assert stavy.najhorsi(["ok", "chyba", "upozornenie"]) == "chyba"
    assert stavy.najhorsi([Stav("ok"), Stav("nezname")]) == "nezname"
    assert stavy.najhorsi(["necinny", "ok"]) == "ok"


# ---------- subor_json ----------
def test_subor_json_ok(k):
    zapis(k.koren_nastrojov / "_stav" / "app" / "PC1.json", {
        "stav": "ok", "riadky": ["a", "b"], "cipy": [{"text": "MB65 A", "stav": "ok"}, {"text": "bez stavu"}],
        "cas": iso(TERAZ - timedelta(minutes=5)), "pocitac": "PC-PROG1"})
    s = stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\app"}), k)
    assert s.stav == "ok" and s.riadky == ["a", "b"] and s.pocitac == "PC-PROG1"
    assert s.cipy == [("MB65 A", "ok"), ("bez stavu", "nezname")]


def test_subor_json_stary_subor_je_nezname(k):
    zapis(k.koren_nastrojov / "_stav" / "app" / "PC1.json", {
        "stav": "ok", "cas": iso(TERAZ - timedelta(minutes=1441))})
    s = stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\app"}), k)
    assert s.stav == "nezname"


def test_subor_json_vlastny_max_vek(k):
    zapis(k.koren_nastrojov / "_stav" / "app" / "PC1.json", {"stav": "ok", "cas": iso(TERAZ - timedelta(minutes=30))})
    a = app_s({"adapter": "subor_json", "cesta": "_stav\\app", "max_vek_min": 10})
    assert stavy.precitaj_stav(a, k).stav == "nezname"


def test_subor_json_bez_casu_berie_mtime(k):
    p = k.koren_nastrojov / "_stav" / "app" / "PC1.json"
    zapis(p, {"stav": "chyba"})
    cas = time.mktime((TERAZ - timedelta(minutes=1)).timetuple())
    import os
    os.utime(p, (cas, cas))
    assert stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\app"}), k).stav == "chyba"


def test_subor_json_viac_pocitacov_najhorsi_stav_detaily_z_najnovsieho(k):
    d = k.koren_nastrojov / "_stav" / "app"
    zapis(d / "A.json", {"stav": "ok", "riadky": ["novy"], "cas": iso(TERAZ - timedelta(minutes=1))})
    zapis(d / "B.json", {"stav": "chyba", "riadky": ["starsi"], "cas": iso(TERAZ - timedelta(minutes=50))})
    zapis(d / "C.json", {"stav": "chyba", "cas": iso(TERAZ - timedelta(days=5))})   # zastaraný sa ignoruje
    s = stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\app"}), k)
    assert s.stav == "chyba" and s.riadky == ["novy"]


def test_subor_json_chybny_a_chybajuci(k):
    d = k.koren_nastrojov / "_stav" / "app"
    d.mkdir(parents=True)
    (d / "zly.json").write_text("{nie json", encoding="utf-8")
    (d / "pole.json").write_text("[1, 2]", encoding="utf-8")
    a = app_s({"adapter": "subor_json", "cesta": "_stav\\app"})
    assert stavy.precitaj_stav(a, k).stav == "nezname"
    assert stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\neexistuje"}), k).stav == "nezname"
    assert stavy.precitaj_stav(app_s({"adapter": "subor_json"}), k).stav == "nezname"


def test_subor_json_neznama_hodnota_stavu(k):
    zapis(k.koren_nastrojov / "_stav" / "app" / "A.json", {"stav": "super", "cas": iso(TERAZ)})
    assert stavy.precitaj_stav(app_s({"adapter": "subor_json", "cesta": "_stav\\app"}), k).stav == "nezname"


# ---------- tnc_sync ----------
def tnc_data(vysledok="OK", koniec=None, stroje=None, **beh):
    koniec = koniec or TERAZ - timedelta(hours=1)
    return {"format": 1, "pc": "PC-PROG1", "last_run": {
        "start": iso(koniec - timedelta(minutes=3)), "end": iso(koniec), "result": vysledok,
        "machines_ok": 5, "machines_total": 6, "errors": [], **beh}, "machines": stroje or {}}


def tnc_stav(k, data, stav=None):
    if data is not None:
        zapis(k.koren_l / "_tnc_sync" / "_tnc_sync_stav.json", data)
    return stavy.precitaj_stav(app_s({"adapter": "tnc_sync", **(stav or {})}), k)


def test_tnc_sync_ok(k):
    s = tnc_stav(k, tnc_data("OK"))
    assert s.stav == "ok" and s.text == "OK"
    assert s.riadky == ["Posledná záloha: dnes 11:00", "Stroje: 5 / 6"]
    assert s.pocitac == "PC-PROG1"


def test_tnc_sync_ok_s_upozornenim(k):
    s = tnc_stav(k, tnc_data("UPOZORNENIE"))
    assert s.stav == "upozornenie" and s.text == "OK s upozornením"


@pytest.mark.parametrize("vysledok,stav", [("CIASTOCNE", "upozornenie"), ("ZRUSENE", "upozornenie"),
                                           ("ZLYHALO", "chyba"), ("???", "nezname")])
def test_tnc_sync_ostatne_vysledky(k, vysledok, stav):
    assert tnc_stav(k, tnc_data(vysledok)).stav == stav


def test_tnc_sync_zaloha_nebezi(k):
    s = tnc_stav(k, tnc_data("OK", koniec=TERAZ - timedelta(days=2, hours=1)))
    assert s.stav == "chyba" and s.text == "Záloha nebeží"
    # presne na hrane (2 dni) ešte beží
    s = tnc_stav(k, tnc_data("OK", koniec=TERAZ - timedelta(days=2)))
    assert s.stav == "ok"


def test_tnc_sync_cipy_strojov(k):
    cerstve = iso(TERAZ - timedelta(hours=1))
    stroje = {
        "A": {"last_try": cerstve, "last_ok": cerstve},                                        # ok
        "B": {"last_try": cerstve, "last_ok": iso(TERAZ - timedelta(days=1))},                  # nedávny úspech
        "C": {"last_try": cerstve, "last_ok": iso(TERAZ - timedelta(days=10))},                 # dávno
        "D": {"last_try": cerstve},                                                             # nikdy
        "E": {},                                                                                # nič
    }
    s = tnc_stav(k, tnc_data("OK", stroje=stroje))
    assert s.cipy == [("A", "ok"), ("B", "upozornenie"), ("C", "chyba"), ("D", "chyba"), ("E", "nezname")]
    assert s.stav == "upozornenie"   # „OK“ s problémovým strojom sa zhorší


def test_tnc_sync_chybajuci_alebo_poskodeny_subor(k):
    assert tnc_stav(k, None).stav == "nezname"
    (k.koren_l / "_tnc_sync").mkdir(parents=True)
    (k.koren_l / "_tnc_sync" / "_tnc_sync_stav.json").write_text("{", encoding="utf-8")
    assert tnc_stav(k, None).stav == "nezname"


def test_tnc_sync_vlastna_cesta(k):
    zapis(k.koren_l / "inde" / "stav.json", tnc_data("ZLYHALO"))
    s = tnc_stav(k, None, {"cesta": "inde\\stav.json"})
    assert s.stav == "chyba"


# ---------- lupa_sken ----------
def lupa_app(**stav):
    return app_s({"adapter": "lupa_sken", **stav}, id="lupa", typ="web", url="file:///L:/_Lupa/index.html")


def lupa_zapis(k, vek, **data):
    zapis(k.koren_l / "_Lupa" / "lupa_scan.json",
          {"finished": (TERAZ - vek).timestamp(), "errors": 0, "full": False, **data})


def test_lupa_sken_ok_cesta_z_url(k):
    lupa_zapis(k, timedelta(hours=1))
    s = stavy.precitaj_stav(lupa_app(), k)
    assert s.stav == "ok"
    assert s.riadky == ["Posledný sken: dnes 11:00", "Inkrementálny sken · chýb: 0"]


def test_lupa_sken_stary_a_s_chybami(k):
    lupa_zapis(k, timedelta(hours=25))
    s = stavy.precitaj_stav(lupa_app(), k)
    assert s.stav == "upozornenie" and s.text == "Starý sken"
    lupa_zapis(k, timedelta(hours=1), errors=3, full=True)
    s = stavy.precitaj_stav(lupa_app(), k)
    assert s.stav == "upozornenie" and s.riadky[1] == "Úplný sken · chýb: 3"


def test_lupa_sken_chybajuci_subor_a_vlastna_cesta(k):
    assert stavy.precitaj_stav(lupa_app(), k).stav == "nezname"
    zapis(k.koren_l / "ina" / "lupa_scan.json", {"finished": (TERAZ - timedelta(hours=1)).timestamp()})
    assert stavy.precitaj_stav(lupa_app(cesta="ina"), k).stav == "ok"
    assert stavy.precitaj_stav(lupa_app(cesta="ina\\lupa_scan.json"), k).stav == "ok"


def test_lupa_sken_poskodeny_obsah(k):
    zapis(k.koren_l / "_Lupa" / "lupa_scan.json", {"finished": "zle"})
    assert stavy.precitaj_stav(lupa_app(), k).stav == "nezname"


def test_lupa_cesta_url_s_diakritikou_a_unc(k):
    a = App(id="l", nazov="L", typ="web", url="file:///L:/_Lupa%20x/index.html", stav={"adapter": "lupa_sken"})
    assert stavy._lupa_cesta(a, k) == k.koren_l / "_Lupa x" / "lupa_scan.json"
    a.url = "file://server/share/index.html"
    assert stavy._lupa_cesta(a, k) is None
    a.url = "https://example.com/lupa"
    assert stavy._lupa_cesta(a, k) is None


# ---------- proces ----------
def test_proces_bezi_a_nebezi(k, tmp_path):
    zdroj = k.koren_nastrojov / "moja_app" / "1.0"
    zdroj.mkdir(parents=True)
    skript = zdroj / "ciel.py"
    skript.write_text("import time; time.sleep(60)", encoding="utf-8")
    a = app_s({"adapter": "proces"}, id="moja_app", zdroj="moja_app\\1.0", spustit="ciel.py")
    assert stavy.precitaj_stav(a, k).stav == "necinny"
    p = subprocess.Popen([sys.executable, str(skript)])
    try:
        for _ in range(50):   # proces sa musí stihnúť objaviť
            if stavy.precitaj_stav(a, k).stav == "ok":
                break
            time.sleep(0.1)
        s = stavy.precitaj_stav(a, k)
        assert s.stav == "ok" and s.text == "Beží"
    finally:
        p.kill()
        p.wait()
    assert stavy.precitaj_stav(a, k).stav == "necinny"


def test_proces_webova_aplikacia_nebezi(k):
    assert stavy.precitaj_stav(app_s({"adapter": "proces"}, typ="web"), k).stav == "necinny"


# ---------- registrácia a odolnosť ----------
def test_bez_adaptera_a_neznamy_adapter(k):
    assert stavy.precitaj_stav(app_s({}), k) == Stav("necinny", "Pripravený")
    assert stavy.precitaj_stav(app_s({"adapter": "neexistuje"}), k).stav == "nezname"


def test_adapter_s_vynimkou_nezhodi_launcher(k, monkeypatch):
    def zly(app, kontext):
        raise RuntimeError("boom")
    monkeypatch.setitem(stavy.ADAPTERY, "zly", zly)
    s = stavy.precitaj_stav(app_s({"adapter": "zly"}), k)
    assert s.stav == "nezname"


def test_obnov_vsetko(k, monkeypatch):
    zapis(k.koren_l / "_Lupa" / "lupa_scan.json", {"finished": (TERAZ - timedelta(hours=1)).timestamp()})
    apps = [lupa_app(), app_s({}, id="bez"), app_s({"adapter": "neexistuje"}, id="zly")]
    v = stavy.obnov_vsetko(apps, k)
    assert v.stavy["lupa"].stav == "ok" and v.stavy["bez"].stav == "necinny" and v.stavy["zly"].stav == "nezname"
    assert v.l_ok is True and v.r_ok is False   # R: v teste neexistuje


def test_obnov_vsetko_timeout_nezablokuje(k, monkeypatch):
    def pomaly(app, kontext):
        time.sleep(1.0)
        return Stav("ok")
    monkeypatch.setitem(stavy.ADAPTERY, "pomaly", pomaly)
    a = app_s({"adapter": "pomaly"}, id="pomaly_app")
    t0 = time.monotonic()
    v = stavy.obnov_vsetko([a], k, timeout_s=0.1)
    assert time.monotonic() - t0 < 0.9
    assert v.stavy["pomaly_app"].stav == "nezname" and v.stavy["pomaly_app"].text == "Čas vypršal"
    time.sleep(1.1)   # visiaca úloha dobehne a pri ďalšom obnovení sa už použije výsledok
    assert stavy.obnov_vsetko([a], k, timeout_s=2).stavy["pomaly_app"].stav in ("ok", "nezname")
