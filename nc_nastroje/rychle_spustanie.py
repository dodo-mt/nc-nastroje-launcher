"""Rýchle spúšťanie aplikácií z poľa zákazky: návrhy aplikácií podľa písaného textu a vlastné skratky (aliasy)."""
import re
import unicodedata
from dataclasses import dataclass

from .katalog import App
from . import zakazky

MAX_APLIKACII = 4          # najviac návrhov aplikácií nad zákazkami


@dataclass(frozen=True)
class ZhodaApp:
    """Návrh aplikácie pod poľom (rovnaké miesto ako Zhoda zákazky)."""
    app_id: str
    nazov: str
    popis: str = ""
    alias: str = ""
    ikona: str = ""
    farba: str = "#005FB8"
    je_aplikacia = True


def bez_diakritiky(text: str) -> str:
    """`Nástrojový List` -> `nastrojovy list` (malé písmená, bez diakritiky)."""
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.casefold().split())


def normalizuj_alias(alias: str) -> str:
    return bez_diakritiky(alias).replace(" ", "")


def chyba_aliasu(alias: str, app_id: str, aliasy: dict[str, str]) -> str:
    """Prázdny reťazec = alias je v poriadku. Kontroluje tvar, kolíziu s číslom zákazky a duplicitu."""
    a = normalizuj_alias(alias)
    if not a:
        return ""
    if not re.fullmatch(r"[a-z0-9._-]+", a):
        return "Skratka môže obsahovať len písmená, číslice, bodku, pomlčku a podčiarkovník."
    if zakazky.normalizuj(a) is not None or a.isdigit():
        return "Skratka nesmie vyzerať ako číslo zákazky (napr. 21930, OD21930)."
    for iny, hodnota in aliasy.items():
        if iny != app_id and normalizuj_alias(hodnota) == a:
            return f"Skratka „{alias}“ je už použitá pri inej aplikácii."
    return ""


def _poradie(app: App, alias: str, q: str) -> int | None:
    """Čím menšie, tým lepšia zhoda; None = nesedí."""
    qa = q.replace(" ", "")
    if alias and alias == qa:
        return 0
    if alias and alias.startswith(qa):
        return 1
    nazov = bez_diakritiky(app.nazov)
    if nazov.startswith(q) or nazov.replace(" ", "").startswith(q):
        return 2
    slova = nazov.split() + [s for s in re.split(r"[_\W]+", app.id.casefold()) if s]
    if any(s.startswith(q) for s in slova):
        return 3
    return None


def najdi_aplikacie(text: str, apps: list[App], aliasy: dict[str, str] | None = None,
                    maximum: int = MAX_APLIKACII) -> list[ZhodaApp]:
    """Aplikácie, ktoré sedia na písaný text (alias, začiatok názvu alebo slova). Text, ktorý je číslom zákazky
    (21930, OD21930, OD626\\001252), aplikáciu nikdy nenavrhne. `apps` majú byť už prefiltrované podľa režimu."""
    q = bez_diakritiky(text)
    if not q or zakazky.normalizuj(text) is not None or "\\" in q or "/" in q:
        return []
    aliasy = {k: normalizuj_alias(v) for k, v in (aliasy or {}).items()}
    kandidati = []
    for poz, a in enumerate(apps):
        p = _poradie(a, aliasy.get(a.id, ""), q)
        if p is not None:
            kandidati.append((p, poz, a))
    kandidati.sort(key=lambda k: (k[0], k[1]))
    return [ZhodaApp(a.id, a.nazov, a.popis, aliasy.get(a.id, ""), a.ikona or f"{a.id}.png", a.farba)
            for _, _, a in kandidati[:maximum]]
