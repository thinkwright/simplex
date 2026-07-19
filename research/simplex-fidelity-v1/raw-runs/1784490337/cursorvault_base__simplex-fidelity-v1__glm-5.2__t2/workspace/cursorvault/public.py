"""Public API for the :mod:`cursorvault` package.

Exposes :func:`paginate` and :class:`CursorError`, which together implement
cursor-based pagination over a list of records that each carry a unique string
``id`` field.

This module depends only on the Python standard library.
"""

from __future__ import annotations


class CursorError(Exception):
    """Raised when a pagination cursor is malformed or references no record."""


def _validate_limit(limit: object) -> int:
    """Return ``limit`` when it is an int in the range [1, 100].

    Booleans are rejected even though ``bool`` subclasses ``int`` in Python.
    Raises :class:`ValueError` otherwise. ``records`` is never touched here.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer between 1 and 100, "
            "got value of type {!r}".format(type(limit).__name__)
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be between 1 and 100 inclusive, got {}".format(limit)
        )
    return limit


def _index_records(records: object) -> dict[str, int]:
    """Map each record's unique string ``id`` to its position in ``records``.

    Validates that ``records`` is a list of dicts each having a unique string
    ``id`` field. ``records`` and its member dicts are never mutated; a fresh
    mapping is returned.
    """
    if not isinstance(records, list):
        raise ValueError(
            "records must be a list of dicts with unique string 'id' fields, "
            "got value of type {!r}".format(type(records).__name__)
        )

    id_to_index: dict[str, int] = {}
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                "each record must be a dict with an 'id' field, "
                "got value of type {!r} at position {}".format(
                    type(record).__name__, position
                )
            )
        if "id" not in record:
            raise ValueError(
                "each record must have an 'id' field; "
                "missing at position {}".format(position)
            )
        record_id = record["id"]
        if not isinstance(record_id, str):
            raise ValueError(
                "record 'id' must be a string, got value of type {!r} "
                "at position {}".format(type(record_id).__name__, position)
            )
        if record_id in id_to_index:
            raise ValueError(
                "record ids must be unique; duplicate id {!r} "
                "at position {}".format(record_id, position)
            )
        id_to_index[record_id] = position
    return id_to_index


def paginate(
    records: list[dict[str, object]],
    cursor: str | None = None,
    limit: int = 3,
) -> dict[str, object]:
    """Return a single page of ``records`` using cursor-based pagination.

    The result is a new dict with exactly the keys ``items``, ``next_cursor``
    and ``has_more``. The input ``records`` list and its member dicts are never
    mutated, and equal inputs always yield equal results.

    ``cursor`` is ``None`` for the first page, or the ``id`` of the last record
    already returned; the next page then begins immediately after that record.
    When records remain after the returned page, ``has_more`` is ``True`` and
    ``next_cursor`` is the ``id`` of the last item in the page; otherwise both
    are falsy/``None``.
    """
    limit = _validate_limit(limit)
    id_to_index = _index_records(records)

    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str):
            raise CursorError(
                "cursor must be a string id or None, got value of type {!r}".format(
                    type(cursor).__name__
                )
            )
        if cursor not in id_to_index:
            raise CursorError(
                "cursor {!r} does not match any record id".format(cursor)
            )
        start = id_to_index[cursor] + 1

    total = len(records)
    page = records[start : start + limit]
    has_more = (start + limit) < total
    next_cursor = page[-1]["id"] if has_more else None

    return {
        "items": list(page),
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


__all__ = ["CursorError", "paginate"]