"""Reproduzierbares Python-Spielpaket ohne Nutzerdaten oder Entwicklungsreste."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "downloads" / "piu-piu-python.zip"


def build(destination=None):
    output = Path(destination) if destination is not None else OUTPUT
    files = [ROOT / name for name in ("piuu.py", "PIUU.bat", "README.md", "LICENSE", "pyproject.toml")]
    files += sorted((ROOT / "piu").glob("*.py"))
    files += sorted((ROOT / "handbuch").glob("*.md"))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for source in files:
                info = ZipInfo("piu-piu/" + source.relative_to(ROOT).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3  # Gleiche ZIP-Metadaten unter Windows und Linux.
                info.external_attr = 0o644 << 16
                content = source.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
                if source.suffix == ".bat":
                    content = content.replace("\n", "\r\n")
                archive.writestr(info, content.encode("utf-8"))
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print("Download gebaut: " + str(output))
    return output


if __name__ == "__main__":
    build()
