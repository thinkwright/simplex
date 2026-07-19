"""Core implementation of detreport.

Uses only the Python standard library.
"""

import json


class ReportError(ValueError):
    """Raised when input events are invalid."""


def _validate_event(event, ids_seen):
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")

    if set(event.keys()) != {"id", "category", "amount_cents"}:
        raise ReportError(
            "event must contain exactly id, category, and amount_cents"
        )

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")

    if event_id in ids_seen:
        raise ReportError("duplicate event id: {!r}".format(event_id))
    ids_seen.add(event_id)

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    amount = event["amount_cents"]
    # bool is a subclass of int in Python; reject booleans explicitly.
    if isinstance(amount, bool):
        raise ReportError("event amount_cents must be an integer, not a boolean")
    if not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer")


def build_report(events):
    """Build a deterministic JSON report string from an iterable of events.

    Returns a compact JSON string with ``ensure_ascii=False`` and sorted keys.
    The input ``events`` is never mutated.
    """
    if events is None:
        raise ReportError("events must be a list")

    # Materialize once so we can iterate twice (validation + grouping) without
    # mutating the caller's container. We accept any iterable.
    try:
        materialized = list(events)
    except TypeError:
        raise ReportError("events must be iterable")

    ids_seen = set()
    for event in materialized:
        _validate_event(event, ids_seen)

    groups_by_category = {}
    running_total = 0
    for event in materialized:
        category = event["category"]
        amount = event["amount_cents"]
        running_total += amount

        bucket = groups_by_category.get(category)
        if bucket is None:
            bucket = {"category": category, "count": 0, "total_cents": 0, "events": []}
            groups_by_category[category] = bucket
        bucket["count"] += 1
        bucket["total_cents"] += amount
        bucket["events"].append(event["id"])

    # Sort event ids ascending within each group, then sort groups by category
    # in ascending Unicode code-point order.
    ordered_groups = []
    for category in sorted(groups_by_category.keys()):
        bucket = groups_by_category[category]
        bucket["events"] = sorted(bucket["events"])
        ordered_groups.append(bucket)

    report = {
        "groups": ordered_groups,
        "grand_total_cents": running_total,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))