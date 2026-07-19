"""Core implementation of detreport."""

import json


class ReportError(Exception):
    """Raised when input events are invalid."""


def _validate_event(event, seen_ids):
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")
    # Exactly the required keys.
    required = {"id", "category", "amount_cents"}
    if set(event.keys()) != required:
        raise ReportError(
            "event must have exactly keys id, category, amount_cents"
        )

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")
    if event_id in seen_ids:
        raise ReportError("duplicate event id: {!r}".format(event_id))
    seen_ids.add(event_id)

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    amount = event["amount_cents"]
    # bool is a subclass of int in Python; reject booleans explicitly.
    if isinstance(amount, bool):
        raise ReportError("event amount_cents must not be a boolean")
    if not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer")


def build_report(events):
    """Build a deterministic JSON report string from an ordered events list.

    Returns a compact JSON string with ensure_ascii=False and sorted keys.
    The input list is never mutated.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    # Preserve order of first appearance per category.
    category_order = []
    groups_by_category = {}

    for index, event in enumerate(events):
        _validate_event(event, seen_ids)
        category = event["category"]
        amount = event["amount_cents"]
        event_id = event["id"]

        if category not in groups_by_category:
            category_order.append(category)
            groups_by_category[category] = {
                "category": category,
                "count": 0,
                "total_cents": 0,
                "events": [],
            }
        bucket = groups_by_category[category]
        bucket["count"] += 1
        bucket["total_cents"] += amount
        bucket["events"].append(event_id)

    # Sort event ids ascending within each group.
    for category in category_order:
        groups_by_category[category]["events"].sort()

    groups = [groups_by_category[category] for category in category_order]
    grand_total_cents = sum(event["amount_cents"] for event in events)

    report = {
        "groups": groups,
        "grand_total_cents": grand_total_cents,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True)