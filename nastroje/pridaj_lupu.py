"""Pridá (alebo opraví) záznam Lupy v apps.json na L:\_Nastroje – Lupa sa spúšťa priamo z L:\_Lupa\Lupa.exe.

    python nastroje/pridaj_lupu.py [--koren L:\_Nastroje] [--exe L:\_Lupa\Lupa.exe]

Pred zápisom urobí zálohu apps.json.bak, zapíše atomicky a bez BOM. Iné záznamy nemení."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ZAZNAM = {"id": "lupa", "nazov": "Lupa", "popis": "Prehliadač zákaziek na L:\\", "typ": "exe",
          "ikona": "lupa.png", "farba": "#C25A00", "tlacidlo": "Otvoriť", "prijima": [],
          "stav": {"adapter": "lupa_sken", "cesta": "_Lupa"}}


def pridaj_lupu(koren: Path, exe: str) -> str:
    apps = Path(koren) / "apps.json"
    data = json.loads(apps.read_text(encoding="utf-8-sig"))
    zaznam = dict(ZAZNAM, spustit=exe)
    zoznam = data.setdefault("aplikacie", [])
    for i, z in enumerate(zoznam):
        if isinstance(z, dict) and z.get("id") == "lupa":
            zoznam[i] = zaznam
            akcia = "opravený"
            break
    else:
        zoznam.append(zaznam)
        akcia = "pridaný"
    shutil.copy2(apps, apps.with_name("apps.json.bak"))
    tmp = apps.with_name("apps.json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, apps)
    return akcia


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--koren", default=r"L:\_Nastroje")
    ap.add_argument("--exe", default=r"L:\_Lupa\Lupa.exe")
    a = ap.parse_args()
    if not Path(a.exe).is_file():
        print(f"CHYBA: {a.exe} neexistuje", file=sys.stderr)
        sys.exit(1)
    print(f"Záznam Lupy {pridaj_lupu(Path(a.koren), a.exe)} v {Path(a.koren) / 'apps.json'}")
