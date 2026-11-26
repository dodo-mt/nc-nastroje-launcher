"""Testy hľadania zákaziek (zakazky.py). Falošný strom L: v tmp – nikdy skutočné L:."""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nc_nastroje import spustac, zakazky
from nc_nastroje.katalog import App
from nc_nastroje.zakazky import Dotaz, IndexZakaziek, Zhoda, normalizuj, vyhovuje


# ---------- normalizácia ----------
@pytest.mark.parametrize("vstup", ["21930", "OD21930", "od21930", "OD00021930", " 21930 ", "OD0021930", "21930-1A", "OD21930-1A_Op10"])
def test_nova_zakazka_sa_normalizuje_na_od_osem_cislic(vstup):
    assert normalizuj(vstup).nova == "OD00021930"


def test_cislo_do_sest_cislic_hlada_aj_stare_znacenie():
    d = normalizuj("21930")
    assert d.nova == "OD00021930" and d.stara == "021930"
    d = normalizuj("001252")
    assert d.nova == "OD00001252" and d.stara == "001252"
    assert normalizuj("1252").stara == "001252"


def test_siedmo_a_osemmiestne_cislo_je_len_nove():
    d = normalizuj("1234567")
    assert d.nova == "OD01234567" and d.stara is None
    d = normalizuj("00021930")
    assert d.nova == "OD00021930" and d.stara is None


def test_predpona_od_je_vzdy_nove_a_on_vzdy_stare():
    assert normalizuj("OD626") == Dotaz("OD626", "OD00000626", None, None)       # nie je to starý zákazník OD626
    d = normalizuj("ON001252")
    assert d.stara == "001252" and d.nova is None
    assert normalizuj("on1252").stara == "001252"


def test_stary_format_so_zakaznikom():
    for vstup in ("OD626\\001252", "OD626/001252", "od626 \\ 001252"):
        d = normalizuj(vstup)
        assert d.zakaznik.upper() == "OD626" and d.stara == "001252" and d.nova is None, vstup


def test_zakaznik_a_nova_zakazka():
    d = normalizuj("101270\\21930")
    assert d.zakaznik == "101270" and d.nova == "OD00021930" and d.stara == "021930"
    d = normalizuj("101270\\OD21930")
    assert d.nova == "OD00021930" and d.stara is None


@pytest.mark.parametrize("vstup", ["", "   ", "abc", "OD", "ON", "123456789", "\\", "101270\\", "OD626\\abc", "výkres"])
def test_neplatny_vstup(vstup):
    assert normalizuj(vstup) is None


def test_vyhovuje_je_zaciatok_nazvu_bez_dalsej_cislice():
    assert vyhovuje("101270-Meno firmy", "101270")
    assert vyhovuje("od00021930", "OD00021930")
    assert vyhovuje("OD00021930 popis", "OD00021930")
    assert not vyhovuje("OD000219301", "OD00021930")
    assert not vyhovuje("1012701-Firma", "101270")
    assert not vyhovuje("X101270", "101270")                     # nie je to začiatok


# ---------- strom L: ----------
def vytvor_strom(koren: Path):
    for rel in ("101270-Firma Alfa spol\\OD00021930\\21930-1A\\NC", "101270-Firma Alfa spol\\OD00021931",
                "100020-Beta AG\\OD00000626", "OD626\\001252", "OD626\\001253", "OD067\\001252", "OD067\\009712 popis",
                "_Nastroje\\x", "$RECYCLE.BIN\\y", "System Volume Information\\z"):
        (koren / rel.replace("\\", "/")).mkdir(parents=True)
    (koren / "povodny_subor.txt").write_text("nie je priečinok")


@pytest.fixture
def L(tmp_path):
    koren = tmp_path / "L"
    vytvor_strom(koren)
    return koren


@pytest.fixture
def idx(L, tmp_path):
    i = IndexZakaziek(L, tmp_path / "cache" / "zakazky.json")
    i.zostav()
    return i


