"""Ikona launchera (tray, okno, zástupcovia) so stavovou bodkou. Kreslí sa kódom, žiadny binárny súbor."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .ui.tema import STAVY, SVETLA

_S = 256   # kreslí sa veľké a zmenší sa (hladké okraje)


def vytvor_ikonu(stav: str | None = None, velkost: int = 64) -> Image.Image:
    """Biely zaoblený štvorec s mriežkou 2×2 (logo launchera). `stav` = farba bodky vpravo dole
    (ok / upozornenie / chyba / nova_verzia / necinny / nezname), None = bez bodky."""
    img = Image.new("RGBA", (_S, _S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, _S - 9, _S - 9), radius=56, fill="#FFFFFF", outline="#D0D5DB", width=6)
    akcent = SVETLA["akcent"]
    for x, y in ((56, 56), (140, 56), (56, 140), (140, 140)):
        d.rounded_rectangle((x, y, x + 60, y + 60), radius=14, outline=akcent, width=12)
    if stav:
        farba = STAVY.get(stav, STAVY["nezname"])[0]
        cx = cy = _S - 66
        d.ellipse((cx - 62, cy - 62, cx + 62, cy + 62), fill="#FFFFFF")     # biely prstenec
        d.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=farba)
    return img.resize((velkost, velkost), Image.LANCZOS)


def uloz_ico(img: Image.Image, cesta: Path) -> Path:
    """Uloží obrázok ako .ico (viac veľkostí) – pre zástupcov (.lnk)."""
    cesta = Path(cesta)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    zdroj = img.resize((256, 256), Image.LANCZOS) if img.size != (256, 256) else img
    zdroj.save(cesta, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    return cesta
