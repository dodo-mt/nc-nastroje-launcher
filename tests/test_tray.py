"""Testy tray (bez pystray vlákna): stav, texty menu, ikona so stavovou bodkou, odovzdanie akcií do UI vlákna."""
from datetime import datetime

from nc_nastroje import tray
from nc_nastroje.ikona import vytvor_ikonu
from nc_nastroje.katalog import App
from nc_nastroje.stavy import Stav
from nc_nastroje.ui.tema import STAVY

TERAZ = datetime(2026, 11, 24, 12, 0)


def app(id_, nazov, **kw):
    return App(id=id_, nazov=nazov, typ="exe", zdroj="x\\1", spustit="x.exe", **kw)


APPS = [app("tnc_sync", "TNC Sync"), app("triedic_nc", "Triedič NC", pozastavit=True),
        app("lupa", "Lupa"), app("nl", "Nástrojový list")]


def stavy_ok():
    return {"tnc_sync": Stav("ok", "OK", cas=datetime(2026, 11, 24, 11, 32)),
            "triedic_nc": Stav("ok", "Beží"), "lupa": Stav("ok", "OK"), "nl": Stav("necinny", "Pripravený")}


def test_hlavicka_diskov():
    assert tray.hlavicka_diskov(True, True) == "NC NÁSTROJE · L:\\ R:\\ OK"
    assert tray.hlavicka_diskov(False, True) == "NC NÁSTROJE · L:\\ nedostupný"
    assert tray.hlavicka_diskov(True, False) == "NC NÁSTROJE · R:\\ nedostupný"
    assert tray.hlavicka_diskov(False, False) == "NC NÁSTROJE · L:\\ R:\\ nedostupné"


def test_stav_menu_a_texty_vpravo():
    s = tray.zostav_tray_stav(APPS, stavy_ok(), True, True, nove={"nl"}, teraz=TERAZ)
    assert [p.vpravo for p in s.polozky] == ["11:32", "beží", "", "nová"]
    assert [tray.text_polozky(p) for p in s.polozky] == [
        "✔  TNC Sync\t11:32", "✔  Triedič NC\tbeží", "✔  Lupa", "⬇  Nástrojový list\tnová"]
    assert s.pozastavit == ("triedic_nc", False)             # triedič beží -> ponúkne sa pozastavenie
    assert s.hlavicka.endswith("L:\\ R:\\ OK")


def test_cas_z_vcerajska_sa_neukaze_a_chyba_ano():
    st = stavy_ok()
    st["tnc_sync"] = Stav("chyba", "Záloha nebeží", cas=datetime(2026, 11, 20, 8, 0))
    s = tray.zostav_tray_stav(APPS, st, True, True, teraz=TERAZ)
    assert s.polozky[0].vpravo == "chyba" and s.polozky[0].stav == "chyba"
    st["tnc_sync"] = Stav("ok", "OK", cas=datetime(2026, 11, 23, 8, 0))
    assert tray.zostav_tray_stav(APPS, st, True, True, teraz=TERAZ).polozky[0].vpravo == ""


def test_pozastavit_len_ked_triedic_bezi_a_pamata_si_stav():
    st = stavy_ok()
    st["triedic_nc"] = Stav("necinny", "Nebeží")
    assert tray.zostav_tray_stav(APPS, st, True, True).pozastavit is None
    s = tray.zostav_tray_stav(APPS, stavy_ok(), True, True, pozastavene={"triedic_nc"})
    assert s.pozastavit == ("triedic_nc", True)


def test_najhorsi_stav_pre_bodku():
    ok = tray.zostav_tray_stav(APPS, stavy_ok(), True, True)
    assert ok.stav == "ok"
    st = stavy_ok()
    st["lupa"] = Stav("upozornenie", "Starý sken")
    assert tray.zostav_tray_stav(APPS, st, True, True).stav == "upozornenie"
    st["tnc_sync"] = Stav("chyba", "Záloha nebeží")
    assert tray.zostav_tray_stav(APPS, st, True, True).stav == "chyba"
    # nedostupný L: = červená, nedostupný R: = oranžová
    assert tray.zostav_tray_stav(APPS, stavy_ok(), False, True).stav == "chyba"
    assert tray.zostav_tray_stav(APPS, stavy_ok(), True, False).stav == "upozornenie"


def test_nova_verzia_neprekryje_chybu():
    st = stavy_ok()
    st["nl"] = Stav("chyba", "Chyba")
    s = tray.zostav_tray_stav(APPS, st, True, True, nove={"nl"}, teraz=TERAZ)
    assert s.polozky[3].stav == "chyba"


