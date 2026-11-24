"""Testy aktualizácií (aktualizacie.py). Všetko v tmp, nikdy skutočné L: ani %LOCALAPPDATA%."""
import json
from pathlib import Path

import pytest

from nc_nastroje import aktualizacie as ak
from nc_nastroje.katalog import App


# ---------- verzie ----------
def test_parsuj_verziu():
    assert ak.parsuj_verziu("2026.11.24-1") == (2026, 11, 24, 1)
    assert ak.parsuj_verziu("2026.1.5-12") == (2026, 1, 5, 12)
    for zle in ("", "2026.11.24", "v2026.11.24-1", "2026-11-24-1", "2026.11.24-x", None):
        assert ak.parsuj_verziu(zle) is None


def test_porovnanie_je_ciselne_nie_textove():
    assert ak.je_novsia("2026.11.24-10", "2026.11.24-9")        # „10“ > „9“ (textovo by to bolo naopak)
    assert ak.je_novsia("2026.12.01-1", "2026.11.30-5")
    assert ak.je_novsia("2027.01.01-1", "2026.12.31-9")
    assert not ak.je_novsia("2026.11.24-1", "2026.11.24-1")      # rovnaká
    assert not ak.je_novsia("2026.11.19-1", "2026.11.24-1")      # staršia
    assert ak.je_novsia("2026.11.24-1", None)                    # lokálne nič = novšia
    assert not ak.je_novsia("nezmysel", "2026.11.24-1")


def test_skrat_verziu():
    assert ak.skrat_verziu("2026.11.19-1", "2026.11.24-1") == "11.24-1"
    assert ak.skrat_verziu("2025.12.30-1", "2026.01.02-1") == "2026.01.02-1"


# ---------- kopírovanie ----------
def zostav(zdroj: Path, subory: dict[str, str]):
    for rel, obsah in subory.items():
        p = zdroj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(obsah, encoding="utf-8")


def test_kopiruj_verziu_cez_tmp(tmp_path):
    zdroj, dir_app = tmp_path / "L" / "app" / "v", tmp_path / "apps" / "app"
    zostav(zdroj, {"app.exe": "x" * 100, "dll/a.dll": "y" * 50})
    ciel = ak.kopiruj_verziu(zdroj, dir_app, "2026.11.24-1")
    assert ciel == dir_app / "2026.11.24-1"
    assert (ciel / "dll" / "a.dll").read_text() == "y" * 50
    assert not list(dir_app.glob("*.tmp"))
    assert zdroj.exists()                                         # zdroj sa nemení


def test_kopiruj_verziu_chybajuci_zdroj_nic_nezanecha(tmp_path):
    with pytest.raises(FileNotFoundError):
        ak.kopiruj_verziu(tmp_path / "neexistuje", tmp_path / "apps" / "app", "2026.11.24-1")
    assert not (tmp_path / "apps" / "app" / "2026.11.24-1").exists()


def test_kopiruj_verziu_nezhoda_velkosti_sa_nenainstaluje(tmp_path, monkeypatch):
    zdroj, dir_app = tmp_path / "zdroj", tmp_path / "apps" / "app"
    zostav(zdroj, {"a.exe": "abc"})
    povodna = ak._spocitaj
    volania = []

    def falosna(p):
        volania.append(p)
        n, v = povodna(p)
        return (n, v) if len(volania) == 1 else (n, v + 1)       # kópia „vyzerá“ väčšia
    monkeypatch.setattr(ak, "_spocitaj", falosna)
    with pytest.raises(OSError, match="nesedia"):
        ak.kopiruj_verziu(zdroj, dir_app, "2026.11.24-1")
    assert not list(dir_app.iterdir())                            # ani hotová verzia, ani .tmp


