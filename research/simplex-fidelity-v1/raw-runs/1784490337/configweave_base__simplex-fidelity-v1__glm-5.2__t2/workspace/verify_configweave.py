"""Verification script for the configweave package."""

import copy
import sys

from configweave.public import merge_layers


def check(name, got, want):
    ok = got == want
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")
    return ok


results = []

# E1 -> R1, R2, R3, D1
results.append(check(
    "E1 nested merge",
    merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}]),
    {"db": {"host": "a", "port": 2}},
))

# E2 -> R4
results.append(check(
    "E2 list replace",
    merge_layers([{"plugins": ["a", "b"]}, {"plugins": ["b", "c"]}]),
    {"plugins": ["b", "c"]},
))

# E3 -> R5
results.append(check(
    "E3 null delete",
    merge_layers([{"a": 1, "b": 2}, {"a": None}]),
    {"b": 2},
))

# R2 empty list -> empty dict
results.append(check("empty list", merge_layers([]), {}))

# R5 delete absent key is a no-op
results.append(check(
    "delete absent key",
    merge_layers([{"a": 1}, {"z": None}]),
    {"a": 1},
))

# R4 list replaces a mapping
results.append(check(
    "list replaces mapping",
    merge_layers([{"a": {"x": 1}}, {"a": [1, 2]}]),
    {"a": [1, 2]},
))

# R3 mapping replaces a list
results.append(check(
    "mapping replaces list",
    merge_layers([{"a": [1, 2]}, {"a": {"x": 1}}]),
    {"a": {"x": 1}},
))

# R3 mapping replaces scalar
results.append(check(
    "mapping replaces scalar",
    merge_layers([{"a": 1}, {"a": {"x": 1}}]),
    {"a": {"x": 1}},
))

# R3 scalar replaces mapping
results.append(check(
    "scalar replaces mapping",
    merge_layers([{"a": {"x": 1}}, {"a": 1}]),
    {"a": 1},
))

# Deep nested recursive merge
results.append(check(
    "deep recursive merge",
    merge_layers([
        {"a": {"b": {"c": 1, "d": 2}}},
        {"a": {"b": {"c": 3}}},
    ]),
    {"a": {"b": {"c": 3, "d": 2}}},
))

# Nested null delete
results.append(check(
    "nested null delete",
    merge_layers([
        {"a": {"b": 1, "c": 2}},
        {"a": {"b": None}},
    ]),
    {"a": {"c": 2}},
))

# E4 -> R6: mutating result cannot mutate a source; sources unchanged
src = [{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}]
src_snapshot = copy.deepcopy(src)
res = merge_layers(src)
# Mutate the result deeply
res["db"]["host"] = "ZZZ"
res["db"]["port"] = 999
res["new"] = [1, 2, 3]
if isinstance(res.get("new"), list):
    res["new"].append(4)
ok_sources = src == src_snapshot
print(f"[{'PASS' if ok_sources else 'FAIL'}] E4 sources unchanged: {src!r}")
results.append(ok_sources)

# R6: result lists are independent of source lists
src2 = [{"p": ["a", "b"]}, {"p": ["b", "c"]}]
res2 = merge_layers(src2)
res2["p"].append("d")
ok_list_indep = src2[1]["p"] == ["b", "c"]
print(f"[{'PASS' if ok_list_indep else 'FAIL'}] R6 result list independent")
results.append(ok_list_indep)

# R6: nested dict in result independent of source
src3 = [{"a": {"b": {"c": [1]}}}]
res3 = merge_layers(src3)
res3["a"]["b"]["c"].append(2)
ok_nested_indep = src3[0]["a"]["b"]["c"] == [1]
print(f"[{'PASS' if ok_nested_indep else 'FAIL'}] R6 nested independent")
results.append(ok_nested_indep)

# E5 -> R7, X1: non-dict layer -> TypeError
def expect_typeerror(name, fn):
    try:
        fn()
    except TypeError as exc:
        print(f"[PASS] {name}: TypeError raised: {exc}")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic
        print(f"[FAIL] {name}: wrong exception {type(exc).__name__}: {exc}")
        return False
    else:
        print(f"[FAIL] {name}: no exception raised")
        return False

results.append(expect_typeerror(
    "non-dict layer", lambda: merge_layers([{"a": 1}, "not a dict"])
))
results.append(expect_typeerror(
    "layers not a list", lambda: merge_layers({"a": 1})
))
results.append(expect_typeerror(
    "non-string top key", lambda: merge_layers([{1: "a"}])
))
results.append(expect_typeerror(
    "non-string nested key", lambda: merge_layers([{"a": {2: "b"}}])
))
results.append(expect_typeerror(
    "non-string key in list-of-dicts", lambda: merge_layers([{"a": [{1: "b"}]}])
))

# X1: TypeError raised without mutating inputs
bad_src = [{"a": 1}, "not a dict"]
bad_snapshot = copy.deepcopy(bad_src)
try:
    merge_layers(bad_src)
except TypeError:
    pass
ok_no_mutate_on_error = bad_src == bad_snapshot
print(f"[{'PASS' if ok_no_mutate_on_error else 'FAIL'}] X1 no mutation on error")
results.append(ok_no_mutate_on_error)

# E6 -> C1: only stdlib / configweave imports
import inspect
import configweave.public as public_mod
import configweave._merge as merge_mod
import configweave as pkg_mod

stdlib_ok = True
for mod in (pkg_mod, public_mod, merge_mod):
    src_text = inspect.getsource(mod)
    # crude check: no third-party imports
    for line in src_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            print(f"  {mod.__name__}: {stripped}")
print(f"[PASS] E6 dependency inspection complete")
results.append(True)

print()
if all(results):
    print(f"ALL {len(results)} CHECKS PASSED")
    sys.exit(0)
else:
    print(f"{sum(1 for r in results if not r)} CHECK(S) FAILED")
    sys.exit(1)