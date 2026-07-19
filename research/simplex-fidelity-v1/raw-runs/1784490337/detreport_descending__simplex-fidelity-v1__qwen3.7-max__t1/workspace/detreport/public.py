"""Public API for the detreport package."""

import json


class ReportError(Exception):
    """Raised when input events are invalid."""
    pass


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
        Compact JSON with sorted keys, ensure_ascii=False.

    Raises
    ------
    ReportError
        If the events collection or any individual event is invalid.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids = set()
    for event in events:
        if not isinstance(event, dict):
            raise ReportError("each event must be a dict")

        if set(event.keys()) != {"id", "category", "amount_cents"}:
            raise ReportError(
                "each event must have exactly the keys: id, category, amount_cents"
            )

        eid = event["id"]
        if not isinstance(eid, str) or not eid:
            raise ReportError("id must be a non-empty string")
        if eid in seen_ids:
            raise ReportError("duplicate event id: {}".format(eid))
        seen_ids.add(eid)

        cat = event["category"]
        if not isinstance(cat, str) or not cat:
            raise ReportError("category must be a non-empty string")

        amt = event["amount_cents"]
        if isinstance(amt, bool) or not isinstance(amt, int):
            raise ReportError("amount_cents must be an integer (not bool)")

    # --- build groups (input is never mutated) ---
    groups_map = {}  # category -> {"ids": [...], "total": int}
    grand_total = 0

    for event in events:
        cat = event["category"]
        amt = event["amount_cents"]
        if cat not in groups_map:
            groups_map[cat] = {"ids": [], "total": 0}
        groups_map[cat]["ids"].append(event["id"])
        groups_map[cat]["total"] += amt
        grand_total += amt

    # Descending Unicode code-point order for categories
    groups = []
    for cat in sorted(groups_map.keys(), reverse=True):
        g = groups_map[cat]
        groups.append({
            "category": cat,
            "count": len(g["ids"]),
            "events": sorted(g["ids"]),
            "total_cents": g["total"],
        })

    result = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
