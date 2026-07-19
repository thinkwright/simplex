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

MODE = 'conflict'
TASK_SLUG = 'idledger_base'

EXPECTED = ["C1", "C2", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "D1", "X1", "X2"]
ROOT = project_root("idledger")

try:
    module = importlib.import_module("idledger.public")
    Ledger = module.Ledger
    InsufficientFunds = module.InsufficientFunds
    CommandConflict = module.CommandConflict
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


DEBIT = {"id": "c1", "account": "a", "kind": "debit", "amount": 40}


def basic_example():
    ledger = Ledger({"a": 100})
    expect_equal(ledger.apply(deepcopy(DEBIT)), {"id": "c1", "account": "a", "balance": 60})
    expect_equal(ledger.snapshot(), {"a": 60})


def duplicate_example():
    ledger = Ledger({"a": 100})
    first = ledger.apply(deepcopy(DEBIT))
    first["balance"] = -999
    second = ledger.apply(deepcopy(DEBIT))
    expect_equal(second, {"id": "c1", "account": "a", "balance": 60})
    expect_equal(ledger.snapshot(), {"a": 60})


def conflict_example():
    ledger = Ledger({"a": 100})
    original = ledger.apply(deepcopy(DEBIT))
    replacement = {"id": "c1", "account": "a", "kind": "credit", "amount": 20}
    if MODE == "conflict":
        expect_raises(CommandConflict, lambda: ledger.apply(replacement))
        expect_equal(ledger.snapshot(), {"a": 60})
    elif MODE == "firstwins":
        expect_equal(ledger.apply(replacement), original)
        expect_equal(ledger.snapshot(), {"a": 60})
    else:
        expect_equal(ledger.apply(replacement), {"id": "c1", "account": "a", "balance": 120})
        expect_equal(ledger.snapshot(), {"a": 120})


def insufficient_example():
    ledger = Ledger({"a": 100})
    bad = {"id": "x", "account": "a", "kind": "debit", "amount": 101}
    expect_raises(InsufficientFunds, lambda: ledger.apply(bad))
    expect_equal(ledger.snapshot(), {"a": 100})
    good = {"id": "x", "account": "a", "kind": "credit", "amount": 1}
    expect_equal(ledger.apply(good), {"id": "x", "account": "a", "balance": 101})


def invalid_example():
    ledger = Ledger({"a": 10})
    before = ledger.snapshot()
    invalid = [
        {"id": "x", "account": "a", "kind": "credit", "amount": True},
        {"id": "x", "account": "a", "kind": "credit", "amount": 0},
        {"id": "x", "account": "a", "kind": "credit", "amount": 1, "extra": 2},
    ]
    for command in invalid:
        expect_raises(ValueError, lambda command=command: ledger.apply(command))
        expect_equal(ledger.snapshot(), before)


def concurrent_example():
    ledger = Ledger({"a": 0})
    errors = []

    def worker(index):
        try:
            ledger.apply({"id": f"c{index}", "account": "a", "kind": "credit", "amount": 1})
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    expect_equal(errors, [])
    expect_equal(ledger.snapshot(), {"a": 50})


def initial_and_snapshot():
    ledger = Ledger({"z": 2, "a": 1})
    snapshot = ledger.snapshot()
    expect_equal(list(snapshot), ["a", "z"])
    snapshot["a"] = 99
    expect_equal(ledger.snapshot(), {"a": 1, "z": 2})
    for bad in [{"a": -1}, {"a": True}, {1: 2}, []]:
        expect_raises(ValueError, lambda bad=bad: Ledger(bad))


def exact_command_contract():
    ledger = Ledger()
    result = ledger.apply({"id": "n", "account": "new", "kind": "credit", "amount": 7})
    expect_equal(result, {"id": "n", "account": "new", "balance": 7})
    expect_equal(set(result), {"id", "account", "balance"})


def hidden_conflict():
    ledger = Ledger({"a": 100})
    original_command = {"id": "same", "account": "a", "kind": "credit", "amount": 50}
    original_result = ledger.apply(original_command)
    replacement = {"id": "same", "account": "a", "kind": "debit", "amount": 30}
    if MODE == "conflict":
        expect_raises(CommandConflict, lambda: ledger.apply(replacement))
        expect_equal(ledger.snapshot(), {"a": 150})
    elif MODE == "firstwins":
        expect_equal(ledger.apply(replacement), original_result)
        expect_equal(ledger.snapshot(), {"a": 150})
    else:
        expect_equal(ledger.apply(replacement), {"id": "same", "account": "a", "balance": 70})
        expect_equal(ledger.snapshot(), {"a": 70})


def replacement_rollback():
    if MODE != "lastwins":
        hidden_conflict()
        return
    ledger = Ledger({"a": 10})
    ledger.apply({"id": "same", "account": "a", "kind": "credit", "amount": 5})
    expect_raises(
        InsufficientFunds,
        lambda: ledger.apply({"id": "same", "account": "a", "kind": "debit", "amount": 20}),
    )
    expect_equal(ledger.snapshot(), {"a": 15})
    expect_equal(
        ledger.apply({"id": "same", "account": "a", "kind": "credit", "amount": 5}),
        {"id": "same", "account": "a", "balance": 15},
    )


record("E1_public_import", "R1", "visible", lambda: callable(Ledger), "E1")
record("E1_initial_and_snapshot", "R2", "visible", basic_example, "E1")
record("E1_apply_result", "R3", "visible", basic_example, "E1")
record("E1_nonnegative_integer_balance", "C1", "visible", basic_example, "E1")
record("E1_end_to_end", "D1", "visible", basic_example, "E1")
record("E2_identical_idempotency", "R4", "visible", duplicate_example, "E2")
record("E3_conflict_policy", "R5", "visible", conflict_example, "E3")
record("E4_insufficient_funds", "R6", "visible", insufficient_example, "E4")
record("E4_insufficient_error", "X1", "visible", insufficient_example, "E4")
record("E5_invalid_atomicity", "R7", "visible", invalid_example, "E5")
record("E5_invalid_error", "X2", "visible", invalid_example, "E5")
record("E6_concurrent_credits", "R8", "visible", concurrent_example, "E6")
record("E7_stdlib_dependencies", "C2", "visible", lambda: assert_stdlib_only(ROOT, "idledger"), "E7")

record("hidden_public_symbols", "R1", "hidden", lambda: all(callable(value) for value in [Ledger]))
record("hidden_initial_validation_copy", "R2", "hidden", initial_and_snapshot)
record("hidden_exact_command_result", "R3", "hidden", exact_command_contract)
record("hidden_duplicate_result_copy", "R4", "hidden", duplicate_example)
record("hidden_conflict_policy", "R5", "hidden", hidden_conflict)
record("hidden_lastwins_rollback", "R5", "hidden", replacement_rollback)
record("hidden_failed_id_reusable", "R6", "hidden", insufficient_example)
record("hidden_invalid_commands_atomic", "R7", "hidden", invalid_example)
record("hidden_concurrency", "R8", "hidden", concurrent_example)
record("hidden_full_smoke", "D1", "hidden", exact_command_contract)
record("hidden_no_negative_balance", "C1", "hidden", insufficient_example)
record("hidden_stdlib_only", "C2", "hidden", lambda: assert_stdlib_only(ROOT, "idledger"))
record("hidden_insufficient_type", "X1", "hidden", insufficient_example)
record("hidden_value_error_type", "X2", "hidden", invalid_example)

finish(EXPECTED)