def test_kopiruj_verziu_prepise_zvysok_nedokonceneho_tmp(tmp_path):
    zdroj, dir_app = tmp_path / "zdroj", tmp_path / "apps" / "app"
    zostav(zdroj, {"a.exe": "abc"})
    zostav(dir_app / "2026.11.24-1.tmp", {"stary_odpad.txt": "x"})
    ciel = ak.kopiruj_verziu(zdroj, dir_app, "2026.11.24-1")
    assert [p.name for p in ciel.iterdir()] == ["a.exe"]


# ---------- lokálne verzie, ponechanie, návrat ----------
def nainstaluj(dir_app: Path, *verzie):
    for v in verzie:
        zostav(dir_app / v, {"app.exe": v})


def test_lokalne_verzie_ignoruju_tmp_a_cudzie(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.24-10", "2026.11.24-9", "2026.11.19-1")
    (d / "2026.11.30-1.tmp").mkdir()
    (d / "nieco").mkdir()
    (d / "poznamka.txt").write_text("x")
    assert ak.lokalne_verzie(d) == ["2026.11.19-1", "2026.11.24-9", "2026.11.24-10"]
    assert ak.lokalne_verzie(tmp_path / "neexistuje") == []


def test_vycisti_stare_ponecha_aktualnu_a_jednu_predchadzajucu(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.01-1", "2026.11.10-1", "2026.11.19-1", "2026.11.24-1")
    (d / "2026.11.30-1.tmp").mkdir()
    (d / "iny_priecinok").mkdir()                                 # cudzie sa nikdy nemažú
    ak.vycisti_stare(d)
    assert ak.lokalne_verzie(d) == ["2026.11.19-1", "2026.11.24-1"]
    assert not (d / "2026.11.30-1.tmp").exists() and (d / "iny_priecinok").exists()


def test_vycisti_stare_nezmaze_pripnutu(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.01-1", "2026.11.19-1", "2026.11.24-1")
    ak.pripni(d, "2026.11.01-1")
    ak.vycisti_stare(d)
    assert ak.lokalne_verzie(d) == ["2026.11.01-1", "2026.11.19-1", "2026.11.24-1"]   # pripnutá + 2 najnovšie
    assert ak.aktivna_verzia(d) == "2026.11.01-1"


def test_vycisti_stare_zamknuty_subor_nespadne(tmp_path, monkeypatch):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.01-1", "2026.11.19-1", "2026.11.24-1")

    def zamknute(*a, **k):
        raise PermissionError("beží")
    monkeypatch.setattr(ak.shutil, "rmtree", zamknute)
    ak.vycisti_stare(d)                                           # nesmie vyhodiť výnimku
    assert "2026.11.01-1" in ak.lokalne_verzie(d)


def test_navrat_na_predchadzajucu_a_spat(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.19-1", "2026.11.24-1")
    assert ak.aktivna_verzia(d) == "2026.11.24-1"
    assert ak.predchadzajuca_verzia(d) == "2026.11.19-1"
    ak.pripni(d, "2026.11.19-1")
    assert ak.aktivna_verzia(d) == "2026.11.19-1"
    assert ak.predchadzajuca_verzia(d) is None                    # staršia už nie je
    ak.odpni(d)
    assert ak.aktivna_verzia(d) == "2026.11.24-1"


def test_pripni_nenainstalovanu_verziu_nejde(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.24-1")
    with pytest.raises(ValueError):
        ak.pripni(d, "2026.11.01-1")


def test_pripnuta_verzia_ktora_zmizla_sa_ignoruje(tmp_path):
    d = tmp_path / "app"
    nainstaluj(d, "2026.11.24-1")
    (d / ak.PRIPNUTA).write_text("2026.01.01-1")
    assert ak.aktivna_verzia(d) == "2026.11.24-1"


def test_priecinok_aktivnej(tmp_path):
    nainstaluj(tmp_path / "x", "2026.11.24-1")
    assert ak.priecinok_aktivnej("x", tmp_path) == tmp_path / "x" / "2026.11.24-1"
    assert ak.priecinok_aktivnej("ina", tmp_path) is None


# ---------- aktualizácia aplikácií ----------
@pytest.fixture
def prostredie(tmp_path):
    koren, apps_dir = tmp_path / "L" / "_Nastroje", tmp_path / "local" / "apps"
    zostav(koren / "nl" / "2026.11.19-1", {"nl.exe": "stara"})
    zostav(koren / "nl" / "2026.11.24-1", {"nl.exe": "nova", "lib/x.dll": "d"})
    zostav(koren / "nl", {"CO_JE_NOVE.md": "# Čo je nové\n- opravy"})
    app = App(id="nl", nazov="Nástrojový list", typ="exe", verzia="2026.11.24-1", zdroj="nl\\2026.11.24-1",
              spustit="nl.exe", co_je_nove="nl\\CO_JE_NOVE.md")
    return koren, apps_dir, app


def test_prvy_start_skopiruje_aktualnu_verziu(prostredie):
    koren, apps_dir, app = prostredie
    caka = {}
    v = ak.aktualizuj_aplikacie([app], koren, lambda a: False, caka, apps_dir)
    assert v["nl"].stav == "aktualna" and v["nl"].lokalna == "2026.11.24-1"
    assert (apps_dir / "nl" / "2026.11.24-1" / "lib" / "x.dll").exists()
    assert "opravy" in ak.precitaj_co_je_nove("nl", apps_dir)
    assert caka == {}


def test_nova_verzia_sa_skopiruje_a_stara_ostane_ako_predchadzajuca(prostredie):
    koren, apps_dir, app = prostredie
    zostav(apps_dir / "nl" / "2026.11.19-1", {"nl.exe": "stara"})          # už nainštalovaná stará verzia
    priebeh = []
    v = ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir,
                                pri_priebehu=lambda i, s: priebeh.append((i, s.stav)))
    assert priebeh == [("nl", "kopiruje")]
    assert v["nl"].stav == "aktualna"
    assert ak.lokalne_verzie(apps_dir / "nl") == ["2026.11.19-1", "2026.11.24-1"]
    assert ak.predchadzajuca_verzia(apps_dir / "nl") == "2026.11.19-1"


def test_bezi_nova_verzia_caka_na_dalsie_spustenie(prostredie):
    koren, apps_dir, app = prostredie
    zostav(apps_dir / "nl" / "2026.11.19-1", {"nl.exe": "stara"})
    caka, bezi = {}, {"nl": True}
    v = ak.aktualizuj_aplikacie([app], koren, lambda a: bezi[a.id], caka, apps_dir)
    assert v["nl"].stav == "caka" and v["nl"].stara == "2026.11.19-1" and v["nl"].lokalna == "2026.11.24-1"
    assert caka == {"nl": "2026.11.19-1"}
    # ďalší cyklus: stále beží -> stále čaká a nekopíruje znova
    assert ak.aktualizuj_aplikacie([app], koren, lambda a: True, caka, apps_dir)["nl"].stav == "caka"
    # aplikácia sa zavrela -> hotovo
    bezi["nl"] = False
    assert ak.aktualizuj_aplikacie([app], koren, lambda a: False, caka, apps_dir)["nl"].stav == "aktualna"
    assert caka == {}


def test_novsia_verzia_zrusi_navrat_na_predchadzajucu(prostredie):
    koren, apps_dir, app = prostredie
    zostav(apps_dir / "nl" / "2026.11.19-1", {"nl.exe": "stara"})
    zostav(apps_dir / "nl" / "2026.11.20-1", {"nl.exe": "stredna"})
    ak.pripni(apps_dir / "nl", "2026.11.19-1")
    ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir)
    assert ak.aktivna_verzia(apps_dir / "nl") == "2026.11.24-1"


def test_navrat_na_staru_verziu_prezije_kontrolu_ked_nie_je_nic_nove(prostredie):
    koren, apps_dir, app = prostredie
    ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir)       # nainštaluje 11.24-1
    zostav(apps_dir / "nl" / "2026.11.19-1", {"nl.exe": "stara"})
    ak.pripni(apps_dir / "nl", "2026.11.19-1")
    v = ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir)
    assert v["nl"].stav == "aktualna" and v["nl"].lokalna == "2026.11.19-1"   # používateľ sa vrátil, nenúti sa


def test_chybajuci_zdroj_na_l_je_chyba_ale_nespadne(prostredie):
    koren, apps_dir, app = prostredie
    app.verzia, app.zdroj = "2026.12.01-1", "nl\\2026.12.01-1"                # publikovaná, ale priečinok chýba
    v = ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir)
    assert v["nl"].stav == "chyba" and "zlyhalo" in v["nl"].sprava
    assert not (apps_dir / "nl" / "2026.12.01-1").exists()


