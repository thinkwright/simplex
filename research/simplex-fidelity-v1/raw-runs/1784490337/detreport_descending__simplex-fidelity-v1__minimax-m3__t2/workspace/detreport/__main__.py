"""CLI entry point: python -m detreport INPUT_JSON."""

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
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        print("could not read {0}: {1}".format(path, exc), file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print("invalid JSON in {0}: {1}".format(path, exc), file=sys.stderr)
        return 1
    try:
        output = build_report(data)
    except ReportError as exc:
        print("invalid input: {0}".format(exc), file=sys.stderr)
        return 1
    sys.stdout.write(output)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())