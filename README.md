# PIU PIU — Kleiner Held. Großes Piu.

```text
 ____  ___ _   _   ____  ___ _   _
|  _ \|_ _| | | | |  _ \|_ _| | | |
| |_) || || | | | | |_) || || | | |
|  __/ | || |_| | |  __/ | || |_| |
|_|   |___|\___/  |_|   |___|\___/

       (ง•_•)ง   - - piu!    |#|
  ___/__/__/__/__/__/__/__/__/__/___
```

Ein deutscher ASCII-Endlosrunner: springen, Hindernisse wegschießen und den
eigenen Rekord schlagen. Das **Python-Spiel** läuft ohne zusätzliche Pakete.
Die **Webseite** enthält eine eigenständige, direkt spielbare Browser-Version.

## Schnellstart

Voraussetzung: **Python 3.10 oder neuer**. Windows: `PIUU.bat` doppelklicken.
Alternativ im entpackten Projektordner:

```console
python piuu.py
```

Auch `python -m piu` funktioniert. Unter Windows kann der Python-Launcher mit
`py -3 piuu.py` verwendet werden. Kein `pip install` erforderlich.
Ein explizites, freigegebenes Python lässt sich über `PIU_PYTHON` für die
Windows-Startdatei angeben. Firmen-Sicherheitssoftware wird nicht umgangen.

## Spiel und Einstellungen

| Im Spiel | Aktion |
|---|---|
| Leertaste / W / ↑ | Springen; ein zweites Mal für den Doppelsprung |
| Enter | Schießen |
| S / ↓ | Ducken; in der Luft schneller fallen |
| P | Pause und speichern |
| Q / Strg+C | Runde speichern und beenden |

Im Startmenü gibt es **START**, **SETTINGS** und **ENDE**. Bei vorhandenem
Rundenstand erscheint **FORTSETZEN**. Vor dem Ersetzen einer Runde wird gefragt.
Menüs: W/S oder ↑/↓ wählen, A/D oder ←/→ ändern, Enter/Leertaste bestätigen,
Escape zurück. Die Settings-Liste scrollt in kleinen Fenstern.

| Preset | Tempo | Hindernisse | Magazin |
|---|---|---|---|
| leicht | x0.75 | wenig | 15 |
| normal | x1.00 | normal | 10 |
| schwer | x1.35 | viele | 8 |
| irre | x1.75 | extrem | 6 |

Tempo, Dichte und Magazin sind einzeln einstellbar; das Label wechselt dann zu
**eigen**. Fünf kombinierbare Cheats: unendlich Munition, Nachladen in 0,35 s,
Unverwundbarkeit, doppelte Punkte, Mega-Sprung mit 45 % mehr Sprungkraft.

**Cheat-Runden zählen weder für den Highscore noch zum Laufzähler.**
Schwierigkeit ist kein Cheat: Auch leicht und eigen zählen regulär.

## Alles bleibt erhalten

Settings werden sofort gespeichert. Die Runde wird alle **fünf Sekunden
Spielzeit**, beim Start, bei Pause und beim Beenden gesichert. Fortsetzen erhält
Position, Munition, Nachladezeit, Hindernisse, Punkte und die Zufallsfolge.

- Windows: `%LOCALAPPDATA%\PiuPiu`
- Linux/macOS: `$XDG_STATE_HOME/piu-piu`, sonst `~/.local/state/piu-piu`
- Eigener Ordner: `python piuu.py --data-dir "D:\Spiele\PiuDaten"`

Profil, Backup und Fehlerprotokoll liegen dort gemeinsam. Alte Score-Dateien
neben dem bisherigen Spiel werden beim ersten Start übernommen und behalten.
Die Browser-Version speichert unabhängig im lokalen Browserspeicher.

## Häufige Optionen

```console
python piuu.py --silent
python piuu.py --ascii --size 80x20
python piuu.py --name Alex
python piuu.py --scores
python piuu.py --diagnose
python piuu.py --demo 400 --seed 0
python piuu.py --help
```

Bei Problemen zuerst `--diagnose` und die [Fehlerbehebung](handbuch/FEHLERBEHEBUNG.md)
lesen. Eine Demo benötigt kein interaktives Terminal und schreibt keine Profile.

## Handbuch

| Dokument | Inhalt |
|---|---|
| [Spielanleitung](handbuch/SPIELANLEITUNG.md) | Regeln, Bedienung, Presets, Cheats, Optionen |
| [Daten und Wiederherstellung](handbuch/DATEN.md) | Speicherformat, Backups, Migration, Fortsetzen |
| [Fehlerbehebung](handbuch/FEHLERBEHEBUNG.md) | Symptome, Diagnose, Lösungen und Fehlercodes |
| [Architektur](handbuch/ARCHITEKTUR.md) | Module, Datenfluss, öffentliche Schnittstellen, Invarianten |
| [Entwicklung und QA](handbuch/ENTWICKLUNG.md) | Tests, Erweiterungen, Webseite, Download- und EXE-Build |
| [QA-Bericht](handbuch/QA_BERICHT.md) | Konkrete Prüfergebnisse und verbleibende Prüfgrenzen |
| [Änderungen](handbuch/AENDERUNGEN.md) | Umbau und Änderungen gegenüber der Einzeldatei |

## Projektstruktur

```text
piuu.py                 Kleiner, stabiler Einstiegspunkt
PIUU.bat                Windows-Start mit vorhandener Python-Installation
piu/                    Python-Spiel als getrennte Fachmodule
tests/                  Deterministische Python- und Browser-Tests
handbuch/               Durchgehende deutsche Dokumentation
scripts/                QA, Vorschau und Build-Hilfen
docs/                   Neue statische Webseite (GitHub Pages)
  assets/               CSS, Browser-Simulation, Oberfläche, Favicon
  downloads/            Reproduzierbar gebautes Python-ZIP
```

## Tests und Vorschau

```console
python -m unittest discover -s tests -v
node --test tests/web/*.test.js
node scripts/preview.mjs
```

Die Vorschau ist unter `http://127.0.0.1:4173` erreichbar. Node ab Version 20
wird nur für Webentwicklung und deren Tests benötigt, nicht für das Python-Spiel
oder für Besucher der veröffentlichten Webseite. Keine npm-Pakete erforderlich.
Der Download wird mit `python scripts/build_download.py` gebaut.

## Lizenz

[MIT](LICENSE). Ursprüngliches Spiel: Philipp Paulik und die PIU-PIU-Mitwirkenden.
Keine Konten, keine Werbung, kein Tracking.
