"""Testy publikovania (nastroje/publikuj.py) – len falošný koreň v tmp."""
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

SKRIPT = Path(__file__).resolve().parent.parent / "nastroje" / "publikuj.py"
spec = importlib.util.spec_from_file_location("publikuj", SKRIPT)
publikuj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publikuj)

DNES = date(2026, 11, 24)


@pytest.fixture
def koren(tmp_path):
    k = tmp_path / "L" / "_Nastroje"
    k.mkdir(parents=True)
    apps = {"verzia_formatu": 1, "vlastny_kluc": {"zachovat": True}, "aplikacie": [
        {"id": "nl", "nazov": "Nástrojový list", "typ": "exe", "verzia": "2026.11.19-1",
         "zdroj": "nl\\2026.11.19-1", "spustit": "nl.exe", "neznamy_kluc": 5},
        {"id": "lupa", "nazov": "Lupa", "typ": "web", "url": "file:///x"}],
        "launcher": {"verzia": "2026.11.19-1", "zdroj": "launcher\\2026.11.19-1", "spustit": "nc_nastroje.exe"}}
    (k / "apps.json").write_text(json.dumps(apps, ensure_ascii=False, indent=2), encoding="utf-8")
    return k


@pytest.fixture
def build(tmp_path):
    b = tmp_path / "build"
    (b / "lib").mkdir(parents=True)
    (b / "nl.exe").write_text("exe" * 100)
    (b / "lib" / "a.dll").write_text("dll")
    (b / "CO_JE_NOVE.md").write_text("# nové")
    return b


def apps_json(koren):
    return json.loads((koren / "apps.json").read_text(encoding="utf-8"))


def test_publikovanie_skopiruje_a_zapise_verziu(koren, build):
    v = publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    assert v["verzia"] == "2026.11.24-1" and v["subory"] == 3
    assert (koren / "nl" / "2026.11.24-1" / "lib" / "a.dll").read_text() == "dll"
    zaznam = apps_json(koren)["aplikacie"][0]
    assert zaznam["verzia"] == "2026.11.24-1" and zaznam["zdroj"] == "nl\\2026.11.24-1"
    assert (koren / "nl" / "CO_JE_NOVE.md").read_text() == "# nové"
    assert not list((koren / "nl").glob("*.tmp"))


def test_zalohuje_a_zachova_ostatne_kluce(koren, build):
    povodny = (koren / "apps.json").read_text(encoding="utf-8")
    publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    assert (koren / "apps.json.bak").read_text(encoding="utf-8") == povodny      # záloha pôvodného
    novy = apps_json(koren)
    assert novy["vlastny_kluc"] == {"zachovat": True}
    assert novy["aplikacie"][0]["neznamy_kluc"] == 5
    assert novy["aplikacie"][1]["id"] == "lupa" and novy["launcher"]["verzia"] == "2026.11.19-1"
    assert not (koren / "apps.json.tmp").exists()


def test_automaticka_verzia_zvysuje_poradie(koren, build):
    v1 = publikuj.publikuj(koren, "nl", build, dnes=DNES)
    v2 = publikuj.publikuj(koren, "nl", build, dnes=DNES)
    assert v1["verzia"] == "2026.11.24-1" and v2["verzia"] == "2026.11.24-2"


def test_dalsia_verzia():
    d = publikuj.dalsia_verzia
    assert d([], DNES) == "2026.11.24-1"
    assert d(["2026.11.24-9", "2026.11.24-10", "2026.11.23-50"], DNES) == "2026.11.24-11"   # číselne, nie textovo
    assert d(["2026.11.19-1", "nezmysel", ""], DNES) == "2026.11.24-1"


@pytest.fixture
def build_launchera(build):
    (build / "nc_nastroje.exe").write_text("launcher")
    return build


def test_publikuje_launcher(koren, build_launchera):
    v = publikuj.publikuj(koren, "launcher", build_launchera, "2026.11.24-3")
    assert apps_json(koren)["launcher"] == {"verzia": "2026.11.24-3", "zdroj": "launcher\\2026.11.24-3",
                                            "spustit": "nc_nastroje.exe"}
    assert (v["cielovy"] / "nc_nastroje.exe").exists()


def test_launcher_berie_verziu_z_verzia_txt(koren, build_launchera):
    """Verzia v apps.json musí sedieť s verziou v exe, inak by sa aktualizácia launchera opakovala."""
    (build_launchera / "verzia.txt").write_text("2026.11.24-8\n", encoding="utf-8")
    v = publikuj.publikuj(koren, "launcher", build_launchera)               # bez --verzia
    assert v["verzia"] == "2026.11.24-8" and apps_json(koren)["launcher"]["verzia"] == "2026.11.24-8"


