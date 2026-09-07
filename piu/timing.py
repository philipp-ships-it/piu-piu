"""Feste Simulationstakte unabhängig von Renderdauer und Sound."""
from .settings import FPS


class FixedClock:
    """Nach Hängern höchstens vier Takte nachholen; Pausen explizit zurücksetzen."""
    def __init__(self, now=0.0):
        self.reset(now)

    def reset(self, now):
        self.previous = now
        self.accumulator = 0.0

    def consume(self, now):
        elapsed = max(0.0, min(now - self.previous, 4 / FPS))
        self.previous = now
        self.accumulator += elapsed
        count = min(4, int((self.accumulator + 1e-9) * FPS))
        self.accumulator -= count / FPS
        return count
