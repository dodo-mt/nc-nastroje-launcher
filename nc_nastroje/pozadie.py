"""Práca na pozadí: sieťové a dlhé operácie bežia vo vlákne, výsledky sa odovzdajú v hlavnom vlákne.

UI nikdy nečaká na sieť. Výsledky idú cez frontu a hlavné vlákno ich preberá cez `after`
(Tkinter sa nesmie volať z cudzieho vlákna).
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

log = logging.getLogger(__name__)


class Pozadie:
    def __init__(self, root, interval_ms: int = 200):
        self._root = root
        self._interval = interval_ms
        self._q: queue.Queue = queue.Queue()
        self._bezi: set[str] = set()
        self._callbacky: dict[str, tuple] = {}
        self._cakajuce: dict[str, tuple] = {}    # najnovšia žiadosť, ktorá čaká na dobehnutie bežiacej
        root.after(interval_ms, self._prevezmi)

    def spusti(self, kluc: str, praca: Callable, pri_vysledku: Callable | None = None,
               pri_priebehu: Callable | None = None) -> bool:
        """Spustí `praca(posli)` vo vlákne. `posli(obj)` odovzdá priebežný údaj do `pri_priebehu(obj)`;
        návratová hodnota ide do `pri_vysledku(vysledok)` (ak práca zlyhá, nevolá sa).
        Ak práca s rovnakým kľúčom ešte beží, zapamätá sa len najnovšia žiadosť a spustí sa po dobehnutí
        (vráti False)."""
        if kluc in self._bezi:
            self._cakajuce[kluc] = (praca, pri_vysledku, pri_priebehu)
            return False
        self._bezi.add(kluc)
        self._callbacky[kluc] = (pri_vysledku, pri_priebehu)

        def telo():
            try:
                vysledok = praca(lambda obj: self._q.put(("priebeh", kluc, obj)))
            except Exception:  # noqa: BLE001 – vlákno nesmie padnúť potichu
                log.exception("Práca na pozadí '%s' zlyhala", kluc)
                vysledok = None
            self._q.put(("hotovo", kluc, vysledok))

        threading.Thread(target=telo, daemon=True, name=f"pozadie-{kluc}").start()
        return True

    def bezi(self, kluc: str) -> bool:
        return kluc in self._bezi

    def _volaj(self, fn, obj):
        try:
            fn(obj)
        except Exception:  # noqa: BLE001 – chyba v UI callbacku nesmie zastaviť preberanie výsledkov
            log.exception("Spracovanie výsledku z pozadia zlyhalo")

    def _prevezmi(self):
        try:
            while True:
                typ, kluc, obj = self._q.get_nowait()
                pri_vysledku, pri_priebehu = self._callbacky.get(kluc, (None, None))
                if typ == "priebeh":
                    if pri_priebehu:
                        self._volaj(pri_priebehu, obj)
                    continue
                self._bezi.discard(kluc)
                self._callbacky.pop(kluc, None)
                if obj is not None and pri_vysledku:
                    self._volaj(pri_vysledku, obj)
                if kluc in self._cakajuce:
                    self.spusti(kluc, *self._cakajuce.pop(kluc))
        except queue.Empty:
            pass
        self._root.after(self._interval, self._prevezmi)