def test_launcher_nezhoda_verzie_s_verzia_txt_sa_odmietne(koren, build_launchera):
    (build_launchera / "verzia.txt").write_text("2026.11.24-8\n", encoding="utf-8")
    pred = (koren / "apps.json").read_text(encoding="utf-8")
    with pytest.raises(publikuj.PublikaciaChyba, match="nesedí s verzia.txt"):
        publikuj.publikuj(koren, "launcher", build_launchera, "2026.11.25-1")
    assert (koren / "apps.json").read_text(encoding="utf-8") == pred
    publikuj.publikuj(koren, "launcher", build_launchera, "2026.11.24-8")      # rovnaká verzia je v poriadku


def test_launcher_bez_verzia_txt_vyzaduje_verziu(koren, build_launchera):
    with pytest.raises(publikuj.PublikaciaChyba, match="verzia.txt"):
        publikuj.publikuj(koren, "launcher", build_launchera)


def test_launcher_bez_exe_sa_odmietne(koren, build):
    with pytest.raises(publikuj.PublikaciaChyba, match="nc_nastroje.exe"):
        publikuj.publikuj(koren, "launcher", build, "2026.11.24-3")


def test_instalator_pre_kolegov_sa_zapise_len_pri_launcheri(koren, build_launchera):
    publikuj.publikuj(koren, "nl", build_launchera, "2026.11.24-1")
    assert not (koren / publikuj.INSTALATOR).exists()
    v = publikuj.publikuj(koren, "launcher", build_launchera, "2026.11.24-3")
    assert v["instalator"] == koren / publikuj.INSTALATOR
    text = (koren / publikuj.INSTALATOR).read_text(encoding="utf-8")
    assert 'set "VERZIA=2026.11.24-3"' in text
    # nová verzia prepíše zapečenú verziu v inštalátore
    (build_launchera / "nc_nastroje.exe").write_text("novy")
    publikuj.publikuj(koren, "launcher", build_launchera, "2026.11.24-4")
    assert 'set "VERZIA=2026.11.24-4"' in (koren / publikuj.INSTALATOR).read_text(encoding="utf-8")


def test_text_instalatora():
    riadky = publikuj.text_instalatora("2026.11.24-8").split("\r\n")
    assert 'set "VERZIA=2026.11.24-8"' in riadky
    assert any(r.startswith("robocopy") and "/E" in r for r in riadky)             # kópia z L: do %LOCALAPPDATA%
    assert any("aktualna.txt" in r and r.startswith(">") for r in riadky)          # štartér potom pozná verziu
    assert any(r.startswith("start") and "--prve-spustenie" in r for r in riadky)
    assert any(r == "if errorlevel 8 goto chyba" for r in riadky)                  # robocopy: 8+ = chyba
    assert riadky.index("if errorlevel 8 goto chyba") < next(i for i, r in enumerate(riadky) if "aktualna.txt" in r)
    assert "%LOCALAPPDATA%\\NC_Nastroje\\launcher" in "\n".join(riadky)


@pytest.mark.parametrize("app_id,sprava", [("neznama", "nie je v apps.json"), ("lupa", "webová")])
def test_nezname_a_webove_aplikacie_sa_odmietnu(koren, build, app_id, sprava):
    with pytest.raises(publikuj.PublikaciaChyba, match=sprava):
        publikuj.publikuj(koren, app_id, build, "2026.11.24-1")


def test_existujuca_verzia_sa_neprepise(koren, build):
    publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    pred = (koren / "apps.json").read_text(encoding="utf-8")
    (build / "nl.exe").write_text("ina")
    with pytest.raises(publikuj.PublikaciaChyba, match="nie je novšia|už existuje"):
        publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    assert (koren / "apps.json").read_text(encoding="utf-8") == pred
    assert (koren / "nl" / "2026.11.24-1" / "nl.exe").read_text() == "exe" * 100


def test_starsia_verzia_sa_odmietne(koren, build):
    with pytest.raises(publikuj.PublikaciaChyba, match="nie je novšia"):
        publikuj.publikuj(koren, "nl", build, "2026.11.01-1")
    assert apps_json(koren)["aplikacie"][0]["verzia"] == "2026.11.19-1"


