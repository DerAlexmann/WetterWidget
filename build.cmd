@echo off
REM ---------------------------------------------------------------------
REM Baut WetterWidget.exe neu; das Ergebnis liegt anschliessend in
REM dist\WetterWidget.exe, daneben die Lizenzhinweise.
REM
REM Voraussetzung:  pip install -r requirements-build.txt
REM
REM Die veroeffentlichte EXE entsteht nicht hier, sondern im Release-Workflow
REM (.github/workflows/release.yml) aus genau den Fassungen in
REM requirements-build.txt. Dieses Skript ist fuer den Bau von Hand.
REM ---------------------------------------------------------------------
setlocal

REM Python finden: bevorzugt ueber den Windows-Starter py, sonst python
set "PY=py -3"
py -3 --version >nul 2>nul || set "PY=python"

REM Ohne --version-file legt PyInstaller keine Versionsressource an: Produkt-
REM name, Version und Urheber blieben in den Dateieigenschaften leer. Die
REM Angaben kommen aus VERSION in wetter_widget.py, derselben Stelle, aus der
REM auch die Seite unter "Ueber" liest.
%PY% versionsinfo_erzeugen.py
if errorlevel 1 (
  echo.
  echo Die Versionsangaben liessen sich nicht erzeugen.
  pause
  exit /b 1
)

REM --exclude-module cryptography: PyInstaller packt das Paket mit ein,
REM sobald es in der Python-Installation liegt - das Widget benutzt es nicht
REM und die .exe waere um vier Megabyte groesser.
%PY% -m PyInstaller --noconfirm --onefile --windowed --clean ^
  --name "WetterWidget" ^
  --icon "wetter_widget.ico" ^
  --version-file "versionsinfo.txt" ^
  --add-data "wetter-widget.html;." ^
  --add-data "wetter_widget.ico;." ^
  --exclude-module cryptography ^
  wetter_widget.py

if errorlevel 1 (
  echo.
  echo Der Bau ist fehlgeschlagen. Fehlen die Pakete?
  echo     pip install -r requirements-build.txt
  pause
  exit /b 1
)

REM Welche Fremdkomponenten liegen wirklich im Buendel? Hier nur als Bericht:
REM Eine Python-Installation mit vielen Paketen bringt Teile mit, die in der
REM veroeffentlichten EXE nicht liegen. Im Release-Workflow laeuft derselbe
REM Aufruf mit --streng und bricht dann ab.
%PY% buendel_pruefen.py "build\WetterWidget"
if errorlevel 1 (
  echo.
  echo Die Pruefung des Buendels ist gescheitert - siehe Meldung darueber.
  pause
  exit /b 1
)

REM Die Lizenzhinweise gehoeren neben die EXE, nicht nur ins Repository: Wer
REM nur die EXE weitergibt, gibt sonst ein MIT-Werk ohne seinen Lizenztext
REM weiter. Nach jedem Kopieren eine Pruefung - cmd.exe bricht nicht von
REM selbst ab, und am Ende stuende sonst "Fertig" ueber einem halben Ergebnis.
copy /y "DRITTANBIETER-LIZENZEN.md" "dist\" >nul
if errorlevel 1 goto :kopie_gescheitert
copy /y "NOTICE" "dist\" >nul
if errorlevel 1 goto :kopie_gescheitert
copy /y "LICENSE" "dist\" >nul
if errorlevel 1 goto :kopie_gescheitert

echo.
echo Fertig: dist\WetterWidget.exe
for /f "delims=" %%H in ('%PY% -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('dist/WetterWidget.exe').read_bytes()).hexdigest())"') do echo SHA-256: %%H
pause
exit /b 0

:kopie_gescheitert
echo.
echo Die Lizenzhinweise liessen sich nicht nach dist\ kopieren.
pause
exit /b 1
