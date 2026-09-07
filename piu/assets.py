"""ASCII-Grafiken und Hinderniskatalog. Zufall wird explizit uebergeben."""

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


def make_obstacle(level, rng):
    """Liefert dict mit art/art2/kind/off - gewichtet nach Level."""
    # Woerter kommen extra oft
    if rng.random() < 0.16:
        hi = level >= 2 and rng.random() < 0.5
        w = rng.choice(WORDS_HIGH if hi else WORDS_LOW)
        return {"art": [w], "art2": None, "kind": "word",
                "off": rng.choice([3, 4]) if hi else 0}

    opts = [c for c in CATALOG if c[4] <= level]
    weights = [c[5] for c in opts]
    a, b, kind, offs, _, _ = rng.choices(opts, weights=weights)[0]
    return {"art": list(a), "art2": (list(b) if b else None),
            "kind": kind, "off": rng.choice(offs)}
