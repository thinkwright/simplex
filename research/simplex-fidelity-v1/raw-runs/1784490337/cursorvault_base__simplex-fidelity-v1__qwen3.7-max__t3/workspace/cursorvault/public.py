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
        Ordered list of dicts, each with a unique ``"id"`` string field.
    cursor:
        The ``id`` of the last record already seen (``None`` for the first page).
    limit:
        Maximum number of items to return (1–100 inclusive).  Booleans are
        **not** accepted as integers.

    Returns
    -------
    dict
        ``{"items": [...], "next_cursor": str | None, "has_more": bool}``

    Raises
    ------
    ValueError
        If *limit* is not a valid integer in 1..100.
    CursorError
        If *cursor* is malformed or does not match any record id.
    """

    # ── validate limit (R3 / X1) ──────────────────────────────────────
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit!r}"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            f"limit must be an integer from 1 through 100, got {limit}"
        )

    # ── empty input (R5) ──────────────────────────────────────────────
    if not records:
        if cursor is not None:
            raise CursorError(f"unknown cursor: {cursor!r}")
        return {"items": [], "next_cursor": None, "has_more": False}

    # ── resolve cursor position (R4 / X2) ─────────────────────────────
    start: int = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError(f"malformed cursor: expected a string, got {type(cursor).__name__}")
        for idx, record in enumerate(records):
            if record.get("id") == cursor:
                start = idx + 1
                break
        else:
            raise CursorError(f"unknown cursor: {cursor!r}")

    # ── build page (R2 / R5 / R6) ─────────────────────────────────────
    page: List[Dict[str, Any]] = records[start : start + limit]
    has_more: bool = (start + limit) < len(records)
    next_cursor: Optional[str] = page[-1]["id"] if has_more and page else None

    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
