# Architektur

## Leitgedanken

Die frühere Einzeldatei ist in Fachmodule zerlegt. Die Simulation kennt weder
Terminal noch Festplatte, Systemuhr oder Soundgerät. Ihr Ergebnis hängt von
Ausgangszustand, eigenem Zufallsgenerator und Aktionen ab. Darstellung liefert
Text, ohne den Spielzustand zu ändern. I/O wird nur im Anwendungsablauf verknüpft.

## Module

| Modul | Aufgabe und zentrale Schnittstelle |
|---|---|
| `piuu.py`, `piu/__main__.py` | Einstieg, delegiert an `app.main` |
| `piu/settings.py` | `Settings`, Presets, Cheats, Werteprüfung, JSON-Konvertierung |
| `piu/geometry.py` | Unveränderliches `Geometry(width, height)` mit Boden/Spielerposition |
| `piu/assets.py` | ASCII-Grafiken und `make_obstacle(level, rng)` |
| `piu/engine.py` | `Game`, reine Aktionen und feste Simulationsschritte |
| `piu/checkpoint.py` | Snapshot-Kodierung/-Validierung, Wiederherstellung des RNG |
| `piu/colors.py` | ANSI-Farben und Steuerzeichen |
| `piu/buffer.py` | `Buf`: Zeichenraster, Grafikplatzierung und Clipping |
| `piu/rendering.py` | Start, Settings, Spiel, Meldungen, Game Over als Text |
| `piu/menu.py` | Zustandsautomat für Menünavigation und neue Runde |
| `piu/timing.py` | `FixedClock`, Sammlung verstrichener Zeit in 18-Hz-Takten |
| `piu/terminal.py` | Plattformtastatur, Terminal-Lebenszyklus, Soundwarteschlange |
| `piu/storage.py` | Profile, Bestenliste, Sperre, atomare Speicherung und Backup |
| `piu/diagnostics.py` | Umgebungstest und begrenztes Fehlerprotokoll |
| `piu/app.py` | CLI, Menü-/Rundenablauf und Speicherzeitpunkte |

## Ablauf

```text
CLI → Profil sperren/laden → Startmenü → neue/gespeicherte Runde
                                ↓                  ↓
                            Settings            Eingabeaktionen
                                ↓                  ↓
                           Profil sichern      FixedClock → Game.step
                                                   ↓
                                      Rendering + Soundereignisse
                                                   ↓
                                    Autosave / Pause / Q / Game Over
```

Die Engine verwendet einen festen Zeitschritt von 1/18 Sekunde. `FixedClock`
sammelt kurze Zeitabschnitte; nach langen Hängern werden höchstens vier Takte
nachgeholt. Pause und Speicherpausen setzen den Timer zurück. Das verhindert
unfaire Zeitsprünge. Absolute Echtzeitgarantien bei einem blockierten Betriebssystem
sind damit nicht gemeint.

Die Reihenfolge eines Schritts ist fest: Distanz, Spielerphysik, Munition,
Hintergrund, Hindernisse, Projektile/Partikel, Spielerkollision, Punkte.
Nach dem Tod ändern Aktionen und Schritte den Zustand nicht mehr.

## Engine verwenden

```python
from piu.engine import Game
from piu.geometry import Geometry
from piu.settings import Settings

settings = Settings()
settings.preset("leicht")
game = Game(settings=settings, geometry=Geometry(80, 20), seed=0)
game.jump()
game.step()
events = game.drain_events()
snapshot = game.snapshot()
restored = Game.from_snapshot(snapshot)
```

`Game` kopiert die Settings beim Start. Geometrie ist pro Instanz vorhanden;
globale mutable Spielfeldgrößen gibt es nicht mehr. `on_resize(geometry)` passt
laufende Objekte kontrolliert an. `snapshot()` kopiert Listen; gespeicherte oder
geladene Zustände teilen keine veränderlichen Listen mit der Ursprungsrunde.

Sound wird als Ereignisname ausgeliefert. `Audio` spielt Ereignisse in einem
separaten Thread mit begrenzter Warteschlange. Bei Überlast dürfen Soundeffekte
ausfallen; sie verändern niemals die Simulation. Sound nutzt keinen Spiel-RNG.

## Datenstrukturen

Die Hindernisse behalten bewusst kleine, serialisierbare Datensätze:
`x`, `art`, `art2`, `kind`, `off`, `w`, `h`, `f`.
Projektile bestehen aus x/Zeile, Partikel aus Position, Geschwindigkeit,
Lebenszeit und Zeichen. Die zentrale Snapshot-Validierung prüft diese Formen.
So bleiben das Katalogformat und die bestehende Spielmechanik überschaubar,
ohne ein unnötiges Entity-Component-System einzuführen.

Schüsse verwenden eine Prüfung der **relativen Bewegung über den ganzen Takt**.
Dadurch treffen sich schnell kreuzende Projektile/Hindernisse auch dann,
wenn ihre Endpositionen nicht mehr überlappen. Die Spielerhitbox bleibt
zeilenbasiert; Details zum Ducken stehen in der Spielanleitung.

## Speichergrenze

`Store` hält den Profilzustand im Speicher. `save()` schreibt atomar oder wirft
`StorageError`; ein Fehler wird nicht als erfolgreicher Rekord ausgegeben.
`remember(game)` sichert einen Snapshot. `finish(game, name)` verlangt eine
beendete Runde, verbucht Nicht-Cheat-Punkte und entfernt den Snapshot gemeinsam.
Bei Fehlern wird der Zustand der Transaktion zurückgerollt. `last_run_id`
macht die Wiederholung desselben Abschlusses nach einem Neustart idempotent.

Details zu Schema, Migration und Recovery: [Daten](DATEN.md).

## Browserarchitektur

Die neue Seite in `docs/` ist eigenständig und ersetzt das frühere HTML vollständig:

- `index.html`: semantische deutsche Inhalte, Tastaturhinweise und Download.
- `assets/style.css`: responsives Arcade-Design, lokale Schriftfamilien, Bewegung.
- `assets/world.js`: reine Browser-Simulation und Canvas-Zeichnen; importierbar
  ohne DOM für Node-Tests.
- `assets/site.js`: Tastatur/Touch, DOM, Browser-Speicher, feste Takte und Pause.

Es gibt keine CDN-, Framework-, Font-, Analytics- oder API-Abhängigkeiten.
Die Seite benötigt einen HTTP-Server für JavaScript-Module. `docs/` bleibt
bewusst der Veröffentlichungsordner für GitHub Pages; schriftliche
Projektdokumentation liegt getrennt unter `handbuch/`.
