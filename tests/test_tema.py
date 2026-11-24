"""Testy palety (svetlý / tmavý režim): kontrast textu, konzistencia paliet, prepínanie a prefarbenie widgetov."""
import tkinter as tk

import pytest

from nc_nastroje.ui import tema
from nc_nastroje.ui.tema import (PALETA, STAVY, SVETLA, TMAVA, _STAVY_SVETLE, _STAVY_TMAVE, kontrast, nastav_temu,
                                 prefarbi_strom)

# dvojice (text, pozadie), ktoré sa v UI skutočne vyskytujú – kontrast min. 4.5:1
TEXT_NA_POZADI = [("text", "karta"), ("text", "pozadie"), ("text2", "karta"), ("text2", "pozadie"),
                  ("text", "karta2"), ("text2", "karta2"), ("text", "vyber"), ("text2", "vyber"),
                  ("text", "pruh"), ("akcent", "karta"), ("akcent", "pozadie"), ("akcent", "pruh"),
                  ("akcent", "karta2"), ("chyba_fg", "chyba_bg"), ("var_fg", "var_bg"), ("tip_fg", "tip_bg"),
                  ("odznak_fg", "akcent")]


@pytest.fixture(autouse=True)
def vrat_svetlu():
    """Paleta je globálny stav – každý test sa končí vo svetlom režime, ako ho očakávajú ostatné testy."""
    yield
    nastav_temu(False)


def test_kontrast_zname_hodnoty():
    assert round(kontrast("#000000", "#FFFFFF"), 1) == 21.0
    assert kontrast("#777777", "#777777") == 1.0
    assert kontrast("#1B1B1B", "#FFFFFF") == kontrast("#FFFFFF", "#1B1B1B")      # symetrický


@pytest.mark.parametrize("nazov,paleta", [("svetla", SVETLA), ("tmava", TMAVA)])
def test_text_ma_kontrast_aspon_4_5(nazov, paleta):
    zle = {f"{a}/{b}": round(kontrast(paleta[a], paleta[b]), 2) for a, b in TEXT_NA_POZADI
           if kontrast(paleta[a], paleta[b]) < 4.5}
    assert not zle, f"{nazov}: kontrast pod 4.5:1 {zle}"


@pytest.mark.parametrize("nazov,stavy,paleta", [("svetla", _STAVY_SVETLE, SVETLA), ("tmava", _STAVY_TMAVE, TMAVA)])
def test_farby_stavov_su_ako_text_citatelne(nazov, stavy, paleta):
    """Farba stavu sa používa aj ako text (podtext kariet, chyba na dlaždici) – min. 4.5:1 na všetkých pozadiach."""
    for stav in ("ok", "upozornenie", "chyba", "nova_verzia"):
        for pozadie in ("karta", "karta2", "pozadie"):
            assert kontrast(stavy[stav][0], paleta[pozadie]) >= 4.5, (nazov, stav, pozadie)


def test_palety_maju_rovnake_kluce_a_stavy_rovnake_texty():
    assert SVETLA.keys() == TMAVA.keys()
    assert {k: v[1] for k, v in _STAVY_SVETLE.items()} == {k: v[1] for k, v in _STAVY_TMAVE.items()}


def test_farby_sa_medzi_paletami_neprekryvaju():
    """Mapa stará→nová farba by sa pri prekryve zmýlila (a prefarbila by už nové widgety)."""
    svetle = {v.lower() for v in SVETLA.values()} | {v[0].lower() for v in _STAVY_SVETLE.values()}
    tmave = {v.lower() for v in TMAVA.values()} | {v[0].lower() for v in _STAVY_TMAVE.values()}
    assert not svetle & tmave


def test_farby_v_jednej_palete_su_jednoznacne():
    for paleta in (SVETLA, TMAVA):
        opakovane = {v for v in paleta.values() if list(paleta.values()).count(v) > 1}
        assert opakovane <= {paleta["text"]}                         # jediná povolená zhoda: text a tip_fg