def test_neplatna_verzia_a_prazdny_build(koren, build, tmp_path):
    with pytest.raises(publikuj.PublikaciaChyba, match="Neplatná verzia"):
        publikuj.publikuj(koren, "nl", build, "dnes")
    (tmp_path / "prazdny").mkdir()
    with pytest.raises(publikuj.PublikaciaChyba, match="prázdny"):
        publikuj.publikuj(koren, "nl", tmp_path / "prazdny", "2026.11.24-1")
    with pytest.raises(publikuj.PublikaciaChyba, match="prázdny"):
        publikuj.publikuj(koren, "nl", tmp_path / "neexistuje", "2026.11.24-1")


def test_nezhoda_pri_kontrole_nezapise_apps_json(koren, build, monkeypatch):
    pred = (koren / "apps.json").read_text(encoding="utf-8")
    volania = []
    from nc_nastroje import publikovanie
    povodna = publikovanie._spocitaj

    def falosna(p):
        volania.append(p)
        n, v = povodna(p)
        return (n, v) if len(volania) == 1 else (n - 1, v)               # kópia „stratila“ súbor
    monkeypatch.setattr(publikovanie, "_spocitaj", falosna)
    with pytest.raises(publikuj.PublikaciaChyba, match="Kontrola zlyhala"):
        publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    assert (koren / "apps.json").read_text(encoding="utf-8") == pred     # klienti o ničom nevedia
    assert not (koren / "apps.json.bak").exists()
    assert not (koren / "nl" / "2026.11.24-1").exists() and not list((koren / "nl").glob("*.tmp"))


def test_cli_v_rezime_na_prezeranie_nepublikuje(koren, build, monkeypatch, capsys):
    from nc_nastroje import config
    monkeypatch.setattr(config, "nacitaj_nastavenia", lambda: config.Nastavenia(rezim="prezeranie"))
    kod = publikuj.main(["nl", str(build), "--verzia", "2026.11.24-1", "--koren", str(koren), "--ano"])
    assert kod == 2 and apps_json(koren)["aplikacie"][0]["verzia"] == "2026.11.19-1"


def test_poskodeny_apps_json(koren, build):
    (koren / "apps.json").write_text("{ rozbite", encoding="utf-8")
    with pytest.raises(publikuj.PublikaciaChyba, match="JSON"):
        publikuj.publikuj(koren, "nl", build, "2026.11.24-1")
    (koren / "apps.json").unlink()
    with pytest.raises(publikuj.PublikaciaChyba, match="nedá prečítať"):
        publikuj.publikuj(koren, "nl", build, "2026.11.24-1")


def test_cli_bez_potvrdenia_pre_skutocny_koren_sa_pyta(koren, build, monkeypatch, capsys):
    from nc_nastroje import config
    monkeypatch.setattr(config, "nacitaj_nastavenia", lambda: config.Nastavenia(rezim="plny"))   # nie reálne nastavenia
    monkeypatch.setattr("builtins.input", lambda _p="": "nie")
    kod = publikuj.main(["nl", str(build), "--verzia", "2026.11.24-1", "--koren", str(koren)])
    assert kod == 1 and "Zrušené" in capsys.readouterr().out
    assert apps_json(koren)["aplikacie"][0]["verzia"] == "2026.11.19-1"
    kod = publikuj.main(["nl", str(build), "--verzia", "2026.11.24-1", "--koren", str(koren), "--ano"])
    assert kod == 0 and apps_json(koren)["aplikacie"][0]["verzia"] == "2026.11.24-1"


def test_zoznam_aplikacii_obsahuje_aj_nenasadene_a_launcher(tmp_path):
    from nc_nastroje.publikovanie import zoznam_aplikacii
    (tmp_path / "apps.json").write_text(json.dumps({
        "aplikacie": [{"id": "a", "nazov": "Alfa", "typ": "exe", "verzia": "", "zdroj": ""},
                      {"id": "w", "nazov": "Web", "typ": "web", "url": "x"}, {"nazov": "bez id"}],
        "launcher": {"verzia": ""}}), encoding="utf-8")
    assert zoznam_aplikacii(tmp_path) == [("a", "Alfa"), ("launcher", "NC Nástroje (samotný launcher)")]


def test_zoznam_aplikacii_bez_apps_json(tmp_path):
    from nc_nastroje.publikovanie import zoznam_aplikacii
    with pytest.raises(publikuj.PublikaciaChyba, match="apps.json"):
        zoznam_aplikacii(tmp_path)
