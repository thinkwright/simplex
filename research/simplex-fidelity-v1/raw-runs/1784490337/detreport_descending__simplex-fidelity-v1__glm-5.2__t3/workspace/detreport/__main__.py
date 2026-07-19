"""Command line entry point: python -m detreport INPUT_JSON"""

import json
import sys

from detreport.public import ReportError, build_report


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        sys.stderr.write("usage: python -m detreport INPUT_JSON\n")
        return 2
    path = argv[0]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        sys.stderr.write("error reading input: %s\n" % error)
        return 1
    try:
        result = build_report(data)
    except ReportError as error:
        sys.stderr.write("report error: %s\n" % error)
        return 1
    sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())