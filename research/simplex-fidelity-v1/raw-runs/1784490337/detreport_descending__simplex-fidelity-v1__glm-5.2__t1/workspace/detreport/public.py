"""Public API for building deterministic event reports.

Only the Python standard library is used (see :mod:`json`), in keeping with
the ``detreport_contract`` constraint that amounts and totals are integer
cents implemented with the standard library only.
"""

import json

__all__ = ["build_report", "ReportError"]


class ReportError(Exception):
    """Raised when the event collection or any single event is invalid."""


_REQUIRED_KEYS = frozenset({"id", "category", "amount_cents"})


def _validate_events(events):
    """Validate the event collection and return a list of validated tuples.

    Each returned tuple is ``(category, event_id, amount_cents)``.  The input
    collection and its event dicts are never mutated: this function only reads
    from them.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a JSON array (list)")

    seen_ids = set()
    validated = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(
                "event at index {0} is not an object (dict)".format(index)
            )

        if set(event.keys()) != _REQUIRED_KEYS:
            raise ReportError(
                "event at index {0} must have exactly the keys "
                "id, category, amount_cents".format(index)
            )

        event_id = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        if not isinstance(event_id, str) or event_id == "":
            raise ReportError(
                "event at index {0} has an invalid id: "
                "must be a non-empty string".format(index)
            )
        if not isinstance(category, str) or category == "":
            raise ReportError(
                "event at index {0} has an invalid category: "
                "must be a non-empty string".format(index)
            )
        # bool is a subclass of int, so reject it explicitly.
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                "event at index {0} has an invalid amount_cents: "
                "must be an integer (not a boolean)".format(index)
            )

        if event_id in seen_ids:
            raise ReportError("duplicate event id: {0!r}".format(event_id))
        seen_ids.add(event_id)

        validated.append((category, event_id, amount))

    return validated


def build_report(events):
    """Build a deterministic JSON report string from ``events``.

    ``events`` is a list of event dicts.  Each event must be a dict with
    exactly ``id`` (non-empty string), ``category`` (non-empty string) and
    ``amount_cents`` (integer, not boolean).  Ids must be unique.

    Returns a compact JSON string (``ensure_ascii=False``, sorted keys) with
    exactly the top-level keys ``groups`` and ``grand_total_cents``.  The
    input is never mutated.
    """
    validated = _validate_events(events)

    groups_by_category = {}
    grand_total_cents = 0
    for category, event_id, amount in validated:
        grand_total_cents += amount
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
        group["total_cents"] += amount
        group["events"].append(event_id)

    for group in groups_by_category.values():
        group["events"].sort()

    # Order group objects by category in descending Unicode code-point order.
    groups = sorted(
        groups_by_category.values(),
        key=lambda group: group["category"],
        reverse=True,
    )

    report = {"groups": groups, "grand_total_cents": grand_total_cents}
    return json.dumps(
        report,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    )