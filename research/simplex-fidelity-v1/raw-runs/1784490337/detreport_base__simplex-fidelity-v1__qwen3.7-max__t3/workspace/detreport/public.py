"""Public API for detreport."""

from __future__ import annotations

import copy
import json
from typing import Any


class ReportError(Exception):
    """Raised when input validation fails."""


def _validate_events(events: Any) -> None:
    """Validate the top-level collection and every individual event.

    Raises ReportError on any problem.  Never mutates *events*.
    """
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    seen_ids: set[str] = set()

    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise ReportError(f"event at index {idx} is not a dict")

        keys = set(ev.keys())
        expected = {"id", "category", "amount_cents"}
        if keys != expected:
            extra = keys - expected
            missing = expected - keys
            parts: list[str] = []
            if missing:
                parts.append(f"missing fields {sorted(missing)}")
            if extra:
                parts.append(f"extra fields {sorted(extra)}")
            raise ReportError(
                f"event at index {idx}: {', '.join(parts)}"
            )

        eid = ev["id"]
        if not isinstance(eid, str) or eid == "":
            raise ReportError(
                f"event at index {idx}: id must be a non-empty string"
            )

        cat = ev["category"]
        if not isinstance(cat, str) or cat == "":
            raise ReportError(
                f"event at index {idx}: category must be a non-empty string"
            )

        amt = ev["amount_cents"]
        # bool is a subclass of int in Python – reject booleans explicitly
        if isinstance(amt, bool) or not isinstance(amt, int):
            raise ReportError(
                f"event at index {idx}: amount_cents must be an integer (not bool)"
            )

        if eid in seen_ids:
            raise ReportError(f"duplicate event id: {eid!r}")
        seen_ids.add(eid)


def build_report(events: list[dict[str, Any]]) -> str:
    """Build a deterministic JSON report from *events*.

    Parameters
    ----------
    events:
        A list of event dicts, each with exactly the keys
        ``id`` (non-empty str), ``category`` (non-empty str),
        and ``amount_cents`` (int, non-bool).

    Returns
    -------
    str
        Compact JSON (ensure_ascii=False, sorted keys) with top-level
        keys ``groups`` and ``grand_total_cents``.

    Raises
    ------
    ReportError
        On any validation failure.  The input list is never mutated.
    """
    # Work on a deep copy so the caller's data is never touched.
    events_copy = copy.deepcopy(events)

    _validate_events(events_copy)

    # --- group by category ------------------------------------------------
    groups_map: dict[str, dict[str, Any]] = {}
    grand_total = 0

    for ev in events_copy:
        cat: str = ev["category"]
        amt: int = ev["amount_cents"]
        eid: str = ev["id"]

        grand_total += amt

        if cat not in groups_map:
            groups_map[cat] = {
                "category": cat,
                "count": 0,
                "total_cents": 0,
                "events": [],
            }
        g = groups_map[cat]
        g["count"] += 1
        g["total_cents"] += amt
        g["events"].append(eid)

    # Sort event-id lists ascending
    for g in groups_map.values():
        g["events"].sort()

    # Order groups by category in ascending Unicode code-point order
    sorted_groups = [
        groups_map[cat] for cat in sorted(groups_map.keys())
    ]

    report = {
        "grand_total_cents": grand_total,
        "groups": sorted_groups,
    }

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
