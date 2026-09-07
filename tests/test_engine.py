"""Deterministische Regeln, Kollisionsfälle und vollständige Rundensnapshots.

Langzeittests schalten ausschließlich Spielerkollisionen ab. Es gibt keine
echten Wartezeiten, Terminalzugriffe, Dateien oder externen Prozesse.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import random
import unittest
from unittest.mock import patch

from piu.assets import CATALOG, HERO_ASCII, HERO_KAO, HERO_W, make_obstacle
from piu.engine import Game
from piu.geometry import Geometry
from piu.settings import FPS, Settings


def hindernis(x, breite=3, offset=0, art=None, kind="solid"):
    """Kleine explizite Kollisionsszene statt zufälliger Testvorbedingungen."""
    art = art or ["#" * breite]
    return {"x": float(x), "art": art, "art2": None, "kind": kind,
            "off": offset, "w": max(map(len, art)), "h": len(art), "f": 0}


def fortschalten(game, anzahl):
    with patch.object(game, "_player_hits"):
        for _ in range(anzahl):
            game.step()


def aktionen(game, tick):
    if tick % 31 == 0:
        game.jump()
    if tick % 47 == 0:
        game.duck()
    if tick % 7 == 0:
        game.shoot()


class GeometrieTests(unittest.TestCase):
    def test_terminalrand_und_grenzen(self):
        for eingabe, erwartet in (((80, 24), (79, 23)), ((2, 2), (46, 14)),
                                  ((1000, 1000), (200, 44))):
            geo = Geometry.fit(*eingabe)
            self.assertEqual((geo.width, geo.height), erwartet)
            self.assertLess(geo.ground, geo.height)
            self.assertGreater(geo.player_x, 0)

    def test_geometrie_ist_unveraenderlich(self):
        with self.assertRaises(FrozenInstanceError):
            Geometry().width = 90

    def test_ungueltige_geometrie(self):
        for masse in ((45, 20), (201, 20), (80, 13), (80, 45), (True, 20), (80., 20)):
            with self.subTest(masse=masse), self.assertRaises(ValueError):
                Geometry(*masse)

    def test_zwei_runden_teilen_keine_geometrie(self):
        klein = Game(geometry=Geometry(46, 14), seed=0)
        gross = Game(geometry=Geometry(200, 44), seed=0)
        klein.on_resize(Geometry(60, 18))
        self.assertEqual(gross.geometry, Geometry(200, 44))


class SpielregelnTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(geometry=Geometry(80, 20), seed=0)

    def test_initialzustand(self):
        self.assertEqual((self.game.y, self.game.jumps, self.game.score, self.game.kills), (0, 0, 0, 0))
        self.assertEqual((self.game.ammo, self.game.reload_t), (10, 0))
        self.assertFalse(self.game.dead)

    def test_doppelsprung_und_landung(self):
        self.game.jump()
        self.game.step()
        self.assertGreater(self.game.y, 0)
        self.game.jump()
        geschwindigkeit = self.game.vy
        self.game.jump()
        self.assertEqual((self.game.jumps, self.game.vy), (2, geschwindigkeit))
        fortschalten(self.game, 50)
        self.assertEqual((self.game.y, self.game.vy, self.game.jumps), (0, 0, 0))
        self.game.jump()
        self.assertEqual(self.game.jumps, 1)

    def test_ducken_am_boden_und_schneller_fallen(self):
        self.game.duck()
        self.assertEqual(self.game.ducking, 8)
        self.game.jump()
        self.assertEqual(self.game.ducking, 0)
        self.game.step()
        vorher = self.game.vy
        self.game.duck()
        self.assertAlmostEqual(self.game.vy, vorher - .9)

    def test_mega_sprung_verstaerkt_beide_spruenge_um_45_prozent(self):
        game = Game(Settings(mega_jump=True), seed=0)
        for impulse in (1.55, 1.35):
            game.jump()
            self.assertAlmostEqual(game.vy, impulse * 1.45)
        game.jump()
        self.assertEqual(game.jumps, 2)

    def test_tote_runde_bleibt_bei_aktionen_und_ticks_unveraendert(self):
        self.game.dead = True
        vorher = self.game.snapshot()
        self.game.jump()
        self.game.duck()
        self.game.shoot()
        self.game.step()
        self.assertEqual(self.game.snapshot(), vorher)
        self.assertEqual(self.game.drain_events(), [])

    def test_tempo_skaliert_und_bleibt_langfristig_begrenzt(self):
        self.game.step()
        normaltempo = self.game.speed
        for faktor in (.5, .75, 1.35, 1.75, 2.):
            game = Game(Settings(tempo=faktor), seed=0)
            game.step()
            self.assertAlmostEqual(game.speed, normaltempo * faktor)
            game.dist = 10**6
            game.step()
            self.assertGreater(game.speed, normaltempo * faktor)
            self.assertLess(game.speed, 3 * faktor)

    def test_spawn_messung_400_ticks(self):
        for preset, erwartet in (("leicht", 8), ("irre", 31)):
            with self.subTest(preset=preset):
                settings = Settings()
                settings.preset(preset)
                game = Game(settings, Geometry(80, 20), seed=0)
                fortschalten(game, 400)
                self.assertEqual(game.spawned, erwartet)

    def test_dichte_erhoeht_spawnanzahl_bei_gleichem_tempo(self):
        anzahl = []
        for dichte in ("wenig", "normal", "viele", "extrem"):
            game = Game(Settings(density=dichte), seed=42)
            fortschalten(game, 2000)
            anzahl.append(game.spawned)
        self.assertEqual(anzahl, sorted(set(anzahl)))

    def test_ereignisse_werden_genau_einmal_abgeholt(self):
        self.game.jump()
        self.game.shoot()
        vorher = self.game.snapshot()
        self.assertEqual(self.game.drain_events(), ["jump", "piu"])
        self.assertEqual(self.game.drain_events(), [])
        self.assertEqual(self.game.snapshot(), vorher)

    def test_globaler_zufall_beeinflusst_runden_nicht(self):
        andere = Game(seed=0)
        globaler_zustand = random.getstate()
        try:
            with patch.object(self.game, "_player_hits"), patch.object(andere, "_player_hits"):
                for tick in range(200):
                    aktionen(self.game, tick)
                    self.game.step()
                    random.seed(tick)
                    random.random()
                    aktionen(andere, tick)
                    andere.step()
                    andere.drain_events()
        finally:
            random.setstate(globaler_zustand)
        self.assertEqual(self.game.snapshot()["state"], andere.snapshot()["state"])
        self.assertEqual(self.game.rng.getstate(), andere.rng.getstate())

    def test_resize_bereinigt_unsichtbare_objekte(self):
        self.game.on_resize(Geometry(200, 44))
        self.game.obs = [hindernis(190), hindernis(20)]
        self.game.bul = [[190., 37], [20., 37]]
        self.game.y, self.game.jumps = 25., 2
        self.game.on_resize(Geometry(46, 14))
        self.assertEqual(len(self.game.obs), 1)
        self.assertEqual(len(self.game.bul), 1)
        self.assertLess(self.game.bul[0][1], self.game.geometry.ground)
        self.assertEqual((self.game.y, self.game.jumps), (0, 0))


class MunitionTests(unittest.TestCase):
    def test_jedes_magazin_leert_sich_und_blockiert_weiteren_schuss(self):
        for magazin in (1, 6, 8, 10, 15, 30):
            with self.subTest(magazin=magazin):
                game = Game(Settings(magazine=magazin), seed=0)
                for _ in range(magazin):
                    game.shoot()
                self.assertEqual((game.ammo, len(game.bul), game.reload_t), (0, magazin, 5.))
                game.shoot()
                self.assertEqual(len(game.bul), magazin)
                self.assertIn("click", game.drain_events())

    def test_normaler_reload_ist_genau_90_ticks(self):
        game = Game(Settings(magazine=1), seed=0)
        game.shoot()
        fortschalten(game, 89)
        self.assertEqual(game.ammo, 0)
        fortschalten(game, 1)
        self.assertEqual((game.ammo, game.reload_t, game.mag_t), (1, 0, 30.))
        self.assertEqual(game.drain_events().count("reload_done"), 1)
        fortschalten(game, 1)
        self.assertNotIn("reload_done", game.drain_events())

    def test_schneller_reload_erst_nach_sieben_ticks(self):
        game = Game(Settings(instant_reload=True, magazine=1), seed=0)
        game.shoot()
        self.assertEqual(game.reload_t, .35)
        fortschalten(game, 6)
        self.assertEqual(game.ammo, 0)
        fortschalten(game, 1)
        self.assertEqual((game.ammo, game.reload_t), (1, 0))

    def test_magazinfenster_fuellt_nach_540_ticks(self):
        game = Game(Settings(magazine=15), seed=0)
        game.shoot()
        fortschalten(game, int(30 * FPS) - 1)
        self.assertEqual(game.ammo, 14)
        fortschalten(game, 1)
        self.assertEqual(game.ammo, 15)
        self.assertEqual(game.drain_events().count("reload_done"), 1)

    def test_volles_magazin_erzeugt_keinen_reloadton(self):
        game = Game(seed=0)
        fortschalten(game, 540)
        self.assertNotIn("reload_done", game.drain_events())

    def test_unendlich_munition_mit_beiden_reloadvarianten(self):
        for schnell in (False, True):
            game = Game(Settings(infinite_ammo=True, instant_reload=schnell, magazine=6), seed=0)
            for _ in range(100):
                game.shoot()
            self.assertEqual((game.ammo, len(game.bul), game.reload_t), (6, 100, 0))
            game.step()
            self.assertEqual(game.mag_t, 30.)
            self.assertNotIn("empty", game.drain_events())


class KollisionTests(unittest.TestCase):
    def test_bodenkollision_toetet_und_sprung_rettet(self):
        for hoehe, tot in ((0., True), (5., False)):
            game = Game(seed=0)
            game.y = hoehe
            game.obs = [hindernis(game.geometry.player_x + 1)]
            game._player_hits()
            self.assertEqual(game.dead, tot)

    def test_entferntes_hindernis_toetet_nicht(self):
        game = Game(seed=0)
        game.obs = [hindernis(70)]
        game._player_hits()
        self.assertFalse(game.dead)

    def test_unverwundbarkeit_zerplatzt_alle_beruehrten_hindernisse(self):
        game = Game(Settings(invincible=True), seed=0)
        entfernt = hindernis(70)
        game.obs = [hindernis(game.geometry.player_x), hindernis(game.geometry.player_x), entfernt]
        game._player_hits()
        self.assertFalse(game.dead)
        self.assertEqual(game.obs, [entfernt])
        self.assertEqual((game.kills, len(game.parts)), (2, 14))

    def test_doppelte_punkte_beinhalten_entfernung_und_kill_im_selben_tick(self):
        for doppelt, erwartet in ((False, 35), (True, 70)):
            game = Game(Settings(invincible=True, double_points=doppelt), seed=0)
            game.dist = 30
            game.obs = [hindernis(game.geometry.player_x + 1)]
            game.step()
            self.assertEqual((game.kills, game.score), (1, erwartet))

    def test_zwei_projektile_zaehlen_ein_ziel_nur_einmal(self):
        game = Game(seed=0)
        game.obs = [hindernis(20)]
        game.bul = [[19., game.geometry.ground - 1], [19., game.geometry.ground - 1]]
        game.step()
        self.assertEqual((len(game.obs), game.kills, len(game.bul)), (0, 1, 1))
        self.assertEqual(game.drain_events().count("kill"), 1)

    def test_bodenschuss_verfehlt_flugziel(self):
        game = Game(seed=0)
        game.obs = [hindernis(20, offset=4)]
        game.bul = [[19., game.geometry.ground - 1]]
        game.step()
        self.assertEqual((len(game.obs), game.kills), (1, 0))

    def test_schnelle_kreuzung_trifft_auch_ohne_ueberlappende_endpunkte(self):
        game = Game(Settings(tempo=2.), seed=0)
        game.dist = 10**6
        game.obs = [hindernis(14)]
        game.bul = [[10., game.geometry.ground - 1]]
        game.step()
        self.assertEqual((len(game.obs), game.kills, len(game.bul)), (0, 1, 0))


class GrafikdatenTests(unittest.TestCase):
    def test_alle_posen_haben_einheitliche_breite(self):
        for satz in (HERO_ASCII, HERO_KAO):
            for posen in satz.values():
                for pose in posen:
                    self.assertEqual(len(pose), HERO_W)

    def test_ascii_posen_enthalten_nur_ascii(self):
        self.assertTrue(all(pose.isascii() for posen in HERO_ASCII.values() for pose in posen))

    def test_katalog_strukturell_gueltig_und_im_kleinsten_feld_sichtbar(self):
        for art, animation, artname, offsets, level, gewicht in CATALOG:
            with self.subTest(art=artname, grafik=art):
                self.assertTrue(art)
                self.assertTrue(all(isinstance(zeile, str) and zeile for zeile in art))
                self.assertIn(artname, ("solid", "bird", "word"))
                self.assertGreater(gewicht, 0)
                self.assertGreaterEqual(level, 0)
                self.assertLess(len(art) + max(offsets), Geometry(46, 14).ground)
                if animation:
                    self.assertEqual(len(animation), len(art))

    def test_hindernisgenerator_nutzt_uebergebenen_rng(self):
        links, rechts = random.Random(12), random.Random(12)
        for level in range(8):
            for _ in range(30):
                self.assertEqual(make_obstacle(level, links), make_obstacle(level, rechts))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(Settings(invincible=True), Geometry(80, 20), seed=0)

    def test_json_roundtrip_setzt_runde_exakt_fort(self):
        for tick in range(170):
            aktionen(self.game, tick)
            self.game.step()
            self.game.drain_events()
        daten = json.loads(json.dumps(self.game.snapshot(), allow_nan=False))
        geladen = Game.from_snapshot(daten)
        self.assertEqual(geladen.snapshot(), self.game.snapshot())
        for tick in range(170, 600):
            aktionen(self.game, tick)
            aktionen(geladen, tick)
            self.game.step()
            geladen.step()
            self.assertEqual(geladen.drain_events(), self.game.drain_events())
        self.assertEqual(geladen.snapshot(), self.game.snapshot())

    def test_reload_und_sprung_ueberstehen_roundtrip(self):
        game = Game(Settings(magazine=1, instant_reload=True), seed=4)
        game.shoot()
        game.jump()
        game.step()
        geladen = Game.from_snapshot(json.loads(json.dumps(game.snapshot())))
        fortschalten(game, 6)
        fortschalten(geladen, 6)
        self.assertEqual(geladen.snapshot(), game.snapshot())
        self.assertEqual(geladen.ammo, 1)

    def test_snapshot_und_geladene_runde_teilen_keine_listen(self):
        self.game.obs = [hindernis(60)]
        daten = self.game.snapshot()
        geladen = Game.from_snapshot(daten)
        daten["state"]["obs"][0]["art"][0] = "kaputt"
        geladen.obs[0]["x"] = 20
        self.assertEqual(self.game.obs[0]["art"], ["###"])
        self.assertEqual(self.game.obs[0]["x"], 60)
        self.assertEqual(geladen.obs[0]["art"], ["###"])

    def test_ereignisse_werden_nicht_erneut_abgespielt(self):
        self.game.jump()
        geladen = Game.from_snapshot(self.game.snapshot())
        self.assertEqual(geladen.drain_events(), [])

    def test_tote_runde_bleibt_nach_laden_tot(self):
        self.game.dead = True
        geladen = Game.from_snapshot(self.game.snapshot())
        vorher = geladen.snapshot()
        geladen.step()
        self.assertEqual(geladen.snapshot(), vorher)

    def test_beschaedigte_skalarwerte_werden_abgelehnt(self):
        for feld, werte in {"y": (-1, float("nan"), float("inf")), "jumps": (3, True, 1.5),
                            "ammo": (-1, 31), "reload_t": (6,), "mag_t": (31,),
                            "score": (1, -1), "dead": (1, "nein"),
                            "msg": ("\x1b[2J", "x" * 101), "cheated": (False,)}.items():
            for wert in werte:
                with self.subTest(feld=feld, wert=wert):
                    daten = self.game.snapshot()
                    daten["state"][feld] = wert
                    with self.assertRaises(ValueError):
                        Game.from_snapshot(daten)

    def test_fehlende_felder_falsche_version_und_falsche_wurzel(self):
        for daten in (None, [], {}, {"version": 99}):
            with self.subTest(daten=daten), self.assertRaises(ValueError):
                Game.from_snapshot(daten)
        for feld in ("geometry", "settings", "rng", "run_id", "state"):
            daten = self.game.snapshot()
            del daten[feld]
            with self.subTest(feld=feld), self.assertRaises(ValueError):
                Game.from_snapshot(daten)

    def test_beschaedigte_rng_zustaende_werden_abgelehnt(self):
        original = json.loads(json.dumps(self.game.snapshot()))
        for rng in (None, [], [3, [], None], [2, original["rng"][1], None],
                    [3, original["rng"][1], .1]):
            daten = deepcopy(original)
            daten["rng"] = rng
            with self.subTest(rng_typ=type(rng).__name__), self.assertRaises(ValueError):
                Game.from_snapshot(daten)
        for index, wert in ((0, -1), (0, True), (624, 625)):
            daten = deepcopy(original)
            daten["rng"][1][index] = wert
            with self.assertRaises(ValueError):
                Game.from_snapshot(daten)

    def test_beschaedigte_objekte_werden_abgelehnt(self):
        for feld, wert in (("obs", [{}]), ("bul", [[1]]), ("clouds", [[1, "oben"]]),
                           ("bg", [[1, 2, "\n"]]), ("parts", [[1, 2, 0, 0, 0, "*"]]),
                           ("bul", [[1, 2]] * 1001)):
            daten = self.game.snapshot()
            daten["state"][feld] = wert
            with self.subTest(feld=feld), self.assertRaises(ValueError):
                Game.from_snapshot(daten)

    def test_hindernisgroesse_muss_zur_grafik_passen(self):
        for feld, wert in (("w", 8), ("h", 3), ("art", []), ("kind", "unbekannt"),
                           ("art2", ["#", "#"]), ("off", -1)):
            daten = self.game.snapshot()
            objekt = hindernis(60)
            objekt[feld] = wert
            daten["state"]["obs"] = [objekt]
            with self.subTest(feld=feld), self.assertRaises(ValueError):
                Game.from_snapshot(daten)


if __name__ == "__main__":
    unittest.main()
