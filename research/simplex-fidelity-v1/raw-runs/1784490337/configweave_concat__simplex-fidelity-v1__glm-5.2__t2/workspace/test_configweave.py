"""Verification tests for the configweave public API."""
import ast
import copy
import os
import sys

from configweave.public import merge_layers


def test_e1_nested_mapping_merge():
    got = merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}])
    assert got == {"db": {"host": "a", "port": 2}}, got


def test_e2_list_concatenation():
    got = merge_layers([{"plugins": ["a", "b"]}, {"plugins": ["b", "c"]}])
    assert got == {"plugins": ["a", "b", "b", "c"]}, got


def test_e3_null_deletes():
    got = merge_layers([{"a": 1, "b": 2}, {"a": None}])
    assert got == {"b": 2}, got


def test_e4_no_mutation_or_sharing():
    layer1 = {"db": {"host": "a"}, "plugins": ["a", "b"]}
    layer2 = {"db": {"port": 2}, "plugins": ["c"]}
    snapshot1 = copy.deepcopy(layer1)
    snapshot2 = copy.deepcopy(layer2)

    result = merge_layers([layer1, layer2])

    # Mutating the result must not touch the sources.
    result["db"]["host"] = "changed"
    result["plugins"].append("zzz")
    assert layer1 == snapshot1, layer1
    assert layer2 == snapshot2, layer2

    # The result containers must not be the same objects as the inputs.
    assert result["db"] is not layer1["db"]
    assert result["db"] is not layer2["db"]
    assert result["plugins"] is not layer1["plugins"]
    assert result["plugins"] is not layer2["plugins"]


def test_e5_invalid_structure_raises_typeerror():
    bad_cases = [
        "not a list",
        [{"a": 1}, "not a dict"],
        [{"a": 1}, [1, 2, 3]],
        [{1: "non-string key"}],
        [{"a": {2: "nested non-string key"}}],
        [{"a": [{2: "non-string key inside list"}]}],
        None,
    ]
    for bad in bad_cases:
        try:
            merge_layers(bad)
        except TypeError:
            continue
        raise AssertionError("expected TypeError for {0!r}".format(bad))


def test_e5_invalid_does_not_mutate_inputs():
    layer = {"a": 1}
    snapshot = copy.deepcopy(layer)
    try:
        merge_layers([{1: "bad"}])
    except TypeError:
        pass
    # The valid layer passed alongside must remain untouched.
    try:
        merge_layers([layer, {1: "bad"}])
    except TypeError:
        pass
    assert layer == snapshot, layer


def test_empty_layers_returns_empty_dict():
    got = merge_layers([])
    assert got == {}, got
    got["x"] = 1  # must be a fresh dict
    assert merge_layers([]) == {}


def test_list_replaces_non_list():
    got = merge_layers([{"a": 1}, {"a": ["x"]}])
    assert got == {"a": ["x"]}, got
    got = merge_layers([{"a": {"k": 1}}, {"a": ["x"]}])
    assert got == {"a": ["x"]}, got


def test_non_list_replaces_list():
    got = merge_layers([{"a": ["x"]}, {"a": 1}])
    assert got == {"a": 1}, got
    got = merge_layers([{"a": ["x"]}, {"a": {"k": 1}}])
    assert got == {"a": {"k": 1}}, got


def test_null_delete_absent_is_noop():
    got = merge_layers([{"a": None}])
    assert got == {}, got
    got = merge_layers([{"a": 1}, {"b": None}])
    assert got == {"a": 1}, got


def test_nested_list_deep_copy():
    inner = {"k": [1]}
    layer = {"a": [inner]}
    result = merge_layers([layer])
    result["a"][0]["k"].append(2)
    assert layer == {"a": [{"k": [1]}]}, layer


def _imported_modules(node):
    """Return the top-level module names imported by an ast import node."""
    names = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            names.append(alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            names.append(node.module.split(".")[0])
    return names


def test_e6_only_stdlib_imports():
    import configweave

    pkg_dir = os.path.dirname(configweave.__file__)
    stdlib_top = set(sys.stdlib_module_names)
    allowed = stdlib_top | {"configweave"}

    for fname in os.listdir(pkg_dir):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(pkg_dir, fname)
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for top in _imported_modules(node):
                    assert top in allowed, "{0}: {1!r} not stdlib/configweave".format(
                        fname, top
                    )


def main():
    failures = []
    for name, obj in sorted(globals().items()):
        if name.startswith("test_") and callable(obj):
            try:
                obj()
                print("ok   {0}".format(name))
            except Exception as exc:  # noqa: BLE001
                failures.append((name, exc))
                print("FAIL {0}: {1}".format(name, exc))
    if failures:
        print("\n{0} test(s) failed".format(len(failures)))
        sys.exit(1)
    print("\nall tests passed")


if __name__ == "__main__":
    main()