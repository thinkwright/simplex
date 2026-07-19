"""CLI entry point: python -m detreport INPUT_JSON

Reads a JSON array from the supplied path, prints build_report output plus
one newline, and exits successfully.
"""

from __future__ import annotations

import json
import sys

from .public import ReportError, build_report


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1:
        print("usage: python -m detreport INPUT_JSON", file=sys.stderr)
        return 2

    path = argv[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except OSError as exc:
        print(f"error reading {path}: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error parsing {path}: {exc}", file=sys.stderr)
        return 1

    try:
        output = build_report(events)
    except ReportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())