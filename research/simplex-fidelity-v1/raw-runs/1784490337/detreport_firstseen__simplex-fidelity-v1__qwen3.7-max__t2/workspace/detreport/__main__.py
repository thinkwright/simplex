"""CLI entry point for detreport."""

import json
import sys

from detreport.public import ReportError, build_report


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m detreport INPUT_JSON", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        report = build_report(events)
    except ReportError as e:
        print(f"Report error: {e}", file=sys.stderr)
        sys.exit(1)

    print(report)


if __name__ == '__main__':
    main()
