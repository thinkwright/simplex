"""Public API for detreport."""

import json


class ReportError(Exception):
    """Raised when input validation fails."""
    pass


def build_report(events):
    """Build a deterministic report from a list of event dicts.

    Args:
        events: list of dicts, each with exactly keys 'id', 'category', 'amount_cents'

    Returns:
        JSON string with groups and grand_total_cents

    Raises:
        ReportError: if input is invalid
    """
    # Validate top-level structure
    if not isinstance(events, list):
        raise ReportError("events must be a list")

    # Validate each event and collect them (without mutating input)
    seen_ids = set()
    validated_events = []

    for event in events:
        if not isinstance(event, dict):
            raise ReportError("each event must be a dict")

        # Check exact keys
        if set(event.keys()) != {'id', 'category', 'amount_cents'}:
            raise ReportError("each event must have exactly keys: id, category, amount_cents")

        event_id = event['id']
        category = event['category']
        amount_cents = event['amount_cents']

        # Validate id
        if not isinstance(event_id, str) or not event_id:
            raise ReportError("id must be a non-empty string")

        # Validate category
        if not isinstance(category, str) or not category:
            raise ReportError("category must be a non-empty string")

        # Validate amount_cents (must be int, not bool)
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            raise ReportError("amount_cents must be an integer (not boolean)")

        # Check unique id
        if event_id in seen_ids:
            raise ReportError(f"duplicate id: {event_id}")
        seen_ids.add(event_id)

        validated_events.append({
            'id': event_id,
            'category': category,
            'amount_cents': amount_cents,
        })

    # Group by category, preserving first-appearance order
    category_order = []
    groups_dict = {}

    for event in validated_events:
        cat = event['category']
        if cat not in groups_dict:
            category_order.append(cat)
            groups_dict[cat] = {
                'category': cat,
                'count': 0,
                'total_cents': 0,
                'events': [],
            }
        groups_dict[cat]['count'] += 1
        groups_dict[cat]['total_cents'] += event['amount_cents']
        groups_dict[cat]['events'].append(event['id'])

    # Sort event ids within each group
    for cat in groups_dict:
        groups_dict[cat]['events'].sort()

    # Build groups list in first-appearance order
    groups = [groups_dict[cat] for cat in category_order]

    # Calculate grand total
    grand_total_cents = sum(e['amount_cents'] for e in validated_events)

    # Build result
    result = {
        'groups': groups,
        'grand_total_cents': grand_total_cents,
    }

    # Return compact JSON with sorted keys and ensure_ascii=False
    return json.dumps(result, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
