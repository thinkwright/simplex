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

MODE = 'reject'
TASK_SLUG = 'wirecodec_reject'

EXPECTED = ["C1", "P1", "P2", "V1", "V2", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1", "X2"]
ROOT = project_root("wirecodec")

try:
    module = importlib.import_module("wirecodec.public")
    encode = module.encode
    decode = module.decode
    CodecError = module.CodecError
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum(record):
    import hashlib

    payload = {"id": record["id"], "value": record["value"], "version": 2}
    return hashlib.sha256(compact(payload).encode("utf-8")).hexdigest()


def encode_example():
    source = {"id": "a", "value": 2}
    before = deepcopy(source)
    text = encode(source)
    expect_equal(source, before)
    raw = json.loads(text)
    expect_equal(set(raw), {"checksum", "id", "value", "version"})
    expect_equal(raw["version"], 2)
    expect_equal(raw["checksum"], checksum(raw))
    expect_equal(text, compact(raw))


def decode_v1_example():
    expect_equal(decode('{"id":"a","value":2}'), {"id": "a", "value": 2, "version": 1})


def valid_v2_text(identifier="a", value=2):
    raw = {"id": identifier, "value": value, "version": 2}
    raw["checksum"] = checksum(raw)
    return compact(raw)


def decode_v2_example():
    expect_equal(decode(valid_v2_text()), {"id": "a", "value": 2, "version": 2})


def unknown_example(version=2):
    if version == 2:
        raw = json.loads(valid_v2_text())
    else:
        raw = {"id": "a", "value": 2, "version": 1}
    raw["note"] = "ok"
    text = compact(raw)
    if MODE == "reject":
        expect_raises(CodecError, lambda: decode(text))
    else:
        expected = {"id": "a", "value": 2, "version": version}
        if MODE == "preserve":
            expected["extras"] = {"note": "ok"}
        expect_equal(decode(text), expected)


def checksum_error():
    raw = json.loads(valid_v2_text())
    raw["value"] = 3
    expect_raises(CodecError, lambda: decode(compact(raw)))


def deterministic_no_mutation():
    source = {"id": "café", "value": -4}
    before = deepcopy(source)
    first = encode(source)
    second = encode(source)
    expect_equal(first, second)
    expect_equal(source, before)
    if "café" not in first:
        raise AssertionError("Unicode was escaped")


def invalid_encode():
    invalid = [
        {"value": 1},
        {"id": "", "value": 1},
        {"id": "a", "value": True},
        {"id": "a", "value": 1, "extra": 2},
    ]
    for record in invalid:
        before = deepcopy(record)
        expect_raises(ValueError, lambda record=record: encode(record))
        expect_equal(record, before)


def canonical_exactness():
    raw = json.loads(encode({"id": "z", "value": 10}))
    expect_equal(raw["checksum"], checksum(raw))
    expect_equal(encode({"id": "z", "value": 10}), compact(raw))


def v1_compatibility():
    expect_equal(decode('{"value":3,"id":"b"}'), {"id": "b", "value": 3, "version": 1})
    expect_equal(decode('{"version":1,"id":"b","value":3}'), {"id": "b", "value": 3, "version": 1})


def decode_errors():
    for text in ["not-json", "[]", '{"version":3,"id":"a","value":1}', '{"id":"a","value":true}']:
        expect_raises(CodecError, lambda text=text: decode(text))
    expect_raises(CodecError, lambda: decode(3))


def extras_absent_when_empty():
    result = decode(valid_v2_text("x", 1))
    if "extras" in result:
        raise AssertionError("extras must be omitted when no unknown fields exist")


record("E1_public_import", "R1", "visible", lambda: callable(encode) and callable(decode), "E1")
record("E1_encode_validation", "R2", "visible", encode_example, "E1")
record("E1_canonical_v2", "R3", "visible", encode_example, "E1")
record("E1_evolved_encoding", "V1", "visible", encode_example, "E1")
record("E1_preserved_imports", "P2", "visible", lambda: callable(encode) and callable(decode), "E1")
record("E1_end_to_end", "D1", "visible", encode_example, "E1")
record("E2_decode_v1", "R4", "visible", decode_v1_example, "E2")
record("E2_preserve_v1", "P1", "visible", decode_v1_example, "E2")
record("E3_v2_canonical", "R3", "visible", decode_v2_example, "E3")
record("E3_decode_v2", "R4", "visible", decode_v2_example, "E3")
record("E3_validate_checksum", "R5", "visible", decode_v2_example, "E3")
record("E3_evolved_decode", "V2", "visible", decode_v2_example, "E3")
record("E4_unknown_fields", "R6", "visible", unknown_example, "E4")
record("E5_checksum_mismatch", "R5", "visible", checksum_error, "E5")
record("E5_codec_error", "X2", "visible", checksum_error, "E5")
record("E6_encode_repeatability", "R2", "visible", deterministic_no_mutation, "E6")
record("E6_deterministic_bytes", "R7", "visible", deterministic_no_mutation, "E6")
record("E7_invalid_encode", "R2", "visible", invalid_encode, "E7")
record("E7_value_error", "X1", "visible", invalid_encode, "E7")
record("E8_stdlib_sha256", "C1", "visible", lambda: (encode_example(), assert_stdlib_only(ROOT, "wirecodec")), "E8")

record("hidden_public_symbols", "R1", "hidden", lambda: callable(encode) and callable(decode) and issubclass(CodecError, ValueError))
record("hidden_encode_input_contract", "R2", "hidden", invalid_encode)
record("hidden_canonical_checksum", "R3", "hidden", canonical_exactness)
record("hidden_explicit_v1", "R4", "hidden", v1_compatibility)
record("hidden_v2_checksum_rejection", "R5", "hidden", checksum_error)
record("hidden_unknown_v1", "R6", "hidden", lambda: unknown_example(1))
record("hidden_unknown_v2", "R6", "hidden", lambda: unknown_example(2))
record("hidden_empty_extras_omitted", "R6", "hidden", extras_absent_when_empty)
record("hidden_unicode_repeatability", "R7", "hidden", deterministic_no_mutation)
record("hidden_full_smoke", "D1", "hidden", decode_v2_example)
record("hidden_stdlib_and_sha256", "C1", "hidden", lambda: (canonical_exactness(), assert_stdlib_only(ROOT, "wirecodec")))
record("hidden_v1_compatibility", "P1", "hidden", v1_compatibility)
record("hidden_import_stability", "P2", "hidden", lambda: callable(encode) and callable(decode))
record("hidden_v2_encode", "V1", "hidden", canonical_exactness)
record("hidden_v2_decode", "V2", "hidden", decode_v2_example)
record("hidden_value_error", "X1", "hidden", invalid_encode)
record("hidden_codec_errors", "X2", "hidden", decode_errors)

finish(EXPECTED)
