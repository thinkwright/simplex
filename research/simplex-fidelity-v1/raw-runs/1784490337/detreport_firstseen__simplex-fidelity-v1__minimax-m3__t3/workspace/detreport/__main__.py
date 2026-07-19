"""CLI entry point: python -m detreport INPUT_JSON."""

import json
import sys

from .core import build_report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m detreport INPUT_JSON", file=sys.stderr)
        return 2
    path = argv[0]
    with open(path, "r", encoding="utf-8") as fh:
        events = json.load(fh)
    sys.stdout.write(build_report(events))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())