"""Lokale Profile: atomare Speicherung, Sicherungskopie und Wiederherstellung."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile

from .engine import Game
from .settings import Settings

PROFILE_VERSION = 1
MAX_SCORES = 10
MAX_BYTES = 2_000_000


class StorageError(Exception):
    """Erwarteter Speicherfehler mit verständlichem Hinweis für die Oberfläche."""


def default_data_dir():
    """Benutzerdaten liegen außerhalb von Quellcode und installierter EXE."""
    override = os.environ.get("PIU_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PiuPiu"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "piu-piu"


def clean_name(value):
    """Steuerzeichen entfernen; Namen auf 14 sichtbare Zeichen begrenzen."""
    if not isinstance(value, str):
        return "Piu"
    return " ".join("".join(c for c in value if c.isprintable()).split())[:14] or "Piu"


def normalize_scores(entries):
    """Ungültige Einträge auslassen, Spieler zusammenführen, Top 10 behalten."""
    if not isinstance(entries, list):
        return [], 1
    merged, skipped = {}, 0
    for entry in entries:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        values = [entry.get("score", 0), entry.get("kills", 0), entry.get("runs", 1)]
        if any(type(n) is not int or not 0 <= n <= 10**12 for n in values) or values[2] < 1:
            skipped += 1
            continue
        name = clean_name(entry.get("name", "Piu"))
        key = name.casefold()
        result = {"name": name, "score": values[0], "kills": values[1], "runs": values[2],
                  "date": str(entry.get("date", ""))[:32]}
        # Auch Datumstext darf keine Terminal-Steuersequenzen einschleusen.
        result["date"] = "".join(c for c in result["date"] if c.isprintable())
        if key in merged:
            previous = merged[key]
            runs = min(10**12, previous["runs"] + result["runs"])
            if result["score"] > previous["score"]:
                merged[key] = result
            merged[key]["runs"] = runs
        else:
            merged[key] = result
    return sorted(merged.values(), key=lambda e: e["score"], reverse=True)[:MAX_SCORES], skipped


def _read_json(path):
    """Dateigröße begrenzen, bevor JSON verarbeitet wird."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Profildatei ist zu groß.")
    return json.loads(raw), raw


