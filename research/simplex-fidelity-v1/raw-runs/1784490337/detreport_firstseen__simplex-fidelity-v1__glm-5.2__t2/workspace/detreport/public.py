"""Public API for the detreport package.

All amounts and totals are integer cents. Only the Python standard library is
used by this module.
"""

import json


class ReportError(Exception):
    """Raised when report input is invalid."""


def _validate_event(event, index):
    """Validate a single event and return its (id, category, amount_cents).

    Raises ReportError if the event is not a dict with exactly the keys
    ``id``, ``category`` and ``amount_cents`` whose values meet the contract.
    """
    if not isinstance(event, dict):
        raise ReportError(f"event at index {index} is not a dict")
    if set(event.keys()) != {"id", "category", "amount_cents"}:
        raise ReportError(
            f"event at index {index} must have exactly the keys "
            f"id, category, amount_cents"
        )
    event_id = event["id"]
    category = event["category"]
    amount = event["amount_cents"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError(f"event at index {index} has an invalid id")
    if not isinstance(category, str) or category == "":
        raise ReportError(f"event at index {index} has an invalid category")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ReportError(f"event at index {index} has an invalid amount_cents")
    return event_id, category, amount


def build_report(events):
    """Build a deterministic JSON report string from an ordered event list.

    The input is never mutated. The returned string is compact JSON
    (``ensure_ascii=False``, sorted keys) with exactly the top-level keys
    ``groups`` and ``grand_total_cents``.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    order = []
    groups = {}
    grand_total = 0

    for index, event in enumerate(events):
        event_id, category, amount = _validate_event(event, index)
        if event_id in seen_ids:
            raise ReportError(f"duplicate event id {event_id!r}")
        seen_ids.add(event_id)
        if category not in groups:
            order.append(category)
            groups[category] = {"count": 0, "total_cents": 0, "events": []}
        group = groups[category]
        group["count"] += 1
        group["total_cents"] += amount
        group["events"].append(event_id)
        grand_total += amount

    group_objects = []
    for category in order:
        group = groups[category]
        group_objects.append(
            {
                "category": category,
                "count": group["count"],
                "total_cents": group["total_cents"],
                "events": sorted(group["events"]),
            }
        )

    report = {
        "groups": group_objects,
        "grand_total_cents": grand_total,
    }
    return json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )