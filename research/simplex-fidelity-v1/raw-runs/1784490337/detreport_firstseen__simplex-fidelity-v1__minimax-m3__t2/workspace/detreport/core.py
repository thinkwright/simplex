"""Core implementation of the detreport builder.

Only the Python standard library is used.
"""

import json


class ReportError(Exception):
    """Raised when input events are invalid."""


_REQUIRED_EVENT_FIELDS = ("id", "category", "amount_cents")


def _validate_event(event, seen_ids):
    """Validate a single event dict.

    Returns the validated (id, category, amount_cents) tuple.
    Raises :class:`ReportError` on any invalid input.
    """
    if not isinstance(event, dict):
        raise ReportError("event must be a dict")

    # Reject extra fields beyond the three required ones.
    if len(event) != len(_REQUIRED_EVENT_FIELDS):
        # Distinguish missing vs extra for a descriptive message.
        keys = set(event.keys())
        required = set(_REQUIRED_EVENT_FIELDS)
        missing = required - keys
        extra = keys - required
        if missing:
            raise ReportError(
                "event missing required field(s): {0}".format(
                    ", ".join(sorted(missing))
                )
            )
        if extra:
            raise ReportError(
                "event has unexpected field(s): {0}".format(
                    ", ".join(sorted(extra))
                )
            )
        raise ReportError("event has invalid field set")

    event_id = event["id"]
    if not isinstance(event_id, str) or event_id == "":
        raise ReportError("event id must be a non-empty string")

    if event_id in seen_ids:
        raise ReportError("duplicate event id: {0}".format(event_id))

    category = event["category"]
    if not isinstance(category, str) or category == "":
        raise ReportError("event category must be a non-empty string")

    amount = event["amount_cents"]
    # bool is a subclass of int in Python; explicitly reject booleans.
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ReportError("event amount_cents must be an integer (not boolean)")

    return event_id, category, amount


def build_report(events):
    """Build a deterministic report from an ordered sequence of events.

    Parameters
    ----------
    events : sequence
        Sequence of event dicts. Each event must have exactly the keys
        ``id``, ``category``, and ``amount_cents``.

    Returns
    -------
    str
        Compact JSON string (UTF-8, ``ensure_ascii=False``) with sorted
        keys, containing ``groups`` and ``grand_total_cents``.

    Raises
    ------
    ReportError
        If the input is not a sequence of valid events.
    """
    # Validate the outer container without mutating it.
    if isinstance(events, str) or not hasattr(events, "__iter__"):
        raise ReportError("events must be an iterable of dicts")

    # Materialize once so we can iterate twice (validation + grouping)
    # without mutating the caller's input.
    try:
        materialized = list(events)
    except TypeError:
        raise ReportError("events must be an iterable of dicts")

    seen_ids = set()
    # Preserve first-appearance order of categories.
    category_order = []
    category_buckets = {}

    for index, event in enumerate(materialized):
        event_id, category, amount = _validate_event(event, seen_ids)
        seen_ids.add(event_id)

        bucket = category_buckets.get(category)
        if bucket is None:
            bucket = {"count": 0, "total_cents": 0, "events": []}
            category_buckets[category] = bucket
            category_order.append(category)

        bucket["count"] += 1
        bucket["total_cents"] += amount
        bucket["events"].append(event_id)

    grand_total = 0
    groups = []
    for category in category_order:
        bucket = category_buckets[category]
        groups.append({
            "category": category,
            "count": bucket["count"],
            "total_cents": bucket["total_cents"],
            "events": sorted(bucket["events"]),
        })
        grand_total += bucket["total_cents"]

    report = {
        "groups": groups,
        "grand_total_cents": grand_total,
    }

    return json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )