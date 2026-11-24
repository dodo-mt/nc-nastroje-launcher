"""Testy jednej inštancie (socket 127.0.0.1) – náhodné voľné porty, token v tmp."""
import json
import queue
import socket
import time

import pytest

from nc_nastroje import instancia as ins
from nc_nastroje.instancia import Instancia


def volny_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def token(tmp_path):
    return tmp_path / "instancia.token"


@pytest.fixture
def prva(token):
    i = Instancia(volny_port(), token)
    assert i.ziskaj()
    prijate = queue.Queue()
    i.nastav_obsluhu(prijate.put)
    yield i, prijate
    i.zatvor()


def test_druha_instancia_posle_prikaz_prvej(prva, token):
    i, prijate = prva
    druha = Instancia(i.port, token)
    assert druha.spusti_alebo_posli({"akcia": "aplikacia", "id": "nl", "cesty": ["C:\\a b\\x.pof"]}) is False
    assert prijate.get(timeout=2) == {"akcia": "aplikacia", "id": "nl", "cesty": ["C:\\a b\\x.pof"]}


def test_prva_instancia_ziska_port_druha_nie(token):
    port = volny_port()
    a, b = Instancia(port, token), Instancia(port, token)
    try:
        assert a.ziskaj() is True
        assert b.ziskaj() is False
    finally:
        a.zatvor()
    assert b.ziskaj() is True                                          # po zatvorení prvej ho získa druhá
    b.zatvor()


def test_zly_token_sa_odmietne(prva):
    i, prijate = prva
    with socket.create_connection(("127.0.0.1", i.port), timeout=2) as c:
        c.sendall((json.dumps({"token": "zly", "prikaz": {"akcia": "zobraz"}}) + "\n").encode())
        assert c.recv(16).strip() == b"zle"
    with socket.create_connection(("127.0.0.1", i.port), timeout=2) as c:
        c.sendall(b"nie je json\n")
        assert c.recv(16).strip() == b"zle"
    with socket.create_connection(("127.0.0.1", i.port), timeout=2) as c:
        c.sendall((json.dumps({"token": i._token(), "prikaz": "nie objekt"}) + "\n").encode())
        assert c.recv(16).strip() == b"zle"
    time.sleep(0.2)
    assert prijate.empty()


def test_prikazy_pred_nastavenim_obsluhy_sa_zachovaju(token):
    i = Instancia(volny_port(), token)
    assert i.ziskaj()
    try:
        assert Instancia(i.port, token).posli({"akcia": "zobraz"})
        assert Instancia(i.port, token).posli({"akcia": "tray"})
        prijate = queue.Queue()
        i.nastav_obsluhu(prijate.put)                                   # okno ešte nebolo hotové
        assert [prijate.get(timeout=1)["akcia"], prijate.get(timeout=1)["akcia"]] == ["zobraz", "tray"]
    finally:
        i.zatvor()


def test_chyba_v_obsluhe_nezhodi_server(prva):
    i, prijate = prva
    volania = []

    def zla(p):
        volania.append(p)
        raise RuntimeError("boom")
    i.nastav_obsluhu(zla)
    assert Instancia(i.port, i.token_subor if hasattr(i, "token_subor") else i._token_subor).posli({"akcia": "zobraz"})
    assert Instancia(i.port, i._token_subor).posli({"akcia": "tray"})   # server stále žije
    assert len(volania) == 2


def test_posli_bez_servera_vrati_false(token):
    assert Instancia(volny_port(), token).posli({"akcia": "zobraz"}) is False


def test_cudzi_proces_na_porte_nezablokuje_start(token, monkeypatch):
    """Ak port drží niečo, čo neodpovedá, launcher sa aj tak spustí (bez kontroly jednej inštancie)."""
    monkeypatch.setattr(ins, "TIMEOUT_S", 0.2)
    monkeypatch.setattr(ins.time, "sleep", lambda s: None)
    cudzi = socket.socket()
    cudzi.bind(("127.0.0.1", 0))
    cudzi.listen(1)                                                    # počúva, ale nikdy neodpovie
    try:
        assert Instancia(cudzi.getsockname()[1], token).spusti_alebo_posli({"akcia": "zobraz"}) is True
    finally:
        cudzi.close()


def test_token_sa_vytvori_raz_a_zostane(token):
    t1 = Instancia(1, token)._token()
    assert len(t1) == 32 and Instancia(2, token)._token() == t1
