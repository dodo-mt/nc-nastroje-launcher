"""Editor strojov – logika: jednoduchý zápis textov, operácie, kontrola, zápis so zálohou a ochrana pred cudzou zmenou."""
import pytest

from nc_nastroje import nc_parsery_cesta  # noqa: F401 – pridá balík nc_parsery do sys.path
from nc_nastroje import stroje_editor as se
from nc_parsery import stroje


# ---- jednoduchý zápis textov hlavičky

@pytest.mark.parametrize("text, regex", [
    ("Kondia", "Kondia"),
    ("DMC 160", r"DMC\s*160"),
    ("  DMU   65  monoBLOCK ", r"DMU\s*65\s*monoBLOCK"),
    ("3x-HH", "3x-HH"),
    ("MAZAK INTEGREX (EIA/ISO)", r"MAZAK\s*INTEGREX\s*\(EIA/ISO\)"),
])
def test_text_na_regex_a_spat(text, regex):
    assert se.text_na_regex(text) == regex
    assert se.regex_na_text(regex) == " ".join(text.split())


@pytest.mark.parametrize("regex", [r"DMU\s*75|monoBLOCK.*840D", r"DMU\s*(80|85)\s*eVo", r"J-?200", r"\d+"])
def test_pokrocile_vyrazy_ostanu_regexom(regex):
    assert se.regex_na_text(regex) is None
    assert se.riadky_na_regexy(se.regexy_na_riadky([regex])) == [regex]       # tam a späť bez straty


def test_riadky_a_regexy_v_poli():
    pole = se.regexy_na_riadky([r"DMC\s*160", r"DMU\s*(80|85)\s*eVo", "Kondia"])
    assert pole == "DMC 160\nre:DMU\\s*(80|85)\\s*eVo\nKondia"
    assert se.riadky_na_regexy(pole + "\n\n  ") == [r"DMC\s*160", r"DMU\s*(80|85)\s*eVo", "Kondia"]
    assert se.riadky_na_regexy("RE: a|b") == ["a|b"]


def test_predvolene_hlavicky_prezijú_prevod_tam_a_spat():
    for m in stroje.predvolene().modely:
        assert se.riadky_na_regexy(se.regexy_na_riadky(list(m.hlavicka))) == list(m.hlavicka), m.id


# ---- operácie

def editor():
    return se.Editor(stroje.predvolene())


def test_predvolene_bez_chyb_a_bez_zmeny():
    e = editor()
    assert e.chyby() == [] and not e.zmenene


def test_pridanie_s_unikatnym_id():
    e = editor()
    s1 = e.pridaj_skupinu("Nový stroj")
    s2 = e.pridaj_skupinu("Nový stroj")
    assert (s1, s2) == ("novy_stroj", "novy_stroj_2") and e.zmenene
    m = e.pridaj_model("Nový post", s1)
    k = e.pridaj_kus("Nový A", m)
    assert e.model(m)["skupina"] == s1 and e.kus(k)["model"] == m
    with pytest.raises(ValueError):
        e.pridaj_model("X", "neexistuje")
    assert e.pridaj_kus("Bez modelu", "neexistuje") and e.kus("bez_modelu")["model"] is None
    assert e.chyby() == []


def test_premenovanie_nemeni_id():
    e = editor()
    e.skupina("evo")["nazov"] = "eVo (premenované)"
    z = e.zoznam()
    assert z.skupina("evo").nazov == "eVo (premenované)" and z.skupina_modelu("evo80").id == "evo"
    assert e.kus("evo_80_a")["model"] == "evo80"


def test_zmazanie():
    e = editor()
    with pytest.raises(ValueError):
        e.zmaz_skupinu("evo")                                   # má modely
    assert e.zmaz_model("evo80") == 2                           # kusy eVo 80 A/B ostanú bez modelu
    assert e.kus("evo_80_a")["model"] is None and e.model("evo80") is None
    e.zmaz_model("evo60")
    e.zmaz_skupinu("evo")
    assert e.skupina("evo") is None and e.chyby() == []
    e.zmaz_kus("tyc")
    assert e.kus("tyc") is None


def test_poradie_modelov():
    e = editor()
    ids = [m["id"] for m in e.modely]
    assert e.posun_model("mono_h640", -1)
    assert [m["id"] for m in e.modely][:3] == ["mono_840d", "mono_h640", "mono_3x"]
    assert e.zoznam().rozpoznaj("DMG DMU 65 monoBLOCK 3X").id == "mono_h640"      # priorita sa zmenila
    assert not e.posun_model(ids[0], -1) and not e.posun_model(ids[-1], 1) and not e.posun_model("x", 1)


