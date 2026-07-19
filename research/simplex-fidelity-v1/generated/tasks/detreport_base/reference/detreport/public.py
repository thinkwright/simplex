from __future__ import annotations

import json


MODE = "ascending"


class ReportError(ValueError):
    pass


def _validate(events: object) -> list[dict]:
    if not isinstance(events, list):
        raise ReportError("events must be a list")
    seen = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != {"id", "category", "amount_cents"}:
            raise ReportError("event has invalid fields")
        if not isinstance(event["id"], str) or not event["id"] or event["id"] in seen:
            raise ReportError("event id must be unique and non-empty")
        if not isinstance(event["category"], str) or not event["category"]:
            raise ReportError("category must be a non-empty string")
        if isinstance(event["amount_cents"], bool) or not isinstance(event["amount_cents"], int):
            raise ReportError("amount_cents must be an integer")
        seen.add(event["id"])
    return events


def build_report(events) -> str:
    _validate(events)
    grouped: dict[str, dict] = {}
    order = []
    grand_total = 0
    for event in events:
        category = event["category"]
        if category not in grouped:
            grouped[category] = {"category": category, "count": 0, "total_cents": 0, "events": []}
            order.append(category)
        group = grouped[category]
        group["count"] += 1
        group["total_cents"] += event["amount_cents"]
        group["events"].append(event["id"])
        grand_total += event["amount_cents"]
    if MODE == "ascending":
        order = sorted(order)
    elif MODE == "descending":
        order = sorted(order, reverse=True)
    for group in grouped.values():
        group["events"].sort()
    result = {"groups": [grouped[key] for key in order], "grand_total_cents": grand_total}
    return json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
