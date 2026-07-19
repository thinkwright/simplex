"""Public cursor-based pagination API for the cursorvault package.

The module exposes :func:`paginate` and :class:`CursorError` and uses only
the Python standard library (plus other ``cursorvault`` modules).
"""

from cursorvault.errors import CursorError

__all__ = ["paginate", "CursorError"]

# Limits outside this inclusive range are rejected (see [R3]/[X1]).
_MIN_LIMIT = 1
_MAX_LIMIT = 100
# The record field that carries the unique cursor identifier.
_ID_FIELD = "id"


def paginate(records, cursor=None, limit=3):
    """Return a single page of ``records`` keyed by string ``id``.

    The result is a new dict with exactly three keys:

    * ``items``        - the records on this page, in input order;
    * ``next_cursor`` - the ``id`` of the last item when more records
      remain, otherwise ``None``;
    * ``has_more``    - ``True`` exactly when records remain after this page.

    ``records`` must be a list (or tuple) of dicts, each carrying a unique
    string ``id`` field.  ``cursor``, when not ``None``, is the ``id`` of the
    last record already returned; the page begins immediately after it.

    ``limit`` must be an integer in ``[1, 100]``; booleans are rejected even
    though they are ``int`` subclasses.

    The input is never mutated: neither ``records`` nor any record dict is
    modified, and equal inputs always yield equal results.
    """
    # --- [R3]/[X1] validate limit before touching records ---------------
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )
    if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )

    # --- [R2] validate records: list of dicts with unique string ids -----
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list of dicts with unique string id fields"
        )

    id_to_index = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("each record must be a dict")
        if _ID_FIELD not in record:
            raise ValueError("each record must have an id field")
        record_id = record[_ID_FIELD]
        if not isinstance(record_id, str):
            raise ValueError("each record id must be a string")
        if record_id in id_to_index:
            raise ValueError("record ids must be unique")
        id_to_index[record_id] = index

    # --- [R4]/[X2] resolve the cursor into a start index ----------------
    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string id or None")
        if cursor not in id_to_index:
            raise CursorError("cursor does not match any record id")
        start = id_to_index[cursor] + 1

    # --- [R4]/[R5] build the page (a fresh list; input untouched) --------
    total = len(records)
    end = start + limit
    items = list(records[start:end])
    has_more = end < total

    # When ``has_more`` is true, ``items`` is guaranteed non-empty because
    # ``end < total`` implies ``start < total`` (limit >= 1), so the slice
    # contains at least ``records[start]``.
    next_cursor = items[-1][_ID_FIELD] if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}