def test_bez_stavov_nepadne():
    s = tray.zostav_tray_stav(APPS, {}, True, True)
    assert s.stav == "necinny" and [p.stav for p in s.polozky] == ["necinny"] * 4
    assert tray.zostav_tray_stav([], {}, True, True).polozky == []


# ---------- menu ----------
def ikona_s_frontou():
    fronta = []
    volane = []
    t = tray.TrayIkona(fronta.append, lambda: volane.append("zobraz"), lambda i: volane.append(("app", i)),
                       lambda i: volane.append(("pozastav", i)), lambda: volane.append("zakazka"),
                       lambda: volane.append("koniec"))
    return t, fronta, volane


def test_menu_ma_poradie_z_navrhu():
    t, _f, _v = ikona_s_frontou()
    s = tray.zostav_tray_stav(APPS, stavy_ok(), True, True, nove={"nl"}, teraz=TERAZ)
    menu = t.zostav_menu(s)
    texty = [m[0] for m in menu]
    assert texty == ["NC NÁSTROJE · L:\\ R:\\ OK", "✔  TNC Sync\t11:32", "✔  Triedič NC\tbeží", "✔  Lupa",
                     "⬇  Nástrojový list\tnová", "-", "Pozastaviť triedič", "Otvoriť zákazku…",
                     "Otvoriť NC Nástroje", "-", "Ukončiť"]
    assert menu[0][2] == {"enabled": False}                          # hlavička je len nadpis
    predvolena = [m[0] for m in menu if m[2].get("default")]
    assert predvolena == ["Otvoriť NC Nástroje"]                     # tučné + dvojklik


def test_menu_pokracovat_ked_je_triedenie_pozastavene():
    t, _f, _v = ikona_s_frontou()
    s = tray.zostav_tray_stav(APPS, stavy_ok(), True, True, pozastavene={"triedic_nc"})
    assert "Pokračovať v triedení" in [m[0] for m in t.zostav_menu(s)]


def test_menu_bez_pozastavenia_ked_triedic_nebezi():
    t, _f, _v = ikona_s_frontou()
    st = stavy_ok()
    st["triedic_nc"] = Stav("necinny", "Nebeží")
    texty = [m[0] for m in t.zostav_menu(tray.zostav_tray_stav(APPS, st, True, True))]
    assert "Pozastaviť triedič" not in texty and "Pokračovať v triedení" not in texty


def test_akcie_z_tray_idu_cez_ui_frontu_nie_priamo():
    """Callback z pystray vlákna nesmie meniť UI priamo – len zaradí prácu do hlavného vlákna."""
    t, fronta, volane = ikona_s_frontou()
    menu = t.zostav_menu(tray.zostav_tray_stav(APPS, stavy_ok(), True, True, teraz=TERAZ))
    akcie = {m[0]: m[1] for m in menu if m[1]}
    akcie["✔  Lupa"](None, None)
    akcie["Otvoriť NC Nástroje"](None, None)
    akcie["Ukončiť"](None, None)
    assert volane == [] and len(fronta) == 3                         # zatiaľ nič nevykonané
    for fn in fronta:
        fn()
    assert volane == [("app", "lupa"), "zobraz", "koniec"]


def test_chyba_v_akcii_nezhodi_tray():
    def zla_fronta(fn):
        raise RuntimeError("okno je zavreté")
    t = tray.TrayIkona(zla_fronta, lambda: None, lambda i: None, lambda i: None, lambda: None, lambda: None)
    menu = t.zostav_menu(tray.zostav_tray_stav(APPS, stavy_ok(), True, True))
    menu[-1][1](None, None)                                          # nevyhodí výnimku


def test_tray_bez_spustenia_je_bezpecny():
    t, _f, _v = ikona_s_frontou()
    t.aktualizuj(tray.TrayStav("NC NÁSTROJE · L:\\ R:\\ OK", [], "ok"))     # bez ikony len zapamätá
    t.upozorni("text")
    t.zastav()
    assert t.bezi is False


# ---------- ikona ----------
def test_ikona_ma_bodku_vo_farbe_stavu():
    for stav in ("ok", "upozornenie", "chyba", "nova_verzia"):
        img = vytvor_ikonu(stav, 64)
        r, g, b, a = img.getpixel((47, 47))
        h = STAVY[stav][0].lstrip("#")
        assert (r, g, b) == tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) and a == 255
    bez = vytvor_ikonu(None, 64).getpixel((47, 47))
    assert bez[:3] != (15, 123, 15)                                  # bez stavu tam bodka nie je
    assert vytvor_ikonu(None, 32).size == (32, 32)
