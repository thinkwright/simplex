EXPECTED = ["C1", "R1", "R2", "R3", "R4", "R5", "R6", "D1", "X1", "X2"]
ROOT = project_root("cursorvault")

try:
    module = importlib.import_module("cursorvault.public")
    paginate = module.paginate
    CursorError = module.CursorError
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


RECORDS = [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "c", "v": 3}]


def first_expected():
    cursor = "2" if MODE == "offset" else ("c" if MODE == "inclusive" else "b")
    return {
        "items": deepcopy(RECORDS[:2]),
        "next_cursor": cursor,
        "has_more": True,
    }


def second_call():
    cursor = "1" if MODE == "offset" else "b"
    return paginate(deepcopy(RECORDS), cursor, 2)


def second_expected():
    start = 2 if MODE == "exclusive" else 1
    return {"items": deepcopy(RECORDS[start:]), "next_cursor": None, "has_more": False}


def check_first():
    expect_equal(paginate(deepcopy(RECORDS), None, 2), first_expected())


def check_first_common():
    result = paginate(deepcopy(RECORDS), None, 2)
    expect_equal(set(result), {"items", "next_cursor", "has_more"})
    expect_equal(result["items"], RECORDS[:2])


def check_first_metadata():
    result = paginate(deepcopy(RECORDS), None, 2)
    expect_equal(result["has_more"], True)
    if result["next_cursor"] is None:
        raise AssertionError("next_cursor must be present when records remain")


def check_second():
    expect_equal(second_call(), second_expected())


def check_second_terminal():
    # Use a cursor-neutral terminal page so this R5 check does not also grade
    # the R4 cursor interpretation selected by the variant.
    result = paginate(deepcopy(RECORDS), None, len(RECORDS))
    expect_equal(result["has_more"], False)
    expect_equal(result["next_cursor"], None)


def check_invalid_limit():
    expect_raises(ValueError, lambda: paginate(deepcopy(RECORDS), None, True))
    expect_raises(ValueError, lambda: paginate(deepcopy(RECORDS), None, 0))


def check_invalid_cursor():
    expect_raises(CursorError, lambda: paginate(deepcopy(RECORDS), "missing", 2))


def check_immutable():
    source = deepcopy(RECORDS)
    before = deepcopy(source)
    first = paginate(source, None, 2)
    second = paginate(source, None, 2)
    expect_equal(source, before)
    expect_equal(first, second)


def check_output_shape():
    result = paginate(deepcopy(RECORDS), None, 1)
    expect_equal(set(result), {"items", "next_cursor", "has_more"})
    expect_equal(result["items"], [RECORDS[0]])


def check_limit_boundaries():
    expect_equal(len(paginate(deepcopy(RECORDS), None, 100)["items"]), 3)
    expect_raises(ValueError, lambda: paginate(deepcopy(RECORDS), None, 101))
    expect_raises(ValueError, lambda: paginate(deepcopy(RECORDS), None, 1.0))


def check_cursor_walk():
    records = [{"id": str(index)} for index in range(7)]
    cursor = None
    seen = []
    for _ in range(10):
        result = paginate(records, cursor, 2)
        seen.extend(item["id"] for item in result["items"])
        if not result["has_more"]:
            expect_equal(result["next_cursor"], None)
            break
        cursor = result["next_cursor"]
    expect_equal(seen, [str(index) for index in range(7)])


def check_empty_terminal():
    expect_equal(paginate([], None, 3), {"items": [], "next_cursor": None, "has_more": False})


def check_variant_boundary():
    records = [{"id": value} for value in ["a", "b", "c", "d"]]
    cursor = "1" if MODE == "offset" else "b"
    result = paginate(records, cursor, 2)
    if MODE == "exclusive":
        expected = {"items": records[2:4], "next_cursor": None, "has_more": False}
    elif MODE == "inclusive":
        expected = {"items": records[1:3], "next_cursor": "d", "has_more": True}
    else:
        expected = {"items": records[1:3], "next_cursor": "3", "has_more": True}
    expect_equal(result, expected)


def check_done_smoke():
    result = paginate([{"id": "only"}], None, 1)
    expect_equal(result["items"], [{"id": "only"}])


def check_error_atomicity():
    source = deepcopy(RECORDS)
    before = deepcopy(source)
    expect_raises(ValueError, lambda: paginate(source, None, 0))
    expect_equal(source, before)


record("E1_public_import", "R1", "visible", lambda: callable(paginate), "E1")
record("E1_first_page_shape", "R2", "visible", check_first_common, "E1")
record("E1_cursor_value", "R4", "visible", check_first, "E1")
record("E1_terminal_metadata", "R5", "visible", check_first_metadata, "E1")
record("E1_end_to_end", "D1", "visible", check_done_smoke, "E1")
record("E2_variant_cursor", "R4", "visible", check_second, "E2")
record("E2_variant_terminal", "R5", "visible", check_second_terminal, "E2")
record("E3_invalid_limit", "R3", "visible", check_invalid_limit, "E3")
record("E3_invalid_limit_error", "X1", "visible", check_invalid_limit, "E3")
record("E4_input_immutable", "R6", "visible", check_immutable, "E4")
record("E5_invalid_cursor", "R4", "visible", check_invalid_cursor, "E5")
record("E5_cursor_error_type", "X2", "visible", check_invalid_cursor, "E5")
record("E6_stdlib_dependencies", "C1", "visible", lambda: assert_stdlib_only(ROOT, "cursorvault"), "E6")

record("hidden_public_symbols", "R1", "hidden", lambda: (callable(paginate) and issubclass(CursorError, ValueError)))
record("hidden_output_exactness", "R2", "hidden", check_output_shape)
record("hidden_limit_boundaries", "R3", "hidden", check_limit_boundaries)
record("hidden_cursor_boundary", "R4", "hidden", check_variant_boundary)
record("hidden_empty_terminal", "R5", "hidden", check_empty_terminal)
record("hidden_repeatability", "R6", "hidden", check_immutable)
record("hidden_full_smoke", "D1", "hidden", check_done_smoke)
record("hidden_stdlib_only", "C1", "hidden", lambda: assert_stdlib_only(ROOT, "cursorvault"))
record("hidden_limit_atomicity", "X1", "hidden", check_error_atomicity)
record("hidden_cursor_type", "X2", "hidden", lambda: expect_raises(CursorError, lambda: paginate(deepcopy(RECORDS), 1, 2)))

finish(EXPECTED)
