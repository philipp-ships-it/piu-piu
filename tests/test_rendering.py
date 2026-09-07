"""Reine Darstellung, Rastergrenzen und sichtbare Bedienzustände."""
from copy import deepcopy
import re
import unittest

from piu.buffer import Buf
from piu.engine import Game
from piu.geometry import Geometry
from piu.menu import Menu
from piu.rendering import (draw_confirm, draw_game, draw_gameover, draw_message,
                           draw_settings, draw_start, hero_pose)
from piu.settings import SETTING_ROWS, Settings

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
GROESSEN = ((46, 14), (60, 18), (80, 20), (80, 22), (100, 28), (200, 44))


def lesbar(text):
    return ANSI.sub("", text)


class DarstellungTests(unittest.TestCase):
    def pruefe_raster(self, text, geometry):
        zeilen = lesbar(text).splitlines()
        self.assertEqual(len(zeilen), geometry.height)
        self.assertLessEqual(max(map(len, zeilen)), geometry.width)

    def test_alle_bildschirme_halten_rastergrenzen_ein(self):
        for masse in GROESSEN:
            geo = Geometry(*masse)
            game = Game(geometry=geo, seed=0)
            menu = Menu(Settings(), resumable=True)
            screens = (draw_start(menu, geo), draw_settings(menu.settings, geo), draw_confirm(menu, geo),
                       draw_game(game), draw_gameover(game, []),
                       draw_message(geo, "HINWEIS", "Ein langer erklärender Hinweis. " * 20))
            for index, text in enumerate(screens):
                with self.subTest(masse=masse, screen=index):
                    self.pruefe_raster(text, geo)

    def test_jede_settingsauswahl_ist_bei_jeder_groesse_sichtbar(self):
        for masse in GROESSEN:
            geo = Geometry(*masse)
            for index, (_, label) in enumerate(SETTING_ROWS):
                with self.subTest(masse=masse, label=label):
                    text = lesbar(draw_settings(Settings(), geo, index))
                    self.assertIn("> " + label, text)
                    self.assertIn("Cheat-Laeufe: kein Highscore", text)
                    self.pruefe_raster(text, geo)

    def test_start_zeigt_jede_auswahl_und_fortsetzen(self):
        for masse in GROESSEN:
            geo = Geometry(*masse)
            for fortsetzbar in (False, True):
                menu = Menu(Settings(), fortsetzbar)
                for index, (_, label) in enumerate(menu.choices):
                    menu.selected = index
                    with self.subTest(masse=masse, label=label):
                        text = lesbar(draw_start(menu, geo, 120))
                        self.assertIn(">>  " + label + "  <<", text)
                        self.assertIn("normal | tempo x1.00 | normal", text)
                        self.assertEqual("FORTSETZEN" in text, fortsetzbar)

    def test_bestaetigung_zeigt_beide_moeglichkeiten(self):
        menu = Menu(Settings(), True)
        for index, label in enumerate(("ZURUECK", "JA, NEUE RUNDE")):
            menu.selected = index
            self.assertIn("> " + label + " <", lesbar(draw_confirm(menu, Geometry(46, 14))))

    def test_rendern_aendert_weder_runde_rng_noch_menue(self):
        game = Game(Settings(invincible=True), seed=0)
        for _ in range(100):
            game.step()
        menu = Menu(game.settings, True)
        vorher = game.snapshot()
        events = deepcopy(game.events)
        menue_vorher = deepcopy(menu.__dict__)
        for _ in range(3):
            draw_game(game)
            draw_gameover(game, [])
            draw_start(menu, game.geometry)
            draw_settings(game.settings, game.geometry)
            draw_confirm(menu, game.geometry)
        self.assertEqual(game.snapshot(), vorher)
        self.assertEqual(game.events, events)
        self.assertEqual(menu.__dict__, menue_vorher)

    def test_ascii_modus_fuer_spiel_start_und_gameover(self):
        for masse in GROESSEN:
            game = Game(geometry=Geometry(*masse), seed=0)
            menu = Menu(game.settings)
            for text in (draw_game(game, ascii_only=True),
                         draw_start(menu, game.geometry, tick=6, ascii_only=True),
                         draw_gameover(game, [], ascii_only=True)):
                self.assertTrue(lesbar(text).isascii())

    def test_ascii_startscreen_ist_animiert_bei_ausreichender_hoehe(self):
        menu = Menu(Settings())
        geo = Geometry(100, 28)
        self.assertNotEqual(draw_start(menu, geo, tick=0, ascii_only=True),
                            draw_start(menu, geo, tick=3, ascii_only=True))

    def test_cheat_gameover_zeigt_keinen_rekord_auch_bei_improved(self):
        for masse in GROESSEN:
            game = Game(Settings(mega_jump=True), Geometry(*masse), seed=0)
            text = lesbar(draw_gameover(game, [], rank=1, improved=True))
            self.assertIn("CHEAT-LAUF: zaehlt nicht fuer den Highscore", text)
            self.assertNotIn("NEUE BESTLEISTUNG", text)

    def test_gameover_rekord_und_speicherfehler_sind_eindeutig(self):
        game = Game(seed=0)
        rekord = lesbar(draw_gameover(game, [], rank=2, improved=True))
        self.assertIn("NEUE BESTLEISTUNG! PLATZ 2", rekord)
        fehler = lesbar(draw_gameover(game, [], rank=2, improved=True, saved=False))
        self.assertIn("NICHT GESPEICHERT", fehler)
        self.assertNotIn("NEUE BESTLEISTUNG", fehler)

    def test_cheat_hud_erhoeht_bestleistung_nicht(self):
        game = Game(Settings(double_points=True), geometry=Geometry(120, 30), seed=0)
        game.score = 99999
        text = lesbar(draw_game(game, hs=120))
        self.assertIn("best   120", text)
        self.assertIn("score 99999", text)

    def test_munition_und_reload_bleiben_im_hud_sichtbar(self):
        for masse in GROESSEN:
            game = Game(Settings(magazine=1), Geometry(*masse), seed=0)
            self.assertIn("piu", lesbar(draw_game(game)).splitlines()[-1])
            game.shoot()
            self.assertIn("RELOAD", lesbar(draw_game(game)).splitlines()[-1])
            endlos = Game(Settings(infinite_ammo=True), Geometry(*masse), seed=0)
            self.assertIn("piu unendlich", lesbar(draw_game(endlos)))

    def test_heldenpose_folgt_zustand(self):
        game = Game(seed=0)
        game.jump()
        game.step()
        self.assertEqual(hero_pose(game, True), "\\(o_o)/")
        game.vy = -1
        self.assertEqual(hero_pose(game, True), "/(o_o)\\")
        game.dead = True
        self.assertEqual(hero_pose(game, True), "~(x_x)~")


class PufferTests(unittest.TestCase):
    def test_clipping_erhaelt_passende_zeichen(self):
        buffer = Buf(Geometry(46, 14))
        buffer.put(-2, 0, "abcd")
        buffer.put(45, 1, "xyz")
        buffer.put(0, -1, "oben")
        buffer.put(0, 14, "unten")
        zeilen = lesbar(buffer.render()).splitlines()
        self.assertTrue(zeilen[0].startswith("cd"))
        self.assertEqual(zeilen[1][-1], "x")
        self.assertEqual(len(zeilen), 14)
        self.assertNotIn("oben", "".join(zeilen))

    def test_mehrzeilige_grafik_wird_am_boden_ausgerichtet(self):
        buffer = Buf(Geometry(46, 14))
        buffer.art(2, 5, ["AAA", "BBB"])
        zeilen = lesbar(buffer.render()).splitlines()
        self.assertEqual(zeilen[4][2:5], "AAA")
        self.assertEqual(zeilen[5][2:5], "BBB")


if __name__ == "__main__":
    unittest.main()
