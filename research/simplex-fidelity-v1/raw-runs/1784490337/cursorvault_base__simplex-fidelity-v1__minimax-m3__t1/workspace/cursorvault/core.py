"""Core pagination implementation.

Uses only the Python standard library.
"""


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown record."""


def _validate_limit(limit):
    # R3: limit must be an int from 1..100; booleans are excluded.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer between 1 and 100 inclusive"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be an integer between 1 and 100 inclusive"
        )


def paginate(records, cursor=None, limit=3):
    """Return a page of records after ``cursor`` with at most ``limit`` items.

    R2: returns a dict with exactly ``items``, ``next_cursor``, ``has_more``.
    R4: a non-null cursor is the id of the last record already returned.
    R5: ``has_more`` is true iff records remain; ``next_cursor`` is the id of
        the last item in the current page when ``has_more`` is true, else null.
    R6: input records are not mutated.
    """
    _validate_limit(limit)

    # Defensive shallow copy so we never mutate the caller's list.
    records = list(records)

    if cursor is None:
        start = 0
    else:
        # R4 / X2: cursor must be a string id present in records.
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string id")
        found = -1
        for i, rec in enumerate(records):
            # R6: do not mutate rec; read id via get with default.
            rec_id = rec.get("id") if isinstance(rec, dict) else None
            if rec_id == cursor:
                found = i
                break
        if found < 0:
            raise CursorError("cursor does not match any record id")
        start = found + 1

    page = records[start:start + limit]
    has_more = start + len(page) < len(records)

    if has_more and page:
        next_cursor = page[-1].get("id") if isinstance(page[-1], dict) else None
    else:
        next_cursor = None

    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }