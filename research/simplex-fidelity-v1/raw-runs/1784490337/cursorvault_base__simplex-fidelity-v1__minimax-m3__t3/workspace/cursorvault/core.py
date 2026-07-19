"""Core implementation of cursor-based pagination.

Only the Python standard library is used.
"""

from typing import Any, Dict, List, Optional


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown record."""


def _is_valid_limit(limit: Any) -> bool:
    # Booleans are not integers for this contract.
    if isinstance(limit, bool):
        return False
    if not isinstance(limit, int):
        return False
    return 1 <= limit <= 100


def paginate(
    records: List[Dict[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """Return a page of ``records`` after ``cursor`` with at most ``limit`` items.

    The returned dict has exactly three keys: ``items``, ``next_cursor``, and
    ``has_more``. ``records`` and its dicts are not mutated.
    """
    if not _is_valid_limit(limit):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive; "
            "booleans are not integers"
        )

    # Build an index of id -> position without mutating records.
    id_to_index: Dict[str, int] = {}
    for idx, record in enumerate(records):
        record_id = record.get("id")
        if not isinstance(record_id, str):
            raise CursorError("record missing string id field")
        if record_id in id_to_index:
            raise CursorError("record ids must be unique")
        id_to_index[record_id] = idx

    start = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string or null")
        if cursor not in id_to_index:
            raise CursorError("cursor does not match any record id")
        start = id_to_index[cursor] + 1

    end = start + limit
    page = records[start:end]

    if len(page) < len(records) - start:
        has_more = True
        next_cursor = page[-1]["id"]
    else:
        has_more = False
        next_cursor = None

    # Return shallow copies of the record dicts so callers cannot mutate input.
    items = [dict(record) for record in page]

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }