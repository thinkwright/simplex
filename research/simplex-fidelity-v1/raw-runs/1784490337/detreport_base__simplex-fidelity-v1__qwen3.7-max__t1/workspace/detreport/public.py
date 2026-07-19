"""Public API for detreport."""

import copy
import json


class ReportError(Exception):
    """Raised when input events are invalid."""


def build_report(events):
    """Build a deterministic JSON report string from a list of event dicts.

    Parameters
    ----------
    events : list[dict]
        Each dict must have exactly three keys:
        - id (non-empty str, unique across all events)
        - category (non-empty str)
        - amount_cents (int, not bool)

    Returns
    -------
    str
        Compact JSON (ensure_ascii=False, sorted keys) with top-level
        keys ``groups`` and ``grand_total_cents``.

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
    groups = {}  # category -> {total_cents, ids}
    grand_total = 0

    for i, event in enumerate(events_copy):
        if not isinstance(event, dict):
            raise ReportError(f"event at index {i} is not a dict")

        # Exactly three required keys
        expected_keys = {"id", "category", "amount_cents"}
        if set(event.keys()) != expected_keys:
            extra = set(event.keys()) - expected_keys
            missing = expected_keys - set(event.keys())
            parts = []
            if missing:
                parts.append(f"missing keys: {missing}")
            if extra:
                parts.append(f"extra keys: {extra}")
            raise ReportError(
                f"event at index {i} has invalid keys: {', '.join(parts)}"
            )

        eid = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        # Validate id
        if not isinstance(eid, str) or eid == "":
            raise ReportError(
                f"event at index {i}: id must be a non-empty string"
            )

        # Validate category
        if not isinstance(category, str) or category == "":
            raise ReportError(
                f"event at index {i}: category must be a non-empty string"
            )

        # Validate amount_cents – must be int but NOT bool
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                f"event at index {i}: amount_cents must be an integer (not bool)"
            )

        # Check uniqueness of id
        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)

        # Accumulate
        grand_total += amount
        if category not in groups:
            groups[category] = {"total_cents": 0, "ids": []}
        groups[category]["total_cents"] += amount
        groups[category]["ids"].append(eid)

    # Build sorted group list (ascending Unicode code-point order on category)
    sorted_categories = sorted(groups.keys())

    group_list = []
    for cat in sorted_categories:
        g = groups[cat]
        sorted_ids = sorted(g["ids"])
        group_list.append({
            "category": cat,
            "count": len(sorted_ids),
            "events": sorted_ids,
            "total_cents": g["total_cents"],
        })

    report = {
        "grand_total_cents": grand_total,
        "groups": group_list,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
