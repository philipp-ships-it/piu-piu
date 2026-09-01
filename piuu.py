#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIU PIU - ein ASCII-Endlosrunner fuers Windows-Terminal.

Ein kleines Kaomoji-Maennchen. Es rennt. Es springt. Es macht piu piu.

    LEERTASTE / W / PFEIL HOCH  = springen (2x fuer Doppelsprung)
    S / PFEIL RUNTER            = ducken
    ENTER                       = piu piu schiessen (10 Schuss pro Magazin)
    P                           = Pause
    Q / STRG+C                  = beenden

Start:  python piu.py
"""

import argparse
import json
import math
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
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------- Farben ----------------
R = "\033[0m"
DIM = "\033[90m"
RED = "\033[91m"
YEL = "\033[93m"
GRN = "\033[92m"
CYN = "\033[96m"
MAG = "\033[95m"
BLU = "\033[94m"
WHT = "\033[97m"

HIDE = "\033[?25l"
SHOW = "\033[?25h"
HOME = "\033[H"
CLEAR = "\033[2J"

# --- Spielfeld-Geometrie: passt sich dem Terminal an ---
MIN_W, MAX_W = 46, 200
MIN_H, MAX_H = 14, 44

W = 78
H = 18
GROUND = H - 4
PX = 6
TOO_SMALL = False


def term_size():
    try:
        c = os.get_terminal_size()
        return c.columns, c.lines
    except OSError:
        return 80, 24


def fit():
    """Terminalgroesse lesen, W/H/GROUND/PX anpassen. True bei Aenderung."""
    global W, H, GROUND, PX, TOO_SMALL
    cols, rows = term_size()
    TOO_SMALL = cols < MIN_W + 1 or rows < MIN_H + 1
    nw = max(MIN_W, min(MAX_W, cols - 1))
    nh = max(MIN_H, min(MAX_H, rows - 1))
    ng = nh - max(3, min(6, nh // 5))
    npx = max(3, min(10, nw // 13))
    changed = (nw, nh, ng, npx) != (W, H, GROUND, PX)
    W, H, GROUND, PX = nw, nh, ng, npx
    return changed


def set_size(cols, rows):
    global W, H, GROUND, PX
    W = max(MIN_W, min(MAX_W, cols))
    H = max(MIN_H, min(MAX_H, rows))
    GROUND = H - max(3, min(6, H // 5))
    PX = max(3, min(10, W // 13))

# ---------------- Der Held (Kaomoji-Maennchen) ----------------
# Alle Posen sind gleich breit, damit nichts wackelt.
HERO_W = 7

HERO_KAO = {
    "run":   ["(\u0e07\u2022_\u2022)\u0e07", "\u1566(\u2022_\u2022)\u1564"],
    "jump":  ["\\(\u2022o\u2022)/"],
    "fall":  ["/(\u2022_\u2022)\\"],
    "duck":  ["(>_<)__"],
    "shoot": ["(\u0e07\u2022_\u2022)="],
    "dead":  ["~(X_X)~"],
}
HERO_ASCII = {
    "run":   ["(o_o)/ ", "(o_o)\\ "],
    "jump":  ["\\(o_o)/"],
    "fall":  ["/(o_o)\\"],
    "duck":  ["(>_<)__"],
    "shoot": ["(o_o)=>"],
    "dead":  ["~(x_x)~"],
}

MAG_SIZE = 10          # Schuss pro Magazin
MAG_WINDOW = 30.0      # Sekunden bis das Magazin sich selbst auffrischt
RELOAD_TIME = 5.0      # Sekunden Nachladen wenn leergeballert
FPS = 18.0             # Frames pro Sekunde (Frame = 1/FPS Sekunden)

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piu_highscores.json")
MAX_SCORES = 10

# ---------------- Hintergrund-Spruechle ----------------
PHRASES = [
    "piu piu",
    "hast du aslok haare?",
    "ik maken piu piu",
    "und du nie wieder aslok haare",
    "autsch*",
    "piu",
    "piu piu piu",
    "wer rennt der rennt",
    "aslok? nie gehoert",
    "PIU!",
    "ik ben een piu",
    "haare weg. piu.",
]

CLOUDS = [
    "   .-~-.   ",
    " (  ___  ) ",
    "  `-...-`  ",
]

# ---------------- Hindernisse ----------------
# Kleine Kakteen
CACTUS_S  = ["  _  ", " | | ", "_|_|_"]
CACTUS_L  = [" _ _ ", "| | |", "|_|_|", "  |  "]
CACTUS_XL = [" _ _ _ ", "| | | |", "|_|_|_|", "   |   ", "   |   "]

# Steine / Geroell
ROCK      = [" __ ", "/  \\", "\\__/"]
ROCK_BIG  = ["  ___  ", " /   \\ ", "/     \\", "\\_____/"]
PEBBLES   = ["o O o"]

# Spikes
SPIKE     = ["/\\", "/_\\"]
SPIKE_2   = ["/\\/\\", "/__ _\\"]
SPIKE_3   = ["/\\/\\/\\", "/_ _ _\\"]

# Sonstiger Kram am Boden
BARREL    = [",---.", "|###|", "|###|", "`---'"]
CRATE     = ["+---+", "|\\ /|", "|/ \\|", "+---+"]
FENCE     = ["|-|-|", "|-|-|", "|_|_|"]
TOMBSTONE = [" ___ ", "/RIP\\", "|   |", "|___|"]
BUSH      = [" %%% ", "%%%%%", " \\|/ "]
MUSHROOM  = [" .-. ", "(ooo)", " |_| "]
TRASHCAN  = ["[___]", "|:::|", "|:::|", "|___|"]
SNOWMAN   = [" (o) ", "(   )", "(   )"]
PYRAMID   = ["  ^  ", " /-\\ ", "/---\\"]

# Fliegendes Zeug (2 Frames fuer Animation)
BIRD_A    = ["~o>", " ^ "]
BIRD_B    = ["~o>", " v "]
BAT_A     = ["/\\o/\\"]
BAT_B     = ["_o_"]
UFO_A     = [" .-. ", "(-o-)", "'* *'"]
UFO_B     = [" .-. ", "(-o-)", "* * *"]
DRONE_A   = ["[+]", "/ \\"]
DRONE_B   = ["[+]", "\\ /"]
GHOST_A   = [".oOo.", "(o o)", " ~~~ "]
GHOST_B   = [".oOo.", "(o o)", " www "]

# Wort-Hindernisse
WORDS_LOW  = ["piu", "piu piu", "PIU", "autsch*", "piu!"]
WORDS_HIGH = ["piu piu piu", "aslok", "haare", "PIU PIU", "nope"]

# (art_a, art_b, kind, offset_choices, min_level, gewicht)
CATALOG = [
    (CACTUS_S,   None,    "solid", [0],    0, 10),
    (ROCK,       None,    "solid", [0],    0, 8),
    (SPIKE,      None,    "solid", [0],    0, 7),
    (PEBBLES,    None,    "solid", [0],    0, 4),
    (BUSH,       None,    "solid", [0],    0, 5),
    (CACTUS_L,   None,    "solid", [0],    1, 7),
    (CRATE,      None,    "solid", [0],    1, 5),
    (MUSHROOM,   None,    "solid", [0],    1, 4),
    (SPIKE_2,    None,    "solid", [0],    1, 5),
    (BIRD_A,     BIRD_B,  "bird",  [3, 4], 1, 7),
    (BARREL,     None,    "solid", [0],    2, 5),
    (FENCE,      None,    "solid", [0],    2, 4),
    (TRASHCAN,   None,    "solid", [0],    2, 4),
    (BAT_A,      BAT_B,   "bird",  [4, 5], 2, 5),
    (SPIKE_3,    None,    "solid", [0],    3, 5),
    (TOMBSTONE,  None,    "solid", [0],    3, 4),
    (PYRAMID,    None,    "solid", [0],    3, 4),
    (DRONE_A,    DRONE_B, "bird",  [3, 5], 3, 5),
    (CACTUS_XL,  None,    "solid", [0],    4, 5),
    (SNOWMAN,    None,    "solid", [0],    4, 3),
    (GHOST_A,    GHOST_B, "bird",  [3, 4], 4, 4),
    (UFO_A,      UFO_B,   "bird",  [4, 5], 5, 4),
]


def make_obstacle(level):
    """Liefert dict mit art/art2/kind/off - gewichtet nach Level."""
    # Woerter kommen extra oft
    if random.random() < 0.16:
        hi = level >= 2 and random.random() < 0.5
        w = random.choice(WORDS_HIGH if hi else WORDS_LOW)
        return {"art": [w], "art2": None, "kind": "word",
                "off": random.choice([3, 4]) if hi else 0}

    opts = [c for c in CATALOG if c[4] <= level]
    weights = [c[5] for c in opts]
    a, b, kind, offs, _, _ = random.choices(opts, weights=weights)[0]
    return {"art": list(a), "art2": (list(b) if b else None),
            "kind": kind, "off": random.choice(offs)}


# ---------------- Sound ----------------
def beep(f, d):
    if winsound:
        try:
            winsound.Beep(int(max(37, min(32767, f))), int(max(1, d)))
        except Exception:
            pass


class Snd:
    def __init__(self, silent):
        self.silent = silent

    def piu(self):
        if self.silent:
            return
        f = random.randint(1500, 2100)
        for i in range(4):
            beep(f - i * 220, 9)

    def jump(self):
        if self.silent:
            return
        beep(700, 14)
        beep(1100, 14)

    def hit(self):
        if self.silent:
            return
        for f in (300, 220, 160, 110):
            beep(f, 45)

    def kill(self):
        if self.silent:
            return
        beep(900, 12)
        beep(400, 22)

    def click(self):
        if self.silent:
            return
        beep(150, 18)
        beep(90, 14)

    def empty(self):
        if self.silent:
            return
        beep(400, 40)
        beep(260, 60)

    def reload_done(self):
        if self.silent:
            return
        beep(700, 40)
        beep(1050, 55)

    def start(self):
        if self.silent:
            return
        for f in (523, 659, 784, 1046):
            beep(f, 80)


# ---------------- Tastatur ----------------
class Keys:
    def __init__(self):
        self.ok = False
        self._win = False
        self._old = None
        try:
            if IS_WIN:
                import msvcrt
                self._m = msvcrt
                self._win = True
                self.ok = True
            else:
                import termios, tty
                if sys.stdin.isatty():
                    self._t = termios
                    self._fd = sys.stdin.fileno()
                    self._old = termios.tcgetattr(self._fd)
                    tty.setcbreak(self._fd)
                    self.ok = True
        except Exception:
            self.ok = False

    def get(self):
        """'jump' | 'duck' | 'shoot' | 'pause' | 'quit' | None"""
        if not self.ok:
            return None
        try:
            if self._win:
                if not self._m.kbhit():
                    return None
                ch = self._m.getch()
                if ch in (b"\x00", b"\xe0"):
                    c2 = self._m.getch()
                    return {b"H": "jump", b"P": "duck"}.get(c2)
                if ch == b"\x03":
                    return "quit"
                return self._map(ch.decode("latin-1"))
            import select
            if not select.select([sys.stdin], [], [], 0)[0]:
                return None
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                if select.select([sys.stdin], [], [], 0.001)[0]:
                    sys.stdin.read(1)
                    c = sys.stdin.read(1)
                    return {"A": "jump", "B": "duck"}.get(c)
                return "quit"
            if ch == "\x03":
                return "quit"
            return self._map(ch)
        except Exception:
            return None

    @staticmethod
    def _map(ch):
        ch = ch.lower()
        if ch in (" ", "w"):
            return "jump"
        if ch in ("\r", "\n"):
            return "shoot"
        if ch == "s":
            return "duck"
        if ch == "p":
            return "pause"
        if ch == "q":
            return "quit"
        return None

    def flush(self):
        for _ in range(50):
            if self.get() is None:
                break

    def wait_any(self):
        while True:
            k = self.get()
            if k:
                return k
            time.sleep(0.03)

    def restore(self):
        if self._old is not None:
            try:
                self._t.tcsetattr(self._fd, self._t.TCSADRAIN, self._old)
            except Exception:
                pass


# ---------------- Framebuffer ----------------
class Buf:
    def __init__(self):
        self.w = W
        self.h = H
        self.g = [[" "] * self.w for _ in range(self.h)]
        self.c = [[None] * self.w for _ in range(self.h)]

    def put(self, x, y, s, col=None, wide=False):
        if y < 0 or y >= self.h:
            return
        x = int(x)
        for i, chpos in enumerate(s):
            xx = x + i
            if 0 <= xx < self.w:
                self.g[y][xx] = chpos
                self.c[y][xx] = col
        if wide and 0 <= x + 1 < self.w:
            self.g[y][x + 1] = ""
            self.c[y][x + 1] = col

    def art(self, x, y_bottom, art, col=None):
        for i, row in enumerate(reversed(art)):
            self.put(x, y_bottom - i, row, col)

    def render(self):
        lines = []
        for y in range(self.h):
            parts = []
            cur = None
            for x in range(self.w):
                ch = self.g[y][x]
                if ch == "":
                    continue
                col = self.c[y][x]
                if col != cur:
                    parts.append(R if col is None else col)
                    cur = col
                parts.append(ch)
            parts.append(R)
            lines.append("".join(parts).rstrip() + "\033[K")
        return "\n".join(lines)


# ---------------- Highscore ----------------
def _norm(name):
    """Vergleichsschluessel fuer Spielernamen (case/space-insensitiv)."""
    return " ".join((name or "").split()).lower()


def load_scores():
    """Liest die Bestenliste. Alte Dateien mit Duplikaten werden
    beim Laden automatisch zu einem Eintrag pro Spieler zusammengefasst."""
    try:
        with open(SCORE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, list):
            return []
    except Exception:
        return []

    merged = {}
    for e in d:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name", "Piu"))[:14]
        k = _norm(name)
        cur = merged.get(k)
        score = int(e.get("score", 0) or 0)
        kills = int(e.get("kills", 0) or 0)
        runs = int(e.get("runs", 1) or 1)
        if cur is None:
            merged[k] = {"name": name, "score": score, "kills": kills,
                         "runs": runs, "date": e.get("date", "")}
        else:
            # Bestwert behalten, Laeufe aufsummieren
            cur["runs"] = cur.get("runs", 1) + runs
            if score > cur["score"]:
                cur.update({"name": name, "score": score, "kills": kills,
                            "date": e.get("date", cur.get("date", ""))})

    out_list = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
    return out_list[:MAX_SCORES]


def save_score(name, score, kills):
    """Speichert einen Lauf. Pro Spieler bleibt nur die Bestleistung.
    Rueckgabe: (liste, platz, is_record) - is_record = eigener Rekord verbessert."""
    scores = load_scores()
    name = (name or "Piu")[:14]
    key = _norm(name)
    score = int(score)

    entry = None
    for e in scores:
        if _norm(e.get("name", "")) == key:
            entry = e
            break

    if entry is None:
        entry = {"name": name, "score": score, "kills": int(kills),
                 "runs": 1, "date": datetime.now().strftime("%d.%m.%y %H:%M")}
        scores.append(entry)
        improved = True
    else:
        entry["runs"] = int(entry.get("runs", 1)) + 1
        entry["name"] = name
        improved = score > int(entry.get("score", 0))
        if improved:
            entry["score"] = score
            entry["kills"] = int(kills)
            entry["date"] = datetime.now().strftime("%d.%m.%y %H:%M")

    scores.sort(key=lambda x: x.get("score", 0), reverse=True)
    del scores[MAX_SCORES:]

    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    rank = None
    for i, e in enumerate(scores, 1):
        if _norm(e.get("name", "")) == key:
            rank = i
            break
    return scores, rank, improved


def best():
    s = load_scores()
    return s[0]["score"] if s else 0


# ---------------- Screens ----------------
TITLE = [
    " ____  _   _   _     ____  _   _   _ ",
    "|  _ \\| | | | | |   |  _ \\| | | | | |",
    "| |_) | | | | | |   | |_) | | | | | |",
    "|  __/| | | |_| |   |  __/| | | |_| |",
    "|_|   |_|  \\___/    |_|    |_|  \\___/",
]


def _center(b, y, text, col=None):
    b.put((b.w - len(text)) // 2, y, text, col)

def log_error(category, message):
    """Enhanced error logging with category and timestamp."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    error_msg = f"[{timestamp}] [{category}] {message}"
    print(error_msg)
    # Also write to a log file for debugging
    try:
        with open("piuu_error.log", "a", encoding="utf-8") as f:
            f.write(error_msg + "\n")
    except:
        pass  # If we can't write to log file, just continue

