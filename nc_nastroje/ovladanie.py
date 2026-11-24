"""Ovládanie aplikácií cez príznakové súbory (zatiaľ len pozastavenie Triediča NC).

Launcher kód aplikácií nemení. Pozastavenie je preto LOKÁLNA požiadavka – súbor
`%LOCALAPPDATA%\\NC_Nastroje\\ovladanie\\<id>.pozastaveny`. Aplikácia ju zohľadní, až keď ju začne čítať
(návrh v docs/zmeny_v_aplikaciach.md). Nič sa nezapisuje na L: ani R:.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import LOCAL_DIR

log = logging.getLogger(__name__)

OVLADANIE_DIR = LOCAL_DIR / "ovladanie"


def _subor(app_id: str, adresar: Path | None = None) -> Path:
    return Path(adresar or OVLADANIE_DIR) / f"{app_id}.pozastaveny"


def je_pozastaveny(app_id: str, adresar: Path | None = None) -> bool:
    return _subor(app_id, adresar).exists()


def nastav_pozastaveny(app_id: str, pozastaveny: bool, adresar: Path | None = None) -> None:
    subor = _subor(app_id, adresar)
    if pozastaveny:
        subor.parent.mkdir(parents=True, exist_ok=True)
        subor.write_text("pozastavene\n", encoding="utf-8")
    else:
        try:
            subor.unlink()
        except FileNotFoundError:
            pass
    log.info("Požiadavka na %s pre %s", "pozastavenie" if pozastaveny else "pokračovanie", app_id)
