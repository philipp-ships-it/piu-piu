"""Veröffentlichungspaket und Dokumentlinks gegen echte Dateien prüfen."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from scripts.build_download import build, ROOT


class PaketTests(unittest.TestCase):
    def test_zip_ist_reproduzierbar_und_enthaelt_keine_nutzerdaten(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            first = build(Path(directory) / "first.zip")
            second = build(Path(directory) / "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(first) as archive:
                names = archive.namelist()
                self.assertIn("piu-piu/piuu.py", names)
                self.assertIn("piu-piu/piu/engine.py", names)
                self.assertIn("piu-piu/handbuch/FEHLERBEHEBUNG.md", names)
                self.assertFalse(any("profile" in name or "__pycache__" in name or "/tests/" in name for name in names))

    def test_entpacktes_spiel_startet_ohne_repository(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            archive_path = build(Path(directory) / "release.zip")
            # Ausschließlich das unmittelbar zuvor selbst gebaute Archiv entpacken.
            with ZipFile(archive_path) as archive:
                archive.extractall(Path(directory) / "entpackt")
            folder = Path(directory) / "entpackt" / "piu-piu"
            result = subprocess.run([sys.executable, "piuu.py", "--ascii", "--silent", "--demo", "40"],
                                    cwd=folder, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Demo OK:", result.stdout)
            self.assertFalse((folder / "profile.json").exists())

    def test_markdown_dateilinks_zeigen_auf_vorhandene_dokumente(self):
        for file in [ROOT / "README.md", *sorted((ROOT / "handbuch").glob("*.md"))]:
            for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", file.read_text(encoding="utf-8")):
                if "://" not in target:
                    self.assertTrue((file.parent / target).exists(), f"{file.name}: {target}")
