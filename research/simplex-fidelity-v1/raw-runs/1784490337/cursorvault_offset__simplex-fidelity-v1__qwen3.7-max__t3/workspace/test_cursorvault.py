#!/usr/bin/env python3
"""Test script to verify cursorvault implementation."""

from cursorvault import paginate, CursorError

def test_e1():
    """E1: paginate([{id: a}, {id: b}, {id: c}], null, 2) → {items: [{id: a}, {id: b}], next_cursor: "2", has_more: true}"""
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = paginate(records, None, 2)
    assert result == {"items": [{"id": "a"}, {"id": "b"}], "next_cursor": "2", "has_more": True}, f"E1 failed: {result}"
    print("✓ E1 passed")

def test_e2():
    """E2: paginate([{id: a}, {id: b}, {id: c}], "1", 2) → {items: [{id: b}, {id: c}], next_cursor: null, has_more: false}"""
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = paginate(records, "1", 2)
    assert result == {"items": [{"id": "b"}, {"id": "c"}], "next_cursor": None, "has_more": False}, f"E2 failed: {result}"
    print("✓ E2 passed")

def test_e3():
    """E3: limit 0 or true → ValueError"""
    records = [{"id": "a"}]
    
    # Test limit 0
    try:
        paginate(records, None, 0)
        assert False, "E3 failed: limit 0 should raise ValueError"
    except ValueError:
        pass
    
    # Test limit True (boolean)
    try:
        paginate(records, None, True)
        assert False, "E3 failed: limit True should raise ValueError"
    except ValueError:
        pass
    
    print("✓ E3 passed")

def test_e4():
    """E4: any valid records and arguments → records remain unchanged after paginate"""
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    records_copy = [dict(r) for r in records]
    
    paginate(records, None, 2)
    paginate(records, "1", 2)
    
    assert records == records_copy, f"E4 failed: records were mutated"
    print("✓ E4 passed")

def test_e5():
    """E5: cursor "missing" → CursorError"""
    records = [{"id": "a"}, {"id": "b"}]
    
    try:
        paginate(records, "missing", 2)
        assert False, "E5 failed: cursor 'missing' should raise CursorError"
    except CursorError:
        pass
    
    print("✓ E5 passed")

def test_e6():
    """E6: inspect the cursorvault package dependencies → every imported dependency is from the Python standard library or cursorvault itself"""
    # Check that public.py only imports from standard library or cursorvault
    with open('cursorvault/public.py', 'r') as f:
        content = f.read()
    
    # Should not have any external imports
    import_lines = [line for line in content.split('\n') if line.strip().startswith('import ') or line.strip().startswith('from ')]
    for line in import_lines:
        # Only cursorvault imports are allowed
        if 'cursorvault' not in line:
            assert False, f"E6 failed: external import found: {line}"
    
    print("✓ E6 passed")

def test_empty_records():
    """Test empty input returns empty terminal page"""
    result = paginate([], None, 2)
    assert result == {"items": [], "next_cursor": None, "has_more": False}, f"Empty records failed: {result}"
    print("✓ Empty records test passed")

def test_limit_validation():
    """Test limit validation"""
    records = [{"id": "a"}]
    
    # Test limit > 100
    try:
        paginate(records, None, 101)
        assert False, "limit 101 should raise ValueError"
    except ValueError:
        pass
    
    # Test limit False (boolean)
    try:
        paginate(records, None, False)
        assert False, "limit False should raise ValueError"
    except ValueError:
        pass
    
    # Test limit as string
    try:
        paginate(records, None, "2")
        assert False, "limit as string should raise ValueError"
    except ValueError:
        pass
    
    print("✓ Limit validation tests passed")

def test_cursor_validation():
    """Test cursor validation"""
    records = [{"id": "a"}, {"id": "b"}]
    
    # Test negative cursor
    try:
        paginate(records, "-1", 2)
        assert False, "negative cursor should raise CursorError"
    except CursorError:
        pass
    
    # Test cursor out of range
    try:
        paginate(records, "10", 2)
        assert False, "cursor out of range should raise CursorError"
    except CursorError:
        pass
    
    # Test non-string cursor
    try:
        paginate(records, 1, 2)
        assert False, "non-string cursor should raise CursorError"
    except CursorError:
        pass
    
    print("✓ Cursor validation tests passed")

if __name__ == "__main__":
    test_e1()
    test_e2()
    test_e3()
    test_e4()
    test_e5()
    test_e6()
    test_empty_records()
    test_limit_validation()
    test_cursor_validation()
    print("\n✅ All tests passed!")
