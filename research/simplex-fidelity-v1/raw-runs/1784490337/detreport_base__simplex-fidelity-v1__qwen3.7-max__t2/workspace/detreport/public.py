"""Public API for detreport."""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List


class ReportError(Exception):
    """Raised when input events are invalid."""


def build_report(events: Any) -> str:
    """Build a deterministic JSON report from a list of event dicts.

    Parameters
    ----------
    events : list[dict]
        Each dict must have exactly three keys:
        - ``id``: non-empty string, unique across all events
        - ``category``: non-empty string
        - ``amount_cents``: integer (not bool)

    Returns
    -------
    str
        Compact JSON with ``ensure_ascii=False``, sorted keys,
        top-level keys ``groups`` and ``grand_total_cents``.

    Raises
    ------
    ReportError
        If the input is invalid.
    """
    # Validate top-level structure
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Deep-copy so we never mutate the caller's data
    events_copy: List[Dict[str, Any]] = copy.deepcopy(events)

    seen_ids: set[str] = set()
    grand_total: int = 0

    # category -> {total_cents, ids}
    groups_map: Dict[str, Dict[str, Any]] = {}

    for idx, event in enumerate(events_copy):
        if not isinstance(event, dict):
            raise ReportError(f"event at index {idx} is not a dict")

        # Exactly three required keys
        expected_keys = {"id", "category", "amount_cents"}
        if set(event.keys()) != expected_keys:
            extra = set(event.keys()) - expected_keys
            missing = expected_keys - set(event.keys())
            parts = []
            if extra:
                parts.append(f"extra keys: {extra}")
            if missing:
                parts.append(f"missing keys: {missing}")
            raise ReportError(
                f"event at index {idx} has invalid keys: {', '.join(parts)}"
            )

        eid = event["id"]
        category = event["category"]
        amount = event["amount_cents"]

        # Validate id
        if not isinstance(eid, str) or not eid:
            raise ReportError(f"event at index {idx}: id must be a non-empty string")

        # Validate category
        if not isinstance(category, str) or not category:
            raise ReportError(
                f"event at index {idx}: category must be a non-empty string"
            )

        # Validate amount_cents – must be int, not bool
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ReportError(
                f"event at index {idx}: amount_cents must be an integer (not bool)"
            )

        # Unique id check
        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)

        grand_total += amount

        if category not in groups_map:
            groups_map[category] = {"total_cents": 0, "ids": []}
        groups_map[category]["total_cents"] += amount
        groups_map[category]["ids"].append(eid)

    # Build group objects sorted by category (ascending Unicode code-point order)
    groups: List[Dict[str, Any]] = []
    for cat in sorted(groups_map.keys()):
        info = groups_map[cat]
        groups.append(
            {
                "category": cat,
                "count": len(info["ids"]),
                "events": sorted(info["ids"]),
                "total_cents": info["total_cents"],
            }
        )

    report = {
        "grand_total_cents": grand_total,
        "groups": groups,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
