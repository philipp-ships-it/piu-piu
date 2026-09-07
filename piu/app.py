"""Anwendungsablauf: Menüs, feste Spieltakte und sichere Speicherzeitpunkte."""
import argparse
import logging
import math
import os
from pathlib import Path
import sys
import time

from . import __version__
from .diagnostics import configure_logging, diagnose
from .engine import Game
from .geometry import Geometry, MIN_W, MIN_H
from .menu import Menu
from .rendering import draw_confirm, draw_game, draw_gameover, draw_message, draw_settings, draw_start
from .settings import Settings, FPS
from .storage import Store, StorageError, clean_name
from .terminal import Terminal, TerminalError, Audio
from .timing import FixedClock

AUTOSAVE_TICKS = int(FPS * 5)
LOGGER = logging.getLogger(__name__)


def parse_size(value):
    try:
        width, height = value.lower().split("x")
        return Geometry(int(width), int(height))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Größe als BREITExHOEHE, z. B. 80x20 (46x14 bis 200x44).") from exc


def parse_speed(value):
    try:
        speed = float(value)
        if not math.isfinite(speed) or not .5 <= speed <= 2:
            raise ValueError
        return speed
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tempo muss zwischen 0.5 und 2.0 liegen.") from exc


def parser():
    ap = argparse.ArgumentParser(description="PIU PIU – ASCII-Endlosrunner", epilog="Hilfe bei Fehlern: handbuch/FEHLERBEHEBUNG.md")
    ap.add_argument("--silent", action="store_true", help="ohne Sound")
    ap.add_argument("--ascii", action="store_true", help="ausschließlich ASCII-Zeichen")
    ap.add_argument("--speed", type=parse_speed, help="gespeichertes Tempo überschreiben (0.5 bis 2.0)")
    ap.add_argument("--size", type=parse_size, help="feste Spielfeldgröße, z. B. 80x20")
    ap.add_argument("--name", help="gespeicherten Spielernamen überschreiben")
    ap.add_argument("--data-dir", type=Path, help="eigener Ordner für Profil, Backup und Protokoll")
    ap.add_argument("--scores", action="store_true", help="Highscores anzeigen")
    ap.add_argument("--demo", type=int, default=0, metavar="FRAMES", help="deterministische Demo ohne Profilzugriff")
    ap.add_argument("--seed", type=int, default=0, help="Zufallsstartwert für die Demo (Standard: 0)")
    ap.add_argument("--diagnose", action="store_true", help="Python, Terminal und Datenordner prüfen")
    ap.add_argument("--version", action="version", version="PIU PIU " + __version__)
    return ap


