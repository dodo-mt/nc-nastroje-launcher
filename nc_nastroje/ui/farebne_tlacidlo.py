"""Plošné farebné tlačidlo (ttk téma sv-ttk neumožňuje vlastné farby tlačidiel).

Má rovnaké rozhranie ako ttk.Button, ktoré dlaždica používa: `state([...])`, `configure(text=…)`, `pack/grid`.
"""
import tkinter as tk

from .tema import FONT


class FarebneTlacidlo(tk.Label):
    def __init__(self, rodic, text: str, command, farba: str, hover: str | None = None, fg: str = "#FFFFFF"):
        super().__init__(rodic, text=text, font=(FONT, 10), padx=14, pady=7, bd=0, cursor="arrow")
        self._command = command
        self._farba, self._hover, self._fg = farba, hover or farba, fg
        self._povolene = True
        self._nad = False
        self.bind("<Enter>", lambda e: self._nastav_nad(True))
        self.bind("<Leave>", lambda e: self._nastav_nad(False))
        self.bind("<ButtonRelease-1>", self._klik)
        self._prekresli()

    def nastav_farbu(self, farba: str, hover: str | None = None, fg: str = "#FFFFFF"):
        self._farba, self._hover, self._fg = farba, hover or farba, fg
        self._prekresli()

    def state(self, stavy=None):
        """Ako ttk: `state(["disabled"])` vypne, `state(["!disabled"])` zapne."""
        if stavy is None:
            return ("disabled",) if not self._povolene else ()
        for s in stavy:
            if s == "disabled":
                self._povolene = False
            elif s == "!disabled":
                self._povolene = True
        self._prekresli()

    def _nastav_nad(self, nad: bool):
        self._nad = nad
        self._prekresli()

    def _klik(self, e):
        if self._povolene and 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height():
            self._command()

    def _prekresli(self):
        if self._povolene:
            self.configure(bg=self._hover if self._nad else self._farba, fg=self._fg)
        else:
            self.configure(bg="#D9DCDF", fg="#8A9096")
