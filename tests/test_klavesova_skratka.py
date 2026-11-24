"""Globálna klávesová skratka: parsovanie zápisu (registrácia v systéme sa tu nevolá)."""
import pytest

from nc_nastroje import klavesova_skratka as k
from nc_nastroje.config import Nastavenia


def test_parsuj_bezne_skratky():
    assert k.parsuj("Ctrl+Alt+N") == (k.MOD_CONTROL | k.MOD_ALT, ord("N"))
    assert k.parsuj("ctrl + shift + space") == (k.MOD_CONTROL | k.MOD_SHIFT, 0x20)
    assert k.parsuj("Win+F2") == (k.MOD_WIN, 0x71)
    assert k.parsuj("Ctrl+Alt+5") == (k.MOD_CONTROL | k.MOD_ALT, ord("5"))


def test_prazdne_je_vypnute():
    assert k.parsuj("") is None
    assert k.parsuj("   ") is None


@pytest.mark.parametrize("zle", ["N", "Space", "Foo+N", "Ctrl+Ž", "Ctrl+F99", "Ctrl+"])
def test_zly_zapis(zle):
    with pytest.raises(ValueError):
        k.parsuj(zle)


def test_nastavenia_skratka_predvolena_a_normalizovana():
    assert Nastavenia().klavesova_skratka == "Ctrl+Alt+N"
    assert Nastavenia(klavesova_skratka="  Ctrl+Shift+Q ").klavesova_skratka == "Ctrl+Shift+Q"
    assert Nastavenia(klavesova_skratka="").klavesova_skratka == ""
