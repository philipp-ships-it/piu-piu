"""Diagnosefehler, ASCII-Raster und Plattformadapter ohne echte Eingabegeräte."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from piu.app import main
from piu.diagnostics import diagnose
from piu.terminal import Audio, Keys, Terminal, TerminalError


class DiagnoseTests(unittest.TestCase):
    def test_diagnose_prueft_schreibzugriff_ohne_profil(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report, code = diagnose(folder)
            self.assertEqual(code, 0)
            self.assertIn("Schreibzugriff: OK", report)
            self.assertEqual(list(folder.iterdir()), [])

    def test_diagnose_schreibfehler_hat_status_drei(self):
        with patch("piu.diagnostics.tempfile.TemporaryFile", side_effect=PermissionError("gesperrt")):
            with tempfile.TemporaryDirectory() as directory:
                report, code = diagnose(Path(directory))
            self.assertEqual(code, 3)
            self.assertIn("--data-dir", report)

    def test_cli_diagnose_speichert_keine_settings(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--diagnose", "--data-dir", directory]), 0)
            self.assertFalse((Path(directory) / "profile.json").exists())

    def test_cli_terminalfehler_wird_erklaert(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch("piu.app.Terminal", side_effect=TerminalError("Keine Eingabe")), redirect_stderr(output):
                self.assertEqual(main(["--data-dir", directory, "--silent"]), 3)
            self.assertIn("Keine Eingabe", output.getvalue())
            self.assertIn("FEHLERBEHEBUNG", output.getvalue())

    def test_ascii_ausgabe_bleibt_gleich_breit(self):
        terminal = Terminal(ascii_only=True)
        terminal.write = Mock()
        terminal.show("| Grüße: älter, größer! |")
        rendered = terminal.write.call_args.args[0].removeprefix("\033[H")
        self.assertTrue(rendered.isascii())
        self.assertEqual(len(rendered), len("| Grüße: älter, größer! |"))

    def test_windows_pfeiltasten_und_strg_c(self):
        for raw, expected in ((b"H", "jump"), (b"P", "duck"), (b"K", "left"), (b"M", "right")):
            keys = Keys.__new__(Keys)
            keys.ok = keys._win = True
            keys._m = Mock()
            keys._m.getch.side_effect = [b"\xe0", raw]
            self.assertEqual(keys.get(menu=True), expected)

    def test_eingabefehler_ist_keine_stumme_endlosschleife(self):
        keys = Keys.__new__(Keys)
        keys.ok = keys._win = True
        keys._m = Mock()
        keys._m.kbhit.side_effect = OSError("getrennt")
        with self.assertRaises(TerminalError):
            keys.get()

    def test_stummer_sound_startet_keinen_hintergrundthread(self):
        with patch("piu.terminal.Thread") as thread:
            audio = Audio(silent=True)
            audio.play(["jump", "piu"])
            audio.close()
            thread.assert_not_called()


if __name__ == "__main__":
    unittest.main()
