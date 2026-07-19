"""Pagination implementation for cursorvault.

Uses only the Python standard library.
"""

from typing import Any, Iterable, List, Mapping, Optional


class CursorError(Exception):
    """Raised when a cursor is malformed or does not match any record."""


def _is_strict_int(value: Any) -> bool:
    # bool is a subclass of int in Python; reject it explicitly per R3.
    if isinstance(value, bool):
        return False
    return isinstance(value, int)


def _normalize_records(records: Iterable[Any]) -> List[Mapping[str, Any]]:
    if isinstance(records, (str, bytes)):
        raise TypeError("records must be an iterable of mappings, not a string")
    if not hasattr(records, "__iter__"):
        raise TypeError("records must be iterable")
    result: List[Mapping[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise TypeError(
                "record at index {0} is not a mapping".format(index)
            )
        result.append(record)
    return result


def paginate(
    records: Iterable[Mapping[str, Any]],
    cursor: Optional[str] = None,
    limit: int = 3,
) -> dict:
    """Return a page of records starting at ``cursor`` with at most ``limit`` items.

    The returned dict has exactly three keys: ``items``, ``next_cursor``,
    ``has_more``. Input records are not mutated.
    """
    # --- validate limit (R3, X1) ---
    if not _is_strict_int(limit):
        raise ValueError("limit must be an integer between 1 and 100")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")

    # --- normalize records without mutating them (R6) ---
    normalized = _normalize_records(records)

    # --- determine start index from cursor (R4, X2) ---
    start = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string")
        found = False
        for i, record in enumerate(normalized):
            rid = record.get("id")
            if not isinstance(rid, str):
                raise CursorError("record id must be a string")
            if rid == cursor:
                start = i
                found = True
                break
        if not found:
            raise CursorError("cursor does not match any record id")

    # --- slice the page (R2, R4, R5) ---
    page = normalized[start : start + limit]
    has_more = (start + limit) < len(normalized)
    next_cursor: Optional[str] = None
    if has_more:
        next_cursor = normalized[start + limit]["id"]

    # --- build result; do not share references with input records (R6) ---
    items = [dict(record) for record in page]
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}