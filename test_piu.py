#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA-Suite fuer PIU PIU.

    python -m unittest test_piu -v
    python test_piu.py

Deckt ab: Highscores (ein Eintrag pro Spieler), Munition/Reload,
Physik, Kollision, Hindernis-Katalog, responsive Layout, Rendering,
Screens und die CLI.
"""
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import piuu as P  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def strip(s):
    return ANSI.sub("", s.replace("\033[H", ""))


def capture(fn, *a, **kw):
    """Ruft eine Zeichenfunktion auf und gibt den reinen Text zurueck."""
    buf = io.StringIO()
    old = P.out
    P.out = buf.write
    try:
        fn(*a, **kw)
    finally:
        P.out = old
    return strip(buf.getvalue())


class ScoreBase(unittest.TestCase):
    """Legt SCORE_FILE in ein temporaeres Verzeichnis."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.orig = P.SCORE_FILE
        P.SCORE_FILE = os.path.join(self.tmp, "scores.json")

    def tearDown(self):
        P.SCORE_FILE = self.orig

    def write(self, data):
        with open(P.SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def read(self):
        with open(P.SCORE_FILE, encoding="utf-8") as f:
            return json.load(f)


# ============================================================
class TestHighscoreEinEintragProSpieler(ScoreBase):
    """Der gemeldete Bug: derselbe Spieler mehrfach in der Liste."""

    def test_gemeldeter_bug_wird_beim_laden_repariert(self):
        self.write([
            {"name": "philipp", "score": 294, "kills": 3, "date": "x"},
            {"name": "philipp", "score": 57, "kills": 0, "date": "y"},
        ])
        sc = P.load_scores()
        self.assertEqual(len(sc), 1, "philipp darf nur einmal vorkommen")
        self.assertEqual(sc[0]["score"], 294, "Bestwert muss gewinnen")
        self.assertEqual(sc[0]["runs"], 2, "beide Laeufe zaehlen")

    def test_viele_laeufe_bleiben_ein_eintrag(self):
        for i in range(25):
            P.save_score("philipp", i * 10, i)
        sc = P.load_scores()
        self.assertEqual(len(sc), 1)
        self.assertEqual(sc[0]["score"], 240)
        self.assertEqual(sc[0]["runs"], 25)

    def test_schlechterer_lauf_ueberschreibt_nicht(self):
        P.save_score("philipp", 500, 9)
        sc, rank, improved = P.save_score("philipp", 80, 1)
        self.assertEqual(sc[0]["score"], 500)
        self.assertFalse(improved)
        self.assertEqual(rank, 1)

    def test_besserer_lauf_aktualisiert(self):
        P.save_score("philipp", 100, 1)
        sc, rank, improved = P.save_score("philipp", 900, 12)
        self.assertEqual(sc[0]["score"], 900)
        self.assertEqual(sc[0]["kills"], 12)
        self.assertTrue(improved)

    def test_name_case_und_leerzeichen_sind_derselbe_spieler(self):
        P.save_score("philipp", 100, 1)
        P.save_score("PHILIPP", 200, 2)
        P.save_score("  philipp  ", 50, 0)
        sc = P.load_scores()
        self.assertEqual(len(sc), 1)
        self.assertEqual(sc[0]["score"], 200)
        self.assertEqual(sc[0]["runs"], 3)

    def test_mehrere_spieler_bleiben_getrennt(self):
        P.save_score("philipp", 300, 3)
        P.save_score("kevin", 500, 5)
        P.save_score("philipp", 100, 1)
        sc = P.load_scores()
        self.assertEqual(len(sc), 2)
        self.assertEqual([e["name"] for e in sc], ["kevin", "philipp"])

    def test_datei_hat_keine_duplikate(self):
        for _ in range(10):
            P.save_score("philipp", random.randint(1, 999), 1)
        raw = self.read()
        namen = [e["name"].lower() for e in raw]
        self.assertEqual(len(namen), len(set(namen)), "Datei enthaelt Duplikate")


class TestHighscoreRobust(ScoreBase):
    def test_fehlende_datei(self):
        self.assertEqual(P.load_scores(), [])
        self.assertEqual(P.best(), 0)

    def test_kaputtes_json(self):
        with open(P.SCORE_FILE, "w") as f:
            f.write("{kein json")
        self.assertEqual(P.load_scores(), [])

    def test_falscher_typ(self):
        self.write({"nicht": "liste"})
        self.assertEqual(P.load_scores(), [])

    def test_muell_eintraege_werden_ignoriert(self):
        self.write([None, 42, "text", {"name": "ok", "score": 5}])
        sc = P.load_scores()
        self.assertEqual(len(sc), 1)
        self.assertEqual(sc[0]["name"], "ok")

    def test_fehlende_felder(self):
        self.write([{"name": "x"}])
        sc = P.load_scores()
        self.assertEqual(sc[0]["score"], 0)

    def test_maximal_10_spieler(self):
        for i in range(20):
            P.save_score("spieler%d" % i, i * 10, i)
        self.assertLessEqual(len(P.load_scores()), P.MAX_SCORES)

    def test_best_liefert_hoechsten(self):
        P.save_score("a", 100, 1)
        P.save_score("b", 700, 2)
        self.assertEqual(P.best(), 700)

    def test_langer_name_wird_gekuerzt(self):
        P.save_score("x" * 50, 10, 0)
        self.assertLessEqual(len(P.load_scores()[0]["name"]), 14)

    def test_leerer_name_faellt_auf_piu(self):
        P.save_score("", 10, 0)
        self.assertEqual(P.load_scores()[0]["name"], "Piu")

    def test_rank_stimmt(self):
        P.save_score("a", 900, 1)
        sc, rank, _ = P.save_score("b", 100, 1)
        self.assertEqual(rank, 2)
        self.assertEqual(sc[rank - 1]["name"], "b")


# ============================================================
class TestMunitionSpec(unittest.TestCase):
    """Die geforderten Werte selbst: 10 Schuss / 30s Fenster / 5s Reload."""

    def test_magazin_hat_zehn_schuss(self):
        self.assertEqual(P.MAG_SIZE, 10)

    def test_fenster_ist_dreissig_sekunden(self):
        self.assertEqual(P.MAG_WINDOW, 30.0)

    def test_reload_dauert_fuenf_sekunden(self):
        self.assertEqual(P.RELOAD_TIME, 5.0)

    def test_fps_passt_zur_schlafzeit(self):
        """FPS muss zum sleep() der Hauptschleife passen, sonst stimmen
        die 30s/5s in echter Zeit nicht."""
        with io.open(os.path.join(HERE, "piuu.py"), encoding="utf-8") as f:
            src = f.read()
        m = re.search(r"time\.sleep\((0\.\d+)\)\s*\n\s*except KeyboardInterrupt", src)
        if m is None:
            m = re.search(r"g\.draw\(best\(\)\)\s*\n\s*time\.sleep\((0\.\d+)\)", src)
        self.assertIsNotNone(m, "sleep der Spielschleife nicht gefunden")
        schlaf = float(m.group(1))
        self.assertAlmostEqual(1.0 / P.FPS, schlaf, delta=0.008,
                               msg="FPS=%s passt nicht zu sleep=%s" % (P.FPS, schlaf))

    def test_genau_zehn_schuss_dann_leer(self):
        P.set_size(80, 20)
        g = P.Game(P.Snd(True), True, 1.0)
        for i in range(10):
            self.assertGreater(g.ammo, 0, "Schuss %d muss gehen" % (i + 1))
            g.shoot()
        self.assertEqual(g.ammo, 0)
        self.assertEqual(len(g.bul), 10, "genau 10 Projektile")

    def test_reload_exakt_fuenf_sekunden(self):
        P.set_size(80, 20)
        g = P.Game(P.Snd(True), True, 1.0)
        for _ in range(10):
            g.shoot()
        sek = 0.0
        while g.ammo == 0 and sek < 20:
            g.step()
            sek += 1.0 / P.FPS
        self.assertAlmostEqual(sek, 5.0, delta=0.2,
                               msg="Reload muss ~5s dauern, war %.2fs" % sek)

    def test_fenster_exakt_dreissig_sekunden(self):
        P.set_size(80, 20)
        g = P.Game(P.Snd(True), True, 1.0)
        g.shoot()
        sek = 0.0
        while g.ammo < 10 and sek < 60:
            g.step()
            sek += 1.0 / P.FPS
        self.assertAlmostEqual(sek, 30.0, delta=0.5,
                               msg="Fenster muss ~30s sein, war %.2fs" % sek)


class TestMunition(unittest.TestCase):
    def setUp(self):
        P.set_size(80, 20)
        self.g = P.Game(P.Snd(True), True, 1.0)

    def test_startet_voll(self):
        self.assertEqual(self.g.ammo, P.MAG_SIZE)
        self.assertEqual(self.g.reload_t, 0)

    def test_schuss_kostet_munition(self):
        self.g.shoot()
        self.assertEqual(self.g.ammo, P.MAG_SIZE - 1)
        self.assertEqual(len(self.g.bul), 1)

    def test_genau_zehn_schuss(self):
        for _ in range(P.MAG_SIZE):
            self.g.shoot()
        self.assertEqual(self.g.ammo, 0)
        self.assertEqual(len(self.g.bul), P.MAG_SIZE)
        self.assertAlmostEqual(self.g.reload_t, P.RELOAD_TIME)

    def test_elfter_schuss_klickt_nur(self):
        for _ in range(P.MAG_SIZE):
            self.g.shoot()
        n = len(self.g.bul)
        self.g.shoot()
        self.assertEqual(len(self.g.bul), n, "kein Schuss bei leerem Magazin")
        self.assertGreater(self.g.click_t, 0)

    def test_reload_dauert_fuenf_sekunden(self):
        for _ in range(P.MAG_SIZE):
            self.g.shoot()
        for _ in range(int(P.RELOAD_TIME * P.FPS) - 2):
            self.g.step()
        self.assertEqual(self.g.ammo, 0, "vor Ablauf noch leer")
        for _ in range(4):
            self.g.step()
        self.assertEqual(self.g.ammo, P.MAG_SIZE, "nach 5s wieder voll")
        self.assertEqual(self.g.reload_t, 0)

    def test_magazin_fenster_fuellt_auf(self):
        for _ in range(3):
            self.g.shoot()
        self.assertEqual(self.g.ammo, P.MAG_SIZE - 3)
        for _ in range(int(P.MAG_WINDOW * P.FPS) + 2):
            self.g.step()
        self.assertEqual(self.g.ammo, P.MAG_SIZE)

    def test_kein_schuss_waehrend_reload(self):
        for _ in range(P.MAG_SIZE):
            self.g.shoot()
        self.g.step()
        n = len(self.g.bul)
        self.g.shoot()
        self.assertEqual(len(self.g.bul), n)


# ============================================================
class TestPhysik(unittest.TestCase):
    def setUp(self):
        P.set_size(80, 20)
        self.g = P.Game(P.Snd(True), True, 1.0)

    def test_startet_am_boden(self):
        self.assertEqual(self.g.y, 0)
        self.assertEqual(self.g.jumps, 0)

    def test_sprung_hebt_ab(self):
        self.g.jump()
        self.g.step()
        self.assertGreater(self.g.y, 0)

    def test_doppelsprung_dann_schluss(self):
        self.g.jump()
        self.g.jump()
        self.assertEqual(self.g.jumps, 2)
        vy = self.g.vy
        self.g.jump()
        self.assertEqual(self.g.vy, vy, "dritter Sprung darf nichts tun")

    def test_kommt_wieder_runter(self):
        self.g.jump()
        for _ in range(120):
            self.g.step()
            if self.g.dead:
                self.g.dead = False
                self.g.obs = []
        self.assertEqual(self.g.y, 0)
        self.assertEqual(self.g.jumps, 0, "Spruenge nach Landung zurueckgesetzt")

    def test_ducken_nur_am_boden(self):
        self.g.duck()
        self.assertGreater(self.g.ducking, 0)

    def test_tempo_steigt(self):
        self.g.step()
        v1 = self.g.speed
        self.g.dist = 5000
        self.g.step()
        self.assertGreater(self.g.speed, v1)

    def test_tempo_bleibt_begrenzt(self):
        self.g.dist = 10 ** 6
        self.g.step()
        self.assertLess(self.g.speed, 4.0)

    def test_score_waechst(self):
        for _ in range(50):
            self.g.step()
            if self.g.dead:
                self.g.dead = False
                self.g.obs = []
        self.assertGreater(self.g.score, 0)

    def test_kill_gibt_punkte(self):
        self.g.obs = []
        s0 = self.g.score
        self.g.kills = 1
        self.g.step()
        self.assertGreater(self.g.score, s0)


class TestKollision(unittest.TestCase):
    def setUp(self):
        P.set_size(80, 20)
        self.g = P.Game(P.Snd(True), True, 1.0)
        self.g.obs = []

    def _obs(self, x, off=0, art=None):
        art = art or ["###"]
        return {"x": float(x), "art": art, "art2": None, "kind": "solid",
                "off": off, "w": max(len(r) for r in art), "h": len(art), "f": 0}

    def test_trifft_hindernis_am_boden(self):
        self.g.obs = [self._obs(P.PX + 1)]
        self.g._player_hits()
        self.assertTrue(self.g.dead)

    def test_sprung_rettet(self):
        self.g.obs = [self._obs(P.PX + 1)]
        self.g.y = 5.0
        self.g._player_hits()
        self.assertFalse(self.g.dead)

    def test_weit_entferntes_hindernis_egal(self):
        self.g.obs = [self._obs(P.PX + 40)]
        self.g._player_hits()
        self.assertFalse(self.g.dead)

    def test_schuss_zerstoert(self):
        self.g.obs = [self._obs(P.PX + 20)]
        self.g.bul = [[float(P.PX + 20), P.GROUND - 1]]
        self.g._bullet_hits()
        self.assertEqual(len(self.g.obs), 0)
        self.assertEqual(self.g.kills, 1)

    def test_schuss_verfehlt_fliegendes_ziel_am_boden(self):
        self.g.obs = [self._obs(P.PX + 20, off=4)]
        self.g.bul = [[float(P.PX + 20), P.GROUND - 1]]
        self.g._bullet_hits()
        self.assertEqual(len(self.g.obs), 1, "Bodenschuss trifft Flieger nicht")


# ============================================================
class TestHindernisse(unittest.TestCase):
    def test_level0_hat_auswahl(self):
        arten = {"|".join(P.make_obstacle(0)["art"]) for _ in range(3000)}
        self.assertGreaterEqual(len(arten), 8)

    def test_mehr_vielfalt_in_hoeheren_leveln(self):
        a0 = {"|".join(P.make_obstacle(0)["art"]) for _ in range(4000)}
        a5 = {"|".join(P.make_obstacle(5)["art"]) for _ in range(4000)}
        self.assertGreater(len(a5), len(a0))
        self.assertGreaterEqual(len(a5), 25)

    def test_struktur_immer_gueltig(self):
        for lvl in range(7):
            for _ in range(500):
                o = P.make_obstacle(lvl)
                self.assertIn(o["kind"], ("solid", "bird", "word"))
                self.assertTrue(o["art"])
                self.assertTrue(all(isinstance(r, str) for r in o["art"]))
                self.assertGreaterEqual(o["off"], 0)
                self.assertLess(o["off"], 8)

    def test_fliegende_haben_zweites_frame(self):
        found = False
        for _ in range(4000):
            o = P.make_obstacle(5)
            if o["kind"] == "bird" and o["art2"]:
                self.assertEqual(len(o["art"]), len(o["art2"]))
                found = True
        self.assertTrue(found, "keine animierten Flieger erzeugt")

    def test_woerter_kommen_vor(self):
        woerter = set()
        for _ in range(4000):
            o = P.make_obstacle(3)
            if o["kind"] == "word":
                woerter.add(o["art"][0])
        self.assertTrue(woerter)
        self.assertTrue(any("piu" in w.lower() for w in woerter))

    def test_hindernisse_passen_ins_bild(self):
        P.set_size(P.MIN_W, P.MIN_H)
        for lvl in range(7):
            for _ in range(300):
                o = P.make_obstacle(lvl)
                hoehe = len(o["art"]) + o["off"]
                self.assertLess(hoehe, P.GROUND,
                                "Hindernis ragt aus dem Spielfeld")


# ============================================================
class TestResponsive(unittest.TestCase):
    def tearDown(self):
        P.set_size(80, 20)

    def test_set_size_wirkt(self):
        P.set_size(120, 30)
        self.assertEqual((P.W, P.H), (120, 30))
        self.assertLess(P.GROUND, P.H)
        self.assertGreater(P.PX, 0)

    def test_grenzen_werden_eingehalten(self):
        P.set_size(5, 5)
        self.assertEqual((P.W, P.H), (P.MIN_W, P.MIN_H))
        P.set_size(9999, 9999)
        self.assertEqual((P.W, P.H), (P.MAX_W, P.MAX_H))

    def test_fit_erkennt_aenderung(self):
        orig = P.term_size
        try:
            P.term_size = lambda: (80, 24)
            P.fit()
            self.assertFalse(P.fit(), "gleiche Groesse -> keine Aenderung")
            P.term_size = lambda: (140, 40)
            self.assertTrue(P.fit(), "neue Groesse -> Aenderung")
            self.assertEqual(P.W, 139)
        finally:
            P.term_size = orig

    def test_too_small_flag(self):
        orig = P.term_size
        try:
            P.term_size = lambda: (20, 8)
            P.fit()
            self.assertTrue(P.TOO_SMALL)
            P.term_size = lambda: (100, 30)
            P.fit()
            self.assertFalse(P.TOO_SMALL)
        finally:
            P.term_size = orig

    def test_spiel_laeuft_in_allen_groessen(self):
        for cols, rows in [(46, 14), (60, 18), (80, 20), (120, 30), (200, 44)]:
            P.set_size(cols, rows)
            random.seed(1)
            g = P.Game(P.Snd(True), True, 1.0)
            for i in range(60):
                if i % 7 == 0:
                    g.jump()
                if i % 5 == 0:
                    g.shoot()
                g.step()
                if g.dead:
                    g.dead = False
                    g.obs = []
                txt = capture(g.draw, 100)
                zeilen = txt.split("\n")
                self.assertEqual(len(zeilen), rows,
                                 "%dx%d: falsche Zeilenzahl" % (cols, rows))
                self.assertLessEqual(max(len(z) for z in zeilen), cols,
                                     "%dx%d: Zeile zu lang" % (cols, rows))

    def test_live_resize_stuerzt_nicht_ab(self):
        P.set_size(80, 20)
        random.seed(2)
        g = P.Game(P.Snd(True), True, 1.0)
        for cols, rows in [(50, 16), (140, 40), (46, 14), (200, 44), (70, 19)]:
            P.set_size(cols, rows)
            g.on_resize()
            for _ in range(30):
                g.step()
                if g.dead:
                    g.dead = False
                    g.obs = []
                capture(g.draw, 100)
        self.assertTrue(True)

    def test_on_resize_holt_objekte_ins_bild(self):
        P.set_size(200, 44)
        g = P.Game(P.Snd(True), True, 1.0)
        for _ in range(60):
            g.step()
        P.set_size(46, 14)
        g.on_resize()
        for o in g.obs:
            self.assertLess(o["x"], P.W + 5)
        for b in g.bul:
            self.assertLess(b[0], P.W)
            self.assertLess(b[1], P.GROUND)
        for p in g.bg:
            self.assertLess(p[1], P.GROUND)


class TestRendering(unittest.TestCase):
    def setUp(self):
        P.set_size(80, 20)

    def test_buffer_masse(self):
        b = P.Buf()
        self.assertEqual(len(b.g), P.H)
        self.assertEqual(len(b.g[0]), P.W)

    def test_put_clippt_am_rand(self):
        b = P.Buf()
        b.put(-5, 0, "abc")
        b.put(P.W - 1, 0, "xyz")
        b.put(0, -1, "oben")
        b.put(0, P.H + 5, "unten")
        self.assertEqual(len(b.render().split("\n")), P.H)

    def test_held_ist_sichtbar(self):
        g = P.Game(P.Snd(True), True, 1.0)
        g.obs = []
        txt = capture(g.draw, 0)
        self.assertIn(P.HERO_KAO["run"][0].split("(")[0][:2], txt)

    def test_alle_posen_gleich_breit(self):
        for satz in (P.HERO_KAO, P.HERO_ASCII):
            breiten = {len(v[0]) for v in satz.values()}
            self.assertEqual(len(breiten), 1,
                             "Posen unterschiedlich breit: %s" % breiten)
            self.assertEqual(breiten.pop(), P.HERO_W)

    def test_posen_wechseln_je_zustand(self):
        g = P.Game(P.Snd(True), True, 1.0)
        g.y, g.vy = 3.0, 1.0
        self.assertEqual(g.hero_pose(), P.HERO_KAO["jump"][0])
        g.vy = -1.0
        self.assertEqual(g.hero_pose(), P.HERO_KAO["fall"][0])
        g.y, g.vy = 0.0, 0.0
        g.ducking = 3
        self.assertEqual(g.hero_pose(), P.HERO_KAO["duck"][0])
        g.ducking = 0
        g.shoot_t = 2
        self.assertEqual(g.hero_pose(), P.HERO_KAO["shoot"][0])
        g.shoot_t = 0
        g.dead = True
        self.assertEqual(g.hero_pose(), P.HERO_KAO["dead"][0])

    def test_ascii_modus_ohne_kaomoji(self):
        g = P.Game(P.Snd(True), False, 1.0)
        self.assertEqual(g.hero_pose(), P.HERO_ASCII["run"][0])
        self.assertTrue(all(ord(c) < 128 for c in g.hero_pose()))

    def test_hud_passt_sich_breite_an(self):
        for cols in (46, 60, 80, 120):
            P.set_size(cols, 20)
            g = P.Game(P.Snd(True), True, 1.0)
            g.obs = []
            letzte = capture(g.draw, 500).split("\n")[-1]
            self.assertLessEqual(len(letzte), cols)
            self.assertIn("piu", letzte, "Munition fehlt im HUD")

    def test_reload_erscheint_im_hud(self):
        P.set_size(80, 20)
        g = P.Game(P.Snd(True), True, 1.0)
        g.obs = []
        for _ in range(P.MAG_SIZE):
            g.shoot()
        self.assertIn("RELOAD", capture(g.draw, 0))


class TestScreens(unittest.TestCase):
    def tearDown(self):
        P.set_size(80, 20)

    def test_startscreen_in_allen_groessen(self):
        for cols, rows in [(46, 14), (60, 18), (80, 20), (200, 44)]:
            P.set_size(cols, rows)
            txt = capture(P.draw_start, True, 1234)
            zeilen = txt.split("\n")
            self.assertEqual(len(zeilen), rows)
            self.assertLessEqual(max(len(z) for z in zeilen), cols)
            self.assertIn("START", txt)

    def test_startscreen_blinkt(self):
        P.set_size(80, 20)
        self.assertIn("[ START ]", capture(P.draw_start, True, 0))
        self.assertNotIn("[ START ]", capture(P.draw_start, False, 0))

    def test_gameover_in_allen_groessen(self):
        scores = [{"name": "philipp", "score": 900, "kills": 5, "runs": 3}]
        for cols, rows in [(46, 14), (80, 20), (200, 44)]:
            P.set_size(cols, rows)
            txt = capture(P.draw_gameover, 900, 5, 300, 1, scores, True)
            zeilen = txt.split("\n")
            self.assertEqual(len(zeilen), rows)
            self.assertLessEqual(max(len(z) for z in zeilen), cols)
            self.assertIn("philipp", txt)

    def test_gameover_zeigt_rekord_nur_bei_verbesserung(self):
        P.set_size(80, 20)
        sc = [{"name": "a", "score": 900, "runs": 2}]
        self.assertIn("REKORD", capture(P.draw_gameover, 900, 1, 10, 1, sc, True))
        txt = capture(P.draw_gameover, 100, 1, 10, 1, sc, False)
        self.assertNotIn("REKORD", txt)
        self.assertIn("bestleistung", txt)

    def test_gameover_liste_ohne_duplikate(self):
        P.set_size(80, 20)
        sc = [{"name": "philipp", "score": 294, "kills": 3, "runs": 2}]
        txt = capture(P.draw_gameover, 57, 0, 20, 1, sc, False)
        self.assertEqual(txt.count("philipp"), 1,
                         "Spieler darf nur einmal in der Liste stehen")

    def test_too_small_screen(self):
        orig = P.term_size
        try:
            P.term_size = lambda: (20, 8)
            txt = capture(P.draw_too_small)
            self.assertIn("zu klein", txt)
        finally:
            P.term_size = orig


class TestSonstiges(unittest.TestCase):
    def test_phrasen_vorhanden(self):
        alle = " ".join(P.PHRASES).lower()
        self.assertIn("piu", alle)
        self.assertIn("aslok", alle)

    def test_sound_stumm_wirft_nicht(self):
        s = P.Snd(True)
        for fn in (s.piu, s.jump, s.hit, s.kill, s.start,
                   s.click, s.empty, s.reload_done):
            fn()

    def test_kein_hardcodierter_name(self):
        with io.open(os.path.join(HERE, "piuu.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("philipp", src.lower(),
                         "Spielername darf nicht im Code stehen")

    def test_keine_doppelten_methoden(self):
        with io.open(os.path.join(HERE, "piuu.py"), encoding="utf-8") as f:
            src = f.read()
        for name in ("def draw(self, hs):", "def step(self):",
                     "def hero_pose(self):", "def _rows_of(self, o):",
                     "def fit():", "def main():"):
            self.assertEqual(src.count(name), 1,
                             "%s kommt mehrfach vor" % name)


class TestCLI(unittest.TestCase):
    """Startet das Spiel wirklich als Prozess."""

    def run_game(self, *args, timeout=60):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "piuu.py")] + list(args),
            capture_output=True, text=True, timeout=timeout,
            cwd=tempfile.mkdtemp())

    def test_help(self):
        r = self.run_game("--help")
        self.assertEqual(r.returncode, 0)
        for opt in ("--silent", "--ascii", "--size", "--name", "--scores"):
            self.assertIn(opt, r.stdout)

    def test_demo_laeuft(self):
        r = self.run_game("--silent", "--demo", "60")
        self.assertEqual(r.returncode, 0)
        self.assertIn("demo ok", r.stdout)

    def test_demo_mit_fester_groesse(self):
        r = self.run_game("--silent", "--size", "120x34", "--demo", "40")
        self.assertIn("demo ok", r.stdout)

    def test_demo_minimalgroesse(self):
        r = self.run_game("--silent", "--size", "46x14", "--demo", "40")
        self.assertIn("demo ok", r.stdout)

    def test_ascii_modus(self):
        r = self.run_game("--silent", "--ascii", "--demo", "40")
        self.assertIn("demo ok", r.stdout)

    def test_ungueltige_groesse(self):
        r = self.run_game("--size", "quatsch")
        self.assertIn("BREITExHOEHE", r.stdout)

    def test_scores_ohne_datei(self):
        r = self.run_game("--scores")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
