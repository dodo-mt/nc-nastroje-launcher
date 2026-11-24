"""Vytvorí falošný koreň test_data\\L\\_Nastroje: apps.json + fiktívne aplikácie.

Spustenie: python nastroje/vytvor_testovacie_data.py
Nesiaha na skutočné L:/R:.
"""
import json
import time
from datetime import datetime, timedelta
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


def _zapis(cesta: Path, data: dict):
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def stavove_subory():
    """Falošné stavy pre fázu 2 (časy vzhľadom na „teraz“, aby boli stále čerstvé).
    Formáty: viď CLAUDE.md (subor_json) a skutočné súbory TNC Sync / Lupy."""
    teraz = datetime.now().replace(microsecond=0)
    iso = lambda dt: dt.isoformat(timespec="seconds")  # noqa: E731
    # subor_json – Nástrojový list
    _zapis(KOREN / "L" / "_Nastroje" / "_stav" / "nastrojovy_list" / "PC-PROG1.json", {
        "stav": "ok", "riadky": ["Posledné spustenie: dnes", "Vygenerované listy: 12"],
        "cipy": [{"text": "HTML", "stav": "ok"}, {"text": "PDF", "stav": "upozornenie"}],
        "cas": iso(teraz - timedelta(minutes=20)), "pocitac": "PC-PROG1"})
    # TNC Sync – _tnc_sync\_tnc_sync_stav.json (formát 1 zo skutočného TNC Sync)
    koniec = teraz - timedelta(hours=1)
    stroje = {n: {"last_try": iso(koniec), "last_ok": iso(koniec), "kind": "heidenhain", "error": ""}
              for n in ("MB65 A", "MB65 B", "eVo 80", "H640")}
    stroje["DMC 160"] = {"last_try": iso(koniec), "last_ok": iso(teraz - timedelta(days=1)),
                         "kind": "heidenhain", "error": "stroj nedostupný"}
    _zapis(KOREN / "L" / "_tnc_sync" / "_tnc_sync_stav.json", {
        "format": 1, "written": iso(koniec), "pc": "PC-PROG1", "user": "test", "app_version": "2026.11.20-1",
        "last_run": {"start": iso(koniec - timedelta(minutes=4)), "end": iso(koniec), "mode": "auto",
                     "result": "UPOZORNENIE", "duration_s": 240, "machines_ok": 4, "machines_total": 5,
                     "copied": 31, "failed": 0, "bytes": 1234567, "errors": []},
        "machines": stroje})
    # Lupa – lupa_scan.json vedľa databázy (L:\_Lupa)
    _zapis(KOREN / "L" / "_Lupa" / "lupa_scan.json", {
        "finished": time.time() - 3 * 3600, "errors": 0, "full": False, "jobs": 14, "files": 2310,
        "version": "1.5.0"})


def strom_zakaziek():
    """Falošný L: a R: so zákazkami pre fázu 6 (hľadanie, Otvoriť L: / R:). Skutočné L:/R: sa nedotýka.
    Nové zákazky: <zákazník s menom>/OD########/<pozícia>; staré: OD<zákazník>/<6 číslic> na najvyššej úrovni."""
    l, r = KOREN / "L", KOREN / "R"
    for cesta in (
        ("101270-Firma Alfa spol", "OD00021930", "21930-1A", "NC"),
        ("101270-Firma Alfa spol", "OD00021930", "21930-1B", "NC"),
        ("101270-Firma Alfa spol", "OD00021931", "21931-1A", "NC"),
        ("100020-Beta AG", "OD00000626", "626-1A", "NC"),
        ("OD626", "001252", "NC"),            # stará zákazka (nie je totožná s novou OD00000626)
        ("OD626", "001253"),
        ("OD067", "001252"),                  # rovnaké staré číslo u iného zákazníka -> viac zhôd
        ("OD067", "009712"),
    ):
        l.joinpath(*cesta).mkdir(parents=True, exist_ok=True)
    # R: = zrkadlo L: len s programami (nie všetko)
    r.joinpath("101270-Firma Alfa spol", "OD00021930", "21930-1A", "NC").mkdir(parents=True, exist_ok=True)
    (r / "101270-Firma Alfa spol" / "OD00021930" / "21930-1A" / "NC" / "21930-1A_10.h").write_text("; fiktívny program\n")


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
    # poznámky „Čo je nové“ (apps.json ich referuje relatívne ku koreňu nástrojov)
    (NASTROJE / "nastrojovy_list" / "CO_JE_NOVE.md").write_text(
        "# Nástrojový list\n\n## 2026.11.24-1\n- Výstup aj do PDF.\n\n## 2026.11.19-1\n- Prvá verzia.\n",
        encoding="utf-8")
    # záznam launchera (zo zdrojového kódu sa neaktualizuje, len zo zostaveného exe)
    launcher_dir = NASTROJE / "launcher" / "2026.11.24-1"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    (launcher_dir / "nc_nastroje.exe").write_bytes(b"fiktivny launcher")
    launcher = {"verzia": "2026.11.24-1", "zdroj": "launcher\\2026.11.24-1", "spustit": "nc_nastroje.exe",
                "co_je_nove": "launcher\\CO_JE_NOVE.md"}
    (NASTROJE / "launcher" / "CO_JE_NOVE.md").write_text("# NC Nástroje\n- Fáza 4.\n", encoding="utf-8")
    (NASTROJE / "apps.json").write_text(
        json.dumps({"verzia_formatu": 1, "aplikacie": zaznamy, "launcher": launcher}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (KOREN / "R").mkdir(exist_ok=True)
    stavove_subory()
    strom_zakaziek()
    print("Hotovo:", NASTROJE)


if __name__ == "__main__":
    main()
