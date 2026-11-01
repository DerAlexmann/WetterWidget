"""Wächter für die Auslieferung: Lizenzen, Versionsangaben, fester Bau.

Jede Vorkehrung der Auslieferung verfällt still, wenn niemand darüber wacht.
Ein Lizenzhinweis, der eine Komponente nicht nennt, fällt niemandem auf; ein
Release-Job, dessen Bedingung verkehrt herum steht, auch nicht. Deshalb steht
hier zu jedem Punkt ein Test.

Die Tests lesen Dateien und führen das Programm nicht aus: Sie brauchen weder
pywebview noch Windows und laufen deshalb in der normalen Prüfmatrix mit. Was
die Bauumgebung braucht - die installierten Pakete für die Lizenztexte -,
überspringt sich selbst und wird im Release-Workflow über
AUSLIEFERUNG_PFLICHT=1 zur Pflicht.

Gegengeprüft wurde jeder Wächter durch eine absichtliche Verschlechterung:
Was nicht rot wird, ist kein Wächter.
"""

from __future__ import annotations

import ast
import importlib.metadata as metadata
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PFLICHT, pflicht_oder_ueberspringen

from buendel_pruefen import TEILE, normieren

WURZEL = Path(__file__).resolve().parent.parent
LIZENZDATEI = WURZEL / "DRITTANBIETER-LIZENZEN.md"
NOTICE = WURZEL / "NOTICE"
SECURITY = WURZEL / "SECURITY.md"
CHANGELOG = WURZEL / "CHANGELOG.md"
QUELLTEXT = WURZEL / "wetter_widget.py"
PYPROJECT = WURZEL / "pyproject.toml"
BUILD_CMD = WURZEL / "build.cmd"
LAUFZEIT = WURZEL / "requirements.txt"
FESTER_BAU = WURZEL / "requirements-build.txt"
DEPENDABOT = WURZEL / ".github" / "dependabot.yml"
WORKFLOW_ORDNER = WURZEL / ".github" / "workflows"
RELEASE_YML = WORKFLOW_ORDNER / "release.yml"
CI_YML = WORKFLOW_ORDNER / "ci.yml"
READMES = (WURZEL / "README.md", WURZEL / "README.en.md")

# Alle Workflow-Dateien, keine feste Liste: Eine dritte Datei - fuer Labels,
# Automerge, was auch kommt - waere sonst nie geprueft, und das ohne jede
# Fehlermeldung. Deshalb auch .yaml, nicht nur .yml.
WORKFLOWS = sorted(pfad.name for pfad in WORKFLOW_ORDNER.glob("*.y*ml"))

# Die englische Haelfte der Lizenzdatei beginnt mit dieser Ueberschrift.
ENGLISCHE_UEBERSCHRIFT = "# Licenses of third-party components"

# Der Name, unter dem die EXE entsteht - in build.cmd, im Release-Workflow und
# in den Versionsangaben muss derselbe stehen.
EXE = "WetterWidget"

# Teile des Buendels, die nicht aus einem Python-Paket kommen und deshalb
# nicht in TEILE stehen. Sie muessen trotzdem in beiden Sprachen als
# Tabellenzeile dastehen, sonst fehlt in der Lizenzdatei die halbe EXE.
OHNE_PAKET = (
    "Python 3.14",
    "WebView2",
    "netstandard.dll",
    "OpenSSL",
    "libffi",
    "Expat",
    "bzip2",
    "XZ Utils",
    "Zstandard",
)


# --------------------------------------------------------------------------
# Hilfen
# --------------------------------------------------------------------------

def ohne_kommentare(text: str) -> str:
    """Kommentarzeilen weg - ein Kommentar ist kein Beweis."""
    return "\n".join(z for z in text.splitlines() if not z.lstrip().startswith("#"))


def build_cmd_ohne_kommentare() -> str:
    """build.cmd ohne seine REM-Zeilen.

    In den Kommentaren von build.cmd stehen fast alle Namen, auf die es hier
    ankommt - "--version-file", "DRITTANBIETER-LIZENZEN.md",
    "buendel_pruefen.py". Ein Test, der den ganzen Text durchsucht, bleibt
    deshalb grün, wenn der Befehl verschwindet und nur der Kommentar bleibt.
    """
    text = BUILD_CMD.read_text(encoding="cp1252")
    return "\n".join(z for z in text.splitlines()
                     if not z.lstrip().lower().startswith("rem"))


def fremde_verweise(text: str) -> list[tuple[str, str]]:
    """Jedes uses: auf eine Action ausserhalb von actions/*, als (Zeile, Verweis)."""
    gefunden = []
    for zeile in ohne_kommentare(text).splitlines():
        # Nicht nach "uses:" als Teilzeichenkette suchen: "uses : x" und
        # '"uses": x' sind gueltiges YAML und wuerden still uebersprungen.
        # Der Blick zurueck haelt "reuses:" und aehnliche Schluessel draussen.
        treffer = re.search(r"""(?<![\w"'-])["']?uses["']?\s*:\s*(\S.*)""", zeile)
        if not treffer:
            continue
        verweis = treffer.group(1).strip().strip("'\"")
        # Eigene Actions im Repository (./.github/actions/...) sind nicht fremd
        # und lassen sich auch nicht festnageln - sie liegen in diesem Commit.
        if verweis.startswith("./"):
            continue
        # Nur die echte Organisation actions: "actions/../anderswo" nicht.
        if verweis.lower().startswith("actions/") and ".." not in verweis:
            continue
        gefunden.append((zeile, verweis))
    return gefunden


def jobs_zerlegen(text: str) -> dict[str, str]:
    """Die Jobs eines Workflows als Name -> Block, gelesen erst ab "jobs:".

    Erst ab "jobs:", weil "push" und "workflow_dispatch" unter "on:" genauso
    eingerueckt sind und keine Jobs sind.
    """
    zeilen = ohne_kommentare(text).splitlines()
    for nummer, zeile in enumerate(zeilen):
        if zeile.rstrip() == "jobs:":
            zeilen = zeilen[nummer + 1:]
            break
    else:
        raise AssertionError("Der Workflow hat keinen Abschnitt 'jobs:'.")

    jobs: dict[str, list[str]] = {}
    aktuell = None
    for zeile in zeilen:
        kopf = re.fullmatch(r"  ([A-Za-z][\w-]*):\s*", zeile)
        if kopf:
            aktuell = kopf.group(1)
            jobs[aktuell] = []
        elif aktuell is not None:
            jobs[aktuell].append(zeile)
    return {name: "\n".join(block) for name, block in jobs.items()}


def schritt(block: str, name: str) -> str:
    """Ein einzelner Schritt eines Jobs, am Namen gefunden.

    Gebraucht wird das, weil eine Suche über den ganzen Job zu leicht gruen
    bleibt: "Test-Path" steht auch im Rauchtest, "dist\\SHA256SUMS.txt" auch in
    dem Schritt, der die Datei erst schreibt. Wer wissen will, ob *dieser*
    Schritt etwas prueft, muss ihn allein ansehen.
    """
    teile = re.split(r"\n      - ", "\n" + block)
    passend = [t for t in teile if t.lstrip().startswith(f"name: {name}")]
    assert len(passend) == 1, (
        f"Der Schritt {name!r} steht {len(passend)}-mal im Job."
    )
    return passend[0]


def laufblock(abschnitt: str) -> str | None:
    """Der Inhalt eines mehrzeiligen run:-Blocks, sonst None.

    "run: >" faltet alles zu einem Befehl zusammen und "run: python ..." ist
    einer - dort schlaegt der Rueckgabewert von selbst durch.
    """
    if "run: |" not in abschnitt:
        return None
    return abschnitt.split("run: |", 1)[1]


def pakete(datei: Path) -> set[str]:
    """Die Paketnamen aus einer requirements-Datei."""
    namen = set()
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#")[0].strip()
        if zeile:
            namen.add(re.split(r"[=<>!~;\[ ]", zeile)[0])
    return namen


