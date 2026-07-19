EXPECTED = ["C1", "S1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1"]
ROOT = project_root("detreport")

try:
    module = importlib.import_module("detreport.public")
    build_report = module.build_report
    ReportError = module.ReportError
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


EVENTS = [
    {"id": "b", "category": "x", "amount_cents": 2},
    {"id": "a", "category": "x", "amount_cents": -1},
]


def parse_report(events):
    text = build_report(events)
    parsed = json.loads(text)
    expect_equal(text, json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return text, parsed


def aggregation_example():
    _, report = parse_report(deepcopy(EVENTS))
    expect_equal(set(report), {"groups", "grand_total_cents"})
    expect_equal(report["grand_total_cents"], 1)
    expect_equal(
        report["groups"],
        [{"category": "x", "count": 2, "total_cents": 1, "events": ["a", "b"]}],
    )


def order_expected(categories):
    if MODE == "ascending":
        return sorted(categories)
    if MODE == "descending":
        return sorted(categories, reverse=True)
    return categories


def ordering_example():
    events = [
        {"id": "1", "category": "beta", "amount_cents": 1},
        {"id": "2", "category": "alpha", "amount_cents": 1},
    ]
    _, report = parse_report(events)
    expect_equal([group["category"] for group in report["groups"]], order_expected(["beta", "alpha"]))


def unicode_example():
    text, report = parse_report([{"id": "u", "category": "café", "amount_cents": 3}])
    if "café" not in text or "\\u00e9" in text:
        raise AssertionError("Unicode category was escaped")
    expect_equal(report["groups"][0]["category"], "café")


def invalid_example():
    invalid = [
        [{"id": "a", "category": "x", "amount_cents": 1}, {"id": "a", "category": "y", "amount_cents": 2}],
        [{"id": "a", "category": "x", "amount_cents": True}],
        [{"id": "a", "category": "x"}],
        [{"id": "a", "category": "x", "amount_cents": 1, "extra": 2}],
        "not-a-list",
    ]
    for value in invalid:
        before = deepcopy(value)
        expect_raises(ReportError, lambda value=value: build_report(value))
        expect_equal(value, before)


def repeatability_example():
    events = deepcopy(EVENTS)
    before = deepcopy(events)
    first = build_report(events)
    second = build_report(events)
    expect_equal(first, second)
    expect_equal(events, before)


def cli_example():
    events = [
        {"id": "2", "category": "z", "amount_cents": 4},
        {"id": "1", "category": "a", "amount_cents": 5},
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "events.json"
        path.write_text(json.dumps(events), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        completed = subprocess.run(
            [sys.executable, "-m", "detreport", str(path)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
    expect_equal(completed.returncode, 0)
    expect_equal(completed.stderr, "")
    expect_equal(completed.stdout, build_report(events) + "\n")


def hidden_grouping():
    events = [
        {"id": "c", "category": "b", "amount_cents": 5},
        {"id": "a", "category": "a", "amount_cents": -2},
        {"id": "b", "category": "b", "amount_cents": 7},
    ]
    _, report = parse_report(events)
    by_category = {group["category"]: group for group in report["groups"]}
    expect_equal(by_category["b"], {"category": "b", "count": 2, "total_cents": 12, "events": ["b", "c"]})
    expect_equal(by_category["a"], {"category": "a", "count": 1, "total_cents": -2, "events": ["a"]})
    expect_equal(report["grand_total_cents"], 10)


def hidden_ordering():
    categories = ["m", "z", "a"]
    events = [
        {"id": str(index), "category": category, "amount_cents": index}
        for index, category in enumerate(categories)
    ]
    _, report = parse_report(events)
    expect_equal([group["category"] for group in report["groups"]], order_expected(categories))


record("E1_public_import", "R1", "visible", lambda: callable(build_report), "E1")
record("E1_grouping", "R3", "visible", aggregation_example, "E1")
record("E1_compact_schema", "R4", "visible", aggregation_example, "E1")
record("E1_total_and_immutability", "R6", "visible", aggregation_example, "E1")
record("E1_end_to_end", "D1", "visible", aggregation_example, "E1")
record("E1_integer_cents", "C1", "visible", aggregation_example, "E1")
record("E2_group_order", "R5", "visible", ordering_example, "E2")
record("E3_unicode_json", "R4", "visible", unicode_example, "E3")
record("E4_input_validation", "R2", "visible", invalid_example, "E4")
record("E4_report_error", "X1", "visible", invalid_example, "E4")
record("E5_input_immutable", "R6", "visible", repeatability_example, "E5")
record("E5_strict_determinism", "S1", "visible", repeatability_example, "E5")
record("E6_cli", "R7", "visible", cli_example, "E6")
record("E7_stdlib_dependencies", "C1", "visible", lambda: assert_stdlib_only(ROOT, "detreport"), "E7")

record("hidden_public_symbols", "R1", "hidden", lambda: callable(build_report) and issubclass(ReportError, ValueError))
record("hidden_validation_matrix", "R2", "hidden", invalid_example)
record("hidden_multiple_groups", "R3", "hidden", hidden_grouping)
record("hidden_exact_compact_json", "R4", "hidden", hidden_grouping)
record("hidden_three_group_order", "R5", "hidden", hidden_ordering)
record("hidden_grand_total_no_mutation", "R6", "hidden", repeatability_example)
record("hidden_cli_contract", "R7", "hidden", cli_example)
record("hidden_full_smoke", "D1", "hidden", hidden_grouping)
record("hidden_integer_cents_stdlib", "C1", "hidden", lambda: (aggregation_example(), assert_stdlib_only(ROOT, "detreport")))
record("hidden_byte_repeatability", "S1", "hidden", repeatability_example)
record("hidden_error_atomicity", "X1", "hidden", invalid_example)

finish(EXPECTED)
