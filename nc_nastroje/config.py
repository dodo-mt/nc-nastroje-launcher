"""Cesty a nastavenia používateľa."""
import json
import logging
import logging.handlers
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
_PREPIS = os.environ.get("NC_NASTROJE_DATA")  # pre testy: jeden koreň pre APPDATA aj LOCALAPPDATA

APPDATA_DIR = Path(_PREPIS) / "appdata" if _PREPIS else Path(os.environ.get("APPDATA", Path.home())) / "NC_Nastroje"
LOCAL_DIR = Path(_PREPIS) / "local" if _PREPIS else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NC_Nastroje"
NASTAVENIA_SUBOR = APPDATA_DIR / "nastavenia.json"
LOG_DIR = LOCAL_DIR / "log"
CACHE_DIR = LOCAL_DIR / "cache"
IKONY_DIR = Path(__file__).resolve().parent / "ikony"

TEST_DATA = PROJEKT / "test_data"


def _predvoleny_koren(nazov: str, skutocny: str) -> str:
    """Pri vývoji (existuje test_data) sa nikdy nepoužije skutočné L:/R:."""
    test = TEST_DATA / nazov
    return str(test) if test.exists() else skutocny


@dataclass
class Nastavenia:
    koren_nastrojov: str = ""
    koren_l: str = ""
    koren_r: str = ""
    rezim: str = "plny"          # plny | prezeranie
    zobrazenie: str = "A"        # A | B
    tmavy_rezim: bool = False
    interval_stavov_s: int = 30  # ako často sa obnovujú stavy aplikácií

    def __post_init__(self):
        try:
            self.interval_stavov_s = max(5, int(self.interval_stavov_s))
        except (TypeError, ValueError):
            self.interval_stavov_s = 30
        if not self.koren_nastrojov:
            self.koren_nastrojov = _predvoleny_koren(r"L\_Nastroje", r"L:\_Nastroje")
        if not self.koren_l:
            self.koren_l = _predvoleny_koren("L", "L:\\")
        if not self.koren_r:
            self.koren_r = _predvoleny_koren("R", "R:\\")


def nacitaj_nastavenia() -> Nastavenia:
    try:
        data = json.loads(NASTAVENIA_SUBOR.read_text(encoding="utf-8"))
        znamy = {f.name for f in fields(Nastavenia)}
        return Nastavenia(**{k: v for k, v in data.items() if k in znamy})
    except (OSError, ValueError, TypeError):
        return Nastavenia()


def uloz_nastavenia(n: Nastavenia) -> None:
    NASTAVENIA_SUBOR.parent.mkdir(parents=True, exist_ok=True)
    tmp = NASTAVENIA_SUBOR.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(n), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, NASTAVENIA_SUBOR)


def nastav_logovanie() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(
        LOG_DIR / "launcher.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(h)
