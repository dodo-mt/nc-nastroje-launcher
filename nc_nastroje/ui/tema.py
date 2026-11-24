"""Farby, fonty, pomocné funkcie pre UI."""
import tkinter as tk

SVETLA = dict(pozadie="#F3F3F3", karta="#FFFFFF", okraj="#E0E3E7", text="#1B1B1B",
              text2="#555555", akcent="#005FB8", pruh="#DDEBF9")
FONT = "Segoe UI"

STAVY = {
    "ok": ("#0F7B0F", "OK"),
    "upozornenie": ("#9D5D00", "Upozornenie"),
    "chyba": ("#C42B1C", "Chyba"),
    "nova_verzia": ("#005FB8", "Nová verzia"),
    "necinny": ("#9AA0A6", "Pripravený"),
    "nezname": ("#9AA0A6", "Neznámy"),
}


def centruj(okno: tk.Misc, rodic: tk.Misc) -> None:
    """Umiestni dialóg do stredu hlavného okna."""
    okno.update_idletasks()
    w, h = okno.winfo_reqwidth(), okno.winfo_reqheight()
    if rodic.winfo_viewable():
        x = rodic.winfo_rootx() + (rodic.winfo_width() - w) // 2
        y = rodic.winfo_rooty() + (rodic.winfo_height() - h) // 2
    else:                                      # hlavné okno je skryté v tray – do stredu obrazovky
        x = (okno.winfo_screenwidth() - w) // 2
        y = (okno.winfo_screenheight() - h) // 3
    okno.geometry(f"+{max(x, 0)}+{max(y, 0)}")


class Tooltip:
    """Jednoduchý tooltip po 500 ms nad widgetom."""

    def __init__(self, widget: tk.Misc, text: str):
        self.widget, self.text, self._id, self._okno = widget, text, None, None
        widget.bind("<Enter>", self._plan, add="+")
        widget.bind("<Leave>", self._zrus, add="+")
        widget.bind("<ButtonPress>", self._zrus, add="+")

    def _plan(self, _e=None):
        self._zrus()
        self._id = self.widget.after(500, self._ukaz)

    def _ukaz(self):
        x, y = self.widget.winfo_rootx() + 10, self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._okno = tk.Toplevel(self.widget)
        self._okno.wm_overrideredirect(True)
        self._okno.wm_geometry(f"+{x}+{y}")
        tk.Label(self._okno, text=self.text, bg="#FFFFE1", fg="#1B1B1B", relief="solid", bd=1,
                 font=(FONT, 9), padx=6, pady=3).pack()

    def _zrus(self, _e=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._okno:
            self._okno.destroy()
            self._okno = None
