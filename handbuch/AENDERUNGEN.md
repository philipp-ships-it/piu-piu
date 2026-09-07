# Änderungen

## 2.0.0

- Einzeldatei in unabhängige Module für Regeln, Simulation, Darstellung,
  Terminal, Profil und Anwendung aufgeteilt; bestehender Startbefehl bleibt.
- Settings, Highscores und die aktive Runde werden dauerhaft gespeichert.
- Fortsetzen inklusive Zufallsfolge; Bestätigung vor dem Ersetzen einer Runde.
- Atomare Profiltransaktionen, Backup, Recovery-Kopien, Formatprüfung und
  Betriebssystem-Sperre gegen parallele Profilzugriffe.
- Alte Score-Dateien werden einmalig übernommen, nicht gelöscht.
- Vier Presets, Einzelwerte und alle fünf Cheats samt Highscore-Sperre erhalten.
- Größerer ASCII-Startscreen, animierte Szene und kompakte Terminalvarianten.
- Feste 18-Hz-Simulation, eigene Zufallsfolge pro Runde und Sound außerhalb
  des Spieltakts. Töne verändern keine Hindernisse mehr.
- Schüsse treffen auch bei Kreuzung zwischen den Frame-Endpositionen.
- Tote Runden simulieren nicht weiter; Nachladegrenzen berücksichtigen
  Gleitkomma-Rundung; Q funktioniert auch in der Pause.
- Speicherfehler werden angezeigt, statt fälschlich erfolgreiche Rekorde zu melden.
- Deterministische Unit-/Integrationstests ersetzen globale Zustände,
  ungesäte Stichproben und Quelltext-Regex-Prüfungen.
- Alte Webseite vollständig durch eine eigenständige Arcade-Seite mit
  animierter ASCII-Art, Browser-Spiel, lokaler Speicherung und Download ersetzt.
- Deutsche Anleitung, Architektur-, Daten-, Entwicklungs- und Fehlerdokumentation.
- Alte Root-Tests und automatisches Pushskript entfernt; Buildwerkzeuge
  nach `scripts/` verlegt; keine automatische Paketinstallation mehr.
- Neuere Menü-/Logging-Commits aus GitHub inhaltlich abgeglichen: deren
  Platzhalter für Mods und Spielmodi werden durch die funktionierenden Settings
  ersetzt; Fehlerprotokolle sind jetzt zentral und begrenzt. Die bisherige
  Autorennennung bleibt im README erhalten. Alte, an die Einzeldatei gekoppelte
  Menüschnelltests werden durch die neue Anwendungssuite ersetzt.