def test_rovnaka_svetla_farba_ma_rovnaky_tmavy_protejsok():
    """Ak sa v svetlej téme paleta a farba stavu zhodujú (napr. chyba, akcent), musia sa zhodovať aj v tmavej –
    inak by mapa stará→nová vybrala jednu z nich náhodne."""
    svetle = [(k, v) for k, v in SVETLA.items()] + [(f"stav:{k}", v[0]) for k, v in _STAVY_SVETLE.items()]
    tmave = {**TMAVA, **{f"stav:{k}": v[0] for k, v in _STAVY_TMAVE.items()}}
    for kluc_a, farba_a in svetle:
        for kluc_b, farba_b in svetle:
            if farba_a.lower() == farba_b.lower():
                assert tmave[kluc_a].lower() == tmave[kluc_b].lower(), (kluc_a, kluc_b)


def test_siva_dlazdica_je_zamerne_slaby_kontrast():
    for paleta in (SVETLA, TMAVA):
        assert kontrast(paleta["siva_text"], paleta["siva_karta"]) < 4.5


# ---------- prepínanie ----------
def test_nastav_temu_meni_paletu_na_mieste_a_vrati_mapu():
    objekt = PALETA
    mapa = nastav_temu(True)
    assert PALETA is objekt and tema.PALETA is objekt                # rovnaký objekt – importy ostanú platné
    assert PALETA["pozadie"] == TMAVA["pozadie"] and tema.je_tmava()
    assert STAVY["ok"][0] == _STAVY_TMAVE["ok"][0]
    assert mapa[SVETLA["pozadie"].lower()] == TMAVA["pozadie"]       # stará -> nová
    assert mapa[_STAVY_SVETLE["chyba"][0].lower()] == _STAVY_TMAVE["chyba"][0]
    mapa2 = nastav_temu(False)
    assert PALETA["pozadie"] == SVETLA["pozadie"] and not tema.je_tmava()
    assert mapa2[TMAVA["karta"].lower()] == SVETLA["karta"]


def test_opakovane_nastavenie_rovnakej_temy_je_bezpecne():
    nastav_temu(True)
    mapa = nastav_temu(True)                                         # stará == nová
    assert all(k == v.lower() for k, v in mapa.items())              # nič sa nemení


@pytest.fixture
def tk_koren():
    try:
        koren = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk nie je k dispozícii (bez displeja)")
    koren.withdraw()
    yield koren
    koren.destroy()


def test_prefarbi_strom_prefarbi_tk_widgety_a_nechá_cudzie_farby(tk_koren):
    ram = tk.Frame(tk_koren, bg=SVETLA["karta"])
    ram.pack()
    popis = tk.Label(ram, text="x", bg=SVETLA["karta"], fg=SVETLA["text2"])
    popis.pack()
    cudzi = tk.Label(ram, text="y", bg="#C25A00", fg=SVETLA["text"])           # farba aplikácie, nie z palety
    cudzi.pack()
    platno = tk.Canvas(ram, bg=SVETLA["pozadie"], highlightthickness=0)
    platno.pack()
    bodka = platno.create_oval(1, 1, 11, 11, fill=_STAVY_SVETLE["ok"][0], outline="")
    prefarbi_strom(tk_koren, nastav_temu(True))
    assert ram.cget("bg").lower() == TMAVA["karta"].lower()
    assert popis.cget("bg").lower() == TMAVA["karta"].lower() and popis.cget("fg").lower() == TMAVA["text2"].lower()
    assert cudzi.cget("bg").lower() == "#c25a00" and cudzi.cget("fg").lower() == TMAVA["text"].lower()
    assert platno.cget("bg").lower() == TMAVA["pozadie"].lower()
    assert platno.itemcget(bodka, "fill").lower() == _STAVY_TMAVE["ok"][0].lower()
    prefarbi_strom(tk_koren, nastav_temu(False))                       # a naspäť
    assert ram.cget("bg").lower() == SVETLA["karta"].lower()
    assert platno.itemcget(bodka, "fill").lower() == _STAVY_SVETLE["ok"][0].lower()


def test_prefarbi_strom_nepadne_na_ttk_widgetoch(tk_koren):
    from tkinter import ttk
    ttk.Button(tk_koren, text="ok").pack()
    ttk.Entry(tk_koren).pack()
    prefarbi_strom(tk_koren, nastav_temu(True))                        # ttk nemá bg/fg – musí to preskočiť
