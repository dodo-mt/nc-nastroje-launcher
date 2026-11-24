"""Nakreslí jednoduché PNG ikony aplikácií (80×80, farebný symbol na svetlom štvorci)."""
from pathlib import Path
from PIL import Image, ImageDraw

CIEL = Path(__file__).resolve().parent.parent / "nc_nastroje" / "ikony"
S = 640  # kreslí sa veľké, zmenší sa na 80


def zmiesaj(farba, podiel):
    c = tuple(int(farba[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(255 - (255 - v) * podiel) for v in c)


def zaklad(farba):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=S // 6, fill=zmiesaj(farba, 0.12))
    return img, d


def sync(d, c, w):
    d.arc((150, 150, 490, 490), 200, 340, fill=c, width=w)
    d.arc((150, 150, 490, 490), 20, 160, fill=c, width=w)
    d.polygon([(470, 160), (500, 270), (390, 250)], fill=c)
    d.polygon([(170, 480), (140, 370), (250, 390)], fill=c)


def filtr(d, c, w):
    for y, x in ((190, 150), (320, 220), (450, 290)):
        d.line((x, y, S - x, y), fill=c, width=w)


def lupa(d, c, w):
    d.ellipse((150, 150, 400, 400), outline=c, width=w)
    d.line((370, 370, 500, 500), fill=c, width=w)


def dokument(d, c, w):
    d.rounded_rectangle((170, 120, 470, 520), radius=30, outline=c, width=w)
    for y in (260, 340, 420):
        d.line((240, y, 400, y), fill=c, width=w - 8)


def obrazok(d, c, w):
    d.rounded_rectangle((120, 150, 520, 490), radius=40, outline=c, width=w)
    d.ellipse((220, 230, 290, 300), outline=c, width=w - 10)
    d.line((140, 450, 270, 360, 340, 410, 420, 330, 500, 420), fill=c, width=w - 8, joint="curve")


def ozubene_koleso(d, c, w):
    import math
    cx = cy = S // 2
    zubov = 8
    body = []
    for i in range(zubov * 4):
        r = 225 if i % 4 in (0, 1) else 175
        uhol = math.radians(i * 360 / (zubov * 4) - 360 / (zubov * 8))
        body.append((cx + r * math.cos(uhol), cy + r * math.sin(uhol)))
    d.polygon(body, fill=c)
    d.ellipse((cx - 80, cy - 80, cx + 80, cy + 80), fill=zmiesaj(c, 0.12))


def zameriavac(d, c, w):
    d.rounded_rectangle((130, 130, 510, 510), radius=30, outline=c, width=w - 12)
    d.ellipse((240, 240, 400, 400), outline=c, width=w - 8)
    for x1, y1, x2, y2 in ((320, 170, 320, 230), (320, 410, 320, 470), (170, 320, 230, 320), (410, 320, 470, 320)):
        d.line((x1, y1, x2, y2), fill=c, width=w - 12)


def kod(d, c, w):
    d.line((250, 190, 130, 320, 250, 450), fill=c, width=w, joint="curve")
    d.line((390, 190, 510, 320, 390, 450), fill=c, width=w, joint="curve")


IKONY = {
    "tnc_sync": ("#005FB8", sync), "triedic_nc": ("#7B3FBF", filtr), "lupa": ("#C4244B", lupa),
    "nastrojovy_list": ("#0B7A55", dokument), "programovy_list": ("#E07B00", ozubene_koleso),
    "nc_editor": ("#555555", kod), "cnc_vykres_edgecam": ("#4A962D", zameriavac),
}


def main():
    CIEL.mkdir(parents=True, exist_ok=True)
    for nazov, (farba, kresli) in IKONY.items():
        img, d = zaklad(farba)
        kresli(d, farba, 38)
        img.resize((80, 80), Image.LANCZOS).save(CIEL / f"{nazov}.png")
    print("Ikony:", CIEL)


if __name__ == "__main__":
    main()
