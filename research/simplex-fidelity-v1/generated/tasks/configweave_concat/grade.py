from __future__ import annotations

import ast
import importlib
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
from collections import defaultdict
from copy import deepcopy
from pathlib import Path


CHECKS = []
IMPORT_OK = False


def requirement_type(requirement_id):
    prefixes = {
        "R": "rule",
        "D": "done_when",
        "X": "error",
        "C": "constraint",
        "P": "baseline_preserve",
        "V": "baseline_evolve",
        "S": "determinism_stable",
    }
    return prefixes.get(requirement_id[:1], "contract")


def project_root(project):
    cwd = Path.cwd()
    candidates = [cwd, cwd / TASK_SLUG]
    candidates.extend(path for path in cwd.iterdir() if path.is_dir())
    for candidate in candidates:
        if (candidate / project).is_dir() or (candidate / f"{project}.py").is_file():
            value = str(candidate.resolve())
            if value not in sys.path:
                sys.path.insert(0, value)
            return candidate
    return cwd


def record(name, requirement_id, evidence, callback, example_id=None):
    passed = False
    note = ""
    try:
        value = callback()
        if value is False:
            raise AssertionError("check returned false")
        passed = True
    except BaseException as error:
        note = f"{type(error).__name__}: {error}"[:240]
    CHECKS.append(
        {
            "name": name,
            "requirement_id": requirement_id,
            "requirement_type": requirement_type(requirement_id),
            "evidence": evidence,
            "example_id": example_id,
            "passed": passed,
            "note": note,
        }
    )


def fail_import(expected_requirements, error):
    note = f"{type(error).__name__}: {error}"[:240]
    for requirement_id in expected_requirements:
        CHECKS.append(
            {
                "name": f"import_blocked_{requirement_id}",
                "requirement_id": requirement_id,
                "requirement_type": requirement_type(requirement_id),
                "evidence": "hidden",
                "example_id": None,
                "passed": False,
                "note": note,
            }
        )


def expect_equal(actual, expected):
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def expect_close(actual, expected, tolerance=1e-9):
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def expect_raises(error_type, callback):
    try:
        callback()
    except error_type:
        return
    except BaseException as error:
        raise AssertionError(f"expected {error_type.__name__}, got {type(error).__name__}") from error
    raise AssertionError(f"expected {error_type.__name__}, no exception raised")


def assert_stdlib_only(root, project):
    package = root / project
    files = [package] if package.is_file() else list(package.rglob("*.py"))
    allowed_local = {project}
    stdlib = set(getattr(sys, "stdlib_module_names", set()))
    for file in files:
        if not file.is_file():
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name not in stdlib and name not in allowed_local:
                    raise AssertionError(f"non-standard-library import {name!r} in {file.name}")


def finish(expected_requirements):
    grouped = defaultdict(list)
    for check in CHECKS:
        grouped[check["requirement_id"]].append(check)
    unknown = sorted(set(grouped) - set(expected_requirements))
    missing = sorted(set(expected_requirements) - set(grouped))
    if unknown or missing:
        raise RuntimeError(f"grader mapping mismatch: unknown={unknown}, missing={missing}")
    requirements = {}
    for requirement_id in expected_requirements:
        rows = grouped[requirement_id]
        passed_checks = sum(1 for row in rows if row["passed"])
        requirements[requirement_id] = {
            "type": requirement_type(requirement_id),
            "passed": passed_checks == len(rows),
            "passed_checks": passed_checks,
            "total_checks": len(rows),
            "visible_checks": sum(1 for row in rows if row["evidence"] == "visible"),
            "hidden_checks": sum(1 for row in rows if row["evidence"] == "hidden"),
        }
    passed = sum(1 for value in requirements.values() if value["passed"])
    total = len(requirements)
    print(
        json.dumps(
            {
                "score": passed / total if total else 0.0,
                "passed": passed,
                "total": total,
                "import_ok": IMPORT_OK,
                "requirements": requirements,
                "checks": CHECKS,
            },
            sort_keys=True,
        )
    )

MODE = 'concat'
TASK_SLUG = 'configweave_concat'

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
