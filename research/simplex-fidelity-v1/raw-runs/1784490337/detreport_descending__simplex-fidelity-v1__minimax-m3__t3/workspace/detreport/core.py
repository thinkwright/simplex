"""Core logic for detreport.

Pure functions that validate events and build the report dict.
Only the Python standard library is used.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class ReportError(ValueError):
    """Raised when the input events are invalid."""


_REQUIRED_EVENT_FIELDS = ("id", "category", "amount_cents")


def _validate_event(event: Any, seen_ids: set) -> None:
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")

    keys = set(event.keys())
    required = set(_REQUIRED_EVENT_FIELDS)
    if keys != required:
        missing = required - keys
        extra = keys - required
        if missing:
            raise ReportError(f"event missing required field(s): {sorted(missing)}")
        if extra:
            raise ReportError(f"event has unexpected field(s): {sorted(extra)}")

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")
    if event_id in seen_ids:
        raise ReportError(f"duplicate event id: {event_id!r}")
    seen_ids.add(event_id)

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    amount = event["amount_cents"]
    # bool is a subclass of int in Python; reject booleans explicitly.
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer (non-boolean)")


def _validate_events(events: Any) -> List[Dict[str, Any]]:
    if not isinstance(events, list):
        raise ReportError("events must be a list")
    seen_ids: set = set()
    for event in events:
        _validate_event(event, seen_ids)
    return events


def build_report(events: Any) -> Dict[str, Any]:
    """Validate ``events`` and return the report dict.

    The input list is never mutated.
    """
    validated = _validate_events(events)

    groups: Dict[str, Dict[str, Any]] = {}
    grand_total = 0

    for event in validated:
        category = event["category"]
        amount = event["amount_cents"]
        event_id = event["id"]

        group = groups.get(category)
        if group is None:
            group = {
                "category": category,
                "count": 0,
                "total_cents": 0,
                "events": [],
            }
            groups[category] = group
        group["count"] += 1
        group["total_cents"] += amount
        group["events"].append(event_id)
        grand_total += amount

    # Sort event ids ascending within each group.
    for group in groups.values():
        group["events"].sort()

    # Order groups by category in descending Unicode code-point order.
    ordered_groups = [groups[c] for c in sorted(groups.keys(), reverse=True)]

    return {
        "groups": ordered_groups,
        "grand_total_cents": grand_total,
    }