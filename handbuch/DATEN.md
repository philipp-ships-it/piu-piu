# Daten, Sicherung und Wiederherstellung

## Speicherort und Dateien

Die Priorität des Datenordners lautet: `--data-dir`, dann `PIU_DATA_DIR`, dann
der Standardordner des Betriebssystems. Pfade in `--data-dir` sind relativ zum
aktuellen Arbeitsverzeichnis oder können absolut angegeben werden.

| System | Standard |
|---|---|
| Windows | `%LOCALAPPDATA%\PiuPiu` |
| Linux/macOS | `$XDG_STATE_HOME/piu-piu`, sonst `~/.local/state/piu-piu` |

| Datei | Zweck |
|---|---|
| `profile.json` | Aktuelles Profil mit Settings, Scores und Rundenstand |
| `profile.backup.json` | Vorheriger erfolgreich gespeicherter Profilstand |
| `profile.recovery-DATUM-ZEIT.json` | Unveränderte Kopie einer beschädigten Datei |
| `profile.lock` | Betriebssystem-Sperre gegen parallele Schreibzugriffe |
| `piu.log`, `.1`, `.2` | Rotierendes Fehlerprotokoll, je maximal 256 KiB |

Profildaten gehören nicht ins Git-Repository. Im Download und in einer EXE sind
keine persönlichen Daten enthalten. Eine verschobene EXE behält dasselbe Profil,
solange der Datenordner unverändert bleibt.

## Wann wird gesichert?

- Settings unmittelbar nach jeder Menüänderung.
- Eine neue oder fortgesetzte Runde vor dem ersten Spieltakt.
- Während des Spiels alle 90 Takte, entsprechend fünf Sekunden Spielzeit.
- Bei Pause, Q, Strg+C und bestmöglich bei einem unerwarteten Fehler.
- Bei Game Over: Punkte verbuchen und Rundenstand in einer Transaktion entfernen.

Ein harter Prozessabbruch kann die seit der letzten Sicherung gespielte Zeit
verlieren. Im normalen Betrieb sind das höchstens ungefähr fünf Sekunden
Spielzeit. Bei Schreibfehlern gilt diese Grenze nicht: Das Spiel pausiert und
bietet Wiederholen oder bewusstes Beenden ohne Speichern an.

## Atomare Speicherung

Die neue Datei wird zunächst in einer temporären Datei im **gleichen Ordner**
geschrieben und mit `fsync` synchronisiert. Anschließend ersetzt `os.replace`
die Profildatei atomar. Vorher wird der letzte gültige Stand als Backup gesichert.
Ein fehlgeschlagener Schreib- oder Replace-Schritt meldet keinen Erfolg und
behält das vorige Profil. Temporäre Dateien werden regulär aufgeräumt.

Die Anwendung hält während der Nutzung eine Betriebssystem-Dateisperre.
Eine zweite Instanz desselben Profils wird verständlich abgelehnt.
Die Sperre wird beim Prozessende freigegeben; die übrig gebliebene
`profile.lock`-Datei allein bedeutet nicht, dass noch eine Sperre besteht.

## Format

UTF-8-JSON mit expliziten Versionsnummern. Oberste Felder von Profilversion 1:

| Feld | Inhalt |
|---|---|
| `version` | Formatversion, aktuell 1 |
| `player_name` | Bereinigter Spielername |
| `settings` | Schwierigkeit, Tempo, Dichte, Magazin und fünf boolesche Cheats |
| `scores` | Höchstens zehn Einträge: name, score, kills, runs, date |
| `checkpoint` | Rundensnapshot oder null |
| `last_run_id` | Zuletzt verbuchte Runde; verhindert doppelte Verbuchung bei Wiederholung |

Ein Snapshot enthält `version`, `run_id`, `geometry`, `settings`, `rng` und
`state`. Der Zustand umfasst Position und Geschwindigkeit des Helden, Sprünge,
Munition und Timer, Distanz und Punkte, Hindernisse, Projektile, Hintergrund,
Partikel und Cheat-Markierung. Der Zustand des Python-Zufallsgenerators wird
als kontrollierte JSON-Zahlenliste gespeichert. **Kein Pickle, kein ausführbarer
Code** wird geladen. Soundereignisse werden nicht erneut abgespielt.

Numerische Typen, endliche Werte, Grenzen, Objektgrößen und Pflichtfelder werden
vor der Übernahme geprüft. Profildateien sind auf 2 MB begrenzt. Ein boolescher
Wert wird nicht als Integer akzeptiert. Eine unbekannte Profilversion wird
nicht überschrieben; dafür ist eine passende Spielversion erforderlich.

## Highscores

Namen werden von Steuerzeichen bereinigt, auf 14 Zeichen gekürzt und unabhängig
von Groß-/Kleinschreibung sowie überflüssigen Leerzeichen verglichen. Pro Name
bleibt die höchste Punktzahl. Jeder beendete Lauf ohne Cheats erhöht den
Laufzähler, auch wenn er den Rekord nicht verbessert. Die Liste enthält maximal
zehn Spieler. Nicht platzierte Namen werden nicht als separates Spielerverzeichnis
geführt. Cheat-Läufe verändern die Liste überhaupt nicht.

## Migration alter Daten

Wenn noch kein neues Profil oder Backup existiert, prüft das Spiel
`piu_highscores.json`, danach `piuu_highscores.json` neben `piuu.py`
(bei einer EXE neben der EXE). Die erste lesbare Liste wird übernommen.
Duplikate werden zusammengeführt, ungültige Einträge ausgelassen und gemeldet.
Die Originaldatei bleibt unverändert. Ein bereits vorhandenes Profil wird
nicht erneut mit alten Scores vermischt.

## Rettung eines beschädigten Profils

1. Das Spiel beenden und den gesamten Datenordner kopieren.
2. Beim nächsten Start versucht das Spiel nach beschädigtem JSON das Backup.
   Eine Recovery-Kopie hält den defekten Inhalt für eine spätere Rettung fest.
3. Ist nur ein Teil des gültigen JSON beschädigt, bleiben brauchbare Highscores
   erhalten. Settings können auf Standardwerte zurückfallen; ein ungültiger
   Rundenstand wird verworfen. Die Oberfläche erklärt, was passiert ist.
4. Zum manuellen Wiederherstellen bei geschlossenem Spiel das gewünschte Backup
   kopieren und als `profile.json` ablegen. Das Backup vorher separat behalten.
5. Zum unbelasteten Test lieber `--data-dir` mit einem neuen Ordner verwenden,
   statt bestehende Nutzerdaten zu löschen.

Lokale JSON-Dateien sind keine manipulationssichere Online-Bestenliste. Die
Cheat-Sperre verhindert reguläre Cheat-Verbuchungen; sie ist kein Anti-Cheat-
System gegen manuelle Änderungen auf dem eigenen Rechner.

## Browserdaten

Die Webseite verwendet den Local-Storage-Schlüssel `piu-piu.arcade.v2` mit
Version 2, Bestleistung, ausgewähltem Preset und optionaler Runde. Automatisch
gesichert wird alle fünf Sekunden Spielzeit sowie bei Pause/Verlassen der Seite.
Ohne Speicherfreigabe bleibt das Spiel nutzbar, zeigt aber einen Hinweis.
Das Löschen von Websitedaten löscht diesen Fortschritt. Kein Server erhält Daten.