def draw_menu(sel_blink, hs, difficulty=1, mode='normal', show_settings=False, settings_sel=0, menu_sel=0, credits_page=0):
    b = Buf()
    y = 1
    if b.h >= 17 and b.w >= len(TITLE[0]) + 2:
        for i, row in enumerate(TITLE):
            _center(b, y + i, row, CYN)
        y += len(TITLE) + 1
    else:
        _center(b, y, "P I U   P I U", CYN)
        y += 2
    _center(b, y, "renn. spring. mach piu piu.", DIM)
    y += 2

    if b.h >= 16 and b.w >= 44:
        sx = max(2, (b.w - 40) // 2)
        b.put(sx, y, HERO_KAO["run"][0], GRN)
        b.put(sx + 9, y, "- - -", YEL)
        b.put(sx + 16, y, "piu piu", MAG)
        b.put(sx + 27, y, "~o>", RED)
        b.put(sx + 34, y, " _ ", GRN)
        b.put(sx + 34, y + 1, "|_|", GRN)
        y += 2
    b.put(0, min(y, b.h - 6), "^" * b.w, DIM)

    if show_settings:
        # Settings Menu
        settings_options = [
            "[ Difficulty: Easy ]" if difficulty == 1 else "[ Difficulty: Medium ]" if difficulty == 2 else "[ Difficulty: Hard ]",
            "[ Mode: Normal ]" if mode == 'normal' else "[ Mode: Endless ]",
            "[ Controls: WASD ]",
            "[ Graphics: Full ]",
            "[ Sound: On ]",
            "[ Press Enter to Start ]"
        ]

        for i, option in enumerate(settings_options):
            color = GRN if settings_sel == i and option.startswith("[ ") else YEL if settings_sel == i else DIM
            _center(b, by + 2 + i, option, color)
    elif menu_sel == 0:
        # Main Menu
        _center(b, by + 2, "[ START GAME ]" if sel_blink else "[           ]", GRN)
        _center(b, by + 3, "[ SETTINGS ]" if menu_sel == 1 else "[             ]", CYN)
        _center(b, by + 4, "[ MODS ]" if menu_sel == 2 else "[          ]", MAG)
        _center(b, by + 5, "[ CREDITS ]" if menu_sel == 3 else "[            ]", YEL)
        _center(b, by + 6, "[ EXIT ]" if menu_sel == 4 else "[          ]", RED)
    elif menu_sel == 1:
        # Settings Menu
        _center(b, by + 2, "[ Difficulty ]" if settings_sel == 0 else "[               ]", YEL)
        _center(b, by + 3, "[ Game Mode ]" if settings_sel == 1 else "[                 ]", CYN)
        _center(b, by + 4, "[ Controls ]" if settings_sel == 2 else "[               ]", MAG)
        _center(b, by + 5, "[ Graphics ]" if settings_sel == 3 else "[               ]", GRN)
        _center(b, by + 6, "[ Sound ]" if settings_sel == 4 else "[                ]", RED)
    elif menu_sel == 2:
        # Mods Menu - Show some featured mods or info
        mod_info = [
            "[ 1. Speed Mod: x1.5 (Hard) ]",
            "[ 2. Double Jump: Enabled ]",
            "[ 3. Infinite Ammo: On ]",
            "[ 4. Fast Reload: 15s ]",
            "[ 5. Big Enemies: Off ]",
            "[ Press SPACE for more ]"
        ]

        for i, line in enumerate(mod_info):
            color = YEL if i == credits_page else DIM
            _center(b, by + 2 + i, line, color)
    elif menu_sel == 3:
        # Credits Menu
        credit_lines = [
            "[ PIU PIU - ASCII Endlosrunner ]",
            "[ Created by: Philipp Paulik ]",
            "[ Version: 1.0.0 ]",
            "",
            "[ Controls: WASD + Space + S + Q ]",
            "[ Easy/Medium/Hard difficulties ]",
            "[ Endless and Normal modes ]",
            "",
            "[ Special thanks to all testers! ]"
        ]

        for i, line in enumerate(credit_lines):
            color = CYN if i == credits_page else DIM
            _center(b, by + 2 + i, line, color)
    elif menu_sel == 4:
        # Exit Confirmation
        _center(b, by + 2, "[ YES ]" if credits_page == 0 else "[ NO ]", RED)

    out(HOME + b.render())


GAMEOVER = [
    "  ____   _    __  __ ___    _____   _____ ____  ",
    " / ___| / \\  |  \\/  | __|  / _ \\ \\ / / __|  _ \\ ",
    "| |  _ / _ \\ | |\\/| | _|  | (_) \\ V /| _|| |_) |",
    "|_|_|_/_/ \\_\\|_|  |_|___|  \\___/ \\_/ |___|_| \\_\\",
]


def draw_gameover(score, kills, dist, rank, scores, improved=False):
    b = Buf()
    y = 1
    if b.h >= 17 and b.w >= len(GAMEOVER[0]) + 2:
        for i, row in enumerate(GAMEOVER):
            _center(b, y + i, row, RED)
        y += len(GAMEOVER) + 1
    else:
        _center(b, y, "*** GAME OVER ***", RED)
        y += 2

    _center(b, y, HERO_KAO["dead"][0], RED)
    _center(b, y + 1, "autsch*", YEL)
    _center(b, y + 2, "score %d   kills %d   strecke %dm" % (score, kills, dist), WHT)
    if improved and rank == 1:
        _center(b, y + 3, "*** NEUER REKORD! ***", MAG)
    elif improved:
        _center(b, y + 3, "neue bestleistung! platz %d" % rank, GRN)
    else:
        pb = 0
        for e in scores:
            if rank and scores.index(e) + 1 == rank:
                pb = e.get("score", 0)
        _center(b, y + 3, "bestleistung bleibt: %d" % pb, DIM)

    y += 5
    room = (b.h - 2) - y
    if room >= 2:
        _center(b, y, "-- hall of piu --", CYN)
        for i, e in enumerate(scores[:max(0, min(5, room - 1))]):
            runs = int(e.get("runs", 1))
            row = "%d. %-14s %6d" % (i + 1, e.get("name", "?"), e.get("score", 0))
            if b.w >= 54:
                row += "  (%d %s)" % (runs, "lauf" if runs == 1 else "laeufe")
            _center(b, y + 1 + i, row, GRN if (i + 1) == rank else DIM)

    _center(b, b.h - 1, "LEERTASTE = nochmal    Q = ende", YEL)
    out(HOME + b.render())


def draw_too_small():
    cols, rows = term_size()
    out(CLEAR + HOME)
    out(YEL + "  Terminal zu klein\n\n" + R)
    out("  jetzt:    %d x %d\n" % (cols, rows))
    out("  noetig: >=%d x %d\n\n" % (MIN_W + 1, MIN_H + 1))
    out(DIM + "  Fenster groesser ziehen - es geht automatisch weiter.\n" + R)


def out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


# ---------------- Spiel ----------------
class Game:
    def __init__(self, snd, wide_ok, speed_mult=1.0, difficulty=1, mode='normal'):
        self.snd = snd
        self.wide = wide_ok
        self.sm = speed_mult
        self.difficulty = difficulty
        self.mode = mode
        self.y = 0.0          # Hoehe ueber Boden
        self.vy = 0.0
        self.jumps = 0
        self.ducking = 0
        self.shoot_t = 0
        self.ammo = MAG_SIZE
        self.reload_t = 0.0      # >0 = laedt gerade nach
        self.mag_t = MAG_WINDOW  # Restzeit des 30s-Fensters
        self.click_t = 0         # "klick" Anzeige bei leerem Magazin
        self.obs = []
        self.bul = []
        self.bg = []
        self.clouds = []
        self.parts = []
        self.dist = 0.0
        self.score = 0
        self.kills = 0
        self.speed = 1.0
        self.t = 0
        self.spawn = 22
        self.dead = False
        self.msg = ""
        self.msg_t = 0
        _span = list(range(2, max(3, GROUND - 5)))
        _cnt = max(3, min(7, (W * GROUND) // 300))
        rows = random.sample(_span, min(_cnt, len(_span)))
        for ry in rows:
            self.bg.append([random.uniform(0, W), ry, random.choice(PHRASES)])
        self.clouds.append([random.uniform(0, W), 1])

        # Difficulty-based settings
        self.base_speed = speed_mult
        self.obstacle_spawn_rate = max(5.0, 15.0 - (difficulty * 3.0))  # 15s -> 5s for Easy -> Hard
        self.word_obstacle_chance = min(0.4, 0.16 + (difficulty - 1) * 0.1)  # Easy: 16%, Medium: 26%, Hard: 36%
        self.hard_collision = (difficulty == 3)  # Hard: birds cause damage even when ducking

        # Mode-based settings
        if mode == 'endless':
            self.endless_mode = True
            self.dist_target = None  # No distance target for endless mode
        else:
            self.endless_mode = False
            self.dist_target = 400  # Normal mode target distance

    # ---- Aktionen ----
    def jump(self):
        if self.jumps < 2:
            self.vy = 1.55 if self.jumps == 0 else 1.35
            self.jumps += 1
            self.ducking = 0
            self.snd.jump()

    def duck(self):
        if self.y <= 0.01:
            self.ducking = 8
        else:
            self.vy -= 0.9   # schnell runter

    def shoot(self):
        if self.reload_t > 0 or self.ammo <= 0:
            if self.click_t <= 0:
                self.snd.click()
            self.click_t = 10
            return
        by = GROUND - 1 - int(self.y)
        if self.ducking:
            by = GROUND - 1
        self.bul.append([PX + HERO_W - 1.0, by])
        self.shoot_t = 4
        self.ammo -= 1
        self.snd.piu()
        if self.ammo == 0:
            self.reload_t = RELOAD_TIME
            self.snd.empty()

    def on_resize(self):
        """Nach Groessenaenderung alles wieder ins Bild holen."""
        self.bg = [p for p in self.bg if 2 <= p[1] < max(3, GROUND - 4)]
        for p in self.bg:
            p[0] = min(p[0], float(W))
        for c in self.clouds:
            c[0] = min(c[0], float(W))
        self.obs = [o for o in self.obs if o["x"] < W + 4]
        self.bul = [bl for bl in self.bul if bl[0] < W]
        for bl in self.bul:
            bl[1] = max(0, min(GROUND - 1, bl[1]))
        self.parts = []
        if GROUND - 1 - int(round(self.y)) < 1:
            self.y = 0.0
            self.vy = 0.0

    # ---- Physik / Logik ----
    def step(self):
        self.t += 1
        # Grundtempo waechst mit der Strecke, dazu eine sanfte Welle
        base = 0.95 + 1.75 * (1.0 - math.exp(-self.dist / 1400.0))
        wave = 0.12 * math.sin(self.t / 47.0) + 0.07 * math.sin(self.t / 13.0)
        self.speed = max(0.7, (base + wave)) * self.sm
        self.dist += self.speed
        self.score = int(self.dist / 3) + self.kills * 25

        # Spieler
        self.vy -= 0.16
        self.y += self.vy
        if self.y <= 0:
            self.y = 0.0
            self.vy = 0.0
            self.jumps = 0
        if self.ducking:
            self.ducking -= 1
        if self.shoot_t > 0:
            self.shoot_t -= 1
        if self.click_t > 0:
            self.click_t -= 1

        # Munition: Reload-Countdown bzw. 30s-Fenster
        dt = 1.0 / FPS
        if self.reload_t > 0:
            self.reload_t -= dt
            if self.reload_t <= 0:
                self.reload_t = 0.0
                self.ammo = MAG_SIZE
                self.mag_t = MAG_WINDOW
                self.snd.reload_done()
        else:
            self.mag_t -= dt
            if self.mag_t <= 0:
                if self.ammo < MAG_SIZE:
                    self.ammo = MAG_SIZE
                    self.snd.reload_done()
                self.mag_t = MAG_WINDOW

        # Hintergrund-Saetze (Parallax)
        for p in self.bg:
            p[0] -= self.speed * 0.35
        self.bg = [p for p in self.bg if p[0] + len(p[2]) > 0]
        max_bg = max(3, min(9, (W * GROUND) // 260))
        if random.random() < 0.035 * (W / 78.0) and len(self.bg) < max_bg:
            taken = {p[1] for p in self.bg if p[0] + len(p[2]) > W - 4}
            free = [y for y in range(2, max(3, GROUND - 5)) if y not in taken]
            if free:
                self.bg.append([float(W), random.choice(free),
                                random.choice(PHRASES)])
        for c in self.clouds:
            c[0] -= self.speed * 0.18
        self.clouds = [c for c in self.clouds if c[0] + 11 > 0]
        max_cl = max(2, min(5, W // 42))
        if random.random() < 0.012 * (W / 78.0) and len(self.clouds) < max_cl:
            self.clouds.append([float(W), random.choice([0, 1])])

        # Hindernisse
        for o in self.obs:
            o["x"] -= self.speed
            if o["kind"] == "bird":
                o["x"] -= self.speed * 0.25
                o["f"] = (o.get("f", 0) + 1) % 8
                o["h"] = len(o["art2"] if (o["art2"] and o["f"] >= 4) else o["art"])
        self.obs = [o for o in self.obs if o["x"] + o["w"] > 0]

        self.spawn -= self.speed
        if self.spawn <= 0:
            lvl = int(self.dist / 400)
            m = make_obstacle(lvl)
            art = m["art"]
            self.obs.append({"x": float(W + 2), "art": art, "art2": m["art2"],
                             "kind": m["kind"], "off": m["off"],
                             "w": max(len(r) for r in art),
                             "h": len(art), "f": random.randint(0, 7)})
            # Abstand: skaliert mit Tempo (Reaktionszeit bleibt fair),
            # dazu Rhythmus-Variation und gelegentliche Doppel-/Ruhepausen
            react = 15.0 + 9.0 * self.speed
            jitter = random.uniform(0.75, 1.65)
            gap = react * jitter
            r = random.random()
            if r < 0.14 and lvl >= 1:
                gap = react * 0.55            # Doppelschlag
            elif r > 0.93:
                gap = react * 2.4             # Verschnaufpause
            self.spawn = max(13.0, gap)

        # Schuesse
        for bl in self.bul:
            bl[0] += 3.4
        self.bul = [bl for bl in self.bul if bl[0] < W]
        self._bullet_hits()

        # Partikel
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.parts = [p for p in self.parts if p[4] > 0]

        if self.msg_t > 0:
            self.msg_t -= 1

        self._player_hits()

    def _rows_of(self, o):
        bot = GROUND - 1 - o["off"]
        return bot - o["h"] + 1, bot

    def _bullet_hits(self):
        for bl in list(self.bul):
            for o in list(self.obs):
                top, bot = self._rows_of(o)
                if o["x"] - 1 <= bl[0] <= o["x"] + o["w"] and top <= bl[1] <= bot:
                    self.obs.remove(o)
                    if bl in self.bul:
                        self.bul.remove(bl)
                    self.kills += 1
                    self.snd.kill()
                    self.msg = random.choice(["piu!", "autsch*", "weg damit", "piu piu"])
                    self.msg_t = 12
                    for _ in range(7):
                        self.parts.append([o["x"] + o["w"] / 2, (top + bot) / 2,
                                           random.uniform(-.8, .8),
                                           random.uniform(-.5, .5),
                                           random.randint(3, 7),
                                           random.choice("*.,'`^")])
                    break

    def _player_hits(self):
        prow = GROUND - 1 - int(round(self.y))
        px0, px1 = PX + 1, PX + HERO_W - 3
        for o in self.obs:
            top, bot = self._rows_of(o)
            ox0, ox1 = o["x"], o["x"] + o["w"] - 1
            if ox1 < px0 - 0.2 or ox0 > px1 + 0.2:
                continue
            if top <= prow <= bot:
                self.dead = True
                return

    # ---- Held ----
    def hero_pose(self):
        k = HERO_KAO if self.wide else HERO_ASCII
        if self.dead:
            return k["dead"][0]
        if self.ducking:
            return k["duck"][0]
        if self.shoot_t > 0:
            return k["shoot"][0]
        if self.y > 0.3:
            return k["jump"][0] if self.vy > 0 else k["fall"][0]
        run = k["run"]
        return run[(self.t // 3) % len(run)]

    def hero_col(self):
        if self.dead:
            return RED
        if self.shoot_t > 0:
            return YEL
        if self.ducking:
            return CYN
        return GRN

    # ---- Zeichnen ----
    def draw(self, hs):
        b = Buf()
        for c in self.clouds:
            for i, row in enumerate(CLOUDS):
                b.put(int(c[0]), c[1] + i, row, DIM)
        for p in self.bg:
            b.put(int(p[0]), p[1], p[2], DIM)
        for p in self.parts:
            b.put(int(p[0]), int(p[1]), p[5], YEL)

        for o in self.obs:
            col = MAG if o["kind"] == "word" else (RED if o["kind"] == "bird" else GRN)
            art = o["art"]
            if o["art2"] and o["f"] >= 4:
                art = o["art2"]
            b.art(int(o["x"]), GROUND - 1 - o["off"], art, col)

        for bl in self.bul:
            b.put(int(bl[0]), bl[1], "-=", YEL)

        prow = GROUND - 1 - int(round(self.y))
        b.put(PX, prow, self.hero_pose(), self.hero_col())
        if self.y > 0.3 and not self.ducking:
            b.put(PX + 2, prow + 1, "^", DIM)

        # Boden
        pat = "^~-_" 
        gline = "".join(pat[(x + int(self.dist)) % len(pat)] for x in range(b.w))
        b.put(0, GROUND, "_" * b.w, DIM)
        b.put(0, GROUND + 1, gline, DIM)

        if b.w >= 74:
            hud = " score %5d  best %5d  kills %2d  %4dm  x%.1f" % (
                self.score, max(hs, self.score), self.kills,
                int(self.dist / 4), self.speed)
        elif b.w >= 58:
            hud = " %5d  best %5d  k%2d  %4dm" % (
                self.score, max(hs, self.score), self.kills, int(self.dist / 4))
        else:
            hud = " %d  k%d  %dm" % (self.score, self.kills, int(self.dist / 4))
        b.put(1, b.h - 1, hud, WHT)

        # Munition: rechtsbuendig, kuerzt sich bei schmalem Fenster
        if self.reload_t > 0:
            filled = int(round((1.0 - self.reload_t / RELOAD_TIME) * 10))
            if b.w >= 74:
                am = "RELOAD [%s] %.1fs" % ("#" * filled + "." * (10 - filled),
                                            self.reload_t)
            else:
                am = "RELOAD %.1fs" % self.reload_t
            acol = RED
        else:
            acol = GRN if self.ammo > 3 else YEL
            bar = "|" * self.ammo + "." * (MAG_SIZE - self.ammo)
            if b.w >= 74:
                am = "piu [%s] %2d  %2ds" % (bar, self.ammo, int(self.mag_t))
            elif b.w >= 58:
                am = "piu [%s]" % bar
            else:
                am = "piu %d" % self.ammo
        b.put(b.w - len(am) - 1, b.h - 1, am, acol)

        if self.click_t > 0:
            b.put(PX + HERO_W, prow, " *klick*", RED)
        if self.msg_t > 0:
            b.put(PX + 4, prow - 1, self.msg, YEL)
        out(HOME + b.render())


# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser(description="PIU PIU - ASCII Endlosrunner")
    ap.add_argument("--silent", action="store_true", help="ohne Ton")
    ap.add_argument("--ascii", action="store_true", help="kein Emoji, nur ASCII")
    ap.add_argument("--speed", type=float, default=1.0, help="Tempofaktor")
    ap.add_argument("--name", default=None)
    ap.add_argument("--scores", action="store_true")
    ap.add_argument("--demo", type=int, default=0, help="Autoplay N Frames (Test)")
    ap.add_argument("--size", default=None,
                    help="feste Spielfeldgroesse statt automatisch, z.B. 100x30")
    a = ap.parse_args()

    if a.scores:
        sc = load_scores()
        if not sc:
            print("noch keine eintraege. spiel erst mal.")
        for i, e in enumerate(sc, 1):
            runs = int(e.get("runs", 1))
            print("%2d. %-14s %6d  %3d kills  %4d %s  %s" % (
                i, e.get("name", "?"), e.get("score", 0), e.get("kills", 0),
                runs, "lauf " if runs == 1 else "laeufe", e.get("date", "")))
        return

    if IS_WIN:
        try:
            os.system("title PIU PIU")
        except Exception as e:
            log_error("TITLE_SETUP", f"window title setup failed: {str(e)}")

    if a.size:
        try:
            cw, ch = a.size.lower().split("x")
            set_size(int(cw), int(ch))
        except Exception as e:
            log_error("SIZE_SETUP", f"size setup failed: {str(e)}")
            print("--size braucht die Form BREITExHOEHE, z.B. 100x30")
            return
    else:
        try:
            fit()
        except Exception as e:
            log_error("FIT_SETUP", f"terminal fit failed: {str(e)}")

    try:
        snd = Snd(a.silent)
    except Exception as e:
        log_error("SOUND_INIT", f"sound system initialization failed: {str(e)}")
        snd = None

    try:
        keys = Keys()
    except Exception as e:
        log_error("KEY_INIT", f"keyboard initialization failed: {str(e)}")
        keys = None

    wide = not a.ascii
    name = a.name or os.environ.get("USERNAME") or os.environ.get("USER") or "Piu"
    demo = a.demo > 0

    try:
        out(CLEAR + HIDE)
    except Exception as e:
        log_error("OUTPUT_SETUP", f"output initialization failed: {str(e)}")
        # Continue anyway

    try:
        while True:
            # ---- Startscreen ----
            if not demo:
                if not keys.ok:
                    out(HOME + CLEAR)
                    print("Kein interaktives Terminal. Starte mit --demo 200 zum Testen.")
                    return
                keys.flush()
                blink = 0
                fit()
                out(CLEAR)
                while True:
                    if fit():
                        out(CLEAR)
                    if TOO_SMALL:
                        draw_too_small()
                        if keys.get() == "quit":
                            return
                        time.sleep(0.25)
                        continue

                    # Menu state
                    menu_sel = 0  # 0: Main, 1: Settings, 2: Mods, 3: Credits, 4: Exit
                    settings_sel = 0
                    credits_page = 0
                    difficulty = 1  # Default: Easy
                    mode = 'normal'  # Default: Normal

                    try:
                        draw_menu((blink // 5) % 2 == 0, best(), difficulty, mode, False, 0, menu_sel, credits_page)
                    except Exception as e:
                        log_error("MENU_RENDER", f"draw_menu failed: {type(e).__name__}: {str(e)}")
                        # Fallback to simple menu
                        out(CLEAR + HOME)
                        # Use the same buffer logic as draw_menu but without calling it
                        b_fallback = Buf()
                        if b_fallback.h >= 17 and b_fallback.w >= len(TITLE[0]) + 2:
                            for i, row in enumerate(TITLE):
                                _center(b_fallback, i + 1, row, CYN)
                            y = len(TITLE) + 2
                        else:
                            _center(b_fallback, 1, "P I U P I U", CYN)
                            y = 3
                        _center(b_fallback, y, "MENU ERROR - RESTARTING", RED)
                        _center(b_fallback, y + 2, "Press any key...", DIM)
                        out(HOME + b_fallback.render())
                        keys.wait_any()
                        continue

                    try:
                        k = keys.get()
                    except Exception as e:
                        log_error("KEY_READ", f"keyboard read failed: {type(e).__name__}: {str(e)}")
                        k = None

                    # Menu navigation
                    if menu_sel == 0:  # Main Menu
                        if k == "jump":
                            menu_sel = (menu_sel + 1) % 5  # Navigate between main menu items
                        elif k == "duck":
                            menu_sel = (menu_sel + 4) % 5  # Navigate backwards
                        elif k == "shoot":
                            if menu_sel == 0:  # Start Game
                                break
                            elif menu_sel == 1:  # Settings
                                settings_sel = 0
                                menu_sel = 1  # Enter settings
                            elif menu_sel == 2:  # Mods
                                credits_page = 0
                                menu_sel = 2  # Enter mods
                            elif menu_sel == 3:  # Credits
                                credits_page = 0
                                menu_sel = 3  # Enter credits
                            elif menu_sel == 4:  # Exit
                                menu_sel = 5  # Enter exit confirmation
                    elif menu_sel == 1:  # Settings
                        if k == "jump":
                            settings_sel = max(0, settings_sel - 1)
                        elif k == "duck":
                            settings_sel = min(5, settings_sel + 1)
                        elif k == "shoot":
                            if settings_sel == 0:  # Difficulty
                                difficulty = (difficulty % 3) + 1
                            elif settings_sel == 1:  # Game Mode
                                mode = 'endless' if mode == 'normal' else 'normal'
                            elif settings_sel == 2:  # Controls
                                pass
                            elif settings_sel == 3:  # Graphics
                                pass
                            elif settings_sel == 4:  # Sound
                                pass
                            elif settings_sel == 5:  # Back to main menu
                                menu_sel = 0
                    elif menu_sel == 2:  # Mods
                        if k == "jump":
                            credits_page = max(0, credits_page - 1)
                        elif k == "duck":
                            credits_page = min(9, credits_page + 1)
                        elif k == "shoot":
                            if credits_page == 9:
                                menu_sel = 0  # Back to main menu
                    elif menu_sel == 3:  # Credits
                        if k == "jump":
                            credits_page = max(0, credits_page - 1)
                        elif k == "duck":
                            credits_page = min(11, credits_page + 1)
                        elif k == "shoot":
                            if credits_page == 11:
                                menu_sel = 0  # Back to main menu
                    elif menu_sel == 4:  # Exit Confirmation
                        if k == "jump":
                            menu_sel = 4  # Yes (default)
                        elif k == "duck":
                            menu_sel = 0  # No
                        elif k == "shoot":
                            if menu_sel == 4:  # Yes
                                return
                            else:
                                menu_sel = 0
                    blink += 1
                    time.sleep(0.07)
                snd.start()
                out(CLEAR)

            # ---- Runde ----
            # Apply game settings (difficulty affects speed, mode can be used for future enhancements)
            speed_mult = a.speed
            if difficulty == 2:
                speed_mult *= 0.8    # Medium: 20% slower
            elif difficulty == 3:
                speed_mult *= 0.6    # Hard: 40% slower
            g = Game(snd, wide, speed_mult, difficulty, mode)
            frames = 0
            while not g.dead:
                if demo:
                    # simple KI: springt vor Hindernissen, ballert Voegel
                    for o in g.obs:
                        d = o["x"] - PX
                        if o["kind"] == "bird" and 8 < d < 26:
                            if frames % 4 == 0:
                                g.shoot()
                        elif 6 < d < 13 and g.y < 0.2:
                            g.jump()
                    frames += 1
                    if frames >= a.demo:
                        break
                else:
                    while True:
                        k = keys.get()
                        if k is None:
                            break
                        if k == "jump":
                            g.jump()
                        elif k == "duck":
                            g.duck()
                        elif k == "shoot":
                            g.shoot()
                        elif k == "pause":
                            b = Buf()
                            b.put(W // 2 - 4, H // 2, "|| PAUSE", YEL)
                            out(HOME + b.render())
                            keys.wait_any()
                        elif k == "quit":
                            return
                if not demo:
                    if fit():
                        g.on_resize()
                        out(CLEAR)
                    if TOO_SMALL:
                        draw_too_small()
                        time.sleep(0.25)
                        continue
                g.step()
                g.draw(best())
                time.sleep(0.055)

            if demo:
                out("\n")
                print("demo ok: score=%d kills=%d dead=%s" % (g.score, g.kills, g.dead))
                return

            # ---- Game Over ----
            snd.hit()
            scores, rank, improved = save_score(name, g.score, g.kills)
            out(CLEAR)
            draw_gameover(g.score, g.kills, int(g.dist / 4), rank, scores, improved)
            keys.flush()
            while True:
                if fit():
                    out(CLEAR)
                    draw_gameover(g.score, g.kills, int(g.dist / 4), rank, scores, improved)
                k = keys.get()
                if k == "quit":
                    return
                if k in ("jump", "shoot"):
                    break
                time.sleep(0.05)
            out(CLEAR)
    except KeyboardInterrupt:
        pass
    finally:
        keys.restore()
        out(SHOW + R + "\n")
        print(DIM + "  piu piu. und du nie wieder aslok haare." + R)


if __name__ == "__main__":
    main()
