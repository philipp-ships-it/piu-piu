# Entwicklung und Qualitätssicherung

## Umgebung

Python ab 3.10 genügt zum Spielen und für die Python-Tests. Es gibt keine
Laufzeitabhängigkeiten. Node ab 20 ist optional für Webtests und Vorschau.
Alle Tests verwenden Standardbibliotheken; weder pytest noch npm-Pakete müssen
installiert werden. Die Start-/Buildskripte laden keine Pakete automatisch nach.
GitHub Actions führt die Suite bei Push und Pull Request unter Windows/Python
3.12 sowie Linux/Python 3.10 und 3.12 aus. Ein weiterer Job prüft Browserlogik
und Aktualität des Download-ZIPs. Die offiziellen Actions sind auf feste Commits gepinnt.

## Prüfungen ausführen

Im Repository-Hauptordner:

```console
python -m unittest discover -s tests -v
node --test tests/web/*.test.js
python scripts/qa.py
```

`scripts/qa.py` führt Python-Tests und Syntaxprüfung aus. Mit `--coverage`
erstellt es zusätzlich einen lokalen Zeilenabdeckungsbericht für `piu/` mit der
Standardbibliothek `trace`. Eine Zeilenquote ersetzt keine Verhaltensprüfungen.
Ausgaben gehören in `.qa/` und werden nicht versioniert.

## Teststrategie

| Ebene | Geprüftes Verhalten |
|---|---|
| Regeln | Presets, Wertebereiche, Cheat-Markierung, Reset, unabhängige Settings |
| Simulation | Sprünge, Landung, Munition, exakte Timergrenzen, Kollisionsfälle, Punkte |
| Determinismus | Gleicher Seed/Aktionen, unabhängiger RNG, Snapshot/Resume gegen ununterbrochenen Lauf |
| Speicher | Atomare Writes, Fehler bei fsync/Replace, Backup, Recovery, Migration, Locks |
| Anwendung | Start/Settings/Resume, Pause, Q/Strg+C, Fehlerdialoge, profilfreie Demo |
| Darstellung | Rastergrenzen, sichtbare Auswahl, ASCII-Modus, unveränderter Zustand/RNG |
| Browser | Regeln, Checkpoints, ungültige Daten und zustandsneutrales Zeichnen |

Tests nutzen isolierte Game-Instanzen, explizite Seeds und temporäre Verzeichnisse
mit Aufräumen. Die Anwendungsintegration verwendet echte Fachlogik mit
Fake-Terminal, Tastenskript und Fake-Uhr. Echte Wartezeiten, zufällige globale
Testreihenfolgen und Quelltext-Regex als Funktionsnachweis werden vermieden.

Die feste Hindernismessung verwendet Seed 0, Raster 80×20, 400 Takte und
ausgeschaltete Spielerkollision: leicht erzeugt 8, irre 31 Hindernisse.
Das ist ein Regressionstest für diese Konfiguration, keine Zufallsgarantie
für jeden beliebigen Lauf.

## Neue Features sauber ergänzen

1. Fachliches Verhalten als Test beschreiben, einschließlich eines Grenzfalls.
2. Regeln in `settings` bzw. `engine` ergänzen, I/O nicht in die Engine ziehen.
3. Bei neuen Zustandsfeldern Snapshot-Schema und Validierung aktualisieren.
   Bei inkompatiblen Änderungen die Formatversion erhöhen und Migration planen.
4. Rendering getrennt implementieren und auf dem kleinsten Raster prüfen.
5. Änderungen an Bedienung, Daten oder Optionen im deutschen Handbuch nachziehen.
6. Vollständige Tests, Demo und Webprüfung ausführen; anschließend ZIP neu bauen.

Ruff-Konfiguration liegt optional in `pyproject.toml`. Falls Ruff bereits
installiert ist, kann `ruff check piu tests scripts` als zusätzliche statische
Prüfung verwendet werden. Das Spiel benötigt Ruff nicht.

## Webseite prüfen

```console
node scripts/preview.mjs
```

Vorschau: `http://127.0.0.1:4173`. Ohne Node geht auch:

```console
python -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Manuelle Browser-QA: Breiten 360, 768 und 1440 Pixel; kein horizontaler Überlauf;
Start, Sprung, Schuss, Pause, Resume nach Reload, Presetwahl, Touch-Tasten,
Tastaturfokus, Download, FAQ, Kopieren und reduzierte Bewegung prüfen.
Bei blockiertem Browser-Speicher muss ein sichtbarer Hinweis erscheinen.
Die Spieltasten dürfen außerhalb des Spielfelds nicht das Scrollen blockieren.

## Download bauen

```console
python scripts/build_download.py
```

Erzeugt `docs/downloads/piu-piu-python.zip` aus einer expliziten Dateiliste:
Einstiegspunkt, Windows-Start, Python-Paket, README, Handbuch, Lizenz und
Projektmetadaten. Keine Nutzerprofile, Tests, Caches oder Entwicklungswerkzeuge.
Einheitliche ZIP-Zeitstempel ermöglichen reproduzierbare Ausgaben.
Das ZIP wird mitversioniert, damit der Webseiten-Download sofort funktioniert.
Die beschriebenen Tests und Buildwerkzeuge befinden sich im vollständigen
GitHub-Repository; das Spieler-ZIP enthält nur Spiel und Handbuch.

## EXE optional bauen

Nur in einer dafür freigegebenen Umgebung mit vorhandenem PyInstaller:

```console
python -m PyInstaller --clean --onefile --console --name PIUU piuu.py
```

Unter Windows gibt es zusätzlich `scripts\build_exe.bat`. Das Ergebnis liegt
unter `dist/PIUU.exe` und wird nicht ins Repository aufgenommen. Eine EXE ist
nicht automatisch von Firmensicherheitssoftware freigegeben. Der normale
Python-Start ist der reguläre, getestete Weg.

## GitHub und Veröffentlichung

Quellcode liegt im Repository `philipp-ships-it/piu-piu`. Vor einem Push Tests
und ZIP-Build durchführen. Keine persönlichen Profile committen. GitHub Pages
kann den Ordner `/docs` des Zweigs `main` veröffentlichen. Der lokale
Vorschauprozess allein veröffentlicht nichts.

Das frühere Pushskript wurde entfernt: Es mischte Commit, Repository-Erstellung,
Push und Pages-Konfiguration ohne klaren Prüfpunkt. Git und GitHub bleiben
bewusste, getrennte Entwicklungsschritte.
