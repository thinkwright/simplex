"""CLI entry point: ``python -m detreport INPUT_JSON``.

Reads a JSON array of events from the supplied path, prints the
result of :func:`detreport.build_report` followed by exactly one
newline, and exits successfully.
"""

import json
import sys

from detreport.public import ReportError, build_report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(
            "usage: python -m detreport INPUT_JSON",
            file=sys.stderr,
        )
        return 2

    path = argv[0]
    with open(path, "r", encoding="utf-8") as fh:
        events = json.load(fh)

    output = build_report(events)
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReportError as exc:
        print("error: {0}".format(exc), file=sys.stderr)
        sys.exit(1)