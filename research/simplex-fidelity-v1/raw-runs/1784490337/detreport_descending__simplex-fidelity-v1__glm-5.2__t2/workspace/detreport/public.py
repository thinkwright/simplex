"""Public API for building deterministic event reports.

All amounts and totals are integer cents. Only the Python standard library
is used (``json``).
"""

import json

__all__ = ["build_report", "ReportError"]

# The exact set of keys a valid event dict must have.
_EVENT_KEYS = frozenset({"id", "category", "amount_cents"})


class ReportError(Exception):
    """Raised when the event collection or an individual event is invalid."""


def _validate_events(events):
    """Validate the event collection and each event without mutating input.

    Returns the list of events unchanged on success; raises ``ReportError``
    on any invalid input.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a JSON array (list)")

    seen_ids = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(
                "event at index %d must be an object (dict)" % index
            )
        if set(event.keys()) != _EVENT_KEYS:
            raise ReportError(
                "event at index %d must have exactly the keys "
                "id, category, amount_cents" % index
            )

        event_id = event["id"]
        if not isinstance(event_id, str) or event_id == "":
            raise ReportError(
                "event at index %d has an id that must be a non-empty string"
                % index
            )

        category = event["category"]
        if not isinstance(category, str) or category == "":
            raise ReportError(
                "event at index %d has a category that must be a non-empty "
                "string" % index
            )

        amount = event["amount_cents"]
        # bool is a subclass of int in Python; reject it explicitly.
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                "event at index %d has amount_cents that must be an integer "
                "(not a boolean)" % index
            )

        if event_id in seen_ids:
            raise ReportError(
                "duplicate event id %r at index %d" % (event_id, index)
            )
        seen_ids.add(event_id)

    return events


def build_report(events):
    """Build a deterministic report string from an ordered list of events.

    Each event must be a dict with exactly ``id`` (unique non-empty string),
    ``category`` (non-empty string) and ``amount_cents`` (integer, not bool).
    The input is never mutated.

    Returns compact JSON (``ensure_ascii=False``, sorted keys) with exactly
    ``grand_total_cents`` and ``groups`` at the top level. Groups are ordered
    by category in descending Unicode code-point order; each group has exactly
    ``category``, ``count``, ``total_cents`` and ``events`` (ids sorted
    ascending).
    """
    _validate_events(events)

    # Group events by category without mutating the input events.
    groups_by_category = {}
    for event in events:
        category = event["category"]
        group = groups_by_category.get(category)
        if group is None:
            group = {
                "category": category,
                "count": 0,
                "total_cents": 0,
                "events": [],
            }
            groups_by_category[category] = group
        group["count"] += 1
        group["total_cents"] += event["amount_cents"]
        group["events"].append(event["id"])

    for group in groups_by_category.values():
        group["events"].sort()

    # Order group objects by category in descending Unicode code-point order.
    ordered_groups = [
        groups_by_category[category]
        for category in sorted(groups_by_category, reverse=True)
    ]

    grand_total_cents = sum(event["amount_cents"] for event in events)

    report = {
        "grand_total_cents": grand_total_cents,
        "groups": ordered_groups,
    }

    return json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )