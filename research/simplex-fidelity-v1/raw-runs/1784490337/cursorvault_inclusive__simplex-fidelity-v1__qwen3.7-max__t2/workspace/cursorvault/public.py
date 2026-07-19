"""Public API for the cursorvault package."""


class CursorError(Exception):
    """Raised when a cursor is malformed or references an unknown record."""


def paginate(records, cursor=None, limit=3):
    """Return a page of *records* starting at the record whose ``id`` equals *cursor*.

    Parameters
    ----------
    records : list[dict]
        Each dict must contain a unique string ``id`` field.
    cursor : str | None
        The ``id`` of the first record to include.  ``None`` starts from the
        beginning.
    limit : int
        Maximum number of items to return (1 – 100 inclusive).  Booleans are
        **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str | None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in the allowed range.
    CursorError
        If *cursor* is not ``None`` and does not match any record ``id``, or is
        not a string.
    """

    # ── validate limit (R3 / X1) ────────────────────────────────────────
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )

    # ── determine start index (R4 / X2) ─────────────────────────────────
    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str):
            raise CursorError(
                f"cursor must be a string id, got {type(cursor).__name__}"
            )
        start = None
        for i, record in enumerate(records):
            if record.get("id") == cursor:
                start = i
                break
        if start is None:
            raise CursorError(
                f"cursor {cursor!r} does not match any record id"
            )

    # ── build the page (R2 / R5 / R6) ───────────────────────────────────
    end = start + limit
    items = list(records[start:end])          # new list, same dict refs (no mutation)
    has_more = end < len(records)
    next_cursor = records[end]["id"] if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
