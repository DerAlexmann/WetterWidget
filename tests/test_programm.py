"""Wächter über das Verhalten, auf dem der Rauchtest der EXE beruht.

`--selbsttest` ist der Schalter, mit dem die gepackte EXE im Release-Workflow
ihre Seite aufbaut und endet, ohne ein Fenster zu öffnen. Bisher war er nur
dort geprüft - also erst beim Tag, mit allem, was dann schon geschehen ist.
Hier steht sein Verhalten: der gelungene Lauf, der Rückgabewert im Fehlerfall,
der Grund in der Nebendatei und der Schalter auf der Kommandozeile.

Dazu kommt ein Rückfalltest für das Entschärfen der Startwerte - die
Sicherheitskorrektur aus 1.8.3, die ohne Wächter bei der nächsten Änderung an
`seite_bauen()` lautlos verloren gehen könnte.

Diese Tests führen das Programm wirklich aus und brauchen deshalb Windows und
pywebview: `wetter_widget.py` importiert `ctypes.wintypes` und `webview`. In
der Prüfmatrix auf Linux überspringen sie sich; im Bau-Job der
veröffentlichten EXE steht AUSLIEFERUNG_PFLICHT=1, und dort werden sie zur
Pflicht - übersprungen ist nicht grün.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import WURZEL, pflicht_oder_ueberspringen

QUELLTEXT = WURZEL / "wetter_widget.py"

# So steht das Objekt in der Seite: <script>window.WIDGET_CONFIG = {...};
STARTWERTE = re.compile(r"window\.WIDGET_CONFIG = (\{.*?\});", re.DOTALL)


def programm_laeuft_hier() -> str | None:
    """Der Grund, warum das Programm hier nicht laufen kann - oder None."""
    if sys.platform != "win32":
        return f"wetter_widget.py braucht Windows (hier: {sys.platform})"
    try:
        import webview  # noqa: F401
    except Exception as fehler:                 # ImportError, aber auch mehr
        return f"pywebview ist nicht einsatzbereit: {fehler}"
    return None


@pytest.fixture(scope="module")
def programm():
    """Das Programm als Modul.

    Importiert wird erst hier und nicht oben: Sonst scheitert schon das
    Einsammeln der Tests auf Linux, und ein Fehler beim Einsammeln liest sich
    wie ein kaputter Test, nicht wie eine fehlende Umgebung.
    """
    pflicht_oder_ueberspringen(programm_laeuft_hier())
    import wetter_widget
    return wetter_widget


@pytest.fixture
def eigene_einstellungen(programm, tmp_path, monkeypatch):
    """Die Einstellungen aus einem eigenen Ordner lesen.

    Ohne das läse der Test die Einstellungsdatei neben dem Programm - die des
    Anwenders. Er wäre dann von ihrem Inhalt abhängig und vom Ort, an dem er
    gerade läuft.
    """
    pfad = tmp_path / "wetter-widget.json"
    pfad.write_text(json.dumps({"ort": "Teststadt", "sprache": "de",
                                "transparenz": 20}), encoding="utf-8")
    monkeypatch.setattr(programm, "config_path", lambda: str(pfad))
    return pfad


def startwerte_lesen(seite: str) -> dict:
    """Die Startwerte aus der aufgebauten Seite - als Objekt, nicht als Text."""
    treffer = STARTWERTE.search(seite)
    assert treffer, "In der Seite steht kein window.WIDGET_CONFIG."
    return json.loads(treffer.group(1))


def test_selbsttest_schreibt_eine_brauchbare_seite(programm, tmp_path,
                                                   eigene_einstellungen):
    """Der gelungene Lauf: Datei da, Startwerte drin, Fassung richtig.

    Genau das verlangt der Release-Workflow von der fertigen EXE. Die Datei
    entsteht nur, wenn die eingebettete HTML-Datei gefunden wird und die
    gespeicherten Werte hineinpassen.
    """
    ziel = tmp_path / "seite.html"
    assert programm.selbsttest(str(ziel)) == 0
    werte = startwerte_lesen(ziel.read_text(encoding="utf-8"))
    assert werte["version"] == programm.VERSION, (
        "Die Seite nennt eine andere Fassung als das Programm - "
        "der Workflow hält sie gegen die Versionsangaben der EXE."
    )
    assert werte["ort"] == "Teststadt", "Die gespeicherten Werte kommen nicht an."
    assert not (tmp_path / "seite.html.fehler.txt").exists(), (
        "Nach einem gelungenen Lauf darf keine Fehlerdatei liegen."
    )


def test_selbsttest_legt_den_grund_in_eine_nebendatei(programm, tmp_path,
                                                      eigene_einstellungen,
                                                      monkeypatch):
    """Scheitert der Aufbau, muss der Grund lesbar dastehen - nicht nur eine Zahl.

    Eine EXE ohne Konsole kann nichts ausgeben: Der Workflow holt sich diese
    Datei ins Protokoll. Ohne sie bliebe von einem gescheiterten Rauchtest nur
    "Exit 1".
    """
    monkeypatch.setattr(programm, "resource_path",
                        lambda name: str(tmp_path / "gibt-es-nicht.html"))
    ziel = tmp_path / "seite.html"
    assert programm.selbsttest(str(ziel)) == 1
    grund = (tmp_path / "seite.html.fehler.txt").read_text(encoding="utf-8")
    # Der ganze Rückverfolgungsbericht, nicht nur Art und Text des Fehlers:
    # Bei einem Fehler aus der Tiefe des Aufbaus ist die Zeile, in der er
    # auftrat, die halbe Antwort.
    assert "Traceback" in grund
    assert "gibt-es-nicht.html" in grund
    assert not ziel.exists(), "Eine halbe Seite darf nicht liegen bleiben."


def test_selbsttest_raeumt_den_grund_des_frueheren_laufs_weg(programm, tmp_path,
                                                             eigene_einstellungen):
    """Sonst liegt die alte Fehlerdatei neben einem gelungenen Ergebnis.

    Im Protokoll des Workflows stünde dann der Grund von gestern, und wer ihn
    liest, sucht einen Fehler, den es nicht mehr gibt.
    """
    ziel = tmp_path / "seite.html"
    alt = tmp_path / "seite.html.fehler.txt"
    alt.write_text("ein Fehler von gestern", encoding="utf-8")
    assert programm.selbsttest(str(ziel)) == 0
    assert not alt.exists(), "Die Fehlerdatei des früheren Laufs liegt noch da."


def test_selbsttest_meldet_zwei_wenn_auch_der_grund_nicht_geht(programm, tmp_path,
                                                               eigene_einstellungen):
    """Lässt sich nicht einmal der Grund schreiben, muss das ein eigener Wert sein.

    Ein Rückgabewert von 1 hieße "gescheitert, der Grund steht in der Datei" -
    und die gibt es dann nicht. Der Workflow suchte sie und schwiege.
    """
    ziel = tmp_path / "ordner-fehlt" / "seite.html"
    assert programm.selbsttest(str(ziel)) == 2


def test_der_schalter_auf_der_kommandozeile_oeffnet_kein_fenster(tmp_path):
    """Der Weg über __main__: --selbsttest muss vor main() abzweigen.

    Läuft das Programm als Unterprozess durch, ist belegt, dass der Zweig
    greift und dass kein Fenster aufgeht - sonst endete dieser Aufruf nicht
    von selbst. Genau daran hängt der Rauchtest der EXE.
    """
    pflicht_oder_ueberspringen(programm_laeuft_hier())
    ziel = tmp_path / "seite.html"
    lauf = subprocess.run([sys.executable, str(QUELLTEXT), "--selbsttest", str(ziel)],
                          cwd=tmp_path, capture_output=True, text=True, timeout=180)
    grunddatei = Path(f"{ziel}.fehler.txt")
    grund = grunddatei.read_text(encoding="utf-8") if grunddatei.exists() else ""
    assert lauf.returncode == 0, (
        f"Exit {lauf.returncode}\n{lauf.stdout}\n{lauf.stderr}\n{grund}"
    )
    assert startwerte_lesen(ziel.read_text(encoding="utf-8"))["version"]


def test_seite_bauen_entschaerft_das_ende_des_skripts(programm, tmp_path,
                                                      eigene_einstellungen):
    """Rückfalltest zur Korrektur aus 1.8.3.

    Die Startwerte landen in einem <script>-Element. Stünde in einem von ihnen
    "</script>", endete dort das Element, und der Rest des Wertes wäre Markup,
    das der Browser aufbaut. Der Ortsname kommt aus der Einstellungsdatei und
    aus der Antwort des Suchdienstes - also nicht aus der eigenen Hand.
    """
    bosheit = "</script><img src=x onerror=alert(1)>"
    seite = programm.seite_bauen({"ort": bosheit})
    assert bosheit not in seite, (
        "Der Wert steht unverändert in der Seite - das Skript-Element endet dort."
    )
    assert "<\\/script>" in seite, "Das Entschärfen fehlt."
    # Und der Wert muss trotzdem heil ankommen: Die Seite liest den maskierten
    # Schrägstrich wieder als gewöhnlichen.
    assert startwerte_lesen(seite)["ort"] == bosheit
