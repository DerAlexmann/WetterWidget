"""Sammelt die vollständigen Lizenztexte der mitgelieferten Komponenten.

`DRITTANBIETER-LIZENZEN.md` nennt die Komponenten und verlinkt sie. MIT, BSD
und die PSF-Lizenz verlangen aber mehr als einen Verweis: Bei der Weitergabe
eines Binärbündels muss der Lizenztext selbst beiliegen.

Die Texte werden nicht ins Repository gelegt, sondern beim Bauen aus den
Paketen geholt, die tatsächlich installiert sind. Das hat zwei Vorteile: Sie
passen immer zu der Fassung, die in der EXE steckt, und es gibt keine Kopie,
die beim nächsten Versionssprung still veraltet.

Welche Pakete im Bündel liegen, steht an einer Stelle - in `TEILE` in
`buendel_pruefen.py`. Dieselbe Liste prüft nach dem Bauen die Stückliste von
PyInstaller gegen das Bündel.

Aufruf:  python lizenztexte_sammeln.py [Zielordner]
"""

from __future__ import annotations

import importlib.metadata as metadata
import re
import shutil
import sys
from pathlib import Path

from buendel_pruefen import TEILE

# Dateinamen, unter denen Pakete ihre Lizenz ablegen. Die Schreibweise und der
# Ort sind nicht einheitlich: bottle legt LICENSE in den Unterordner licenses/
# der .dist-info, andere Pakete direkt hinein, und packaging bringt drei
# Dateien mit, weil es doppelt lizenziert ist.
LIZENZNAMEN = ("license", "licence", "copying", "notice")

UEBERSICHT = "00-UEBERSICHT.txt"

# Unter dieser Groesse ist eine Lizenzdatei kein Lizenztext, sondern ein
# Platzhalter oder eine leer gebliebene Datei. Die Schwelle liegt tief, weil
# eine echte Datei dieser Sammlung nur 197 Bytes hat: packaging ist doppelt
# lizenziert, und sein LICENSE verweist in zwei Saetzen auf LICENSE.APACHE und
# LICENSE.BSD, die beide mitgesammelt werden. Die MIT-Lizenz kommt auf rund 1 KB.
MINDESTGROESSE = 150

KOPF = """Lizenztexte der Komponenten im Wetter Widget
===========================================

Diese Sammlung entsteht beim Bauen der Windows-EXE aus den Paketen, die dafür
installiert wurden - die Texte passen deshalb genau zu der EXE, die daneben
liegt. Welche Komponente was tut und unter welcher Lizenz steht, steht in
DRITTANBIETER-LIZENZEN.md.

Enthalten:

"""

FUSS = """
Nicht als Text enthalten, sondern verlinkt
------------------------------------------

Ein Teil der Komponenten legt in der Installation keine eigene Lizenzdatei ab.
Ihre Texte stehen vollständig an diesen Stellen:

    Microsoft WebView2 (Microsoft.Web.WebView2.*.dll, WebView2Loader.dll)
    https://developer.microsoft.com/microsoft-edge/webview2/

    .NET-Laufzeitteile, die pythonnet mitbringt (System.*.dll, netstandard.dll)
    https://github.com/dotnet/runtime/blob/main/LICENSE.TXT

    Bestandteile des Windows-Builds von Python - OpenSSL, libffi, Expat,
    bzip2, XZ Utils, Zstandard. Lizenzseite von Python, Abschnitt
    "Licenses and Acknowledgements for Incorporated Software":
    https://docs.python.org/3/license.html

Systembibliotheken von Windows (VCRUNTIME140.dll, ucrtbase.dll,
api-ms-win-*.dll) gehören zum Betriebssystem und sind nicht aufgeführt.
"""


def lizenzdateien(paket: str) -> list[tuple[Path, str]]:
    """Die Lizenzdateien eines Pakets als (Pfad, Pfad innerhalb des Pakets).

    Gesucht wird in jeder .dist-info unterhalb des Pakets, nicht nur in der
    eigenen: setuptools legt Kopien fremder Pakete in setuptools/_vendor ab -
    jaraco.text, more_itertools, tomli, wheel und eine eigene Fassung von
    packaging -, und jede bringt ihren Lizenztext mit. Deren Module stehen in
    der Stückliste des Bündels, also gehören ihre Texte in die Sammlung.

    Der Pfad innerhalb des Pakets wird mitgegeben, weil der bloße Dateiname
    nicht unterscheidbar ist: Diese Kopien heißen alle LICENSE.
    """
    verteilung = metadata.distribution(paket)
    gefunden = []
    for eintrag in verteilung.files or ():
        rel = str(eintrag).replace("\\", "/")
        if ".dist-info" not in rel:
            continue
        if not Path(eintrag.name).stem.lower().startswith(LIZENZNAMEN):
            continue
        pfad = Path(verteilung.locate_file(eintrag))
        if pfad.is_file():
            gefunden.append((pfad, rel))
    return gefunden


