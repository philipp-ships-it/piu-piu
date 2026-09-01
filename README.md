# PIU PIU (ง•_•)ง

> Ein ASCII-Endlosrunner fürs Terminal. Ein kleines Kaomoji-Männchen rennt, springt und macht piu piu.

```
 ____  _   _   _     ____  _   _   _
|  _ \| | | | | |   |  _ \| | | | | |
| |_) | | | | | |   | |_) | | | | | |
|  __/| | | |_| |   |  __/| | | |_| |
|_|   |_|  \___/    |_|    |_|  \___/
```

**🎮 [Im Browser spielen](https://philipp-ships-it.github.io/piu-piu/)**

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
| `ENTER` | **piu piu** schießen — 10 Schuss pro Magazin |
| `P` | Pause |
| `Q` / `STRG+C` | beenden |

## Der Held

Ein Kaomoji-Männchen mit eigener Pose für jeden Zustand (alle exakt 7 Zeichen breit,
damit nichts wackelt):

| Zustand | Pose |
|---|---|
| rennen | `(ง•_•)ง` ↔ `ᕦ(•_•)ᕤ` (animiert) |
| springen | `\(•o•)/` |
| fallen | `/(•_•)\` |
| ducken | `(>_<)__` |
| schießen | `(ง•_•)=` |
| tot | `~(X_X)~` |

Mit `--ascii` gibt's die reine ASCII-Variante `(o_o)/` für alte Terminals.

## Munition

Ballern ist **begrenzt**:

- **10 Schuss pro Magazin**
- Das Magazin frischt sich alle **30 Sekunden** von selbst auf
- Wer leerballert, muss **5 Sekunden nachladen** — solange macht es nur `*klick*`
- HUD zeigt `piu [||||||....] 6  17s` bzw. `RELOAD [####......] 3.1s`

Also: nicht jedes `piu` zählt, überspringen ist oft schlauer.

## Hindernisse

Über **30 verschiedene ASCII-Hindernisse**, die gewichtet nach Level auftauchen —
je weiter du kommst, desto exotischer wird es:

```
  _      __     /\      %%%    .-.     ,---.   +---+    ___
 | |    /  \    /_\    %%%%%  (ooo)    |###|   |\ /|   /RIP\
_|_|_   \__/           \|/     |_|     `---'   +---+   |___|
 Kaktus  Stein  Spike   Busch   Pilz    Fass    Kiste   Grab
```

Dazu fliegendes Zeug auf verschiedenen Höhen (animiert, 2 Frames):
Vögel `~o>`, Fledermäuse `/\o/\`, Drohnen `[+]`, Geister `(o o)`, UFOs `(-o-)`.

Und natürlich Wort-Hindernisse: `piu` · `piu piu` · `autsch*` · `aslok` · `haare` · `nope`
— am Boden oder in der Luft.

## Dynamik

- **Tempo** wächst sanft mit der Strecke (exponentiell gedämpft, x1.0 → x2.7)
  plus einer Wellen-Modulation, damit es sich nicht monoton anfühlt
- **Abstände** skalieren mit dem Tempo, damit die Reaktionszeit fair bleibt
- Dazu Rhythmus-Wechsel: manchmal ein **Doppelschlag**, manchmal eine **Verschnaufpause**
- Das HUD zeigt den aktuellen Tempo-Multiplikator als `x1.8`

## Was passiert da

- Das Männchen rennt durch eine scrollende ASCII-Landschaft
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
python piuu.py --ascii         # reines ASCII-Maennchen (o_o)/
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
In der alten `cmd.exe` sehen die Kaomoji evtl. kaputt aus — dann `--ascii` benutzen.
Terminal sollte mindestens **80×20** Zeichen groß sein.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