def test_neplatna_verzia_v_apps_json_je_chyba(prostredie):
    koren, apps_dir, app = prostredie
    app.verzia = "dnes"
    assert ak.aktualizuj_aplikacie([app], koren, lambda a: False, {}, apps_dir)["nl"].stav == "chyba"


def test_zla_aplikacia_nezastavi_ostatne(prostredie):
    koren, apps_dir, app = prostredie
    zla = App(id="zla", nazov="Zlá", typ="exe", verzia="2026.11.24-1", zdroj="zla\\x", spustit="z.exe")
    web = App(id="lupa", nazov="Lupa", typ="web", url="file:///x")
    v = ak.aktualizuj_aplikacie([zla, web, app], koren, lambda a: False, {}, apps_dir)
    assert v["zla"].stav == "chyba" and v["nl"].stav == "aktualna" and "lupa" not in v


def test_vyjatok_v_bezi_nezhodi_aktualizaciu(prostredie):
    koren, apps_dir, app = prostredie
    zostav(apps_dir / "nl" / "2026.11.19-1", {"nl.exe": "stara"})

    def zle(a):
        raise RuntimeError("psutil")
    v = ak.aktualizuj_aplikacie([app], koren, zle, {}, apps_dir)
    assert v["nl"].stav == "chyba"


