"""Deterministische Spiellogik. Keine Terminal-, Datei- oder Soundzugriffe."""
import math
import random
import uuid
from dataclasses import replace
from .assets import HERO_W, PHRASES, make_obstacle
from .settings import Settings, FPS, MAG_WINDOW, RELOAD_TIME, DENSITIES
from .geometry import Geometry

class Game:
    """Eine Runde mit eigenem Zufallsgenerator und festem 18-Hz-Zeitschritt."""
    def __init__(self, settings=None, geometry=None, seed=None):
        self.geometry = geometry or Geometry()
        self.rng = random.Random(seed)
        self.events = []
        self.run_id = uuid.uuid4().hex
        self.settings = replace(settings) if settings is not None else Settings()
        self.settings.validate()
        self.sm = self.settings.tempo
        self.cheated = self.settings.cheats_active
        self.mag_size = self.settings.magazine
        self.reload_time = 0.35 if self.settings.instant_reload else RELOAD_TIME
        self.y = 0.0          # Hoehe ueber Boden
        self.vy = 0.0
        self.jumps = 0
        self.ducking = 0
        self.shoot_t = 0
        self.ammo = self.mag_size
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
        self.spawned = 0
        self.spawn = 22 / DENSITIES[self.settings.density]
        self.dead = False
        self.msg = ""
        self.msg_t = 0
        _span = list(range(2, max(3, self.geometry.ground - 5)))
        _cnt = max(3, min(7, (self.geometry.width * self.geometry.ground) // 300))
        rows = self.rng.sample(_span, min(_cnt, len(_span)))
        for ry in rows:
            self.bg.append([self.rng.uniform(0, self.geometry.width), ry, self.rng.choice(PHRASES)])
        self.clouds.append([self.rng.uniform(0, self.geometry.width), 1])

    # ---- Aktionen ----
    def jump(self):
        if self.dead:
            return
        if self.jumps < 2:
            self.vy = 1.55 if self.jumps == 0 else 1.35
            if self.settings.mega_jump:
                self.vy *= 1.45
            self.jumps += 1
            self.ducking = 0
            self.events.append("jump")

    def duck(self):
        if self.dead:
            return
        if self.y <= 0.01:
            self.ducking = 8
        else:
            self.vy -= 0.9   # schnell runter

    def shoot(self):
        if self.dead:
            return
        if self.reload_t > 0 or self.ammo <= 0:
            if self.click_t <= 0:
                self.events.append("click")
            self.click_t = 10
            return
        by = self.geometry.ground - 1 - int(self.y)
        if self.ducking:
            by = self.geometry.ground - 1
        self.bul.append([self.geometry.player_x + HERO_W - 1.0, by])
        self.shoot_t = 4
        if not self.settings.infinite_ammo:
            self.ammo -= 1
        self.events.append("piu")
        if self.ammo == 0:
            self.reload_t = self.reload_time
            self.events.append("empty")

    def on_resize(self, geometry):
        """Nach Groessenaenderung alles wieder ins Bild holen."""
        self.geometry = geometry
        self.bg = [p for p in self.bg if 2 <= p[1] < max(3, self.geometry.ground - 4)]
        for p in self.bg:
            p[0] = min(p[0], float(self.geometry.width))
        for c in self.clouds:
            c[0] = min(c[0], float(self.geometry.width))
        self.obs = [o for o in self.obs if o["x"] < self.geometry.width + 4]
        self.bul = [bl for bl in self.bul if bl[0] < self.geometry.width]
        for bl in self.bul:
            bl[1] = max(0, min(self.geometry.ground - 1, bl[1]))
        self.parts = []
        if self.geometry.ground - 1 - int(round(self.y)) < 1:
            self.y = 0.0
            self.vy = 0.0
            self.jumps = 0

    def drain_events(self):
        """Soundereignisse einmalig abholen, ohne den Spielzustand zu ändern."""
        events, self.events = self.events, []
        return events

    def snapshot(self):
        """Eine von dieser Instanz unabhängige JSON-kompatible Kopie liefern."""
        from .checkpoint import encode
        return encode(self)

    @classmethod
    def from_snapshot(cls, data):
        """Eine validierte Runde samt Zufallsfolge wiederherstellen."""
        from .checkpoint import decode
        return decode(data)

    # ---- Physik / Logik ----
    def step(self):
        """Genau einen Simulationsschritt ausfuehren; keine Uhr, kein I/O."""
        if self.dead:
            return
        self._advance_distance()
        self._update_player()
        self._update_ammo()
        self._update_background()
        self._update_obstacles()
        self._update_projectiles()
        self._player_hits()
        self.score = (int(self.dist / 3) + self.kills * 25) * (
            2 if self.settings.double_points else 1)

    def _burst(self, o):
        top, bot = self._rows_of(o)
        self.obs.remove(o)
        self.kills += 1
        self.events.append("kill")
        self.msg = self.rng.choice(["piu!", "autsch*", "weg damit", "piu piu"])
        self.msg_t = 12
        for _ in range(7):
            self.parts.append([o["x"] + o["w"] / 2, (top + bot) / 2,
                               self.rng.uniform(-.8, .8), self.rng.uniform(-.5, .5),
                               self.rng.randint(3, 7), self.rng.choice("*.,'`^")])

    def _rows_of(self, o):
        bot = self.geometry.ground - 1 - o["off"]
        return bot - o["h"] + 1, bot

    def _bullet_hits(self):
        for bl in list(self.bul):
            for o in list(self.obs):
                top, bot = self._rows_of(o)
                # Relative Bewegung beider Objekte über das gesamte Frame prüfen.
                obstacle_speed = self.speed * (1.25 if o["kind"] == "bird" else 1.0)
                relative_before = bl[0] - 3.4 - (o["x"] + obstacle_speed)
                relative_after = bl[0] - o["x"]
                if relative_before <= o["w"] and relative_after >= -1 and top <= bl[1] <= bot:
                    self._burst(o)
                    if bl in self.bul:
                        self.bul.remove(bl)
                    break

    def _player_hits(self):
        prow = self.geometry.ground - 1 - int(round(self.y))
        px0, px1 = self.geometry.player_x + 1, self.geometry.player_x + HERO_W - 3
        for o in list(self.obs):
            top, bot = self._rows_of(o)
            ox0, ox1 = o["x"], o["x"] + o["w"] - 1
            if ox1 < px0 - 0.2 or ox0 > px1 + 0.2:
                continue
            if top <= prow <= bot:
                if self.settings.invincible:
                    self._burst(o)
                else:
                    self.dead = True
                    return


    def _advance_distance(self):
        self.t += 1
        # Grundtempo waechst mit der Strecke, dazu eine sanfte Welle
        base = 0.95 + 1.75 * (1.0 - math.exp(-self.dist / 1400.0))
        wave = 0.12 * math.sin(self.t / 47.0) + 0.07 * math.sin(self.t / 13.0)
        self.speed = max(0.7, (base + wave)) * self.sm
        self.dist += self.speed


    def _update_player(self):
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


    def _update_ammo(self):
        # Munition: Reload-Countdown bzw. 30s-Fenster
        dt = 1.0 / FPS
        if self.settings.infinite_ammo:
            self.ammo = self.mag_size
            self.reload_t = 0.0
            self.mag_t = MAG_WINDOW
        elif self.reload_t > 0:
            self.reload_t -= dt
            if self.reload_t <= 1e-9:
                self.reload_t = 0.0
                self.ammo = self.mag_size
                self.mag_t = MAG_WINDOW
                self.events.append("reload_done")
        else:
            self.mag_t -= dt
            if self.mag_t <= 1e-9:
                if self.ammo < self.mag_size:
                    self.ammo = self.mag_size
                    self.events.append("reload_done")
                self.mag_t = MAG_WINDOW


    def _update_background(self):
        # Hintergrund-Saetze (Parallax)
        for p in self.bg:
            p[0] -= self.speed * 0.35
        self.bg = [p for p in self.bg if p[0] + len(p[2]) > 0]
        max_bg = max(3, min(9, (self.geometry.width * self.geometry.ground) // 260))
        if self.rng.random() < 0.035 * (self.geometry.width / 78.0) and len(self.bg) < max_bg:
            taken = {p[1] for p in self.bg if p[0] + len(p[2]) > self.geometry.width - 4}
            free = [y for y in range(2, max(3, self.geometry.ground - 5)) if y not in taken]
            if free:
                self.bg.append([float(self.geometry.width), self.rng.choice(free),
                                self.rng.choice(PHRASES)])
        for c in self.clouds:
            c[0] -= self.speed * 0.18
        self.clouds = [c for c in self.clouds if c[0] + 11 > 0]
        max_cl = max(2, min(5, self.geometry.width // 42))
        if self.rng.random() < 0.012 * (self.geometry.width / 78.0) and len(self.clouds) < max_cl:
            self.clouds.append([float(self.geometry.width), self.rng.choice([0, 1])])


    def _update_obstacles(self):
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
            self.spawned += 1
            lvl = int(self.dist / 400)
            m = make_obstacle(lvl, self.rng)
            art = m["art"]
            self.obs.append({"x": float(self.geometry.width + 2), "art": art, "art2": m["art2"],
                             "kind": m["kind"], "off": m["off"],
                             "w": max(len(r) for r in art),
                             "h": len(art), "f": self.rng.randint(0, 7)})
            # Abstand: skaliert mit Tempo (Reaktionszeit bleibt fair),
            # dazu Rhythmus-Variation und gelegentliche Doppel-/Ruhepausen
            react = 15.0 + 9.0 * self.speed
            jitter = self.rng.uniform(0.75, 1.65)
            gap = react * jitter
            r = self.rng.random()
            if r < 0.14 and lvl >= 1:
                gap = react * 0.55            # Doppelschlag
            elif r > 0.93:
                gap = react * 2.4             # Verschnaufpause
            self.spawn = max(13.0, gap) / DENSITIES[self.settings.density]


    def _update_projectiles(self):
        # Schuesse
        for bl in self.bul:
            bl[0] += 3.4
        self.bul = [bl for bl in self.bul if bl[0] < self.geometry.width]
        self._bullet_hits()

        # Partikel
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.parts = [p for p in self.parts if p[4] > 0]

        if self.msg_t > 0:
            self.msg_t -= 1
