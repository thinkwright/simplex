"""CLI entry point for detreport."""

import json
import sys

from detreport.public import ReportError, build_report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m detreport INPUT_JSON", file=sys.stderr)
        return 2
    path = argv[0]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = build_report(data)
    sys.stdout.write(result)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except ReportError as e:
        print("error: {}".format(e), file=sys.stderr)
        rc = 1
    sys.exit(rc)