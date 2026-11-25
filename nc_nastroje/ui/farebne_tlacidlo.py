"""Farebné tlačidlo so zaoblenými rohmi (téma sv-ttk neumožňuje vlastné farby ttk tlačidiel).

Má rovnaké rozhranie ako ttk.Button, ktoré dlaždica používa: `state([...])`, `pack/grid`; text sa mení cez
`nastav_text`, farba cez `nastav_farbu`. Pozadie plátna sa prefarbuje spolu s dlaždicou (rohy sú priehľadné).
"""
import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

from .tema import FONT

VYSKA = 32
POLOMER = 5
ZVACSENIE = 4          # kreslenie vo väčšom rozlíšení a zmenšenie = vyhladené okraje


def _obrazok(sirka: int, farba: str) -> ImageTk.PhotoImage:
    v = ZVACSENIE
    img = Image.new("RGBA", (sirka * v, VYSKA * v), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, sirka * v - 1, VYSKA * v - 1), POLOMER * v, fill=farba)
    return ImageTk.PhotoImage(img.resize((sirka, VYSKA), Image.LANCZOS))


class FarebneTlacidlo(tk.Canvas):
    def __init__(self, rodic, text: str, command, farba: str, hover: str | None = None, fg: str = "#FFFFFF"):
        super().__init__(rodic, height=VYSKA, bd=0, highlightthickness=0, cursor="arrow", bg=rodic.cget("bg"))
        self._font = tkfont.Font(family=FONT, size=10)
        self._command = command
        self._text, self._farba, self._hover, self._fg = text, farba, hover or farba, fg
        self._povolene, self._nad = True, False
        self._img = None
        self.bind("<Enter>", lambda e: self._nastav_nad(True))
        self.bind("<Leave>", lambda e: self._nastav_nad(False))
        self.bind("<ButtonRelease-1>", self._klik)
        self._prekresli()

    def nastav_text(self, text: str):
        if text != self._text:
            self._text = text
            self._prekresli()

    def nastav_farbu(self, farba: str, hover: str | None = None, fg: str = "#FFFFFF"):
        if (farba, hover or farba, fg) != (self._farba, self._hover, self._fg):
            self._farba, self._hover, self._fg = farba, hover or farba, fg
            self._prekresli()

    def state(self, stavy=None):
        """Ako ttk: `state(["disabled"])` vypne, `state(["!disabled"])` zapne."""
        if stavy is None:
            return ("disabled",) if not self._povolene else ()
        for s in stavy:
            if s in ("disabled", "!disabled"):
                povolene = s == "!disabled"
                if povolene != self._povolene:
                    self._povolene = povolene
                    self._prekresli()

    def _nastav_nad(self, nad: bool):
        if nad != self._nad:
            self._nad = nad
            self._prekresli()

    def _klik(self, e):
        if self._povolene and 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height():
            self._command()

    def _prekresli(self):
        sirka = self._font.measure(self._text) + 32
        if self._povolene:
            farba, fg = (self._hover if self._nad else self._farba), self._fg
        else:
            farba, fg = "#D9DCDF", "#8A9096"
        self.configure(width=sirka)
        self.delete("all")
        self._img = _obrazok(sirka, farba)
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_text(sirka // 2, VYSKA // 2, text=self._text, font=self._font, fill=fg)
