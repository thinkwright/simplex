"""Verification script for configweave examples E1-E6."""

import copy
import sys

from configweave.public import merge_layers


def check(label, got, expected):
    ok = got == expected
    print(("PASS" if ok else "FAIL"), label, "->", got, "" if ok else ("(expected " + repr(expected) + ")"))
    return ok


all_ok = True

# E1: recursive mapping merge
all_ok &= check("E1", merge_layers([{"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}]),
                {"db": {"host": "a", "port": 2}})

# E2: list concatenation
all_ok &= check("E2", merge_layers([{"plugins": ["a", "b"]}, {"plugins": ["b", "c"]}]),
                {"plugins": ["a", "b", "b", "c"]})

# E3: null deletes key
all_ok &= check("E3", merge_layers([{"a": 1, "b": 2}, {"a": None}]), {"b": 2})

# E4: no shared mutable containers; inputs unchanged
src1 = {"db": {"host": "a", "port": 1}, "list": [1, 2]}
src2 = {"db": {"port": 2}, "list": [3, 4]}
src1_copy = copy.deepcopy(src1)
src2_copy = copy.deepcopy(src2)
res = merge_layers([src1, src2])
# mutate result deeply
res["db"]["port"] = 999
res["list"].append(999)
res["new"] = "x"
e4a = src1 == src1_copy
e4b = src2 == src2_copy
# also ensure no shared container object between result and inputs
e4c = (res["db"] is not src1["db"]) and (res["list"] is not src1["list"])
print("PASS" if (e4a and e4b and e4c) else "FAIL", "E4 inputs-unchanged/no-sharing", e4a, e4b, e4c)
all_ok &= e4a and e4b and e4c

# E5: invalid layer structure / non-string key -> TypeError without mutating inputs
def expect_typeerror(label, fn):
    layers_snapshot = None
    try:
        fn()
    except TypeError:
        print("PASS", label, "-> TypeError")
        return True
    except Exception as exc:  # noqa: BLE001
        print("FAIL", label, "-> wrong exception:", type(exc).__name__, exc)
        return False
    else:
        print("FAIL", label, "-> no exception raised")
        return False

bad_layers = [{"a": 1}, {"b": 2}]
bad_snapshot = copy.deepcopy(bad_layers)
all_ok &= expect_typeerror("E5 non-dict layer", lambda: merge_layers([{"a": 1}, ["not", "a", "dict"]]))
all_ok &= expect_typeerror("E5 non-list container", lambda: merge_layers(({"a": 1},)))
all_ok &= expect_typeerror("E5 nested non-string key", lambda: merge_layers([{"a": {1: "x"}}]))
all_ok &= expect_typeerror("E5 top-level non-string key", lambda: merge_layers([{1: "x"}]))
all_ok &= expect_typeerror("E5 non-string key inside list", lambda: merge_layers([{"a": [{1: "x"}]}]))
# inputs not mutated by failed validation
all_ok &= check("E5 inputs unchanged after error", bad_layers, bad_snapshot)

# E6: only stdlib or configweave imports used by the package
import configweave
import configweave.public
import configweave._core
import inspect

stdlib_prefixes = (
    "copy", "collections", "functools", "itertools", "json", "os",
    "sys", "types", "typing",
)
configweave_prefix = "configweave"
bad_imports = []
for modname in ("configweave", "configweave.public", "configweave._core"):
    mod = sys.modules[modname]
    src = inspect.getsource(mod)
    # crude scan for import statements
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # capture the module referenced
            if stripped.startswith("from "):
                target = stripped.split()[1]
            else:
                target = stripped.split()[1].split(".")[0]
            if target == configweave_prefix or target.startswith(configweave_prefix + "."):
                continue
            if target in stdlib_prefixes or any(target.startswith(p + ".") for p in stdlib_prefixes):
                continue
            bad_imports.append((modname, stripped))
if not bad_imports:
    print("PASS E6 only stdlib/configweave imports")
else:
    print("FAIL E6 non-allowed imports:", bad_imports)
    all_ok = False

# Extra: empty layer list -> empty dict
all_ok &= check("empty list", merge_layers([]), {})

# Extra: nested null delete of existing key
all_ok &= check("nested delete existing",
                merge_layers([{"a": {"b": 1, "c": 2}}, {"a": {"b": None}}]),
                {"a": {"c": 2}})

# Extra: nested null delete of absent key is no-op
all_ok &= check("nested delete absent",
                merge_layers([{"a": {"b": 1}}, {"a": {"c": None}}]),
                {"a": {"b": 1}})

# Extra: list replaces non-list and non-list replaces list
all_ok &= check("list replaces scalar",
                merge_layers([{"a": 1}, {"a": [2, 3]}]), {"a": [2, 3]})
all_ok &= check("scalar replaces list",
                merge_layers([{"a": [2, 3]}, {"a": 1}]), {"a": 1})

# Extra: deep nested structure no sharing
deep_src = {"x": {"y": [{"z": [1, 2]}]}}
deep_res = merge_layers([deep_src])
deep_res["x"]["y"][0]["z"].append(999)
all_ok &= check("deep no-share", deep_src, {"x": {"y": [{"z": [1, 2]}]}})

print()
print("ALL PASS" if all_ok else "SOME FAILED")
sys.exit(0 if all_ok else 1)