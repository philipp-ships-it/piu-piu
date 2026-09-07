# Fehlerbehebung

## Immer zuerst

1. Den entpackten Projektordner in einem Terminal öffnen. Nicht nur `piuu.py`
   aus dem ZIP starten; der Ordner `piu` wird ebenfalls benötigt.
2. Mit einer vorhandenen, freigegebenen Python-Installation prüfen:

   ```console
   python --version
   python piuu.py --diagnose
   python piuu.py --silent --ascii --demo 200
   ```

3. Funktioniert die Demo, aber nicht das interaktive Spiel, liegt die Ursache
   meist an Terminal, Eingabe, Zeichenkodierung oder Fenstergröße.
4. Funktioniert das Spiel, aber nicht das Speichern, mit einem **neuen**
   Datenordner testen. Bestehende Daten vorher sichern.

Die Diagnose zeigt Python-Version, Programmpfad, Betriebssystem, Datenordner,
Terminalstatus und Schreibzugriff. Das Protokoll liegt als `piu.log` im
Datenordner; siehe [Daten](DATEN.md). Es gibt keine versteckten Fehlermeldungen
bei gescheitertem Speichern.

## Symptome und Lösungen

| Symptom | Prüfung | Lösung |
|---|---|---|
| „Python nicht gefunden“ | `py -3 --version` bzw. vorhandene Python-Verknüpfung | Start mit dem vollständigen Python-Pfad oder `PIU_PYTHON` setzen |
| Firmenblocker / Zugriff verweigert beim Start | Ist die konkrete Installation freigegeben? | Freigegebenes System-Python nutzen oder IT kontaktieren; keine Sperren umgehen |
| `No module named piu` | Liegt `piu/` neben `piuu.py`? | ZIP vollständig neu entpacken und aus diesem Ordner starten |
| Fenster schließt sofort | Aus einem bereits offenen Terminal starten | Fehlermeldung lesen; `PIUU.bat` hält bei Fehlern an |
| „Kein interaktives Terminal“ | Eingabe aus Datei, IDE-Ausgabefenster oder Pipeline? | Windows Terminal, PowerShell, cmd oder eine echte Unix-Konsole verwenden |
| Seltsame Unicode-Zeichen | `--ascii` testen | ASCII-Modus oder ein UTF-8-Terminal mit Monospace-Schrift benutzen |
| Kein Sound | Windows-Soundgerät vorhanden? | Sound ist optional; `--silent` funktioniert auf allen Systemen |
| Terminal zu klein | Mindestens 47×15 Zeichen für automatische Größe | Fenster vergrößern; die Runde setzt sich ohne Zeitverlust fort |
| Ausgabe scrollt oder wirkt verschoben | Raster größer als sichtbares Terminal? | `--size` entfernen; automatische Größe bevorzugen |
| „Speichern fehlgeschlagen“ | Freier Speicher, Berechtigungen, Ordnerschutz | Ursache beheben und Enter zum erneuten Versuch; Q beendet ausdrücklich ohne neue Sicherung |
| Profil bereits geöffnet | Zweite laufende Spielinstanz? | Andere Instanz schließen oder einen eigenen `--data-dir` verwenden |
| Alte Lock-Datei nach Absturz | Läuft wirklich noch eine Instanz? | Die Dateisperre endet mit dem Prozess; Lock-Datei muss nicht gelöscht werden |
| JSON-/Profilhinweis | `profile.recovery-*.json` und Backup vorhanden? | Hinweise lesen; brauchbare Daten werden erhalten, Backup wird versucht |
| Unbekannte Profilversion | Profil aus einer anderen Spielversion? | Passende Version verwenden; nicht blind auf Version 1 umschreiben |
| Rekord zählt nicht | War einer der fünf Cheats beim Rundenstart aktiv? | Neue Runde ohne Cheats starten; leicht/eigen sind erlaubt |
| Geänderte Settings gelten nicht in fortgesetzter Runde | Resume nutzt ursprüngliche Rundensettings | Eine neue Runde starten, wenn die neuen Werte gelten sollen |
| Browser-Runde speichert nicht | Privater Modus oder Local Storage gesperrt? | Speicherfreigabe erteilen oder in normalem Browserprofil spielen; Hinweis beachten |
| Webseite nach Doppelklick ohne Spiel | ES-Module unter `file://` werden blockiert | Lokale HTTP-Vorschau verwenden, siehe unten |
| Download-Link liefert 404 | Wurde das ZIP nach Änderungen gebaut? | `python scripts/build_download.py` ausführen |

## Vorhandenes Python ohne PATH verwenden

In PowerShell:

```powershell
& "C:\Pfad\zu\Python\python.exe" piuu.py --diagnose
```

Für `PIUU.bat` im aktuellen PowerShell-Fenster:

```powershell
$env:PIU_PYTHON = "C:\Pfad\zu\Python\python.exe"
.\PIUU.bat
```

Unter Windows findet die Startdatei außerdem automatisch `py`, `python` und
die übliche Python-3.12-Installation im lokalen Benutzerordner. Es wird nichts
heruntergeladen oder automatisch installiert.

Wenn eine Sicherheitslösung auch die reguläre Installation blockiert, ist das
kein Spielfehler. Nicht umbenennen, aus einem anderen Ordner erneut ausführen
oder Schutzfunktionen deaktivieren. Nutze die Browser-Runde oder kläre die
Freigabe mit deiner IT.

## Speicherproblem eingrenzen

```console
python piuu.py --data-dir ./testprofil --diagnose
python piuu.py --data-dir ./testprofil --silent --ascii
```

Wenn das neue Testprofil funktioniert, den bisherigen Datenordner sichern und
Rechte bzw. Inhalt prüfen. Recovery-Dateien niemals löschen, solange sie noch
für eine Rettung gebraucht werden. Ein Profil darf nicht gleichzeitig von
zwei Spielprozessen verändert werden.

## Webseite lokal prüfen

```console
node scripts/preview.mjs
```

Dann `http://127.0.0.1:4173` öffnen. Falls Port 4173 belegt ist, den vorhandenen
Vorschauprozess schließen oder die Umgebungsvariable `PORT` setzen.
Alternativ ohne Node:

```console
python -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Die Vorschau startet keine Veröffentlichung und lauscht nur auf dem eigenen Rechner.

## Fehlercodes

| Exit-Code | Bedeutung |
|---|---|
| 0 | Normal beendet, erfolgreiche Demo/Diagnose oder Hilfe |
| 1 | Unerwarteter interner Fehler; Details im Protokoll |
| 2 | Ungültige Kommandozeilenargumente |
| 3 | Terminal-, Profil-, Speicher- oder Zugriffsproblem |

## Einen Fehler melden

Nenne Spielversion, Betriebssystem, Python-Version, Startbefehl, Fenstergröße,
die letzten Aktionen und den angezeigten Fehler. Eine Demo mit `--seed` ist
reproduzierbar. Füge bei Bedarf den relevanten Abschnitt aus `piu.log` hinzu.
Prüfe vor dem Teilen, ob Pfade oder Spielernamen private Informationen enthalten.
Für Speicherprobleme eine **Kopie** des Profils verwenden, nicht das Original.
