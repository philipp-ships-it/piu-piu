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

W = 78          # Spielfeldbreite
H = 18          # Spielfeldhoehe
GROUND = H - 4  # Zeile der Bodenlinie
PX = 6          # Spieler-x

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
        self.g = [[" "] * W for _ in range(H)]
        self.c = [[None] * W for _ in range(H)]

    def put(self, x, y, s, col=None, wide=False):
        if y < 0 or y >= H:
            return
        for i, chpos in enumerate(s):
            xx = x + i
            if 0 <= xx < W:
                self.g[y][xx] = chpos
                self.c[y][xx] = col
        if wide and 0 <= x + 1 < W:
            self.g[y][x + 1] = ""
            self.c[y][x + 1] = col

    def art(self, x, y_bottom, art, col=None):
        for i, row in enumerate(reversed(art)):
            self.put(x, y_bottom - i, row, col)

    def render(self):
        lines = []
        for y in range(H):
            parts = []
            cur = None
            for x in range(W):
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
def load_scores():
    try:
        with open(SCORE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_score(name, score, kills):
    s = load_scores()
    e = {"name": (name or "Piu")[:14], "score": int(score), "kills": kills,
         "date": datetime.now().strftime("%d.%m.%y %H:%M")}
    s.append(e)
    s.sort(key=lambda x: x.get("score", 0), reverse=True)
    s = s[:10]
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return s, (s.index(e) + 1 if e in s else None)


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


def draw_start(sel_blink, hs):
    b = Buf()
    for i, row in enumerate(TITLE):
        b.put((W - len(row)) // 2, 1 + i, row, CYN)
    b.put((W - 28) // 2, 7, "renn. spring. mach piu piu.", DIM)

    b.put(6, 9, HERO_KAO["run"][0], GRN)
    b.put(14, 9, "- - -", YEL)
    b.put(20, 9, "piu piu", MAG)
    b.put(32, 9, "~o>", RED)
    b.put(40, 9, " _  ", GRN)
    b.put(40, 10, "|_| ", GRN)

    b.put(0, 11, "^" * W, DIM)

    btn = "[ START ]" if sel_blink else "[        ]"
    b.put((W - len(btn)) // 2, 13, btn, GRN)
    b.put((W - 46) // 2, 15, "LEER=springen  ENTER=piu piu  S=ducken  Q=ende", DIM)
    b.put((W - 40) // 2, 16, "10 schuss / 30s   danach 5s nachladen", DIM)
    if hs:
        b.put((W - 20) // 2, 17, "bestleistung: %d" % hs, YEL)
    out(HOME + b.render())


GAMEOVER = [
    "  ____   _    __  __ ___    _____   _____ ____  ",
    " / ___| / \\  |  \\/  | __|  / _ \\ \\ / / __|  _ \\ ",
    "| |  _ / _ \\ | |\\/| | _|  | (_) \\ V /| _|| |_) |",
    "|_|_|_/_/ \\_\\|_|  |_|___|  \\___/ \\_/ |___|_| \\_\\",
]


def draw_gameover(score, kills, dist, rank, scores):
    b = Buf()
    for i, row in enumerate(GAMEOVER):
        b.put((W - len(row)) // 2, 1 + i, row, RED)
    kao = HERO_KAO["dead"][0]
    b.put((W - len(kao)) // 2, 6, kao, RED)
    b.put((W - 7) // 2, 7, "autsch*", YEL)
    msg = "score %d   kills %d   strecke %dm" % (score, kills, dist)
    b.put((W - len(msg)) // 2, 8, msg, WHT)
    if rank == 1:
        b.put((W - 21) // 2, 9, "*** NEUER REKORD! ***", MAG)
    elif rank:
        b.put((W - 18) // 2, 9, "platz %d der liste" % rank, GRN)

    b.put((W - 17) // 2, 11, "-- hall of piu --", CYN)
    for i, e in enumerate(scores[:4]):
        row = "%d. %-14s %6d" % (i + 1, e.get("name", "?"), e.get("score", 0))
        b.put((W - len(row)) // 2, 12 + i, row, GRN if (i + 1) == rank else DIM)
    b.put((W - 34) // 2, 16, "LEERTASTE = nochmal    Q = ende", YEL)
    out(HOME + b.render())


def out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


# ---------------- Spiel ----------------
class Game:
    def __init__(self, snd, wide_ok, speed_mult=1.0):
        self.snd = snd
        self.wide = wide_ok
        self.sm = speed_mult
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
        rows = random.sample(range(2, GROUND - 5), 3)
        for ry in rows:
            self.bg.append([random.uniform(0, W), ry, random.choice(PHRASES)])
        self.clouds.append([random.uniform(0, W), 1])

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
        if random.random() < 0.035 and len(self.bg) < 5:
            taken = {p[1] for p in self.bg if p[0] + len(p[2]) > W - 4}
            free = [y for y in range(2, GROUND - 5) if y not in taken]
            if free:
                self.bg.append([float(W), random.choice(free),
                                random.choice(PHRASES)])
        for c in self.clouds:
            c[0] -= self.speed * 0.18
        self.clouds = [c for c in self.clouds if c[0] + 11 > 0]
        if random.random() < 0.012 and len(self.clouds) < 2:
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
        gline = "".join(pat[(x + int(self.dist)) % len(pat)] for x in range(W))
        b.put(0, GROUND, "_" * W, DIM)
        b.put(0, GROUND + 1, gline, DIM)

        hud = " score %5d  best %5d  kills %2d  %4dm  x%.1f" % (
            self.score, max(hs, self.score), self.kills,
            int(self.dist / 4), self.speed)
        b.put(1, H - 1, hud, WHT)

        # Munitionsanzeige
        ax = W - 26
        if self.reload_t > 0:
            frac = 1.0 - (self.reload_t / RELOAD_TIME)
            filled = int(round(frac * 10))
            bar = "#" * filled + "." * (10 - filled)
            b.put(ax, H - 1, "RELOAD [%s] %.1fs" % (bar, self.reload_t), RED)
        else:
            col = GRN if self.ammo > 3 else YEL
            bar = "|" * self.ammo + "." * (MAG_SIZE - self.ammo)
            b.put(ax, H - 1, "piu [%s] %2d  %2ds" % (bar, self.ammo, int(self.mag_t)), col)

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
    a = ap.parse_args()

    if a.scores:
        for i, e in enumerate(load_scores(), 1):
            print("%2d. %-14s %6d  %s" % (i, e.get("name", "?"), e.get("score", 0), e.get("date", "")))
        return

    if IS_WIN:
        try:
            os.system("title PIU PIU")
        except Exception:
            pass

    snd = Snd(a.silent)
    keys = Keys()
    wide = not a.ascii
    name = a.name or os.environ.get("USERNAME") or os.environ.get("USER") or "Piu"
    demo = a.demo > 0

    out(CLEAR + HIDE)
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
                while True:
                    draw_start((blink // 5) % 2 == 0, best())
                    k = keys.get()
                    if k == "quit":
                        return
                    if k in ("jump", "shoot"):
                        break
                    blink += 1
                    time.sleep(0.07)
                snd.start()
                out(CLEAR)

            # ---- Runde ----
            g = Game(snd, wide, a.speed)
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
                g.step()
                g.draw(best())
                time.sleep(0.055)

            if demo:
                out("\n")
                print("demo ok: score=%d kills=%d dead=%s" % (g.score, g.kills, g.dead))
                return

            # ---- Game Over ----
            snd.hit()
            scores, rank = save_score(name, g.score, g.kills)
            out(CLEAR)
            draw_gameover(g.score, g.kills, int(g.dist / 4), rank, scores)
            keys.flush()
            while True:
                k = keys.wait_any()
                if k == "quit":
                    return
                if k in ("jump", "shoot"):
                    break
            out(CLEAR)
    except KeyboardInterrupt:
        pass
    finally:
        keys.restore()
        out(SHOW + R + "\n")
        print(DIM + "  piu piu. und du nie wieder aslok haare." + R)


if __name__ == "__main__":
    main()
