"""Anwendungsintegration mit echter Logik, Testprofil, Fake-Uhr und Tastenskript."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from piu.app import Application, main, parser
from piu.engine import Game
from piu.geometry import Geometry
from piu.menu import Menu
from piu.settings import FPS, SETTING_ROWS, Settings
from piu.storage import StorageError, Store
from piu.terminal import Keys, Terminal, TerminalError
from piu.timing import FixedClock


class FakeUhr:
    """Zeit verstreicht ausschließlich durch simulierte Warteaufrufe."""
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now

    def sleep(self, dauer):
        self.now += dauer


class Tastenskript:
    def __init__(self, tasten):
        self.tasten = iter(tasten)

    def get(self, menu=False):
        try:
            taste = next(self.tasten)
        except StopIteration as exc:
            raise AssertionError("Tastenskript aufgebraucht: unerwarteter weiterer Eingabezyklus.") from exc
        if isinstance(taste, BaseException):
            raise taste
        return taste


class FakeTerminal:
    def __init__(self, tasten):
        self.keys = Tastenskript(tasten)
        self.frames = []
        self.closed = False

    def show(self, text):
        self.frames.append(text)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True


class TaktTests(unittest.TestCase):
    def test_genau_18_takte_in_einer_sekunde(self):
        timer = FixedClock(0.)
        self.assertEqual(sum(timer.consume(index / 1000) for index in range(1, 1001)), 18)

    def test_teilzeiten_werden_aufgesammelt(self):
        timer = FixedClock()
        self.assertEqual(timer.consume(.5 / FPS), 0)
        self.assertEqual(timer.consume(1. / FPS), 1)
        self.assertEqual(timer.consume(1. / FPS), 0)

    def test_lange_haenger_holen_maximal_vier_takte_nach(self):
        timer = FixedClock()
        self.assertEqual(timer.consume(60), 4)
        self.assertEqual(timer.consume(60), 0)

    def test_pause_reset_verhindert_nachholen(self):
        timer = FixedClock()
        timer.consume(.02)
        timer.reset(60.)
        self.assertEqual(timer.consume(60.), 0)
        self.assertEqual(timer.consume(60. + 1 / FPS), 1)


class MenueTests(unittest.TestCase):
    def test_start_settings_reset_und_zurueck(self):
        menu = Menu(Settings())
        menu.handle("duck")
        menu.handle("shoot")
        self.assertEqual(menu.screen, "settings")
        self.assertEqual(menu.handle("left"), "changed")
        self.assertEqual(menu.settings.difficulty, "leicht")
        menu.selected = next(i for i, (key, _) in enumerate(SETTING_ROWS) if key == "reset")
        self.assertEqual(menu.handle("shoot"), "changed")
        self.assertEqual(menu.settings, Settings())
        menu.handle("back")
        self.assertEqual(menu.handle("shoot"), "start")

    def test_fortsetzen_ist_standardauswahl(self):
        menu = Menu(Settings(), True)
        self.assertEqual(menu.handle("shoot"), "resume")

    def test_neue_runde_braucht_bewusste_bestaetigung(self):
        menu = Menu(Settings(), True)
        menu.handle("duck")
        self.assertIsNone(menu.handle("shoot"))
        self.assertEqual((menu.screen, menu.selected), ("confirm", 0))
        self.assertIsNone(menu.handle("shoot"))
        self.assertEqual(menu.screen, "start")
        menu.handle("duck")
        menu.handle("shoot")
        menu.handle("duck")
        self.assertEqual(menu.handle("shoot"), "start")

    def test_escape_verwirft_bestaetigung_und_navigation_rotiert(self):
        menu = Menu(Settings(), True)
        menu.handle("jump")
        self.assertEqual(menu.handle("shoot"), "quit")
        menu.selected = 1
        menu.handle("shoot")
        menu.handle("back")
        self.assertEqual((menu.screen, menu.selected), ("start", 0))


class AblaufTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="piu-app-qa-")
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.store = Store(self.directory)
        self.uhr = FakeUhr()
        self.args = parser().parse_args(["--silent", "--ascii", "--size", "80x20", "--data-dir", str(self.directory)])

    def anwendung(self, tasten):
        terminal = FakeTerminal(tasten)
        app = Application(self.args, self.store, terminal, Mock(), self.uhr, self.uhr.sleep)
        return app, terminal

    def test_start_spielen_beenden_sichert_fortsetzbaren_stand(self):
        app, terminal = self.anwendung(["shoot"] + [None] * 30 + ["quit"])
        self.assertEqual(app.run(), 0)
        geladen = Store(self.directory).load()
        self.assertIsNotNone(geladen.checkpoint)
        self.assertGreater(geladen.checkpoint["state"]["t"], 0)
        self.assertFalse(geladen.checkpoint["state"]["dead"])
        self.assertTrue(terminal.frames)

    def test_pause_q_sichert_ohne_einen_simulationstakt(self):
        app, terminal = self.anwendung(["pause", None, None, "quit"])
        app.game = Game(seed=0)
        vorher = app.game.snapshot()
        self.assertEqual(app.play(), "quit")
        self.assertEqual(app.game.snapshot(), vorher)
        self.assertEqual(Game.from_snapshot(Store(self.directory).load().checkpoint).snapshot(), vorher)
        self.assertTrue(any("P A U S E" in text for text in terminal.frames))

    def test_pause_fortsetzen_holt_pausezeit_nicht_nach(self):
        app, _ = self.anwendung(["pause"] + [None] * 100 + ["shoot", None, "quit"])
        app.game = Game(seed=0)
        self.assertEqual(app.play(), "quit")
        self.assertEqual(app.game.t, 0)
        self.assertGreater(self.uhr.now, 2.9)

    def test_settingsaenderung_wird_sofort_persistent(self):
        app, _ = self.anwendung(["duck", "shoot", "left", "back", "quit"])
        self.assertEqual(app.run(), 0)
        self.assertEqual(Store(self.directory).load().settings.difficulty, "leicht")

    def test_fortsetzen_verwendet_rundensettings_statt_neuer_menuewerte(self):
        game = Game(Settings(mega_jump=True), seed=17)
        game.jump()
        game.step()
        self.store.remember(game)
        self.store.settings.preset("irre")
        self.store.save()
        app, _ = self.anwendung(["shoot", "quit"])
        self.assertEqual(app.run(), 0)
        self.assertEqual(app.game.run_id, game.run_id)
        self.assertEqual(app.game.snapshot(), game.snapshot())
        self.assertTrue(app.game.settings.mega_jump)

    def test_neue_runde_ersetzt_checkpoint_erst_nach_bestaetigung(self):
        alt = Game(seed=0)
        self.store.remember(alt)
        app, _ = self.anwendung(["duck", "shoot", "duck", "shoot", "quit"])
        self.assertEqual(app.run(), 0)
        self.assertNotEqual(app.game.run_id, alt.run_id)
        self.assertEqual(Store(self.directory).load().checkpoint["run_id"], app.game.run_id)

    def test_abbrechen_der_neuen_runde_erhaelt_checkpoint(self):
        alt = Game(seed=0)
        self.store.remember(alt)
        vorher = self.store.path.read_bytes()
        app, _ = self.anwendung(["duck", "shoot", "shoot", "quit"])
        self.assertEqual(app.run(), 0)
        self.assertEqual(self.store.path.read_bytes(), vorher)

    def test_ctrl_c_sichert_aktive_runde(self):
        app, _ = self.anwendung(["shoot", KeyboardInterrupt()])
        self.assertEqual(app.run(), 0)
        self.assertEqual(Store(self.directory).load().checkpoint["run_id"], app.game.run_id)

    def test_beendeter_checkpoint_wird_beim_start_einmalig_verbucht(self):
        game = Game(seed=0)
        game.dead = True
        self.store.remember(game)
        app, _ = self.anwendung(["quit"])
        self.assertEqual(app.run(), 0)
        geladen = Store(self.directory).load()
        self.assertIsNone(geladen.checkpoint)
        self.assertEqual(geladen.scores[0]["runs"], 1)

    def test_speicherfehler_q_gibt_fehlerstatus_statt_erfolg(self):
        app, terminal = self.anwendung(["shoot", "quit"])
        with patch.object(self.store, "save", side_effect=StorageError("Test-Schreibfehler")), \
                self.assertLogs("piu.app", level="WARNING"):
            self.assertEqual(app.run(), 3)
        self.assertTrue(any("SPEICHERFEHLER" in text for text in terminal.frames))

    def test_speicherfehler_laesst_sich_erfolgreich_wiederholen(self):
        app, _ = self.anwendung(["shoot"])
        operation = Mock(side_effect=[StorageError("kurzer Fehler"), "gespeichert"])
        with self.assertLogs("piu.app", level="WARNING"):
            self.assertEqual(app.write_safely(operation), (True, "gespeichert"))
        self.assertFalse(app.failed_save)
        self.assertEqual(operation.call_count, 2)

    def test_main_laesst_gespeicherte_settings_ohne_cli_override_bestehen(self):
        self.store.settings.preset("schwer")
        self.store.player_name = "Testperson"
        self.store.save()
        terminal = FakeTerminal(["quit"])
        audio = Mock()

        def erzeugen(args, store, konsole, sound):
            return Application(args, store, konsole, sound, self.uhr, self.uhr.sleep)

        with patch("piu.app.Terminal", return_value=terminal), patch("piu.app.Audio", return_value=audio), \
                patch("piu.app.Application", side_effect=erzeugen):
            self.assertEqual(main(["--silent", "--ascii", "--size", "80x20", "--data-dir", str(self.directory)]), 0)
        geladen = Store(self.directory).load()
        self.assertEqual(geladen.settings.difficulty, "schwer")
        self.assertEqual(geladen.player_name, "Testperson")
        self.assertTrue(terminal.closed)
        audio.close.assert_called_once()


class KommandozeilenTests(unittest.TestCase):
    def test_help_beendet_ohne_profil_oder_terminal(self):
        output = io.StringIO()
        with patch("piu.app.Store", side_effect=AssertionError("Profilzugriff")), redirect_stdout(output), \
                self.assertRaises(SystemExit) as exc:
            main(["--help"])
        self.assertEqual(exc.exception.code, 0)
        for option in ("--ascii", "--size", "--data-dir", "--demo", "--diagnose"):
            self.assertIn(option, output.getvalue())

    def test_demo_ist_deterministisch_und_profilfrei_ohne_sleeps(self):
        resultate = []
        for _ in range(2):
            output = io.StringIO()
            with patch("piu.app.Store", side_effect=AssertionError("Profilzugriff")), \
                    patch("piu.app.Terminal", side_effect=AssertionError("Terminalzugriff")), \
                    patch("piu.app.time.sleep", side_effect=AssertionError("Echte Wartezeit")), redirect_stdout(output):
                self.assertEqual(main(["--demo", "80", "--seed", "7", "--ascii", "--size", "80x20"]), 0)
            resultate.append(output.getvalue())
        self.assertEqual(resultate[0], resultate[1])
        self.assertIn("Demo OK:", resultate[0])

    def test_ungueltige_argumente_liefern_status_zwei(self):
        for argumente in (["--speed", "nan"], ["--speed", "3"], ["--size", "45x14"],
                          ["--size", "abc"], ["--demo", "-1"]):
            with self.subTest(argumente=argumente), redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as exc:
                main(argumente)
            self.assertEqual(exc.exception.code, 2)


class TerminalTests(unittest.TestCase):
    def test_tastenmapping_unterscheidet_menue_und_spiel(self):
        self.assertEqual(Keys._map(" "), "jump")
        self.assertEqual(Keys._map(" ", menu=True), "shoot")
        self.assertEqual(Keys._map("\x1b"), "quit")
        self.assertEqual(Keys._map("\x1b", menu=True), "back")
        for taste, aktion in (("W", "jump"), ("S", "duck"), ("A", "left"), ("D", "right"),
                              ("P", "pause"), ("Q", "quit"), ("\r", "shoot")):
            self.assertEqual(Keys._map(taste), aktion)

    def test_terminal_restore_auch_bei_exception(self):
        keys = Mock(ok=True)
        with patch("piu.terminal.Keys", return_value=keys), patch("piu.terminal.IS_WIN", False), \
                patch.object(Terminal, "write") as write, self.assertRaises(RuntimeError):
            with Terminal():
                raise RuntimeError("Testfehler")
        keys.restore.assert_called_once()
        self.assertIn("\x1b[?25h", write.call_args.args[0])

    def test_nicht_interaktives_terminal_wird_verstaendlich_abgelehnt(self):
        keys = Mock(ok=False)
        with patch("piu.terminal.Keys", return_value=keys), self.assertRaises(TerminalError):
            with Terminal():
                self.fail("Nicht interaktive Konsole darf nicht betreten werden.")
        keys.restore.assert_called_once()


if __name__ == "__main__":
    unittest.main()
