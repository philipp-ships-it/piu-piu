"""Reine Darstellung: Spielzustand hinein, ANSI-Text hinaus."""
from .assets import HERO_W, HERO_ASCII, HERO_KAO, CLOUDS
from .buffer import Buf
from .colors import CYN, DIM, GRN, MAG, RED, WHT, YEL
from .settings import SETTING_ROWS, CHEATS
import textwrap

ORANGE = "\033[38;5;208m"
LOGO = (
    " ____  ___ _   _   ____  ___ _   _ ",
    "|  _ \\|_ _| | | | |  _ \\|_ _| | | |",
    "| |_) || || | | | | |_) || || | | |",
    "|  __/ | || |_| | |  __/ | || |_| |",
    "|_|   |___|\\___/  |_|   |___|\\___/ ",
)


def center(buffer, y, text, color=DIM):
    buffer.put(max(0, (buffer.w - len(text)) // 2), y, text, color)


def frame(geometry, title="PIU PIU // TERMINAL ARCADE"):
    """ASCII-Rahmen bleibt auch bei reinem ASCII-Modus vollständig lesbar."""
    b = Buf(geometry)
    b.put(0, 0, "+" + "-" * (b.w - 2) + "+", DIM)
    b.put(0, b.h - 1, "+" + "-" * (b.w - 2) + "+", DIM)
    for y in range(1, b.h - 1):
        b.put(0, y, "|", DIM)
        b.put(b.w - 1, y, "|", DIM)
    center(b, 0, " " + title + " ", ORANGE)
    return b


def draw_start(menu, geometry, best=0, tick=0, ascii_only=False):
    """Animiertes Arcade-Plakat mit adaptivem Logo und fortsetzbarer Runde."""
    b = frame(geometry)
    if b.h >= 20:
        for y, line in enumerate(LOGO, 2):
            center(b, y, line, ORANGE)
        center(b, 8, "KLEINER HELD. GROSSES PIU.", WHT)
        hero = (HERO_ASCII if ascii_only else HERO_KAO)["run"][(tick // 3) % 2]
        center(b, 9, ".    " + hero + "  - piu!      |#|    .", GRN)
        menu_y = 11
        if b.h >= 28:
            center(b, 10, ".       *         .         .       *", DIM)
            hero = (HERO_ASCII if ascii_only else HERO_KAO)["run"][(tick // 3) % 2]
            center(b, 12, hero + "    - - piu!             |#|    /\\", GRN)
            center(b, 13, "___/__/__/__/__/__/__/__/__/__/__/__/___", DIM)
            menu_y = 16
    else:
        center(b, 2, "<<< P I U   P I U >>>", ORANGE)
        menu_y = 4
    for index, (_, label) in enumerate(menu.choices):
        chosen = index == menu.selected
        center(b, menu_y + index, ">>  " + label + "  <<" if chosen else label, ORANGE if chosen else WHT)
    summary_y = menu_y + len(menu.choices) + 1
    s = menu.settings
    center(b, summary_y, "%s | tempo x%.2f | %s" % (s.difficulty, s.tempo, s.density), CYN)
    center(b, summary_y + 1, "CHEATS AN - kein Highscore" if s.cheats_active else "BESTLEISTUNG  %06d" % best, YEL)
    if b.h >= 22:
        center(b, b.h - 4, "[ LEER: SPRUNG ]  [ ENTER: PIU ]  [ S: DUCKEN ]", DIM)
    center(b, b.h - 2, "W/S: Auswahl  ENTER: OK  Q: Ende", DIM)
    return b.render()


def draw_settings(settings, geometry, selected=0):
    b = frame(geometry, "S E T T I N G S")
    rows = []
    active = 0
    for index, (key, label) in enumerate(SETTING_ROWS):
        if index == 4:
            rows.append(("  -- CHEATS ---------------------", ORANGE))
        if index == selected:
            active = len(rows)
        value = ""
        if key in dict(CHEATS):
            value = "an" if getattr(settings, key) else "aus"
        elif key not in ("reset", "back"):
            value = "x%.2f" % settings.tempo if key == "tempo" else str(getattr(settings, key))
        if index == selected and value:
            value = "< %s >" % value
        rows.append(("%s %-21s %s" % (">" if index == selected else " ", label, value),
                     ORANGE if index == selected else WHT))
    room = b.h - 5
    offset = min(max(0, active - room + 1), max(0, len(rows) - room))
    for y, (line, color) in enumerate(rows[offset:offset + room], 1):
        b.put(max(2, (b.w - 38) // 2), y, line, color)
    if offset or offset + room < len(rows):
        b.put(b.w - 5, 0, "^ v", ORANGE)
    center(b, b.h - 4, "Cheat-Laeufe: kein Highscore.", YEL)
    hints = {"instant_reload": "Nachladen: 0.35s statt 5s.", "mega_jump": "Beide Spruenge: +45% Sprungkraft.",
             "invincible": "Hindernisse zerplatzen bei Beruehrung.",
             "infinite_ammo": "Unbegrenzt schiessen, ohne Nachladepause.",
             "double_points": "Doppelte Punkte fuer Strecke und Kills."}
    center(b, b.h - 3, hints.get(SETTING_ROWS[selected][0], "Schwierigkeit ist kein Cheat - auch leicht."), DIM)
    center(b, b.h - 2, "W/S: Wahl  A/D: Wert  ENTER: OK  ESC: Zurueck", DIM)
    return b.render()


def draw_message(geometry, title, message, footer="ENTER: Weiter  Q: Speichern und Ende"):
    """Mehrzeilige Hinweise, Fehler und Pause mit fester Bedienzeile."""
    b = frame(geometry, title)
    lines = []
    for paragraph in message.split("\n"):
        lines.extend(textwrap.wrap(paragraph, b.w - 6) or [""])
    for y, line in enumerate(lines[:b.h - 5], 2):
        center(b, y, line, WHT)
    center(b, b.h - 2, footer, ORANGE)
    return b.render()


def draw_confirm(menu, geometry):
    b = frame(geometry, "NEUE RUNDE?")
    center(b, 3, "Gespeicherten Rundenstand ersetzen?", WHT)
    for i, label in enumerate(("ZURUECK", "JA, NEUE RUNDE")):
        center(b, 6 + i, "> " + label + " <" if i == menu.selected else label,
               ORANGE if i == menu.selected else DIM)
    center(b, b.h - 2, "W/S: Auswahl  ENTER: OK  ESC: Zurueck", DIM)
    return b.render()


def draw_gameover(game, scores, rank=None, improved=False, saved=True, ascii_only=False):
    b = frame(game.geometry, "G A M E   O V E R")
    center(b, 2, (HERO_ASCII if ascii_only else HERO_KAO)["dead"][0] + "   autsch*", ORANGE)
    center(b, 4, "SCORE %d   KILLS %d   STRECKE %dm" % (game.score, game.kills, int(game.dist / 4)), WHT)
    if not saved:
        message = "NICHT GESPEICHERT - Details im Fehlerhinweis"
    elif game.cheated:
        message = "CHEAT-LAUF: zaehlt nicht fuer den Highscore"
    elif improved:
        message = "NEUE BESTLEISTUNG!" + (" PLATZ %d" % rank if rank else "")
    else:
        message = "Runde gespeichert. Dein Rekord bleibt."
    center(b, 6, message, YEL)
    center(b, 8, "-- HALL OF PIU --", CYN)
    for i, entry in enumerate(scores[:max(0, min(5, b.h - 12))], 1):
        line = "%d. %-14s %7d" % (i, entry["name"], entry["score"])
        center(b, 8 + i, line, ORANGE if i == rank else DIM)
    center(b, b.h - 2, "ENTER/LEER: Startmenue  Q: Ende", ORANGE)
    return b.render()

# ---- Held ----
def hero_pose(g, ascii_only=False):
    k = HERO_ASCII if ascii_only else HERO_KAO
    if g.dead:
        return k["dead"][0]
    if g.ducking:
        return k["duck"][0]
    if g.shoot_t > 0:
        return k["shoot"][0]
    if g.y > 0.3:
        return k["jump"][0] if g.vy > 0 else k["fall"][0]
    run = k["run"]
    return run[(g.t // 3) % len(run)]

def hero_col(g):
    if g.dead:
        return RED
    if g.shoot_t > 0:
        return YEL
    if g.ducking:
        return CYN
    return GRN

# ---- Zeichnen ----
def draw_game(g, hs=0, ascii_only=False):
    b = Buf(g.geometry)
    for c in g.clouds:
        for i, row in enumerate(CLOUDS):
            b.put(int(c[0]), c[1] + i, row, DIM)
    for p in g.bg:
        b.put(int(p[0]), p[1], p[2], DIM)
    for p in g.parts:
        b.put(int(p[0]), int(p[1]), p[5], YEL)

    for o in g.obs:
        col = MAG if o["kind"] == "word" else (RED if o["kind"] == "bird" else GRN)
        art = o["art"]
        if o["art2"] and o["f"] >= 4:
            art = o["art2"]
        b.art(int(o["x"]), g.geometry.ground - 1 - o["off"], art, col)

    for bl in g.bul:
        b.put(int(bl[0]), bl[1], "-=", YEL)

    prow = g.geometry.ground - 1 - int(round(g.y))
    b.put(g.geometry.player_x, prow, hero_pose(g, ascii_only), hero_col(g))
    if g.y > 0.3 and not g.ducking:
        b.put(g.geometry.player_x + 2, prow + 1, "^", DIM)

    # Boden
    pat = "^~-_"
    gline = "".join(pat[(x + int(g.dist)) % len(pat)] for x in range(b.w))
    b.put(0, g.geometry.ground, "_" * b.w, DIM)
    b.put(0, g.geometry.ground + 1, gline, DIM)

    if b.w >= 74:
        hud = " score %5d  best %5d  kills %2d  %4dm  x%.1f" % (
            g.score, hs if g.cheated else max(hs, g.score), g.kills,
            int(g.dist / 4), g.speed)
    elif b.w >= 58:
        hud = " %5d  best %5d  k%2d  %4dm" % (
            g.score, hs if g.cheated else max(hs, g.score), g.kills, int(g.dist / 4))
    else:
        hud = " %d  k%d  %dm" % (g.score, g.kills, int(g.dist / 4))
    b.put(1, b.h - 1, hud, WHT)

    # Munition: rechtsbuendig, kuerzt sich bei schmalem Fenster
    if g.settings.infinite_ammo:
        am, acol = "piu unendlich", GRN
    elif g.reload_t > 0:
        filled = int(round((1.0 - g.reload_t / g.reload_time) * 10))
        if b.w >= 74:
            am = "RELOAD [%s] %.1fs" % ("#" * filled + "." * (10 - filled),
                                        g.reload_t)
        else:
            am = "RELOAD %.1fs" % g.reload_t
        acol = RED
    else:
        acol = GRN if g.ammo > 3 else YEL
        filled = int(round(10 * g.ammo / g.mag_size))
        bar = "|" * filled + "." * (10 - filled)
        if b.w >= 74:
            am = "piu [%s] %2d  %2ds" % (bar, g.ammo, int(g.mag_t))
        elif b.w >= 58:
            am = "piu [%s]" % bar
        else:
            am = "piu %d" % g.ammo
    b.put(b.w - len(am) - 1, b.h - 1, am, acol)

    if g.click_t > 0:
        b.put(g.geometry.player_x + HERO_W, prow, " *klick*", RED)
    if g.msg_t > 0:
        b.put(g.geometry.player_x + 4, prow - 1, g.msg, YEL)
    return b.render()
