"""Testbare Menünavigation; kennt weder Dateien noch Terminalausgabe."""
from .settings import SETTING_ROWS


class Menu:
    def __init__(self, settings, resumable=False):
        self.settings = settings
        self.resumable = resumable
        self.screen = "start"
        self.selected = 0

    @property
    def choices(self):
        return ([('resume', 'FORTSETZEN')] if self.resumable else []) + [
            ('start', 'NEUE RUNDE' if self.resumable else 'START'), ('settings', 'SETTINGS'), ('quit', 'ENDE')]

    def handle(self, key):
        """Aktion start/resume/quit/changed liefern oder nur die Auswahl verschieben."""
        if key == "quit":
            return "quit"
        if key == "back":
            self.screen, self.selected = "start", 0
        elif key in ("jump", "duck"):
            count = len(SETTING_ROWS) if self.screen == "settings" else (2 if self.screen == "confirm" else len(self.choices))
            self.selected = (self.selected + (1 if key == "duck" else -1)) % count
        elif self.screen == "confirm" and key == "shoot":
            if self.selected == 1:
                return "start"
            self.screen, self.selected = "start", 0
        elif self.screen == "start" and key == "shoot":
            action = self.choices[self.selected][0]
            if action == "settings":
                self.screen, self.selected = "settings", 0
            elif action == "start" and self.resumable:
                self.screen, self.selected = "confirm", 0
            else:
                return action
        elif self.screen == "settings" and key in ("left", "right", "shoot"):
            field = SETTING_ROWS[self.selected][0]
            if field == "back":
                if key == "shoot":
                    self.screen, self.selected = "start", 0
            elif field == "reset":
                if key == "shoot":
                    self.settings.reset()
                    return "changed"
            else:
                self.settings.adjust(field, -1 if key == "left" else 1)
                return "changed"
