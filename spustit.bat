@echo off
rem Spustac NC Nastroje (vyvoj). Dvojklik spusti aplikaciu bez konzolneho okna.
rem Parameter "-k" spusti s konzolou (vypisy chyb): spustit.bat -k
cd /d "%~dp0"

where pythonw >nul 2>nul
if errorlevel 1 (
    echo Python sa nenasiel. Nainstaluj Python 3.11+ a pridaj ho do PATH.
    pause
    exit /b 1
)

if /i "%~1"=="-k" (
    python -m nc_nastroje.main
    if errorlevel 1 pause
) else (
    start "" pythonw -m nc_nastroje.main
)
