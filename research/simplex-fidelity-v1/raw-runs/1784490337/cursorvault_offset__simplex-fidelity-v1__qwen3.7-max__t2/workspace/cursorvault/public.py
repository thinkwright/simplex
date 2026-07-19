"""Public API for cursorvault."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CursorError(Exception):
    """Raised when a cursor value is malformed or unknown."""


def paginate(
    records: List[Dict[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """Return a page of *records* using cursor-based pagination.

    Parameters
    ----------
    records:
        Sequence of dicts, each with a unique ``id`` field.
    cursor:
        ``None`` (start from the beginning) or a decimal zero-based index
        string indicating the first record to return.
    limit:
        Maximum number of items per page (1 – 100 inclusive).
        Booleans are **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str | None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not an integer in 1 – 100.
    CursorError
        If *cursor* is malformed or unknown.
    """

    # ── validate limit (R3 / X1) ──────────────────────────────────────
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit!r}"
        )

    # ── validate cursor (R4 / X2) ─────────────────────────────────────
    start: int = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError(
                f"cursor must be a decimal index string or None, got {cursor!r}"
            )
        # Must parse as an integer
        try:
            start = int(cursor)
        except (ValueError, TypeError):
            raise CursorError(f"malformed cursor: {cursor!r}")
        # Must be non-negative
        if start < 0:
            raise CursorError(f"unknown cursor (negative index): {cursor!r}")
        # Must be the canonical decimal representation (no leading zeros, etc.)
        if cursor != str(start):
            raise CursorError(f"malformed cursor: {cursor!r}")

    # ── paginate (R2, R4, R5, R6) ─────────────────────────────────────
    total = len(records)

    if start > total:
        # Cursor points past the end – still a valid cursor, just no data.
        return {"items": [], "next_cursor": None, "has_more": False}

    end = min(start + limit, total)
    # Shallow-copy the slice so the caller's list is not mutated;
    # individual record dicts are referenced but never modified (R6).
    items = list(records[start:end])

    has_more = end < total
    next_cursor: Optional[str] = str(end) if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
