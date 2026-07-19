"""Public API for detreport."""

from __future__ import annotations

import json
from typing import Any, Dict, List


class ReportError(Exception):
    """Raised when input events are invalid."""


def _validate_events(events: Any) -> None:
    """Validate the top-level events collection and each individual event."""
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids: set = set()

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ReportError(f"event at index {idx} is not a dict")

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
                f"event at index {idx} has invalid keys: {'; '.join(parts)}"
            )

        eid = event["id"]
        if not isinstance(eid, str) or eid == "":
            raise ReportError(
                f"event at index {idx}: id must be a non-empty string"
            )

        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)

        cat = event["category"]
        if not isinstance(cat, str) or cat == "":
            raise ReportError(
                f"event at index {idx}: category must be a non-empty string"
            )

        amt = event["amount_cents"]
        if isinstance(amt, bool) or not isinstance(amt, int):
            raise ReportError(
                f"event at index {idx}: amount_cents must be an integer (non-boolean)"
            )


def build_report(events: List[Dict[str, Any]]) -> str:
    """Build a deterministic JSON report from a list of event dicts.

    Parameters
    ----------
    events:
        A list of dicts, each with exactly the keys ``id`` (non-empty str),
        ``category`` (non-empty str), and ``amount_cents`` (int, not bool).

    Returns
    -------
    str
        Compact JSON with sorted keys, ``ensure_ascii=False``, containing
        top-level ``groups`` and ``grand_total_cents``.

    Raises
    ------
    ReportError
        If the input is invalid.
    """
    _validate_events(events)

    # Build groups without mutating input
    groups_map: Dict[str, Dict[str, Any]] = {}
    grand_total = 0

    for event in events:
        eid: str = event["id"]
        cat: str = event["category"]
        amt: int = event["amount_cents"]

        grand_total += amt

        if cat not in groups_map:
            groups_map[cat] = {
                "category": cat,
                "count": 0,
                "total_cents": 0,
                "events": [],
            }

        groups_map[cat]["count"] += 1
        groups_map[cat]["total_cents"] += amt
        groups_map[cat]["events"].append(eid)

    # Sort event ids ascending within each group
    for group in groups_map.values():
        group["events"] = sorted(group["events"])

    # Order groups by category descending (Unicode code-point order)
    sorted_categories = sorted(groups_map.keys(), reverse=True)
    groups_list = [groups_map[cat] for cat in sorted_categories]

    report = {
        "grand_total_cents": grand_total,
        "groups": groups_list,
    }

    return json.dumps(report, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