def atomic_write(path, payload):
    """Im selben Verzeichnis schreiben, synchronisieren und atomar ersetzen."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".piu-", suffix=".tmp", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class Store:
    """Ein Profil pro Datenordner. Änderungen werden ausschließlich mit save festgeschrieben."""
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else default_data_dir()
        self.path = self.directory / "profile.json"
        self.backup = self.directory / "profile.backup.json"
        self.settings = Settings()
        self.scores = []
        self.checkpoint = None
        self.player_name = "Piu"
        self.last_run_id = None
        self.warnings = []
        self._last_good = None

    @property
    def best(self):
        return self.scores[0]["score"] if self.scores else 0

    @contextmanager
    def locked(self):
        """Parallele Spielinstanzen dürfen dasselbe Profil nicht überschreiben."""
        lock = None
        acquired = False
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            lock = (self.directory / "profile.lock").open("a+b")
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as exc:
            if lock:
                lock.close()
            raise StorageError("Profil nicht zugänglich oder bereits geöffnet. Zweite Instanz schließen; "
                               "alternativ --data-dir mit einem beschreibbaren Ordner verwenden.") from exc
        try:
            yield self
        finally:
            if acquired:
                try:
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                finally:
                    lock.close()

    def _restore(self, data):
        if not isinstance(data, dict):
            raise ValueError("Profil ist kein JSON-Objekt.")
        if type(data.get("version")) is not int or data["version"] != PROFILE_VERSION:
            raise StorageError("Unbekannte Profilversion. Datei bleibt unverändert; passende Spielversion verwenden.")
        self.player_name = clean_name(data.get("player_name", "Piu"))
        try:
            self.settings = Settings.from_dict(data.get("settings", {}))
        except ValueError:
            self.settings = Settings()
            self.warnings.append("Einstellungen beschädigt: Standardwerte geladen.")
        self.scores, skipped = normalize_scores(data.get("scores", []))
        if skipped:
            self.warnings.append("Ungültige Highscore-Einträge ausgelassen; gültige Werte bleiben erhalten.")
        self.checkpoint = data.get("checkpoint")
        if self.checkpoint is not None:
            try:
                Game.from_snapshot(self.checkpoint)
            except ValueError:
                self.checkpoint = None
                self.warnings.append("Rundenstand beschädigt: Fortsetzen ist nicht möglich.")
        last_run = data.get("last_run_id")
        self.last_run_id = last_run if isinstance(last_run, str) and len(last_run) == 32 else None

    def _preserve_damaged(self, path):
        """Beschädigte Nutzerdaten zur manuellen Rettung aufbewahren."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(path, self.directory / ("profile.recovery-" + stamp + ".json"))

    def load(self, legacy_paths=()):
        """Profil laden, bei defektem JSON Backup versuchen, alte Scores einmalig übernehmen."""
        self.warnings = []
        for path in (self.path, self.backup):
            try:
                data, raw = _read_json(path)
                self._restore(data)
                if self.warnings and path == self.path:
                    self._preserve_damaged(path)
                self._last_good = raw
                if path == self.backup:
                    self.warnings.append("Sicherungskopie geladen. Der letzte Speicherschritt kann fehlen.")
                return self
            except FileNotFoundError:
                continue
            except (ValueError, UnicodeError, RecursionError):
                try:
                    self._preserve_damaged(path)
                except OSError as exc:
                    raise StorageError("Beschädigte Datei konnte nicht gesichert werden. Datenordner prüfen.") from exc
                self.warnings.append("Beschädigtes JSON gesichert: " + path.name)
            except OSError as exc:
                raise StorageError("Profildatei konnte nicht gelesen werden. Zugriffsrechte und --data-dir prüfen.") from exc
        for legacy in legacy_paths:
            try:
                entries, _ = _read_json(Path(legacy))
                self.scores, skipped = normalize_scores(entries)
                self.warnings.append("Alte Highscores übernommen; Originaldatei bleibt erhalten.")
                if skipped:
                    self.warnings.append("Ungültige alte Einträge wurden ausgelassen.")
                self.save()
                break
            except FileNotFoundError:
                continue
            except (ValueError, OSError, UnicodeError):
                self.warnings.append("Alte Highscores nicht lesbar: " + str(legacy))
        return self

    def _document(self):
        return {"version": PROFILE_VERSION, "player_name": self.player_name,
                "settings": self.settings.to_dict(), "scores": self.scores,
                "checkpoint": self.checkpoint, "last_run_id": self.last_run_id}

    def save(self):
        """Erfolg erst melden, wenn das vollständige Profil atomar ersetzt wurde."""
        try:
            payload = json.dumps(self._document(), ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
            if len(payload) > MAX_BYTES:
                raise ValueError("Profil überschreitet die erlaubte Dateigröße.")
            self.directory.mkdir(parents=True, exist_ok=True)
            if self._last_good is not None:
                atomic_write(self.backup, self._last_good)
            atomic_write(self.path, payload)
            self._last_good = payload
        except (OSError, ValueError, TypeError) as exc:
            raise StorageError("Speichern fehlgeschlagen. Freien Speicher und Schreibrechte prüfen; "
                               "vorherige Daten bleiben erhalten. " + str(exc)) from exc

    def remember(self, game):
        """Auch Cheat-Runden sind fortsetzbar; Highscores werden hier nicht verändert."""
        self.checkpoint = game.snapshot()
        self.save()

    def finish(self, game, name):
        """Runde und Score in einer Transaktion abschließen, Wiederholungen nicht doppelt zählen."""
        if not game.dead:
            raise ValueError("Eine laufende Runde darf nicht als beendet verbucht werden.")
        previous = deepcopy((self.scores, self.checkpoint, self.last_run_id))
        improved = False
        name = clean_name(name)
        if game.run_id != self.last_run_id:
            if not game.cheated:
                entry = next((e for e in self.scores if e["name"].casefold() == name.casefold()), None)
                improved = entry is None or game.score > entry["score"]
                if entry is None:
                    entry = {"name": name, "score": 0, "kills": 0, "runs": 0, "date": ""}
                    self.scores.append(entry)
                entry["runs"] = min(10**12, entry["runs"] + 1)
                if improved:
                    entry.update(name=name, score=game.score, kills=game.kills,
                                 date=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                self.scores.sort(key=lambda e: e["score"], reverse=True)
                del self.scores[MAX_SCORES:]
            self.last_run_id = game.run_id
        self.checkpoint = None
        try:
            self.save()
        except StorageError:
            self.scores, self.checkpoint, self.last_run_id = previous
            raise
        rank = next((i for i, e in enumerate(self.scores, 1) if e["name"].casefold() == name.casefold()), None)
        return None if game.cheated else rank, improved
