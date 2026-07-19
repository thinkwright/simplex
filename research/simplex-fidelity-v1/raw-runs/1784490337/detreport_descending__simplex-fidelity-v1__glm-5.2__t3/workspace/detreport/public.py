"""Deterministic event report builder.

Public API:
    build_report(events) -> str
    ReportError
"""

import json


class ReportError(Exception):
    """Raised when the input event collection or any event is invalid."""


def build_report(events):
    """Build a deterministic JSON report string from an event collection.

    ``events`` must be a list of event dicts. Each event dict must have
    exactly the keys ``id`` (non-empty string, unique), ``category``
    (non-empty string) and ``amount_cents`` (integer, not a bool).

    The input is never mutated. Invalid input raises :class:`ReportError`.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    expected_keys = {"id", "category", "amount_cents"}
    seen_ids = set()
    categories = {}
    grand_total = 0

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError("event at index %d is not a dict" % index)
        if set(event.keys()) != expected_keys:
            raise ReportError(
                "event at index %d must have exactly id, category, "
                "amount_cents keys" % index
            )

        event_id = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        if not isinstance(event_id, str) or not event_id:
            raise ReportError(
                "event at index %d has invalid id" % index
            )
        if not isinstance(category, str) or not category:
            raise ReportError(
                "event at index %d has invalid category" % index
            )
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                "event at index %d has invalid amount_cents" % index
            )
        if event_id in seen_ids:
            raise ReportError("duplicate event id: %s" % event_id)
        seen_ids.add(event_id)

        grand_total += amount
        bucket = categories.get(category)
        if bucket is None:
            bucket = {"ids": [], "total": 0}
            categories[category] = bucket
        bucket["ids"].append(event_id)
        bucket["total"] += amount

    groups = []
    for category in sorted(categories, reverse=True):
        bucket = categories[category]
        groups.append(
            {
                "category": category,
                "count": len(bucket["ids"]),
                "total_cents": bucket["total"],
                "events": sorted(bucket["ids"]),
            }
        )

    report = {"groups": groups, "grand_total_cents": grand_total}
    return json.dumps(
        report,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )