"""Command line entry point: ``python -m detreport INPUT_JSON``."""

import json
import sys

from detreport.public import build_report, ReportError


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        sys.stderr.write("usage: python -m detreport INPUT_JSON\n")
        return 2
    path = argv[0]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        sys.stderr.write("error: cannot read %s: %s\n" % (path, error))
        return 1
    except json.JSONDecodeError as error:
        sys.stderr.write("error: invalid JSON in %s: %s\n" % (path, error))
        return 1
    try:
        result = build_report(data)
    except ReportError as error:
        sys.stderr.write("error: %s\n" % error)
        return 1
    sys.stdout.write(result)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())