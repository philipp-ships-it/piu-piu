"""Versionierte Rundensnapshots: JSON, strenge Grenzen, niemals Pickle."""
from copy import deepcopy
from dataclasses import asdict
import math
import random

from .geometry import Geometry
from .settings import Settings

SCHEMA = 1
SCALARS = ("y", "vy", "jumps", "ducking", "shoot_t", "ammo", "reload_t", "mag_t",
           "click_t", "dist", "score", "kills", "speed", "t", "spawned", "spawn",
           "dead", "msg", "msg_t", "cheated")
COLLECTIONS = ("obs", "bul", "bg", "clouds", "parts")


def number(value, low=-10000, high=10**12):
    """Bool ist in Python eine Zahl, im Speicherformat jedoch kein Zahlenwert."""
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Spielstand enthält einen ungültigen Zahlenwert.")
    return value


def integer(value, low=0, high=10**12):
    number(value, low, high)
    if type(value) is not int:
        raise ValueError("Spielstand benötigt eine ganze Zahl.")
    return value


def text(value, limit=100):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Spielstand enthält ungültigen Text.")
    return value


def encode(game):
    """Nur fachlichen Zustand sichern; Terminal, Ereignisse und Dateien auslassen."""
    return deepcopy({"version": SCHEMA, "run_id": game.run_id,
                     "geometry": asdict(game.geometry), "settings": game.settings.to_dict(),
                     "rng": game.rng.getstate(),
                     "state": {key: getattr(game, key) for key in SCALARS + COLLECTIONS}})


def _rows(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("Hindernisgrafik ist ungültig.")
    for row in value:
        text(row, 32)
        if not row:
            raise ValueError("Leere Hinderniszeile.")


def _collections(state):
    for key in COLLECTIONS:
        if not isinstance(state[key], list) or len(state[key]) > 1000:
            raise ValueError("Zu viele oder ungültige Spielobjekte.")
    for obj in state["obs"]:
        if not isinstance(obj, dict) or set(obj) != {"x", "art", "art2", "kind", "off", "w", "h", "f"}:
            raise ValueError("Hindernis ist unvollständig.")
        number(obj["x"], -100, 204)
        _rows(obj["art"])
        if obj["art2"] is not None:
            _rows(obj["art2"])
            if len(obj["art2"]) != len(obj["art"]):
                raise ValueError("Animationshöhen stimmen nicht überein.")
        if obj["kind"] not in ("solid", "bird", "word"):
            raise ValueError("Unbekanntes Hindernis.")
        integer(obj["off"], 0, 8)
        integer(obj["f"], 0, 7)
        integer(obj["w"], 1, 32)
        integer(obj["h"], 1, 8)
        if obj["w"] != max(map(len, obj["art"])) or obj["h"] != len(obj["art"]):
            raise ValueError("Hindernisgröße stimmt nicht mit der Grafik überein.")
    for key, size in (("bul", 2), ("bg", 3), ("clouds", 2), ("parts", 6)):
        for obj in state[key]:
            if not isinstance(obj, list) or len(obj) != size:
                raise ValueError("Spielobjekt ist unvollständig.")
            for value in obj[:2]:
                number(value, -200, 250)
            if key in ("bul", "bg", "clouds"):
                integer(obj[1], -100, 44)
            if key == "bg":
                text(obj[2])
            if key == "parts":
                number(obj[2], -2, 2)
                number(obj[3], -2, 2)
                integer(obj[4], 1, 10)
                text(obj[5], 1)


def decode(data):
    """Ungültige Snapshots vollständig ablehnen, bevor Zustand übernommen wird."""
    from .engine import Game
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != SCHEMA:
        raise ValueError("Spielstandversion wird nicht unterstützt.")
    try:
        run_id = text(data["run_id"], 32)
        if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Rundenkennung ist ungültig.")
        geometry = Geometry(**data["geometry"])
        settings = Settings.from_dict(data["settings"])
        state = deepcopy(data["state"])
        if not isinstance(state, dict) or set(state) != set(SCALARS + COLLECTIONS):
            raise ValueError("Spielstand ist unvollständig.")
        for key in ("jumps", "ducking", "shoot_t", "ammo", "click_t", "score", "kills", "t", "spawned", "msg_t"):
            integer(state[key])
        for key in ("y", "dist", "speed", "spawn", "reload_t", "mag_t"):
            number(state[key], 0)
        number(state["vy"], -100, 10)
        for key in ("dead", "cheated"):
            if type(state[key]) is not bool:
                raise ValueError("Spielstatus ist ungültig.")
        text(state["msg"])
        if state["jumps"] > 2 or state["ammo"] > settings.magazine or state["reload_t"] > 5 or state["mag_t"] > 30:
            raise ValueError("Spielregeln im Speicherstand verletzt.")
        if settings.cheats_active and not state["cheated"]:
            raise ValueError("Cheat-Kennzeichnung fehlt.")
        expected_score = (int(state["dist"] / 3) + state["kills"] * 25) * (2 if settings.double_points else 1)
        if state["score"] != expected_score:
            raise ValueError("Punktestand ist inkonsistent.")
        _collections(state)
        rng = data["rng"]
        if not isinstance(rng, (list, tuple)) or len(rng) != 3 or rng[0] != 3:
            raise ValueError("Zufallszustand ist ungültig.")
        if not isinstance(rng[1], (list, tuple)) or len(rng[1]) != 625 or rng[2] is not None:
            raise ValueError("Zufallszustand ist unvollständig.")
        for value in rng[1][:-1]:
            integer(value, 0, 2**32 - 1)
        integer(rng[1][-1], 0, 624)
        restored_rng = random.Random()
        restored_rng.setstate((3, tuple(rng[1]), None))
        game = Game(settings, geometry, seed=0)
        for key, value in state.items():
            setattr(game, key, value)
        game.rng = restored_rng
        game.run_id = run_id
        return game
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("Spielstand hat ein ungültiges Format.") from exc
