#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIUU PIUU 3000 - die sinnloseste Windows-Terminal-Anwendung der Welt.

Mit Gegnern, Highscore-Datei und Tastatursteuerung.
Sie macht trotzdem hauptsaechlich piuu piuu.

Start:  python piuu.py

Tasten (im Spiel):
    LEERTASTE / ENTER  = schiessen
    A                  = Autofire an/aus
    M                  = Ton an/aus
    N                  = naechster Sound-Modus
    P                  = Pause
    Q / STRG+C         = beenden

Optionen:
    --speed 1.0     Tempo (kleiner = schneller)
    --silent        ohne Ton starten
    --mode laser|blaster|chaos
    --classic       alter Modus ohne Gegner
    --auto          Autofire von Anfang an (kein Tastendruck noetig)
    --scores        Highscore-Tabelle zeigen und beenden
    --name NAME     Name fuer den Highscore
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

IS_WIN = os.name == "nt"

try:
    import winsound
except ImportError:
    winsound = None

if IS_WIN:
    os.system("")

R = "\033[0m"
DIM = "\033[90m"
COLORS = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[95m", "\033[94m"]
RED, YEL, GRN, CYN, MAG = COLORS[0], COLORS[1], COLORS[2], COLORS[3], COLORS[4]

SHIP = ">=|=>"
ENEMIES = ["<@>", "{x}", "(o)", "<#>", "[*]", "<%>", "vVv"]
BOOMS = ["*BOOM*", "*PENG*", "*KRACH*", "*PLOPP*", "*RUMMS*", "*BLUBB*"]
SOUNDS = ["piuu", "piuu piuu", "PIUU!", "piu-piu-piu", "pjuuuu", "pIuU~"]
MODES = ["laser", "blaster", "chaos"]

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piuu_highscores.json")
MAX_SCORES = 10


# ---------------- Tastatur (nicht blockierend) ----------------
class Keys:
    """Liest einzelne Tasten ohne Enter - Windows (msvcrt) und Unix (termios)."""

    def __init__(self):
        self.ok = False
        self._win = False
        self._fd = None
        self._old = None
        try:
            if IS_WIN:
                import msvcrt
                self._m = msvcrt
                self._win = True
                self.ok = True
            else:
                import termios
                import tty
                if sys.stdin.isatty():
                    self._termios = termios
                    self._fd = sys.stdin.fileno()
                    self._old = termios.tcgetattr(self._fd)
                    tty.setcbreak(self._fd)
                    self.ok = True
        except Exception:
            self.ok = False

    def get(self):
        """Gibt gedrueckte Taste als Kleinbuchstabe zurueck, sonst None."""
        if not self.ok:
            return None
        try:
            if self._win:
                if self._m.kbhit():
                    ch = self._m.getch()
                    if ch in (b"\x00", b"\xe0"):
                        self._m.getch()
                        return None
                    if ch == b"\x03":
                        raise KeyboardInterrupt
                    return ch.decode("latin-1").lower()
                return None
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x03":
                    raise KeyboardInterrupt
                return ch.lower()
            return None
        except KeyboardInterrupt:
            raise
        except Exception:
            return None

    def flush(self):
        while self.get() is not None:
            pass

    def restore(self):
        if self._old is not None:
            try:
                self._termios.tcsetattr(self._fd, self._termios.TCSADRAIN, self._old)
            except Exception:
                pass


# ---------------- Sound ----------------
def beep(freq, dur):
    if winsound:
        try:
            winsound.Beep(int(max(37, min(32767, freq))), int(max(1, dur)))
            return
        except Exception:
            pass
    sys.stdout.write("\a")
    sys.stdout.flush()
    time.sleep(dur / 1000.0)


def piuu_sound(mode, silent):
    if silent:
        time.sleep(0.08)
        return
    if mode == "laser":
        f = random.randint(1400, 2200)
        for i in range(9):
            beep(f - i * 110, 12)
    elif mode == "blaster":
        f = random.randint(500, 800)
        for i in range(7):
            beep(f + i * 130, 14)
    else:
        for _ in range(random.randint(4, 12)):
            beep(random.randint(300, 3000), random.randint(8, 30))


def boom_sound(silent):
    if silent:
        time.sleep(0.05)
        return
    for _ in range(6):
        beep(random.randint(90, 320), random.randint(15, 40))


def fanfare(silent):
    if silent:
        return
    for f in (523, 659, 784, 1046):
        beep(f, 90)


def highscore_jingle(silent):
    if silent:
        return
    for f in (784, 988, 1175, 988, 1175, 1568):
        beep(f, 110)


# ---------------- Highscores ----------------
def load_scores():
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_score(name, state):
    scores = load_scores()
    entry = {
        "name": (name or "Pilot")[:16],
        "score": state["score"],
        "kills": state["kills"],
        "shots": state["shots"],
        "wave": state["wave"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    scores.append(entry)
    scores.sort(key=lambda e: e.get("score", 0), reverse=True)
    scores = scores[:MAX_SCORES]
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(DIM + "   (Highscore konnte nicht gespeichert werden: %s)" % e + R)
    rank = scores.index(entry) + 1 if entry in scores else None
    return scores, rank


def print_scores(scores, highlight=None):
    print()
    print(CYN + "  ===== PIUU HALL OF FAME =====" + R)
    if not scores:
        print(DIM + "  Noch keine Eintraege. Sei der erste Held." + R)
        return
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for i, e in enumerate(scores, 1):
        m = medals[i - 1] if i <= 3 else "  "
        row = "  %s %2d. %-16s %7d Pkt   %3d Kills   Welle %-3d %s" % (
            m, i, e.get("name", "?"), e.get("score", 0), e.get("kills", 0),
            e.get("wave", 1), DIM + str(e.get("date", "")) + R)
        print((GRN + row + R) if highlight == i else row)
    print()


# ---------------- Helpers ----------------
def width():
    try:
        return max(40, min(110, os.get_terminal_size().columns - 2))
    except OSError:
        return 78


def out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def line(s):
    out("\r\033[K" + s)


BANNER = r"""
  ____  _____ _   _ _   _   ____  _____ _   _ _   _
 |  _ \|_   _| | | | | | | |  _ \|_   _| | | | | | |
 | |_) | | | | | | | | | | | |_) | | | | | | | | | |
 |  __/  | | | |_| | |_| | |  __/  | | | |_| | |_| |
 |_|     |_|  \___/ \___/  |_|     |_|  \___/ \___/
                    ~ 3000 ~
"""

HELP = ("  LEERTASTE=schiessen   A=Autofire   M=Ton   N=Sound-Modus   "
        "P=Pause   Q=Ende")


# ---------------- Tasten verarbeiten ----------------
def handle_keys(keys, cfg):
    """Return: 'fire', 'quit' oder None."""
    fire = False
    while True:
        k = keys.get()
        if k is None:
            break
        if k in (" ", "\r", "\n"):
            fire = True
        elif k == "a":
            cfg["auto"] = not cfg["auto"]
            out("\r\033[K" + CYN + "  >> Autofire: %s" % ("AN" if cfg["auto"] else "AUS") + R + "\n")
        elif k == "m":
            cfg["silent"] = not cfg["silent"]
            out("\r\033[K" + CYN + "  >> Ton: %s" % ("AUS" if cfg["silent"] else "AN") + R + "\n")
        elif k == "n":
            cfg["mode"] = MODES[(MODES.index(cfg["mode"]) + 1) % len(MODES)]
            out("\r\033[K" + CYN + "  >> Sound-Modus: %s" % cfg["mode"] + R + "\n")
        elif k == "p":
            out("\r\033[K" + YEL + "  || PAUSE - beliebige Taste weiter..." + R)
            while keys.get() is None:
                time.sleep(0.05)
            out("\r\033[K" + GRN + "  >> weiter!" + R + "\n")
        elif k == "q":
            return "quit"
    return "fire" if fire else None


def wait_for_fire(keys, cfg):
    """Wartet im Manuell-Modus auf Schuss. Return 'fire'/'quit'."""
    blink = 0
    while True:
        act = handle_keys(keys, cfg)
        if act == "quit":
            return "quit"
        if act == "fire" or cfg["auto"]:
            return "fire"
        blink += 1
        dot = "\u25cf" if (blink // 6) % 2 == 0 else "\u25cb"
        line(DIM + "  %s bereit - LEERTASTE zum Feuern (A = Autofire)" % dot + R)
        time.sleep(0.08)


# ---------------- Spiel ----------------
def classic_shot(cfg, state):
    w = width()
    c = random.choice(COLORS)
    word = random.choice(SOUNDS)
    trail = random.choice(["-", "=", "~", "*", "\u00b7"])
    max_x = w - len(SHIP) - len(word) - 4
    step = max(1, w // 28)
    for x in range(0, max_x, step):
        line(" " * x + c + SHIP + trail * min(6, max_x - x) + R)
        time.sleep(0.012)
    out("\r\033[K" + " " * max_x + c + SHIP + " " + word + R + "\n")
    piuu_sound(cfg["mode"], cfg["silent"])
    state["shots"] += 1


def battle_round(keys, cfg, state):
    """Ein Gegner. Return 'quit' wenn beendet werden soll."""
    w = width()
    c = random.choice(COLORS)
    trail = random.choice(["-", "=", "~", "*", "\u00b7"])
    enemy = random.choice(ENEMIES)
    hp = random.randint(1, 3)
    ex = w - len(enemy) - 1
    max_x = ex - len(SHIP) - 1
    step = max(1, w // 30)

    while hp > 0:
        line(c + SHIP + R + " " * (max_x + 1) + RED + enemy + R
             + DIM + "  HP:" + "#" * hp + R)
        if wait_for_fire(keys, cfg) == "quit":
            return "quit"

        for x in range(0, max_x, step):
            beam = trail * min(7, max_x - x)
            line(c + SHIP + R + " " * x + c + beam + R
                 + " " * max(0, max_x - x - len(beam)) + RED + enemy + R)
            time.sleep(0.010)
        piuu_sound(cfg["mode"], cfg["silent"])
        hp -= 1
        state["shots"] += 1
        if hp > 0:
            line(c + SHIP + R + " " * (max_x + 1) + YEL + enemy + "  <- haelt noch durch" + R)
            time.sleep(0.10)

    boom = random.choice(BOOMS)
    for frame in (YEL + "\\|/" + R, RED + "-*-" + R, MAG + "/|\\" + R, DIM + " . " + R):
        line(c + SHIP + R + " " * (max_x + 1) + frame + "  " + RED + boom + R)
        time.sleep(0.05)
    boom_sound(cfg["silent"])

    state["kills"] += 1
    pts = random.randint(50, 250) + state["wave"] * 10
    state["score"] += pts
    out("\r\033[K" + c + SHIP + R + " " * (max_x + 1) + GRN + boom + R
        + DIM + "  +%d Punkte" % pts + R + "\n")
    return None


def hud(state, cfg):
    acc = (100.0 * state["kills"] / state["shots"]) if state["shots"] else 0.0
    out(DIM + "  [ Kills: %d | Schuesse: %d | Trefferquote: %.0f%% | Score: %d | Welle: %d | %s%s ]%s\n"
        % (state["kills"], state["shots"], acc, state["score"], state["wave"],
           cfg["mode"], " / stumm" if cfg["silent"] else "", R))


def wave_banner(state, cfg):
    out("\n" + CYN + "  >>> WELLE %d <<<  " % state["wave"]
        + DIM + "(die Gegner werden nicht schlauer)" + R + "\n")
    fanfare(cfg["silent"])


# ---------------- Main ----------------
def main():
    p = argparse.ArgumentParser(description="Macht piuu piuu - mit Gegnern und Highscore.")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--silent", action="store_true")
    p.add_argument("--mode", choices=MODES, default="laser")
    p.add_argument("--classic", action="store_true")
    p.add_argument("--auto", action="store_true", help="Autofire von Anfang an")
    p.add_argument("--scores", action="store_true", help="Highscores zeigen")
    p.add_argument("--name", default=None, help="Spielername")
    a = p.parse_args()

    if a.scores:
        print_scores(load_scores())
        return

    if IS_WIN:
        try:
            os.system("title PIUU PIUU 3000")
        except Exception:
            pass

    print(random.choice(COLORS) + BANNER + R)
    print(DIM + HELP + R)

    keys = Keys()
    cfg = {"mode": a.mode, "silent": a.silent, "auto": a.auto or a.classic or not keys.ok}
    if not keys.ok:
        print(DIM + "  (keine Tastatureingabe verfuegbar - laeuft im Autofire-Modus)" + R)
    keys.flush()

    state = {"kills": 0, "shots": 0, "score": 0, "wave": 1}
    name = a.name or os.environ.get("USERNAME") or os.environ.get("USER") or "Pilot"

    if not a.classic:
        wave_banner(state, cfg)

    try:
        while True:
            if a.classic:
                classic_shot(cfg, state)
                if state["shots"] % 10 == 0:
                    print(DIM + "   ... %d x piuu abgefeuert. Kein Ende in Sicht." % state["shots"] + R)
                if handle_keys(keys, cfg) == "quit":
                    break
            else:
                if battle_round(keys, cfg, state) == "quit":
                    break
                if state["kills"] % 5 == 0:
                    hud(state, cfg)
                    state["wave"] += 1
                    wave_banner(state, cfg)
            time.sleep(random.uniform(0.05, 0.25) * a.speed)
    except KeyboardInterrupt:
        pass
    finally:
        keys.restore()

    print()
    if a.classic:
        print(YEL + "   Munition geschont. %d piuus insgesamt. Tschau!" % state["shots"] + R)
        return

    print(YEL + "   Feierabend! %d Gegner pulverisiert, %d Schuesse, %d Punkte."
          % (state["kills"], state["shots"], state["score"]) + R)

    if state["score"] > 0:
        scores, rank = save_score(name, state)
        if rank:
            print(GRN + "   Platz %d in der Hall of Fame als '%s'!" % (rank, name) + R)
            if rank == 1:
                print(MAG + "   *** NEUER HIGHSCORE! ***" + R)
                highscore_jingle(cfg["silent"])
        print_scores(scores, highlight=rank)
    print(DIM + "   Sinn des Ganzen: weiterhin unklar." + R)


if __name__ == "__main__":
    main()
