"""Command-line entry point: ``python -m detreport INPUT_JSON``.

Reads a JSON array from the supplied path, prints exactly the output of
:func:`detreport.public.build_report` followed by a single newline, and exits
successfully on valid input.
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
    except OSError as exc:
        sys.stderr.write("error: cannot read {0}: {1}\n".format(path, exc))
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write("error: invalid JSON in {0}: {1}\n".format(path, exc))
        return 1

    try:
        result = build_report(data)
    except ReportError as exc:
        sys.stderr.write("error: {0}\n".format(exc))
        return 1

    sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))