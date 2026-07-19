"""Verification tests for the cursorvault public API (examples E1-E6)."""

import copy
import sys
import types

from cursorvault.public import paginate, CursorError


def test_e1_basic_pagination():
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = paginate(records, None, 2)
    assert result == {
        "items": [{"id": "a"}, {"id": "b"}],
        "next_cursor": "c",
        "has_more": True,
    }, result
    # exactly three keys
    assert set(result) == {"items", "next_cursor", "has_more"}
    # items retain input order
    assert [r["id"] for r in result["items"]] == ["a", "b"]


def test_e2_cursor_inclusive_terminal():
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = paginate(records, "b", 2)
    assert result == {
        "items": [{"id": "b"}, {"id": "c"}],
        "next_cursor": None,
        "has_more": False,
    }, result


def test_e3_invalid_limit():
    records = [{"id": "a"}, {"id": "b"}]
    for bad in (0, True, False, 101, -1, 1.5, "3", None):
        try:
            paginate(records, None, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for limit=%r" % (bad,))
    # records unchanged after invalid limit
    assert records == [{"id": "a"}, {"id": "b"}]
    # valid boundaries accepted
    assert paginate(records, None, 1)["items"] == [{"id": "a"}]
    assert paginate(records, None, 100)["has_more"] is False


def test_e4_no_mutation_and_stable():
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    snapshot = copy.deepcopy(records)
    paginate(records, None, 2)
    paginate(records, "b", 5)
    assert records == snapshot
    # repeated calls with equal inputs return equal results
    r1 = paginate(records, None, 2)
    r2 = paginate(records, None, 2)
    assert r1 == r2
    # returned items are the same record objects (not mutated copies)
    assert r1["items"][0] is records[0]


def test_e5_missing_cursor():
    records = [{"id": "a"}, {"id": "b"}]
    try:
        paginate(records, "zzz", 2)
    except CursorError:
        pass
    else:
        raise AssertionError("expected CursorError for missing cursor")
    assert records == [{"id": "a"}, {"id": "b"}]
    # malformed (unhashable) cursor also raises CursorError
    try:
        paginate(records, ["a"], 2)
    except CursorError:
        pass
    else:
        raise AssertionError("expected CursorError for malformed cursor")


def test_e6_stdlib_only():
    import cursorvault
    import cursorvault._core
    import cursorvault.public

    allowed = set(sys.stdlib_module_names)
    allowed.add("cursorvault")  # self-imports within the package are allowed

    for mod in (cursorvault, cursorvault._core, cursorvault.public):
        for name, value in vars(mod).items():
            if isinstance(value, types.ModuleType):
                top = value.__name__.split(".")[0]
                assert top in allowed, (
                    "%s imports non-stdlib/non-cursorvault module %s"
                    % (mod.__name__, value.__name__)
                )


def test_empty_input():
    result = paginate([], None, 3)
    assert result == {"items": [], "next_cursor": None, "has_more": False}


def test_default_limit():
    records = [{"id": str(i)} for i in range(5)]
    result = paginate(records)
    assert result == {
        "items": [{"id": "0"}, {"id": "1"}, {"id": "2"}],
        "next_cursor": "3",
        "has_more": True,
    }


def test_full_walk():
    records = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
    cursor = None
    seen = []
    while True:
        page = paginate(records, cursor, 2)
        seen.extend(page["items"])
        if not page["has_more"]:
            break
        cursor = page["next_cursor"]
    assert seen == records


def test_invalid_limit_before_cursor_error():
    # invalid limit takes precedence and raises ValueError, not CursorError
    records = [{"id": "a"}, {"id": "b"}]
    try:
        paginate(records, "missing", 0)
    except ValueError:
        pass
    except CursorError:
        raise AssertionError("limit error should precede cursor error")
    else:
        raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_e1_basic_pagination()
    test_e2_cursor_inclusive_terminal()
    test_e3_invalid_limit()
    test_e4_no_mutation_and_stable()
    test_e5_missing_cursor()
    test_e6_stdlib_only()
    test_empty_input()
    test_default_limit()
    test_full_walk()
    test_invalid_limit_before_cursor_error()
    print("all tests passed")