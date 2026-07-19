"""Core implementation of detreport."""

import json


class ReportError(Exception):
    """Raised when input events are invalid."""


_ALLOWED_EVENT_KEYS = {"id", "category", "amount_cents"}


def _validate_event(event, seen_ids):
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")
    keys = set(event.keys())
    if keys != _ALLOWED_EVENT_KEYS:
        extra = keys - _ALLOWED_EVENT_KEYS
        missing = _ALLOWED_EVENT_KEYS - keys
        problems = []
        if missing:
            problems.append("missing field(s): {}".format(", ".join(sorted(missing))))
        if extra:
            problems.append("extra field(s): {}".format(", ".join(sorted(extra))))
        raise ReportError("invalid event keys: " + "; ".join(problems))

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")
    if event_id in seen_ids:
        raise ReportError("duplicate event id: {}".format(event_id))

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    amount = event["amount_cents"]
    if isinstance(amount, bool):
        raise ReportError("event amount_cents must be an integer, not a boolean")
    if not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer")


def build_report(events):
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    # Validate all events first (without mutating input).
    for event in events:
        _validate_event(event, seen_ids)
        seen_ids.add(event["id"])

    # Group by category, preserving first-appearance order.
    order = []
    groups_by_category = {}
    for event in events:
        category = event["category"]
        if category not in groups_by_category:
            order.append(category)
            groups_by_category[category] = []
        groups_by_category[category].append(event)

    groups = []
    grand_total = 0
    for category in order:
        cat_events = groups_by_category[category]
        ids = sorted(e["id"] for e in cat_events)
        total = sum(e["amount_cents"] for e in cat_events)
        grand_total += total
        groups.append({
            "category": category,
            "count": len(cat_events),
            "events": ids,
            "total_cents": total,
        })

    report = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))