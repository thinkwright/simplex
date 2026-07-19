"""Public API for the :mod:`cursorvault` package.

This module exposes :func:`paginate` and :class:`CursorError`, which together
implement offset-free, cursor-based pagination over a sequence of records
that each carry a unique string ``id`` field.

Only the Python standard library is used.
"""


class CursorError(Exception):
    """Raised when a pagination cursor is malformed or cannot be resolved.

    A cursor is malformed when it is not a string (and not ``None``) and it is
    unknown when no record carries the supplied id.
    """


def paginate(records, cursor=None, limit=3):
    """Return a single page of ``records`` identified by ``cursor``.

    Parameters
    ----------
    records:
        A sequence of mappings, each containing a unique string ``id``
        field. The input and every record mapping are left untouched.
    cursor:
        The ``id`` of the last record already returned, or ``None`` to begin
        from the first record. A non-null cursor must reference an existing
        record id; otherwise a :class:`CursorError` is raised.
    limit:
        The maximum number of items in the returned page. Must be an integer
        between 1 and 100 inclusive. Booleans are rejected even though they
        are ``int`` subclasses.

    Returns
    -------
    dict
        A dictionary with exactly the keys ``items``, ``next_cursor`` and
        ``has_more``. ``items`` preserves the input order. ``has_more`` is
        ``True`` exactly when records remain after the returned page.
        ``next_cursor`` is the id of the last item in the page when
        ``has_more`` is ``True`` and ``None`` otherwise.

    Raises
    ------
    ValueError
        If ``limit`` is invalid or ``records`` is malformed. Records are not
        modified before the error is raised.
    CursorError
        If ``cursor`` is malformed or does not match any record id. Records
        are not modified before the error is raised.
    """
    _validate_limit(limit)
    record_list = _coerce_records(records)
    _validate_records(record_list)

    start_index = _resolve_cursor(record_list, cursor)

    page = record_list[start_index:start_index + limit]
    has_more = (start_index + limit) < len(record_list)
    next_cursor = page[-1]["id"] if has_more else None

    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


def _validate_limit(limit):
    """Ensure ``limit`` is an integer in the inclusive range [1, 100]."""
    # Booleans are subclasses of int but are explicitly rejected.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer between 1 and 100 inclusive, "
            "got {!r}".format(limit)
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be between 1 and 100 inclusive, got {!r}".format(limit)
        )


def _coerce_records(records):
    """Return a shallow copy of ``records`` as a list without mutating it."""
    if isinstance(records, (str, bytes, bytearray)):
        raise ValueError("records must be a sequence of mappings, not a string")
    try:
        return list(records)
    except TypeError as exc:
        raise ValueError("records must be an iterable of mappings") from exc


def _validate_records(record_list):
    """Ensure every record is a mapping with a unique string ``id`` field."""
    seen = set()
    for index, record in enumerate(record_list):
        if not isinstance(record, dict):
            raise ValueError(
                "record at index {} must be a mapping, got {!r}".format(
                    index, record
                )
            )
        if "id" not in record:
            raise ValueError(
                "record at index {} is missing the 'id' field".format(index)
            )
        record_id = record["id"]
        if not isinstance(record_id, str):
            raise ValueError(
                "record at index {} has a non-string 'id': {!r}".format(
                    index, record_id
                )
            )
        if record_id in seen:
            raise ValueError(
                "duplicate record id {!r} at index {}".format(record_id, index)
            )
        seen.add(record_id)


def _resolve_cursor(record_list, cursor):
    """Return the index at which the current page should begin.

    A ``None`` cursor starts at index 0. A string cursor must match an
    existing record id; the page then begins immediately after that record.
    """
    if cursor is None:
        return 0
    if not isinstance(cursor, str):
        raise CursorError(
            "cursor must be a string id or None, got {!r}".format(cursor)
        )
    for index, record in enumerate(record_list):
        if record["id"] == cursor:
            return index + 1
    raise CursorError(
        "cursor {!r} does not match any record id".format(cursor)
    )