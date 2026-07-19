"""Public API for the cursorvault package.

Exposes :func:`paginate` and :class:`CursorError` for cursor-based pagination
over a list of records.
"""

__all__ = ["CursorError", "paginate"]


class CursorError(Exception):
    """Raised when a cursor is malformed or unknown."""


def paginate(records, cursor=None, limit=3):
    """Return a page of ``records`` keyed by a decimal index cursor.

    The result is a new dict with exactly three keys:

    * ``items``: the records in the requested page, in input order.
    * ``next_cursor``: the decimal index immediately after the page when more
      records remain, otherwise ``None``.
    * ``has_more``: ``True`` exactly when records remain after the page.

    ``records`` is never mutated, nor are any of its record dicts. Equal inputs
    always produce equal outputs.

    Args:
        records: a list of records (each expected to have a unique string
            ``id`` field).
        cursor: ``None`` to start at the first record, or a string holding the
            decimal zero-based index of the first record to return.
        limit: an integer from 1 through 100 inclusive (booleans are rejected).

    Returns:
        dict with keys ``items``, ``next_cursor`` and ``has_more``.

    Raises:
        ValueError: if ``limit`` is not an integer in ``[1, 100]``.
        CursorError: if ``cursor`` is malformed or unknown.
    """
    # [R3]/[X1]: validate the limit before touching records. Booleans are a
    # subclass of int, so they are rejected explicitly.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer from 1 to 100, got " + repr(limit)
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be between 1 and 100 inclusive, got " + repr(limit)
        )

    # Guard against a missing record list with a descriptive message.
    if records is None:
        raise ValueError("records must be a list, not None")

    length = len(records)

    # [R4]/[X2]: resolve the cursor to a starting index without mutating
    # records. A non-null cursor is the decimal zero-based index of the first
    # record to return.
    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str):
            raise CursorError(
                "cursor must be a string of decimal digits or None, got "
                + repr(cursor)
            )
        # A valid decimal index is a non-empty run of ASCII digits only. This
        # rejects signs, whitespace, underscores, decimal points and unicode
        # digits while accepting leading zeros such as "01".
        if not (cursor.isascii() and cursor.isdigit()):
            raise CursorError("malformed cursor: " + repr(cursor))
        start = int(cursor)
        # An index equal to the length is the natural end position and yields
        # an empty terminal page; an index beyond the length is unknown.
        if start > length:
            raise CursorError(
                "cursor out of range: " + repr(cursor)
                + " (records has " + repr(length) + " items)"
            )

    # [R2]: build the page without mutating records or any record dict. The
    # slice produces a fresh list of references in input order.
    page = list(records[start:start + limit])
    end = start + len(page)

    # [R5]: has_more is true exactly when records remain after the page. The
    # next cursor is the decimal index immediately after the page when more
    # records remain, and null otherwise.
    has_more = end < length
    next_cursor = str(end) if has_more else None

    return {"items": page, "next_cursor": next_cursor, "has_more": has_more}