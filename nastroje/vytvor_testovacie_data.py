"""Vytvorí falošný koreň test_data\\L\\_Nastroje: apps.json + fiktívne aplikácie.

Spustenie: python nastroje/vytvor_testovacie_data.py
Nesiaha na skutočné L:/R:.
"""
import json
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent / "test_data"
NASTROJE = KOREN / "L" / "_Nastroje"

FIKTIVNA = '''import sys, tkinter as tk
r = tk.Tk()
r.title({nazov!r})
tk.Label(r, text={nazov!r} + " (fiktívna aplikácia, v " + {verzia!r} + ")", font=("Segoe UI", 12)).pack(padx=30, pady=15)
tk.Label(r, text="Argumenty:\\n" + "\\n".join(sys.argv[1:]) if len(sys.argv) > 1 else "Bez argumentov").pack(padx=30, pady=10)
r.mainloop()
'''

APLIKACIE = [
    dict(id="tnc_sync", nazov="TNC Sync", popis="Záloha programov zo strojov", verzia="2026.11.20-1",
         ikona="tnc_sync.png", farba="#005FB8", prijima=["priecinok"],
         stav={"adapter": "tnc_sync"}),
    dict(id="triedic_nc", nazov="Triedič NC", popis="Rozdelenie programov podľa stroja", verzia="2026.11.19-2",
         ikona="triedic_nc.png", farba="#7B3FBF", prijima=[".h", ".mpf"], len_plny_rezim=True,
         tlacidlo="Otvoriť", pozastavit=True, stav={"adapter": "proces"}),
    dict(id="lupa", nazov="Lupa", popis="Prehliadač zákaziek na L:\\", typ="web",
         url="file:///L:/_Lupa/index.html", url_hladat="{url}?q={text}", url_cesta="{url}?cesta={cesta}",
         ikona="lupa.png", farba="#C25A00", prijima=["priecinok", "*"], tlacidlo="Otvoriť",
         stav={"adapter": "lupa_sken"}),
    dict(id="nastrojovy_list", nazov="Nástrojový list", popis="Z .pof súborov hyperMILL", verzia="2026.11.24-1",
         ikona="nastrojovy_list.png", farba="#0B7A55", prijima=[".pof", "priecinok"],
         stav={"adapter": "subor_json", "cesta": "_stav\\nastrojovy_list"},
         co_je_nove="nastrojovy_list\\CO_JE_NOVE.md"),
    dict(id="programovy_list", nazov="Programový list", popis="Nákresy upnutia → Excel + PDF", verzia="2026.11.20-1",
         ikona="programovy_list.png", farba="#C4244B", prijima=[".png", ".jpg", ".xlsx", "priecinok"]),
    dict(id="nc_editor", nazov="NC Editor", popis="Úprava a porovnanie programov", verzia="2026.11.22-1",
         ikona="nc_editor.png", farba="#555555", prijima=[".h", ".i", ".mpf", ".spf", ".nc"]),
]

# Staršie verzie, aby fáza 4 mala čo porovnávať
STARE = {"nastrojovy_list": "2026.11.19-1"}


def main():
    zaznamy = []
    for a in APLIKACIE:
        a = dict(a)
        a.setdefault("typ", "python")  # fiktívne aplikácie sú .py skripty, nie exe
        if a["typ"] != "web":
            zdroj = f"{a['id']}\\{a['verzia']}"
            a.update(zdroj=zdroj, spustit="fiktivna_app.py", argumenty="{cesty}")
            for verzia in {a["verzia"], STARE.get(a["id"])} - {None}:
                p = NASTROJE / a["id"] / verzia
                p.mkdir(parents=True, exist_ok=True)
                (p / "fiktivna_app.py").write_text(
                    FIKTIVNA.format(nazov=a["nazov"], verzia=verzia), encoding="utf-8")
        zaznamy.append(a)
    NASTROJE.mkdir(parents=True, exist_ok=True)
    (NASTROJE / "apps.json").write_text(
        json.dumps({"verzia_formatu": 1, "aplikacie": zaznamy}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (KOREN / "R").mkdir(exist_ok=True)
    print("Hotovo:", NASTROJE)


if __name__ == "__main__":
    main()
