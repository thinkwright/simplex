EXPECTED = ["C1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1"]
ROOT = project_root("configweave")

try:
    module = importlib.import_module("configweave.public")
    merge_layers = module.merge_layers
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


def nested_example():
    actual = merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}])
    expect_equal(actual, {"db": {"host": "a", "port": 2}})


def list_expected():
    if MODE == "replace":
        return {"plugins": ["b", "c"]}
    if MODE == "concat":
        return {"plugins": ["a", "b", "b", "c"]}
    return {"plugins": ["a", "b", "c"]}


def list_example():
    actual = merge_layers([{"plugins": ["a", "b"]}, {"plugins": ["b", "c"]}])
    expect_equal(actual, list_expected())


def deletion_example():
    expect_equal(merge_layers([{"a": 1, "b": 2}, {"a": None}]), {"b": 2})


def immutable_example():
    layers = [{"nested": {"items": [{"x": 1}]}}, {"other": [1, 2]}]
    before = deepcopy(layers)
    result = merge_layers(layers)
    expect_equal(layers, before)
    result["nested"]["items"][0]["x"] = 9
    result["other"].append(3)
    expect_equal(layers, before)


def invalid_example():
    expect_raises(TypeError, lambda: merge_layers([{"ok": {1: "bad"}}]))
    expect_raises(TypeError, lambda: merge_layers([{}, "bad"]))


def layer_order_and_empty():
    expect_equal(merge_layers([]), {})
    expect_equal(merge_layers([{"a": 1}, {"a": 2}, {"a": 3}]), {"a": 3})


def recursive_type_changes():
    layers = [
        {"a": {"b": {"c": 1}}, "scalar": 1},
        {"a": {"b": {"d": 2}}, "scalar": {"nested": True}},
    ]
    expect_equal(
        merge_layers(layers),
        {"a": {"b": {"c": 1, "d": 2}}, "scalar": {"nested": True}},
    )


def hidden_lists():
    old = [{"x": 1}, {"x": 2}]
    new = [{"x": 2}, {"x": 3}, {"x": 1}]
    result = merge_layers([{"v": old}, {"v": new}])["v"]
    if MODE == "replace":
        expected = new
    elif MODE == "concat":
        expected = old + new
    else:
        expected = [{"x": 1}, {"x": 2}, {"x": 3}]
    expect_equal(result, expected)


def nested_deletion():
    result = merge_layers([{"a": {"b": 1, "c": 2}}, {"a": {"b": None, "missing": None}}])
    expect_equal(result, {"a": {"c": 2}})


def invalid_atomicity():
    layers = [{"a": [1]}, {"b": {2: "bad"}}]
    before = deepcopy(layers)
    expect_raises(TypeError, lambda: merge_layers(layers))
    expect_equal(layers, before)


record("E1_public_import", "R1", "visible", lambda: callable(merge_layers), "E1")
record("E1_layer_order", "R2", "visible", nested_example, "E1")
record("E1_recursive_merge", "R3", "visible", nested_example, "E1")
record("E1_end_to_end", "D1", "visible", nested_example, "E1")
record("E2_list_policy", "R4", "visible", list_example, "E2")
record("E3_null_deletion", "R5", "visible", deletion_example, "E3")
record("E4_deep_immutability", "R6", "visible", immutable_example, "E4")
record("E5_invalid_structure", "R7", "visible", invalid_example, "E5")
record("E5_type_error", "X1", "visible", invalid_example, "E5")
record("E6_stdlib_dependencies", "C1", "visible", lambda: assert_stdlib_only(ROOT, "configweave"), "E6")

record("hidden_public_symbol", "R1", "hidden", lambda: callable(merge_layers))
record("hidden_empty_and_order", "R2", "hidden", layer_order_and_empty)
record("hidden_recursive_type_changes", "R3", "hidden", recursive_type_changes)
record("hidden_unhashable_lists", "R4", "hidden", hidden_lists)
record("hidden_nested_deletion", "R5", "hidden", nested_deletion)
record("hidden_no_shared_containers", "R6", "hidden", immutable_example)
record("hidden_recursive_key_validation", "R7", "hidden", invalid_example)
record("hidden_full_smoke", "D1", "hidden", recursive_type_changes)
record("hidden_stdlib_only", "C1", "hidden", lambda: assert_stdlib_only(ROOT, "configweave"))
record("hidden_error_atomicity", "X1", "hidden", invalid_atomicity)

finish(EXPECTED)