def tabellenzeile(text: str, name: str) -> str | None:
    """Die Tabellenzeile eines Bestandteils - die ganze Zeile, nicht ein Wort.

    Gesucht wird eine Zeile, die mit | beginnt und mindestens drei | hat, also
    wirklich Bestandteil, Lizenz und Fundstelle nennt. Eine Erwaehnung
    irgendwo im Text genuegt nicht: Genau so wird ein Test gruen, obwohl die
    Tabellenzeile gelöscht wurde.
    """
    for zeile in text.splitlines():
        if zeile.startswith("|") and zeile.count("|") >= 4 and name in zeile:
            return zeile
    return None


def version_aus_quelltext() -> str:
    treffer = re.findall(r'^VERSION\s*=\s*"([^"]+)"', QUELLTEXT.read_text(encoding="utf-8"),
                         re.MULTILINE)
    assert len(treffer) == 1, f"VERSION steht {len(treffer)}-mal in {QUELLTEXT.name}."
    return treffer[0]


def skript_laden(name: str):
    """Ein Skript neben dem Programm als Modul laden, ohne es zu importieren."""
    pfad = WURZEL / name
    spec = importlib.util.spec_from_file_location(pfad.stem, pfad)
    assert spec is not None and spec.loader is not None
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="module")
def lizenztext() -> str:
    return LIZENZDATEI.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def haelften(lizenztext: str) -> tuple[str, str]:
    """Deutscher und englischer Teil der Lizenzdatei."""
    assert ENGLISCHE_UEBERSCHRIFT in lizenztext, (
        "Die Lizenzdatei hat keinen englischen Teil mehr."
    )
    deutsch, englisch = lizenztext.split(ENGLISCHE_UEBERSCHRIFT, 1)
    return deutsch, englisch


