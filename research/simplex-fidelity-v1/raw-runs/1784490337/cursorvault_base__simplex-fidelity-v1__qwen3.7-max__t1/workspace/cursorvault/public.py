"""Public API for cursorvault."""

import copy


class CursorError(Exception):
    """Raised when a cursor is malformed or does not match any record."""


def paginate(records, cursor=None, limit=3):
    """Return a page of *records* starting after the record identified by *cursor*.

    Parameters
    ----------
    records : list[dict]
        Each dict must contain a unique ``id`` field (string).
    cursor : str | None
        The ``id`` of the last record already returned.  ``None`` means
        start from the beginning.
    limit : int
        Maximum number of items to return (1 – 100 inclusive).
        Booleans are **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str|None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in 1 – 100.
    CursorError
        If *cursor* is not ``None`` and does not match any record id.
    """

    # ── validate limit (R3 / X1) ──────────────────────────────────────
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 to 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be an integer from 1 to 100, got {limit!r}"
        )

    # ── work on a shallow copy so we never mutate the caller's list ───
    records_list = list(records)

    # ── locate start index based on cursor (R4 / X2) ──────────────────
    if cursor is None:
        start = 0
    else:
        start = None
        for idx, record in enumerate(records_list):
            if record.get("id") == cursor:
                start = idx + 1
                break
        if start is None:
            raise CursorError(
                f"cursor {cursor!r} does not match any record id"
            )

    # ── slice the page (R2, R5) ───────────────────────────────────────
    page = records_list[start : start + limit]

    # Deep-copy each record dict so the caller's dicts are untouched (R6)
    items = [copy.deepcopy(r) for r in page]

    remaining = len(records_list) - (start + limit)
    has_more = remaining > 0

    if has_more:
        next_cursor = items[-1]["id"]
    else:
        next_cursor = None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
