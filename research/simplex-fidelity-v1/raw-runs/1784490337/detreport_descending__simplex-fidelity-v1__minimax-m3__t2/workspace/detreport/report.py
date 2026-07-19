"""Core report-building logic for detreport.

Uses only the Python standard library.
"""

import json
from collections import OrderedDict


class ReportError(Exception):
    """Raised when input events are invalid."""


_REQUIRED_EVENT_KEYS = ("id", "category", "amount_cents")


def _validate_event(event, index):
    if not isinstance(event, dict):
        raise ReportError(
            "event at index {0} is not a dict".format(index)
        )
    # Check for exactly the required keys (no extras, no missing).
    keys = set(event.keys())
    required = set(_REQUIRED_EVENT_KEYS)
    if keys != required:
        missing = required - keys
        extra = keys - required
        parts = []
        if missing:
            parts.append("missing field(s): {0}".format(
                ", ".join(sorted(missing))
            ))
        if extra:
            parts.append("extra field(s): {0}".format(
                ", ".join(sorted(extra))
            ))
        raise ReportError(
            "event at index {0} has invalid keys ({1})".format(index, "; ".join(parts))
        )

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError(
            "event at index {0} has invalid id".format(index)
        )

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError(
            "event at index {0} has invalid category".format(index)
        )

    amount = event["amount_cents"]
    # bool is a subclass of int in Python; explicitly reject booleans.
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ReportError(
            "event at index {0} has invalid amount_cents".format(index)
        )


def build_report(events):
    """Build a deterministic JSON report string from an ordered list of events.

    Returns a compact JSON string with ensure_ascii=False and sorted keys.
    The input list is never mutated.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Validate every event first, collecting ids to check uniqueness.
    seen_ids = set()
    for index, event in enumerate(events):
        _validate_event(event, index)
        event_id = event["id"]
        if event_id in seen_ids:
            raise ReportError(
                "duplicate event id {0!r} at index {1}".format(event_id, index)
            )
        seen_ids.add(event_id)

    # Group events by category, preserving insertion order of first occurrence.
    groups_by_category = OrderedDict()
    totals_by_category = OrderedDict()
    counts_by_category = OrderedDict()
    event_ids_by_category = OrderedDict()

    for event in events:
        category = event["category"]
        if category not in groups_by_category:
            groups_by_category[category] = True
            totals_by_category[category] = 0
            counts_by_category[category] = 0
            event_ids_by_category[category] = []
        totals_by_category[category] += event["amount_cents"]
        counts_by_category[category] += 1
        event_ids_by_category[category].append(event["id"])

    # Build group objects sorted by category in descending Unicode code-point order.
    sorted_categories = sorted(
        groups_by_category.keys(), key=lambda c: c, reverse=True
    )

    groups = []
    grand_total = 0
    for category in sorted_categories:
        ids_sorted = sorted(event_ids_by_category[category])
        group_obj = {
            "category": category,
            "count": counts_by_category[category],
            "events": ids_sorted,
            "total_cents": totals_by_category[category],
        }
        groups.append(group_obj)
        grand_total += totals_by_category[category]

    report = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )