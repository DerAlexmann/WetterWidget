@echo off
REM ---------------------------------------------------------------------
REM Baut WetterWidget.exe neu; das Ergebnis liegt anschliessend in
REM dist\WetterWidget.exe.
REM
REM Voraussetzung:  pip install -r requirements.txt
REM ---------------------------------------------------------------------
setlocal

REM Python finden: bevorzugt ueber den Windows-Starter py, sonst python
set "PY=py -3"
py -3 --version >nul 2>nul || set "PY=python"

%PY% -m PyInstaller --noconfirm --onefile --windowed --clean ^
  --name "WetterWidget" ^
  --icon "wetter_widget.ico" ^
  --add-data "wetter-widget.html;." ^
  wetter_widget.py

if errorlevel 1 (
  echo.
  echo Der Bau ist fehlgeschlagen. Fehlen die Pakete?
  echo     pip install -r requirements.txt
  pause
  exit /b 1
)

echo.
echo Fertig: dist\WetterWidget.exe
pause
