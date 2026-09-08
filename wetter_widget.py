"""Wetter Widget - eigenständiges Desktop-Fenster.

Zeigt die Oberfläche aus wetter-widget.html in einem nativen Fenster
(Microsoft WebView2) an, es wird kein externer Browser benötigt.

Dieses Programm ist nur der Rahmen: Aussehen, Sprachtabelle und Wetterabruf
stehen vollständig in der HTML-Datei. Hier liegt, was ein Fenster können muss
und eine Webseite nicht kann - Position und Einstellungen über das
Programmende hinaus behalten.

Licensed under MIT License
Copyright 2026 Alexander Unverhau
Created with assistance of Claude AI
"""

import ctypes
import json
import os
import sys
import threading


def _dpi_bewusstsein_setzen():
    """Muss vor dem Import von webview laufen.

    Ohne DPI-Awareness rendert WebView2 auf skalierten Bildschirmen (z. B.
    150 %) mit einem größeren Layout-Viewport, als das Fenster anzeigen kann -
    das Widget wird dann rechts abgeschnitten.
    """
    try:  # Windows 10 1703+: Per-Monitor v2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:  # ältere Windows-Versionen
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if sys.platform == "win32":
    _dpi_bewusstsein_setzen()

import webview  # noqa: E402  - erst nach dem DPI-Setup importieren

PROGRAMM = "Wetter Widget"
VERSION = "1.7.0"
CONFIG_NAME = "wetter-widget.json"
UEBER_TITEL = "Über " + PROGRAMM

# Darstellungen und die Anzeigefläche, die jede von ihnen braucht - in
# Punkten, also unabhängig von der Bildschirmskalierung. Gemeint ist die
# Fläche *innerhalb* des Fensters; der Rahmen kommt aussen hinzu.
DARSTELLUNGEN = ("karte", "leiste")
GROESSE = {"karte": (400, 428), "leiste": (780, 76)}
LAGE_SCHLUESSEL = {"karte": "fenster", "leiste": "leiste"}
DEFAULT_DARSTELLUNG = "karte"

MINDESTGROESSE = (320, 56)

# Transparenzstufen, die das Kontextmenü anbietet (Prozent). 100 % fehlt mit
# Absicht: das Fenster wäre unsichtbar und nur über die Taskleiste zu fassen.
TRANSPARENZSTUFEN = tuple(range(0, 100, 10))

# Abstände der selbsttätigen Aktualisierung in Minuten, 0 heißt "nur von Hand".
# Muss zu INTERVALLE in wetter-widget.html passen.
INTERVALLE = (0, 15, 30, 60, 180, 360)

# Autostart: der Zweig des angemeldeten Benutzers kommt ohne
# Administratorrechte aus, anders als derselbe Schlüssel unter HKEY_LOCAL_MACHINE.
AUTOSTART_SCHLUESSEL = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = PROGRAMM

# Farbe hinter der Seite, bis das HTML gezeichnet ist - sonst blitzt beim
# Start kurz Weiß auf. Die Werte sind BG aus den Paletten in der HTML-Datei.
FENSTERFARBE = {"light": "#eef1f5", "dark": "#12161d"}
DEFAULT_THEME = "dark"


# --------------------------------------------------------------------------
# Einstellungen
#
# Alles, was das Programm behalten soll, steht in einer JSON-Datei neben der
# .exe: der zuletzt gesuchte Ort, Sprache, Farbschema und die Fensterlage.
# --------------------------------------------------------------------------

def ist_eingefroren() -> bool:
    """Läuft das Programm als gebündelte EXE (PyInstaller & Co.)?"""
    return getattr(sys, "frozen", False)


def programm_ordner() -> str:
    """Ordner, in dem das Programm für den Anwender sichtbar liegt.

    Als PyInstaller-EXE mit --onefile entpackt sich das Programm in einen
    temporären Ordner (sys._MEIPASS), den PyInstaller beim Beenden wieder
    löscht - __file__ zeigt dorthin. Alles, was den Programmlauf überdauern
    soll, gehört deshalb neben die EXE und nicht neben __file__.
    """
    if ist_eingefroren():
        return os.path.dirname(os.path.abspath(sys.executable))
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:                       # z. B. interaktive Eingabe
        return os.path.expanduser("~")


