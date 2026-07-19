"""Public API for CursorVault pagination."""


class CursorError(Exception):
    """Raised when a cursor is malformed or references an unknown position."""
    pass


def paginate(records, cursor=None, limit=3):
    """
    Paginate a list of records using cursor-based pagination.
    
    Args:
        records: List of dicts, each with a unique 'id' field
        cursor: Optional string representing zero-based index, or None
        limit: Integer from 1 to 100 (booleans not allowed)
    
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
    start_index = 0
    if cursor is not None:
        if not isinstance(cursor, str):
            raise CursorError("cursor must be a string or None")
        
        try:
            start_index = int(cursor)
        except ValueError:
            raise CursorError(f"cursor '{cursor}' is not a valid decimal index")
        
        if start_index < 0:
            raise CursorError(f"cursor '{cursor}' is negative")
        
        if start_index > len(records):
            raise CursorError(f"cursor '{cursor}' is beyond the end of records")
    
    # Slice records from start_index
    remaining = records[start_index:]
    
    # Take up to limit items
    items = remaining[:limit]
    
    # Calculate next_cursor and has_more
    has_more = len(remaining) > limit
    
    if has_more:
        next_cursor = str(start_index + limit)
    else:
        next_cursor = None
    
    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more
    }
