"""Jedna inštancia launchera: druhé spustenie pošle argumenty prvej (lokálny socket) a skončí.

Server počúva len na 127.0.0.1 s exkluzívnym portom (nikto iný ho nezoberie) a každý príkaz musí
niesť token z `%LOCALAPPDATA%\\NC_Nastroje\\instancia.token` – bez neho ho iný používateľ ani program
na tomto počítači nepošle. Príkazy sa len odovzdajú ďalej (`pri_prikaze`), nič sa tu nespúšťa.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import socket
import threading
import time
from pathlib import Path
from typing import Callable

from .config import LOCAL_DIR

log = logging.getLogger(__name__)

TOKEN_SUBOR = LOCAL_DIR / "instancia.token"
MAX_PRIKAZ = 1_000_000          # bajtov
TIMEOUT_S = 2.0


class Instancia:
    def __init__(self, port: int, token_subor: Path | None = None):
        self.port = port
        self._token_subor = Path(token_subor or TOKEN_SUBOR)
        self._srv: socket.socket | None = None
        self._obsluha: Callable[[dict], None] | None = None
        self._cakajuce: list[dict] = []      # príkazy, ktoré prišli skôr, než bola nastavená obsluha
        self._zamok = threading.Lock()

    # ---------- token ----------
    def _token(self) -> str:
        try:
            t = self._token_subor.read_text(encoding="utf-8").strip()
            if t:
                return t
        except OSError:
            pass
        t = secrets.token_hex(16)
        self._token_subor.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._token_subor.with_name(self._token_subor.name + ".tmp")
        tmp.write_text(t, encoding="utf-8")
        os.replace(tmp, self._token_subor)
        return t

    # ---------- server ----------
    def ziskaj(self) -> bool:
        """Pokúsi sa stať prvou inštanciou (obsadí port a spustí server). False = port už niekto drží."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):      # Windows: nik iný nezíska ten istý port
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(("127.0.0.1", self.port))
            s.listen(8)
        except OSError:
            s.close()
            return False
        self._srv = s
        self._token()                                    # vytvorí sa vopred, aby ho mal klient z čoho prečítať
        threading.Thread(target=self._slucka, daemon=True, name="instancia").start()
        return True

    def nastav_obsluhu(self, fn: Callable[[dict], None]) -> None:
        """Od teraz sa príkazy odovzdávajú `fn(prikaz)` (z vlákna servera – má ich len zaradiť do UI);
        čo prišlo skôr, sa odovzdá hneď."""
        with self._zamok:
            self._obsluha = fn
            cakajuce, self._cakajuce = self._cakajuce, []
        for p in cakajuce:
            fn(p)

    def zatvor(self) -> None:
        srv, self._srv = self._srv, None
        if srv:
            try:
                srv.close()
            except OSError:
                pass

    def _slucka(self) -> None:
        srv = self._srv
        while srv is not None and self._srv is srv:
            try:
                conn, _adr = srv.accept()
            except OSError:
                return                                   # server zatvorený
            threading.Thread(target=self._spracuj, args=(conn,), daemon=True).start()

    def _spracuj(self, conn: socket.socket) -> None:
        try:
            with conn:
                conn.settimeout(TIMEOUT_S)
                data = b""
                while not data.endswith(b"\n") and len(data) < MAX_PRIKAZ:
                    kus = conn.recv(65536)
                    if not kus:
                        break
                    data += kus
                try:
                    obsah = json.loads(data.decode("utf-8"))
                    ok = hmac.compare_digest(str(obsah.get("token", "")), self._token()) \
                        and isinstance(obsah.get("prikaz"), dict)
                except (ValueError, AttributeError):
                    ok = False
                if not ok:
                    log.warning("Príkaz na inštanciu odmietnutý (zlý token alebo formát)")
                    conn.sendall(b"zle\n")
                    return
                self._dorucit(obsah["prikaz"])
                conn.sendall(b"ok\n")
        except OSError as e:
            log.warning("Spojenie s druhou inštanciou zlyhalo: %s", e)

    def _dorucit(self, prikaz: dict) -> None:
        with self._zamok:
            fn = self._obsluha
            if fn is None:
                self._cakajuce.append(prikaz)
                return
        try:
            fn(prikaz)
        except Exception:  # noqa: BLE001 – chyba obsluhy nesmie zhodiť server
            log.exception("Obsluha príkazu zlyhala")

    # ---------- klient ----------
    def posli(self, prikaz: dict) -> bool:
        """Pošle príkaz prvej inštancii. True = prijala."""
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=TIMEOUT_S) as c:
                c.settimeout(TIMEOUT_S)
                c.sendall((json.dumps({"token": self._token(), "prikaz": prikaz}) + "\n").encode("utf-8"))
                return c.recv(16).strip() == b"ok"
        except OSError:
            return False

    def spusti_alebo_posli(self, prikaz: dict) -> bool:
        """True = sme prvá inštancia (pokračuj v štarte). False = príkaz prevzala už bežiaca inštancia (skonči).
        Ak port drží niečo, čo neodpovedá, štart pokračuje bez kontroly jednej inštancie (zaloguje sa)."""
        if self.ziskaj():
            return True
        for _ in range(3):                               # prvá inštancia mohla port práve obsadzovať
            if self.posli(prikaz):
                return False
            time.sleep(0.3)
        log.warning("Port %s je obsadený a nikto neodpovedá – štart bez kontroly jednej inštancie", self.port)
        return True
