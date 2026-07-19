"""Core implementation of cursor-based pagination.

Only the Python standard library is used.
"""

from typing import Any, Iterable, List, Mapping, Optional


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown position."""


def _is_int(value: Any) -> bool:
    # bool is a subclass of int in Python; the contract excludes booleans.
    return isinstance(value, int) and not isinstance(value, bool)


def paginate(
    records: Iterable[Mapping[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> dict:
    """Return a page of records using a decimal string cursor.

    Args:
        records: An iterable of mappings. Each record must have a unique
            string ``id`` field. The iterable is consumed into a list; the
            input is not mutated.
        cursor: Optional decimal zero-based index of the first record to
            return. ``None`` starts at the beginning.
        limit: Integer page size in [1, 100]. Booleans are not valid.

    Returns:
        A dict with exactly three keys: ``items`` (a list of records in
        input order), ``next_cursor`` (decimal string index of the next
            page's first record, or ``None`` when no records remain), and
        ``has_more`` (bool, true iff records remain after this page).

    Raises:
        ValueError: If ``limit`` is not an int in [1, 100].
        CursorError: If ``cursor`` is non-null and not a valid decimal
            index, or refers to a position past the end of records.
    """
    # --- validate limit (X1) ---
    if not _is_int(limit):
        raise ValueError("limit must be an integer between 1 and 100")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")

    # --- materialize records without mutating the input (R6) ---
    # Build a fresh list of references; do not deep-copy record dicts.
    # The contract forbids mutating any record dict, but does not require
    # defensive copies of the records themselves.
    records_list: List[Mapping[str, Any]] = list(records)

    # --- parse cursor (X2) ---
    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a decimal string or null")
        s = cursor
        # Disallow empty, whitespace, signs, and non-digits.
        if s == "" or any(ch.isspace() for ch in s):
            raise CursorError("cursor must be a decimal string or null")
        if s[0] in ("+", "-"):
            raise CursorError("cursor must be a decimal string or null")
        if not all("0" <= ch <= "9" for ch in s):
            raise CursorError("cursor must be a decimal string or null")
        # Reject leading zeros for non-zero values to keep the format strict.
        if len(s) > 1 and s[0] == "0":
            raise CursorError("cursor must be a decimal string or null")
        start = int(s)
        # A cursor strictly past the end is unknown; a cursor at the end
        # is a valid terminal page (no items, has_more=False).
        if start > len(records_list):
            raise CursorError("cursor is beyond the end of records")

    # --- slice the page ---
    end = start + limit
    items = records_list[start:end]

    # --- compute next_cursor / has_more (R4, R5) ---
    if end < len(records_list):
        next_cursor: Optional[str] = str(end)
        has_more = True
    else:
        next_cursor = None
        has_more = False

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}