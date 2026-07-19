"""Verification script covering all examples and rules."""

import json
import subprocess
import sys
import tempfile
import os

from detreport.public import ReportError, build_report


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[{0}] {1}{2}".format(status, label, " - " + detail if detail else ""))
    if not condition:
        sys.exit(1)


# E1: single-category report
events = [
    {"id": "b", "category": "x", "amount_cents": 2},
    {"id": "a", "category": "x", "amount_cents": -1},
]
out = build_report(events)
parsed = json.loads(out)
check("E1: single category group structure", len(parsed["groups"]) == 1)
g = parsed["groups"][0]
check("E1: category", g["category"] == "x")
check("E1: count", g["count"] == 2)
check("E1: total_cents", g["total_cents"] == 1)
check("E1: events sorted ascending", g["events"] == ["a", "b"])
check("E1: grand_total_cents", parsed["grand_total_cents"] == 1)

# E2: descending Unicode order
events2 = [
    {"id": "1", "category": "beta", "amount_cents": 1},
    {"id": "2", "category": "alpha", "amount_cents": 2},
]
out2 = build_report(events2)
parsed2 = json.loads(out2)
check("E2: descending order", [g["category"] for g in parsed2["groups"]] == ["beta", "alpha"])

# E3: non-ASCII preserved
events3 = [{"id": "1", "category": "café", "amount_cents": 5}]
out3 = build_report(events3)
check("E3: café literal preserved", "café" in out3)
check("E3: no \\u escape", "\\u" not in out3)

# E4: invalid inputs raise ReportError
def expect_error(label, evs):
    try:
        build_report(evs)
    except ReportError:
        check(label, True)
    else:
        check(label, False, "no error raised")

expect_error("E4: duplicate ids", [
    {"id": "a", "category": "x", "amount_cents": 1},
    {"id": "a", "category": "y", "amount_cents": 2},
])
expect_error("E4: boolean amount", [
    {"id": "a", "category": "x", "amount_cents": True},
])
expect_error("E4: missing field", [
    {"id": "a", "category": "x"},
])
expect_error("E4: extra field", [
    {"id": "a", "category": "x", "amount_cents": 1, "extra": 1},
])
expect_error("E4: empty id", [
    {"id": "", "category": "x", "amount_cents": 1},
])
expect_error("E4: empty category", [
    {"id": "a", "category": "", "amount_cents": 1},
])
expect_error("E4: float amount", [
    {"id": "a", "category": "x", "amount_cents": 1.5},
])
expect_error("E4: not a list", {"id": "a", "category": "x", "amount_cents": 1})

# E5: determinism + no mutation
events5 = [
    {"id": "b", "category": "x", "amount_cents": 2},
    {"id": "a", "category": "x", "amount_cents": -1},
]
snapshot = json.dumps(events5)
out5a = build_report(events5)
out5b = build_report(events5)
check("E5: byte-identical", out5a == out5b)
check("E5: input not mutated", json.dumps(events5) == snapshot)

# R4: top-level keys exactly
parsed5 = json.loads(out5a)
check("R4: top-level keys", set(parsed5.keys()) == {"groups", "grand_total_cents"})

# R4: compact JSON (no spaces)
check("R4: compact (no spaces)", ": " not in out5a and ", " not in out5a)

# R4: sorted keys
check("R4: keys sorted", '"category"' in out5a and out5a.index('"category"') < out5a.index('"count"'))

# E6: CLI
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(events, f)
    path = f.name
try:
    result = subprocess.run(
        [sys.executable, "-m", "detreport", path],
        capture_output=True, text=True,
    )
    check("E6: CLI exit 0", result.returncode == 0)
    check("E6: CLI stdout matches", result.stdout == out5a + "\n")
    check("E6: CLI stderr empty", result.stderr == "")
finally:
    os.unlink(path)

# E7: only stdlib + detreport imports
import detreport.report as rmod
import ast
src = open(rmod.__file__, encoding="utf-8").read()
tree = ast.parse(src)
imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for n in node.names:
            imports.append(n.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module)
bad = [i for i in imports if not (i == "detreport" or i.startswith("detreport.") or i in sys.stdlib_module_names)]
check("E7: only stdlib + detreport imports", bad == [], "bad: " + str(bad))

print("\nAll checks passed.")