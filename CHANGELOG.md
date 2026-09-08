# Änderungsverlauf

Die Nummern folgen dem Muster `Haupt.Neben.Korrektur`.

## 1.7.0

- Neue Darstellung **Leiste**: dieselbe Anzeige in einer Zeile, für den oberen
  oder unteren Bildschirmrand. Umschaltbar über *Darstellung* im Kontextmenü.
- Jede Darstellung führt ihre **eigene Fensterlage** - die Leiste steht am
  Rand, die Karte anderswo, und beide finden beim Umschalten dorthin zurück.
- **Über** öffnet sich in einem eigenen Fenster, statt die Anzeige zu
  überdecken; in der Leiste wäre dafür ohnehin kein Platz.
- Gespeichert wird nun die Anzeigefläche statt des Außenmaßes. Der Wert
  bedeutet damit in jeder Lage dasselbe - mit Rahmen wie ohne, bei jeder
  Bildschirmskalierung.
- Behoben: Zwei Aufrufe aus dem Menü konnten sich gegenseitig überschreiben,
  weil beide die ganze Einstellungsdatei lasen und zurückschrieben. Änderungen
  laufen jetzt unter einer Sperre.

## 1.6.0

- Menüpunkt **Über** mit Fassungsnummer, Datenquellen, Lizenz und Copyright.
- Lizenzvermerk im Kopf beider Quelldateien.

## 1.5.0

- Menüpunkt **Einheiten**: metrisch oder imperial (°F, mph, Zoll, inHg,
  Meilen), unabhängig von der Sprache einstellbar.
- Zahlen werden in der Schreibweise der eingestellten Sprache dargestellt -
  auf Deutsch also mit Komma statt Punkt.
- Abrufen und Anzeigen sind getrennt: ein Wechsel der Einheiten zeichnet die
  vorhandenen Messwerte neu, ohne den Wetterdienst erneut zu befragen.

## 1.4.1

- Der Menüeintrag *Nicht automatisch* heißt jetzt *Durch User*.

## 1.4.0

- Menüpunkt **Mit Windows starten**: trägt das Widget im Autostart des
  angemeldeten Benutzers ein und wieder aus, ohne Administratorrechte. Ein
  verschobenes Programm trägt sich beim nächsten Start selbst nach.
- **Aktualisieren** wurde zum Untermenü: *Jetzt* sowie Abstände von 15
  Minuten bis 6 Stunden für die selbsttätige Aktualisierung, voreingestellt
  30 Minuten.
- Einmal nachgeschlagene Orte werden behalten; die Ortssuche wird bei der
  selbsttätigen Aktualisierung nicht erneut befragt.

## 1.3.1

- Behoben: Beim Umschalten des Rahmens blieb das Außenmaß stehen, sodass sich
  die Anzeigefläche um die Rahmenbreite änderte - einmal mit Lücke, einmal mit
  Rollbalken. Jetzt bleibt die Anzeigefläche gleich groß.
- Behoben: Ein rahmenlos erzeugtes Fenster wurde bei jedem Speichern und
  Neustart ein Stück kleiner. Das Fenster entsteht nun immer mit Rahmen und
  verliert ihn erst, solange es noch verborgen ist.
- Beim Öffnen ist der Inhalt des Ortsfelds nicht mehr blau hinterlegt.

## 1.3.0

- Alle Einstellungen sitzen im **Kontextmenü**; die Kopfzeile mit den
  Schaltern entfällt.
- **Rahmenlos**: Windows-Rahmen samt Titelleiste abnehmbar.
- **Verriegelt**: sichert das Fenster gegen versehentliches Verschieben.
- **Transparenz** in Zehnerschritten von 0 bis 90 Prozent.
- Das Widget lässt sich auf seiner Fläche mit der Maus verschieben.

## 1.2.0

- Menüpunkt **Immer vorn** hält das Fenster über allen anderen.

## 1.1.0

- Position, Größe, Ort, Sprache und Farbschema überdauern das Programmende.
- Farbpaletten hell und dunkel aus der Bild-Toolbox und dem
  QR-Code-Generator; Sprachumschaltung Deutsch/Englisch.
- Behoben: fehlte der Windwert in den Daten des Wetterdienstes, stand dort
  `NaN km/h`.

## 1.0.0

- Erste Fassung: das HTML-Widget als eigenständiges Windows-Programm im
  nativen Fenster über WebView2.
