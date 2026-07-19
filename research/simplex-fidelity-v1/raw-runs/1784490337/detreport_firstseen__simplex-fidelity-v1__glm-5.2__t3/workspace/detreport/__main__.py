"""Command line entry point: python -m detreport INPUT_JSON."""

import json
import sys

from detreport.public import ReportError, build_report


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: python -m detreport INPUT_JSON\n")
        return 2

    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        sys.stderr.write("error: cannot read input file: " + str(error) + "\n")
        return 1
    except json.JSONDecodeError as error:
        sys.stderr.write("error: invalid JSON: " + str(error) + "\n")
        return 1

    try:
        result = build_report(data)
    except ReportError as error:
        sys.stderr.write("error: " + str(error) + "\n")
        return 1

    sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))