"""Command-line entry point: ``python -m detreport INPUT_JSON``.

Reads a JSON array from the supplied path, prints exactly the output of
:func:`detreport.build_report` followed by a single newline, and exits
successfully. Only the Python standard library and detreport itself are used.
"""

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
    except (OSError, ValueError) as error:
        sys.stderr.write(f"error: could not read {path}: {error}\n")
        return 1
    try:
        output = build_report(data)
    except ReportError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))