@pytest.fixture(scope="module")
def release() -> str:
    return ohne_kommentare(RELEASE_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def release_jobs() -> dict[str, str]:
    return jobs_zerlegen(RELEASE_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def versionsinfo():
    return skript_laden("versionsinfo_erzeugen.py")


@pytest.fixture(scope="module")
def sammler():
    return skript_laden("lizenztexte_sammeln.py")


# --------------------------------------------------------------------------
# Lizenzen der Fremdkomponenten
# --------------------------------------------------------------------------

@pytest.mark.parametrize("teil", TEILE, ids=[t.doku for t in TEILE])
def test_lizenzdatei_nennt_jedes_paket_im_buendel(teil, haelften):
    """Jedes Paket aus TEILE braucht eine Tabellenzeile - in beiden Sprachen.

    Verlangt wird die ganze Zeile. Ein Test, der nur nach dem Namen irgendwo
    im Text sucht, bleibt gruen, wenn jemand die Tabellenzeile loescht und der
    Name noch in einem Absatz steht.
    """
    deutsch, englisch = haelften
    for sprache, text in (("deutschen", deutsch), ("englischen", englisch)):
        zeile = tabellenzeile(text, f"**{teil.doku}**")
        assert zeile, (f"Im {sprache} Teil fehlt die Tabellenzeile zu {teil.doku}. "
                       "Es liegt im Bündel, also muss es dastehen.")


@pytest.mark.parametrize("bestandteil", OHNE_PAKET)
def test_lizenzdatei_nennt_die_teile_ohne_paket(bestandteil, haelften):
    """Die EXE enthält mehr als Python-Pakete: Laufzeit, WebView2, .NET."""
    deutsch, englisch = haelften
    for sprache, text in (("deutschen", deutsch), ("englischen", englisch)):
        assert tabellenzeile(text, bestandteil), (
            f"Im {sprache} Teil fehlt die Tabellenzeile zu {bestandteil}."
        )


def test_lizenzdatei_grenzt_die_systembibliotheken_ab(haelften):
    """Was zum Betriebssystem gehört, muss ausdrücklich abgegrenzt sein."""
    deutsch, englisch = haelften
    for text in (deutsch, englisch):
        assert "VCRUNTIME140.dll" in text
        assert "api-ms-win-" in text


def test_lizenzdatei_nennt_die_ausnahme_von_pyinstaller(haelften):
    """Ohne die Ausnahme müsste das Bündel unter die GPL - das ist der Kernsatz.

    Geprüft wird nicht nur, dass PyInstaller vorkommt: Die Zeile muss GPL und
    Ausnahme zusammen nennen, sonst steht dort am Ende nur "GPLv2" und die
    Begründung fehlt.
    """
    deutsch, englisch = haelften
    zeile_de = tabellenzeile(deutsch, "**PyInstaller**")
    zeile_en = tabellenzeile(englisch, "**PyInstaller**")
    assert zeile_de and "GPLv2" in zeile_de and "Ausnahme" in zeile_de
    assert zeile_en and "GPLv2" in zeile_en and "exception" in zeile_en


def test_lizenzdatei_haelt_das_gesamtwerk_bei_mit(haelften):
    """Die Lizenz des Gesamtwerks samt Begründung gehört in beide Hälften."""
    deutsch, englisch = haelften
    assert "MIT" in deutsch and "Warum bleibt alles MIT?" in deutsch
    assert "MIT" in englisch and "Why does everything stay MIT?" in englisch


def test_lizenzdatei_trennt_laufzeit_und_sdk_von_webview2(haelften):
    """Die Evergreen-Laufzeit steckt nicht in der EXE - das darf nicht verwischen.

    Stünde dort nur "WebView2", läse es sich wie ein mitgelieferter Browser.
    """
    deutsch, englisch = haelften
    assert "Evergreen" in deutsch and "Evergreen" in englisch


def test_lizenzdatei_nennt_die_gebaute_python_fassung(haelften, release_jobs):
    """Die Fassung in der Tabelle muss die sein, mit der gebaut wird.

    Sonst steht in der Lizenzdatei irgendwann eine Reihe, die niemand mehr
    baut - und der Verweis auf deren Lizenzseite geht am Bündel vorbei.
    """
    treffer = re.search(r'python-version:\s*"([\d.]+)"', release_jobs["windows-exe"])
    assert treffer, "Der Bau-Job nennt keine Python-Fassung."
    reihe = ".".join(treffer.group(1).split(".")[:2])
    deutsch, englisch = haelften
    for text in (deutsch, englisch):
        assert tabellenzeile(text, f"Python {reihe}"), (
            f"Der Bau nutzt Python {reihe}; die Lizenzdatei nennt eine andere Reihe."
        )


def test_lizenzdatei_verweist_nur_auf_absolute_adressen(lizenztext):
    """Ein Verweis auf eine Datei im Repository erreicht den Anwender nicht."""
    for ziel in re.findall(r"\]\(([^)]+)\)", lizenztext):
        if ziel.startswith("#"):          # Sprung innerhalb der Datei
            continue
        assert ziel.startswith("https://"), (
            f"{ziel} ist keine absolute Adresse. Wer nur die EXE hat, "
            "kommt damit nirgendwohin."
        )


def test_jeder_doku_name_kommt_nur_einmal_vor():
    """Zwei Teile mit demselben Namen in der Doku wären nicht unterscheidbar."""
    namen = [teil.doku for teil in TEILE]
    assert len(namen) == len(set(namen)), f"Doppelte Namen in TEILE: {namen}"


def test_notice_verweist_auf_die_lizenzdatei():
    """NOTICE liegt neben der EXE und muss den Weg zur vollen Liste zeigen."""
    text = NOTICE.read_text(encoding="utf-8")
    assert "DRITTANBIETER-LIZENZEN.md" in text
    assert f"{EXE}-lizenztexte.zip" in text
    # Der Hinweis auf die KI-Mithilfe gehoert zu jedem Copyright-Vermerk.
    assert "Claude AI" in text


@pytest.mark.parametrize("datei", READMES, ids=[p.name for p in READMES])
def test_readmes_verweisen_auf_die_lizenzdatei(datei):
    """Die Datei muss den Anwender erreichen, nicht nur das Repository."""
    text = datei.read_text(encoding="utf-8")
    assert "DRITTANBIETER-LIZENZEN.md" in text, (
        f"{datei.name} verweist nicht auf die Lizenzen der Fremdkomponenten."
    )


@pytest.mark.parametrize("datei", READMES, ids=[p.name for p in READMES])
def test_erst_start_hinweis_steht_in_beiden_readmes(datei):
    """Jedes Release mit unsignierter EXE braucht diesen Hinweis.

    Verlangt werden alle drei Teile: SmartScreen, der Virenschutz und der Weg
    zur Prüfsumme. Ein "oder" zwischen ihnen hiesse, dass zwei fehlen dürfen.
    """
    text = datei.read_text(encoding="utf-8")
    assert "SmartScreen" in text
    assert "SHA-256" in text
    assert "SHA256SUMS.txt" in text, (
        f"{datei.name} sagt nicht, woher die Prüfsumme kommt."
    )


# --------------------------------------------------------------------------
# Lizenztexte einsammeln
# --------------------------------------------------------------------------

def sammeln_moeglich() -> str | None:
    """Der Grund, warum das Einsammeln hier nicht laufen kann - oder None."""
    for teil in TEILE:
        try:
            metadata.distribution(teil.verteilung)
        except metadata.PackageNotFoundError:
            return f"{teil.verteilung} ist in dieser Umgebung nicht installiert"
    if not (Path(sys.base_prefix) / "LICENSE.txt").is_file():
        return "die Python-Installation hat keine LICENSE.txt"
    return None


def nur_mit_bauumgebung() -> None:
    """Überspringen, wo das Sammeln nicht laufen kann - aber nicht im Bau-Job."""
    pflicht_oder_ueberspringen(sammeln_moeglich())


def test_pflicht_macht_aus_einem_uebersprungen_ein_rot(monkeypatch):
    """Der Wächter über die Wächter - er trägt die Hälfte der Prüfungen.

    Fünf Tests hängen an dieser Hilfe. Wäre die Bedingung verkehrt herum oder
    hieße die Umgebungsvariable im Workflow anders, überspränge sich alles
    auch im Bau-Job - und das sähe von außen genauso aus wie ein grüner Lauf.
    """
    monkeypatch.setenv(PFLICHT, "1")
    # Nicht mit pytest.raises: Überspringt die Hilfe hier, dann hebt
    # pytest.skip() diesen Test selbst auf - und ein übersprungener Test wird
    # nicht rot. Der Fall muss ausdrücklich abgefangen werden.
    try:
        pflicht_oder_ueberspringen("ein Paket fehlt")
    except pytest.fail.Exception as fehler:
        assert "ein Paket fehlt" in str(fehler)
    except pytest.skip.Exception:
        pytest.fail(f"Mit {PFLICHT}=1 wurde übersprungen statt rot.")
    else:
        pytest.fail("Die Hilfe lief über den Grund hinweg.")

    # Ohne die Variable - die normale Prüfmatrix - wird übersprungen.
    monkeypatch.delenv(PFLICHT)
    with pytest.raises(pytest.skip.Exception):
        pflicht_oder_ueberspringen("ein Paket fehlt")

    # Und wo es keinen Grund gibt, läuft der Test einfach weiter.
    monkeypatch.setenv(PFLICHT, "1")
    pflicht_oder_ueberspringen(None)


def test_der_bau_job_setzt_genau_diese_umgebungsvariable(release_jobs):
    """Ein Tippfehler im Workflow wäre von außen nicht zu sehen."""
    block = schritt(release_jobs["windows-exe"], "Waechter der Auslieferung")
    assert f'{PFLICHT}: "1"' in block, (
        f"Der Bau-Job setzt {PFLICHT} nicht - dann überspringt sich dort alles, "
        "was die Bauumgebung braucht."
    )


def test_lizenztexte_werden_vollstaendig_eingesammelt(sammler, tmp_path):
    """Für jedes Paket mit Lizenztext entsteht eine Datei, dazu die Übersicht."""
    nur_mit_bauumgebung()
    ziel = tmp_path / "lizenztexte"
    sammler.main(ziel)

    dateien = {pfad.name for pfad in ziel.iterdir()}
    assert sammler.UEBERSICHT in dateien
    for teil in TEILE:
        if not teil.lizenztext:
            continue
        passend = [name for name in dateien if name.startswith(f"{teil.verteilung}-")]
        assert passend, f"Kein Lizenztext für {teil.verteilung} eingesammelt."
    # Die Python-Lizenz gehoert dazu: Die Laufzeit liegt mit in der EXE.
    assert any(name.startswith("Python-") for name in dateien)

    uebersicht = (ziel / sammler.UEBERSICHT).read_text(encoding="utf-8")
    for name in dateien - {sammler.UEBERSICHT}:
        assert name in uebersicht, f"{name} liegt im Ordner, steht aber nicht in der Übersicht."
    # Was ohne Text bleibt, muss dastehen statt zu fehlen.
    for teil in TEILE:
        if not teil.lizenztext:
            assert teil.doku in uebersicht


def test_uebersicht_verweist_auf_die_nicht_beiliegenden_texte(sammler, tmp_path):
    """WebView2, .NET und die Teile der Python-Laufzeit liegen nur als Verweis bei."""
    nur_mit_bauumgebung()
    ziel = tmp_path / "lizenztexte"
    sammler.main(ziel)
    uebersicht = (ziel / sammler.UEBERSICHT).read_text(encoding="utf-8")
    assert "WebView2" in uebersicht
    assert "docs.python.org" in uebersicht
    assert "DRITTANBIETER-LIZENZEN.md" in uebersicht


def test_lizenztexte_brechen_ohne_python_lizenz_ab(sammler, tmp_path, monkeypatch):
    """Fehlt die LICENSE.txt der Python-Installation, ist die Sammlung unvollständig.

    Sie darf dann nicht einfach kleiner ausfallen.
    """
    nur_mit_bauumgebung()
    monkeypatch.setattr(sammler.sys, "base_prefix", str(tmp_path / "kein-python"))
    with pytest.raises(SystemExit) as fehler:
        sammler.main(tmp_path / "lizenztexte")
    assert "LICENSE.txt" in str(fehler.value)


def test_lizenztexte_brechen_bei_fehlender_lizenzdatei_ab(sammler, tmp_path, monkeypatch):
    """Ein Paket ohne Lizenzdatei muss laut abbrechen, nicht stillschweigend fehlen."""
    nur_mit_bauumgebung()
    monkeypatch.setattr(sammler, "lizenzdateien", lambda paket: [])
    with pytest.raises(SystemExit) as fehler:
        sammler.main(tmp_path / "lizenztexte")
    assert "keine Lizenzdatei" in str(fehler.value)


def test_lizenztexte_brechen_bei_unbekanntem_paket_ab(sammler, tmp_path, monkeypatch):
    """Steht ein Paket in TEILE, das nicht installiert ist, bricht der Bau ab."""
    nur_mit_bauumgebung()
    erfunden = TEILE[0]._replace(verteilung="gibt-es-nicht-123")
    monkeypatch.setattr(sammler, "TEILE", (erfunden,))
    with pytest.raises(SystemExit) as fehler:
        sammler.main(tmp_path / "lizenztexte")
    assert "nicht installiert" in str(fehler.value)


def test_lizenztexte_lehnen_eine_namenskollision_ab(sammler, tmp_path, monkeypatch):
    """Zwei Lizenzdateien gleichen Namens dürfen sich nicht überschreiben.

    setuptools bringt ein Dutzend Dateien mit, die alle LICENSE heißen - ohne
    den Pfad im Namen wäre am Ende nur eine davon in der Sammlung, und die
    Übersicht führte den Namen zweimal auf.
    """
    nur_mit_bauumgebung()
    quelle = tmp_path / "LICENSE"
    quelle.write_text("x" * (sammler.MINDESTGROESSE + 1), encoding="utf-8")
    monkeypatch.setattr(sammler, "lizenzdateien",
                        lambda paket: [(quelle, "a/LICENSE"), (quelle, "a/LICENSE")])
    with pytest.raises(SystemExit) as fehler:
        sammler.main(tmp_path / "lizenztexte")
    assert "Zwei Lizenzdateien" in str(fehler.value)


def test_lizenztexte_lehnen_eine_zu_kleine_datei_ab(sammler, tmp_path, monkeypatch):
    """Ein Platzhalter ist kein Lizenztext - und fällt sonst niemandem auf."""
    nur_mit_bauumgebung()
    quelle = tmp_path / "LICENSE"
    quelle.write_text("MIT", encoding="utf-8")
    monkeypatch.setattr(sammler, "lizenzdateien", lambda paket: [(quelle, "LICENSE")])
    with pytest.raises(SystemExit) as fehler:
        sammler.main(tmp_path / "lizenztexte")
    assert "kein Lizenztext" in str(fehler.value)


def test_lizenztexte_lehnen_einen_vollen_zielordner_ab(sammler, tmp_path):
    """Reste eines früheren Laufs kämen sonst mit ins ZIP.

    Die Dateinamen tragen die Versionsnummer: Nach einem Versionssprung
    blieben die alten Texte liegen und stünden in keiner Übersicht.
    """
    ziel = tmp_path / "lizenztexte"
    ziel.mkdir()
    (ziel / "rest-von-vorher.txt").write_text("alt", encoding="utf-8")
    with pytest.raises(SystemExit) as fehler:
        sammler.main(ziel)
    assert "nicht leer" in str(fehler.value)


def test_ablagename_behaelt_den_pfad_im_paket(sammler):
    """Der Name muss verraten, aus welcher Kopie ein Text kommt."""
    eigen = sammler.ablagename("setuptools", "84.0.0",
                               "setuptools-84.0.0.dist-info/licenses/LICENSE")
    fremd = sammler.ablagename("setuptools", "84.0.0",
                               "setuptools/_vendor/tomli-2.4.0.dist-info/LICENSE")
    assert eigen == "setuptools-84.0.0-licenses_LICENSE.txt"
    assert "tomli" in fremd and fremd.endswith(".txt")
    assert eigen != fremd


# --------------------------------------------------------------------------
# Stückliste des Bündels
# --------------------------------------------------------------------------

@pytest.mark.parametrize("roh, erwartet", [
    ("markupsafe-3.0.4.dist-info", "markupsafe"),
    ("bottle.py", "bottle"),
    ("_cffi_backend.cp314-win_amd64.pyd", "_cffi_backend"),
    ("webview", "webview"),
    ("typing_extensions.py", "typing_extensions"),
])
def test_normieren_findet_den_paketnamen(roh, erwartet):
    assert normieren(roh) == erwartet


def stueckliste_schreiben(ordner: Path, posten: list[str]) -> Path:
    """Eine Stückliste bauen, wie PyInstaller sie schreibt."""
    ordner.mkdir(parents=True, exist_ok=True)
    zeilen = [f"  ('irgendwas', 'C:\\\\Python\\\\Lib\\\\site-packages\\\\{p}', 'DATA')"
              for p in posten]
    (ordner / "PYZ-00.toc").write_text("[\n" + ",\n".join(zeilen) + "\n]\n",
                                       encoding="utf-8")
    return ordner


def test_buendelpruefung_erkennt_ein_unbekanntes_paket(tmp_path):
    """Ein Paket im Bündel, das nicht in TEILE steht, muss auffallen."""
    pruefer = skript_laden("buendel_pruefen.py")
    ordner = stueckliste_schreiben(tmp_path / "bau", ["webview", "heimlichespaket"])
    assert pruefer.main([str(ordner), "--streng"]) == 1
    # Ohne --streng wird nur berichtet: Beim Bau von Hand bringt eine volle
    # Python-Installation Teile mit, die in der veroeffentlichten EXE fehlen.
    assert pruefer.main([str(ordner)]) == 0


def test_buendelpruefung_ist_mit_den_bekannten_teilen_zufrieden(tmp_path):
    pruefer = skript_laden("buendel_pruefen.py")
    ordner = stueckliste_schreiben(tmp_path / "bau",
                                   [o for teil in TEILE for o in teil.ordner])
    assert pruefer.main([str(ordner), "--streng"]) == 0


def test_buendelpruefung_bricht_ohne_den_pflichtteil_ab(tmp_path):
    """Eine Prüfung, die nichts findet, ist sonst grün und prüft nichts.

    Ändert PyInstaller das Format der Stückliste, greift der Suchausdruck
    nicht mehr. Die Liste der gefundenen Pakete wäre dann leer - und damit
    auch die Liste der unbekannten. Ohne diese Schranke wäre das der
    freundlichste denkbare Befund.
    """
    pruefer = skript_laden("buendel_pruefen.py")
    ordner = tmp_path / "bau"
    ordner.mkdir()
    # Eine Stückliste im neuen, unbekannten Format: lesbar, aber ohne jeden
    # Posten aus site-packages.
    (ordner / "PYZ-00.toc").write_text("{'format': 2, 'entries': []}\n",
                                       encoding="utf-8")
    with pytest.raises(SystemExit) as fehler:
        pruefer.main([str(ordner), "--streng"])
    assert pruefer.PFLICHTTEIL in str(fehler.value)


def test_buendelpruefung_lehnt_eine_unbekannte_option_ab(tmp_path):
    """Ein Tippfehler wie --strenge würde die Prüfung stillschweigend abschalten."""
    pruefer = skript_laden("buendel_pruefen.py")
    ordner = stueckliste_schreiben(tmp_path / "bau", ["webview", "heimlichespaket"])
    with pytest.raises(SystemExit) as fehler:
        pruefer.main([str(ordner), "--strenge"])
    assert "--strenge" in str(fehler.value)


def test_buendelpruefung_bricht_ohne_stueckliste_ab(tmp_path):
    """Ohne Stückliste darf die Prüfung nicht einfach grün sein.

    Verlangt wird die Meldung zu diesem Fall, nicht irgendein Abbruch: Die
    Schranke um den Pflichtteil nennt ebenfalls die Stückliste, und ein Test
    auf dieses Wort wäre grün geblieben, obwohl die Prüfung hier nicht mehr
    greift.
    """
    pruefer = skript_laden("buendel_pruefen.py")
    leer = tmp_path / "leer"
    leer.mkdir()
    with pytest.raises(SystemExit) as fehler:
        pruefer.main([str(leer), "--streng"])
    assert "Wurde die EXE gebaut?" in str(fehler.value)


def test_release_prueft_das_buendel_streng(release_jobs):
    """Die Prüfung muss dort laufen, wo die veröffentlichte EXE entsteht."""
    block = release_jobs["windows-exe"]
    assert re.search(r"python buendel_pruefen\.py .*--streng", block), (
        "Im Bau-Job fehlt der strenge Aufruf von buendel_pruefen.py."
    )


def test_build_cmd_prueft_das_buendel_und_legt_die_hinweise_dazu():
    """Auch der Bau von Hand soll berichten und die Hinweise neben die EXE legen.

    Gelesen wird ohne die REM-Zeilen: Jeder dieser Namen steht auch in einem
    Kommentar von build.cmd, und ein Kommentar ist kein Beweis. Verlangt wird
    deshalb der ganze Befehl beziehungsweise der ganze Schalter.
    """
    text = build_cmd_ohne_kommentare()
    assert "buendel_pruefen.py" in text
    assert '--version-file "versionsinfo.txt"' in text
    for name in ("DRITTANBIETER-LIZENZEN.md", "NOTICE", "LICENSE"):
        assert f'copy /y "{name}"' in text, (
            f"{name} wird beim Bau von Hand nicht neben die EXE gelegt."
        )


def test_build_cmd_bricht_bei_einem_fehler_ab():
    """Sonst steht am Ende "Fertig" über einem Scherbenhaufen.

    cmd.exe bricht von sich aus nicht ab: Nach jedem Aufruf muss eine eigene
    Prüfung stehen, sonst läuft das Skript über einen gescheiterten Bau hinweg
    und nennt zuletzt eine EXE, die von einem früheren Lauf stammt.
    """
    text = build_cmd_ohne_kommentare()
    aufrufe = re.findall(r"^(?:%PY% |copy /y )", text, re.MULTILINE)
    assert aufrufe, "In build.cmd steht gar kein Aufruf mehr."
    assert text.count("if errorlevel 1") >= len(aufrufe), (
        f"{len(aufrufe)} Aufrufe, aber nur {text.count('if errorlevel 1')} Prüfungen."
    )


def test_bau_von_hand_und_workflow_bauen_dieselbe_exe():
    """Beide Aufrufe von PyInstaller müssen dieselben Schalter tragen.

    Sonst entsteht beim Bau von Hand etwas anderes als die veröffentlichte
    EXE, und ein Fehler zeigt sich erst dort - mit dem Tag schon gesetzt.
    """
    hand = build_cmd_ohne_kommentare()
    workflow = ohne_kommentare(RELEASE_YML.read_text(encoding="utf-8"))
    for schalter in ("--onefile", "--windowed", "--clean", f'--name "{EXE}"',
                     '--icon "wetter_widget.ico"',
                     '--version-file "versionsinfo.txt"',
                     '--add-data "wetter-widget.html;."',
                     '--add-data "wetter_widget.ico;."',
                     "--exclude-module cryptography"):
        assert schalter in hand, f"build.cmd baut ohne {schalter}."
        assert schalter in workflow, f"Der Release-Workflow baut ohne {schalter}."


# --------------------------------------------------------------------------
# Release-Workflow
# --------------------------------------------------------------------------

def test_release_laesst_sich_proben(release_jobs):
    """Nur der veröffentlichende Job hängt am Tag, die Bau-Jobs nicht.

    Ohne Tag kennt die Action keinen Namen für den Release und bricht ab - ein
    Probelauf per workflow_dispatch wäre dann immer rot, und ein roter Lauf,
    der nichts bedeutet, wird irgendwann nicht mehr angesehen. Erwartet wird
    der genaue Ausdruck: "github.ref_type != 'tag'" käme sonst durch und hätte
    genau die verkehrte Wirkung.

    Und sie muss am Job hängen, nicht an einem Schritt: Mit vier Leerzeichen
    eingerückt gilt sie für den ganzen Job, mit acht nur für einen Schritt -
    dann liefe die Action bei einem Probelauf doch an.
    """
    assert re.search(r"^    if: github\.ref_type == 'tag'$",
                     release_jobs["release"], re.MULTILINE), (
        "Die Bedingung steht nicht auf der Höhe des Jobs."
    )
    for name in ("quellpaket", "windows-exe"):
        assert "if:" not in release_jobs[name], (
            f"Der Bau-Job {name} hat eine Bedingung - dann prüft der Probelauf nichts mehr."
        )


def test_release_bleibt_ein_entwurf(release_jobs):
    """draft: true - der Release-Schritt selbst wird nie geprobt."""
    assert "draft: true" in release_jobs["release"]


def test_release_haengt_an_den_richtigen_ausloesern(release):
    assert re.search(r'tags:\s*\["v\*"\]', release)
    assert "workflow_dispatch:" in release


def test_release_wartet_auf_beide_bau_jobs(release_jobs):
    assert "needs: [quellpaket, windows-exe]" in release_jobs["release"]


def test_release_schreibt_notizen(release_jobs):
    assert "generate_release_notes: true" in release_jobs["release"]


def test_release_scheitert_wenn_eine_datei_fehlt(release):
    """Die Vorgaben der Actions sind zu lasch - beide müssen umgestellt sein."""
    assert "fail_on_unmatched_files: true" in release
    assert "if-no-files-found: error" in release
    assert "if-no-files-found: warn" not in release


def test_upload_und_anhang_nennen_dieselben_dateien(release_jobs):
    """Was gebaut wird, muss auch am Release hängen - und umgekehrt.

    Ein Tippfehler in einem der beiden Pfade fällt sonst erst beim Tag auf.
    """
    hochgeladen = set(re.findall(r"dist/([A-Za-z0-9_.-]+)", release_jobs["windows-exe"]))
    angehaengt = set(re.findall(r"artefakte/windows-exe/([A-Za-z0-9_.-]+)",
                                release_jobs["release"]))
    assert hochgeladen, "Der Bau-Job lädt nichts aus dist/ hoch."
    assert hochgeladen == angehaengt, (
        f"Hochgeladen: {sorted(hochgeladen)}, angehängt: {sorted(angehaengt)}"
    )
    # Das Quellpaket kommt aus dem anderen Job und faellt sonst durch das
    # Raster dieses Vergleichs.
    assert "artefakte/quellpaket/" in release_jobs["release"], (
        "Das Quellpaket hängt nicht am Release."
    )


def test_release_ersetzt_schraegstriche_im_refnamen(release):
    """Sonst scheitert ein Probelauf von einem Zweig wie dependabot/pip/... am Pfad."""
    assert "${GITHUB_REF_NAME//\\//-}" in release


def test_release_baut_aus_den_festen_versionen(release_jobs):
    block = release_jobs["windows-exe"]
    assert "pip install -r requirements-build.txt" in block
    assert "pip install -r requirements.txt" not in block


def test_release_erzeugt_und_benutzt_die_versionsangaben(release_jobs):
    """Erzeugen allein genügt nicht - die Datei muss auch übergeben werden."""
    block = release_jobs["windows-exe"]
    assert "python versionsinfo_erzeugen.py" in block
    # Der ganze Schalter samt Datei: "--version-file" allein steht auch in der
    # Fehlermeldung des Pruefschritts, und "versionsinfo.txt" ebenfalls.
    assert '--version-file "versionsinfo.txt"' in block, (
        "Die erzeugten Angaben werden PyInstaller nicht übergeben."
    )


def test_release_sieht_sich_die_fertige_exe_an(release_jobs):
    """Der Build-Text beweist nichts - die fertige Datei muss gelesen werden."""
    block = schritt(release_jobs["windows-exe"], "Versionsangaben der EXE pruefen")
    assert f'(Get-Item "dist\\{EXE}.exe").VersionInfo' in block, (
        "Der Schritt liest die Versionsangaben der fertigen Datei nicht."
    )
    assert "$info.ProductName" in block and "$info.ProductVersion" in block
    # Der genaue Ausdruck, nicht nur die Namen: "-eq 'branch'" oder ein
    # umgedrehter Vergleich kaeme sonst durch und haette genau die verkehrte
    # Wirkung.
    assert "$env:GITHUB_REF_TYPE -eq 'tag'" in block, (
        "Die Version wird nicht gegen den Tag gehalten - "
        "eine vergessene Anhebung fiele nicht auf."
    )
    assert "-ne $env:GITHUB_REF_NAME" in block, (
        "Der Vergleich mit dem Tag steht verkehrt herum."
    )


def test_release_verlangt_eine_ausgabe_von_der_exe(release_jobs):
    """Ein stehendes Fenster beweist wenig: Es muss eine Datei entstehen.

    Eine --windowed-EXE zeigt bei einem Fehler im Start einen Dialog und läuft
    dabei weiter - ein Rauchtest nach dem Muster "lebt noch" wäre dafür grün.

    Angesehen wird allein dieser Schritt: Über den ganzen Job gesucht, findet
    sich "Test-Path" auch anderswo, und der Test bliebe grün, wenn hier nur
    noch der Aufruf ohne jede Prüfung stünde.
    """
    block = schritt(release_jobs["windows-exe"], "Baut die EXE ihre Seite wirklich auf?")
    assert "'--selbsttest','selbsttest.html'" in block, (
        "Der Rauchtest ruft die EXE nicht mit dem Schalter auf."
    )
    # -Wait: Ohne das Warten liest der Schritt die Datei, bevor sie geschrieben
    # ist - und was danach kommt, prueft dann nichts.
    assert "-Wait" in block, "Der Schritt wartet nicht auf das Ende der EXE."
    assert "$p.ExitCode -ne 0" in block, (
        "Der Rückgabewert der EXE wird nicht angesehen."
    )
    assert 'Test-Path "selbsttest.html"' in block, (
        "Dass die Datei entstanden ist, wird nicht geprüft."
    )
    assert "WIDGET_CONFIG" in block, (
        "Die geschriebene Datei wird nicht auf ihren Inhalt angesehen."
    )
    # Der Grund eines Scheiterns steht in der Nebendatei - ohne diese Zeile
    # steht im Protokoll nur eine Zahl.
    assert "selbsttest.html.fehler.txt" in block, (
        "Bei einem Fehler wird der Grund nicht ins Protokoll geholt."
    )


def test_release_setzt_dem_rauchtest_ein_zeitlimit(release_jobs):
    """Eine gepackte EXE kann auf einen Dialog warten, den niemand wegklickt.

    Scheitert der Import von webview in der EXE, zeigt der Bootloader von
    PyInstaller ein Meldungsfenster. Start-Process -Wait wartet dann, und ohne
    eigenes Limit sind das die 360 Minuten der Vorgabe von GitHub - für einen
    Lauf, der in Minuten rot sein müsste.
    """
    block = schritt(release_jobs["windows-exe"], "Baut die EXE ihre Seite wirklich auf?")
    treffer = re.search(r"timeout-minutes:\s*(\d+)", block)
    assert treffer, "Der Schritt, der die EXE startet, hat kein Zeitlimit."
    assert int(treffer.group(1)) <= 30, (
        "Das Zeitlimit ist so hoch, dass es nichts mehr abfängt."
    )


def test_selbsttest_steht_im_programm():
    """Der Schalter, auf dem der Rauchtest beruht, muss es wirklich geben."""
    text = QUELLTEXT.read_text(encoding="utf-8")
    assert '"--selbsttest"' in text
    assert "def selbsttest(" in text


def test_release_bildet_die_pruefsumme(release_jobs, release):
    """Die Summe entsteht beim Bau, nicht von Hand - und ohne Wagenrücklauf.

    Out-File schreibt unter Windows CRLF, und dann liest "sha256sum -c" den
    Dateinamen mit einem angehängten Wagenrücklauf und findet die EXE nicht.
    """
    block = schritt(release_jobs["windows-exe"], "Pruefsumme bilden")
    assert "Get-FileHash" in block
    assert "WriteAllText" in block
    assert "Out-File" not in block
    # Der Zeilenumbruch nach Unix-Art, und kein Wagenruecklauf daneben.
    assert "`n" in block, "Die Datei endet ohne Zeilenumbruch."
    assert "`r" not in block, (
        "Ein Wagenrücklauf in der Zeile - dann findet \"sha256sum -c\" die EXE nicht."
    )
    assert "SHA256SUMS.txt" in release
    # Zwei Leerzeichen zwischen Summe und Name - genau das erwartet
    # "sha256sum -c". Mit einem bricht die Prüfung beim Anwender ab.
    assert f'"$h  {EXE}.exe' in block, (
        "Zwischen Summe und Dateiname müssen zwei Leerzeichen stehen."
    )
    # .NET richtet sich nach dem Arbeitsordner des Prozesses, nicht nach dem
    # von PowerShell - ohne Join-Path landet die Datei woanders.
    assert "Join-Path $PWD" in block


def test_release_verlangt_jeden_anhang_einzeln(release_jobs):
    """if-no-files-found: error greift nur, wenn gar nichts gefunden wird.

    Fehlt eine von vier Dateien, bleibt der Schritt grün. Deshalb muss jeder
    Anhang einzeln verlangt werden - mit Test-Path und einer Größe über null.
    """
    # Nur dieser Schritt: "Test-Path" steht auch im Rauchtest, und
    # "dist\\SHA256SUMS.txt" auch in dem Schritt, der die Datei erst schreibt.
    block = schritt(release_jobs["windows-exe"], "Liegen alle Anhaenge bereit?")
    assert "Test-Path $datei" in block
    assert re.search(r"Length\b", block), "Die Größe der Anhänge wird nicht geprüft."
    erwartet = set(re.findall(r'"dist\\([A-Za-z0-9_.-]+)"', block))
    hochgeladen = set(re.findall(r"dist/([A-Za-z0-9_.-]+)",
                                 release_jobs["windows-exe"]))
    assert erwartet == hochgeladen, (
        f"Einzeln verlangt: {sorted(erwartet)}, hochgeladen: {sorted(hochgeladen)}"
    )


def test_release_prueft_den_rueckgabewert_der_skripte(release_jobs):
    """Bei mehrzeiligem run: unter PowerShell zählt nur der letzte Befehl.

    Ein gescheitertes Python-Skript mitten im Block lässt den Schritt sonst
    grün durchlaufen.

    Gezählt wird: Jeder Aufruf eines Programms braucht seine eigene Prüfung.
    Eine einzige im Block genügt nicht - dann bleibt der Schritt grün, wenn
    der Aufruf davor scheitert.
    """
    geprueft = 0
    for abschnitt in re.split(r"\n      - ", release_jobs["windows-exe"]):
        inhalt = laufblock(abschnitt)
        if inhalt is None:
            continue
        aufrufe = re.findall(r"^\s*(?:python|pip|pyinstaller)\b", inhalt, re.MULTILINE)
        if not aufrufe:
            continue
        geprueft += 1
        assert inhalt.count("$LASTEXITCODE") >= len(aufrufe), (
            f"{len(aufrufe)} Programmaufrufe, aber nur "
            f"{inhalt.count('$LASTEXITCODE')} Prüfungen:\n{inhalt[:300]}"
        )
    assert geprueft, "Kein mehrzeiliger Block mit Programmaufruf gefunden."


def test_release_haengt_die_lizenzen_an(release_jobs, release):
    """Die Hinweise und die Volltexte müssen den Anwender erreichen.

    Angesehen wird der Schritt, der sie beilegt: Der Name der Lizenzdatei
    steht auch in der Liste der Anhänge, und dort sagt er nur, dass jemand sie
    erwartet - nicht, dass sie dorthin kommt.
    """
    block = schritt(release_jobs["windows-exe"], "Lizenzhinweise und Lizenztexte beilegen")
    # LICENSE gehört dazu: Wer nur die EXE herunterlädt, bekäme sonst ein
    # MIT-Werk ohne seinen Lizenztext.
    for name in ("DRITTANBIETER-LIZENZEN.md", "LICENSE", "NOTICE"):
        assert f"Copy-Item {name} dist" in block, (
            f"{name} wird der EXE nicht beigelegt."
        )
    assert "lizenztexte_sammeln.py" in block
    assert f"{EXE}-lizenztexte.zip" in block
    assert f"{EXE}-lizenztexte.zip" in release_jobs["release"]


def test_quellpaket_enthaelt_die_genannten_dateien(release_jobs):
    """Worauf die mitgelieferten Dateien verweisen, muss auch mitkommen.

    DRITTANBIETER-LIZENZEN.md nennt buendel_pruefen.py und
    lizenztexte_sammeln.py; ein Verweis auf eine Datei, die nicht mitkommt,
    ist kein Verweis.
    """
    block = release_jobs["quellpaket"]
    for name in ("wetter_widget.py", "wetter-widget.html", "LICENSE", "NOTICE",
                 "DRITTANBIETER-LIZENZEN.md", "requirements-build.txt",
                 "versionsinfo_erzeugen.py", "buendel_pruefen.py",
                 "lizenztexte_sammeln.py", "SECURITY.md"):
        assert name in block, f"{name} fehlt im Quellpaket."


def test_release_prueft_die_waechter_in_der_bauumgebung(release_jobs):
    """Die übersprungenen Tests müssen dort zur Pflicht werden, wo sie zählen."""
    block = schritt(release_jobs["windows-exe"], "Waechter der Auslieferung")
    assert "pytest" in block, "Im Bau-Job laufen die Wächter nicht."
    assert PFLICHT in block, (
        "Ohne diese Umgebungsvariable überspringen sich die Tests auch im Bau-Job."
    )


@pytest.mark.parametrize("datei", [RELEASE_YML, CI_YML], ids=["release", "ci"])
def test_jeder_pytest_aufruf_zeigt_die_uebersprungenen(datei):
    """-rs schreibt jedes Übersprungen mit Grund ins Protokoll.

    Mit -q allein steht dort nur ein "s" in einer Punktreihe. Dass sich ein
    Wächter überspringt, der laufen sollte, fällt dann niemandem auf - und
    übersprungen ist nicht grün.
    """
    text = ohne_kommentare(datei.read_text(encoding="utf-8"))
    aufrufe = re.findall(r"pytest[^\n]*", text)
    assert aufrufe, f"In {datei.name} läuft gar kein pytest."
    for aufruf in aufrufe:
        assert "-rs" in aufruf, f"Ohne -rs bleiben die Übersprungenen stumm: {aufruf}"


def test_schreibrechte_nur_beim_veroeffentlichen(release, release_jobs):
    """Die Bau-Jobs installieren Pakete und packen eine EXE - Lesen genügt."""
    assert re.search(r"^permissions:\n  contents: read", release, re.MULTILINE)
    assert "contents: write" in release_jobs["release"]
    for name in ("quellpaket", "windows-exe"):
        assert "contents: write" not in release_jobs[name]


@pytest.mark.parametrize("datei", WORKFLOWS)
def test_fremde_actions_haengen_an_einem_commit(datei):
    """Eine fremde Action läuft mit den Rechten ihres Jobs; ein Tag ist verschiebbar.

    Die Fassung im Kommentar liest Dependabot und hebt sie mit an. Die Actions
    von GitHub selbst (actions/*) dürfen am Tag bleiben.
    """
    text = (WORKFLOW_ORDNER / datei).read_text(encoding="utf-8")
    for zeile, verweis in fremde_verweise(text):
        assert re.search(r"@[0-9a-f]{40}\b", verweis), (
            f"{datei}: {verweis} hängt nicht an einem Commit-Hash."
        )
        assert re.search(r"#\s*v?\d", zeile), (
            f"{datei}: {verweis} nennt keine Fassung im Kommentar - "
            "Dependabot hebt sie dann nicht an."
        )


def test_mindestens_eine_fremde_action_wird_geprueft():
    """Fällt die fremde Action ganz aus der Datei, soll das auffallen.

    Sonst prüft der Test darüber irgendwann eine leere Liste und ist grün,
    ohne etwas zu bedeuten.
    """
    alle = [v for datei in WORKFLOWS
            for _, v in fremde_verweise((WORKFLOW_ORDNER / datei).read_text(encoding="utf-8"))]
    assert alle, "Keine fremde Action mehr in den Workflows - dann ist der Wächter blind."


# --------------------------------------------------------------------------
# Fester Bau und Dependabot
# --------------------------------------------------------------------------

def test_bauversionen_sind_festgenagelt():
    """Jede Zeile in requirements-build.txt nennt eine genaue Fassung."""
    for zeile in FESTER_BAU.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#")[0].strip()
        if not zeile:
            continue
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[\w.+-]+", zeile), (
            f"{zeile!r} ist keine feste Fassung. Ein Bereich macht den Bau beliebig."
        )


def test_bauversionen_enthalten_den_packer():
    assert "pyinstaller" in {name.lower() for name in pakete(FESTER_BAU)}


def test_bauversionen_decken_die_laufzeitpakete_ab():
    """Was zum Laufen gebraucht wird, muss beim Bauen festgenagelt sein."""
    laufzeit = {name.lower() for name in pakete(LAUFZEIT)}
    fest = {name.lower() for name in pakete(FESTER_BAU)}
    assert laufzeit <= fest, f"Nicht festgenagelt: {sorted(laufzeit - fest)}"


def test_bauversionen_erfuellen_die_untergrenzen():
    """Die feste Fassung darf nicht unter der Untergrenze liegen.

    Sonst stünde in requirements.txt "ab 5.0" und gebaut würde mit 4.x.
    """
    grenzen = {}
    for zeile in LAUFZEIT.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#")[0].strip()
        treffer = re.fullmatch(r"([A-Za-z0-9_.-]+)>=([\w.]+)", zeile)
        if treffer:
            grenzen[treffer.group(1).lower()] = treffer.group(2)

    for zeile in FESTER_BAU.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#")[0].strip()
        treffer = re.fullmatch(r"([A-Za-z0-9_.-]+)==([\w.+-]+)", zeile)
        if not treffer:
            continue
        name, fest = treffer.group(1).lower(), treffer.group(2)
        if name not in grenzen:
            continue
        zahlen = tuple(int(t) for t in re.findall(r"\d+", fest)[:3])
        grenze = tuple(int(t) for t in re.findall(r"\d+", grenzen[name])[:3])
        assert zahlen >= grenze, (
            f"{name}=={fest} liegt unter der Untergrenze >={grenzen[name]}."
        )


def test_ci_prueft_die_waechter():
    """Ein Test, den niemand aufruft, ist kein Test."""
    text = CI_YML.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "requirements-dev.txt" in text


def test_dependabot_laesst_die_untergrenzen_in_ruhe():
    """Die Untergrenze nennt die älteste laufende Fassung, keine Empfehlung."""
    text = ohne_kommentare(DEPENDABOT.read_text(encoding="utf-8"))
    assert 'package-ecosystem: "pip"' in text
    assert "versioning-strategy: increase-if-necessary" in text


def test_dependabot_beobachtet_die_github_actions():
    """Sonst bleibt der Commit-Hash der fremden Action auf Dauer stehen."""
    text = ohne_kommentare(DEPENDABOT.read_text(encoding="utf-8"))
    assert 'package-ecosystem: "github-actions"' in text


def test_abgeleitete_dateien_sind_nicht_eingecheckt():
    """versionsinfo.txt entsteht beim Bauen und gehört nicht in den Verlauf."""
    assert "versionsinfo.txt" in (WURZEL / ".gitignore").read_text(encoding="utf-8")
    try:
        lauf = subprocess.run(["git", "ls-files", "versionsinfo.txt"],
                              cwd=WURZEL, capture_output=True, text=True,
                              check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as fehler:
        pflicht_oder_ueberspringen(f"git nicht verfügbar: {fehler}")
    # Der Rückgabewert gehört geprüft: Ein gescheitertes git - kein
    # Repository, kaputter Index - gibt eine leere Ausgabe zurück, und die
    # sieht genau wie "nicht eingecheckt" aus. Der Test wäre dann grün, ohne
    # etwas geprüft zu haben.
    if lauf.returncode != 0:
        pflicht_oder_ueberspringen(f"git ls-files endete mit {lauf.returncode}: "
                                   f"{lauf.stderr.strip()}")
    assert not lauf.stdout.strip(), "versionsinfo.txt ist eingecheckt."


# --------------------------------------------------------------------------
# Versionsangaben in der EXE
# --------------------------------------------------------------------------

def test_versionsinfo_kommt_aus_dem_quelltext(versionsinfo):
    """Eine Versionsquelle, nicht zwei: gelesen wird VERSION in wetter_widget.py."""
    assert versionsinfo.aus_quelltext("VERSION") == version_aus_quelltext()
    assert versionsinfo.aus_quelltext("PROGRAMM") == "Wetter Widget"


def test_versionsinfo_bleibt_ein_gueltiger_ausdruck(versionsinfo):
    """PyInstaller liest die Datei als Python-Ausdruck ein.

    Ein Apostroph in einem der Felder würde sie mitten im String aufbrechen.
    """
    text = versionsinfo.inhalt("Wetter Widget's Test", "1.2.3")
    ohne = "\n".join(z for z in text.splitlines() if not z.startswith("#"))
    ast.parse(ohne, mode="eval")


def test_versionsinfo_nennt_beide_namen(versionsinfo):
    """Das Programm heißt "Wetter Widget", die Datei WetterWidget.exe."""
    text = versionsinfo.inhalt("Wetter Widget", "1.2.3")
    assert "StringStruct('ProductName', 'Wetter Widget')" in text
    assert f"StringStruct('OriginalFilename', '{EXE}.exe')" in text


def test_versionsinfo_nennt_den_hinweis_auf_die_ki(versionsinfo):
    """Der Hinweis gehört zu jedem Copyright-Vermerk, auch in die EXE."""
    text = versionsinfo.inhalt("Wetter Widget", "1.2.3")
    assert "Claude AI" in text
    assert "MIT" in text


def test_versionsinfo_verweist_auf_die_lizenzdatei(versionsinfo):
    """Wer nur die EXE hat, soll in den Eigenschaften den Weg dorthin finden."""
    assert "DRITTANBIETER-LIZENZEN.md" in versionsinfo.HINWEIS


def test_exe_name_passt_zum_bau(versionsinfo):
    """Heißt die EXE anders als in den Versionsangaben, wird OriginalFilename falsch."""
    assert versionsinfo.EXE_NAME == EXE
    assert f'--name "{EXE}"' in BUILD_CMD.read_text(encoding="cp1252")
    assert f'--name "{EXE}"' in RELEASE_YML.read_text(encoding="utf-8")


def test_workflow_liest_die_versionsangaben_so_wie_sie_entstehen(versionsinfo,
                                                                 release_jobs):
    """Der Suchausdruck im Workflow muss zu der erzeugten Datei passen.

    Beide Seiten liegen weit auseinander: Änderte versionsinfo_erzeugen.py die
    Schreibweise eines Feldes, fände der Ausdruck im Workflow nichts mehr. Der
    Schritt fängt leere Soll-Werte ab und wäre damit rot - aber erst beim
    Bauen. Hier wird der Ausdruck aus dem Workflow auf den erzeugten Text
    angewandt, und zwar genau so, wie er dort steht.
    """
    block = schritt(release_jobs["windows-exe"], "Versionsangaben der EXE pruefen")
    text = versionsinfo.inhalt("Wetter Widget", "1.2.3")
    gefunden = {}
    for feld in ("ProductName", "ProductVersion"):
        treffer = re.search(rf'"(StringStruct[^"]*{feld}[^"]*)"', block)
        assert treffer, f"Der Workflow liest {feld} nicht aus versionsinfo.txt."
        muster = treffer.group(1)
        wert = re.search(muster, text)
        assert wert, (f"Der Ausdruck des Workflows findet {feld} in der erzeugten "
                      f"Datei nicht: {muster}")
        gefunden[feld] = wert.group(1)
    assert gefunden == {"ProductName": "Wetter Widget", "ProductVersion": "1.2.3"}


@pytest.mark.parametrize("version, erwartet", [
    ("1", (1, 0, 0, 0)),
    ("1.9", (1, 9, 0, 0)),
    ("1.9.0", (1, 9, 0, 0)),
    ("1.9.0.7", (1, 9, 0, 7)),
    # Die obere Grenze: Windows legt jede der vier Zahlen in 16 Bit ab.
    ("65535.0.0", (65535, 0, 0, 0)),
])
def test_vierstellig_rechnet_richtig(versionsinfo, version, erwartet):
    assert versionsinfo.vierstellig(version) == erwartet


@pytest.mark.parametrize("version", ["1.9.0rc1", "", "1.9.0-beta", "a.b.c",
                                     "1.2.3.4.5", "70000.0.0",
                                     # Eins über der Grenze von 16 Bit.
                                     "65536.0.0"])
def test_vierstellig_lehnt_unbrauchbares_mit_klartext_ab(versionsinfo, version):
    """Abbrechen statt raten: Windows kann das nicht abbilden."""
    with pytest.raises(SystemExit):
        versionsinfo.vierstellig(version)


def test_versionsinfo_liest_keinen_offenen_ausdruck(versionsinfo, tmp_path, monkeypatch):
    """Bei VERSION = "1.9.0" + SUFFIX darf nicht nur der erste Teil gelesen werden.

    Sonst nennen die Dateieigenschaften eine andere Fassung als das Programm.
    """
    quelle = tmp_path / "wetter_widget.py"
    quelle.write_text('VERSION = "1.9.0" + SUFFIX\n', encoding="utf-8")
    monkeypatch.setattr(versionsinfo, "QUELLE", quelle)
    with pytest.raises(SystemExit):
        versionsinfo.aus_quelltext("VERSION")


def test_versionsinfo_bricht_ohne_konstante_ab(versionsinfo, tmp_path, monkeypatch):
    quelle = tmp_path / "wetter_widget.py"
    quelle.write_text("# keine Fassung hier\n", encoding="utf-8")
    monkeypatch.setattr(versionsinfo, "QUELLE", quelle)
    with pytest.raises(SystemExit) as fehler:
        versionsinfo.aus_quelltext("VERSION")
    assert "0-mal" in str(fehler.value)


def test_versionsinfo_bricht_bei_mehrdeutiger_konstante_ab(versionsinfo, tmp_path,
                                                           monkeypatch):
    """Steht die Konstante zweimal da, ist Abbruch richtiger als die erste zu nehmen."""
    quelle = tmp_path / "wetter_widget.py"
    quelle.write_text('VERSION = "1.9.0"\nVERSION = "2.0.0"\n', encoding="utf-8")
    monkeypatch.setattr(versionsinfo, "QUELLE", quelle)
    with pytest.raises(SystemExit) as fehler:
        versionsinfo.aus_quelltext("VERSION")
    assert "2-mal" in str(fehler.value)


def test_versionsinfo_lehnt_zeichen_ausserhalb_von_ascii_ab(versionsinfo, tmp_path,
                                                            monkeypatch):
    """In den Dateieigenschaften sollen keine verstümmelten Umlaute stehen."""
    quelle = tmp_path / "wetter_widget.py"
    quelle.write_text('PROGRAMM = "Wetter Widget für Windows"\n', encoding="utf-8")
    monkeypatch.setattr(versionsinfo, "QUELLE", quelle)
    with pytest.raises(SystemExit) as fehler:
        versionsinfo.aus_quelltext("PROGRAMM")
    assert "ASCII" in str(fehler.value)


def test_versionsinfo_laesst_keine_alte_datei_stehen(versionsinfo, tmp_path, monkeypatch):
    """Bricht das Erzeugen ab, nimmt ein späterer Bau sonst die Fassung von vorher."""
    quelle = tmp_path / "wetter_widget.py"
    quelle.write_text("# keine Fassung hier\n", encoding="utf-8")
    ziel = tmp_path / "versionsinfo.txt"
    ziel.write_text("alte Angaben\n", encoding="utf-8")
    monkeypatch.setattr(versionsinfo, "QUELLE", quelle)
    monkeypatch.setattr(versionsinfo, "ZIEL", ziel)
    with pytest.raises(SystemExit):
        versionsinfo.main()
    assert not ziel.exists(), "Die alte Datei liegt noch da."


# --------------------------------------------------------------------------
# Kleinigkeiten, die dazugehören
# --------------------------------------------------------------------------

def test_pyproject_nennt_dieselbe_fassung():
    """Zwei Stellen von Hand sind eine zu viel - beim Bau von 1.8.3 ging es fast schief."""
    treffer = re.findall(r'^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"),
                         re.MULTILINE)
    assert treffer == [version_aus_quelltext()], (
        f"pyproject.toml nennt {treffer}, wetter_widget.py {version_aus_quelltext()}."
    )


def test_security_md_nennt_die_aktuelle_reihe():
    """1.8.x, wenn 1.9.0 läuft, wäre die Reihe von vorgestern."""
    haupt, neben, *_ = version_aus_quelltext().split(".")
    text = SECURITY.read_text(encoding="utf-8")
    assert f"{haupt}.{neben}.x" in text, (
        f"SECURITY.md nennt nicht die Reihe {haupt}.{neben}.x."
    )


def test_security_md_nennt_den_meldeweg():
    text = SECURITY.read_text(encoding="utf-8")
    assert "security/advisories/new" in text
    assert "DerAlexmann/WetterWidget" in text


def test_changelog_nennt_die_aktuelle_fassung():
    """Die oberste Überschrift muss die Fassung sein, die im Programm steht."""
    for zeile in CHANGELOG.read_text(encoding="utf-8").splitlines():
        treffer = re.fullmatch(r"## ([\d.]+)\s*", zeile)
        if treffer:
            assert treffer.group(1) == version_aus_quelltext(), (
                f"Der CHANGELOG beginnt mit {treffer.group(1)}, "
                f"das Programm meldet {version_aus_quelltext()}."
            )
            return
    pytest.fail("Im CHANGELOG steht keine Fassung.")
