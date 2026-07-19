"""Public API for the detreport package."""

import json


class ReportError(Exception):
    """Raised when the input events are invalid."""


_REQUIRED_KEYS = {"id", "category", "amount_cents"}


def build_report(events):
    """Build a compact JSON report grouping events by category.

    ``events`` must be a list of dicts each having exactly the keys
    ``id`` (unique non-empty string), ``category`` (non-empty string)
    and ``amount_cents`` (integer, not a boolean). The input is never
    mutated. A :class:`ReportError` is raised for any invalid input.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    categories = {}
    category_order = []
    grand_total_cents = 0

    for event in events:
        if not isinstance(event, dict):
            raise ReportError("each event must be a dict")
        if set(event.keys()) != _REQUIRED_KEYS:
            raise ReportError(
                "each event must have exactly id, category and amount_cents"
            )

        event_id = event["id"]
        category = event["category"]
        amount_cents = event["amount_cents"]

        if not isinstance(event_id, str) or event_id == "":
            raise ReportError("id must be a non-empty string")
        if not isinstance(category, str) or category == "":
            raise ReportError("category must be a non-empty string")
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            raise ReportError("amount_cents must be an integer and not a boolean")
        if event_id in seen_ids:
            raise ReportError("duplicate id: " + repr(event_id))
        seen_ids.add(event_id)

        if category not in categories:
            categories[category] = {"ids": [], "total_cents": 0, "count": 0}
            category_order.append(category)
        bucket = categories[category]
        bucket["ids"].append(event_id)
        bucket["total_cents"] += amount_cents
        bucket["count"] += 1
        grand_total_cents += amount_cents

    groups = []
    for category in category_order:
        bucket = categories[category]
        groups.append(
            {
                "category": category,
                "count": bucket["count"],
                "total_cents": bucket["total_cents"],
                "events": sorted(bucket["ids"]),
            }
        )

    report = {"grand_total_cents": grand_total_cents, "groups": groups}
    return json.dumps(
        report, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )