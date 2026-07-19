"""CLI entry point for detreport."""

import json
import sys

from detreport.public import build_report, ReportError


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        raise SystemExit("usage: python -m detreport INPUT_JSON")
    path = argv[0]
    with open(path, "r", encoding="utf-8") as f:
        events = json.load(f)
    try:
        output = build_report(events)
    except ReportError as exc:
        raise SystemExit("ReportError: {}".format(exc))
    sys.stdout.write(output + "\n")


if __name__ == "__main__":
    main()