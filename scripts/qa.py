"""Python-QA mit Standardbibliothek: Syntax, Unit-Tests, optionale Zeilenabdeckung."""
import argparse
import ast
from pathlib import Path
import sys
import trace
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", action="store_true", help="Zeilenabdeckung unter .qa/coverage ablegen")
    args = parser.parse_args()
    sources = [ROOT / "piuu.py"]
    for folder in ("piu", "tests", "scripts"):
        sources.extend((ROOT / folder).rglob("*.py"))
    for source in sources:
        ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    def run():
        # Imports gehören zur Messung; sonst erscheinen Konstanten fälschlich ungetestet.
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        return unittest.TextTestRunner(verbosity=2).run(suite)
    if args.coverage:
        tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.base_prefix])
        result = tracer.runfunc(run)
        report = tracer.results()
        report.counts = {(filename, line): count for (filename, line), count in report.counts.items()
                         if Path(filename).resolve().is_relative_to(ROOT / "piu")}
        output = ROOT / ".qa" / "coverage"
        output.mkdir(parents=True, exist_ok=True)
        report.write_results(show_missing=True, summary=True, coverdir=str(output))
    else:
        result = run()
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