def test_zostav_index_dvoch_urovni_bez_systemovych_priecinkov(idx):
    assert sorted(idx._zakaznici) == ["100020-Beta AG", "101270-Firma Alfa spol", "OD067", "OD626"]
    assert idx.pocet == 7
    assert idx._zakaznici["101270-Firma Alfa spol"] == ["OD00021930", "OD00021931"]   # len 2 úrovne, nie pozície


def test_nova_zakazka_je_pod_zakaznikom_s_menom(idx):
    zh = idx.najdi(normalizuj("21930"))
    assert zh == [Zhoda("101270-Firma Alfa spol", "OD00021930")]
    assert zh[0].rel == "101270-Firma Alfa spol\\OD00021930" and not zh[0].stara


def test_stara_zakazka_viac_zhod_su_vsetky_ponuknute(idx):
    zh = idx.najdi(normalizuj("001252"))
    assert [(z.zakaznik, z.zakazka) for z in zh] == [("OD067", "001252"), ("OD626", "001252")]
    assert all(z.stara for z in zh)


def test_stary_zakaznik_zuzi_vyber(idx):
    zh = idx.najdi(normalizuj("OD626\\001252"))
    assert zh == [Zhoda("OD626", "001252")]


def test_nove_a_stare_cislo_su_roznee_zakazky(idx):
    """OD626 = nová zákazka OD00000626 (u zákazníka 100020), nie starý zákazník OD626."""
    zh = idx.najdi(normalizuj("OD626"))
    assert zh == [Zhoda("100020-Beta AG", "OD00000626")]


def test_zakazka_s_textom_za_cislom(idx):
    assert idx.najdi(normalizuj("ON9712")) == [Zhoda("OD067", "009712 popis")]


def test_nic_nenajdene(idx):
    assert idx.najdi(normalizuj("99999")) == []


def test_nove_pred_starymi(tmp_path):
    koren = tmp_path / "L"
    for rel in ("OD100\\000626", "100020-Beta\\OD00000626"):
        (koren / rel.replace("\\", "/")).mkdir(parents=True)
    i = IndexZakaziek(koren, tmp_path / "c.json")
    i.zostav()
    zh = i.najdi(normalizuj("626"))
    assert [z.stara for z in zh] == [False, True]


# ---------- cache ----------
def test_cache_prezije_restart_a_nepotrebuje_siet(L, tmp_path):
    subor = tmp_path / "c.json"
    IndexZakaziek(L, subor).zostav()
    novy = IndexZakaziek(L, subor)                                  # nová inštancia číta len cache
    assert novy.pocet == 7 and novy.cas is not None
    assert novy.hladaj(normalizuj("21930"))


def test_cache_pre_iny_koren_sa_nepouzije(L, tmp_path):
    subor = tmp_path / "c.json"
    IndexZakaziek(L, subor).zostav()
    assert IndexZakaziek(tmp_path / "ina_L", subor).pocet == 0


def test_poskodena_cache_nezhodi(L, tmp_path):
    subor = tmp_path / "c.json"
    subor.write_text("{ rozbite", encoding="utf-8")
    assert IndexZakaziek(L, subor).pocet == 0
    subor.write_text(json.dumps({"format": 1, "koren": str(L), "zakaznici": "zle", "cas": "x"}), encoding="utf-8")
    assert IndexZakaziek(L, subor).pocet == 0


def test_zastaranie_indexu(idx):
    assert not idx.je_zastaraly()
    assert idx.je_zastaraly(datetime.now() + timedelta(days=1, minutes=1))
    assert IndexZakaziek(idx.koren, idx.subor.with_name("ina.json")).je_zastaraly()       # bez cache je zastaraný


def test_nedostupny_koren_nechaj_staru_cache(idx, tmp_path):
    pred = idx.pocet
    idx.koren = tmp_path / "neexistuje"
    with pytest.raises(OSError):
        idx.zostav()
    assert idx.pocet == pred


