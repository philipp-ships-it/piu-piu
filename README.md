# PIU PIU 😈

> Ein ASCII-Endlosrunner fürs Terminal. Du bist ein kleiner Teufel. Du rennst. Du springst. Du machst piu piu.

```
 ____  _   _   _     ____  _   _   _
|  _ \| | | | | |   |  _ \| | | | | |
| |_) | | | | | |   | |_) | | | | | |
|  __/| | | |_| |   |  __/| | | |_| |
|_|   |_|  \___/    |_|    |_|  \___/
```

**🎮 [Im Browser spielen](https://USER.github.io/piuu-piuu-3000/)**

## Starten

Doppelklick auf **`PIUU.bat`** oder:

```
python piuu.py
```

## Steuerung

| Taste | Wirkung |
|---|---|
| `LEERTASTE` / `W` / `↑` | springen — **2× für Doppelsprung** |
| `S` / `↓` | ducken (in der Luft: schnell runter) |
| `ENTER` | **piu piu** schießen — zerstört Hindernisse |
| `P` | Pause |
| `Q` / `STRG+C` | beenden |

## Was passiert da

- Ein 😈 rennt durch eine scrollende ASCII-Landschaft
- Hindernisse: Kakteen `|_|`, Felsen `/  \`, Spikes `/_\`, fliegende Vögel `~o>`
- **Manchmal ist das Wort `piu` selbst das Hindernis** — überspringen oder wegballern
- Im Himmel treiben Sprüche vorbei:
  *piu piu* · *hast du aslok haare?* · *ik maken piu piu* · *und du nie wieder aslok haare* · *autsch\** · *piu*
- Wolken, Parallax-Scrolling, Explosionspartikel, mitlaufender Boden
- Es wird immer schneller. Kills geben +25 Punkte.
- Startscreen mit `[ START ]`, Game-Over-Screen mit **Hall of Piu**

## Optionen

```
python piuu.py --silent        # ohne Ton
python piuu.py --ascii         # kein Emoji, Held wird @>
python piuu.py --speed 0.7     # gemütlicher
python piuu.py --name Kevin    # Name für den Highscore
python piuu.py --scores        # Hall of Piu anzeigen
python piuu.py --demo 300      # Autoplay-Demo (Test, ohne Tastatur)
```

## Highscores

Top 10 landen in **`piu_highscores.json`** im selben Ordner.

## Exe bauen

Doppelklick auf **`build_exe.bat`** → erzeugt `PIUU.exe` (läuft ohne Python).

Manuell:
```
pip install pyinstaller
pyinstaller --onefile --console --name PIUU piuu.py
```

## Web-Demo / GitHub Page

Die Seite liegt in `docs/`. Auf GitHub aktivieren unter
**Settings → Pages → Source: `main` / Ordner `/docs`**.

## Hinweise

Läuft am besten im **Windows Terminal** (Emoji + ANSI-Farben).
In der alten `cmd.exe` sieht 😈 evtl. kaputt aus — dann `--ascii` benutzen.
Terminal sollte mindestens **80×20** Zeichen groß sein.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
