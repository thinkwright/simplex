"""Public API for detreport."""

import copy
import json

__all__ = ["build_report", "ReportError"]


class ReportError(Exception):
    """Raised when input is invalid."""


def build_report(events):
    """Build a deterministic JSON report string from a list of event dicts.

    Parameters
    ----------
    events : list[dict]
        Each dict must have exactly the keys ``id`` (non-empty str),
        ``category`` (non-empty str), and ``amount_cents`` (int, not bool).

    Returns
    -------
    str
        Compact JSON with sorted keys, ``ensure_ascii=False``.

    Raises
    ------
    ReportError
        If the input is invalid.
    """
    # Validate top-level structure
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Deep-copy so we never mutate the caller's data
    events_copy = copy.deepcopy(events)

    seen_ids = set()
    # Track category first-appearance order and accumulate data
    category_order = []
    category_data = {}  # category -> {"total_cents": int, "ids": list}
    grand_total = 0

    for event in events_copy:
        if not isinstance(event, dict):
            raise ReportError("each event must be a dict")

        # Exactly three keys required
        if set(event.keys()) != {"id", "category", "amount_cents"}:
            raise ReportError(
                "each event must have exactly the keys: id, category, amount_cents"
            )

        eid = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        # Validate id
        if not isinstance(eid, str) or eid == "":
            raise ReportError("id must be a non-empty string")

        # Validate category
        if not isinstance(category, str) or category == "":
            raise ReportError("category must be a non-empty string")

        # Validate amount_cents: must be int, not bool
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError("amount_cents must be an integer (not bool)")

        # Check uniqueness of id
        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)

        # Accumulate
        if category not in category_data:
            category_order.append(category)
            category_data[category] = {"total_cents": 0, "ids": []}

        category_data[category]["total_cents"] += amount
        category_data[category]["ids"].append(eid)
        grand_total += amount

    # Build groups in first-appearance order
    groups = []
    for cat in category_order:
        data = category_data[cat]
        groups.append({
            "category": cat,
            "count": len(data["ids"]),
            "events": sorted(data["ids"]),
            "total_cents": data["total_cents"],
        })

    report = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
