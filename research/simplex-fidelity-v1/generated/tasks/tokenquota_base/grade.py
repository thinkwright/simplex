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

MODE = 'exact'
TASK_SLUG = 'tokenquota_base'

EXPECTED = ["C1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1"]
ROOT = project_root("tokenquota")

try:
    module = importlib.import_module("tokenquota.public")
    Bucket = module.Bucket
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value


def consumption_example():
    clock = FakeClock()
    bucket = Bucket(2, 0, clock)
    expect_equal([bucket.allow(1), bucket.allow(1), bucket.allow(1)], [True, True, False])
    expect_close(bucket.available(), 0)


def rounded_expected():
    return {"exact": 1.5, "floor": 1.0, "ceiling": 2.0}[MODE]


def rounding_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    expect_equal(bucket.allow(3), True)
    clock.value = 3
    expect_close(bucket.available(), rounded_expected())


def refill_property_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    bucket.allow(3)
    clock.value = 3
    value = bucket.available()
    if not 0 < value <= 3:
        raise AssertionError(f"refill did not produce a bounded positive balance: {value!r}")


def available_property_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    bucket.allow(3)
    clock.value = 3
    first = bucket.available()
    second = bucket.available()
    expect_close(first, second)


def cap_and_backward():
    clock = FakeClock(10)
    bucket = Bucket(3, 1, clock)
    expect_equal(bucket.allow(2), True)
    clock.value = 100
    expect_close(bucket.available(), 3)
    clock.value = 50
    expect_close(bucket.available(), 3)
    expect_equal(bucket.allow(3), True)


def invalid_example():
    clock = FakeClock()
    for args in [(0, 1), (-1, 1), (1, -1), (True, 1)]:
        expect_raises(ValueError, lambda args=args: Bucket(*args, clock=clock))
    bucket = Bucket(2, 0, clock)
    for amount in [0, -1, True, float("inf")]:
        expect_raises(ValueError, lambda amount=amount: bucket.allow(amount))
    expect_close(bucket.available(), 2)


def concurrent_example():
    clock = FakeClock()
    bucket = Bucket(20, 0, clock)
    results = []
    errors = []

    def worker():
        try:
            results.append(bucket.allow(1))
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(80)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    expect_equal(errors, [])
    expect_equal(sum(results), 20)
    expect_close(bucket.available(), 0)


def initial_and_failed_consumption():
    clock = FakeClock()
    bucket = Bucket(2.5, 0, clock)
    expect_close(bucket.available(), 2.5)
    expect_equal(bucket.allow(3), False)
    expect_close(bucket.available(), 2.5)
    expect_equal(bucket.allow(2.5), True)


def incremental_refill():
    clock = FakeClock()
    bucket = Bucket(5, 0.4, clock)
    bucket.allow(5)
    clock.value = 3
    first = bucket.available()
    expected_first = {"exact": 1.2, "floor": 1.0, "ceiling": 2.0}[MODE]
    expect_close(first, expected_first)
    expect_equal(bucket.allow(1), True)
    clock.value = 4
    second = bucket.available()
    expected_second = {"exact": 0.6, "floor": 0.0, "ceiling": 2.0}[MODE]
    expect_close(second, expected_second)


def available_no_consume():
    clock = FakeClock()
    bucket = Bucket(4, 0, clock)
    first = bucket.available()
    second = bucket.available()
    expect_close(first, 4)
    expect_close(second, 4)
    expect_equal(bucket.allow(4), True)


def backward_does_not_reset_origin():
    clock = FakeClock(10)
    bucket = Bucket(10, 1, clock)
    bucket.allow(10)
    clock.value = 5
    expect_close(bucket.available(), 0)
    clock.value = 11
    expected = {"exact": 1.0, "floor": 1.0, "ceiling": 1.0}[MODE]
    expect_close(bucket.available(), expected)


record("E1_public_import", "R1", "visible", lambda: callable(Bucket), "E1")
record("E1_consumption", "R2", "visible", consumption_example, "E1")
record("E1_end_to_end", "D1", "visible", consumption_example, "E1")
record("E2_elapsed_refill", "R3", "visible", refill_property_example, "E2")
record("E2_rounding_policy", "R4", "visible", rounding_example, "E2")
record("E2_available_value", "R5", "visible", available_property_example, "E2")
record("E3_capacity_backward_clock", "R3", "visible", cap_and_backward, "E3")
record("E4_invalid_values", "R6", "visible", invalid_example, "E4")
record("E4_value_error", "X1", "visible", invalid_example, "E4")
record("E5_thread_safety", "R7", "visible", concurrent_example, "E5")
record("E6_supplied_clock", "C1", "visible", backward_does_not_reset_origin, "E6")
record("E6_clock_refill", "R3", "visible", backward_does_not_reset_origin, "E6")

record("hidden_initial_full", "R1", "hidden", initial_and_failed_consumption)
record("hidden_failed_allow_no_consume", "R2", "hidden", initial_and_failed_consumption)
record("hidden_elapsed_capacity_clock", "R3", "hidden", cap_and_backward)
record("hidden_fractional_policy", "R4", "hidden", incremental_refill)
record("hidden_available_no_consume", "R5", "hidden", available_no_consume)
record("hidden_constructor_and_amount_validation", "R6", "hidden", invalid_example)
record("hidden_concurrent_limit", "R7", "hidden", concurrent_example)
record("hidden_full_smoke", "D1", "hidden", consumption_example)
record("hidden_clock_and_stdlib", "C1", "hidden", lambda: (backward_does_not_reset_origin(), assert_stdlib_only(ROOT, "tokenquota")))
record("hidden_invalid_atomicity", "X1", "hidden", invalid_example)

finish(EXPECTED)