def test_texty_modelu_z_formulara():
    e = editor()
    e.nastav_texty_modelu("kondia", "Kondia\nKondia CNC\nre:Kon+dia", "(STROJ: Kondia)\n", "h, .I")
    m = e.model("kondia")
    assert m["hlavicka"] == ["Kondia", r"Kondia\s*CNC", "Kon+dia"]
    assert m["triedic"] == {"match": ["(STROJ: Kondia)"]} and m["pripony"] == [".h", ".i"]
    e.nastav_texty_modelu("kondia", "Kondia", "", "")
    assert "triedic" not in e.model("kondia") and e.model("kondia")["pripony"] == []


def test_kontrola_chyb():
    e = editor()
    e.nastav_texty_modelu("kondia", "re:(nezatvorene", "Kondia bez zatvoriek", "")
    ch = " | ".join(e.chyby())
    assert "chybný regex" in ch and "tvar (STROJ" in ch
    e2 = editor()
    e2.skupina("evo")["priecinok"] = "DMC 160"                   # duplicitný priečinok
    assert any("priečinok" in c for c in e2.chyby())
    e3 = editor()
    e3.model("kondia")["skupina"] = "neexistuje"
    assert any("skupina" in c for c in e3.chyby())


# ---- súbor

def test_uloz_so_zalohou_a_zmenou_podpisu(tmp_path):
    cesta = stroje.cesta_suboru(tmp_path)
    se.vytvor_z_predvolenych(cesta)
    with pytest.raises(FileExistsError):
        se.vytvor_z_predvolenych(cesta)                         # existujúci súbor sa nikdy neprepíše
    e = se.Editor(stroje.nacitaj(cesta))
    p = se.podpis(cesta)
    e.skupina("evo")["kinematika"] = "5x (upravené)"
    se.uloz(e, cesta, p)
    assert (cesta.parent / "stroje.json.bak").exists() and not e.zmenene
    assert stroje.nacitaj(cesta).skupina("evo").kinematika == "5x (upravené)"


def test_uloz_odmietne_cudziu_zmenu_a_chyby(tmp_path):
    cesta = stroje.cesta_suboru(tmp_path)
    se.vytvor_z_predvolenych(cesta)
    e = se.Editor(stroje.nacitaj(cesta))
    p = se.podpis(cesta)
    # niekto iný (napr. „Naučiť sa“ v Triediči) súbor zmení
    iny = se.Editor(stroje.nacitaj(cesta))
    iny.skupina("evo")["kinematika"] = "iné"
    stroje.uloz(iny.zoznam(), cesta)
    e.skupina("dmc160")["kinematika"] = "moje"
    with pytest.raises(se.SuborZmenenyChyba):
        se.uloz(e, cesta, p)
    assert stroje.nacitaj(cesta).skupina("dmc160").kinematika == "5x"           # nič sa neprepísalo
    e.nastav_texty_modelu("kondia", "re:(zle", "", "")
    with pytest.raises(ValueError):
        se.uloz(e, cesta, se.podpis(cesta))


def test_podpis_neexistujuceho():
    assert se.podpis("/neexistuje/stroje.json") is None


# ---- test hlavičky

def test_otestuj_hlavicku():
    z = stroje.predvolene()
    r = se.otestuj_hlavicku(z, "DMG DMU 65 monoBLOCK 3X")
    assert r["model"].id == "mono_3x" and r["skupina"].id == "mono_h640" and r["triedic"] == ["monoBLOCK H640"]
    r = se.otestuj_hlavicku(z, "10 ;  (STROJ: 3x-HH iTNC530)\n")
    assert r["stroj"] == "3x-HH iTNC530" and r["skupina"].id == "h530_3x" and r["triedic"] == ["3X H530"]
    r = se.otestuj_hlavicku(z, "DMU 60 U")                            # Lupa pozná (DMC 60), Triedič netriedi
    assert r["skupina"].id == "dmc60" and r["triedic"] == []
    r = se.otestuj_hlavicku(z, "Neznamy")
    assert r["model"] is None and r["triedic"] == []
    assert se.otestuj_hlavicku(z, "DMG DMC 160", vybrane=set())["triedic"] == []     # nevybraná skupina sa netriedi


def test_otestuj_subor(tmp_path):
    p = tmp_path / "x.h"
    p.write_bytes("0 BEGIN PGM X MM\n7 ;  (STROJ: DMG DMC 160)\n".encode("cp1250"))
    assert se.otestuj_subor(stroje.predvolene(), p)["skupina"].id == "dmc160"
