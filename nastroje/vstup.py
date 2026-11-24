"""Vstupný skript pre PyInstaller (balík `nc_nastroje` používa relatívne importy, preto sa nedá spustiť priamo)."""
from nc_nastroje.main import main

if __name__ == "__main__":
    main()
