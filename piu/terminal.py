"""Plattformadapter fuer Terminaleingabe und optionalen Windows-Sound."""
import os
import sys
import time
import logging
from queue import Queue, Empty, Full
from threading import Thread
from .colors import CLEAR, HIDE, HOME, R, SHOW
IS_WIN = os.name == "nt"
try:
    import winsound
except ImportError:
    winsound = None

def beep(f, d):
    if winsound:
        try:
            winsound.Beep(int(max(37, min(32767, f))), int(max(1, d)))
        except RuntimeError:
            logging.getLogger(__name__).debug("Soundgerät nicht verfügbar.", exc_info=True)


class Snd:
    def __init__(self, silent):
        self.silent = silent

    def piu(self):
        if self.silent:
            return
        f = 1800
        for i in range(4):
            beep(f - i * 220, 9)

    def jump(self):
        if self.silent:
            return
        beep(700, 14)
        beep(1100, 14)

    def hit(self):
        if self.silent:
            return
        for f in (300, 220, 160, 110):
            beep(f, 45)

    def kill(self):
        if self.silent:
            return
        beep(900, 12)
        beep(400, 22)

    def click(self):
        if self.silent:
            return
        beep(150, 18)
        beep(90, 14)

    def empty(self):
        if self.silent:
            return
        beep(400, 40)
        beep(260, 60)

    def reload_done(self):
        if self.silent:
            return
        beep(700, 40)
        beep(1050, 55)

    def start(self):
        if self.silent:
            return
        for f in (523, 659, 784, 1046):
            beep(f, 80)


# ---------------- Tastatur ----------------
class Keys:
    def __init__(self):
        self.ok = False
        self._win = False
        self._old = None
        if not sys.stdin.isatty():
            return
        try:
            if IS_WIN:
                import msvcrt
                self._m = msvcrt
                self._win = True
                self.ok = True
            else:
                import termios
                import tty
                if sys.stdin.isatty():
                    self._t = termios
                    self._fd = sys.stdin.fileno()
                    self._old = termios.tcgetattr(self._fd)
                    tty.setcbreak(self._fd)
                    self.ok = True
        except (OSError, ValueError):
            self.ok = False

    def get(self, menu=False):
        """Spielaktionen; im Menue auch left/right/back, LEER bestaetigt."""
        if not self.ok:
            return None
        try:
            if self._win:
                if not self._m.kbhit():
                    return None
                ch = self._m.getch()
                if ch in (b"\x00", b"\xe0"):
                    c2 = self._m.getch()
                    return {b"H": "jump", b"P": "duck", b"K": "left", b"M": "right"}.get(c2)
                if ch == b"\x03":
                    return "quit"
                return self._map(ch.decode("latin-1"), menu)
            import select
            if not select.select([sys.stdin], [], [], 0)[0]:
                return None
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                if select.select([sys.stdin], [], [], 0.001)[0]:
                    sys.stdin.read(1)
                    c = sys.stdin.read(1)
                    return {"A": "jump", "B": "duck", "D": "left", "C": "right"}.get(c)
                return "back" if menu else "quit"
            if ch == "\x03":
                return "quit"
            return self._map(ch, menu)
        except (OSError, ValueError) as exc:
            raise TerminalError("Tastatur nicht lesbar. In einem interaktiven Terminal starten.") from exc

    @staticmethod
    def _map(ch, menu=False):
        ch = ch.lower()
        if ch == "\x1b":
            return "back" if menu else "quit"
        if menu and ch == " ":
            return "shoot"
        if ch in ("a", "d"):
            return "left" if ch == "a" else "right"
        if ch in (" ", "w"):
            return "jump"
        if ch in ("\r", "\n"):
            return "shoot"
        if ch == "s":
            return "duck"
        if ch == "p":
            return "pause"
        if ch == "q":
            return "quit"
        return None

    def flush(self):
        for _ in range(50):
            if self.get() is None:
                break

    def wait_any(self):
        while True:
            k = self.get()
            if k:
                return k
            time.sleep(0.03)

    def restore(self):
        if self._old is not None:
            try:
                self._t.tcsetattr(self._fd, self._t.TCSADRAIN, self._old)
            except (OSError, ValueError):
                logging.getLogger(__name__).warning("Terminalmodus konnte nicht wiederhergestellt werden.")


class TerminalError(Exception):
    """Bedienbarer Terminalfehler, den die Anwendung verständlich anzeigt."""


class Audio:
    """Begrenzte Soundwarteschlange; Beep blockiert niemals den Spieltakt."""
    def __init__(self, silent=False):
        self.sound = Snd(silent)
        self.queue = Queue(maxsize=2)
        self.thread = None
        if not silent and winsound is not None:
            self.thread = Thread(target=self._work, daemon=True, name="piu-sound")
            self.thread.start()

    def _work(self):
        while True:
            event = self.queue.get()
            if event is None:
                return
            getattr(self.sound, event)()

    def play(self, events):
        if self.thread is None:
            return
        for event in events:
            if event not in ("piu", "jump", "hit", "kill", "click", "empty", "reload_done", "start"):
                continue
            try:
                self.queue.put_nowait(event)
            except Full:
                break

    def close(self):
        if self.thread is not None:
            try:
                while True:
                    self.queue.get_nowait()
            except Empty:
                pass
            self.queue.put_nowait(None)
            self.thread.join(timeout=.5)


class Terminal:
    """Cursor und Eingabemodus auch bei Exceptions zuverlässig zurücksetzen."""
    def __init__(self, ascii_only=False):
        self.keys = None
        self.ascii_only = ascii_only

    def __enter__(self):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        self.keys = Keys()
        if not self.keys.ok:
            self.keys.restore()
            raise TerminalError("Kein interaktives Terminal. Windows Terminal öffnen oder --demo 200 verwenden.")
        try:
            if IS_WIN:
                os.system("")  # ANSI-Ausgabe in älteren Windows-Konsolen aktivieren.
            self.write(CLEAR + HIDE)
        except OSError:
            self.keys.restore()
            raise
        return self

    def write(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def show(self, frame):
        if self.ascii_only:
            # Ein Zeichen bleibt eine Rasterzelle; Meldungen dürfen nicht breiter werden.
            for source, replacement in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("Ä", "A"), ("Ö", "O"), ("Ü", "U"), ("ß", "s")):
                frame = frame.replace(source, replacement)
            frame = frame.encode("ascii", errors="replace").decode("ascii")
        self.write(HOME + frame)

    def __exit__(self, *exc):
        self.keys.restore()
        try:
            self.write(SHOW + R + "\n")
        except OSError:
            logging.getLogger(__name__).warning("Terminalausgabe nicht mehr verfügbar.")
