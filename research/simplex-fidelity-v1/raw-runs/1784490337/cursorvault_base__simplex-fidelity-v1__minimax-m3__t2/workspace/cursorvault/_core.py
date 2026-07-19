"""Core implementation of cursor-based pagination.

Only the Python standard library is used.
"""

from typing import Any, Dict, List, Optional


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown record."""


def _validate_limit(limit: Any) -> int:
    # Booleans are excluded: bool is a subclass of int, but the contract
    # treats booleans as not-integers.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    return limit


def _validate_records(records: Any) -> List[Dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError("records must be a list of dicts")
    return records


def paginate(
    records: List[Dict[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> Dict[str, Any]:
    """Return a page of records after ``cursor`` with at most ``limit`` items.

    The returned dict has exactly three keys: ``items``, ``next_cursor``,
    and ``has_more``. Input records and their dicts are not mutated.
    """
    _validate_limit(limit)
    validated = _validate_records(records)

    # Determine the starting index. A non-null cursor must reference the id
    # of the last record already returned; the next page begins after it.
    start = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string")
        found = False
        for idx, record in enumerate(validated):
            if not isinstance(record, dict):
                raise CursorError("record is not a dict")
            record_id = record.get("id")
            if not isinstance(record_id, str):
                raise CursorError("record id is not a string")
            if record_id == cursor:
                start = idx + 1
                found = True
                break
        if not found:
            raise CursorError("cursor does not match any record id")

    # Slice without mutating the input list.
    page = list(validated[start : start + limit])

    has_more = len(validated) > start + len(page)

    if has_more:
        # next_cursor is the id of the last record in the current page.
        next_cursor = page[-1]["id"]
    else:
        next_cursor = None

    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }