"""Public API for the detreport package."""

import json

__all__ = ["build_report", "ReportError"]


class ReportError(Exception):
    """Raised when the input event collection or any event is invalid."""


_REQUIRED_KEYS = frozenset({"id", "category", "amount_cents"})


def _validate_events(events):
    if not isinstance(events, list):
        raise ReportError("events must be a JSON array (list)")
    seen_ids = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError("event at index %d is not an object" % index)
        if set(event.keys()) != _REQUIRED_KEYS:
            raise ReportError(
                "event at index %d must have exactly id, category, amount_cents"
                % index
            )
        event_id = event["id"]
        if not isinstance(event_id, str) or not event_id:
            raise ReportError("event at index %d has an invalid id" % index)
        category = event["category"]
        if not isinstance(category, str) or not category:
            raise ReportError("event at index %d has an invalid category" % index)
        amount = event["amount_cents"]
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ReportError("event at index %d has an invalid amount_cents" % index)
        if event_id in seen_ids:
            raise ReportError("duplicate id %r at index %d" % (event_id, index))
        seen_ids.add(event_id)


def build_report(events):
    """Build a deterministic JSON report string from a list of events.

    Each event must be a dict with exactly ``id`` (non-empty string),
    ``category`` (non-empty string) and ``amount_cents`` (integer, non-boolean).
    The input is never mutated.
    """
    _validate_events(events)

    groups = {}
    grand_total_cents = 0
    for event in events:
        category = event["category"]
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
        group["total_cents"] += event["amount_cents"]
        group["events"].append(event["id"])
        grand_total_cents += event["amount_cents"]

    ordered_groups = [
        groups[category] for category in sorted(groups.keys())
    ]
    for group in ordered_groups:
        group["events"].sort()

    report = {
        "groups": ordered_groups,
        "grand_total_cents": grand_total_cents,
    }
    return json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )