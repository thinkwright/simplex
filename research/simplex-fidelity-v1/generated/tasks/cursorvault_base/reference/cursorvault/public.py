from __future__ import annotations

from copy import deepcopy


MODE = "exclusive"


class CursorError(ValueError):
    pass


def paginate(records: list[dict], cursor: str | None = None, limit: int = 3) -> dict:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    ids = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError("each record must have a string id")
        ids.append(record["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("record ids must be unique")

    if cursor is None:
        start = 0
    elif not isinstance(cursor, str):
        raise CursorError("cursor must be a string or null")
    elif MODE == "offset":
        if not cursor.isdigit():
            raise CursorError("cursor must be a decimal offset")
        start = int(cursor)
        if start > len(records):
            raise CursorError("cursor offset is outside the record list")
    else:
        try:
            index = ids.index(cursor)
        except ValueError as error:
            raise CursorError("cursor does not identify a record") from error
        start = index + 1 if MODE == "exclusive" else index

    end = min(len(records), start + limit)
    items = deepcopy(records[start:end])
    has_more = end < len(records)
    if not has_more:
        next_cursor = None
    elif MODE == "exclusive":
        next_cursor = ids[end - 1]
    elif MODE == "inclusive":
        next_cursor = ids[end]
    else:
        next_cursor = str(end)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
