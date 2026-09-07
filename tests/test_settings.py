"""Fachregeln und Eingabevalidierung der dauerhaften Einstellungen."""
import itertools
import json
import unittest

from piu.engine import Game
from piu.settings import CHEATS, DENSITIES, PRESETS, Settings


class EinstellungenTests(unittest.TestCase):
    def test_vier_presets_setzen_alle_drei_regeln(self):
        erwartet = {"leicht": (.75, "wenig", 15), "normal": (1., "normal", 10),
                    "schwer": (1.35, "viele", 8), "irre": (1.75, "extrem", 6)}
        self.assertEqual(PRESETS, erwartet)
        for name, werte in erwartet.items():
            with self.subTest(name=name):
                settings = Settings()
                settings.preset(name)
                self.assertEqual((settings.tempo, settings.density, settings.magazine), werte)
                self.assertEqual(settings.difficulty, name)
                self.assertFalse(settings.cheats_active)

    def test_einzelwert_aendert_nur_seine_regel(self):
        for feld in ("tempo", "density", "magazine"):
            with self.subTest(feld=feld):
                settings = Settings()
                vorher = settings.to_dict()
                settings.adjust(feld, 1)
                nachher = settings.to_dict()
                self.assertEqual(nachher["difficulty"], "eigen")
                self.assertNotEqual(nachher[feld], vorher[feld])
                for anderes in vorher.keys() - {feld, "difficulty"}:
                    self.assertEqual(nachher[anderes], vorher[anderes])

    def test_zurueckstellen_eines_einzelwerts_bleibt_eigen(self):
        for feld in ("tempo", "density", "magazine"):
            settings = Settings()
            settings.adjust(feld, 1)
            settings.adjust(feld, -1)
            self.assertEqual(settings.difficulty, "eigen")
            self.assertEqual(getattr(settings, feld), getattr(Settings(), feld))

    def test_tempo_und_magazin_haben_feste_grenzen(self):
        settings = Settings()
        for richtung, tempo, magazin in ((-1, .5, 1), (1, 2., 30)):
            for _ in range(100):
                settings.adjust("tempo", richtung)
                settings.adjust("magazine", richtung)
            self.assertEqual((settings.tempo, settings.magazine), (tempo, magazin))

    def test_dichte_und_presets_rotieren(self):
        settings = Settings()
        for _ in DENSITIES:
            settings.adjust("density", 1)
        self.assertEqual(settings.density, "normal")
        settings.reset()
        for _ in PRESETS:
            settings.adjust("difficulty", -1)
        self.assertEqual(settings.difficulty, "normal")

    def test_presets_erhalten_cheats_reset_loescht_sie(self):
        settings = Settings(**{feld: True for feld, _ in CHEATS})
        settings.preset("irre")
        self.assertTrue(all(getattr(settings, feld) for feld, _ in CHEATS))
        settings.reset()
        self.assertEqual(settings, Settings())

    def test_cheats_lassen_sich_einzeln_umschalten(self):
        for feld, _ in CHEATS:
            settings = Settings()
            settings.adjust(feld, 1)
            self.assertTrue(settings.cheats_active)
            self.assertTrue(getattr(settings, feld))
            settings.adjust(feld, -1)
            self.assertFalse(settings.cheats_active)

    def test_alle_31_cheatkombinationen_markieren_die_runde(self):
        for werte in itertools.product((False, True), repeat=len(CHEATS)):
            with self.subTest(cheats=werte):
                settings = Settings(**dict(zip((feld for feld, _ in CHEATS), werte)))
                self.assertEqual(settings.cheats_active, any(werte))
                self.assertEqual(Game(settings, seed=0).cheated, any(werte))

    def test_schwierigkeitsgrade_und_eigen_sind_keine_cheats(self):
        for name in (*PRESETS, "eigen"):
            settings = Settings()
            if name == "eigen":
                settings.adjust("magazine", 1)
            else:
                settings.preset(name)
            self.assertFalse(Game(settings, seed=0).cheated)

    def test_runde_kopiert_einstellungen(self):
        settings = Settings(infinite_ammo=True)
        settings.preset("leicht")
        game = Game(settings, seed=0)
        settings.reset()
        self.assertEqual((game.sm, game.mag_size, game.settings.difficulty), (.75, 15, "leicht"))
        self.assertTrue(game.cheated)
        self.assertTrue(game.settings.infinite_ammo)

    def test_json_roundtrip_aller_presets_mit_cheats(self):
        for name in PRESETS:
            settings = Settings(mega_jump=True)
            settings.preset(name)
            self.assertEqual(Settings.from_dict(json.loads(json.dumps(settings.to_dict()))), settings)

    def test_fehlende_felder_erhalten_standardwerte(self):
        self.assertEqual(Settings.from_dict({}), Settings())
        self.assertEqual(Settings.from_dict({"magazine": 15}).difficulty, "eigen")

    def test_inkonsistenter_preset_wird_eigen(self):
        settings = Settings(difficulty="leicht", tempo=1.)
        settings.validate()
        self.assertEqual(settings.difficulty, "eigen")

    def test_ungueltige_typen_und_werte_werden_abgelehnt(self):
        faelle = {"tempo": (True, "1", None, [], float("nan"), float("inf"), .49, 2.01),
                  "magazine": (True, 1., "10", None, 0, 31),
                  "density": (None, [], "sehr viele"),
                  "difficulty": (None, [], "unmoeglich")}
        for feld, _ in CHEATS:
            faelle[feld] = (0, 1, "aus", None, [])
        for feld, werte in faelle.items():
            for wert in werte:
                with self.subTest(feld=feld, wert=wert):
                    with self.assertRaises(ValueError):
                        Settings.from_dict({feld: wert})

    def test_unbekannte_felder_und_falsche_wurzel_werden_abgelehnt(self):
        for daten in (None, [], "normal", 42, {"geheimer_cheat": True}):
            with self.subTest(daten=daten), self.assertRaises(ValueError):
                Settings.from_dict(daten)

    def test_to_dict_liefert_unabhaengige_kopie(self):
        settings = Settings()
        daten = settings.to_dict()
        daten["magazine"] = 1
        self.assertEqual(settings.magazine, 10)


if __name__ == "__main__":
    unittest.main()
