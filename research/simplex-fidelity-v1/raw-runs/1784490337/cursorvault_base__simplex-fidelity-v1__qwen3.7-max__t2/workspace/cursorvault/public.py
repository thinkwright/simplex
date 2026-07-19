"""Public API for cursorvault."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CursorError(Exception):
    """Raised when a cursor is malformed or references an unknown record."""


def paginate(
    records: List[Dict[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """Return a page of *records* using cursor-based pagination.

    Parameters
    ----------
    records:
        A list of dicts, each containing a unique ``"id"`` field (string).
    cursor:
        The ``id`` of the last record already seen by the caller.
        ``None`` means "start from the beginning".
    limit:
        Maximum number of items to return (1 – 100 inclusive).
        Booleans are **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str | None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in [1, 100].
    CursorError
        If *cursor* is malformed or does not match any record id.
    """

    # ── validate limit (X1) ──────────────────────────────────────────
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit!r}"
        )

    # ── validate cursor (X2) ─────────────────────────────────────────
    start_index: int = 0

    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError(
                f"cursor must be a string id or None, got {cursor!r}"
            )
        # Find the record whose id matches the cursor.
        found = False
        for idx, record in enumerate(records):
            if record.get("id") == cursor:
                start_index = idx + 1
                found = True
                break
        if not found:
            raise CursorError(
                f"cursor {cursor!r} does not match any record id"
            )

    # ── build the page (R2, R4, R5, R6) ──────────────────────────────
    # Use slicing (creates shallow copies of the list, not the dicts)
    # so we never mutate the caller's list or dicts.
    page_records = records[start_index : start_index + limit]

    # items: shallow-copy the list but keep the same dict references.
    # We must NOT mutate any record dict, and we return them as-is.
    items: List[Dict[str, Any]] = list(page_records)

    remaining_after_page = len(records) - (start_index + limit)
    has_more: bool = remaining_after_page > 0

    if has_more:
        # next_cursor is the id of the last record in the current page (R4)
        next_cursor: Optional[str] = items[-1]["id"]
    else:
        next_cursor = None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
