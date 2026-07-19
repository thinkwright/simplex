"""Public API for cursorvault."""

__all__ = ["paginate", "CursorError"]


class CursorError(Exception):
    """Raised when a cursor is malformed or references an unknown record."""


def paginate(records, cursor=None, limit=3):
    """Return a page of *records* starting after the given *cursor*.

    Parameters
    ----------
    records : list[dict]
        Each dict must contain a unique ``"id"`` key whose value is a string.
    cursor : str or None
        If not ``None``, the id of the first record to **include** in the
        returned page.
    limit : int
        Maximum number of records to return (1 – 100 inclusive).
        Booleans are **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str|None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in 1..100.
    CursorError
        If *cursor* is malformed or does not match any record id.
    """

    # --- validate limit (X1) ------------------------------------------------
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 to 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be between 1 and 100 inclusive, got {limit}"
        )

    # --- validate cursor (X2) -----------------------------------------------
    if cursor is not None and not isinstance(cursor, str):
        raise CursorError(f"cursor must be a string or None, got {cursor!r}")

    # --- locate start index --------------------------------------------------
    start = 0
    if cursor is not None:
        for idx, rec in enumerate(records):
            if rec.get("id") == cursor:
                start = idx
                break
        else:
            raise CursorError(f"unknown cursor: {cursor!r}")

    # --- build page ----------------------------------------------------------
    end = start + limit
    items = list(records[start:end])  # shallow copy of the slice

    if end < len(records):
        has_more = True
        next_cursor = records[end]["id"]
    else:
        has_more = False
        next_cursor = None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
