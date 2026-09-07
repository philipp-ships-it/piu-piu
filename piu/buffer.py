"""ANSI-Framebuffer mit Clipping: liefert Text, schreibt nicht ins Terminal."""
from .colors import R

class Buf:
    def __init__(self, geometry):
        self.w = geometry.width
        self.h = geometry.height
        self.g = [[" "] * self.w for _ in range(self.h)]
        self.c = [[None] * self.w for _ in range(self.h)]

    def put(self, x, y, s, col=None, wide=False):
        if y < 0 or y >= self.h:
            return
        x = int(x)
        for i, chpos in enumerate(s):
            xx = x + i
            if 0 <= xx < self.w:
                self.g[y][xx] = chpos
                self.c[y][xx] = col
        if wide and 0 <= x + 1 < self.w:
            self.g[y][x + 1] = ""
            self.c[y][x + 1] = col

    def art(self, x, y_bottom, art, col=None):
        for i, row in enumerate(reversed(art)):
            self.put(x, y_bottom - i, row, col)

    def render(self):
        lines = []
        for y in range(self.h):
            parts = []
            cur = None
            for x in range(self.w):
                ch = self.g[y][x]
                if ch == "":
                    continue
                col = self.c[y][x]
                if col != cur:
                    parts.append(R if col is None else col)
                    cur = col
                parts.append(ch)
            parts.append(R)
            lines.append("".join(parts).rstrip() + "\033[K")
        return "\n".join(lines)
