"""Core implementation for detreport.

Validates events, groups them by category, and produces a compact JSON report.
Uses only the Python standard library.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, List, Mapping


class ReportError(Exception):
    """Raised when input events are invalid or the input collection is invalid."""


_REQUIRED_EVENT_KEYS = ("id", "category", "amount_cents")


def _validate_events(events: Any) -> List[Mapping[str, Any]]:
    """Validate the events collection and each event.

    Returns a list of validated event dicts. Raises ReportError on any
    structural or semantic problem. The input is never mutated.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    validated: List[Mapping[str, Any]] = []
    seen_ids = set()

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(f"event at index {index} is not a dict")

        # Check for missing required keys.
        for key in _REQUIRED_EVENT_KEYS:
            if key not in event:
                raise ReportError(
                    f"event at index {index} is missing required field {key!r}"
                )

        # Check for extra keys.
        extra = set(event.keys()) - set(_REQUIRED_EVENT_KEYS)
        if extra:
            raise ReportError(
                f"event at index {index} has unexpected fields: {sorted(extra)}"
            )

        event_id = event["id"]
        if not isinstance(event_id, str) or event_id == "":
            raise ReportError(
                f"event at index {index} has invalid id (must be non-empty string)"
            )
        if event_id in seen_ids:
            raise ReportError(
                f"event at index {index} has duplicate id {event_id!r}"
            )
        seen_ids.add(event_id)

        category = event["category"]
        if not isinstance(category, str) or category == "":
            raise ReportError(
                f"event at index {index} has invalid category (must be non-empty string)"
            )

        amount = event["amount_cents"]
        # bool is a subclass of int in Python; explicitly reject booleans.
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                f"event at index {index} has invalid amount_cents "
                f"(must be integer, not boolean)"
            )

        validated.append(event)

    return validated


def build_report(events: Any) -> str:
    """Build a compact JSON report from a list of events.

    The input list is never mutated. The returned string is byte-for-byte
    stable for the same ordered input.
    """
    validated = _validate_events(events)

    # Group events by category. Use a dict to preserve insertion order, then
    # sort by category code-point order at the end.
    groups: "dict[str, List[Mapping[str, Any]]]" = {}
    grand_total = 0

    for event in validated:
        category = event["category"]
        amount = event["amount_cents"]
        grand_total += amount
        groups.setdefault(category, []).append(event)

    # Build group objects sorted by category ascending (Unicode code-point).
    sorted_categories = sorted(groups.keys())
    group_objects = []
    for category in sorted_categories:
        category_events = groups[category]
        total_cents = sum(e["amount_cents"] for e in category_events)
        event_ids = sorted(e["id"] for e in category_events)
        group_objects.append({
            "category": category,
            "count": len(category_events),
            "total_cents": total_cents,
            "events": event_ids,
        })

    report = {
        "groups": group_objects,
        "grand_total_cents": grand_total,
    }

    # Compact JSON, sorted keys, ensure_ascii=False so non-ASCII characters
    # appear literally (e.g. "café" not "caf\u00e9").
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))