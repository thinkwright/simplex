"""Public API for the detreport package.

This module depends only on the Python standard library.
"""

import json

__all__ = ["build_report", "ReportError"]

_REQUIRED_KEYS = frozenset({"id", "category", "amount_cents"})


class ReportError(Exception):
    """Raised when the event collection or an individual event is invalid."""


def build_report(events):
    """Build a compact JSON report from an ordered collection of events.

    Each event must be a ``dict`` with exactly the keys ``id``, ``category``
    and ``amount_cents``. ``id`` and ``category`` must be non-empty strings,
    ``amount_cents`` must be an integer that is not a ``bool``, and every
    ``id`` must be unique across the collection.

    The input is never mutated. The returned value is a compact JSON string
    (``ensure_ascii=False``, sorted keys) whose top level contains exactly
    ``groups`` and ``grand_total_cents``.

    Raises:
        ReportError: if the collection or any event is invalid.
    """
    validated = _validate(events)
    groups = _group(validated)
    grand_total_cents = sum(event["amount_cents"] for event in validated)
    report = {"grand_total_cents": grand_total_cents, "groups": groups}
    return json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _validate(events):
    """Validate the event collection without mutating it.

    Returns a list of freshly-built event dicts mirroring the input data.
    """
    if not isinstance(events, (list, tuple)):
        raise ReportError("events must be a list or tuple")
    seen_ids = set()
    validated = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(
                "event at index {} is not a dict".format(index)
            )
        if set(event.keys()) != _REQUIRED_KEYS:
            raise ReportError(
                "event at index {} must have exactly id, category and "
                "amount_cents keys".format(index)
            )
        event_id = event["id"]
        category = event["category"]
        amount = event["amount_cents"]
        if not isinstance(event_id, str) or not event_id:
            raise ReportError(
                "event at index {} has an invalid id".format(index)
            )
        if not isinstance(category, str) or not category:
            raise ReportError(
                "event at index {} has an invalid category".format(index)
            )
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ReportError(
                "event at index {} has an invalid amount_cents".format(index)
            )
        if event_id in seen_ids:
            raise ReportError("duplicate event id: {}".format(event_id))
        seen_ids.add(event_id)
        validated.append(
            {"id": event_id, "category": category, "amount_cents": amount}
        )
    return validated


def _group(validated):
    """Group validated events by category into ordered group objects."""
    buckets = {}
    for event in validated:
        category = event["category"]
        bucket = buckets.get(category)
        if bucket is None:
            bucket = {"ids": [], "total_cents": 0}
            buckets[category] = bucket
        bucket["ids"].append(event["id"])
        bucket["total_cents"] += event["amount_cents"]
    groups = []
    for category in sorted(buckets.keys()):
        bucket = buckets[category]
        groups.append(
            {
                "category": category,
                "count": len(bucket["ids"]),
                "total_cents": bucket["total_cents"],
                "events": sorted(bucket["ids"]),
            }
        )
    return groups