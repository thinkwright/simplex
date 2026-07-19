"""Command-line entry point: ``python -m detreport INPUT_JSON``.

Reads a JSON array from the supplied path, prints exactly the output of
``build_report`` followed by one newline, and exits successfully.
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
        sys.stderr.write("error: cannot read %s: %s\n" % (path, exc))
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write("error: invalid JSON in %s: %s\n" % (path, exc))
        return 1

    try:
        output = build_report(data)
    except ReportError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 1

    payload = output.encode("utf-8") + b"\n"
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))