def ablagename(paket: str, version: str, rel: str) -> str:
    """Der Name, unter dem ein Lizenztext in der Sammlung liegt."""
    # Der Vorsatz der eigenen .dist-info kann weg, er steht schon im Namen.
    # Alles andere bleibt stehen, flach gelegt: So ist jeder Text eindeutig und
    # man sieht ihm an, wo er herkommt.
    innen = re.sub(rf"^{re.escape(paket)}-[^/]*\.dist-info/", "", rel, flags=re.IGNORECASE)
    name = f"{paket}-{version}-{innen.replace('/', '_')}"
    return name if name.lower().endswith(".txt") else name + ".txt"


def python_lizenz() -> Path:
    """Die Lizenzdatei der Python-Installation, mit der gebaut wird."""
    pfad = Path(sys.base_prefix) / "LICENSE.txt"
    if not pfad.is_file():
        raise SystemExit(f"Die Python-Installation hat keine LICENSE.txt ({pfad}). "
                         "Ohne sie wäre die Sammlung unvollständig.")
    return pfad


def ablegen(quelle: Path, ziel: Path, name: str, schon_da: set[str]) -> str:
    """Einen Lizenztext ablegen - und dabei nichts stillschweigend verlieren."""
    # Verglichen wird ohne Ruecksicht auf Gross- und Kleinschreibung: Das
    # Dateisystem von Windows unterscheidet sie nicht, ein set aber schon -
    # LICENSE und license wuerden sich sonst ohne Meldung ueberschreiben.
    if name.lower() in schon_da:
        # Zwei Dateien gleichen Namens aus verschiedenen Ordnern einer
        # .dist-info wuerden sich sonst gegenseitig ueberschreiben, und die
        # Uebersicht fuehrte den Namen zweimal auf.
        raise SystemExit(f"Zwei Lizenzdateien wollen als {name} abgelegt werden.")
    if quelle.stat().st_size < MINDESTGROESSE:
        raise SystemExit(f"{quelle} ist nur {quelle.stat().st_size} Bytes groß - "
                         "das ist kein Lizenztext.")
    shutil.copyfile(quelle, ziel / name)
    schon_da.add(name.lower())
    return name


def main(ziel: Path) -> None:
    # Ein Ordner mit Resten eines frueheren Laufs waere tueckisch: Die
    # Dateinamen tragen die Versionsnummer, alte Texte blieben also liegen,
    # kaemen mit ins ZIP und stuenden nicht in der Uebersicht. Auf einem
    # frischen Runner ist der Ordner leer; lokal wird abgebrochen.
    if ziel.exists() and any(ziel.iterdir()):
        raise SystemExit(f"{ziel} ist nicht leer. Bitte den Ordner wegräumen - "
                         "Reste eines früheren Laufs kämen sonst mit ins ZIP.")
    ziel.mkdir(parents=True, exist_ok=True)

    zeilen: list[str] = []
    abgelegt: set[str] = set()
    bericht: list[str] = []

    for teil in TEILE:
        try:
            version = metadata.version(teil.verteilung)
        except metadata.PackageNotFoundError:
            raise SystemExit(f"Das Paket {teil.verteilung} ist nicht installiert. "
                             "Ohne es ist die Sammlung unvollständig.") from None
        if not teil.lizenztext:
            # Kein Text im Paket - das muss dastehen, statt zu fehlen. Die
            # Lizenz kommt aus den Paketdaten und nicht aus dem Gedächtnis:
            # Wechselt das Paket seine Lizenz, soll hier nichts Falsches
            # stehen bleiben.
            roh = (metadata.metadata(teil.verteilung).get("License-Expression")
                   or metadata.metadata(teil.verteilung).get("License") or "").strip()
            lizenz = roh.splitlines()[0] if roh else "keine Angabe"
            zeilen.append(f"  (kein Lizenztext im Paket: {teil.doku} {version}, "
                          f"Angabe {lizenz} in den Paketdaten)")
            bericht.append(f"  {teil.verteilung} {version}: kein Text ({lizenz})")
            continue
        dateien = lizenzdateien(teil.verteilung)
        if not dateien:
            # Lieber laut abbrechen: Eine stillschweigend fehlende Lizenz ist
            # genau der Mangel, den diese Sammlung verhindern soll.
            raise SystemExit(f"Im Paket {teil.verteilung} war keine Lizenzdatei "
                             "zu finden.")
        for datei, rel in dateien:
            name = ablagename(teil.verteilung, version, rel)
            zeilen.append(f"  {ablegen(datei, ziel, name, abgelegt)}")
        # Die Zahl gehört ins Protokoll: Gesucht wird nach Namensanfängen, und
        # legt ein Paket nach einer Aktualisierung seine Texte anders ab, fällt
        # das nur auf, wenn die Zahl sichtbar ist.
        bericht.append(f"  {teil.verteilung} {version}: {len(dateien)} Text(e)")

    quelle = python_lizenz()
    name = f"Python-{'.'.join(map(str, sys.version_info[:3]))}-{quelle.name}"
    zeilen.append(f"  {ablegen(quelle, ziel, name, abgelegt)}")

    (ziel / UEBERSICHT).write_text(KOPF + "\n".join(zeilen) + "\n" + FUSS,
                                   encoding="utf-8", newline="\n")
    print(f"{len(zeilen)} Einträge in {ziel}")
    for zeile in bericht:
        print(zeile)
    for zeile in zeilen:
        print(zeile)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "lizenztexte"))
