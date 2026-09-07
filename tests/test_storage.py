"""Persistenz-QA mit temporären Profilen und gezielt simulierten Schreibfehlern."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from piu.engine import Game
from piu.settings import CHEATS, PRESETS, Settings
from piu.storage import MAX_BYTES, StorageError, Store, clean_name, normalize_scores


def beendete_runde(punkte=100, settings=None):
    """Eine konsistente beendete Runde ohne Terminal und ohne Wartezeit."""
    game = Game(settings=settings, seed=0)
    faktor = 2 if game.settings.double_points else 1
    game.dist = punkte * 3 / faktor
    game.score = punkte
    game.dead = True
    return game


class ProfilTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="piu-qa-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = Store(self.directory)

    def schreibe(self, daten, path=None):
        (path or self.store.path).write_text(json.dumps(daten), encoding="utf-8")

    def test_fehlendes_profil_hat_defaults_ohne_datei_nebenwirkung(self):
        self.assertIs(self.store.load(), self.store)
        self.assertEqual(self.store.settings, Settings())
        self.assertEqual((self.store.scores, self.store.best, self.store.checkpoint), ([], 0, None))
        self.assertFalse(self.store.path.exists())

    def test_settings_und_spielername_ueberstehen_neuladen(self):
        self.store.settings.preset("schwer")
        self.store.settings.mega_jump = True
        self.store.player_name = "Jörg"
        self.store.save()
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.settings, self.store.settings)
        self.assertEqual(geladen.player_name, "Jörg")
        self.assertEqual(geladen.warnings, [])

    def test_remember_sichert_komplette_runde_ohne_highscore(self):
        game = Game(Settings(invincible=True, mega_jump=True), seed=2)
        game.jump()
        game.shoot()
        for _ in range(60):
            game.step()
        self.store.remember(game)
        geladen = Store(self.directory).load()
        fortgesetzt = Game.from_snapshot(geladen.checkpoint)
        self.assertEqual(fortgesetzt.snapshot(), game.snapshot())
        self.assertEqual(geladen.scores, [])
        for _ in range(100):
            game.step()
            fortgesetzt.step()
        self.assertEqual(fortgesetzt.snapshot(), game.snapshot())

    def test_remember_kopiert_rundenstand(self):
        game = Game(seed=0)
        self.store.remember(game)
        game.jump()
        game.step()
        self.assertEqual(self.store.checkpoint["state"]["t"], 0)
        self.assertEqual(Store(self.directory).load().checkpoint["state"]["t"], 0)

    def test_finish_speichert_score_und_entfernt_checkpoint(self):
        game = beendete_runde(300)
        self.store.remember(game)
        self.assertEqual(self.store.finish(game, "QA"), (1, True))
        geladen = Store(self.directory).load()
        self.assertIsNone(geladen.checkpoint)
        self.assertEqual(geladen.last_run_id, game.run_id)
        self.assertEqual((geladen.best, geladen.scores[0]["runs"]), (300, 1))

    def test_finish_ist_auch_nach_neuladen_idempotent(self):
        game = beendete_runde()
        self.store.finish(game, "QA")
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.finish(game, "QA"), (1, False))
        self.assertEqual(geladen.scores[0]["runs"], 1)
        self.assertEqual(Store(self.directory).load().scores[0]["runs"], 1)

    def test_laufende_runde_darf_nicht_abgeschlossen_werden(self):
        with self.assertRaises(ValueError):
            self.store.finish(Game(seed=0), "QA")
        self.assertFalse(self.store.path.exists())

    def test_niedrigere_und_gleiche_scores_erhoehen_nur_laufzaehler(self):
        self.store.finish(beendete_runde(300), "QA")
        for punkte in (100, 300):
            self.assertEqual(self.store.finish(beendete_runde(punkte), "qa"), (1, False))
        self.assertEqual(len(self.store.scores), 1)
        self.assertEqual((self.store.scores[0]["score"], self.store.scores[0]["runs"]), (300, 3))
        self.assertEqual(self.store.finish(beendete_runde(600), "Qa"), (1, True))
        self.assertEqual(self.store.scores[0]["runs"], 4)

    def test_alle_schwierigkeiten_zaehlen_normal(self):
        for name in (*PRESETS, "eigen"):
            with self.subTest(name=name):
                settings = Settings()
                if name == "eigen":
                    settings.adjust("tempo", 1)
                else:
                    settings.preset(name)
                rank, verbessert = self.store.finish(beendete_runde(120, settings), name)
                self.assertIsNotNone(rank)
                self.assertTrue(verbessert)
        self.assertEqual(len(Store(self.directory).load().scores), 5)

    def test_alle_31_cheatkombinationen_lassen_highscores_unveraendert(self):
        self.store.finish(beendete_runde(100), "QA")
        vorher = deepcopy(self.store.scores)
        for werte in itertools.product((False, True), repeat=5):
            if not any(werte):
                continue
            with self.subTest(cheats=werte):
                settings = Settings(**dict(zip((feld for feld, _ in CHEATS), werte)))
                game = beendete_runde(99900, settings)
                self.store.remember(game)
                self.assertEqual(self.store.finish(game, "QA"), (None, False))
                self.assertEqual(self.store.scores, vorher)
                geladen = Store(self.directory).load()
                self.assertEqual(geladen.scores, vorher)
                self.assertIsNone(geladen.checkpoint)
                self.assertEqual(geladen.last_run_id, game.run_id)

    def test_top_zehn_und_rang_fuer_nicht_platzierte(self):
        for index in range(12):
            self.store.finish(beendete_runde(100 + index), f"Spieler{index}")
        self.assertEqual(len(self.store.scores), 10)
        self.assertEqual(self.store.best, 111)
        rank, _ = self.store.finish(beendete_runde(1), "Schlusslicht")
        self.assertIsNone(rank)
        self.assertEqual(len(Store(self.directory).load().scores), 10)

    def test_backup_enthaelt_den_vorherigen_gueltigen_stand(self):
        self.store.save()
        vorher = self.store.path.read_bytes()
        self.store.settings.preset("irre")
        self.store.save()
        self.assertEqual(self.store.backup.read_bytes(), vorher)
        self.assertEqual(Store(self.directory).load().settings.difficulty, "irre")

    def test_replace_fehler_erhaelt_profildatei_und_entfernt_temporaerdatei(self):
        self.store.save()
        vorher = self.store.path.read_bytes()
        self.store.settings.preset("irre")
        # Der Backup-Replace gelingt; erst der eigentliche Profil-Replace scheitert.
        import os
        original = os.replace

        def ersetzen(quelle, ziel):
            if Path(ziel) == self.store.path:
                raise PermissionError("simulierter Replace-Fehler")
            return original(quelle, ziel)

        with patch("piu.storage.os.replace", side_effect=ersetzen), self.assertRaises(StorageError):
            self.store.save()
        self.assertEqual(self.store.path.read_bytes(), vorher)
        self.assertEqual(list(self.directory.glob(".piu-*.tmp")), [])
        self.assertEqual(Store(self.directory).load().settings, Settings())

    def test_fsync_fehler_erhaelt_vorherige_bytes(self):
        self.store.save()
        vorher = self.store.path.read_bytes()
        import os
        original = os.fsync
        anzahl = 0

        def synchronisieren(deskriptor):
            nonlocal anzahl
            anzahl += 1
            if anzahl == 2:
                raise OSError("simulierter Plattenfehler beim Profil nach erfolgreichem Backup")
            return original(deskriptor)

        with patch("piu.storage.os.fsync", side_effect=synchronisieren), \
                self.assertRaises(StorageError):
            self.store.save()
        self.assertEqual(anzahl, 2)
        self.assertEqual(self.store.path.read_bytes(), vorher)
        self.assertEqual(list(self.directory.glob(".piu-*.tmp")), [])

    def test_erster_speicherversuch_mit_fehler_erzeugt_keine_halbe_datei(self):
        with patch("piu.storage.os.replace", side_effect=PermissionError("simulierter Schreibschutz")), \
                self.assertRaises(StorageError):
            self.store.save()
        self.assertFalse(self.store.path.exists())
        self.assertEqual(list(self.directory.glob(".piu-*.tmp")), [])

    def test_finish_rollt_bei_speicherfehler_den_gesamten_zustand_zurueck(self):
        self.store.finish(beendete_runde(100), "QA")
        game = beendete_runde(900)
        self.store.remember(game)
        vorher = deepcopy((self.store.scores, self.store.checkpoint, self.store.last_run_id))
        vorher_bytes = self.store.path.read_bytes()
        with patch.object(self.store, "save", side_effect=StorageError("simulierter Fehler")), \
                self.assertRaises(StorageError):
            self.store.finish(game, "QA")
        self.assertEqual((self.store.scores, self.store.checkpoint, self.store.last_run_id), vorher)
        self.assertEqual(self.store.path.read_bytes(), vorher_bytes)
        self.assertEqual(self.store.finish(game, "QA"), (1, True))
        self.assertEqual(self.store.scores[0]["runs"], 2)

    def test_defektes_json_wird_gesichert_und_backup_geladen(self):
        self.store.settings.preset("leicht")
        self.store.save()
        self.store.settings.preset("irre")
        self.store.save()
        defekt = b'{"version": 1, kaputt'
        self.store.path.write_bytes(defekt)
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.settings.difficulty, "leicht")
        self.assertTrue(any("Sicherungskopie" in warnung for warnung in geladen.warnings))
        recovery = list(self.directory.glob("profile.recovery-*.json"))
        self.assertTrue(any(path.read_bytes() == defekt for path in recovery))
        geladen.save()
        self.assertEqual(Store(self.directory).load().settings.difficulty, "leicht")

    def test_beide_json_dateien_defekt_starten_mit_defaults_und_erhalten_originale(self):
        self.store.path.write_bytes(b"kaputt1")
        self.store.backup.write_bytes(b"kaputt2")
        self.store.load()
        self.assertEqual(self.store.settings, Settings())
        self.assertEqual(self.store.scores, [])
        gerettet = {path.read_bytes() for path in self.directory.glob("profile.recovery-*.json")}
        self.assertEqual(gerettet, {b"kaputt1", b"kaputt2"})

    def test_unbekannte_version_bleibt_unveraendert_auch_mit_backup(self):
        self.store.save()
        self.store.save()
        for version in (999, True, "1"):
            self.schreibe({"version": version, "future": "nicht loeschen"})
            vorher = self.store.path.read_bytes()
            with self.subTest(version=version), self.assertRaises(StorageError):
                Store(self.directory).load()
            self.assertEqual(self.store.path.read_bytes(), vorher)

    def test_typfehler_retten_gueltige_werte_und_erhalten_recovery(self):
        self.store.save()
        daten = json.loads(self.store.path.read_text(encoding="utf-8"))
        daten["settings"] = {"tempo": "schnell"}
        daten["scores"] = [{"name": "Gut", "score": 120}, {"name": "Schlecht", "score": "kaputt"}]
        daten["checkpoint"] = {"version": 1}
        self.schreibe(daten)
        vorher = self.store.path.read_bytes()
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.settings, Settings())
        self.assertEqual(geladen.best, 120)
        self.assertIsNone(geladen.checkpoint)
        self.assertEqual(len(geladen.warnings), 3)
        self.assertTrue(any(path.read_bytes() == vorher for path in self.directory.glob("profile.recovery-*.json")))

    def test_zu_grosses_profil_wird_nicht_unbegrenzt_gelesen(self):
        self.store.path.write_bytes(b" " * (MAX_BYTES + 1))
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.scores, [])
        self.assertTrue(geladen.warnings)

    def test_migration_uebernimmt_legacy_scores_nur_einmal_und_erhaelt_datei(self):
        legacy = self.directory / "alte_scores.json"
        self.schreibe([{"name": "Alt", "score": 200}, {"score": "kaputt"}], legacy)
        vorher = legacy.read_bytes()
        self.store.load(legacy_paths=(self.directory / "fehlt.json", legacy))
        self.assertEqual(self.store.best, 200)
        self.assertEqual(legacy.read_bytes(), vorher)
        self.assertTrue(self.store.path.exists())
        self.schreibe([{"name": "Neu", "score": 900}], legacy)
        self.assertEqual(Store(self.directory).load(legacy_paths=(legacy,)).best, 200)

    def test_unlesbare_legacy_datei_verhindert_naechste_migration_nicht(self):
        defekt = self.directory / "defekt.json"
        gut = self.directory / "gut.json"
        defekt.write_bytes(b"{nicht json")
        self.schreibe([{"name": "Alt", "score": 50}], gut)
        self.store.load(legacy_paths=(defekt, gut))
        self.assertEqual(self.store.best, 50)
        self.assertTrue(any("nicht lesbar" in warnung for warnung in self.store.warnings))

    def test_profil_lock_blockiert_zweite_instanz_und_wird_freigegeben(self):
        andere = Store(self.directory)
        with self.store.locked():
            with self.assertRaises(StorageError):
                with andere.locked():
                    self.fail("Zweite Instanz darf denselben Ordner nicht sperren.")
        with andere.locked():
            andere.save()
        self.assertTrue(andere.path.exists())

    def test_lock_wird_auch_bei_exception_freigegeben(self):
        with self.assertRaisesRegex(RuntimeError, "Testfehler"):
            with self.store.locked():
                raise RuntimeError("Testfehler")
        with Store(self.directory).locked():
            pass


class ScoreValidierungTests(unittest.TestCase):
    def test_namen_werden_bereinigt_begrenzt_und_fallen_auf_piu_zurueck(self):
        for eingabe, erwartet in ((None, "Piu"), ("   ", "Piu"), ("x" * 40, "x" * 14),
                                  ("  Anna   Lena  ", "Anna Lena"), ("Q\x1bA\n", "QA")):
            with self.subTest(eingabe=eingabe):
                self.assertEqual(clean_name(eingabe), erwartet)

    def test_duplikate_werden_mit_bestwert_und_summierten_laeufen_vereinigt(self):
        scores, verworfen = normalize_scores([
            {"name": "  STRASSE  ", "score": 100, "kills": 1, "runs": 2},
            {"name": "Straße", "score": 300, "kills": 5, "runs": 3},
            {"name": "andere", "score": 200}])
        self.assertEqual(verworfen, 0)
        self.assertEqual(len(scores), 2)
        self.assertEqual((scores[0]["score"], scores[0]["kills"], scores[0]["runs"]), (300, 5, 5))

    def test_ungueltige_zahlen_und_eintraege_werden_uebersprungen(self):
        ungueltig = [None, [], "text", 1]
        for feld in ("score", "kills", "runs"):
            for wert in (True, "10", None, [], -1, 1.5, float("nan"), 10**13):
                ungueltig.append({feld: wert})
        ungueltig.append({"runs": 0})
        scores, verworfen = normalize_scores(ungueltig + [{"name": "Gut", "score": 8}])
        self.assertEqual(verworfen, len(ungueltig))
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["score"], 8)

    def test_falsche_wurzel_wird_als_ungueltig_gemeldet(self):
        self.assertEqual(normalize_scores({"score": 1}), ([], 1))

    def test_laufzaehler_beim_zusammenfuehren_begrenzt_und_datum_sauber(self):
        scores, _ = normalize_scores([
            {"name": "QA", "runs": 10**12, "date": "\x1b[2J\nDatum"},
            {"name": "qa", "runs": 1}])
        self.assertEqual(scores[0]["runs"], 10**12)
        self.assertTrue(scores[0]["date"].isprintable())


if __name__ == "__main__":
    unittest.main()
