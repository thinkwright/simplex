"""Public API for the detreport package."""

import copy
import json


class ReportError(Exception):
    """Raised when input validation fails."""


def _validate_events(events):
    """Validate the event collection and each event dict.

    Returns a deep-copied list of validated events (original is never mutated).
    Raises ReportError on any validation failure.
    """
    if not isinstance(events, list):
        raise ReportError("Input must be a JSON array (list) of events.")

    seen_ids = set()
    validated = []

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(
                f"Event at index {idx} is not a dict."
            )

        # Exactly three keys required
        expected_keys = {"id", "category", "amount_cents"}
        actual_keys = set(event.keys())
        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            parts = []
            if missing:
                parts.append(f"missing keys: {missing}")
            if extra:
                parts.append(f"extra keys: {extra}")
            raise ReportError(
                f"Event at index {idx} has invalid keys ({'; '.join(parts)})."
            )

        eid = event["id"]
        category = event["category"]
        amount_cents = event["amount_cents"]

        # id: non-empty string
        if not isinstance(eid, str) or len(eid) == 0:
            raise ReportError(
                f"Event at index {idx}: 'id' must be a non-empty string."
            )

        # category: non-empty string
        if not isinstance(category, str) or len(category) == 0:
            raise ReportError(
                f"Event at index {idx}: 'category' must be a non-empty string."
            )

        # amount_cents: integer, non-boolean
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            raise ReportError(
                f"Event at index {idx}: 'amount_cents' must be an integer (not boolean)."
            )

        # unique id
        if eid in seen_ids:
            raise ReportError(
                f"Duplicate event id: {eid!r}."
            )
        seen_ids.add(eid)

        # Store a copy so we never mutate input
        validated.append({
            "id": eid,
            "category": category,
            "amount_cents": amount_cents,
        })

    return validated


def build_report(events):
    """Build a deterministic report JSON string from a list of event dicts.

    Parameters
    ----------
    events : list[dict]
        Each dict must have exactly the keys ``id`` (non-empty str),
        ``category`` (non-empty str), and ``amount_cents`` (int, not bool).

    Returns
    -------
    str
        Compact JSON (ensure_ascii=False, sort_keys=True) with top-level
        keys ``groups`` and ``grand_total_cents``.

    Raises
    ------
    ReportError
        If the input is invalid.
    """
    validated = _validate_events(events)

    # Group by category, preserving first-appearance order (R5)
    # We use a list of (category, group_dict) to maintain insertion order.
    category_order = []  # list of category strings in first-appearance order
    groups_map = {}      # category -> {"ids": [], "total_cents": 0}

    grand_total_cents = 0

    for ev in validated:
        cat = ev["category"]
        if cat not in groups_map:
            category_order.append(cat)
            groups_map[cat] = {"ids": [], "total_cents": 0}
        groups_map[cat]["ids"].append(ev["id"])
        groups_map[cat]["total_cents"] += ev["amount_cents"]
        grand_total_cents += ev["amount_cents"]

    # Build group objects (R3)
    groups = []
    for cat in category_order:
        g = groups_map[cat]
        groups.append({
            "category": cat,
            "count": len(g["ids"]),
            "events": sorted(g["ids"]),  # ascending sort (R3)
            "total_cents": g["total_cents"],
        })

    report = {
        "grand_total_cents": grand_total_cents,
        "groups": groups,
    }

    # R4: compact, ensure_ascii=False, sorted keys
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
