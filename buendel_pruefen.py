"""Prüft, welche Fremdkomponenten wirklich in der gebauten EXE liegen.

`DRITTANBIETER-LIZENZEN.md` ist nur so viel wert, wie sie vollständig ist. Eine
neue Fassung von pywebview oder PyInstaller kann ein Paket mitbringen, das
bisher nicht im Bündel lag - und eine Lizenz, die dann nirgends genannt ist.
Dieses Skript liest die Stückliste, die PyInstaller beim Bauen schreibt, und
hält sie gegen die Liste unten.

PyInstaller legt die Stückliste als `build/<Name>/PYZ-00.toc` (reine
Python-Module) und `PKG-00.toc` (Binärteile und Daten) ab. Gelesen wird mit
einem Suchausdruck und nicht per `literal_eval`: Dann ist es gleich, ob
PyInstaller das Format der Datei einmal ändert.

Aufruf:
    python buendel_pruefen.py build/WetterWidget            # melden
    python buendel_pruefen.py build/WetterWidget --streng   # und abbrechen

Ohne `--streng` wird nur berichtet. Das ist für den Bau von Hand gedacht: Wer
in seiner Python-Installation noch andere Pakete hat, bekommt sie von
PyInstaller mit ins Bündel gepackt, und das ist kein Mangel des Projekts. Die
veröffentlichte EXE entsteht im Release-Workflow aus `requirements-build.txt`
heraus - dort läuft der Aufruf mit `--streng`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


class Teil(NamedTuple):
    """Eine Fremdkomponente, wie sie an drei Stellen auftaucht."""

    verteilung: str                 # Name des Pakets für pip und importlib.metadata
    ordner: tuple[str, ...]         # so heißt es in der Stückliste des Bündels
    doku: str                       # so steht es in DRITTANBIETER-LIZENZEN.md
    lizenztext: bool                # liegt im Paket selbst ein Lizenztext?


# Was die EXE aus dem Python-Umfeld mitbringt, wenn nur
# requirements-build.txt installiert ist. Die Kette dahinter:
# pywebview -> pythonnet -> clr_loader -> cffi -> pycparser, dazu bottle,
# proxy_tools und typing_extensions; PyInstaller zieht setuptools mit und legt
# seinen Bootloader dazu.
TEILE = (
    Teil("pywebview", ("webview",), "pywebview", True),
    Teil("pythonnet", ("pythonnet", "clr"), "pythonnet", True),
    Teil("clr_loader", ("clr_loader",), "clr_loader", True),
    Teil("cffi", ("cffi", "_cffi_backend"), "cffi", True),
    Teil("pycparser", ("pycparser",), "pycparser", True),
    Teil("bottle", ("bottle",), "bottle", True),
    # proxy_tools bringt keine Lizenzdatei mit - nur die Angabe "MIT" in den
    # Paketdaten. Das steht so in DRITTANBIETER-LIZENZEN.md und in der
    # Übersicht der Lizenztexte; stillschweigend fehlen soll es nicht.
    Teil("proxy_tools", ("proxy_tools",), "proxy_tools", False),
    Teil("typing_extensions", ("typing_extensions",), "typing_extensions", True),
    Teil("setuptools", ("setuptools", "_distutils_hack", "pkg_resources"),
         "setuptools", True),
    # packaging kommt über setuptools._normalization mit und ist zugleich eine
    # Abhängigkeit von PyInstaller - es liegt also auch dann im Bündel, wenn
    # nur requirements-build.txt installiert ist.
    Teil("packaging", ("packaging",), "packaging", True),
    Teil("pyinstaller", ("PyInstaller",), "PyInstaller", True),
)

# Ordner in site-packages, die zu bekannten Teilen gehören.
BEKANNT = {ordner for teil in TEILE for ordner in teil.ordner}

STUECKLISTEN = ("PYZ-00.toc", "PKG-00.toc")

# Ohne pywebview gibt es kein Fenster - dieses Paket muss im Bündel liegen.
# Fehlt es, ist nicht das Bündel falsch, sondern die Prüfung: Dann hat der
# Suchausdruck unten nicht gegriffen, etwa weil PyInstaller das Format der
# Stückliste geändert hat. Eine Prüfung, die nichts findet, ist sonst grün und
# prüft nichts.
PFLICHTTEIL = "webview"

# Ein Posten der Stückliste, der aus site-packages stammt - der Rest kommt aus
# der Standardbibliothek oder dem Projekt selbst und gehört niemand anderem.
AUS_PAKETEN = re.compile(r"site-packages[\\/]+([A-Za-z0-9_.+-]+)")


def normieren(roh: str) -> str:
    """Aus einem Pfadstück den Namen des Pakets machen.

    `markupsafe-3.0.4.dist-info` wird zu `markupsafe`, `bottle.py` zu
    `bottle`, `_cffi_backend.cp314-win_amd64.pyd` zu `_cffi_backend`.
    """
    name = re.sub(r"-[0-9][^-]*\.dist-info$", "", roh)
    return name.split(".")[0]


def aus_stueckliste(bauordner: Path) -> dict[str, int]:
    """Die Pakete im Bündel, mit der Zahl ihrer Posten."""
    gefunden: dict[str, int] = {}
    gelesen = 0
    for name in STUECKLISTEN:
        pfad = bauordner / name
        if not pfad.is_file():
            continue
        gelesen += 1
        # errors="replace": In der Stückliste stehen die Pfade der Bauumgebung,
        # und ein Benutzername mit Umlaut darf das Lesen nicht abbrechen. Ein
        # ersetztes Zeichen kann einen Paketnamen zerlegen - der fällt dann als
        # unbekannt auf, statt still durchzugehen.
        text = pfad.read_text(encoding="utf-8", errors="replace")
        for roh in AUS_PAKETEN.findall(text):
            paket = normieren(roh)
            gefunden[paket] = gefunden.get(paket, 0) + 1
    if not gelesen:
        raise SystemExit(f"In {bauordner} liegt keine Stückliste "
                         f"({', '.join(STUECKLISTEN)}). Wurde die EXE gebaut?")
    return gefunden


def main(argumente: list[str]) -> int:
    streng = "--streng" in argumente
    # Ein Tippfehler wie --strenge wuerde die Pruefung sonst stillschweigend
    # abschalten: Die Option faellt aus der Pfadliste heraus und "streng"
    # bliebe falsch.
    unbekannt = [a for a in argumente if a.startswith("--") and a != "--streng"]
    if unbekannt:
        raise SystemExit(f"Unbekannte Option: {' '.join(unbekannt)}\n{__doc__}")
    pfade = [a for a in argumente if not a.startswith("--")]
    if len(pfade) != 1:
        raise SystemExit(__doc__)

    gefunden = aus_stueckliste(Path(pfade[0]))
    if PFLICHTTEIL not in gefunden:
        raise SystemExit(
            f"In der Stückliste steht kein Posten zu {PFLICHTTEIL}. "
            "Entweder liegt pywebview nicht im Bündel - dann liefe das "
            "Programm nicht -, oder der Suchausdruck greift nicht mehr. "
            "In beiden Fällen prüft dieses Skript sonst nichts und wäre "
            "trotzdem grün."
        )
    fremd = sorted(name for name in gefunden if name not in BEKANNT)

    for teil in TEILE:
        posten = sum(gefunden.get(ordner, 0) for ordner in teil.ordner)
        # Ein Teil, das nicht mehr auftaucht, ist kein Fehler des Baus: Eine
        # neue Fassung von pywebview kann ohne bottle auskommen. Gemeldet wird
        # es, damit die Lizenzdatei nicht auf Dauer mehr nennt als drinsteckt.
        zustand = f"{posten} Posten" if posten else "nicht im Bündel"
        print(f"  {teil.doku:20s} {zustand}")

    if not fremd:
        print("Keine unbekannten Fremdkomponenten im Bündel.")
        return 0

    print()
    print("Nicht in TEILE und damit auch nicht in DRITTANBIETER-LIZENZEN.md:")
    for name in fremd:
        print(f"  {name}  ({gefunden[name]} Posten)")
    # Die Meldungen bleiben ASCII: Sie landen im Protokoll des Workflows und
    # in der Windows-Konsole, und beide stellen Umlaute gern falsch dar.
    if not streng:
        print()
        print("Nur ein Hinweis: Diese Teile kommen aus der Python-Installation, "
              "mit der hier gebaut wurde.")
        print("Die veroeffentlichte EXE entsteht im Release-Workflow aus "
              "requirements-build.txt.")
        return 0
    print()
    print("Abbruch: Jede Fremdkomponente im Buendel muss in "
          "DRITTANBIETER-LIZENZEN.md stehen.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
