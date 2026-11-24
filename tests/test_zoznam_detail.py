"""Testy čistých funkcií zobrazenia B: z `riadky` stavu sa vyrobia 3 karty detailu."""
from nc_nastroje.aktualizacie import AppAktualizacia
from nc_nastroje.stavy import Stav
from nc_nastroje.ui.zoznam_detail import Karta, karty_z_stavu, rozdel_riadok


def test_rozdel_riadok():
    assert rozdel_riadok("Posledná záloha: dnes 11:32") == ("Posledná záloha", "dnes 11:32")
    assert rozdel_riadok("Stroje: 5 / 6") == ("Stroje", "5 / 6")
    assert rozdel_riadok("Len text bez dvojbodky") == ("", "Len text bez dvojbodky")
    assert rozdel_riadok("Čas 11:32") == ("", "Čas 11:32")                    # dvojbodka bez medzery nie je oddeľovač
    assert rozdel_riadok("A: b: c") == ("A", "b: c")                         # delí sa len na prvej
    dlhy = "x" * 40 + ": hodnota"
    assert rozdel_riadok(dlhy) == ("", dlhy)                                 # príliš dlhý názov nie je názov karty
    assert rozdel_riadok("") == ("", "")


def tnc():
    return Stav("upozornenie", "OK s upozornením", ["Posledná záloha: dnes 11:32", "Stroje: 4 / 5"],
                [("MB65 A", "ok"), ("DMC 160", "upozornenie")])


def test_tri_karty_z_riadkov_stavu_a_verzia():
    k = karty_z_stavu(tnc(), "v 2026.11.20-1")
    assert [(c.nazov, c.hodnota) for c in k] == [("Posledná záloha", "dnes 11:32"), ("Stroje", "4 / 5"),
                                                 ("Verzia", "2026.11.20-1")]
    assert k[0].podtext == "OK s upozornením" and k[0].stav == "upozornenie"    # slovný stav adaptéra farbou stavu
    assert k[1].podtext == "DMC 160" and k[1].stav == "upozornenie"             # čo nie je v poriadku
    assert k[2].podtext == "aktuálna" and k[2].stav == "ok"


def test_druha_karta_vsetko_v_poriadku():
    s = Stav("ok", "OK", ["A: 1", "Stroje: 6 / 6"], [("MB65 A", "ok"), ("MB65 B", "ok")])
    k = karty_z_stavu(s, "v 1")
    assert k[1].podtext == "všetko v poriadku" and k[1].stav == "ok"


def test_tri_riadky_stavu_vyplnia_vsetky_karty_bez_verzie():
    s = Stav("ok", "OK", ["Spustenie: dnes", "Listy: 12", "Chyby: 0"])
    assert [c.nazov for c in karty_z_stavu(s, "v 2026.11.24-1")] == ["Spustenie", "Listy", "Chyby"]


def test_viac_ako_tri_riadky_sa_orezu():
    s = Stav("ok", "OK", ["A: 1", "B: 2", "C: 3", "D: 4"])
    assert [c.nazov for c in karty_z_stavu(s, "v 1")] == ["A", "B", "C"]


def test_riadok_bez_nazvu_dostane_nazov_stav():
    k = karty_z_stavu(Stav("ok", "OK", ["Všetko beží"]), "v 1")
    assert k[0] == Karta("Stav", "Všetko beží", "OK", "ok")


def test_verzia_podla_aktualizacie():
    s = Stav("ok", "OK", ["A: 1", "B: 2"])
    caka = AppAktualizacia("caka", "2026.11.24-1", "2026.11.24-1", stara="2026.11.19-1")
    k = karty_z_stavu(s, "v 2026.11.19-1 → 11.24-1", caka)[2]
    assert k.podtext == "Aktualizuje sa pri ďalšom spustení" and k.stav == "nova_verzia"
    assert karty_z_stavu(s, "v 1", AppAktualizacia("kopiruje"))[2].podtext == "Kopíruje sa nová verzia"
    chyba = karty_z_stavu(s, "v 1", AppAktualizacia("chyba", sprava="Kopírovanie z L:\\ zlyhalo"))[2]
    assert chyba.stav == "chyba" and "zlyhalo" in chyba.podtext


def test_bez_stavu_su_karty_verzia_a_stav_a_tretia_prazdna():
    k = karty_z_stavu(None, "v 2026.11.24-1")
    assert len(k) == 3
    assert (k[0].nazov, k[0].hodnota) == ("Verzia", "2026.11.24-1")
    assert (k[1].nazov, k[1].hodnota) == ("Stav", "Pripravený")
    assert (k[2].nazov, k[2].hodnota) == ("", "")                            # prázdna = detail ju skryje


def test_webova_aplikacia_bez_verzie():
    k = karty_z_stavu(Stav("ok", "OK"), "web")
    assert k[0].nazov == "Verzia" and k[0].hodnota == "web"
    k = karty_z_stavu(Stav("ok", "OK"), "")
    assert k[0].hodnota == "–" and k[0].podtext == ""


def test_vzdy_presne_tri_karty():
    for riadky in ([], ["A: 1"], ["A: 1", "B: 2"], ["A: 1", "B: 2", "C: 3"], ["A: 1"] * 6):
        assert len(karty_z_stavu(Stav("ok", "OK", riadky), "v 1")) == 3
    assert len(karty_z_stavu(None, "")) == 3
