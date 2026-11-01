"""Macht die Skripte im Projektordner importierbar.

`lizenztexte_sammeln.py` holt seine Liste der Bestandteile aus
`buendel_pruefen.py`. Damit dieser Import auch unter pytest gelingt, muss der
Projektordner im Suchpfad stehen - pytest legt nur den Ordner der Testdatei
dorthin.
"""

import os
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent

if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

# Die Umgebungsvariable, mit der der Release-Workflow aus einem Übersprungen
# ein Rot macht.
PFLICHT = "AUSLIEFERUNG_PFLICHT"


def pflicht_oder_ueberspringen(grund: str | None) -> None:
    """Überspringen, wo ein Test nicht laufen kann - aber nicht in der Bauumgebung.

    Ein übersprungener Test ist nicht grün. Manche Wächter brauchen Windows
    oder die installierten Pakete; in der normalen Prüfmatrix überspringen sie
    sich, und im Bau-Job der veröffentlichten EXE steht
    AUSLIEFERUNG_PFLICHT=1 - dort wird aus dem Übersprungen ein Rot.

    `grund` ist None, wenn der Test laufen kann.
    """
    if not grund:
        return
    if os.environ.get(PFLICHT) == "1":
        pytest.fail(f"{PFLICHT} ist gesetzt, aber {grund}.")
    pytest.skip(grund)
