"""Spielregeln, Schwierigkeitsprofile und validierbare Einstellungen."""
from dataclasses import dataclass, asdict
import math

MAG_SIZE = 10          # Schuss pro Magazin
MAG_WINDOW = 30.0      # Sekunden bis das Magazin sich selbst auffrischt
RELOAD_TIME = 5.0      # Sekunden Nachladen wenn leergeballert
FPS = 18.0             # Frames pro Sekunde (Frame = 1/FPS Sekunden)

# Presets: Tempo, Hindernisdichte, Magazin. Schwierigkeit ist kein Cheat.
PRESETS = {
    "leicht": (0.75, "wenig", 15),
    "normal": (1.00, "normal", 10),
    "schwer": (1.35, "viele", 8),
    "irre": (1.75, "extrem", 6),
}
DENSITIES = {"wenig": 0.60, "normal": 1.0, "viele": 1.35, "extrem": 1.55}
CHEATS = (
    ("infinite_ammo", "unendlich munition"),
    ("instant_reload", "sofort nachladen"),
    ("invincible", "unverwundbar"),
    ("double_points", "doppelte punkte"),
    ("mega_jump", "mega-sprung"),
)


@dataclass
class Settings:
    """Menuewerte; jede Runde uebernimmt eine eigene Kopie."""
    difficulty: str = "normal"
    tempo: float = 1.0
    density: str = "normal"
    magazine: int = MAG_SIZE
    infinite_ammo: bool = False
    instant_reload: bool = False
    invincible: bool = False
    double_points: bool = False
    mega_jump: bool = False

    @property
    def cheats_active(self):
        return any(getattr(self, key) for key, _ in CHEATS)

    def preset(self, name):
        self.tempo, self.density, self.magazine = PRESETS[name]
        self.difficulty = name

    def adjust(self, field, direction):
        if field == "difficulty":
            names = list(PRESETS)
            index = names.index(self.difficulty) if self.difficulty in names else 1
            self.preset(names[(index + direction) % len(names)])
        elif field in ("tempo", "density", "magazine"):
            if field == "tempo":
                self.tempo = round(max(0.5, min(2.0, self.tempo + direction * 0.05)), 2)
            elif field == "magazine":
                self.magazine = max(1, min(30, self.magazine + direction))
            else:
                values = list(DENSITIES)
                self.density = values[(values.index(self.density) + direction) % len(values)]
            self.difficulty = "eigen"
        elif field in dict(CHEATS):
            setattr(self, field, not getattr(self, field))

    def reset(self):
        self.__dict__.update(Settings().__dict__)

    def validate(self):
        """Ungültige Typen und Werte ablehnen, inkonsistente Presets berichtigen."""
        if not isinstance(self.difficulty, str) or self.difficulty not in (*PRESETS, "eigen"):
            raise ValueError("Unbekannte Schwierigkeit.")
        if type(self.tempo) not in (int, float) or not math.isfinite(self.tempo) or not .5 <= self.tempo <= 2:
            raise ValueError("Tempo muss zwischen x0.50 und x2.00 liegen.")
        if not isinstance(self.density, str) or self.density not in DENSITIES:
            raise ValueError("Unbekannte Hindernisdichte.")
        if type(self.magazine) is not int or not 1 <= self.magazine <= 30:
            raise ValueError("Magazin muss 1 bis 30 Schuss enthalten.")
        if any(type(getattr(self, key)) is not bool for key, _ in CHEATS):
            raise ValueError("Cheats müssen an oder aus sein.")
        if self.difficulty in PRESETS and PRESETS[self.difficulty] != (self.tempo, self.density, self.magazine):
            self.difficulty = "eigen"
        return self

    def to_dict(self):
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """JSON-Einstellungen lesen; fehlende Werte erhalten Standardwerte."""
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError("Einstellungen haben ein unbekanntes Format.")
        return cls(**data).validate()


SETTING_ROWS = (
    ("difficulty", "schwierigkeit"), ("tempo", "tempo"),
    ("density", "hindernisse"), ("magazine", "magazin"),
) + CHEATS + (("reset", "[ zuruecksetzen ]"), ("back", "[ zurueck ]"))