class Application:
    """Verbindet reine Spielfunktionen mit austauschbaren I/O-Adaptern."""
    def __init__(self, args, store, terminal, audio, clock=time.monotonic, sleep=time.sleep):
        self.args, self.store, self.terminal, self.audio = args, store, terminal, audio
        self.clock, self.sleep = clock, sleep
        self.geometry = args.size or Geometry()
        self.game = None
        self.failed_save = False

    def viewport(self):
        if self.args.size:
            return True
        try:
            columns, lines = os.get_terminal_size()
        except OSError:
            columns, lines = 80, 24
        self.geometry = Geometry.fit(columns, lines)
        return columns >= MIN_W + 1 and lines >= MIN_H + 1

    def message(self, title, text, footer="ENTER: Weiter  Q: Ende"):
        """Hinweisbildschirm pausiert die Simulation und unterstützt Q zuverlässig."""
        while True:
            self.viewport()
            self.terminal.show(draw_message(self.geometry, title, text, footer))
            key = self.terminal.keys.get(menu=True)
            if key == "quit":
                return False
            if key in ("shoot", "back", "pause"):
                return True
            self.sleep(.03)

    def write_safely(self, operation):
        """Bei einem Schreibfehler keine Erfolgsmeldung; Wiederholung bewusst anbieten."""
        while True:
            try:
                result = operation()
                self.failed_save = False
                return True, result
            except StorageError as exc:
                LOGGER.warning("Speicheroperation fehlgeschlagen: %s", exc)
                self.failed_save = True
                if not self.message("SPEICHERFEHLER", str(exc), "ENTER: Erneut versuchen  Q: Ohne Speichern"):
                    return False, None

    def save_current(self):
        if self.game is not None:
            if self.game.dead:
                return self.write_safely(lambda: self.store.finish(self.game, self.store.player_name))[0]
            return self.write_safely(lambda: self.store.remember(self.game))[0]
        return self.write_safely(self.store.save)[0]

    def menu(self):
        menu = Menu(self.store.settings, self.store.checkpoint is not None)
        tick = 0
        while True:
            if not self.viewport():
                self.terminal.show(draw_message(self.geometry, "TERMINAL ZU KLEIN", "Bitte auf mindestens 47 Spalten und 15 Zeilen vergrößern.", "Q: Ende"))
                if self.terminal.keys.get(menu=True) == "quit":
                    return "quit"
                self.sleep(.1)
                continue
            if menu.screen == "settings":
                view = draw_settings(menu.settings, self.geometry, menu.selected)
            elif menu.screen == "confirm":
                view = draw_confirm(menu, self.geometry)
            else:
                view = draw_start(menu, self.geometry, self.store.best, tick, self.args.ascii)
            self.terminal.show(view)
            action = menu.handle(self.terminal.keys.get(menu=True))
            if action == "changed":
                if not self.write_safely(self.store.save)[0]:
                    return "quit"
            elif action in ("start", "resume", "quit"):
                return action
            tick += 1
            self.sleep(.055)

    def play(self):
        """18 feste Takte pro Sekunde; Rendern, Pause und Eingabe laufen getrennt."""
        g = self.game
        timer = FixedClock(self.clock())
        while not g.dead:
            if not self.viewport():
                self.terminal.show(draw_message(self.geometry, "PAUSE // FENSTER ZU KLEIN", "Fenster vergrößern. Die Runde wartet.", "Q: Speichern und Ende"))
                if self.terminal.keys.get() == "quit":
                    self.save_current()
                    return "quit"
                timer.reset(self.clock())
                self.sleep(.1)
                continue
            if g.geometry != self.geometry:
                g.on_resize(self.geometry)
            # Pro Durchlauf begrenzen: Tastaturwiederholung darf keinen Takt verhungern lassen.
            for _ in range(16):
                key = self.terminal.keys.get()
                if key is None:
                    break
                if key in ("jump", "duck", "shoot"):
                    getattr(g, key)()
                elif key == "quit":
                    self.save_current()
                    return "quit"
                elif key == "pause":
                    if not self.save_current():
                        return "quit"
                    if not self.message("P A U S E", "Rundenstand gespeichert.\nKurz durchatmen. Das nächste piu wartet.", "P/ENTER: Weiter  Q: Speichern und Ende"):
                        return "quit"
                    timer.reset(self.clock())
            ticks = timer.consume(self.clock())
            for _ in range(ticks):
                g.step()
                if g.dead:
                    break
                if g.t % AUTOSAVE_TICKS == 0:
                    if not self.save_current():
                        return "quit"
                    # Speicherdauer zählt nicht als nachzuholende Spielzeit.
                    timer.reset(self.clock())
            self.audio.play(g.drain_events())
            if ticks:
                self.terminal.show(draw_game(g, self.store.best, self.args.ascii))
            self.sleep(.005)
        return "over"

    def run(self):
        try:
            for warning in self.store.warnings:
                if not self.message("PROFILHINWEIS", warning):
                    return 0
            # Ein beim letzten Schreibversuch beendeter Lauf wird einmalig abgeschlossen.
            if self.store.checkpoint is not None:
                recovered = Game.from_snapshot(self.store.checkpoint)
                if recovered.dead:
                    if not self.write_safely(lambda: self.store.finish(recovered, self.store.player_name))[0]:
                        return 3
            while True:
                action = self.menu()
                if action == "quit":
                    return 3 if self.failed_save else 0
                if action == "resume":
                    self.game = Game.from_snapshot(self.store.checkpoint)
                else:
                    self.game = Game(self.store.settings, self.geometry)
                if self.game.geometry != self.geometry:
                    self.game.on_resize(self.geometry)
                if not self.save_current():
                    return 3
                self.audio.play(["start"])
                if self.play() == "quit":
                    return 3 if self.failed_save else 0
                self.audio.play(["hit"])
                ok, result = self.write_safely(lambda: self.store.finish(self.game, self.store.player_name))
                if not ok:
                    return 3
                rank, improved = result
                while True:
                    self.viewport()
                    self.game.geometry = self.geometry
                    self.terminal.show(draw_gameover(self.game, self.store.scores, rank, improved, ascii_only=self.args.ascii))
                    key = self.terminal.keys.get(menu=True)
                    if key == "quit":
                        return 0
                    if key == "shoot":
                        break
                    self.sleep(.05)
                self.game = None
        except KeyboardInterrupt:
            return 0 if self.save_current() else 3