def config_path() -> str:
    """Ablageort der Einstellungen - neben dem Programm."""
    return os.path.join(programm_ordner(), CONFIG_NAME)


def load_config() -> dict:
    # utf-8-sig: die Datei darf von Hand bearbeitet werden, und Editoren wie
    # der Windows-Editor schreiben gern eine Byte-Reihenfolge-Marke voran.
    # Ohne sie zu überlesen wären alle Einstellungen stillschweigend verloren.
    try:
        with open(config_path(), encoding="utf-8-sig") as datei:
            daten = json.load(datei)
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


# Aufrufe aus der Seite laufen jeweils in einem eigenen Thread. Ohne Sperre
# könnten zwei davon gleichzeitig die ganze Datei lesen, jeder seinen Teil
# ändern und beide zurückschreiben - die Änderung des einen wäre verloren.
_EINSTELLUNGEN_SPERRE = threading.RLock()


def config_aendern(aendern) -> bool:
    """Einstellungen unter der Sperre lesen, ändern und zurückschreiben."""
    with _EINSTELLUNGEN_SPERRE:
        daten = load_config()
        aendern(daten)
        return save_config(daten)


def save_config(daten: dict) -> bool:
    try:
        with open(config_path(), "w", encoding="utf-8") as datei:
            json.dump(daten, datei, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def autostart_befehl() -> str:
    """Befehlszeile, die Windows beim Anmelden ausführen soll."""
    if ist_eingefroren():
        return '"%s"' % os.path.abspath(sys.executable)
    # Als Skript: pythonw.exe, sonst erschiene bei jeder Anmeldung ein
    # Konsolenfenster hinter dem Widget.
    ordner = os.path.dirname(os.path.abspath(sys.executable))
    pythonw = os.path.join(ordner, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return '"%s" "%s"' % (pythonw, os.path.abspath(__file__))


def autostart_lesen() -> bool:
    """Steht das Widget im Autostart - und zeigt der Eintrag hierher?

    Die Registrierung ist die maßgebliche Auskunft, nicht die eigene
    Einstellungsdatei: der Eintrag lässt sich auch außerhalb des Programms
    entfernen, etwa im Task-Manager.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_SCHLUESSEL) as schluessel:
            wert, _art = winreg.QueryValueEx(schluessel, AUTOSTART_NAME)
        return bool(wert)
    except OSError:
        return False


def autostart_setzen(an: bool) -> bool:
    """Eintrag anlegen oder entfernen; zurück kommt der tatsächliche Zustand.

    Schlägt das Schreiben fehl - etwa weil Richtlinien es untersagen -, bleibt
    es beim alten Zustand, und das Häkchen im Menü erscheint schlicht nicht.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUTOSTART_SCHLUESSEL) as schluessel:
            if an:
                winreg.SetValueEx(schluessel, AUTOSTART_NAME, 0,
                                  winreg.REG_SZ, autostart_befehl())
            else:
                try:
                    winreg.DeleteValue(schluessel, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        pass
    return autostart_lesen()


def autostart_nachfuehren() -> None:
    """Verschobenes Programm im Autostart nachtragen.

    Wer die .exe an einen anderen Platz legt, hätte sonst einen Eintrag, der
    ins Leere zeigt. Geändert wird nur, was schon eingetragen war.
    """
    if not autostart_lesen():
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_SCHLUESSEL) as schluessel:
            vorhanden, _art = winreg.QueryValueEx(schluessel, AUTOSTART_NAME)
        if vorhanden != autostart_befehl():
            autostart_setzen(True)
    except OSError:
        pass


def resource_path(name: str) -> str:
    """Pfad zu einer mitgelieferten Datei - im Skript wie in der .exe."""
    basis = getattr(sys, "_MEIPASS", None) or programm_ordner()
    return os.path.join(basis, name)


# --------------------------------------------------------------------------
# Oberfläche laden
# --------------------------------------------------------------------------

def seite_bauen(einstellungen: dict) -> str:
    """HTML einlesen und die gespeicherten Werte hineinreichen.

    Die Seite liest sie aus window.WIDGET_CONFIG. Fehlt das Objekt - beim
    direkten Öffnen der HTML-Datei im Browser -, nimmt sie ihre eigenen
    Vorgaben; die Datei bleibt also für sich allein lauffähig.
    """
    with open(resource_path("wetter-widget.html"), encoding="utf-8") as datei:
        html = datei.read()

    startwerte = {name: einstellungen[name]
                  for name in ("ort", "sprache", "theme", "einheiten",
                               "darstellung")
                  if isinstance(einstellungen.get(name), str)}
    for name in ("vordergrund", "rahmenlos", "verriegelt"):
        startwerte[name] = bool(einstellungen.get(name))
    startwerte["transparenz"] = (einstellungen.get("transparenz")
                                 if einstellungen.get("transparenz") in TRANSPARENZSTUFEN
                                 else 0)
    if einstellungen.get("intervall") in INTERVALLE:
        startwerte["intervall"] = einstellungen["intervall"]
    startwerte["autostart"] = autostart_lesen()
    startwerte["version"] = VERSION
    einbau = "<script>window.WIDGET_CONFIG = %s;</script>\n</head>" % json.dumps(
        startwerte, ensure_ascii=False)
    return html.replace("</head>", einbau, 1)


# --------------------------------------------------------------------------
# Fensterlage
# --------------------------------------------------------------------------

# Fensterstile, die den Windows-Rahmen ausmachen, und die Bits für ein
# durchscheinendes Fenster. Beides wird über Windows-Funktionen gesetzt und
# nicht über pywebview: dessen Wege greifen unmittelbar auf das WinForms-
# Fenster zu, während die Aufrufe aus der Seite in einem eigenen Thread
# ankommen - das blockiert das Programm.
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CAPTION, WS_THICKFRAME = 0x00C00000, 0x00040000
WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_SYSMENU = 0x00020000, 0x00010000, 0x00080000
RAHMENBITS = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER = 0x0001, 0x0002, 0x0004
SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x0010, 0x0020
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2


_USER32 = None


def _user32():
    """user32 mit den Signaturen, die dieses Programm braucht.

    Bewusst eine eigene Instanz und nicht ctypes.windll.user32: dieses Objekt
    teilen sich alle Bibliotheken im Programm. Wer dort argtypes setzt, ändert
    sie auch für pywebview - dessen Fenster-Verschieben ruft dieselbe Funktion
    und bekäme unsere Signatur untergeschoben.
    """
    global _USER32
    if _USER32 is not None:
        return _USER32

    from ctypes import wintypes
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    u.GetWindowLongW.restype = ctypes.c_long
    u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    u.SetWindowLongW.restype = ctypes.c_long
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    u.SetWindowPos.restype = wintypes.BOOL
    u.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF,
                                             ctypes.c_ubyte, ctypes.c_uint]
    u.SetLayeredWindowAttributes.restype = wintypes.BOOL
    u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.FindWindowW.restype = wintypes.HWND
    # Fensterkennungen sind Zeiger: ohne restype schneidet ctypes sie auf
    # 32 Bit zurecht, was auf 64-Bit-Windows danebengehen kann.
    u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u.MonitorFromPoint.restype = wintypes.HANDLE
    u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetClientRect.restype = wintypes.BOOL
    u.AdjustWindowRectEx.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD,
                                     wintypes.BOOL, wintypes.DWORD]
    u.AdjustWindowRectEx.restype = wintypes.BOOL
    try:            # erst ab Windows 10 (1607) vorhanden
        u.GetDpiForWindow.argtypes = [wintypes.HWND]
        u.GetDpiForWindow.restype = wintypes.UINT
        u.AdjustWindowRectExForDpi.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD,
                                               wintypes.BOOL, wintypes.DWORD, wintypes.UINT]
        u.AdjustWindowRectExForDpi.restype = wintypes.BOOL
    except AttributeError:
        pass
    _USER32 = u
    return u


