#!/usr/bin/env python3
"""Run reference, mapping, and cross-variant construction gates."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "generated"
REPORT = ROOT / "construction-report.json"


def run_grader(grader_task: Path, reference_task: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="simplex-fidelity-grade-") as directory:
        workspace = Path(directory)
        for source in (reference_task / "reference").iterdir():
            destination = workspace / source.name
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        shutil.copy2(grader_task / "grade.py", workspace / "grade.py")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            ["python3", "grade.py"],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"grader {grader_task.name} exited {completed.returncode}: "
                f"{completed.stderr[-1000:]}"
            )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError(f"grader {grader_task.name} produced no scorecard")
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"grader {grader_task.name} output is not JSON: {lines[-1][-500:]}"
            ) from error


def failed_requirements(scorecard: dict) -> list[str]:
    return sorted(
        requirement_id
        for requirement_id, value in scorecard["requirements"].items()
        if not value["passed"]
    )


def main() -> int:
    variants_doc = json.loads((GENERATED / "variants.json").read_text(encoding="utf-8"))
    variants = variants_doc["variants"]
    by_family: dict[str, dict[str, dict]] = {}
    for row in variants:
        by_family.setdefault(row["family"], {})[row["variant"]] = row

    report = {"schema_version": 1, "study": "simplex-fidelity-v1", "matching": [], "cross_variant": []}
    for row in variants:
        task = GENERATED / "tasks" / row["task"]
        scorecard = run_grader(task, task)
        expected_ids = sorted(item["id"] for item in row["requirements"])
        actual_ids = sorted(scorecard["requirements"])
        if actual_ids != expected_ids:
            raise RuntimeError(
                f"{row['task']}: requirement inventory mismatch expected={expected_ids} actual={actual_ids}"
            )
        if not scorecard.get("import_ok") or failed_requirements(scorecard):
            raise RuntimeError(
                f"{row['task']}: matching reference failed {failed_requirements(scorecard)}"
            )
        missing_hidden = sorted(
            requirement_id
            for requirement_id, value in scorecard["requirements"].items()
            if value.get("hidden_checks", 0) < 1
        )
        if missing_hidden:
            raise RuntimeError(f"{row['task']}: requirements without held-out checks {missing_hidden}")
        checked_pairs = {
            (check["example_id"], check["requirement_id"])
            for check in scorecard["checks"]
            if check.get("evidence") == "visible" and check.get("example_id")
        }
        expected_pairs = {
            (example["id"], requirement_id)
            for example in row["examples"]
            for requirement_id in example["covers"]
        }
        if checked_pairs != expected_pairs:
            raise RuntimeError(
                f"{row['task']}: direct example-target inventory mismatch "
                f"missing={sorted(expected_pairs - checked_pairs)} "
                f"unexpected={sorted(checked_pairs - expected_pairs)}"
            )
        expected_examples = {example["id"] for example in row["examples"]}
        report["matching"].append(
            {
                "task": row["task"],
                "requirements": len(expected_ids),
                "checks": len(scorecard["checks"]),
                "examples": len(expected_examples),
                "score": scorecard["score"],
            }
        )

    for family, family_variants in sorted(by_family.items()):
        base = family_variants["base"]
        base_task = GENERATED / "tasks" / base["task"]
        target = base["mutation_target"]
        for variant_name, variant in sorted(family_variants.items()):
            if variant_name == "base":
                continue
            variant_task = GENERATED / "tasks" / variant["task"]
            directions = [
                ("base_reference_to_variant_grader", variant_task, base_task),
                ("variant_reference_to_base_grader", base_task, variant_task),
            ]
            for direction, grader_task, reference_task in directions:
                scorecard = run_grader(grader_task, reference_task)
                failed = failed_requirements(scorecard)
                if failed != [target]:
                    raise RuntimeError(
                        f"{family}/{variant_name}/{direction}: expected only {target} to fail, got {failed}"
                    )
                report["cross_variant"].append(
                    {
                        "family": family,
                        "variant": variant_name,
                        "direction": direction,
                        "mutation_target": target,
                        "failed_requirements": failed,
                    }
                )

    report["summary"] = {
        "matching_references": len(report["matching"]),
        "cross_variant_checks": len(report["cross_variant"]),
        "all_matching_full_pass": True,
        "all_cross_variant_failures_localized": True,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"validated {len(report['matching'])} matching references and "
        f"{len(report['cross_variant'])} directional cross-variant checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