def run_demo(args):
    """Ohne Konsole, Ton, Sleeps oder Dateizugriffe bis zur Framegrenze simulieren."""
    settings = Settings()
    if args.speed is not None:
        settings.tempo = args.speed
    g = Game(settings, args.size, args.seed)
    for frame in range(args.demo):
        for obj in g.obs:
            distance = obj["x"] - g.geometry.player_x
            if obj["kind"] == "bird" and 8 < distance < 26 and frame % 4 == 0:
                g.shoot()
            elif 6 < distance < 13 and g.y < .2:
                g.jump()
        g.step()
        g.drain_events()
        if g.dead:
            break
    print(draw_game(g, ascii_only=args.ascii))
    print("Demo OK: Frames=%d Punkte=%d Kills=%d Beendet=%s" % (g.t, g.score, g.kills, g.dead))
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    if args.demo < 0:
        parser().error("--demo benötigt eine positive Framezahl.")
    if args.demo:
        return run_demo(args)
    store = Store(args.data_dir)
    if args.diagnose:
        report, code = diagnose(store.directory)
        print(report)
        return code
    handler = None
    try:
        with store.locked():
            handler = configure_logging(store.directory)
            root = Path(__file__).resolve().parent.parent
            legacy_root = Path(sys.executable).parent if getattr(sys, "frozen", False) else root
            store.load([legacy_root / "piu_highscores.json", legacy_root / "piuu_highscores.json"])
            if args.scores:
                for warning in store.warnings:
                    print("Hinweis: " + warning)
                for index, entry in enumerate(store.scores, 1):
                    print("%2d. %-14s %7d (%d Läufe)" % (index, entry["name"], entry["score"], entry["runs"]))
                if not store.scores:
                    print("Noch keine Highscores. Spiel eine Runde ohne Cheats.")
                return 0
            store.player_name = clean_name(args.name or (store.player_name if store.path.exists() else os.environ.get("USERNAME", os.environ.get("USER", "Piu"))))
            if args.speed is not None:
                store.settings.tempo = args.speed
                store.settings.difficulty = "eigen"
            store.save()
            audio = Audio(args.silent)
            try:
                with Terminal(ascii_only=args.ascii) as terminal:
                    app = Application(args, store, terminal, audio)
                    try:
                        return app.run()
                    except Exception:
                        # Bestmögliche Rettung ohne den ursprünglichen Fehler zu verdecken.
                        if app.game is not None:
                            try:
                                store.remember(app.game)
                            except StorageError:
                                LOGGER.exception("Notfallspeicherung fehlgeschlagen.")
                        raise
            finally:
                audio.close()
    except (StorageError, TerminalError, OSError) as exc:
        LOGGER.error("Betriebsfehler: %s", exc)
        print("PIU PIU: " + str(exc), file=sys.stderr)
        print("Hilfe: handbuch/FEHLERBEHEBUNG.md | Diagnose: python piuu.py --diagnose", file=sys.stderr)
        return 3
    except Exception:
        LOGGER.exception("Unerwarteter Programmfehler.")
        print("PIU PIU: Unerwarteter Fehler. Details: " + str(store.directory / "piu.log"), file=sys.stderr)
        return 1
    finally:
        if handler is not None:
            logging.getLogger("piu").removeHandler(handler)
            handler.close()