def bildschirm_skalierung() -> float:
    """Skalierungsfaktor des Hauptbildschirms (1.5 = 150 %)."""
    try:
        from ctypes import wintypes
        hmon = _user32().MonitorFromPoint(
            wintypes.POINT(0, 0), 1)          # MONITOR_DEFAULTTOPRIMARY
        faktor = ctypes.c_int()
        if ctypes.windll.shcore.GetScaleFactorForMonitor(hmon, ctypes.byref(faktor)) == 0:
            if 50 <= faktor.value <= 500:
                return faktor.value / 100
    except Exception:
        pass
    return 1.0


def fenster_dpi(griff) -> int:
    """Punktdichte des Fensters; 96 entspricht 100 % Skalierung."""
    try:
        dpi = int(_user32().GetDpiForWindow(griff))
        return dpi if dpi > 0 else 96
    except (AttributeError, OSError, ValueError):
        return 96


def sichtbare_lage(lage: dict, vorgabe=None):
    """Gespeicherte Fensterlage prüfen und nötigenfalls zurechtrücken.

    Wird ein Bildschirm abgemeldet oder die Auflösung kleiner, läge das
    Fenster sonst außerhalb und wäre nicht mehr zu greifen. Die Werte werden
    deshalb in die vorhandene Arbeitsfläche geschoben.

    Fehlt in der gespeicherten Lage ein Maß, tritt `vorgabe` an seine Stelle -
    die Größe der jeweiligen Darstellung, die nur der Aufrufer kennt.

    webview.screens meldet physische Pixel, Fensterkoordinaten sind dagegen
    skalierungsunabhängige Punkte - daher die Division durch die Skalierung.
    """
    vorgabe = vorgabe or GROESSE[DEFAULT_DARSTELLUNG]
    try:
        x, y = int(lage["x"]), int(lage["y"])
        breite = max(MINDESTGROESSE[0], int(lage.get("breite", vorgabe[0])))
        hoehe = max(MINDESTGROESSE[1], int(lage.get("hoehe", vorgabe[1])))
    except (KeyError, TypeError, ValueError):
        return None

    skala = bildschirm_skalierung()
    flaechen = [(schirm.x / skala, schirm.y / skala,
                 schirm.width / skala, schirm.height / skala)
                for schirm in webview.screens]
    if not flaechen:
        return None

    # Bildschirm, auf dem die gespeicherte Position liegt - sonst der erste.
    links, oben, sb, sh = next(
        (f for f in flaechen if f[0] <= x < f[0] + f[2] and f[1] <= y < f[1] + f[3]),
        flaechen[0])

    breite, hoehe = min(breite, int(sb)), min(hoehe, int(sh))
    x = min(max(x, int(links)), int(links + sb - breite))
    y = min(max(y, int(oben)), int(oben + sh - hoehe))
    return {"x": x, "y": y, "breite": breite, "hoehe": hoehe}


