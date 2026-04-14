@echo off
:: ============================================================
:: build.bat – Skrypt budowania NetInfo.exe
:: ============================================================
:: Wymagania wstępne (wykonaj raz, przed pierwszym budowaniem):
::   pip install -r requirements.txt
::   pip install pyinstaller
::
:: Uruchomienie:
::   build.bat
::
:: Wynik:
::   dist\NetInfo.exe  – jeden, przenośny plik wykonywalny
:: ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   NetInfo - budowanie pliku wykonywalnego
echo ============================================================
echo.

:: Sprawdź czy Python jest dostępny
python --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Python nie zostal znaleziony w PATH.
    echo Zainstaluj Python 3.10+ ze strony https://python.org
    pause
    exit /b 1
)

:: Sprawdź czy PyInstaller jest zainstalowany
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalowanie PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [BLAD] Nie mozna zainstalowac PyInstaller.
        pause
        exit /b 1
    )
)

:: Sprawdź czy wymagane pakiety są zainstalowane
echo [INFO] Sprawdzanie zaleznosci...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [BLAD] Nie mozna zainstalowac zaleznosci z requirements.txt
    pause
    exit /b 1
)

:: Usuń poprzednie artefakty budowania
echo [INFO] Czyszczenie poprzednich buildow...
if exist dist\NetInfo.exe del /f /q dist\NetInfo.exe
if exist build rmdir /s /q build
if exist NetInfo.spec del /f /q NetInfo.spec

:: Główne polecenie PyInstaller
:: --onefile        : pakuje wszystko do jednego .exe
:: --windowed       : brak czarnego okna konsoli (GUI app)
:: --name           : nazwa pliku wyjściowego
:: --clean          : usuwa cache przed budowaniem
:: --noconfirm      : nie pyta o nadpisanie
echo.
echo [INFO] Budowanie NetInfo.exe...
echo       (Moze to zajac 1-3 minuty)
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "NetInfo" ^
    --clean ^
    --noconfirm ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --hidden-import "customtkinter" ^
    --hidden-import "psutil" ^
    main.py

if errorlevel 1 (
    echo.
    echo [BLAD] Budowanie nie powiodlo sie. Sprawdz komunikaty powyzej.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Sukces! Plik gotowy:
echo   %~dp0dist\NetInfo.exe
echo ============================================================
echo.
echo Mozesz skopiowac dist\NetInfo.exe w dowolne miejsce
echo i uruchomic bez instalacji dodatkowego oprogramowania.
echo.
pause
