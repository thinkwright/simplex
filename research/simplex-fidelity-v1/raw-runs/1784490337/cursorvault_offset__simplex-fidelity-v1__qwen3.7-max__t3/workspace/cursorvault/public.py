"""Public API for CursorVault pagination."""


class CursorError(Exception):
    """Raised when a cursor is malformed or unknown."""
    pass


def paginate(records, cursor=None, limit=3):
    """
    Paginate a list of records using cursor-based pagination.
    
    Args:
        records: List of dicts with unique string id fields
        cursor: Optional string representing decimal zero-based index, or None
        limit: Integer from 1 to 100 inclusive (booleans not allowed)
    
    Returns:
        Dict with keys: items, next_cursor, has_more
    
    Raises:
        ValueError: If limit is invalid
        CursorError: If cursor is malformed or unknown
    """
    # Validate limit - booleans are not integers for this contract
    if isinstance(limit, bool):
        raise ValueError("limit must be an integer, not a boolean")
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100 inclusive")
    
    # Validate and parse cursor
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string or None")
        try:
            start_idx = int(cursor)
        except ValueError:
            raise CursorError("cursor must be a decimal index string")
        if start_idx < 0:
            raise CursorError("cursor must be non-negative")
        if len(records) == 0 or start_idx >= len(records):
            raise CursorError("cursor index out of range")
    else:
        start_idx = 0
    
    # Get items for this page (slicing creates a new list, doesn't mutate)
    end_idx = start_idx + limit
    items = records[start_idx:end_idx]
    
    # Determine next_cursor and has_more
    if end_idx < len(records):
        next_cursor = str(end_idx)
        has_more = True
    else:
        next_cursor = None
        has_more = False
    
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more
    }
