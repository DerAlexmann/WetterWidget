# Sicherheitsrichtlinie

## Unterstützte Versionen

| Version | Unterstützt |
|---|---|
| 1.9.x   | ✅ |
| < 1.9   | ❌ |

Es wird immer nur die jeweils aktuelle Version gepflegt.

## Eine Sicherheitslücke melden

Bitte melden Sie Sicherheitslücken **nicht** als öffentliches Issue.

Nutzen Sie stattdessen die private Meldefunktion von GitHub:

**[Report a vulnerability](https://github.com/DerAlexmann/WetterWidget/security/advisories/new)**
(im Repository unter *Security → Advisories*)

Der Bericht ist dabei nur für Sie und die Projektverantwortlichen sichtbar. Die
Behebung kann im selben Advisory besprochen werden, ohne dass die Lücke vorher
öffentlich wird. Einen weiteren Meldeweg gibt es bewusst nicht – so bleibt alles
an einer Stelle und nachvollziehbar.

Hilfreich für die Meldung:

- Beschreibung der Lücke und der möglichen Auswirkung
- Schritte zum Nachstellen
- Windows-Version und, bei der EXE, deren Fassung aus den Dateieigenschaften
- Falls vorhanden: ein Vorschlag zur Behebung

**Was Sie erwarten können:** eine Eingangsbestätigung innerhalb von 7 Tagen und
eine erste Einschätzung innerhalb von 30 Tagen. Nach der Behebung wird die Lücke
öffentlich gemacht; auf Wunsch mit Nennung der meldenden Person.

Dies ist ein Freizeitprojekt ohne Bug-Bounty-Programm.

## Womit das Programm umgeht – Einschätzung des Risikos

Das Widget zeigt eine mitgelieferte HTML-Seite in einem WebView2-Fenster und
fragt zwei Wetterdienste ab. Es nimmt keine Verbindungen an, lädt keinen Code
nach und sendet keine Telemetrie. Die Stellen, an denen Daten von außen
verarbeitet werden, sind diese:

| Bereich | Hinweis |
|---|---|
| **Netzzugriff** | Genau zwei Ziele, beide über HTTPS: `geocoding-api.open-meteo.com` für die Ortssuche und `api.brightsky.dev` für Messwerte und Vorhersage. Abgefragt wird aus der Seite heraus, mit `fetch`; das Programm selbst öffnet keine Verbindung. |
| **Antworten der Dienste** | Ortsname und Wetterlage kommen von außen. Sie werden maskiert in die Seite gesetzt (`maskieren()`), Meldungen über `textContent`. Bis 1.8.2 war das nicht so – ein Dienst hätte Markup einschleusen können, das der Browser aufbaut. Seit 1.8.3 geschlossen. |
| **Der eingegebene Ort** | Wird gespeichert und beim nächsten Start in die Seite gereicht. Dabei wird jedes `</` entschärft, damit der Wert das eingebaute Skript-Element nicht beenden kann. |
| **Schnittstelle zur Seite** | Die Seite kann über `window.pywebview.api` Einstellungen schreiben, den Autostart setzen und Fenster öffnen. Das ist gewollt – die Oberfläche *ist* die Seite. Sie wird aus der EXE geladen, nicht aus dem Netz; eine Seite von außen bekommt diese Schnittstelle nie. |
| **Einstellungsdatei** | `wetter-widget.json` liegt neben dem Programm und enthält Ort, Sprache, Farbschema, Einheiten, Fensterlage. Keine Zugangsdaten, keine Verlaufsdaten. Sie darf von Hand bearbeitet werden; ungültige Werte werden verworfen, nicht übernommen. |
| **Autostart** | Ein Eintrag unter `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`, nur auf Wunsch über das Kontextmenü und dort auch wieder abschaltbar. Keine Administratorrechte, kein Dienst, kein geplanter Task, kein Eintrag unter `HKEY_LOCAL_MACHINE`. |
| **WebView2** | Die Darstellung übernimmt die Evergreen-Komponente von Microsoft. Deren Sicherheitsaktualisierungen kommen über Windows Update und sind von diesem Programm unabhängig. |
| **Gebündelte EXE** | Enthält die Python-Laufzeit und die Bibliotheken in der beim Bauen aktuellen Fassung. Sicherheitsaktualisierungen dieser Teile erreichen die EXE erst mit einer neuen Veröffentlichung; wer das eng verfolgen möchte, führt `wetter_widget.py` mit einem selbst gepflegten Python aus. Was in der EXE steckt, steht in [DRITTANBIETER-LIZENZEN.md](DRITTANBIETER-LIZENZEN.md). |
| **Nicht signiert** | Die EXE trägt keine Code-Signatur. Vergleichen Sie vor dem ersten Start die SHA-256-Prüfsumme aus `SHA256SUMS.txt` am Release. |

## Abhängigkeiten aktuell halten

```bash
pip install --upgrade -r requirements.txt
```

Im Repository hält [Dependabot](.github/dependabot.yml) die Abhängigkeiten und
die Versionen der GitHub-Actions monatlich nach.
