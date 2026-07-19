"""Public API for the detreport package.

Only the Python standard library is used here (``json``).
"""

import json

__all__ = ["ReportError", "build_report"]

# The exact set of keys every event dict must contain.
_REQUIRED_KEYS = frozenset({"id", "category", "amount_cents"})


class ReportError(Exception):
    """Raised when the event collection or an individual event is invalid."""


def _validate_events(events):
    """Validate the event collection and return a list of (id, category, amount).

    The input is never mutated. Any validation failure raises ``ReportError``.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    validated = []

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError("event at index %d must be a dict" % index)

        if set(event.keys()) != _REQUIRED_KEYS:
            raise ReportError(
                "event at index %d must have exactly id, category, amount_cents"
                % index
            )

        event_id = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        if not isinstance(event_id, str) or event_id == "":
            raise ReportError("event at index %d has an invalid id" % index)

        if not isinstance(category, str) or category == "":
            raise ReportError("event at index %d has an invalid category" % index)

        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ReportError("event at index %d has an invalid amount_cents" % index)

        if event_id in seen_ids:
            raise ReportError("duplicate event id: %r" % event_id)
        seen_ids.add(event_id)

        validated.append((event_id, category, amount))

    return validated


def build_report(events):
    """Build a deterministic JSON report string from ``events``.

    ``events`` is a list of dicts each with exactly ``id`` (unique non-empty
    string), ``category`` (non-empty string) and ``amount_cents`` (integer,
    not a bool). The input is never mutated.

    Returns a compact JSON string (``ensure_ascii=False``, sorted keys) with
    exactly two top-level keys: ``groups`` and ``grand_total_cents``.
    """
    validated = _validate_events(events)

    groups_by_category = {}
    grand_total_cents = 0

    for event_id, category, amount in validated:
        grand_total_cents += amount
        group = groups_by_category.get(category)
        if group is None:
            group = {"category": category, "ids": [], "total_cents": 0, "count": 0}
            groups_by_category[category] = group
        group["ids"].append(event_id)
        group["total_cents"] += amount
        group["count"] += 1

    groups = []
    for category in sorted(groups_by_category):
        group = groups_by_category[category]
        groups.append(
            {
                "category": group["category"],
                "count": group["count"],
                "total_cents": group["total_cents"],
                "events": sorted(group["ids"]),
            }
        )

    report = {"groups": groups, "grand_total_cents": grand_total_cents}

    return json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )