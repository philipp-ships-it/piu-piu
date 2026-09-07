# QA-Bericht zur Version 2.0.0

Stand: 7. September 2026. Die Prüfungen verwenden das regulär vorhandene
Python 3.12.10 und Node 24.14.0. Blockierte Codex-Runtimes wurden nicht verwendet.

## Automatisierte Prüfungen

- **139 Python-Tests erfolgreich**, einschließlich Integration und ZIP-Paketstart.
- **11 Browser-Unit-Tests erfolgreich** mit dem eingebauten Node-Testläufer.
- Syntaxprüfung aller Python-Quellen und der Browser-JavaScript-Dateien erfolgreich.
- Das gebaute ZIP wurde in einen temporären Ordner entpackt und dort als
  unabhängiges Spiel ohne Repository gestartet.
- Wiederholte ZIP-Builds ergeben identische Bytes; Metadaten und Zeilenenden
  sind für Windows/Linux vereinheitlicht.
- Lokale Markdown-Dateilinks wurden gegen vorhandene Dokumente geprüft.

Die `trace`-Zeilenmessung erfasst Imports und Laufzeit. Gemessen wurden unter
anderem 100 % für Engine, Settings, Geometrie und Taktung, 96 % für Snapshots,
93 % für Speicherung und 94 % für Rendering. Das ist **keine Branch-Abdeckung**
und kein Ersatz für die geprüften fachlichen Grenzfälle. Native Tastatur- und
Soundpfade sind nur teilweise durch Adaptertests abgedeckt.

## Browserprüfung

Im echten Browser geprüft:

| Fall | Ergebnis |
|---|---|
| 360 / 768 / 1440 Pixel Breite | Kein horizontaler Seitenüberlauf |
| Start, Schuss, Sprung, Pause | Funktioniert, keine JavaScript-Laufzeitfehler |
| Reload nach Pause | Gespeicherte Runde mit Punkten und Munition fortsetzbar |
| Neue Runde / Abbrechen | Bestätigung erscheint; Abbrechen setzt vorhandene Runde fort |
| Touch-Schuss auf kleinem Bildschirm | Munition verändert sich korrekt |
| Beschädigtes Browserprofil | Verständlicher Hinweis; neue Runde möglich |
| Gesperrter Local Storage | Sichtbarer Warnhinweis statt Absturz |
| Reduzierte Bewegung | Automatisch respektiert; Animationsschalter zeigt passenden Zustand |
| FAQ | Per nativen aufklappbaren Elementen bedienbar |
| Download | HTTP 200, echtes ZIP mit vollständigem Python-Spiel |

## Grenzen der lokalen Prüfung

Die lokalen Python-Tests liefen unter Windows/Python 3.12. Echte Beep-Ausgabe und
eine längere manuelle Terminal-Spielsitzung wurden nicht als bestanden behauptet.
Linux und Python 3.10 werden zusätzlich über den GitHub-Workflow geprüft.
Die Browser-Version hat eine eigene Simulation; bitgleiche Spielstände zwischen
Browser und Python werden nicht versprochen.

Zum erneuten Ausführen: [Entwicklung und QA](ENTWICKLUNG.md).
