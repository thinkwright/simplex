"""Core pagination logic."""

from .errors import CursorError


def paginate(records, cursor=None, limit=3):
    """Return a page of records starting at ``cursor`` (the id of the first
    record to include), with at most ``limit`` items.

    The returned dict has exactly three keys: ``items``, ``next_cursor``,
    and ``has_more``. Input records are not mutated.
    """
    # Validate limit per R3: integer 1..100, booleans excluded.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer between 1 and 100")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100")

    # Empty input is a terminal page per R5.
    if not records:
        return {"items": [], "next_cursor": None, "has_more": False}

    # Build an id -> record index preserving input order.
    index = {}
    for record in records:
        rid = record["id"]
        if rid in index:
            # Duplicate id violates the uniqueness precondition; treat as
            # malformed input by surfacing a CursorError-like failure.
            raise CursorError("duplicate id in records: {!r}".format(rid))
        index[rid] = record

    # Resolve starting position per R4.
    if cursor is None:
        ordered_ids = list(index.keys())
        start = 0
    else:
        if cursor not in index:
            raise CursorError("unknown cursor: {!r}".format(cursor))
        ordered_ids = list(index.keys())
        start = ordered_ids.index(cursor)

    page_ids = ordered_ids[start:start + limit]
    items = [index[rid] for rid in page_ids]

    remaining = len(ordered_ids) - (start + len(page_ids))
    if remaining > 0:
        next_cursor = ordered_ids[start + len(page_ids)]
        has_more = True
    else:
        next_cursor = None
        has_more = False

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}