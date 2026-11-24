# Návrhy zmien v aplikáciách

Launcher kód aplikácií nemení. Čo treba doplniť, sa urobí v repozitári danej aplikácie.

## Stavový súbor pre launcher (adaptér `subor_json`) – nové aplikácie

Ak má aplikácia ukazovať stav na dlaždici (napr. Nástrojový list), po behu zapíše
`L:\_Nastroje\_stav\<app_id>\<POCITAC>.json` (atomicky: zápis do `.tmp` + `os.replace`):

```json
{ "stav": "ok", "riadky": ["Posledná záloha: dnes 11:32", "Stroje: 5 / 6"],
  "cipy": [{"text": "MB65 A", "stav": "ok"}],
  "cas": "2026-11-24T11:32:00", "pocitac": "PC-PROG1" }
```

- `stav`: `ok` | `upozornenie` | `chyba` | `nova_verzia` | `necinny`.
- Súbor starší ako `max_vek_min` (default 1440) launcher ignoruje (stav `nezname`).
- Viac počítačov = viac súborov; launcher ukáže najhorší stav a detaily z najnovšieho.

TNC Sync a Lupa už stavový súbor zapisujú (`_tnc_sync_stav.json`, `lupa_scan.json`) – tam netreba nič meniť.
