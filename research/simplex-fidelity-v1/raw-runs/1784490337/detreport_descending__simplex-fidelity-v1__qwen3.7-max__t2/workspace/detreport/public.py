"""Public API for detreport."""

import copy
import json


class ReportError(Exception):
    """Raised when input events are invalid."""


def _validate_events(events):
    """Validate the event collection and each event dict.

    Returns a deep copy so the original input is never mutated.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Deep-copy to guarantee no mutation of caller data
    events_copy = copy.deepcopy(events)

    seen_ids = set()
    for i, ev in enumerate(events_copy):
        if not isinstance(ev, dict):
            raise ReportError(f"event at index {i} is not a dict")

        # Exactly three keys allowed
        if set(ev.keys()) != {"id", "category", "amount_cents"}:
            raise ReportError(
                f"event at index {i} has unexpected keys: {set(ev.keys())}"
            )

        # id: non-empty string
        eid = ev["id"]
        if not isinstance(eid, str) or eid == "":
            raise ReportError(f"event at index {i} has invalid id")

        # category: non-empty string
        cat = ev["category"]
        if not isinstance(cat, str) or cat == "":
            raise ReportError(f"event at index {i} has invalid category")

        # amount_cents: integer, not boolean
        amt = ev["amount_cents"]
        if isinstance(amt, bool) or not isinstance(amt, int):
            raise ReportError(f"event at index {i} has invalid amount_cents")

        # unique id
        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)

    return events_copy


def build_report(events):
    """Build a deterministic JSON report string from *events*.

    Parameters
    ----------
    events : list[dict]
        Each dict must have exactly the keys ``id`` (non-empty str),
        ``category`` (non-empty str), and ``amount_cents`` (int, not bool).

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
    validated = _validate_events(events)

    # Group by category
    groups_map = {}  # category -> {ids: [], total: int}
    grand_total = 0

    for ev in validated:
        cat = ev["category"]
        amt = ev["amount_cents"]
        grand_total += amt
        if cat not in groups_map:
            groups_map[cat] = {"ids": [], "total": 0}
        groups_map[cat]["ids"].append(ev["id"])
        groups_map[cat]["total"] += amt

    # Build group objects; sort ids ascending within each group
    groups = []
    for cat in groups_map:
        info = groups_map[cat]
        groups.append({
            "category": cat,
            "count": len(info["ids"]),
            "events": sorted(info["ids"]),
            "total_cents": info["total"],
        })

    # R5: order groups by category descending Unicode code-point order
    groups.sort(key=lambda g: g["category"], reverse=True)

    report = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