# ---------- priamy prechod ----------
def test_zakazka_vytvorena_po_indexe_sa_najde_priamym_prechodom(idx, L):
    (L / "101270-Firma Alfa spol" / "OD00021999").mkdir()           # vznikla po poslednom indexe
    d = normalizuj("21999")
    assert idx.hladaj(d) == []                                        # v cache ešte nie je
    zh = idx.najdi(d)
    assert zh == [Zhoda("101270-Firma Alfa spol", "OD00021999")]
    assert idx.hladaj(d) == zh                                        # cache sa doplnila
    assert IndexZakaziek(L, idx.subor).hladaj(d) == zh                # aj na disku


def test_priamy_prechod_pre_staru_zakazku_a_zuzenie_zakaznikom(idx, L):
    (L / "OD626" / "001777").mkdir()
    (L / "OD067" / "001777").mkdir()
    assert [z.zakaznik for z in idx.najdi(normalizuj("001777"))] == ["OD067", "OD626"]
    (L / "OD626" / "001888").mkdir()
    (L / "OD067" / "001888").mkdir()
    assert [z.zakaznik for z in idx.najdi(normalizuj("OD626\\001888"))] == ["OD626"]


def test_priamy_prechod_bez_cache_pouzije_vypis_korena(L, tmp_path):
    i = IndexZakaziek(L, tmp_path / "c.json")                        # index nikdy nebol postavený
    assert i.pocet == 0
    assert i.najdi(normalizuj("21930")) == [Zhoda("101270-Firma Alfa spol", "OD00021930")]
    assert i.pocet == 1


def test_priamy_prechod_nenajde_nic_a_nepadne(idx):
    assert idx.hladaj_priamo(normalizuj("55555")) == []


def test_priamy_prechod_nema_zapisovat_na_l(idx, L):
    pred = sorted(p.name for p in L.rglob("*"))
    idx.najdi(normalizuj("99999"))
    assert sorted(p.name for p in L.rglob("*")) == pred               # L: sa len číta


# ---------- Zhoda ----------
def test_zhoda_cesta_na_l_a_cesta_na_r_ma_zakaznika_len_ako_cislo(L):
    z = Zhoda("101270-Firma Alfa spol", "OD00021930")
    assert z.cesta(L) == L / "101270-Firma Alfa spol" / "OD00021930"
    r = Path("R:/")
    assert z.cesta_r(r) == r / "101270" / "OD00021930"                 # na R: je priečinok zákazníka len číslo (Triedič NC)


# ---------- Lupa ----------
def lupa(**kw):
    return App(id="lupa", nazov="Lupa", typ="web", url="file:///L:/_Lupa/index.html",
               url_hladat="{url}?q={text}", **kw)


def test_hladat_v_lupe_enkoduje_text(monkeypatch):
    otvorene = []
    monkeypatch.setattr(spustac.webbrowser, "open", otvorene.append)
    ok, _ = spustac.spusti_hladaj(lupa(), "OD626\\001252 a b")
    assert ok and otvorene == ["file:///L:/_Lupa/index.html?q=OD626%5C001252%20a%20b"]


def test_hladat_v_lupe_bez_url_hladat_otvori_lupu(monkeypatch):
    otvorene = []
    monkeypatch.setattr(spustac.webbrowser, "open", otvorene.append)
    app = lupa()
    app.url_hladat = ""
    assert spustac.spusti_hladaj(app, "x")[0] and otvorene == ["file:///L:/_Lupa/index.html"]


def test_hladat_v_newebovej_aplikacii_zlyha_cisto(monkeypatch):
    monkeypatch.setattr(spustac.webbrowser, "open", lambda u: pytest.fail("nemalo sa otvárať"))
    ok, sprava = spustac.spusti_hladaj(App(id="x", nazov="X", typ="exe", zdroj="x", spustit="x.exe"), "x")
    assert not ok and "webová" in sprava
