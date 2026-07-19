"""CLI entry point: python -m detreport INPUT_JSON"""

import json
import sys

from detreport.public import build_report, ReportError


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m detreport INPUT_JSON", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        result = build_report(events)
    except ReportError as exc:
        print(f"ReportError: {exc}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
