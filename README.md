# PIUU PIUU 3000

> Eine völlig sinnlose Windows-Terminal-Anwendung, die piuu piuu macht.

**🎮 [Im Browser ausprobieren](https://USER.github.io/piuu-piuu-3000/)** — Web-Demo mit echtem Laser-Sound.

## Starten

Doppelklick auf **`PIUU.bat`** (braucht installiertes Python)
oder im Terminal:

```
python piuu.py
```

## Tasten im Spiel

| Taste | Wirkung |
|---|---|
| `LEERTASTE` / `ENTER` | schießen |
| `A` | Autofire an/aus |
| `M` | Ton an/aus |
| `N` | nächster Sound-Modus (laser → blaster → chaos) |
| `P` | Pause |
| `Q` oder `STRG+C` | beenden + Highscore speichern |

## Optionen

```
python piuu.py --auto            # ballert von allein
python piuu.py --mode chaos      # völlig irre Töne
python piuu.py --speed 0.2       # schneller (kleiner = schneller)
python piuu.py --silent          # ohne Ton
python piuu.py --classic         # alter Modus, nur Laser ohne Gegner
python piuu.py --name Kevin      # Name für den Highscore
python piuu.py --scores          # Hall of Fame anzeigen und beenden
```

## Highscores

Werden automatisch beim Beenden in **`piuu_highscores.json`** gespeichert
(Top 10, im selben Ordner). Punkte gibt's pro zerstörtem Gegner, mehr in
höheren Wellen. Alle 5 Kills startet eine neue Welle mit Fanfare.

## Exe bauen

Doppelklick auf **`build_exe.bat`** → erzeugt `PIUU.exe` (läuft ohne Python).

Manuell:
```
pip install pyinstaller
pyinstaller --onefile --console --name PIUU piuu.py
```

## Dateien

- `piuu.py` – das Programm
- `PIUU.bat` – Starter für Windows
- `build_exe.bat` – baut die Exe
- `piuu_highscores.json` – entsteht beim ersten Spiel

## Web-Demo / GitHub Page

Die Seite liegt in `docs/`. Auf GitHub aktivieren unter
**Settings → Pages → Source: `main` / Ordner `/docs`**.
Danach erreichbar unter `https://USER.github.io/piuu-piuu-3000/`.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
