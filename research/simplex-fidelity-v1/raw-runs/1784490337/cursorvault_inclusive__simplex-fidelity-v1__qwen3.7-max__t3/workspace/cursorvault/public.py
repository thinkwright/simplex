"""Public API for cursorvault."""

import copy


class CursorError(Exception):
    """Raised when a cursor is malformed or references an unknown record."""


def paginate(records, cursor=None, limit=3):
    """Return a page of records using cursor-based pagination.

    Parameters
    ----------
    records : list[dict]
        Each dict must have a unique ``id`` field (string).
    cursor : str or None
        The id of the first record to include in the page.
    limit : int
        Maximum number of records to return (1–100 inclusive).
        Booleans are **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str|None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in [1, 100].
    CursorError
        If *cursor* is not ``None`` and does not match any record id.
    """

    # --- validate limit (R3, X1) ---
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 to 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be an integer from 1 to 100, got {limit!r}"
        )

    # --- empty input (R5) ---
    if not records:
        return {"items": [], "next_cursor": None, "has_more": False}

    # --- resolve cursor (R4, X2) ---
    if cursor is not None:
        start = None
        for idx, rec in enumerate(records):
            if rec.get("id") == cursor:
                start = idx
                break
        if start is None:
            raise CursorError(f"Unknown cursor: {cursor!r}")
    else:
        start = 0

    # --- build page (R2, R4, R5, R6) ---
    end = start + limit
    items = copy.deepcopy(records[start:end])

    if end < len(records):
        has_more = True
        next_cursor = records[end]["id"]
    else:
        has_more = False
        next_cursor = None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
