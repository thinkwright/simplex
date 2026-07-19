"""CLI entry point: ``python -m detreport INPUT_JSON``."""

import json
import sys

from detreport.public import ReportError, build_report


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1:
        print(
            "usage: python -m detreport INPUT_JSON",
            file=sys.stderr,
        )
        return 2

    path = argv[0]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("input must be a JSON array of events", file=sys.stderr)
        return 1

    try:
        output = build_report(data)
    except ReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())