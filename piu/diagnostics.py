"""Diagnose ohne Zusatzpakete; technische Details landen im lokalen Protokoll."""
import logging
from logging.handlers import RotatingFileHandler
import platform
import sys
import tempfile


def configure_logging(directory):
    """Protokoll auf drei Dateien à 256 KiB begrenzen."""
    logger = logging.getLogger("piu")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(directory / "piu.log", maxBytes=262144, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return handler


def diagnose(directory):
    """Umgebung und Schreibzugriff prüfen; keine Sicherheitseinstellungen ändern."""
    lines = ["PIU PIU – Diagnose", "Python: " + platform.python_version(),
             "Programm: " + sys.executable, "System: " + platform.system(),
             "Datenordner: " + str(directory),
             "Interaktive Eingabe: " + ("ja" if sys.stdin.isatty() else "nein"),
             "Protokoll: " + str(directory / "piu.log")]
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=directory) as stream:
            stream.write(b"piu")
            stream.flush()
        lines.append("Schreibzugriff: OK")
        return "\n".join(lines), 0
    except OSError as exc:
        lines.append("Schreibzugriff: FEHLER – " + str(exc))
        lines.append("Mit --data-dir einen beschreibbaren Ordner wählen.")
        return "\n".join(lines), 3
