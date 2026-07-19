"""Core report building logic."""

import copy
import json


class ReportError(ValueError):
    """Raised when input events are invalid."""


_ALLOWED_EVENT_KEYS = {"id", "category", "amount_cents"}


def _validate_event(event, seen_ids):
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")
    keys = set(event.keys())
    if keys != _ALLOWED_EVENT_KEYS:
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
    if isinstance(amount, bool):
        raise ReportError("event amount_cents must not be a boolean")
    if not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer")


def build_report(events):
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Deep copy so input is never mutated.
    working = copy.deepcopy(events)

    seen_ids = set()
    for event in working:
        _validate_event(event, seen_ids)

    groups_map = {}
    grand_total = 0
    for event in working:
        category = event["category"]
        amount = event["amount_cents"]
        grand_total += amount
        group = groups_map.get(category)
        if group is None:
            group = {"category": category, "count": 0, "total_cents": 0, "events": []}
            groups_map[category] = group
        group["count"] += 1
        group["total_cents"] += amount
        group["events"].append(event["id"])

    groups = []
    for category in sorted(groups_map.keys()):
        g = groups_map[category]
        groups.append({
            "category": g["category"],
            "count": g["count"],
            "total_cents": g["total_cents"],
            "events": sorted(g["events"]),
        })

    output = {
        "groups": groups,
        "grand_total_cents": grand_total,
    }

    return json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))