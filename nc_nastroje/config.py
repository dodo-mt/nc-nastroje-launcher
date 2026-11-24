"""Cesty a nastavenia používateľa."""
import json
import logging
import logging.handlers
import os
from dataclasses import dataclass, asdict, field, fields
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
    spustit_po_prihlaseni: bool = False        # zástupca v shell:startup (`--tray`)
    spustat_aplikacie_pri_starte: bool = True  # spustiť aplikácie s `spustit_pri_starte` z apps.json
    odoslat_do: list = field(default_factory=list)   # id aplikácií, ktoré majú zástupcu v „Odoslať do“
    skryte_aplikacie: list = field(default_factory=list)   # id aplikácií, ktoré si používateľ na tomto PC skryl
    klavesova_skratka: str = "Ctrl+Alt+N"  # globálna skratka na vyvolanie okna (prázdne = vypnuté)
    otvarat_v: str = "prieskumnik"             # kde sa otvára priečinok zákazky: prieskumnik | totalcmd
    totalcmd_cesta: str = ""                   # exe alebo priečinok Total Commandera (prázdne = nájde sa sám)
    port_instancie: int = 47653                # lokálny port pre jednu inštanciu launchera (127.0.0.1)
    tray_oznamenie_ukazane: bool = False       # oznámenie „beží v oblasti oznámení“ sa ukáže len raz

    def __post_init__(self):
        try:
            self.interval_stavov_s = max(5, int(self.interval_stavov_s))
        except (TypeError, ValueError):
            self.interval_stavov_s = 30
        try:
            self.port_instancie = int(self.port_instancie)
            if not 1024 <= self.port_instancie <= 65535:
                raise ValueError
        except (TypeError, ValueError):
            self.port_instancie = 47653
        if not isinstance(self.odoslat_do, list):
            self.odoslat_do = []
        self.odoslat_do = [str(x) for x in self.odoslat_do]
        if self.otvarat_v not in ("prieskumnik", "totalcmd"):
            self.otvarat_v = "prieskumnik"
        self.totalcmd_cesta = str(self.totalcmd_cesta or "")
        self.klavesova_skratka = str(self.klavesova_skratka or "").strip()
        if not isinstance(self.skryte_aplikacie, list):
            self.skryte_aplikacie = []
        self.skryte_aplikacie = [str(x) for x in self.skryte_aplikacie]
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
