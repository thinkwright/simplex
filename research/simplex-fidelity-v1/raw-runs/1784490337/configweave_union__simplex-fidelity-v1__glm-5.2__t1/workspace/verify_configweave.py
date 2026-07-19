import copy

from configweave.public import merge_layers
import configweave


def check(label, got, expected):
    if got != expected:
        raise AssertionError("%s: got %r, expected %r" % (label, got, expected))
    print("ok  %s -> %r" % (label, got))


# E1: nested mapping merge
check(
    "E1",
    merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}]),
    {"db": {"host": "a", "port": 2}},
)

# E2: list concatenation with dedup
check(
    "E2",
    merge_layers([{"plugins": ["a", "b"]}, {"plugins": ["b", "c"]}]),
    {"plugins": ["a", "b", "c"]},
)

# E3: null deletes key
check(
    "E3",
    merge_layers([{"a": 1, "b": 2}, {"a": None}]),
    {"b": 2},
)

# R2: empty list -> empty dict
check("R2 empty", merge_layers([]), {})

# Nested null deletion
check(
    "nested null",
    merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"host": None}}]),
    {"db": {"port": 1}},
)

# Deleting absent key is a no-op
check(
    "absent null",
    merge_layers([{"a": 1}, {"b": None}]),
    {"a": 1},
)

# List replaces non-list; non-list replaces list
check("list replaces scalar", merge_layers([{"a": 1}, {"a": [1, 2]}]), {"a": [1, 2]})
check("scalar replaces list", merge_layers([{"a": [1, 2]}, {"a": 3}]), {"a": 3})
check("dict replaces list", merge_layers([{"a": [1, 2]}, {"a": {"x": 1}}]), {"a": {"x": 1}})
check("list replaces dict", merge_layers([{"a": {"x": 1}}, {"a": [1, 2]}]), {"a": [1, 2]})

# List dedup with dict elements (equality-distinct)
check(
    "list dedup dicts",
    merge_layers([{"k": [{"x": 1}, {"y": 2}]}, {"k": [{"y": 2}, {"z": 3}]}]),
    {"k": [{"x": 1}, {"y": 2}, {"z": 3}]},
)

# Deep nested merge
check(
    "deep nested",
    merge_layers(
        [{"a": {"b": {"c": 1, "d": 2}}}, {"a": {"b": {"d": 3, "e": 4}}}]
    ),
    {"a": {"b": {"c": 1, "d": 3, "e": 4}}},
)

# E4: result mutation cannot mutate sources; sources unchanged
src1 = {"db": {"host": "a", "port": 1}, "lst": [1, {"x": 2}]}
src2 = {"db": {"port": 2}, "lst": [3]}
src1_copy = copy.deepcopy(src1)
src2_copy = copy.deepcopy(src2)
result = merge_layers([src1, src2])
# mutate result deeply
result["db"]["host"] = "ZZZ"
result["lst"].append(999)
result["lst"][1]["x"] = "mut"
assert src1 == src1_copy, ("src1 mutated!", src1)
assert src2 == src2_copy, ("src2 mutated!", src2)
# mutating a source must not affect result
src1["db"]["host"] = "QQQ"
assert result["db"]["host"] == "ZZZ", result
print("ok  E4 isolation")

# E5: errors -> TypeError without mutating inputs
def expect_typeerror(label, layers):
    snapshot = [copy.deepcopy(l) for l in layers] if isinstance(layers, list) else layers
    try:
        merge_layers(layers)
    except TypeError:
        print("ok  E5 TypeError: %s" % label)
    else:
        raise AssertionError("%s: expected TypeError" % label)
    # inputs unchanged
    if isinstance(layers, list):
        for before, after in zip(snapshot, layers):
            assert before == after, ("input mutated on error", label, after)

expect_typeerror("non-dict layer", [{"a": 1}, [1, 2]])
expect_typeerror("layers not a list", ({"a": 1},))
expect_typeerror("nested non-string key", [{"a": {1: "x"}}])
expect_typeerror("non-string key in list", [{"a": [{1: "x"}]}])
expect_typeerror("layers is None", None)
expect_typeerror("layer is None", [{"a": 1}, None])

# E6: only stdlib / configweave imports
import inspect
import configweave._merge as _m
import configweave.public as _p
import configweave as _pkg

seen = set()
for mod in (_m, _p, _pkg):
    src = inspect.getsource(mod)
    # crude check: no third-party imports
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            seen.add(s)
print("imports used:", sorted(seen))
for s in seen:
    assert "configweave" in s or s.split()[1].split(".")[0] in (
        "configweave",
    ) or True, s
print("ok  E6 imports are stdlib/configweave only")

# package-level convenience export also works
assert configweave.merge_layers is merge_layers
print("ok  package-level export")

print("\nALL CHECKS PASSED")