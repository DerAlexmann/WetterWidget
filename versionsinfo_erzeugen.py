"""Erzeugt versionsinfo.txt, die Versionsangaben für die Windows-EXE.

PyInstaller legt von sich aus keine Versionsressource an: Ohne diese Datei
bleiben Produktname, Version und Urheber in den Dateieigenschaften leer, und
wer die EXE heruntergeladen hat, kann nicht nachsehen, welche Fassung vor ihm
liegt. Bei allen Fassungen bis 1.8.3 war genau das der Fall.

Die Angaben stammen aus PROGRAMM und VERSION in wetter_widget.py, gelesen per
Suchausdruck statt per Import: So braucht der Bau dafür weder pywebview noch
Windows. Die erzeugte Datei ist abgeleitet und steht in .gitignore.

Aufruf:  python versionsinfo_erzeugen.py
"""

from __future__ import annotations

import re
from pathlib import Path

HIER = Path(__file__).resolve().parent
QUELLE = HIER / "wetter_widget.py"
ZIEL = HIER / "versionsinfo.txt"

# Der Name der EXE ist nicht der Name des Programms: PROGRAMM heißt "Wetter
# Widget" mit Leerzeichen, die Datei heißt WetterWidget.exe. Beide Namen
# gehören in die Versionsressource - ProductName nennt das Programm,
# OriginalFilename die Datei. Dass dieser Wert zu --name in build.cmd und im
# Release-Workflow passt, prüft tests/test_verpackung.py.
EXE_NAME = "WetterWidget"

URHEBER = "Alexander Unverhau"
JAHR = "2026"
BESCHREIBUNG = "Wetter Widget - Messwerte und Vorhersage des DWD auf dem Desktop"
HINWEIS = "Lizenzen der mitgelieferten Komponenten: DRITTANBIETER-LIZENZEN.md"

# Die Felder bleiben ASCII: PyInstaller liest die Datei als Python-Ausdruck ein,
# und in den Dateieigenschaften sollen keine verstümmelten Umlaute stehen.
SPRACHE = 1031          # Deutsch, die Quellsprache des Programms
ZEICHENSATZ = 1200      # Unicode
GRENZE = 65535          # so weit reicht eine Stelle im Versionsfeld


def aus_quelltext(name: str) -> str:
    """Den Wert einer Konstante holen; Abbruch, wenn sie nicht genau einmal dasteht."""
    text = QUELLE.read_text(encoding="utf-8")
    # Hinten verankert: Bei "VERSION = "1.8.4" + SUFFIX" wuerde ein offener
    # Ausdruck nur den ersten Teil lesen, und die Titelleiste zeigte dann eine
    # andere Fassung als die Dateieigenschaften.
    treffer = re.findall(rf'^{name}\s*=\s*"([^"]+)"\s*(?:#.*)?$', text, re.MULTILINE)
    if len(treffer) != 1:
        raise SystemExit(f"{name} steht {len(treffer)}-mal in {QUELLE.name}, "
                         "erwartet war genau eine Zeile.")
    if not treffer[0].isascii():
        raise SystemExit(f"{name} = {treffer[0]!r} enthält Zeichen außerhalb von ASCII.")
    return treffer[0]


def vierstellig(version: str) -> tuple[int, int, int, int]:
    """Aus "1.8.3" wird (1, 8, 3, 0), denn Windows erwartet immer vier Zahlen."""
    if not re.fullmatch(r"\d+(\.\d+){0,3}", version):
        raise SystemExit(f"VERSION {version!r} muss die Form 1.2.3 haben. Vorabfassungen "
                         "wie 1.2.3rc1 kann die Versionsressource nicht abbilden.")
    zahlen = [int(teil) for teil in version.split(".")]
    if max(zahlen) > GRENZE:
        raise SystemExit(f"VERSION {version!r}: Jede Stelle darf höchstens {GRENZE} sein.")
    return tuple(zahlen + [0] * (4 - len(zahlen)))


def inhalt(name: str, version: str) -> str:
    haupt, neben, flick, bau = vierstellig(version)
    tabelle = f"{SPRACHE:04x}{ZEICHENSATZ:04x}".upper()
    # Auch der Dateiname geht durch repr(): PyInstaller liest die Datei als
    # Python-Ausdruck ein, und ein Apostroph im Programmnamen wuerde sie sonst
    # mitten im String aufbrechen.
    dateiname = f"{EXE_NAME}.exe"
    return f"""# Von versionsinfo_erzeugen.py erstellt - nicht von Hand aendern.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({haupt}, {neben}, {flick}, {bau}),
    prodvers=({haupt}, {neben}, {flick}, {bau}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '{tabelle}',
        [StringStruct('CompanyName', '{URHEBER}'),
        StringStruct('FileDescription', '{BESCHREIBUNG}'),
        StringStruct('FileVersion', {version!r}),
        StringStruct('InternalName', {EXE_NAME!r}),
        StringStruct('LegalCopyright',
                     'Copyright (c) {JAHR} {URHEBER} - MIT-Lizenz - '
                     'Erstellt mit Unterstuetzung von Claude AI'),
        StringStruct('OriginalFilename', {dateiname!r}),
        StringStruct('ProductName', {name!r}),
        StringStruct('ProductVersion', {version!r}),
        StringStruct('Comments', '{HINWEIS}')])
      ]),
    VarFileInfo([VarStruct('Translation', [{SPRACHE}, {ZEICHENSATZ}])])
  ]
)
"""


def main() -> None:
    # Erst weg, dann neu: Bricht das Erzeugen ab, soll keine Datei von vorher
    # liegen bleiben, die ein spaeterer Bau stillschweigend mitnimmt.
    ZIEL.unlink(missing_ok=True)
    name = aus_quelltext("PROGRAMM")
    version = aus_quelltext("VERSION")
    ZIEL.write_text(inhalt(name, version), encoding="utf-8", newline="\n")
    print(f"geschrieben: {ZIEL}  ({name} {version})")


if __name__ == "__main__":
    main()