class Fensterablage:
    """Schreibt Position und Anzeigefläche des Fensters in die Einstellungen.

    Die Ereignisse moved und resized feuern während des Ziehens fortlaufend.
    Statt bei jedem Pixel zu speichern, wird der Schreibvorgang gesammelt und
    erst nach kurzer Ruhe ausgeführt.

    Ist das Fenster verriegelt, wird nicht gespeichert, sondern die vorige
    Lage wiederhergestellt. Auf der Widgetfläche greift die Verriegelung schon
    beim Ziehen; über die Titelleiste des Windows-Rahmens lässt sich ein
    Fenster aber nicht am Verschieben hindern - dort schnappt es nach dem
    Loslassen an seinen Platz zurück.

    Gespeichert wird die **Anzeigefläche** in Punkten, nicht das Außenmaß des
    Fensters. Nur so bedeutet der Wert in jeder Lage dasselbe: mit Rahmen wie
    ohne, bei jeder Bildschirmskalierung. Jede Darstellung führt dabei ihre
    eigene Lage - die Leiste steht am Bildschirmrand, die Karte anderswo.
    """

    VERZOEGERUNG = 0.4                      # Sekunden Ruhe vor dem Schreiben

    def __init__(self, fenster, api):
        self.fenster = fenster
        self.api = api
        self.timer = None
        self.sperre = threading.Lock()
        self.verriegelt = False
        self.modus = DEFAULT_DARSTELLUNG
        self.lage = None                    # zuletzt gültige Lage

    def merken(self, *_args):
        with self.sperre:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.VERZOEGERUNG, self.schreiben)
            self.timer.daemon = True
            self.timer.start()

    def _lage_lesen(self):
        flaeche = self.api.client_lesen()
        if flaeche is None:
            return None                     # Fenster ist bereits geschlossen
        try:
            return {"x": int(self.fenster.x), "y": int(self.fenster.y),
                    "breite": flaeche[0], "hoehe": flaeche[1]}
        except Exception:
            return None

    def schreiben(self, *_args):
        with self.sperre:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
        lage = self._lage_lesen()
        if lage is None:
            return

        if self.verriegelt and self.lage is not None:
            if (lage["x"], lage["y"]) != (self.lage["x"], self.lage["y"]):
                try:
                    self.fenster.move(self.lage["x"], self.lage["y"])
                except Exception:
                    pass
                return

        self.lage = lage
        schluessel = LAGE_SCHLUESSEL[self.modus]
        config_aendern(lambda daten: daten.__setitem__(schluessel, lage))