# ---------- katalóg s cache ----------
APPS = {"verzia_formatu": 1, "aplikacie": [
    {"id": "a", "nazov": "A", "typ": "exe", "zdroj": "a\\1", "spustit": "a.exe", "verzia": "2026.11.24-1"}],
    "launcher": {"verzia": "2026.11.24-3", "zdroj": "launcher\\2026.11.24-3", "spustit": "nc_nastroje.exe"}}


def zapis_apps(koren: Path, data=None, text=None):
    koren.mkdir(parents=True, exist_ok=True)
    (koren / "apps.json").write_text(text if text is not None else json.dumps(data or APPS), encoding="utf-8")


def test_katalog_zo_siete_ulozi_cache(tmp_path):
    koren, cache = tmp_path / "L", tmp_path / "cache"
    zapis_apps(koren)
    k = ak.nacitaj_katalog_s_cache(koren, cache)
    assert k.zdroj == "siet" and [a.id for a in k.apps] == ["a"]
    assert k.launcher["verzia"] == "2026.11.24-3"
    assert (cache / "apps.json").exists()


def test_l_nedostupny_pouzije_cache(tmp_path):
    koren, cache = tmp_path / "L", tmp_path / "cache"
    zapis_apps(koren)
    ak.nacitaj_katalog_s_cache(koren, cache)
    (koren / "apps.json").unlink()                                 # L: „zmizol“
    k = ak.nacitaj_katalog_s_cache(koren, cache)
    assert k.zdroj == "cache" and [a.id for a in k.apps] == ["a"]


def test_poskodeny_apps_json_pouzije_cache_a_cache_sa_neprepise(tmp_path):
    koren, cache = tmp_path / "L", tmp_path / "cache"
    zapis_apps(koren)
    ak.nacitaj_katalog_s_cache(koren, cache)
    zapis_apps(koren, text="{ rozbite")
    k = ak.nacitaj_katalog_s_cache(koren, cache)
    assert k.zdroj == "cache" and len(k.apps) == 1
    assert json.loads((cache / "apps.json").read_text(encoding="utf-8"))["aplikacie"][0]["id"] == "a"


