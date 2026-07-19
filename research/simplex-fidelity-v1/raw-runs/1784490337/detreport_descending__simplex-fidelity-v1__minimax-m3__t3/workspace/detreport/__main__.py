"""CLI entry point: ``python -m detreport INPUT_JSON``.

Reads a JSON array from the supplied path, prints the report produced by
:func:`detreport.build_report` followed by a single newline, and exits 0.
"""

from __future__ import annotations

import json
import sys

from .core import ReportError, build_report


def main(argv: list) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: python -m detreport INPUT_JSON\n")
        return 2

    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            events = json.load(fh)
    except FileNotFoundError:
        sys.stderr.write(f"detreport: file not found: {path}\n")
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"detreport: invalid JSON in {path}: {exc}\n")
        return 1

    report = build_report(events)
    sys.stdout.write(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ReportError as exc:
        sys.stderr.write(f"detreport: {exc}\n")
        raise SystemExit(1)