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

MODE = 'descending'
TASK_SLUG = 'detreport_descending'

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
