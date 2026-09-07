"""Unveraenderliche Spielfeldmasse; keine globalen Terminalgroessen."""
from dataclasses import dataclass

MIN_W, MAX_W = 46, 200
MIN_H, MAX_H = 14, 44


@dataclass(frozen=True)
class Geometry:
    """Zeichenraster mit abgeleiteter Bodenlinie und Spielerposition."""
    width: int = 80
    height: int = 20

    def __post_init__(self):
        if type(self.width) is not int or not MIN_W <= self.width <= MAX_W:
            raise ValueError("Spielfeldbreite muss zwischen 46 und 200 liegen.")
        if type(self.height) is not int or not MIN_H <= self.height <= MAX_H:
            raise ValueError("Spielfeldhoehe muss zwischen 14 und 44 liegen.")

    @property
    def ground(self):
        return self.height - max(3, min(6, self.height // 5))

    @property
    def player_x(self):
        return max(3, min(10, self.width // 13))

    @classmethod
    def fit(cls, columns, lines):
        """Eine Randspalte/-zeile fuer den Terminalcursor reservieren."""
        return cls(max(MIN_W, min(MAX_W, columns - 1)),
                   max(MIN_H, min(MAX_H, lines - 1)))
