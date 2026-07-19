"""Core implementation of detreport."""

import json
from typing import Any, Iterable, List, Mapping


class ReportError(Exception):
    """Raised when input data is invalid for report generation."""


def _validate_event(event: Any, seen_ids: set) -> None:
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")

    # Reject extra fields: only id, category, amount_cents allowed.
    allowed = {"id", "category", "amount_cents"}
    extra = set(event.keys()) - allowed
    if extra:
        raise ReportError(f"event has unexpected fields: {sorted(extra)}")

    # Required fields.
    for field in ("id", "category", "amount_cents"):
        if field not in event:
            raise ReportError(f"event missing required field: {field}")

    # id: non-empty string, unique.
    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")
    if event_id in seen_ids:
        raise ReportError(f"duplicate event id: {event_id}")
    seen_ids.add(event_id)

    # category: non-empty string.
    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    # amount_cents: integer, not boolean.
    amount = event["amount_cents"]
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer")


def build_report(events: Iterable[Mapping[str, Any]]) -> str:
    """Build a deterministic JSON report from an iterable of events.

    Returns a compact JSON string with ensure_ascii=False and sorted keys.
    """
    # Materialize input so we don't mutate it and can iterate twice if needed.
    if isinstance(events, (str, bytes)):
        raise ReportError("events must be an iterable of dicts, not a string")

    # Try to detect if input is a dict (not allowed as the top-level events).
    if isinstance(events, dict):
        raise ReportError("events must be an iterable of dicts")

    try:
        event_list: List[Mapping[str, Any]] = list(events)
    except TypeError as exc:
        raise ReportError(f"events is not iterable: {exc}") from exc

    # Validate each event.
    seen_ids: set = set()
    for idx, event in enumerate(event_list):
        try:
            _validate_event(event, seen_ids)
        except ReportError as exc:
            raise ReportError(f"event at index {idx}: {exc}") from exc

    # Group by category, preserving first-seen order.
    groups_order: List[str] = []
    groups_data: dict = {}
    for event in event_list:
        category = event["category"]
        amount = event["amount_cents"]
        if category not in groups_data:
            groups_order.append(category)
            groups_data[category] = {"count": 0, "total_cents": 0, "events": []}
        groups_data[category]["count"] += 1
        groups_data[category]["total_cents"] += amount
        groups_data[category]["events"].append(event["id"])

    # Sort events within each group ascending.
    for category in groups_data:
        groups_data[category]["events"].sort()

    # Order groups by category descending Unicode code-point order.
    sorted_categories = sorted(groups_order, reverse=True)

    # Build group objects.
    group_objects = []
    for category in sorted_categories:
        data = groups_data[category]
        group_objects.append({
            "category": category,
            "count": data["count"],
            "total_cents": data["total_cents"],
            "events": data["events"],
        })

    grand_total = sum(event["amount_cents"] for event in event_list)

    report = {
        "groups": group_objects,
        "grand_total_cents": grand_total,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main(argv: List[str]) -> int:
    """CLI entry point: read JSON array from path, print report + newline."""
    import sys

    if len(argv) != 2:
        print(f"usage: {argv[0]} INPUT_JSON", file=sys.stderr)
        return 2

    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error reading {path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, list):
        print("input must be a JSON array of events", file=sys.stderr)
        return 1

    try:
        output = build_report(data)
    except ReportError as exc:
        print(f"report error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))