def test_cache_pre_iny_koren_sa_nepouzije(tmp_path):
    cache = tmp_path / "cache"
    zapis_apps(tmp_path / "L1")
    ak.nacitaj_katalog_s_cache(tmp_path / "L1", cache)
    k = ak.nacitaj_katalog_s_cache(tmp_path / "L2_neexistuje", cache)
    assert k.zdroj == "ziadny" and k.apps == [] and k.chyby


def test_len_cache_nesiaha_na_siet(tmp_path):
    koren, cache = tmp_path / "L", tmp_path / "cache"
    zapis_apps(koren)
    assert ak.nacitaj_katalog_s_cache(koren, cache, len_cache=True).zdroj == "ziadny"   # cache ešte nie je
    ak.nacitaj_katalog_s_cache(koren, cache)
    assert ak.nacitaj_katalog_s_cache(koren, cache, len_cache=True).zdroj == "cache"


def test_chybny_zaznam_v_katalogu_neprekaza(tmp_path):
    data = {"aplikacie": [APPS["aplikacie"][0], {"id": "zle"}]}
    zapis_apps(tmp_path / "L", data)
    k = ak.nacitaj_katalog_s_cache(tmp_path / "L", tmp_path / "cache")
    assert [a.id for a in k.apps] == ["a"] and len(k.chyby) == 1 and k.launcher is None


# ---------- launcher ----------
def test_launcher_novsia_verzia_sa_stiahne(tmp_path):
    koren, ldir = tmp_path / "L", tmp_path / "local" / "launcher"
    zostav(koren / "launcher" / "2026.11.24-3", {"nc_nastroje.exe": "exe"})
    zostav(koren / "launcher", {"CO_JE_NOVE.md": "novinky"})
    info = {"verzia": "2026.11.24-3", "zdroj": "launcher\\2026.11.24-3", "spustit": "nc_nastroje.exe",
            "co_je_nove": "launcher\\CO_JE_NOVE.md"}
    r = ak.aktualizuj_launcher(info, koren, "2026.11.24-1", ldir)
    assert r.stav == "pripraveny" and r.verzia == "2026.11.24-3" and r.co_je_nove == "novinky"
    assert (r.adresar / "nc_nastroje.exe").exists() and r.adresar == ldir / "2026.11.24-3"


def test_launcher_rovnaka_alebo_chyba_info_nic_nerobi(tmp_path):
    info = {"verzia": "2026.11.24-1", "zdroj": "x", "spustit": "", "co_je_nove": ""}
    assert ak.aktualizuj_launcher(info, tmp_path, "2026.11.24-1", tmp_path / "l").stav == "aktualny"
    assert ak.aktualizuj_launcher(None, tmp_path, "2026.11.24-1", tmp_path / "l").stav == "aktualny"
    assert not (tmp_path / "l").exists()


def test_launcher_chybajuci_zdroj_je_chyba(tmp_path):
    info = {"verzia": "2026.12.01-1", "zdroj": "launcher\\2026.12.01-1", "spustit": "", "co_je_nove": ""}
    r = ak.aktualizuj_launcher(info, tmp_path, "2026.11.24-1", tmp_path / "l")
    assert r.stav == "chyba" and r.adresar is None


def test_aktualizator_bat(tmp_path):
    text = ak.zostav_aktualizator(4321, tmp_path / "launcher" / "2026.11.24-3", "nc_nastroje.exe",
                                  "2026.11.24-3", tmp_path / "launcher")
    riadky = text.split("\r\n")
    assert any('"PID eq 4321"' in r for r in riadky)                 # čaká na ukončenie PID
    assert any(r.startswith(">") and "aktualna.txt" in r and r.endswith("echo 2026.11.24-3") for r in riadky)
    assert any(r.startswith("start") and "nc_nastroje.exe" in r for r in riadky)
    assert text.index("PID eq") < text.index("aktualna.txt") < text.index("start ")   # najprv počkať, potom prepnúť