class Api:
    """Was die Oberfläche aufrufen darf: window.pywebview.api....

    Alles, was hier steht, kann die Seite nicht selbst: Fenster verschieben,
    Rahmen abnehmen, durchscheinend machen, beenden. Namen mit Unterstrich
    bleiben außen vor - pywebview reicht jeden öffentlichen Namen dieses
    Objekts an die Seite weiter und verfängt sich am Fensterobjekt sonst
    endlos.
    """

    # Welche Werte gültig sind, prüft die Oberfläche - sie führt die
    # Tabellen für Farbschemata, Sprachen und Einheiten.
    TEXTFELDER = ("ort", "sprache", "theme", "einheiten", "darstellung")
    SCHALTER = ("vordergrund", "rahmenlos", "verriegelt")

    def __init__(self, ablage=None):
        self._fenster = None                # wird nach create_window gesetzt
        self._ablage = ablage
        self._ueber = None                  # Fenster von "Über", falls offen
        self._hwnd = 0
        self._griff = None                  # Abstand Mauszeiger -> Fensterecke

    # -- Einstellungen ---------------------------------------------------

    def einstellungen_speichern(self, daten):
        """Übernimmt die Werte, die die Oberfläche verwaltet."""
        if not isinstance(daten, dict):
            return False

        def uebernehmen(gespeichert):
            for name in self.TEXTFELDER:
                wert = daten.get(name)
                if isinstance(wert, str) and len(wert) <= 120:
                    gespeichert[name] = wert
            for name in self.SCHALTER:
                if name in daten:
                    gespeichert[name] = bool(daten[name])
            if daten.get("transparenz") in TRANSPARENZSTUFEN:
                gespeichert["transparenz"] = int(daten["transparenz"])
            if daten.get("intervall") in INTERVALLE:
                gespeichert["intervall"] = int(daten["intervall"])
            if self._ablage is not None:
                self._ablage.verriegelt = bool(gespeichert.get("verriegelt"))

        return config_aendern(uebernehmen)

    # -- Fenster ---------------------------------------------------------

    def _fensterhandle(self):
        """Fensterkennung (HWND), einmal ermittelt und dann gemerkt."""
        if self._hwnd:
            return self._hwnd
        try:
            self._hwnd = int(self._fenster.native.Handle.ToInt64())
        except Exception:
            self._hwnd = int(_user32().FindWindowW(None, PROGRAMM) or 0)
        return self._hwnd

    def vordergrund_setzen(self, an):
        """Fenster über oder unter allen anderen halten."""
        hwnd = self._fensterhandle()
        if not hwnd:
            return False
        try:
            from ctypes import wintypes
            u = _user32()
            return bool(u.SetWindowPos(
                wintypes.HWND(hwnd),
                wintypes.HWND(HWND_TOPMOST if an else HWND_NOTOPMOST),
                0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE))
        except Exception:
            return False

    @staticmethod
    def _aussenmass(rechteck, stil, exstil, griff):
        """Rechnet ein Innenmaß in das dafür nötige Außenmaß um.

        Der Rahmen kommt also zum Inhalt hinzu, statt von ihm abgezogen zu
        werden. AdjustWindowRectExForDpi berücksichtigt die Skalierung des
        Bildschirms; auf älterem Windows tut es die Fassung ohne DPI.
        """
        u = _user32()
        stil, exstil = stil & 0xFFFFFFFF, exstil & 0xFFFFFFFF
        try:
            dpi = u.GetDpiForWindow(griff)
            if dpi and u.AdjustWindowRectExForDpi(ctypes.byref(rechteck), stil,
                                                  False, exstil, dpi):
                return True
        except (AttributeError, OSError, ValueError):
            pass
        try:
            return bool(u.AdjustWindowRectEx(ctypes.byref(rechteck), stil, False, exstil))
        except (AttributeError, OSError, ValueError):
            return False

    def rahmen_setzen(self, rahmenlos):
        """Windows-Rahmen samt Titelleiste an- oder abschalten.

        Ohne Rahmen sieht das Widget nach Widget aus - Schließen und
        Verschieben laufen dann über das Kontextmenü und die Widgetfläche.

        Das Fenster wird dabei so nachgemessen, dass die Anzeigefläche gleich
        groß bleibt. Bliebe stattdessen das Außenmaß stehen, wüchse die Fläche
        beim Abnehmen des Rahmens um die Titelleiste - der Inhalt säße oben
        und unten bliebe eine Lücke -, und beim Anlegen fehlte genau dieser
        Streifen, sodass ein Rollbalken erschiene.
        """
        hwnd = self._fensterhandle()
        if not hwnd:
            return False

        try:
            from ctypes import wintypes
            u = _user32()
            griff = wintypes.HWND(hwnd)

            innen = wintypes.RECT()
            hat_innenmass = bool(u.GetClientRect(griff, ctypes.byref(innen)))

            stil = u.GetWindowLongW(griff, GWL_STYLE)
            stil = (stil & ~RAHMENBITS) if rahmenlos else (stil | RAHMENBITS)
            u.SetWindowLongW(griff, GWL_STYLE, stil)
            exstil = u.GetWindowLongW(griff, GWL_EXSTYLE)

            aussen = wintypes.RECT(0, 0, innen.right, innen.bottom)
            if hat_innenmass and self._aussenmass(aussen, stil, exstil, griff):
                u.SetWindowPos(griff, None, 0, 0,
                               aussen.right - aussen.left, aussen.bottom - aussen.top,
                               SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
            else:                       # Maß nicht bestimmbar: nur neu zeichnen
                u.SetWindowPos(griff, None, 0, 0, 0, 0,
                               SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
            return True
        except Exception:
            return False

    def transparenz_setzen(self, prozent):
        """Fenster durchscheinend machen: 0 % deckend, 90 % fast unsichtbar."""
        if prozent not in TRANSPARENZSTUFEN:
            return False
        hwnd = self._fensterhandle()
        if not hwnd:
            return False
        try:
            from ctypes import wintypes
            u = _user32()
            griff = wintypes.HWND(hwnd)
            stil = u.GetWindowLongW(griff, GWL_EXSTYLE)
            u.SetWindowLongW(griff, GWL_EXSTYLE, stil | WS_EX_LAYERED)
            alpha = int(round(255 * (100 - prozent) / 100.0))
            return bool(u.SetLayeredWindowAttributes(griff, 0, alpha, LWA_ALPHA))
        except Exception:
            return False

    # -- Verschieben -----------------------------------------------------

    def ziehen_beginnen(self, maus_x, maus_y):
        """Abstand zwischen Mauszeiger und Fensterecke merken.

        Ohne ihn würde das Fenster beim ersten Ziehen unter den Mauszeiger
        springen. Der Abstand wird vom Programm bestimmt und nicht von der
        Seite, weil nur hier die tatsächliche Fensterecke bekannt ist -
        einschließlich der Rahmenbreite.
        """
        try:
            self._griff = (int(self._fenster.x) - int(maus_x),
                           int(self._fenster.y) - int(maus_y))
            return True
        except Exception:
            self._griff = None
            return False

    def ziehen(self, maus_x, maus_y):
        """Fenster dem Mauszeiger nachführen."""
        if self._griff is None:
            return False
        try:
            self._fenster.move(int(maus_x) + self._griff[0],
                               int(maus_y) + self._griff[1])
            return True
        except Exception:
            return False

    def autostart_setzen(self, an):
        """Widget in den Autostart von Windows eintragen oder daraus lösen."""
        return autostart_setzen(bool(an))

    # -- Anzeigefläche und Darstellung -----------------------------------

    def client_lesen(self):
        """Anzeigefläche in Punkten, oder None bei geschlossenem Fenster."""
        hwnd = self._fensterhandle()
        if not hwnd:
            return None
        try:
            from ctypes import wintypes
            griff = wintypes.HWND(hwnd)
            innen = wintypes.RECT()
            if not _user32().GetClientRect(griff, ctypes.byref(innen)):
                return None
            dpi = fenster_dpi(griff)
            return (int(round(innen.right * 96 / dpi)),
                    int(round(innen.bottom * 96 / dpi)))
        except Exception:
            return None

    def client_setzen(self, breite, hoehe):
        """Fenster so bemessen, dass die Anzeigefläche genau so groß wird.

        Der Rahmen wird dazugerechnet, nicht abgezogen - deshalb stimmt das
        Maß mit und ohne Rahmen und bei jeder Bildschirmskalierung.
        """
        hwnd = self._fensterhandle()
        if not hwnd:
            return False
        try:
            from ctypes import wintypes
            u = _user32()
            griff = wintypes.HWND(hwnd)
            dpi = fenster_dpi(griff)
            aussen = wintypes.RECT(0, 0,
                                   int(round(breite * dpi / 96)),
                                   int(round(hoehe * dpi / 96)))
            stil = u.GetWindowLongW(griff, GWL_STYLE)
            exstil = u.GetWindowLongW(griff, GWL_EXSTYLE)
            if not self._aussenmass(aussen, stil, exstil, griff):
                return False
            return bool(u.SetWindowPos(
                griff, None, 0, 0,
                aussen.right - aussen.left, aussen.bottom - aussen.top,
                SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE))
        except Exception:
            return False

    def darstellung_setzen(self, name):
        """Zwischen Karte und Leiste umschalten.

        Jede Darstellung führt ihre eigene Lage: die Leiste steht meist am
        oberen oder unteren Bildschirmrand, die Karte irgendwo daneben. Beim
        Wechsel wird die bisherige Lage gesichert und die des Ziels geholt.
        """
        if name not in DARSTELLUNGEN or self._ablage is None:
            return False
        if name == self._ablage.modus:
            return True

        # Sichern und Nachschlagen gehören zusammen: käme dazwischen ein
        # anderer Aufruf aus der Seite, läse dieser Zwischenstände.
        with _EINSTELLUNGEN_SPERRE:
            self._ablage.schreiben()        # Lage der bisherigen Darstellung
            self._ablage.modus = name
            gespeichert = load_config().get(LAGE_SCHLUESSEL[name]) or {}
        lage = sichtbare_lage(gespeichert, GROESSE[name]) or {}

        breite = lage.get("breite", GROESSE[name][0])
        hoehe = lage.get("hoehe", GROESSE[name][1])
        self.client_setzen(breite, hoehe)

        if "x" in lage and "y" in lage:
            ziel = (lage["x"], lage["y"])
        else:
            # Für diese Darstellung ist noch keine Lage bekannt: das Fenster
            # bleibt, wo es ist - nur muss es dort auch hinpassen. Die Leiste
            # ist deutlich breiter als die Karte und ragte sonst über den
            # Bildschirmrand hinaus, wenn die Karte rechts aussen stand.
            jetzt = self._ablage._lage_lesen() or {}
            gerueckt = sichtbare_lage({"x": jetzt.get("x", 0), "y": jetzt.get("y", 0),
                                       "breite": breite, "hoehe": hoehe},
                                      (breite, hoehe))
            ziel = (gerueckt["x"], gerueckt["y"]) if gerueckt else None

        if ziel is not None:
            try:
                self._fenster.move(ziel[0], ziel[1])
            except Exception:
                pass
        self._ablage.lage = self._ablage._lage_lesen()
        return True

    # -- Über dieses Programm --------------------------------------------

    def ueber_fenster(self, html):
        """Zeigt "Über" in einem eigenen Fenster.

        In der Leiste wäre für den Text kein Platz, und auch als Karte liest
        es sich in einem eigenen Fenster besser. Ist es bereits offen, wird
        es nur nach vorn geholt.
        """
        if not isinstance(html, str) or len(html) > 200000:
            return False
        try:
            if self._ueber is not None and self._ueber in webview.windows:
                self._ueber.show()
                return True
        except Exception:
            pass
        try:
            self._ueber = webview.create_window(
                UEBER_TITEL, html=html, width=470, height=560,
                min_size=(360, 320), background_color=FENSTERFARBE[
                    load_config().get("theme") if load_config().get("theme")
                    in FENSTERFARBE else DEFAULT_THEME])
            return True
        except Exception:
            return False

    def beenden(self):
        """Widget schließen - ohne Titelleiste der einzige Weg im Fenster."""
        try:
            self._fenster.destroy()
            return True
        except Exception:
            return False


# --------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------

def main():
    einstellungen = load_config()
    thema = einstellungen.get("theme")
    if thema not in FENSTERFARBE:
        thema = DEFAULT_THEME

    transparenz = einstellungen.get("transparenz")
    if transparenz not in TRANSPARENZSTUFEN:
        transparenz = 0

    darstellung = einstellungen.get("darstellung")
    if darstellung not in DARSTELLUNGEN:
        darstellung = DEFAULT_DARSTELLUNG

    rahmenlos = bool(einstellungen.get("rahmenlos"))
    lage = sichtbare_lage(einstellungen.get(LAGE_SCHLUESSEL[darstellung]) or {},
                          GROESSE[darstellung]) or {}
    breite, hoehe = GROESSE[darstellung]
    breite, hoehe = lage.get("breite", breite), lage.get("hoehe", hoehe)
    autostart_nachfuehren()

    api = Api()
    # Das Fenster entsteht verborgen und mit Rahmen. Erst wenn die Seite
    # steht, bekommt es seine Gestalt: Rahmen ab, Anzeigefläche genau
    # bemessen, an seinen Platz gerückt - und dann wird es gezeigt. So blitzt
    # weder eine Titelleiste noch eine falsche Größe auf, und pywebviews
    # eigene Maße spielen keine Rolle mehr.
    fenster = webview.create_window(
        PROGRAMM,
        html=seite_bauen(einstellungen),
        js_api=api,
        width=breite + 40, height=hoehe + 60,
        x=lage.get("x"), y=lage.get("y"),
        min_size=MINDESTGROESSE,
        background_color=FENSTERFARBE[thema],
        on_top=bool(einstellungen.get("vordergrund")),
        frameless=False,
        hidden=True,
        # Das Ziehen macht das Widget selbst, damit die Verriegelung greift.
        easy_drag=False,
    )
    api._fenster = fenster

    ablage = Fensterablage(fenster, api)
    ablage.verriegelt = bool(einstellungen.get("verriegelt"))
    ablage.modus = darstellung
    api._ablage = ablage
    fenster.events.moved += ablage.merken
    fenster.events.resized += ablage.merken
    fenster.events.closing += ablage.schreiben

    fertig = threading.Event()

    def beim_laden():
        """Gestalt des Fensters festlegen, sobald die Seite steht.

        loaded meldet sich auch nach einem erneuten Laden der Seite, deshalb
        die Sperre - das hier geschieht nur einmal.
        """
        if fertig.is_set():
            return
        fertig.set()
        if rahmenlos:
            api.rahmen_setzen(True)
        api.client_setzen(breite, hoehe)
        if "x" in lage and "y" in lage:
            fenster.move(lage["x"], lage["y"])
        if transparenz:
            api.transparenz_setzen(transparenz)
        fenster.show()
        ablage.lage = ablage._lage_lesen()

    fenster.events.loaded += beim_laden

    webview.start()


if __name__ == "__main__":
    main()
