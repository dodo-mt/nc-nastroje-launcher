import json

from nc_nastroje.katalog import nacitaj_katalog


def zapis(tmp_path, obsah):
    p = tmp_path / "apps.json"
    p.write_text(obsah if isinstance(obsah, str) else json.dumps(obsah), encoding="utf-8")
    return p


def test_platny_katalog_a_neznamy_kluc(tmp_path):
    p = zapis(tmp_path, {"aplikacie": [
        {"id": "a", "nazov": "A", "typ": "exe", "zdroj": "a\1", "spustit": "a.exe", "buduci_kluc": 1,
         "prijima": [".POF", "priecinok"]}]})
    apps, chyby = nacitaj_katalog(p)
    assert chyby == [] and apps[0].prijima == [".pof", "priecinok"]


def test_chybny_zaznam_sa_preskoci(tmp_path):
    p = zapis(tmp_path, {"aplikacie": [
        {"id": "dobra", "nazov": "D", "typ": "web", "url": "http://x"},
        {"id": "zly", "nazov": "Z", "typ": "nieco"},
        {"nazov": "bez id", "typ": "exe"},
        {"id": "dobra", "nazov": "dup", "typ": "web", "url": "http://y"},
        "nie objekt"]})
    apps, chyby = nacitaj_katalog(p)
    assert [a.id for a in apps] == ["dobra"] and len(chyby) == 4


def test_poskodeny_alebo_chybajuci_subor(tmp_path):
    assert nacitaj_katalog(zapis(tmp_path, "{nie json"))[0] == []
    assert nacitaj_katalog(tmp_path / "neexistuje.json")[0] == []
    assert nacitaj_katalog(zapis(tmp_path, {"aplikacie": 5}))[0] == []
